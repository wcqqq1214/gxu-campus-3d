"""Fixed rays for the side portal and its connection to the original canopy."""
import bpy,sys,json,re,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-civil-portal-return')
ID,CHUNK,Z='relation/12875606','chunk-n2-n3',4.06
A=Vector((-476.769698452549,-838.0503560000666,0))
V=Vector((0.0012146879723256238,0.9999992622662929,0));E=Vector((V.y,-V.x,0))
U=Vector((-0.9999991092491528,0.0013347287742266436,0));N=Vector((-U.y,U.x,0))

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
 def face(depth,height,material,projection):
  hit=ray(A+V*depth+E*.7+Vector((0,0,Z+height)),-E,1)
  assert hit and hit[2]==material,('portal material',depth,height,material,hit)
  actual=(hit[0]-A).dot(E)
  assert abs(actual-projection)<tolerance and hit[1].dot(E)>.98,('portal plane/normal',depth,height,hit)
  samples.append(dict(kind='return-facade',depth=depth,height=height,material=material,actualProjection=actual))
 for d in (.7,1.3,2.5,3.1):
  for h in (1.5,5.3):face(d,h,'glass',.08)
  face(d,3.6,'stone',.27)
 for d in (.3,1.9,3.5):
  for h in (1.5,5.3):face(d,h,'stone',.27)
 for d in (1,2.8):
  for h in (1.5,5.3):face(d,h,'white',.14)
 for h in (3.3,6.6):face(1.5,h,'glass',.08)
 # Side slab, front corner fill, and points on either side of the old/new seam.
 points=[A+V*d+E*p for d in (.4,1.9,3.5) for p in (.3,1.1)]
 points += [A+U*u+N*d for u in (.1,.20,.28,.38) for d in (.4,1.6)]
 for point in points:
  for h,direction,expected in [(8.8,-1,7.8),(6.2,1,7.2)]:
   hit=ray(point+Vector((0,0,Z+h)),Vector((0,0,direction)),2)
   assert hit and hit[2]=='stone' and abs(hit[0].z-Z-expected)<tolerance and hit[1].z*direction<-.98,('canopy surface/seam',list(point),expected,hit)
   samples.append(dict(kind='canopy-top-or-soffit',x=point.x,y=point.y,expectedHeight=expected,actualHeight=hit[0].z-Z))
 # Verify the front and side exposed fascia limits, not just top surfaces.
 for point,normal in [(A+V*1.9+E*1.4,E),(A+E*.7+N*2,N)]:
  hit=ray(point+normal*.6+Vector((0,0,Z+7.5)),-normal,1)
  assert hit and hit[2]=='stone' and abs((hit[0]-point).dot(normal))<tolerance and hit[1].dot(normal)>.98,('fascia',hit)
  samples.append(dict(kind='canopy-fascia',x=hit[0].x,y=hit[0].y))
 for point in (A+V*2+E*1.7,A+E*.7+N*2.3):
  assert ray(point+Vector((0,0,Z+8.8)),Vector((0,0,-1)),2) is None,('canopy outside footprint',point)
  samples.append(dict(kind='outside-canopy-empty',x=point.x,y=point.y))
 for d in (.5,2,3.5):
  assert ray(A+V*d+E*.8+Vector((0,0,Z+.9)),Vector((0,0,-1)),1) is None,('invented platform',d)
  samples.append(dict(kind='no-added-ground-platform',depth=d))
 return dict(passed=True,rayCount=len(samples),samples=samples,toleranceMeters=tolerance)

report=dict(passed=False,scope='Estimated two-bay side portal glazing 0.1–7.2 m, stone piers and 3.6 m beam, connected canopy 7.2–7.8 m with 1.4 m side projection; no new side door or ground platform inferred.')
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
 print('Civil portal return:',report['passed'],flush=True)
