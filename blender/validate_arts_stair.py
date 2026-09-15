"""Actual source/base/near stair treads, headroom, open sides and host doors."""
import bpy,sys,json,math,re,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-arts-stair')
bs={b['id']:b for b in json.loads((ROOT/'public/data/buildings.json').read_text())};b=bs['way/880089960'];s=b['form']['stairTower'];host=bs['way/759165562'];z=b['elevation'];a=s['angle'];cs,sn=math.cos(a),math.sin(a)
def world(x,y,h):return Vector((s['origin'][0]+x*cs-y*sn,s['origin'][1]+x*sn+y*cs,z+h))
def root_name(o):
    while o.parent:o=o.parent
    return re.sub(r'\.\d+$','',o.name)
def meshes(objects):
    result=[]
    for o in objects:
        if o.type!='MESH':continue
        o.data.calc_loop_triangles();ts=list(o.data.loop_triangles)
        result.append((BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(t.vertices) for t in ts],all_triangles=True),[o.data.materials[t.material_index].name for t in ts]))
    return result
def ray(meshes,p,d,length):
    results=[]
    for tree,mats in meshes:
        hit,n,i,distance=tree.ray_cast(p,Vector(d),length)
        if hit is not None:results.append((distance,hit,n,mats[i]))
    return min(results,key=lambda x:x[0]) if results else None

def check(tower,wall,tol):
    # Fixed intended arrangement: three storey intervals, two flights, ten risers.
    treads=[]
    for level in range(3):
        for lane in range(2):
            for i in range(10):
                x=1.4 if lane==0 else -1.4;y=(1 if lane==0 else -1)*(2.2-4.4*(i+.5)/10);h=.15+(level+lane*.5)*3.3+(i+1)*.165
                found=ray(tower,world(x,y,h+.1),(0,0,-1),.2)
                assert found and abs(found[1].z-z-h)<tol and found[2].z>.98,('Missing or reversed tread',level,lane,i,found)
                assert ray(tower,world(x,y,h+.04),(0,0,1),1.74) is None,('Blocked headroom',level,lane,i)
                treads.append(abs(found[1].z-z-h))
    for level in range(3):
        for side,h in [(1,.15+level*3.3+2.6),(-1,.15+level*3.3+3.7)]:
            assert ray(tower,world(side*8,0,h),(-side*cs,-side*sn,0),8) is None,('Solid side wall',level,side)
    for start,direction,expected in [(13,-1,12.65),(11,1,12.4)]:
        found=ray(tower,world(0,0,start),(0,0,direction),3)
        assert found and abs(found[1].z-z-expected)<tol,('Canopy',found,expected)
    bridges=[];doors=[]
    for level in range(1,4):
        h=.15+level*3.3
        # Stay outside the projecting door sill: this ray measures the deck,
        # while the separate horizontal ray below checks the actual doorway.
        for y in [4,6.4,8.7,s['hostDistance']-.3]:
            found=ray(tower,world(0,y,h+.1),(0,0,-1),.2)
            assert found and abs(found[1].z-z-h)<tol,('Broken landing/bridge',level,y,found)
            bridges.append(abs(found[1].z-z-h))
        found=ray(wall,world(.35,s['hostDistance']-.6,h+1.2),(-sn,cs,0),1)
        assert found and found[3].split('.')[0]=='glass' and abs(found[0]-.46)<tol,('Missing host access door',level,found)
        doors.append(found[0])
    return dict(treadSamples=60,maximumTreadErrorMeters=max(treads),headroomSamples=60,sideVoidRays=6,bridgeSamples=12,maximumBridgeErrorMeters=max(bridges),hostDoorDistances=doors,canopyTopAndUndersidePassed=True,toleranceMeters=tol)

report=dict(passed=False,checkedRoot=str(TARGET),scope='Actual 60 treads and headroom, six open side rays, thin roof, twelve bridge points and three closed host doorways. Dimensions remain photo-constrained estimates.')
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    report['source']=check(meshes(o for o in bpy.context.scene.objects if o.get('featureId')==b['id']),meshes(o for o in bpy.context.scene.objects if o.get('featureId')==host['id']),.006)
    terrain=meshes(o for o in bpy.context.scene.objects if o.get('layer')=='terrain');gaps=[]
    for x,y in [(-4,0),(4,0),(0,4),(0,-4),(0,0)]:
        ground=ray(terrain,world(x,y,10),(0,0,-1),20);assert ground is not None
        gap=z+.15-ground[1].z;assert gap>=-.006,('Ground enters platform',x,y,gap);gaps.append(gap)
    report['groundPlatformClearanceMeters']=gaps
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update()
    group=meshes(o for o in bpy.context.scene.objects if root_name(o)==b['chunk']);report['base']=check(group,group,.05)
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/f"{b['chunk']}.glb"));bpy.context.view_layer.update()
    group=meshes(bpy.context.scene.objects);report['near']=check(group,group,.02)
    report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/models/base.glb',f"public/models/{b['chunk']}.glb",'public/data/buildings.json']};report['passed']=True
except Exception as e:report['failure']=str(e);raise
finally:
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('Arts stair actual geometry:',report['passed'],flush=True)
