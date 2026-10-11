"""Make an isolated road-cleanup candidate, preserving other published assets.

Usage: blender -b --python-exit-code 1 --python blender/update_road_display.py
       -- --output-dir=work/road-junction-cleanup/candidate
Inspect/validate the candidate before copying its blend, base GLB and manifest.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'blender'))
sys.path.insert(0, str(ROOT/'scripts'))
import geometry
from geometry import Mesh
from road_display_cleanup import load_cuts, trim_mesh
from export_attributes import omit_unused_uvs
from preserve_glb_geometry import preserve_geometry, compact_buffer_views, unpack, mesh_nodes_by_name


def signatures(raw):
    doc, binary = unpack(raw)
    result = {}
    for name, node in mesh_nodes_by_name(doc).items():
        result[name] = []
        for p in doc['meshes'][node['mesh']]['primitives']:
            view = doc['bufferViews'][p['extensions']['KHR_draco_mesh_compression']['bufferView']]
            start = view.get('byteOffset', 0)
            result[name].append((doc['materials'][p['material']]['name'],
                                 hashlib.sha256(binary[start:start+view['byteLength']]).hexdigest()))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    output = args.output_dir.resolve()
    if output == ROOT or ROOT/'public' in output.parents or ROOT/'blender' in output.parents:
        raise ValueError('Use an isolated candidate output directory')
    output.mkdir(parents=True, exist_ok=True)
    cuts = load_cuts()
    original = (ROOT/'public/models/base.glb').read_bytes()
    document, _ = unpack(original)
    metadata = mesh_nodes_by_name(document)['roads'].get('extras', {})
    if metadata.get('positionQuantizationBits') != 18 or not metadata.get('sharedPositionQuantizationBounds'):
        raise ValueError('Road display update requires the existing shared 18-bit position grid')
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'))
    source = bpy.data.objects['roads']
    untouched = {o.name: (o.as_pointer(), o.data.as_pointer() if o.data else None)
                 for o in bpy.data.objects if o != source}
    mesh = Mesh()
    mesh.v = [tuple(v.co) for v in source.data.vertices]
    mesh.f = [tuple(p.vertices) for p in source.data.polygons]
    mesh.m = [p.material_index for p in source.data.polygons]
    from mathutils import Matrix
    if source.matrix_world != Matrix.Identity(4) or source.modifiers:
        raise ValueError('Expected ordinary source roads without transforms or modifiers')
    mesh.source_uvs = [[tuple(source.data.uv_layers.active.data[i].uv)
                       for i in p.loop_indices] for p in source.data.polygons]
    fixed, report = trim_mesh(mesh, cuts)
    assert all(r['removedArea'] > 0 for r in report.values()), report
    geometry.MATERIALS = list(source.data.materials)
    changed = {source.data.materials[i].name for i in fixed.changed_materials}
    obj = fixed.object('road-display-candidate', source.users_collection[0], dict(source.items()))
    for p, uvs, old_index in zip(obj.data.polygons, fixed.source_uvs, fixed.source_face_indices):
        p.use_smooth = source.data.polygons[old_index].use_smooth
        for i, uv in zip(p.loop_indices, uvs):
            obj.data.uv_layers.active.data[i].uv = uv
    # Assert exact preservation outside every cut, including source UVs.
    def records(value):
        return Counter((tuple(value.v[i] for i in f), mat, tuple(tuple(u) for u in uv))
                       for f, mat, uv in zip(value.f, value.m, value.source_uvs))
    removed = records(mesh) - records(fixed)
    outside_changed = 0
    for points, _, _ in removed:
        if not any(max(p[0] for p in points) > c['bounds'][0]
                   and min(p[0] for p in points) < c['bounds'][2]
                   and max(p[1] for p in points) > c['bounds'][1]
                   and min(p[1] for p in points) < c['bounds'][3] for c in cuts):
            outside_changed += 1
    assert not outside_changed
    source_data = source.data
    bpy.data.objects.remove(source, do_unlink=True)
    if source_data.users == 0:
        bpy.data.meshes.remove(source_data)
    obj.name = 'roads'
    assert all((bpy.data.objects[k].as_pointer(), bpy.data.objects[k].data.as_pointer()
                if bpy.data.objects[k].data else None) == value for k, value in untouched.items())
    (output/'blender').mkdir(exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output/'blender/gxu-campus.blend'), compress=True)
    # The shipping road contains past export-only seam/UV fixes. Trim its actual
    # decoded triangles rather than recreating those unrelated corrections.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(ROOT/'public/models/base.glb'))
    bpy.context.view_layer.update()
    delivered = next(o for o in bpy.context.scene.objects
                     if o.type == 'MESH' and o.name.split('.')[0] == 'roads')
    mesh = Mesh()
    mesh.v = [tuple(delivered.matrix_world @ v.co) for v in delivered.data.vertices]
    mesh.f = [tuple(p.vertices) for p in delivered.data.polygons]
    mesh.m = [p.material_index for p in delivered.data.polygons]
    mesh.source_uvs = [[tuple(delivered.data.uv_layers.active.data[i].uv)
                       for i in p.loop_indices] for p in delivered.data.polygons]
    # glTF is Y-up. Retain the full decoded road's shared grid, including the
    # northmost extrema about to be removed, so every old vertex re-encodes
    # onto the same lattice as the untouched material primitives.
    import numpy as np
    positions = np.array(mesh.v, dtype=np.float32)[:, [0, 2, 1]]
    positions[:, 2] *= -1
    origin = positions.min(axis=0)
    domain = {'origin': origin.tolist(), 'range': float((positions.max(axis=0)-origin).max())}
    fixed, decoded_report = trim_mesh(mesh, cuts)
    geometry.MATERIALS = list(delivered.data.materials)
    assert changed == {delivered.data.materials[i].name for i in fixed.changed_materials}
    exported = fixed.object('roads', bpy.context.scene.collection, {'layer': 'roads'})
    for p, uvs, old_index in zip(exported.data.polygons, fixed.source_uvs, fixed.source_face_indices):
        p.use_smooth = delivered.data.polygons[old_index].use_smooth
        for i, uv in zip(p.loop_indices, uvs):
            exported.data.uv_layers.active.data[i].uv = uv
    bpy.ops.object.select_all(action='DESELECT')
    exported.select_set(True)
    with omit_unused_uvs(deduplicate_vertices=True, share_position_bounds=True, position_domain=domain):
        bpy.ops.export_scene.gltf(
            filepath=str(output/'roads.glb'), export_format='GLB', use_selection=True,
            export_extras=True, export_draco_mesh_compression_enable=True,
            export_draco_mesh_compression_level=6, export_draco_position_quantization=18,
            export_draco_texcoord_quantization=12, export_draco_normal_quantization=6,
            export_materials='EXPORT', export_cameras=False, export_lights=False)
    candidate = output/'public/models/base.glb'
    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.write_bytes(original)
    preserve_geometry((output/'roads.glb').read_bytes(), candidate, ['roads'], materials=changed)
    compact_buffer_views(candidate)
    before, after = signatures(original), signatures(candidate.read_bytes())
    assert before.keys() == after.keys()
    assert all(v == after[k] for k, v in before.items() if k != 'roads')
    assert all(p == q for p, q in zip(before['roads'], after['roads']) if p[0] not in changed)
    manifest = json.loads((ROOT/'public/data/models.json').read_text())
    raw = candidate.read_bytes()
    manifest['base'].update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    assert len(raw) + manifest['trees']['bytes'] < 6_000_000
    (output/'public/data').mkdir(exist_ok=True)
    (output/'public/data/models.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    summary = dict(cuts=report, decodedCuts=decoded_report,
                   changedBaseNodes=['roads'], changedRoadMaterials=sorted(changed),
                   retainedBaseNodes=len(before)-1, retainedSourceObjects=len(untouched),
                   outsideChangedFaces=outside_changed, positionDomain=domain, baseBytes=len(raw))
    (output/'report.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
