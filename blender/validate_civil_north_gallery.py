"""Fixed-coordinate probes for the civil main building's north courtyard gallery."""
import bpy,sys,json,re,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-civil-north-gallery')
ID,CHUNK,Z='relation/12875606','chunk-n2-n3',4.06
A=Vector((-512.12092773,-824.246676,0));B=Vector((-486.166600955,-824.280072,0))
U=(B-A).normalized();N=Vector((-U.y,U.x,0));L=(B-A).length;BAY=(L-.8)/5

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
 def front(t,h,depth,kind,material='white',normal=N):
  hit=ray(t,-.7,h,-N,2.7)
  assert hit and hit[3]==material,(kind,t,h,material,hit)
  actual=-(hit[1]-A).dot(N)
  assert abs(actual-depth)<tolerance,(kind,'depth',t,h,actual,depth)
  # Compressed base coordinates can rotate the normal of a 6 cm jamb.
  # Keep strict plane positions and full-size-face normals; allow 12 degrees
  # only on these tiny base frames (source/near remain below 8 degrees).
  minimum_dot=.98 if kind=='rear-window-jamb' and tolerance>.02 else .99
  assert hit[2].dot(normal)>minimum_dot,(kind,'normal',hit)
  samples.append(dict(kind=kind,along=t,height=h,expectedDepth=depth,actualDepth=actual,material=material,normalDot=hit[2].dot(normal),minimumNormalDot=minimum_dot))
 def horizontal(t,d,h,dz,expected,kind):
  hit=ray(t,d,h,Vector((0,0,dz)),.8)
  assert hit and hit[3]=='white' and abs(hit[1].z-Z-expected)<tolerance,(kind,t,d,h,expected,hit)
  assert hit[2].z*dz<-.99,(kind,'normal',hit)
  samples.append(dict(kind=kind,along=t,depth=d,expectedHeight=expected,actualHeight=hit[1].z-Z))
 for i in range(5):
  for level in range(1,8):
   floor=level*3.3
   for fraction,depth,slope in [(.1,0,0),(.24,.19,.38/(BAY*.12)),(.5,.38,0),(.76,.19,-.38/(BAY*.12)),(.9,0,0)]:
    t=.4+BAY*(i+fraction)
    front(t,floor+.5,depth,'folded-rail',normal=(N+U*slope).normalized())
    horizontal(t,depth+.3,floor+.3,-1,floor,'slab-top')
    horizontal(t,depth+.3,floor-.4,1,floor-.18,'slab-underside')
    hit=ray(t,-.1,floor+1.3,-N,.65)
    assert hit is None,('old flush wall remains',i,level,fraction,hit)
    samples.append(dict(kind='recess-clearance',bay=i,level=level,fraction=fraction))
   for fraction,width in [(.30,1.1),(.72,.9)]:
    t=.4+BAY*(i+fraction)
    front(t,floor+1.3,1.46,'rear-glass','glass')
    front(t+width/2,floor+1.3,1.4,'rear-window-jamb')
   front(.4+BAY*(i+.5),floor+2.8,1.6,'rear-solid-wall')
  t=.4+BAY*(i+.5)
  horizontal(t,.19,3.5,-1,3.12,'ground-wall-notch-cap')
  assert ray(t,.19,6.8,Vector((0,0,-1)),.5) is None,('notch unexpectedly filled',i)
  samples.append(dict(kind='second-slab-notch-open',bay=i))
  hit=ray(t,.19,27,Vector((0,0,-1)),1)
  assert hit and hit[3]=='paleRoof' and abs(hit[1].z-Z-26.4)<tolerance,('roof changed',hit)
  samples.append(dict(kind='retained-roof',bay=i,actualHeight=hit[1].z-Z))
  horizontal(t,.19,26,1,26.22,'straight-roof-underside')
 for t in (.2,L-.2):
  front(t,15,0,'end-wall-retained')
 for x,y in [(-500,-815),(-505,-820),(-490,-810)]:
  for tree,mats in trees:
   assert tree.ray_cast(Vector((x,y,Z+35)),Vector((0,0,-1)),34.8)[0] is None,('courtyard filled',x,y)
  samples.append(dict(kind='courtyard-void',position=[x,y]))
 return dict(passed=True,rayCount=len(samples),samples=samples,toleranceMeters=tolerance)

report=dict(passed=False,scope='Estimated main courtyard gallery on levels 2–8: 1.6 m rear wall setback, five folded slab/solid-rail groups with 0.38 m inward offset, ten rear glass openings per level, retained ground cap and straight roof. No survey or whole-building acceptance claim.')
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
 print('Civil north gallery:',report['passed'],flush=True)
