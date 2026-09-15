"""Ray-check shipped arts doorway materials and canopy-to-road continuity."""
import bpy,sys,json,math,hashlib,re
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-arts-entry')
bs={b['id']:b for b in json.loads((ROOT/'public/data/buildings.json').read_text())}
b=bs['way/759165563'];entry=b['form']['entrances'][0]
site=next(s for s in json.loads((ROOT/'public/data/sites.json').read_text())['sites'] if s['id']=='arts-west-canopy-connection')
a=site['angle'];cs,sn=math.cos(a),math.sin(a)
def world(x,y):return site['origin'][0]+x*cs-y*sn,site['origin'][1]+x*sn+y*cs

def trees(objects):
    result=[]
    for o in objects:
        if o.type!='MESH':continue
        o.data.calc_loop_triangles();tri=list(o.data.loop_triangles)
        result.append((BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(t.vertices) for t in tri],all_triangles=True),[o.data.materials[t.material_index].name for t in tri]))
    return result

def hit(meshes,point,direction,distance=20):
    hits=[]
    for tree,mats in meshes:
        p,n,i,d=tree.ray_cast(Vector(point),Vector(direction),distance)
        if p is not None:hits.append((d,p,mats[i]))
    return min(hits,key=lambda h:h[0]) if hits else None

def root_name(o):
    while o.parent:o=o.parent
    return re.sub(r'\.\d+$','',o.name)

def check_doors(meshes,tolerance):
    results=[];floor=b['elevation']+.15
    for x in [-3.3,0,3.3]:
        for height in [1.4,2.8]:
            origin=world(x+.5,1);h=hit(meshes,(*origin,floor+height),(sn,-cs,0),2)
            assert h is not None and h[2].split('.')[0]=='glass',('Expected glazed door/transom',x,height,h)
            assert abs(h[0]-.86)<tolerance,('Door is not at west wall',h)
            results.append({'bayCenter':x,'height':height,'material':h[2],'distance':h[0]})
    return results

def check_ground(objects,tolerance):
    objects=list(objects)
    canopy=trees(o for o in objects if o.get('featureId')=='way/880089961' or root_name(o)==bs['way/880089961']['chunk'])
    paving=trees(o for o in objects if o.get('siteId')==site['id'] or root_name(o)=='site-'+site['id'])
    road=trees(o for o in objects if o.name=='roads' or root_name(o)=='roads')
    terrain=trees(o for o in objects if o.get('layer')=='terrain' or root_name(o)=='terrain')
    assert canopy and paving and road and terrain,('Missing actual meshes',len(canopy),len(paving),len(road),len(terrain))
    floor=bs['way/880089961']['elevation']+.15
    def height(mesh,x,y):
        h=hit(mesh,(*world(x,y),floor+1),(0,0,-1),10)
        assert h is not None,('Missing surface',x,y)
        return h[1].z
    starts=site['startColumns'];cols=site['columns']
    result=[]
    for x in [-4.5,0,4.5]:
        start=starts[0][1]+(x-starts[0][0])/(starts[1][0]-starts[0][0])*(starts[1][1]-starts[0][1])
        pair=next((a,b) for a,b in zip(cols,cols[1:]) if a[0]<=x<=b[0]);a,b=pair
        end=a[1]+(x-a[0])/(b[0]-a[0])*(b[1]-a[1])
        near=height(canopy,x,start-.08);begin=height(paving,x,start+.08)
        far=height(paving,x,end-.08);contact=height(paving+road,x,end+.08)
        assert abs(begin-near)<tolerance,('Canopy seam',x,begin,near)
        assert abs(contact-far)<tolerance,('Road seam',x,contact,far)
        clear=[]
        for t in [.2,.5,.8]:
            y=start+(end-start)*t;gap=height(paving,x,y)-height(terrain,x,y)
            assert gap>=.08-tolerance,('Ground crosses connector',x,t,gap)
            clear.append(gap)
        result.append({'x':x,'canopySeamMeters':abs(begin-near),'roadSeamMeters':abs(contact-far),'groundClearanceMeters':clear})
    return result

report={'passed':False,'scope':'Three closed glazed doorway bays and transoms; nine interior ground-clearance samples and three platform/road joins. Geometric continuity, not measured real-world dimensions or accessibility certification.'}
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    report['sourceDoors']=check_doors(trees(o for o in bpy.context.scene.objects if o.get('featureId')==b['id']),.006)
    report['sourceGround']=check_ground(bpy.context.scene.objects,.012)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update()
    report['baseDoors']=check_doors(trees(o for o in bpy.context.scene.objects if root_name(o)==b['chunk']),.05)
    report['baseGround']=check_ground(bpy.context.scene.objects,.04)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/f"{b['chunk']}.glb"));bpy.context.view_layer.update()
    report['nearDoors']=check_doors(trees(bpy.context.scene.objects),.02)
    report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/models/base.glb',f"public/models/{b['chunk']}.glb",'public/data/sites.json']}
    report['passed']=True
except Exception as e:
    report['failure']=str(e);raise
finally:
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Arts entry geometry:',report['passed'],flush=True)
