"""Photo-mapped east terminal return: upper blank wall, retained ground window.

Coordinates and five floor centers are frozen independently of facade rules.
Run against the preceding asset root as a negative control.
"""
import bpy
import hashlib
import json
import re
import sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
TARGET = next((Path(a.split('=', 1)[1]).resolve() for a in sys.argv
               if a.startswith('--check-root=')), ROOT)
PREFIX = next((a.split('=', 1)[1] for a in sys.argv
               if a.startswith('--report-prefix=')), 's3-animal-return')
ID, CHUNK = 'relation/11564704', 'chunk-p0-n1'
A = Vector((330.2559849867264, -247.78718799990145, 0))
B = Vector((329.3634844220806, -243.3677840000648, 0))
U = (B-A).normalized()
N = Vector((-.9802112911185934, -.19795409761765528, 0))


def root_name(obj):
    while obj.parent:
        obj = obj.parent
    return re.sub(r'\.\d+$', '', obj.name)


def check(objects, tolerance, detail):
    trees = []
    for obj in objects:
        if obj.type != 'MESH':
            continue
        # Existing extruded walls are inward wound and rendered double sided.
        # This window-removal batch preserves that convention and checks it
        # explicitly; it does not claim to repair legacy wall winding.
        for material in obj.data.materials:
            if material.name.split('.')[0] == 'stone':
                assert not material.use_backface_culling
        obj.data.calc_loop_triangles()
        triangles = list(obj.data.loop_triangles)
        trees.append((BVHTree.FromPolygons(
            [obj.matrix_world @ v.co for v in obj.data.vertices],
            [tuple(t.vertices) for t in triangles], all_triangles=True),
            [obj.data.materials[t.material_index].name.split('.')[0] for t in triangles]))
    samples = []
    for level, height in enumerate([5.748, 9.048, 12.348, 15.648, 18.948]):
        for along in [-.65, -.35, .35, .65]:
            for vertical in [-.45, .45]:
                origin = (A+B)/2 + U*along + N*.8 + Vector((0, 0, height+vertical))
                hits = []
                for tree, materials in trees:
                    point, normal, index, distance = tree.ray_cast(origin, -N, 1)
                    if point is not None:
                        hits.append((distance, point, normal, materials[index]))
                hit = min(hits, key=lambda h: h[0]) if hits else None
                expected = {'glass', 'shadeGlass'} if level == 0 else {'stone'}
                assert hit and hit[3] in expected, (level, along, vertical, hit)
                depth = (hit[1]-A).dot(N)
                expected_depth = (.25 if detail else .07) if level == 0 else 0
                assert abs(depth-expected_depth) < tolerance, (level, depth)
                # Generic legacy base panes are checked for coverage, not winding.
                if level > 0:
                    assert hit[2].dot(N) < -.99, (level, 'retained wall normal', list(hit[2]))
                samples.append(dict(level=level, along=along, vertical=vertical,
                                    material=hit[3], depth=depth, normalDot=hit[2].dot(N)))
    return dict(passed=True, rayCount=len(samples), toleranceMeters=tolerance, samples=samples)


report = dict(passed=False, buildingId=ID, scope='East terminal short west return only; upper four floors blank, obscured ground window remains estimated. No rear-wing or whole-building acceptance.')
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    objects = [o for o in bpy.context.scene.objects if o.get('featureId') == ID]
    assert len(objects) == 1
    report['source'] = check(objects, .006, True)
    for tier, filename in [('base', 'base.glb'), ('near', CHUNK+'.glb')]:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/filename))
        bpy.context.view_layer.update()
        objects = [o for o in bpy.context.scene.objects if tier == 'near' or root_name(o) == CHUNK]
        report[tier] = check(objects, .05 if tier == 'base' else .02, tier == 'near')
    report['passed'] = True
except Exception as error:
    report['failure'] = repr(error)
    raise
finally:
    report['fingerprints'] = {name: hashlib.sha256((TARGET/name).read_bytes()).hexdigest()
                              for name in ['blender/gxu-campus.blend', 'public/models/base.glb',
                                           'public/models/'+CHUNK+'.glb', 'public/data/models.json']}
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Animal return:', report['passed'], flush=True)
