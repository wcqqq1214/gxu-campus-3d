"""Probe the built southeast civil-school portal using fixed map coordinates."""
import bpy,json,sys,math,re,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-civil-entry')
PORTAL_ONLY='--portal-only' in sys.argv
ID='relation/12875606';CHUNK='chunk-n2-n3';Z=4.06
A=Vector((-476.769698452549,-838.0503560000666,0));B=Vector((-493.45022625596147,-838.0280919998064,0))
U=(B-A).normalized();N=Vector((-U.y,U.x,0));CENTER=(A+B)/2

def root_name(o):
    while o.parent:o=o.parent
    return re.sub(r'\.\d+$','',o.name)

def check(objects,tolerance):
    group=[]
    for o in objects:
        if o.type!='MESH':continue
        o.data.calc_loop_triangles();ts=list(o.data.loop_triangles)
        group.append((BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(t.vertices) for t in ts],all_triangles=True),[o.data.materials[t.material_index].name.split('.')[0] for t in ts]))
    def ray(p,d,limit):
        hits=[]
        for tree,mats in group:
            hit,normal,index,distance=tree.ray_cast(p,d,limit)
            if hit is not None:hits.append((distance,hit,mats[index]))
        return min(hits,key=lambda h:h[0]) if hits else None
    records=[]
    def point(u,v,h):return CENTER+U*u+N*v+Vector((0,0,Z+h))
    def face(u,h,material):
        hit=ray(point(u,1,h),-N,1.3)
        assert hit and hit[2]==material,(u,h,material,hit)
        assert -.02-tolerance<=1-hit[0]<=.4+tolerance,('unexpected face depth',hit)
        records.append({'kind':'facade','u':u,'height':h,'material':material,'depth':1-hit[0]})
    for u in (-5.5,-3.6,-1,1,3.6,5.5):
        for h in (1.5,5.0):face(u,h,'glass')
    for u in (-6.575,-2.3,2.3,6.575):
        for h in (1.5,5.0):face(u,h,'stone')
    if not PORTAL_ONLY:
        for i in range(6):
            u=((.09+(i+.5)*.82/6)-.5)*(B-A).length
            for j in range(12):face(u,7.8+(j+.5)*18.2/12,'glass')
        for u in (-7.6,7.6):face(u,15,'stone')
    for u in (-7.5,-5,-2.5,0,2.5,5,7.5):
        for v in (.4,1,1.7):
            for start,direction,expected in [(8.8,-1,7.8),(6.2,1,7.2)]:
                hit=ray(point(u,v,start),Vector((0,0,direction)),2)
                assert hit and hit[2]=='stone' and abs(hit[1].z-Z-expected)<tolerance,(u,v,expected,hit)
                records.append({'kind':'canopy','u':u,'depth':v,'height':expected,'actualHeight':hit[1].z-Z})
    for u in (-7,0,7):
        assert ray(point(u,2.3,8.8),Vector((0,0,-1)),2) is None,'Canopy protrudes beyond configured front'
        assert ray(point(u,1,.9),Vector((0,0,-1)),.95) is None,'Invented stairs below flush entrance'
        records.append({'kind':'clearance','u':u})
    old=Vector((-476.73892257063244+.8,-812.7139240000054,Z+3.5))
    assert ray(old,Vector((0,0,-1)),3.7) is None,'Obsolete east entrance canopy/platform remains'
    return {'passed':True,'rayCount':len(records)+4,'samples':records,'removedEastEntrance':True,'toleranceMeters':tolerance}
report={'passed':False,'scope':'South edge 17 glazed two-storey portal, optional canopy, upper glazing and obsolete east entry removal; other facades and roof heights not accepted.'}
if PORTAL_ONLY:
    report['scope']='Retained two-storey portal, canopy and obsolete east entry removal; upper curtain wall is checked separately after its corner extension.'
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    report['source']=check([o for o in bpy.context.scene.objects if o.get('featureId')==ID],.006)
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update()
    report['base']=check([o for o in bpy.context.scene.objects if root_name(o)==CHUNK],.05)
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/f'{CHUNK}.glb'));bpy.context.view_layer.update()
    report['near']=check(list(bpy.context.scene.objects),.02)
    report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/models/base.glb',f'public/models/{CHUNK}.glb','public/data/buildings.json']}
    report['passed']=True
except Exception as error:report['failure']=str(error);raise
finally:
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Civil entry:',report['passed'],flush=True)
