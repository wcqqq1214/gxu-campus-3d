"""Check the civil southwest low wing against fixed map-space sample points.

This checks the adopted estimated massing, not the real building's measured
height. It must reject the old uniform eight-storey extrusion.
"""
import bpy, sys, json, re, hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
TARGET = next((Path(a.split('=', 1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')), ROOT)
PREFIX = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--report-prefix=')), 's2-civil-annex')
ID, CHUNK, Z = 'relation/12875606', 'chunk-n2-n3', 4.06
LOW = [(-545, y, 10.8) for y in (-839, -843, -848, -856, -860)]
LOW += [(x, y, 10.8) for x in (-541, -535, -529, -523, -516) for y in (-851, -856, -861)]
HIGH = [(x, -830, 26.4) for x in (-545, -540, -535, -522, -509, -500)]
HIGH += [(x, -800, 26.4) for x in (-525, -520, -510, -500, -490)]
HIGH += [(-480, y, 26.4) for y in (-795, -805, -815, -825)]
SEAM = [(x, y, h) for x in (-546, -542) for y, h in [(-835.6, 10.8), (-834.0, 26.4)]]
VOIDS = [(-530, -840), (-520, -840), (-500, -815), (-505, -820), (-490, -810)]


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
        trees.append(BVHTree.FromPolygons(
            [obj.matrix_world @ v.co for v in obj.data.vertices],
            [tuple(t.vertices) for t in obj.data.loop_triangles], all_triangles=True))

    def ray(origin, direction, distance):
        hits = [tree.ray_cast(Vector(origin), Vector(direction), distance) for tree in trees]
        return min((h for h in hits if h[0] is not None), key=lambda h: h[3], default=None)

    samples = []
    for x, y, expected in LOW + HIGH + SEAM:
        hit = ray((x, y, Z + 35), (0, 0, -1), 35)
        assert hit, ('missing roof', x, y)
        actual = hit[0].z - Z
        assert abs(actual - expected) < tolerance, ('wrong roof height', x, y, actual, expected)
        assert hit[1].z > .98, ('reversed roof normal', x, y, list(hit[1]))
        samples.append(dict(x=x, y=y, expectedHeight=expected, actualHeight=actual))
    for x, y in VOIDS:
        assert ray((x, y, Z + 35), (0, 0, -1), 34.8) is None, ('filled original void', x, y)
    walls = []
    for x in (-546, -542):
        for height in (12, 19, 24):
            hit = ray((x, -838, Z + height), (0, 1, 0), 5)
            assert hit and abs(hit[0].y + 834.82) < .04 + tolerance, ('missing exposed main wall', x, height, hit)
            assert hit[1].y < -.98, ('reversed seam wall', x, height, list(hit[1]))
            walls.append(dict(x=x, height=height, actualY=hit[0].y))
    # Probe the solid storey joint, outside generic window quads/frames, so
    # the base and near representations measure the same structural wall.
    normals = []
    probes = [((-475, -815), (-1, 0), 3), ((-482, -786), (0, -1), 3),
              ((-535, -816), (1, 0), 5), ((-512, -836), (0, 1), 3)]
    probes += [((-500, -815), direction, 16) for direction in [(1, 0), (-1, 0), (0, 1), (0, -1)]]
    for (x, y), (dx, dy), distance in probes:
        hit = ray((x, y, Z + 16.5), (dx, dy, 0), distance)
        assert hit and hit[1].x * dx + hit[1].y * dy < -.98, ('wrong outer/courtyard normal', x, y, dx, dy, hit)
        normals.append(dict(origin=[x, y, Z + 16.5], direction=[dx, dy, 0], normal=list(hit[1])))
    return dict(passed=True, roofSamples=samples, openVoidSamples=VOIDS, exposedWallSamples=walls,
                normalSamples=normals, rayCount=len(samples) + len(VOIDS) + len(walls) + len(normals), toleranceMeters=tolerance)


report = dict(passed=False, scope='Estimated 10.8 m southwest C wing, retained 26.4 m main/rear roof, shared boundary, original courtyard and forecourt voids; detailed roof tiers remain pending.')
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET / 'blender/gxu-campus.blend'))
    report['source'] = check([o for o in bpy.context.scene.objects if o.get('featureId') == ID], .006)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(TARGET / 'public/models/base.glb'))
    bpy.context.view_layer.update()
    report['base'] = check([o for o in bpy.context.scene.objects if root_name(o) == CHUNK], .05)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(TARGET / 'public/models' / f'{CHUNK}.glb'))
    bpy.context.view_layer.update()
    report['near'] = check(list(bpy.context.scene.objects), .02)
    report['fingerprints'] = {p: hashlib.sha256((TARGET / p).read_bytes()).hexdigest() for p in
                              ['blender/gxu-campus.blend', 'public/models/base.glb', f'public/models/{CHUNK}.glb', 'public/data/buildings.json']}
    report['passed'] = True
except Exception as error:
    report['failure'] = str(error)
    raise
finally:
    (ROOT / 'docs/model-checks/refinement' / f'{PREFIX}-geometry.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('Civil annex:', report['passed'], flush=True)
