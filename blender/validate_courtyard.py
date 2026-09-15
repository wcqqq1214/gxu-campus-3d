"""Sample actual source/export paving, soil holes and unchanged terrain planes."""
import bpy, sys, json, math, hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0, str(Path(__file__).resolve().parent))
from site_geometry import inside, ring_distance

ROOT = Path(__file__).resolve().parents[1]
TARGET = next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')), ROOT)
PREFIX = next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')), 's4-courtyard')
site = next(s for s in json.loads((ROOT/'public/data/sites.json').read_text())['sites'] if s['id']=='arts-east-courtyard')


def bvh(objects):
    trees = []
    for o in objects:
        if o.type == 'MESH':
            o.data.calc_loop_triangles()
            trees.append(BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices], [tuple(p.vertices) for p in o.data.loop_triangles], all_triangles=True))
    return trees


def height(trees, x, y):
    hits = [hit[0].z for t in trees if (hit := t.ray_cast(Vector((x,y,200)),Vector((0,0,-1)),400))[0] is not None]
    return max(hits) if hits else None


def check(tolerance):
    objects = list(bpy.context.scene.objects)
    paving = bvh(o for o in objects if o.get('siteId')==site['id'])
    terrain = bvh(o for o in objects if o.get('layer')=='terrain')
    assert paving and terrain, 'Missing courtyard paving or terrain'
    rings = [site['pavingPolygon'], *site['pavingHoles']]
    samples = []; absent = []
    xmin,ymin,xmax,ymax=site['gradingBounds']
    for x in range(math.floor(xmin)-1, math.ceil(xmax)+2):
        for y in range(math.floor(ymin)-1, math.ceil(ymax)+2):
            p=(x+.31,y+.17)
            if min(ring_distance(p,r) for r in rings)<.12: continue
            expected=inside(p,rings[0]) and not any(inside(p,r) for r in rings[1:])
            h=height(paving,*p)
            if expected:
                g=height(terrain,*p)
                assert h is not None and g is not None, ('Missing paved sample',p)
                assert abs(h-g-site['surfaceOffset'])<=tolerance, ('Buried or floating paving',p,h,g)
                samples.append(h-g)
            else:
                assert h is None, ('Paving outside boundary or in a tree pit',p,h)
                absent.append(p)
    assert len(samples)>500 and len(absent)>20
    for x,y,_,_ in site['treeCandidates']:
        for dx,dy in [(0,0),(.6,0),(-.6,0),(0,.6),(0,-.6)]:
            assert height(paving,x+dx,y+dy) is None, 'Tree pit was filled by export'
            assert height(terrain,x+dx,y+dy) is not None, 'Tree pit has no ground'
    return dict(passed=True,pavedSamples=len(samples),unpavedSamples=len(absent),
                minimumOffsetMeters=min(samples),maximumOffsetMeters=max(samples),
                treePitSamples=10,toleranceMeters=tolerance)


report = dict(passed=False,siteId=site['id'],checkedRoot=str(TARGET),
              scope='Actual source/base paving and holes; metre-grid vertical samples away from edges; not real-world elevation verification.')
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    report['source']=check(.001)
    instances=[o for o in bpy.context.scene.objects if o.name.startswith('树木示意-')]
    for row in site['treeCandidates']:
        matches=[o for o in instances if math.dist(o.location[:2],row[:2])<.01]
        assert len(matches)==1 and abs(matches[0].scale.z-row[2]/9)<1e-6, ('Missing final courtyard tree',row)
    report['sourceTreesPresent']=True
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update()
    report['base']=check(.018)
    report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/models/base.glb','public/data/sites.json','public/data/vegetation.json']}
    report['passed']=True
except Exception as error:
    report['failure']=str(error)
    raise
finally:
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Courtyard actual geometry',report['passed'],flush=True)
