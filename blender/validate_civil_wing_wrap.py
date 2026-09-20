"""Probe the four north-wing return walls, independently of override rules."""
import bpy, sys, json, re, hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
TARGET = next((Path(a.split('=', 1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')), ROOT)
PREFIX = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--report-prefix=')), 's2-civil-wing-wrap')
ID, CHUNK, Z = 'relation/12875606', 'chunk-n2-n3', 4.06
WALLS = [
    ([-528.952650393, -806.436055854], [-528.934817691, -791.206900]),
    ([-514.429118852, -791.218032], [-514.439377478, -795.136496]),
    ([-488.577378343, -795.169892], [-488.567119715, -787.366360]),
    ([-476.708146689, -787.377492], [-476.731378534, -806.503250107]),
]


def root_name(obj):
    while obj.parent:
        obj = obj.parent
    return re.sub(r'\.\d+$', '', obj.name)


def check(objects, tolerance):
    trees = []
    for obj in objects:
        if obj.type != 'MESH':
            continue
        obj.data.calc_loop_triangles()
        tris = list(obj.data.loop_triangles)
        tree = BVHTree.FromPolygons([obj.matrix_world @ v.co for v in obj.data.vertices],
                                   [tuple(t.vertices) for t in tris], all_triangles=True)
        trees.append((tree, [obj.data.materials[t.material_index].name.split('.')[0] for t in tris]))
    samples = []
    for a, b in WALLS:
        A, B = Vector((*a, 0)), Vector((*b, 0))
        U = (B-A).normalized()
        N = Vector((-U.y, U.x, 0))
        for fraction in (.2, .5, .8):
            # Continuous wall strips below each row of generic windows.
            for h in (.4, 3.6, 7.2, 10.4):
                target = A + (B-A)*fraction + Vector((0, 0, Z+h))
                hits = []
                for tree, materials in trees:
                    point, normal, index, distance = tree.ray_cast(target+N*.6, -N, .9)
                    if point is not None:
                        hits.append((distance, point, normal, materials[index]))
                hit = min(hits, key=lambda value: value[0]) if hits else None
                assert hit and hit[3] == 'white', (a, fraction, h, hit)
                depth = (hit[1]-target).dot(N)
                assert abs(depth) < tolerance and hit[2].dot(N) > .99, (a, fraction, h, depth, hit)
                samples.append(dict(wallStart=a, fraction=fraction, height=h,
                                    material=hit[3], depth=depth, normalDot=hit[2].dot(N)))
    return dict(passed=True, rayCount=len(samples), toleranceMeters=tolerance, samples=samples)


report = dict(passed=False, scope='Four existing north-wing side/return walls recoloured white; generic side windows remain uncalibrated.')
report['fingerprints'] = {p: hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in
                          ['blender/gxu-campus.blend', 'public/models/base.glb', f'public/models/{CHUNK}.glb', 'public/data/buildings.json']}
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    report['source'] = check([o for o in bpy.context.scene.objects if o.get('featureId') == ID], .006)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'))
    bpy.context.view_layer.update()
    report['base'] = check([o for o in bpy.context.scene.objects if root_name(o) == CHUNK], .05)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/f'{CHUNK}.glb'))
    bpy.context.view_layer.update()
    report['near'] = check(list(bpy.context.scene.objects), .02)
    report['passed'] = True
except Exception as error:
    report['failure'] = str(error)
    raise
finally:
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Civil wing return walls:', report['passed'], flush=True)
