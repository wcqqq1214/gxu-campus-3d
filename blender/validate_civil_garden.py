"""Check exported ring paths, retained lawn and both real road seams."""
import bpy
import hashlib
import json
import math
import sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'blender'))
from site_geometry import inside, ring_distance

TARGET = next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')), ROOT)
PREFIX = next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')), 's2-civil-garden')
SITE = next(s for s in json.loads((ROOT/'public/data/sites.json').read_text())['sites'] if s['id']=='civil-forecourt-garden')


def owner(obj):
    while obj.parent: obj = obj.parent
    return obj


def sampler(objects):
    trees = []
    for obj in objects:
        if obj.type != 'MESH': continue
        obj.data.calc_loop_triangles()
        trees.append(BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],
            [tuple(t.vertices) for t in obj.data.loop_triangles], all_triangles=True))
    def height(x, y):
        hits = [t.ray_cast(Vector((x,y,200)), Vector((0,0,-1)), 400)[0] for t in trees]
        return max((h.z for h in hits if h is not None), default=None)
    return height


def check(tolerance):
    objects = list(bpy.context.scene.objects)
    paths = [o for o in objects if owner(o).get('siteId')=='civil-main-front-connection']
    assert paths, 'Missing civil garden paths'
    path = sampler(paths)
    ground = sampler(o for o in objects if owner(o).get('layer')=='terrain')
    walk = sampler(o for o in objects if owner(o).get('layer')=='roads')
    offsets = []; absent = 0
    rings = [SITE['pavingPolygon'], *SITE['pavingHoles']]
    for ix in range(-1000, -946):
        for iy in range(-1730, -1686):
            p = (ix/2+.13, iy/2+.17)
            if min(ring_distance(p,r) for r in rings)<.06: continue
            expected = inside(p,rings[0]) and not any(inside(p,r) for r in rings[1:])
            h = path(*p)
            if expected:
                g = ground(*p)
                assert h is not None and g is not None, ('Missing path or ground',p)
                offsets.append(h-g)
                assert abs(h-g-.12)<tolerance, ('Path ground offset',p,h-g)
            else:
                if any(inside(p,poly[0]) and not any(inside(p,r) for r in poly[1:]) for poly in SITE['seamPolygons']):
                    assert h is not None and abs(h-ground(*p)-.11)<tolerance+.011, ('Missing buried seam',p)
                    continue
                assert h is None, ('Path outside boundary or in lawn',p,h)
                absent += 1
    assert len(offsets)>180 and absent>500
    # Fixed independent points catch a displaced ring or changed open island.
    for p in [(-491,-856.5),(-477,-856.5),(-484,-852),(-484,-861),(-496,-856.5),(-478,-847)]:
        assert path(*p) is not None, ('Missing fixed loop/branch point',p)
    for p in [(-484,-856.5),(-488,-856.5),(-491.2,-853.2),(-488.2,-864.5)]:
        assert path(*p) is None and ground(*p) is not None, ('Lawn or trunk space filled',p)
    seams = []
    # Fixed intersections with the unchanged service-road boundary, in metres.
    for a,b in [((-498.2006936882,-857.1),(-498.1922699264,-855.9)),
                ((-478.2681673568,-845.5400977549),(-477.0549030263,-845.5792809731))]:
        dx,dy=b[0]-a[0],b[1]-a[1]; length=math.hypot(dx,dy); normal=(-dy/length,dx/length)
        for station in range(1,10):
            c=[a[k]+(b[k]-a[k])*station/10 for k in (0,1)]
            ramp=[c[k]+normal[k]*.04 for k in (0,1)]
            h=path(*ramp);g=ground(*ramp)
            assert h is not None and g is not None and abs(h-g-(.12-.02/3))<tolerance, ('Buried lip does not ramp from contact',ramp,h,g)
            heights=[]
            for step in range(-12,13):
                p=[c[k]+normal[k]*step*.01 for k in (0,1)]
                h=walk(*p)
                assert h is not None, ('Gap at road seam',p)
                heights.append(h)
            jump=max(abs(a-b) for a,b in zip(heights,heights[1:]))
            assert jump<tolerance, ('Step at road seam',c,jump)
            seams.append(jump)
    return dict(passed=True,pavedSamples=len(offsets),unpavedSamples=absent,
                fixedPavedSamples=6,fixedLawnAndTrunkSamples=4,seamProfiles=len(seams),
                seamSamples=len(seams)*25,maximumSeamStepMeters=max(seams),
                minimumGroundOffsetMeters=min(offsets),maximumGroundOffsetMeters=max(offsets),
                toleranceMeters=tolerance)


report=dict(passed=False,checkedRoot=str(TARGET),scope='Actual source and base GLB loop, open lawn, ground offset and road contacts; estimated layout, not surveyed geometry.')
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    report['source']=check(.003)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'))
    bpy.context.view_layer.update()
    report['base']=check(.018)
    report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/models/base.glb','public/data/sites.json']}
    report['passed']=True
except Exception as error:
    report['failure']=str(error)
    raise
finally:
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Civil garden geometry',report['passed'],flush=True)
