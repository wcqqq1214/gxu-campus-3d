"""Fixed-coordinate inspection of the civil tower's continuous tapered white side wall."""
import bpy,sys,json,re,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-civil-sidewall')
ID,CHUNK,Z='relation/12875606','chunk-n2-n3',4.06
A=Vector((-476.769698452549,-838.0503560000666,0))
V=Vector((0.0012146879723256238,0.9999992622662929,0));E=Vector((V.y,-V.x,0))

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
 def face(depth,height,material,projection,label):
  hit=ray(A+V*depth+E*.7+Vector((0,0,Z+height)),-E,1)
  assert hit and hit[2]==material,('side-wall material',depth,height,material,hit)
  actual=(hit[0]-A).dot(E)
  assert abs(actual-projection)<tolerance and hit[1].dot(E)>.98,('side-wall plane/normal',depth,height,hit)
  samples.append(dict(kind=label,depth=depth,height=height,material=material,actualProjection=actual))
 for depth in (4.2,6.334,8,10.557,12.3):
  for h in (.5,3.3,6.6,9.9,13.2,16.5,19.8,23.1,26.4,30,34):
   rear=6.2+(34.8-h)*1.8/8.4
   if depth<rear-.15:face(depth,h,'white',.08,'continuous-white-wall')
 # Former default window centres must now hit the white face in both LODs.
 for depth,h in [(6.334,1.848),(6.334,11.748),(10.557,1.848),(10.557,8.448)]:
  face(depth,h,'white',.08,'covered-window-removed')
 # Keep the side portal strip and stone joints beyond the white wall.
 for depth,h in [(1.5,3.3),(1.5,6.6),(15,3.3),(15,13.2),(15,23.1)]:
  face(depth,h,'stone',0,'retained-stone')
 for h in (3.3,9.9,19.8,27.5,33):
  rear=6.2+(34.8-h)*1.8/8.4
  hit=ray(A+V*16+E*.04+Vector((0,0,Z+h)),-V,12.5)
  assert hit and hit[2]=='white' and abs((hit[0]-A).dot(V)-rear)<tolerance and hit[1].dot(V)>.9,('rear-slope',h,rear,hit)
  samples.append(dict(kind='continuous-rear-slope',height=h,expectedDepth=rear,actualDepth=(hit[0]-A).dot(V)))
 # At storey joints just beyond the sloping edge the original wall remains.
 for h in (3.3,9.9,19.8,23.1):
  rear=6.2+(34.8-h)*1.8/8.4
  face(rear+.35,h,'stone',0,'outside-taper')
 return dict(passed=True,rayCount=len(samples),samples=samples,toleranceMeters=tolerance)

report=dict(passed=False,scope='White east side wall continues from model base -0.5 m to crown 34.8 m, 0.08 m outward, constant estimated taper; generic windows intersecting it removed, portal return and small openings still pending.')
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
 print('Civil side wall:',report['passed'],flush=True)
