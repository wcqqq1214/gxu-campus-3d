"""Check the actual east-end corridor voids, slabs, rails and eight openings."""
import bpy,sys,json,math,re,hashlib,copy
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'blender'))
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-arts-corridor')
b=next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']=='way/759165562')
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

def check(group,building,z,tol):
    f=next(f for f in building['form']['facades'] if f['edge']==0)
    a=Vector((*f['start'],0));edge=Vector((*f['end'],0))-a;n=Vector((*f['normal'],0));length=edge.length
    def point(t,depth,h):return a+edge*t-n*depth+Vector((0,0,z+h))
    def ray(p,d,limit):
        hits=[]
        for tree,materials in group:
            hit,normal,index,distance=tree.ray_cast(p,d,limit)
            if hit is not None:hits.append((distance,hit,materials[index],normal))
        return min(hits,key=lambda h:h[0]) if hits else None
    samples=[]
    for level in (1,2,3):
        floor=3.3*level
        for t in (.3,.5,.7):
            rear=ray(point(t,-.3,floor+1.9),-n,2.5)
            assert rear and abs(rear[0]-2.1)<tol and rear[2]=='white',('closed recess or wrong rear wall',level,t,rear)
            assert rear[3].dot(n)>.98,('reversed rear wall',level,t,rear[3])
            rail=ray(point(t,-.3,floor+.6),-n,.6)
            assert rail and abs(rail[0]-.3)<tol and rail[2]=='pink',('missing solid rail',level,t,rail)
            assert rail[3].dot(n)>.98,('reversed outer railing',level,t,rail[3])
            for direction,expected in [(-1,floor),(1,floor+3.12)]:
                hit=ray(point(t,.9,floor+1.8),Vector((0,0,direction)),2)
                assert hit and abs(hit[1].z-z-expected)<tol,('missing floor or soffit',level,t,direction,hit)
                assert hit[3].z*direction<-.98,('reversed floor or soffit',level,t,direction,hit[3])
            samples.append({'level':level,'t':t,'rearDepth':rear[0]-.3})
        for t in (.01,.99,.35/length,1-.35/length):
            hit=ray(point(t,-.3,floor+1.8),-n,.6)
            assert hit and abs(hit[0]-.3)<tol and hit[2]=='white',('end return or pier',level,t,hit)
    openings=[]
    for level in range(4):
        floor=3.3*level;depth=1.8 if level else 0
        for kind,t,h in [('door',.17,1.8),('window',.86 if level else .4,1.9 if level else 1.8)]:
            hit=ray(point(t,-.3,floor+h),-n,2.5)
            assert hit and hit[2]=='glass' and abs(hit[0]-(depth+.16))<tol,('missing or misplaced opening',level,kind,hit)
            openings.append({'level':level,'kind':kind,'glassDistance':hit[0]})
    ground=ray(point(.7,-.3,1.8),-n,.6)
    assert ground and ground[2]=='white' and abs(ground[0]-.3)<tol,('ground facade still has generic windows',ground)
    return {'passed':True,'recessSamples':samples,'openings':openings,'endReturnAndPierSamples':12,'floorAndSoffitSamples':18,'toleranceMeters':tol}

report={'passed':False,'checkedRoot':str(TARGET),'scope':'East-end three upper open corridors, nine rear/rail stations, 18 floor/ceiling rays, 12 ends/piers and eight photo-estimated openings, with solid ground facade.'}
try:
    if '--generated-only' in sys.argv:
        from generic_buildings import ordinary_building
        from mathutils.geometry import tessellate_polygon
        C={name:i for i,name in enumerate(['stone','pink','white','glass','dark','shadeGlass','paleRoof','red'])}
        results=[]
        for angle in (0,.63,math.pi/2):
            current=copy.deepcopy(b);cs,sn=math.cos(angle),math.sin(angle)
            def rotate(p):return [p[0]*cs-p[1]*sn,p[0]*sn+p[1]*cs]
            current['polygons']=[[[rotate(p) for p in ring] for ring in poly] for poly in b['polygons']]
            current['form']['entrances']=[];current['form']['stairAccessDoors']=[]
            for f in current['form']['facades']:
                for key in ('start','end','normal'):f[key]=rotate(f[key])
            for detail in (False,True):
                mesh=ordinary_building(current,0,C,detail)
                group=[(BVHTree.FromPolygons(mesh.v,mesh.f),[list(C)[m] for m in mesh.m])]
                check(group,current,0,.0001);results.append({'angle':angle,'detail':detail,'passed':True})
        report['generated']=results
    else:
        bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
        report['source']=check(meshes(o for o in bpy.context.scene.objects if o.get('featureId')==b['id']),b,b['elevation'],.006)
        bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update()
        report['base']=check(meshes(o for o in bpy.context.scene.objects if root_name(o)==b['chunk']),b,b['elevation'],.05)
        bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/f"{b['chunk']}.glb"));bpy.context.view_layer.update()
        report['near']=check(meshes(bpy.context.scene.objects),b,b['elevation'],.02)
        report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/models/base.glb',f"public/models/{b['chunk']}.glb",'public/data/buildings.json']}
    report['passed']=True
except Exception as error:report['failure']=str(error);raise
finally:
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('Arts corridor geometry:',report['passed'],flush=True)
