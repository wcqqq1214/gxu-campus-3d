"""Check actual court/stair seams, gap fill and a bounded ground access route."""
import bpy, sys, json, math, re, hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
TARGET = next((Path(a.split('=', 1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')), ROOT)
PREFIX = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--report-prefix=')), 's4-courtyard-connection')
site = next(s for s in json.loads((ROOT/'public/data/sites.json').read_text())['sites'] if s['id']=='arts-east-courtyard')
c = site['stairConnection']
building = next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']==c['buildingId'])
stair = building['form']['stairTower']


def root_name(obj):
    while obj.parent: obj = obj.parent
    return re.sub(r'\.\d+$', '', obj.name)


def meshes(objects):
    result = []
    for obj in objects:
        if obj.type != 'MESH': continue
        obj.data.calc_loop_triangles()
        result.append(BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],
                      [tuple(t.vertices) for t in obj.data.loop_triangles], all_triangles=True))
    return result


def ray(trees, p, direction, distance):
    hits = [hit for tree in trees if (hit:=tree.ray_cast(Vector(p), Vector(direction), distance))[0] is not None]
    return min(hits, key=lambda h:h[3]) if hits else None


def check(tolerance, source=False):
    objects = list(bpy.context.scene.objects)
    court = meshes(o for o in objects if o.get('siteId')==site['id'] or root_name(o)=='site-'+site['id'])
    tower = meshes(o for o in objects if (o.get('featureId')==building['id'] if source else root_name(o)==building['chunk']))
    terrain = meshes(o for o in objects if o.get('layer')=='terrain' or root_name(o)=='terrain')
    assert court and tower and terrain, 'Missing paving, stair or terrain meshes'
    floor_guess = building['elevation']+c['platformOffset']
    def floor(trees, p):
        hit = ray(trees, (*p, floor_guess+.3), (0,0,-1), 1)
        assert hit is not None, ('Missing actual gap paving', p)
        return hit[0].z
    seam_differences = []; clearances = []; sample_count = 0
    normal = c['normal']; section0 = None
    for i in range(23):
        station = -c['width']/2+.1+i*.1
        a, b = next((a,b) for a,b in zip(c['sections'],c['sections'][1:]) if a['station']-1e-8<=station<=b['station']+1e-8)
        t = (station-a['station'])/(b['station']-a['station'])
        start, end = [[x+(y-x)*t for x,y in zip(a[key],b[key])] for key in ['start','end']]
        if i==11: section0 = (start,end)
        for edge, left, right in [(start,court,court), (end,court,tower)]:
            p = [edge[j]-normal[j]*.035 for j in (0,1)]
            q = [edge[j]+normal[j]*.035 for j in (0,1)]
            difference = abs(floor(left,p)-floor(right,q))
            assert difference<tolerance, ('Discontinuous actual seam',station,edge,difference)
            seam_differences.append(difference)
        for k in range(1,20):
            p = [start[j]+(end[j]-start[j])*k/20 for j in (0,1)]
            h = floor(court,p); g = floor(terrain,p)
            assert h-g>.025, ('Buried connection',p,h,g)
            clearances.append(h-g); sample_count+=1
    # A 0.6 m wide sampled route enters west of the supports, turns through
    # the north ground landing and stops before the first up-flight tread.
    # This tests model access only, not real-world accessibility compliance.
    cs, sn = math.cos(stair['angle']), math.sin(stair['angle'])
    def world(p): return [stair['origin'][0]+p[0]*cs-p[1]*sn,stair['origin'][1]+p[0]*sn+p[1]*cs]
    path = [[section0[1][j]+normal[j]*.4 for j in (0,1)], *[world(p) for p in [(-4.4,.5),(-3.7,3.6),(1.4,3.6),(1.4,2.55)]]]
    headroom = []; route_samples = 0
    for a, b in zip(path,path[1:]):
        length=math.dist(a,b); side=[-(b[1]-a[1])/length,(b[0]-a[0])/length]
        for i in range(math.ceil(length/.15)+1):
            t=i/math.ceil(length/.15)
            for offset in [-.3,0,.3]:
                p=[a[j]+(b[j]-a[j])*t+side[j]*offset for j in (0,1)]
                h=floor(tower,p)
                assert abs(h-floor_guess)<tolerance, ('Ground access steps or obstacle',p,h)
                hit=ray(tower,(*p,h+.04),(0,0,1),3.5)
                if hit:
                    clearance=hit[3]+.04
                    assert clearance>=2.1, ('Blocked ground access headroom',p,clearance)
                    headroom.append(clearance)
                route_samples+=1
    return dict(passed=True, gapSurfaceSamples=sample_count, seamPairs=len(seam_differences),
                maximumSeamDifferenceMeters=max(seam_differences), minimumTerrainClearanceMeters=min(clearances),
                routeSamples=route_samples, sampledRouteWidthMeters=.6,
                minimumMeasuredHeadroomMeters=min(headroom), toleranceMeters=tolerance)


report = dict(passed=False, checkedRoot=str(TARGET),
              scope='Actual source/base/near-combined geometry: two seams, gap surface and 0.6 m sampled ground route to first flight; estimated dimensions, not surveyed access certification.')
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    report['source']=check(.008,source=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update()
    report['base']=check(.04)
    for obj in list(bpy.context.scene.objects):
        if root_name(obj)==building['chunk']: bpy.data.objects.remove(obj,do_unlink=True)
    bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/f"{building['chunk']}.glb"));bpy.context.view_layer.update()
    report['nearCombined']=check(.025)
    report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in [
        'blender/gxu-campus.blend','public/data/sites.json','public/data/models.json','public/models/base.glb',f"public/models/{building['chunk']}.glb"]}
    report['passed']=True
except Exception as error:
    report['failure']=str(error)
    raise
finally:
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Courtyard stair actual connection:',report['passed'],flush=True)
