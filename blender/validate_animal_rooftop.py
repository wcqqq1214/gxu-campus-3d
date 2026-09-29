"""Fixed-coordinate probes for the animal college rooftop body and overhanging cap."""
import bpy,json,sys,math,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s3-animal-rooftop')
b=next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']=='relation/11564704')
# Fixed expected world coordinates, separate from the generated volume record.
CENTER=(297.94840461904437,-242.54551397458997);ANGLE=.19779770521036946
CHUNK='chunk-p0-n1'
U=Vector((math.cos(ANGLE),math.sin(ANGLE),0));V=Vector((-math.sin(ANGLE),math.cos(ANGLE),0))
Z=3.9  # Retained building ground datum, independently frozen for this batch.
if 'elevation' in b:assert abs(b['elevation']-Z)<1e-6
def point(u,v,z):return Vector((*CENTER,Z+z))+U*u+V*v
def root_name(o):
    while o.parent:o=o.parent
    return o.name

def check(objects,tolerance):
    trees=[BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons]) for o in objects if o.type=='MESH']
    def hit(origin,direction,length):
        hits=[t.ray_cast(origin,direction,length) for t in trees];hits=[h for h in hits if h[0] is not None]
        return min(hits,key=lambda h:h[3]) if hits else None
    result=[]
    def expect(name,p,d,distance,normal):
        r=hit(p,d,distance+.3)
        assert r and abs(r[3]-distance)<tolerance,(name,'distance',r[3] if r else None,distance)
        assert r[1].dot(normal)>.98,(name,'normal',list(r[1]))
        result.append(dict(name=name,distanceErrorMeters=abs(r[3]-distance)))
    for u in [-4.4,0,4.4]:
        for v in [-2.95,0,2.95]:expect('cap-top',point(u,v,28),Vector((0,0,-1)),1.75,Vector((0,0,1)))
    # On the overhang, the cap underside is above open air rather than a widened body.
    for tangent,extent in [(U,4.2),(V,2.75)]:
        for sign in [-1,1]:
            n=tangent*sign;p=point(0,0,25.2)+n*(extent+.175)
            expect('cap-underside',p,Vector((0,0,1)),.5,Vector((0,0,-1)))
            expect('body-side',point(0,0,24.4)+n*(extent+1),-n,1,n)
            expect('cap-side',point(0,0,25.95)+n*(extent+1),-n,.65,n)
            expect('support-roof',point(0,0,24)+n*(extent+.175),Vector((0,0,-1)),.9,Vector((0,0,1)))
    # Cap coverage must end at the stated overhang, preserving an open roof strip.
    for sign in [-1,1]:expect('outside-cap',point(sign*4.9,0,28),Vector((0,0,-1)),4.9,Vector((0,0,1)))
    # Existing high and lower roofs away from the addition.
    for name,x,y,h in [('front-core',300,-251,23.1),('west-wing',240,-280,16.5),('east-wing',337,-237,16.5)]:
        expect(name,Vector((x,y,Z+h+2)),Vector((0,0,-1)),2,Vector((0,0,1)))
    return dict(passed=True,rayCount=len(result),checks=result)

report=dict(buildingId=b['id'],checkedRoot=str(TARGET),passed=False,scope='Actual source/base/near rooftop surfaces and finite surrounding samples; dimensions estimated, no whole-building acceptance.')
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    objects=[o for o in bpy.context.scene.objects if o.get('featureId')==b['id']];assert len(objects)==1
    report['source']=check(objects,.011)
    for tier,file in [('base','base.glb'),('near',CHUNK+'.glb')]:
        bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/file));bpy.context.view_layer.update()
        objects=[o for o in bpy.context.scene.objects if tier=='near' or root_name(o)==CHUNK]
        report[tier]=check(objects,.05 if tier=='base' else .02)
    report['passed']=True
except Exception as error:
    report['failure']=repr(error);raise
finally:
    report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/models/base.glb','public/models/'+CHUNK+'.glb','public/data/models.json']}
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k in ['passed','failure']}),flush=True)
