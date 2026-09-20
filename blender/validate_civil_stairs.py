"""Fixed geometry and ground probes for the adopted civil annex stair terrace."""
import bpy,sys,json,re,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-civil-stairs')
ID,CHUNK,Z='relation/12875606','chunk-n2-n3',4.06
A=Vector((-512.5723073303868,-846.9559559997294,0));B=Vector((-512.5928245849979,-863.6539559998882,0))
O=(A+B)/2;U=(B-A).normalized();N=Vector((-U.y,U.x,0))

def root_name(o):
    while o.parent:o=o.parent
    return re.sub(r'\.\d+$','',o.name)

def trees(objects):
    result=[]
    for o in objects:
        if o.type!='MESH':continue
        o.data.calc_loop_triangles();tris=list(o.data.loop_triangles)
        result.append((BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(t.vertices) for t in tris],all_triangles=True),[o.data.materials[t.material_index].name.split('.')[0] for t in tris]))
    return result

def ray(group,origin,direction,limit):
    hits=[]
    for tree,mats in group:
        loc,normal,index,distance=tree.ray_cast(origin,direction,limit)
        if loc is not None:hits.append((distance,loc,normal,mats[index]))
    return min(hits,key=lambda h:h[0]) if hits else None

def point(u,v,h):return O+U*u+N*v+Vector((0,0,Z+h))

def check(objects,tolerance):
    group=trees(objects);samples=[]
    def top(u,v,h,kind):
        hit=ray(group,point(u,v,h+.3),Vector((0,0,-1)),h+.65)
        assert hit and hit[3]=='stone' and abs(hit[1].z-Z-h)<tolerance,(kind,u,v,h,hit)
        assert hit[2].z>.98,('top normal',kind,u,v,hit)
        samples.append(dict(kind=kind,u=u,v=v,height=h,actualHeight=hit[1].z-Z))
    for i in range(9):
        v=3.28 if i==0 else 4.08+(i-.5)*.32
        for u in (-5.5,0,5.5):top(u,v,1.62-i*.18,'lower-tread-or-platform')
    for i in range(5):
        v=.6 if i==0 else 1.2+(i-.5)*.32
        for u in (-5.2,-3.2,-1.2):top(u,v,2.52-i*.18,'upper-tread-or-landing')
    # Remaining terrace beside the offset upper flight must stay flat and open.
    for u in (0,2.5,5.5):
        for v in (.5,1.8,3.0):top(u,v,1.62,'side-terrace')
    for count,start,height,us,label in [(9,4.08,1.62,(-5.5,0,5.5),'lower-riser'),(5,1.2,2.52,(-5.2,-3.2,-1.2),'upper-riser')]:
        for i in range(count):
            v=start+i*.32;h=height-i*.18-.09
            for u in us:
                hit=ray(group,point(u,v+.12,h),-N,.3)
                assert hit and hit[3]=='stone' and abs((hit[1]-O).dot(N)-v)<tolerance,(label,u,v,h,hit)
                assert hit[2].dot(N)>.98,('riser normal',label,u,v,h,hit)
                samples.append(dict(kind=label,u=u,v=v,height=h))
    for side in (-1,1):
        hit=ray(group,point(side*6.3,3.1,.8),-U*side,.5)
        assert hit and hit[3]=='stone' and abs((hit[1]-O).dot(U)-side*6)<tolerance,('terrace width',side,hit)
        assert hit[2].dot(U*side)>.98,('terrace side normal',side,hit)
        samples.append(dict(kind='terrace-side',side=side))
    for u,v in [(-6.3,5),(6.3,5),(0,6.94)]:
        assert ray(group,point(u,v,3),Vector((0,0,-1)),3.2) is None,('stair leaves envelope',u,v)
        samples.append(dict(kind='outside-clear',u=u,v=v))
    # Default low windows whose rectangles cross the solid platform must
    # disappear completely, rather than leave glazing/frame fragments above it.
    for u in (-6.261754,.0+2.087251,6.261754):
        hit=ray(group,point(u,.5,2.2),-N,.7)
        assert hit and hit[3]=='stone' and abs((hit[1]-O).dot(N))<tolerance,('window fragment beside terrace',u,hit)
        samples.append(dict(kind='retained-wall-without-window-fragment',u=u,height=2.2))
    return dict(passed=True,rayCount=len(samples),samples=samples,toleranceMeters=tolerance)

def ground_check(objects,tolerance):
    group=trees(objects);samples=[]
    for u in (-5.5,0,5.5):
        for v in (1,3.5,6.48,6.76):
            hit=ray(group,point(u,v,5),Vector((0,0,-1)),7)
            assert hit,('missing ground',u,v)
            ground=hit[1].z-Z
            assert -.25-tolerance<=ground<=.18+tolerance,('foundation/ground mismatch',u,v,ground)
            if v>=6.48:
                assert .02-tolerance<=.18-ground<=.25+tolerance,('first step to ground',u,v,ground)
            samples.append(dict(u=u,v=v,groundHeightRelativeToBuilding=ground,material=hit[3],firstStepRise=.18-ground if v>=6.48 else None))
    return dict(passed=True,samples=samples,scope='Existing terrain and generic road surfaces beneath/at the stair toe; does not prove a full paved connection to the campus road.')

report=dict(passed=False,scope='Estimated two-flight annex stairs: 12 m lower, 4.8 m upper offset north, 1.62/2.52 m platforms, 9/5 risers. Original roof, footprint and main entrance retained; complete road connection remains pending.')
report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/models/base.glb',f'public/models/{CHUNK}.glb','public/data/buildings.json']}
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    report['source']=check([o for o in bpy.context.scene.objects if o.get('featureId')==ID],.006)
    report['sourceGround']=ground_check([o for o in bpy.context.scene.objects if root_name(o) in ('terrain','roads')],.015)
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update()
    report['base']=check([o for o in bpy.context.scene.objects if root_name(o)==CHUNK],.05)
    report['baseGround']=ground_check([o for o in bpy.context.scene.objects if root_name(o) in ('terrain','roads')],.05)
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/f'{CHUNK}.glb'));bpy.context.view_layer.update()
    report['near']=check(list(bpy.context.scene.objects),.02)
    report['passed']=True
except Exception as error:report['failure']=str(error);raise
finally:
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('Civil annex stairs:',report['passed'],flush=True)
