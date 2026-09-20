"""Fixed-coordinate probes for the civil main building's north-east round window wall."""
import bpy,sys,json,re,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-civil-round-windows')
ID,CHUNK,Z='relation/12875606','chunk-n2-n3',4.06
A=Vector((-476.7529258206762,-824.2421847814248,0));B=Vector((-486.16654328656296,-824.2300720739172,0))
U=(B-A).normalized();N=Vector((U.y,-U.x,0));L=(B-A).length;CENTER=.587*L

def root_name(obj):
 while obj.parent:obj=obj.parent
 return re.sub(r'\.\d+$','',obj.name)

def check(objects,tolerance):
 trees=[]
 for obj in objects:
  if obj.type!='MESH':continue
  obj.data.calc_loop_triangles();tris=list(obj.data.loop_triangles)
  trees.append((BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],[tuple(t.vertices) for t in tris],all_triangles=True),[obj.data.materials[t.material_index].name.split('.')[0] for t in tris]))
 def point(t,d,h):return A+U*t+N*d+Vector((0,0,Z+h))
 def ray(origin,direction,limit):
  hits=[]
  for tree,mats in trees:
   p,n,i,length=tree.ray_cast(origin,direction,limit)
   if p is not None:hits.append((length,p,n,mats[i]))
  return min(hits,key=lambda h:h[0]) if hits else None
 samples=[]
 for height in (12.4,15.5,18.6,21.7,24.8):
  for dx,dh,material,depth in [(0,0,'glass',.04),(.36,0,'glass',.04),(-.36,0,'glass',.04),(0,.36,'glass',.04),(0,-.36,'glass',.04),(.45,.45,'white',.15),(-.45,.45,'white',.15),(.45,-.45,'white',.15),(-.45,-.45,'white',.15),(.7,0,'white',.15),(-.7,0,'white',.15),(0,.65,'white',.15),(0,-.65,'white',.15)]:
   hit=ray(point(CENTER+dx,.6,height+dh),-N,.9)
   assert hit and hit[3]==material,('round-window-front',height,dx,dh,material,hit)
   actual=(hit[1]-A).dot(N)
   assert abs(actual-depth)<tolerance and hit[2].dot(N)>.99,('round-window-plane',height,dx,dh,hit)
   samples.append(dict(kind='round-glass' if material=='glass' else 'white-around-circle',height=height,offset=[dx,dh],expectedDepth=depth,actualDepth=actual,normalDot=hit[2].dot(N)))
  import math
  for theta in [math.tau*(i+.5)/32 for i in range(0,32,4)]:
   radial=U*math.cos(theta)+Vector((0,0,math.sin(theta)))
   hit=ray(point(CENTER,.1,height),radial,.8)
   assert hit and hit[3]=='white',('reveal',height,theta,hit)
   assert abs(hit[0]-.55*math.cos(math.pi/32))<tolerance and hit[2].dot(radial)<-.95,('reveal-radius-normal',height,theta,hit)
   samples.append(dict(kind='round-reveal',height=height,angle=theta,actualRadius=hit[0],inwardNormalDot=-hit[2].dot(radial)))
 for t in (L*.12,L*.82):
  for h in (11.8,18,26.1):
   hit=ray(point(t,.6,h),-N,.8)
   assert hit and hit[3]=='white' and abs((hit[1]-A).dot(N)-.15)<tolerance,('white-wall-bounds',t,h,hit)
   samples.append(dict(kind='white-wall',along=t,height=h))
 hit=ray(point(CENTER,-1,28),Vector((0,0,-1)),2)
 assert hit and hit[3]=='paleRoof' and abs(hit[1].z-Z-26.4)<tolerance,('retained-roof',hit)
 samples.append(dict(kind='retained-roof',actualHeight=hit[1].z-Z))
 return dict(passed=True,rayCount=len(samples),samples=samples,toleranceMeters=tolerance)

report=dict(passed=False,scope='Five estimated 1.1 m round apertures in the north-east white wall; circle glazing, white square corners, radial reveals, wall bounds and retained roof. No measured dimensions, stair interior or whole-building acceptance claim.')
report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/models/base.glb',f'public/models/{CHUNK}.glb','public/data/buildings.json']}
try:
 bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
 report['source']=check([o for o in bpy.context.scene.objects if o.get('featureId')==ID],.006)
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update()
 report['base']=check([o for o in bpy.context.scene.objects if root_name(o)==CHUNK],.05)
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/f'{CHUNK}.glb'));bpy.context.view_layer.update()
 report['near']=check(list(bpy.context.scene.objects),.02)
 report['passed']=True
except Exception as error:report['failure']=str(error);raise
finally:
 (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print('Civil round windows:',report['passed'],flush=True)
