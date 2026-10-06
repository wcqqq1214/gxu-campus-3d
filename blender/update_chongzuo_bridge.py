"""Remove the obsolete name plaques from the source and close-view bridge GLB.

Run with Blender --background --python-exit-code 1 --python this_file.
The coarse bridge never included plaques and does not need re-exporting.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path

import bmesh
import bpy

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / 'public/models/chongzuo-bridge.glb'
SOURCE = ROOT / 'blender/gxu-campus.blend'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def faces(mesh, excluded=()):
    """Compare coordinates and materials of every retained source face."""
    return Counter(
        (tuple(tuple(mesh.vertices[i].co) for i in p.vertices),
         mesh.materials[p.material_index].name)
        for p in mesh.polygons
        if not any(i in excluded for i in p.vertices)
    )


def main():
    unchanged = {p: digest(p) for p in MODEL.parent.glob('*.glb') if p != MODEL}
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    obj = next(o for o in bpy.data.objects if o.get('landmark') == 'chongzuo-bridge')
    groups = [g for g in obj.vertex_groups if g.name.startswith('崇左桥入口题名')]
    if groups:
        assert len(groups) == 2, 'Expected the two entrance plaques'
        indices = {g.index for g in groups}
        removed = {v.index for v in obj.data.vertices
                   if any(g.group in indices and g.weight > 0 for g in v.groups)}
        assert removed, 'Plaque groups must contain vertices'
        before = faces(obj.data, removed)
        mesh = bmesh.new()
        mesh.from_mesh(obj.data)
        mesh.verts.ensure_lookup_table()
        bmesh.ops.delete(mesh, geom=[mesh.verts[i] for i in removed], context='VERTS')
        mesh.to_mesh(obj.data)
        mesh.free()
        for group in groups:
            obj.vertex_groups.remove(group)
        obj.data.update()
        assert faces(obj.data) == before, 'Geometry outside the plaques changed'
        print(f'Removed {len(removed)} plaque vertices; retained {len(obj.data.polygons)} faces', flush=True)
    assert not any(g.name.startswith('崇左桥入口题名') for g in obj.vertex_groups)
    assert all(obj.data.materials[p.material_index].name != 'bridgePlaque'
               for p in obj.data.polygons)

    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    original_name = obj.name
    obj.name = 'landmark-chongzuo-bridge'
    try:
        bpy.ops.export_scene.gltf(
            filepath=str(MODEL), export_format='GLB', use_selection=True,
            export_extras=True, export_draco_mesh_compression_enable=True,
            export_draco_mesh_compression_level=6, export_draco_position_quantization=16,
            export_draco_normal_quantization=10, export_materials='EXPORT',
            export_cameras=False, export_lights=False)
    finally:
        obj.name = original_name
    assert all(digest(p) == expected for p, expected in unchanged.items())
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE), compress=True)
    manifest_path = ROOT / 'public/data/models.json'
    manifest = json.loads(manifest_path.read_text())
    entry = next(e for e in manifest['landmarks'] if e['id'] == 'chongzuo-bridge')
    entry.update(bytes=MODEL.stat().st_size, sha256=digest(MODEL))
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print('Updated source, bridge GLB and manifest; all other GLBs unchanged', flush=True)


if __name__ == '__main__':
    main()
