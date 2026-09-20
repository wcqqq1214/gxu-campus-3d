"""Independent fixed-coordinate rays for the civil tower roof silhouette."""
import bpy,sys,json,re,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-civil-crown')
ID,CHUNK,Z='relation/12875606','chunk-n2-n3',4.06
A=Vector((-476.769698452549,-838.0503560000666,0))
U=Vector((-0.9999991092491528,0.0013347287742266436,0))
V=Vector((0.0012146879723256238,0.9999992622662929,0))
N=Vector((-U.y,U.x,0));E=Vector((V.y,-V.x,0))

def root_name(o):
 while o.parent:o=o.parent
 return re.sub(r'\.\d+$','',o.name)

def check(objects,tolerance):
 trees=[]
 for o in objects:
  if o.type!='MESH':continue
  o.data.calc_loop_triangles();ts=list(o.data.loop_triangles)
  trees.append((BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(t.vertices) for t in ts],all_triangles=True),
    [o.data.materials[t.material_index].name.split('.')[0] for t in ts]))
 samples=[]
 def ray(origin,direction,distance):
  hits=[]
  for tree,mats in trees:
   p,n,i,d=tree.ray_cast(origin,direction,distance)
   if p is not None:hits.append((p,n,mats[i],d))
  return min(hits,key=lambda h:h[3]) if hits else None
 def face(label,axis,normal,distance,height,material,depth):
  hit=ray(A+axis*distance+normal*.7+Vector((0,0,Z+height)),-normal,1)
  assert hit and hit[2]==material,(label,distance,height,material,hit)
  actual=(hit[0]-A).dot(normal)
  assert abs(actual-depth)<tolerance and hit[1].dot(normal)>.98,(label,'depth/normal',actual,hit)
  samples.append(dict(kind=label,distance=distance,height=height,material=material,actualDepth=actual))
 for label,axis,normal,end,cols in [('south',U,N,15.179294826891339,6),('east',V,E,3.7,2)]:
  cell=(end-.1-.14)/cols;row=(32.2-26-.14)/4
  for col in range(cols):
   d=.17+(col+.5)*cell
   for j in range(4):face(label+'-glass',axis,normal,d,26.07+(j+.5)*row,'glass',.04)
   for j in range(1,4):face(label+'-frame',axis,normal,d,26.07+j*row,'white',.15)
  for col in range(1,cols):face(label+'-mullion',axis,normal,.17+col*cell,30,'white',.15)
  face(label+'-join',axis,normal,.17+cell*.5,26.2,'glass',.04)
  face(label+'-cap',axis,normal,.17+cell*.5,32.3,'stone',0)
 for s in (1,7,14):
  for t in (1,3):
   hit=ray(A+U*s+V*t+Vector((0,0,Z+38)),Vector((0,0,-1)),15)
   assert hit and abs(hit[0].z-Z-32.4)<tolerance and hit[1].z>.98,('roof',s,t,hit)
   samples.append(dict(kind='crown-roof',u=s,v=t,height=hit[0].z-Z))
 for s,t,h in [(.175,4.5,34.8),(.175,5.8,34.8),(7,5,26.4),(14,6,26.4),(3,10,26.4)]:
  hit=ray(A+U*s+V*t+Vector((0,0,Z+38)),Vector((0,0,-1)),15)
  assert hit and abs(hit[0].z-Z-h)<tolerance and hit[1].z>.98,('screen/retained roof',s,t,h,hit)
  samples.append(dict(kind='screen-or-retained-roof',u=s,v=t,height=hit[0].z-Z))
 for t in (4,5,6):
  for h in (27.5,30,34):face('white-screen',V,E,t,h,'white',0)
 for h in (27,30,34):
  expected=8-(h-26.4)*1.8/8.4
  hit=ray(A+U*.175+V*8.8+Vector((0,0,Z+h)),-V,4)
  assert hit and hit[2]=='white' and abs((hit[0]-A).dot(V)-expected)<tolerance and hit[1].dot(V)>.9,('tapered rear',h,hit)
  samples.append(dict(kind='sloped-rear',height=h,expectedDepth=expected,actualDepth=(hit[0]-A).dot(V)))
 # Rays just behind the taper, above the roof, must stay empty.
 for t,h in [(7.2,33),(8.3,28),(4,35.2)]:
  assert ray(A+V*t+E*.7+Vector((0,0,Z+h)),-E,1) is None,('filled outside crown',t,h)
  samples.append(dict(kind='outside-empty',v=t,height=h))
 return dict(passed=True,rayCount=len(samples),samples=samples,toleranceMeters=tolerance)

report=dict(passed=False,scope='Estimated corner crown roof 32.4 m, glazing 26.0–32.2 m and tapered east roof screen 34.8 m; lower tower fin and side portal pending.')
report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/models/base.glb',f'public/models/{CHUNK}.glb','public/data/buildings.json']}
try:
 bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
 report['source']=check([o for o in bpy.context.scene.objects if o.get('featureId')==ID],.006)
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update()
 report['base']=check([o for o in bpy.context.scene.objects if root_name(o)==CHUNK],.05)
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/f'{CHUNK}.glb'));bpy.context.view_layer.update()
 report['near']=check(list(bpy.context.scene.objects),.02)
 report['passed']=True
except Exception as e:report['failure']=str(e);raise
finally:
 (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print('Civil crown:',report['passed'],flush=True)
