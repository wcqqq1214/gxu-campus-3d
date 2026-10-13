"""Paired basketball LOD assets; incremental exports retain published ground bytes."""
import copy
import hashlib
import json
import struct
import sys
from pathlib import Path
if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from preserve_glb_geometry import compact_buffer_views, mesh_nodes_by_name, unpack


def write_glb(path, doc, binary):
    header = json.dumps(doc, separators=(',', ':')).encode()
    header += b' ' * (-len(header) % 4)
    binary += b'\0' * (-len(binary) % 4)
    path.write_bytes(struct.pack('<4sII', b'glTF', 2, 28 + len(header) + len(binary))
                     + struct.pack('<I4s', len(header), b'JSON') + header
                     + struct.pack('<I4s', len(binary), b'BIN\0') + binary)


def extract_bank(raw, name, path):
    """Copy an untextured, static bank without decoding any of its primitives."""
    doc, binary = unpack(raw)
    node = copy.deepcopy(mesh_nodes_by_name(doc)[name])
    if set(node) - {'name', 'mesh', 'extras'}:
        raise ValueError('Expected an untransformed static basketball bank')
    mesh = copy.deepcopy(doc['meshes'][node['mesh']])
    materials, accessors = [], []
    for primitive in mesh['primitives']:
        if set(primitive) - {'mode', 'material', 'attributes', 'indices', 'extensions'}:
            raise ValueError('Unsupported basketball primitive')
        if set(primitive.get('extensions', {})) != {'KHR_draco_mesh_compression'}:
            raise ValueError('Expected compressed basketball geometry')
        material = doc['materials'][primitive['material']]
        # The current bank uses plain colours. Fail instead of dropping future maps.
        if 'Texture' in json.dumps(material) or material.get('extensions'):
            raise ValueError('Textured or extended basketball materials need explicit handling')
        primitive['material'] = len(materials)
        materials.append(material)
        for container, key in [(primitive, 'indices'), *[(primitive['attributes'], k)
                                                       for k in primitive['attributes']]]:
            accessor = doc['accessors'][container[key]]
            if 'bufferView' in accessor or 'sparse' in accessor:
                raise ValueError('Expected compressed-only bank accessors')
            container[key] = len(accessors)
            accessors.append(accessor)
    node['mesh'] = 0
    result = dict(asset=doc['asset'], scene=0, scenes=[{'nodes': [0]}], nodes=[node],
                  meshes=[mesh], materials=materials, accessors=accessors,
                  buffers=doc['buffers'], bufferViews=doc['bufferViews'],
                  extensionsUsed=['KHR_draco_mesh_compression'],
                  extensionsRequired=['KHR_draco_mesh_compression'])
    write_glb(path, result, binary)
    compact_buffer_views(path)


def manifest_entries(data, directory):
    return [dict(id=bank['id'], url='models/' + bank['id'] + '.glb',
                 bytes=(directory / (bank['id'] + '.glb')).stat().st_size,
                 sha256=hashlib.sha256((directory / (bank['id'] + '.glb')).read_bytes()).hexdigest(),
                 bounds=bank['bounds']) for bank in data['banks']]


if __name__ == '__main__':
    import argparse
    import tempfile
    import bpy
    from geometry import MATERIALS
    from basketball import bank_model
    from export_attributes import omit_unused_uvs
    from preserve_glb_geometry import replace_compressed_node_parts, preserve_geometry

    parser = argparse.ArgumentParser(description='Create paired court assets in an isolated candidate.')
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    root = Path(__file__).resolve().parents[1]
    if args.candidate.resolve() == root:
        raise ValueError('Validate an isolated candidate before promoting it')
    models = args.candidate / 'public/models'
    target = models / 'base.glb'
    previous = target.read_bytes()
    doc, _ = unpack(previous)
    data = json.loads((root / 'public/data/basketball.json').read_text())
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    # Resolve by exact material name instead of relying on Blender slot order.
    names = {doc['materials'][p['material']]['name'] for bank in data['banks']
             for p in doc['meshes'][mesh_nodes_by_name(doc)[bank['id']]['mesh']]['primitives']}
    order = list(dict.fromkeys(doc['materials'][p['material']]['name'] for bank in data['banks']
                              for p in doc['meshes'][mesh_nodes_by_name(doc)[bank['id']]['mesh']]['primitives']))
    MATERIALS[:] = [bpy.data.materials[name] for name in order]
    colors = {m.name: i for i, m in enumerate(MATERIALS)}
    for bank in data['banks']:
        name = bank['id']
        original = doc['meshes'][mesh_nodes_by_name(doc)[name]['mesh']]
        if not any(doc['materials'][p['material']]['name'] == 'goalNet' for p in original['primitives']):
            raise ValueError('Input must be the full-detail bank, not an already simplified base')
        extract_bank(previous, name, models / (name + '.glb'))
        obj = bank_model(bank, data['courts'], colors, False).object(
            name + '-far', bpy.context.scene.collection, {'layer': 'sports'})
        try:
            with tempfile.TemporaryDirectory(prefix='gxu-court-lod-') as directory:
                donor = Path(directory) / 'far.glb'
                bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True)
                with omit_unused_uvs():
                    bpy.ops.export_scene.gltf(filepath=str(donor), export_format='GLB', use_selection=True,
                        export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6,
                        export_draco_position_quantization=15, export_draco_normal_quantization=6,
                        export_materials='EXPORT', export_cameras=False, export_lights=False)
                replace_compressed_node_parts(target, name, [donor.read_bytes()])
                preserve_geometry(previous, target, [name], materials=names - {'goalNet', 'courtOrange'})
                compact_buffer_views(target)
        finally:
            mesh = obj.data; bpy.data.objects.remove(obj, do_unlink=True); bpy.data.meshes.remove(mesh)
    manifest = json.loads((root / 'public/data/models.json').read_text())
    manifest['sports'] = manifest_entries(data, models)
    raw = target.read_bytes()
    manifest['base'].update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    (args.candidate / 'public/data/models.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print('Initial bytes:', len(raw) + manifest['trees']['bytes'], flush=True)
