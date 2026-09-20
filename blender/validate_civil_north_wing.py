"""Fixed-coordinate probes for the civil main building's north wing central gallery."""
import bpy,sys,json,re,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-civil-north-wing')
ID,CHUNK,Z='relation/12875606','chunk-n2-n3',4.06
A=Vector((-514.439377478,-795.136496,0));B=Vector((-488.577378343,-795.169892,0))
U=(B-A).normalized();N=Vector((-U.y,U.x,0));L=(B-A).length;BAY=(L-.6)/7

def root_name(obj):
 while obj.parent:obj=obj.parent
 return re.sub(r'\.\d+$','',obj.name)

def check(objects,tolerance):
 trees=[]
 for obj in objects:
  if obj.type!='MESH':continue
  obj.data.calc_loop_triangles();tris=list(obj.data.loop_triangles)
  trees.append((BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],[tuple(t.vertices) for t in tris],all_triangles=True),[obj.data.materials[t.material_index].name.split('.')[0] for t in tris]))
 def point(t,d,h):return A+U*t-N*d+Vector((0,0,Z+h))
 def ray(t,d,h,direction,limit):
  hits=[]
  for tree,mats in trees:
   p,n,i,length=tree.ray_cast(point(t,d,h),direction,limit)
   if p is not None:hits.append((length,p,n,mats[i]))
  return min(hits,key=lambda h:h[0]) if hits else None
 samples=[]
 def front(t,h,depth,kind,material='white'):
  hit=ray(t,-.7,h,-N,2.3)
  assert hit and hit[3]==material,(kind,t,h,material,hit)
  actual=-(hit[1]-A).dot(N)
  dot=.98 if kind.endswith('jamb') and tolerance>.02 else .99
  assert abs(actual-depth)<tolerance and hit[2].dot(N)>dot,(kind,'plane or normal',t,h,depth,hit)
  samples.append(dict(kind=kind,along=t,height=h,expectedDepth=depth,actualDepth=actual,normalDot=hit[2].dot(N),minimumNormalDot=dot))
 def horizontal(t,d,h,dz,expected,kind):
  hit=ray(t,d,h,Vector((0,0,dz)),.6)
  assert hit and hit[3]=='white' and abs(hit[1].z-Z-expected)<tolerance and hit[2].z*dz<-.99,(kind,t,d,h,expected,hit)
  samples.append(dict(kind=kind,along=t,depth=d,expectedHeight=expected,actualHeight=hit[1].z-Z))
 for bay in range(7):
  t=.3+BAY*(bay+.5)
  for level in (1,2):
   floor=level*3.6
   front(t,floor+.5,0,'solid-rail')
   front(t,floor+1.4,1.16,'rear-glass','glass')
   front(t+1.1,floor+1.4,1.1,'rear-window-jamb')
   front(t,floor+3.0,1.3,'rear-solid-wall')
   assert ray(t,-.1,floor+1.4,-N,.9) is None,('old flush wall or window remains',bay,level)
   samples.append(dict(kind='gallery-clearance',bay=bay,level=level))
   horizontal(t,.65,floor+.3,-1,floor,'slab-top')
   horizontal(t,.65,floor-.4,1,floor-.18,'slab-underside')
  front(t,1.2,-.14,'ground-glass','glass')
  front(t+1.325,1.2,-.2,'ground-window-jamb')
  front(t,3.1,0,'ground-wall-above-glass')
  horizontal(t,.65,10.4,1,10.62,'roof-slab-underside')
 for i in range(8):
  t=.3+BAY*i
  for h in (5.0,8.6):front(t,h,0,'white-pier')
  front(t,1.2,0,'ground-wall-between-glass')
 for t in (.08,L-.08):
  for h in (1.2,5.,8.6):front(t,h,0,'retained-end-wall')
 for x,y in [(-500,-815),(-505,-820),(-490,-810)]:
  for tree,mats in trees:assert tree.ray_cast(Vector((x,y,Z+35)),Vector((0,0,-1)),34.8)[0] is None,('courtyard filled',x,y)
  samples.append(dict(kind='courtyard-void',position=[x,y]))
 return dict(passed=True,rayCount=len(samples),samples=samples,toleranceMeters=tolerance)

report=dict(passed=False,scope='North wing central facade: two upper galleries recessed 1.3 m, seven estimated bays and eight white piers, upper rear glazing and seven ground glazing groups. Fixed adopted dimensions, not a measured window schedule or whole-building acceptance.')
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
 print('Civil north wing:',report['passed'],flush=True)
