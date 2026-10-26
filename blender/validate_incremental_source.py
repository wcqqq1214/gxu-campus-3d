"""Compare untouched editable objects before publishing a staged incremental update."""
import array
import hashlib
import json
import sys
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[1]
args = dict(a[2:].split('=', 1) for a in sys.argv if a.startswith('--') and '=' in a)
baseline = Path(args['baseline-root'])
mode = args['update-kind']
bridges = {b['id'] for b in json.loads((ROOT / 'public/data/infrastructure.json').read_text())['bridges']}


def updated(obj):
    name = obj.name
    if mode == 'new-east-gate':
        return obj.get('landmark') == 'new-east-gate'
    if name in {'roads', 'terrain', 'green'} or name.startswith(('树木示意-', 'site-', 'shore-', 'paving-', 'vegetation-low-')):
        return True
    if obj.get('siteId') or obj.get('pavingId'):
        return True
    if mode == 'roads':
        return name.startswith('infra-approach-') or obj.get('landmark') in bridges
    return name == '其他运动场地' or bool(obj.get('basketballCourt') or obj.get('basketballBank'))


def signatures(path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    output = {}
    for obj in bpy.context.scene.objects:
        if updated(obj):
            continue
        h = hashlib.sha256()
        def add(value):
            h.update(repr(value).encode())
        add(obj.type); add(list(map(tuple, obj.matrix_world)))
        add(sorted((k, str(v)) for k, v in obj.items()))
        if obj.type == 'MESH':
            mesh = obj.data
            for collection, attr, size, typecode in ((mesh.vertices, 'co', 3, 'f'), (mesh.loops, 'vertex_index', 1, 'i'),
                    (mesh.polygons, 'loop_total', 1, 'i'), (mesh.polygons, 'material_index', 1, 'i')):
                values = array.array(typecode, [0]) * (len(collection) * size)
                collection.foreach_get(attr, values); h.update(values.tobytes())
            for layer in mesh.uv_layers:
                add(layer.name)
                values = array.array('f', [0]) * (len(layer.data) * 2)
                layer.data.foreach_get('uv', values); h.update(values.tobytes())
            add([(m.name, tuple(m.diffuse_color), m.surface_render_method) if m else None for m in mesh.materials])
            add([g.name for g in obj.vertex_groups])
            for vertex in mesh.vertices:
                add([(g.group, g.weight) for g in vertex.groups])
        output[obj.name] = h.hexdigest()
    return output


before = signatures(baseline / 'blender/gxu-campus.blend')
after = signatures(ROOT / 'blender/gxu-campus.blend')
changed = sorted(name for name in before.keys() | after.keys() if before.get(name) != after.get(name))
if changed:
    raise RuntimeError(f'Unrelated editable objects changed: {changed}')
print(f'Preserved {len(before)} unrelated editable objects', flush=True)
