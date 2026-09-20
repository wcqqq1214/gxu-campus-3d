"""Probe the central eave in actual source/base/near triangles, including a negative control."""
import bpy
import hashlib
import json
import sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
TARGET = next((Path(a.split('=', 1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')), ROOT)
PREFIX = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--report-prefix=')), 's3-agriculture-eave')
# Fixed mapped wall endpoints and photo-constrained acceptance dimensions;
# deliberately do not derive the expected profile from roofEave parameters.
A = Vector((313.7703710999319, -339.9712799998642, 5.58))
B = Vector((296.4025152736104, -343.8897439997791, 5.58))
T = (B-A).normalized()
N = Vector((.22008398363616913, -.975480927618185, 0))
LENGTH = (B-A).length
UP = Vector((0, 0, 1))


def root_name(obj):
    while obj.parent:
        obj = obj.parent
    return obj.name


def check(objects, tolerance):
    trees = []
    for obj in objects:
        if obj.type != 'MESH':
            continue
        obj.data.calc_loop_triangles()
        tris = obj.data.loop_triangles
        trees.append((BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],
                      [tuple(t.vertices) for t in tris], all_triangles=True),
                      [obj.data.materials[t.material_index].name.split('.')[0] for t in tris]))
    samples = []

    def probe(kind, u, v, z, direction, distance, material='white', maximum=3):
        origin = A+T*u+N*v+UP*z
        hits = []
        for tree, mats in trees:
            hit = tree.ray_cast(origin, direction, maximum)
            if hit[0] is not None:
                hits.append((hit[3], mats[hit[2]]))
        first = min(hits, default=None)
        if distance is None:
            assert first is None, (kind, u, v, z, first)
        else:
            assert first and abs(first[0]-distance) <= tolerance and first[1] == material, (kind, u, v, z, first, distance)
        samples.append(dict(kind=kind, alongMeters=u, outwardMeters=v, height=z,
                            expectedDistance=distance, actual=first))

    for fraction in (.1, .3, .5, .7, .9):
        u = LENGTH*fraction
        for v in (.2, .8, 1.4):
            probe('upper-cap', u, v, 19.3, -UP, 1)
            probe('sloping-underside', u, v, 16.55, UP, v-.05)
        for rise in (.4, .8, 1.2):
            probe('front-profile', u, 2, 16.5+rise, -N, 2-rise)
        probe('cap-front-edge', u, 2, 18.2, -N, .4)
        probe('roof-behind-retained', u, -1, 17, -UP, .5, 'paleRoof')
        probe('clear-beyond-projection', u, 1.8, 19.3, -UP, None, maximum=2.5)
    for u in (-.65, LENGTH+.65):
        probe('widened-cap-end', u, .8, 19.3, -UP, 1)
    for u in (-1, LENGTH+1):
        probe('clear-beyond-end', u, .8, 19.3, -UP, None, maximum=1.5)
    return dict(passed=True, sampleCount=len(samples), toleranceMeters=tolerance, samples=samples)


report = dict(passed=False, buildingId='way/759185166', checkedRoot=str(TARGET),
              method='BVH over actual loop triangles; fixed mapped endpoints and independent profile probes',
              dimensionStatus='Photo-constrained estimates, not measured dimensions or structural reconstruction')
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    report['source'] = check([o for o in bpy.context.scene.objects if o.get('featureId') == 'way/759185166'], .012)
    for label, filename, tolerance in [('base', 'base.glb', .035), ('near', 'chunk-p0-n1.glb', .02)]:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/filename))
        bpy.context.view_layer.update()
        report[label] = check([o for o in bpy.context.scene.objects if label != 'base' or root_name(o) == 'chunk-p0-n1'], tolerance)
    report['passed'] = True
except Exception as error:
    report['failure'] = str(error)
finally:
    report['fingerprints'] = {p: hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in
                              ['blender/gxu-campus.blend', 'public/data/models.json',
                               'public/models/base.glb', 'public/models/chunk-p0-n1.glb']}
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print('Agriculture eave:', report['passed'], report.get('failure', ''), flush=True)
if not report['passed']:
    raise RuntimeError(report['failure'])
