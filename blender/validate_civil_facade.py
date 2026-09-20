"""Check the adopted south-window layout in the source and shipped GLBs.

Independent fixed facade coordinates and sample heights check the estimated
layout. They do not establish surveyed dimensions or verify the pending deep
upper recesses and the western facade above the annex.
"""
import bpy, json, sys, re, hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
TARGET = next((Path(a.split('=', 1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')), ROOT)
PREFIX = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--report-prefix=')), 's2-civil-facade')
ID, CHUNK, Z = 'relation/12875606', 'chunk-n2-n3', 4.06
RETAINED_ONLY = '--retained-only' in sys.argv
A = Vector((-493.43996762938485, -834.8777359997714, 0))
B = Vector((-537.9008578510263, -834.8220759999119, 0))
U = (B-A).normalized()
N = Vector((-U.y, U.x, 0))
LENGTH = (B-A).length


def root_name(obj):
    while obj.parent:
        obj = obj.parent
    return re.sub(r'\.\d+$', '', obj.name)


def check(objects, tolerance):
    meshes = []
    for obj in objects:
        if obj.type != 'MESH':
            continue
        obj.data.calc_loop_triangles()
        triangles = list(obj.data.loop_triangles)
        meshes.append((BVHTree.FromPolygons(
            [obj.matrix_world @ v.co for v in obj.data.vertices],
            [tuple(t.vertices) for t in triangles], all_triangles=True),
            [obj.data.materials[t.material_index].name.split('.')[0] for t in triangles]))

    def point(fraction, depth, height):
        return A + U*(fraction*LENGTH) + N*depth + Vector((0, 0, Z+height))

    def ray(origin, direction, limit):
        hits = []
        for tree, materials in meshes:
            location, normal, index, distance = tree.ray_cast(origin, direction, limit)
            if location is not None:
                hits.append((distance, location, normal, materials[index]))
        return min(hits, key=lambda h: h[0]) if hits else None

    samples = []
    def wall(fraction, height, material):
        hit = ray(point(fraction, 1, height), -N, 1.1)
        assert hit and hit[3] == material, ('facade material', fraction, height, material, hit)
        depth = 1-hit[0]
        assert -.01-tolerance <= depth <= .28+tolerance, ('facade depth', depth)
        if material == 'stone':
            assert abs(depth) < tolerance and hit[2].dot(N) > .98, ('solid wall missing/reversed', hit)
        samples.append(dict(kind='wall', fraction=fraction, height=height, material=material, depth=depth))

    # Broad middle rows must stop below the different two-storey top layout.
    for level in range(1, 6):
        height = level*3.3+1.848
        for bay in range(13):
            wall(.025+(bay+.5)*.95/13+.12/LENGTH, height, 'glass')
        for gap in range(12):
            wall(.025+(gap+1)*.95/13, height, 'stone')
        for fraction in (.12, .36, .62, .88):
            for start, direction, expected in [(level*3.3+3.8, -1, level*3.3+3.198),
                                                (level*3.3+2.8, 1, level*3.3+2.958)]:
                hit = ray(point(fraction, .42, start), Vector((0, 0, direction)), 1)
                assert hit and hit[3] == 'white' and abs(hit[1].z-Z-expected) < tolerance, ('ledge missing/height', level, fraction, expected, hit)
                assert hit[2].z*direction < -.98, ('ledge normal', level, hit)
                samples.append(dict(kind='ledge', level=level, fraction=fraction, expectedHeight=expected, actualHeight=hit[1].z-Z))
            hit = ray(point(fraction, .68, level*3.3+3.8), Vector((0, 0, -1)), 1)
            assert hit is None, ('ledge extends beyond adopted depth', level, fraction, hit)
            samples.append(dict(kind='ledgeOuterClearance', level=level, fraction=fraction))
    for level in ((6,) if RETAINED_ONLY else (6, 7)):
        for bay in range(13):
            center = .025+(bay+.5)*.95/13
            wall(center+.3/LENGTH, level*3.3+1.15, 'glass')
            # This side of the wider middle window must be wall at the top.
            wall(center+.35*.95/13, level*3.3+1.15, 'stone')
        for fraction in (.12, .36, .62, .88):
            hit = ray(point(fraction, .42, level*3.3+3.8), Vector((0, 0, -1)), 1)
            assert hit is None, ('middle ledge duplicated on upper floor', level, fraction, hit)
            samples.append(dict(kind='upperLedgeAbsent', level=level, fraction=fraction))
    # Check backing masonry independently of glass.
    for level in ((1, 3, 5, 6) if RETAINED_ONLY else (1, 3, 5, 6, 7)):
        origin = point(.5, -.4, level*3.3+1.15)
        # Near frames straddle the wall plane: their back face can be the
        # first hit from indoors. Cross that face, then require the masonry
        # itself at the original wall plane, not merely any downstream hit.
        hit = ray(origin, N, .6)
        if hit and hit[3] == 'white' and (hit[1]-A).dot(N) < -.015:
            hit = ray(hit[1]+N*.01, N, .2)
        assert hit and hit[3] == 'stone' and abs((hit[1]-A).dot(N)) < tolerance, ('backing wall absent', level, hit)
        samples.append(dict(kind='backingWall', level=level))
    return dict(passed=True, rayCount=len(samples), samples=samples, toleranceMeters=tolerance)


report = dict(passed=False, scope='Original south edge 1: five middle window/ledge rows, 13 estimated bays, two upper rows of narrower panes. Deep upper recesses, western extension above annex, ground and side/rear facades remain pending.')
if RETAINED_ONLY:
    report['scope'] = 'Retained south edge 1 middle rows and seventh-storey panes only; changed eighth-storey recess is checked separately by validate_civil_recess.py.'
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
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print('Civil facade:', report['passed'], flush=True)
