"""Fixed adopted personnel-door, stair and ground probes; no surveyed dimensions."""
import bpy,json,sys,re,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-platform-door-entry')
Z=-4.76;ID='way/957404988';CHUNK='chunk-n2-n3'
FRONT=Vector((-695.20838278471,-742.4153550071646,Z))
U=Vector((.0063417743114130036,-.9999798907471006,0));N=Vector((-U.y,U.x,0))
def root_name(o):
    while o.parent:o=o.parent
    return re.sub(r'\.\d+$','',o.name)
def meshes(objects):
    result=[]
    for o in objects:
        if o.type!='MESH':continue
        o.data.calc_loop_triangles();ts=list(o.data.loop_triangles)
        result.append((BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(t.vertices) for t in ts],all_triangles=True),[o.data.materials[t.material_index].name.split('.')[0] for t in ts]))
    return result
def ray(group,p,d,limit):
    hits=[]
    for tree,mats in group:
        q,n,i,length=tree.ray_cast(p,Vector(d),limit)
        if q is not None:hits.append((length,q,n,mats[i]))
    return min(hits,key=lambda h:h[0]) if hits else None
def point(u,v,h):return FRONT+U*u+N*v+Vector((0,0,h))
def check(objects,ground,tol):
    group=meshes(objects);records=[]
    # Cover the full adopted 3.6 m door width, including the side nearest a column.
    for u in [-1.7,-.8,0,.8,1.7]:
        for h in [1.3,2.5,3.7]:
            hit=ray(group,point(u,.5,h),-N,4.3)
            assert hit and hit[3]=='glass' and abs(hit[0]-4.01)<tol*2,('door or approach blocked',u,h,hit)
            records.append(dict(kind='door-and-full-width-approach',offset=u,height=h,distance=hit[0]))
    for u in [-1.7,0,1.7]:
        hit=ray(group,point(u,-2.6,3.88),-N,1.2)
        assert hit and hit[3]=='white' and abs(hit[0]-.87)<tol*2,('door-header',u,hit)
        records.append(dict(kind='door-header',offset=u,distance=hit[0]))
    for u in [-1.7,0,1.7]:
        for v in [-.4,-1.8,-3.3]:
            hit=ray(group,point(u,v,2),(0,0,-1),2)
            assert hit and hit[3]=='stone' and abs(hit[1].z-Z-1.05)<tol,('raised landing',u,v,hit)
            records.append(dict(kind='landing',offset=u,depth=v,actualHeight=hit[1].z-Z))
    for i in range(7):
        expected=1.05-i*.15
        for u in [-5.8,0,5.8]:
            v=(i+.5)*.3;hit=ray(group,point(u,v,2),(0,0,-1),3)
            assert hit and hit[3]=='stone' and hit[2].z>.98 and abs(hit[1].z-Z-expected)<tol,('tread',i,u,hit)
            bottom=ray(group,point(u,v,-1),(0,0,1),2)
            assert bottom and abs(bottom[1].z-Z+.15)<tol,('foundation-bottom',i,u,bottom)
            record=dict(kind='stair',step=i,offset=u,height=hit[1].z-Z,foundationBottom=bottom[1].z-Z)
            if ground:
                g=ray(ground,point(u,v,2),(0,0,-1),5)
                assert g and bottom[1].z<g[1].z< hit[1].z,('buried tread or floating foundation',i,u,g)
                record.update(groundHeight=g[1].z-Z,treadAboveGround=hit[1].z-g[1].z,foundationBelowGround=g[1].z-bottom[1].z)
            records.append(record)
    for u,v in [(-6.2,1),(6.2,1),(0,2.25)]:
        assert ray(group,point(u,v,2),(0,0,-1),3) is None,('stairs exceed adopted bounds',u,v)
        records.append(dict(kind='stair-bound-clearance',offset=u,depth=v))
    # Old longest-edge fallback glass/canopy must disappear. Solid wall remains.
    old=Vector((-687.1279782074489,-788.0955060000298,Z));out=Vector((-.001270,-.999999,0))
    for h in [1.3,2.9]:
        hit=ray(group,old+out*2+Vector((0,0,h)),-out,2.2)
        assert hit and hit[3]=='white' and abs(hit[0]-2)<tol*2,('old fallback entry remains',h,hit)
        records.append(dict(kind='old-fallback-removed',height=h,distance=hit[0]))
    return dict(passed=True,rayCount=len(records),groundChecked=bool(ground),samples=records,toleranceMeters=tol)
report=dict(passed=False,scope='Estimated D personnel entry at mapped OSM projection: 3.6 m door, 1.05 m platform, seven 0.3 m treads at 12 m width, 0.15 m foundation. Source/base ground and full adopted doorway approach checked. Not an interior, surveyed reconstruction, accessible route or completed road connection.')
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    ground=meshes([o for o in bpy.context.scene.objects if o.get('layer') in ('terrain','roads')])
    assert ground,'Source ground meshes absent'
    report['source']=check([o for o in bpy.context.scene.objects if o.get('featureId')==ID],ground,.006)
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update()
    ground=meshes([o for o in bpy.context.scene.objects if root_name(o) in ('terrain','roads')]);assert ground,'Base ground meshes absent'
    report['base']=check([o for o in bpy.context.scene.objects if root_name(o)==CHUNK],ground,.04)
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/f'{CHUNK}.glb'));bpy.context.view_layer.update()
    report['near']=check(list(bpy.context.scene.objects),ground,.02)
    report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/models/base.glb',f'public/models/{CHUNK}.glb','public/data/buildings.json']}
    report['passed']=True
except Exception as error:
    report['failure']=str(error);raise
finally:
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
