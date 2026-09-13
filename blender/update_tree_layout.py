"""Update editable tree rotation; --ground also resolves final terrain anchors."""
import bpy
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'blender'))
from vegetation_layout import tree_rotation

path = ROOT / 'blender/gxu-campus.blend'
bpy.ops.wm.open_mainfile(filepath=str(path))
trees = json.loads((ROOT / 'public/data/vegetation.json').read_text())
grounded = '--ground' in sys.argv
if grounded:
    from tree_layout import ground_tree_rows
    terrain = bpy.data.objects['terrain']
    trees = ground_tree_rows(trees, [terrain.matrix_world@v.co for v in terrain.data.vertices],
                             [tuple(p.vertices) for p in terrain.data.polygons])
expected = {(row[0],row[1]): row[2:] for row in trees}
objects = [o for o in bpy.context.scene.objects if o.name.startswith('树木示意-')]
assert len(objects) == len(expected) == len(trees), 'Tree count mismatch; use full model build'
keys = {(round(o.location.x,1), round(o.location.y,1)) for o in objects}
assert keys == set(expected), 'Tree positions changed; use full model build'
unchanged = {o.name: (tuple(v for row in o.matrix_world for v in row), o.data.as_pointer() if o.data else None)
             for o in bpy.context.scene.objects if not o.name.startswith('树木示意-')}
corrections = []
for o in objects:
    x,y = round(o.location.x,1), round(o.location.y,1)
    h,typ = expected[(x,y)][:2]
    assert max(abs(v-h/9) for v in o.scale) < 1e-5
    o.rotation_euler.z = tree_rotation(x,y)
    if grounded:
        corrections.append(expected[(x,y)][2]-o.location.z)
        o.location.z = expected[(x,y)][2]
bpy.context.view_layer.update()
for name, (matrix, data) in unchanged.items():
    o = bpy.context.scene.objects[name]
    assert tuple(v for row in o.matrix_world for v in row) == matrix
    assert (o.data.as_pointer() if o.data else None) == data
bpy.ops.wm.save_as_mainfile(filepath=str(path))
if grounded:
    (ROOT / 'public/data/vegetation.json').write_text(json.dumps(trees,separators=(',',':'))+'\n')
# Inspect saved transforms, not just the in-memory assignment.
bpy.ops.wm.open_mainfile(filepath=str(path))
errors = []
for o in bpy.context.scene.objects:
    if not o.name.startswith('树木示意-'): continue
    x,y = round(o.location.x,1), round(o.location.y,1)
    errors.append(abs(math.remainder(o.rotation_euler.z-tree_rotation(x,y), math.tau)))
assert len(errors) == len(trees) and max(errors) < 1e-6
report = {'trees': len(errors), 'maxSavedRotationErrorRadians': max(errors),
          'unchangedNonTreeObjects': len(unchanged), 'passed': True,
          'grounded': grounded,
          'groundCorrectionMeters': {'min': min(corrections), 'max': max(corrections), 'over25cmAbsolute': sum(abs(v)>.25 for v in corrections)} if corrections else None,
          'scope': 'Saved tree rotations and optional final-terrain elevation; horizontal positions, templates, scales and other object transforms preserved. GLBs are not re-exported.'}
prefix = next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')), 's4-tree')
target = ROOT / f'docs/model-checks/refinement/{prefix}-source.json'
target.write_text(json.dumps(report, indent=2)+'\n')
print(report, flush=True)
