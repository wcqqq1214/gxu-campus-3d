"""Fixed map/height probes for the annex gable screen and arched aperture."""
import bpy,json,sys,re,hashlib,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(s.split('=',1)[1]).resolve() for s in sys.argv if s.startswith('--check-root=')),ROOT)
PREFIX=next((s.split('=',1)[1] for s in sys.argv if s.startswith('--report-prefix=')),'s2-civil-gable')
ID,CHUNK,Z='relation/12875606','chunk-n2-n3',4.06
A=Vector((-515.7928221562697,-863.6500134159477,0));B=Vector((-515.7723045638294,-846.9517384728929,0))
L=(B-A).length;U=(B-A).normalized();N=Vector((U.y,-U.x,0))
def root(o):
 while o.parent:o=o.parent
 return re.sub(r'\.\d+$','',o.name)
def check(objects,tolerance):
 trees=[]
 for o in objects:
  if o.type!='MESH':continue
  o.data.calc_loop_triangles();ts=list(o.data.loop_triangles)
  trees.append((BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(t.vertices) for t in ts],all_triangles=True),[o.data.materials[t.material_index].name.split('.')[0] for t in ts]))
 def point(s,d,h):return A+U*s+N*d+Vector((0,0,Z+h))
 def ray(p,v,length):
  hits=[]
  for tree,mats in trees:
   h,n,i,d=tree.ray_cast(p,v,length)
   if h is not None:hits.append((h,n,mats[i],d))
  return min(hits,key=lambda h:h[3]) if hits else None
 samples=[]
 def wall(s,h,material,depth,reverse=False):
  hit=ray(point(s,-.7 if reverse else .7,h),N if reverse else -N,1.5)
  assert hit and hit[2]==material,('wall/opening material',s,h,reverse,hit)
  assert abs((hit[0]-A).dot(N)-depth)<tolerance,('wall/opening depth',s,h,hit)
  assert hit[1].dot(N)*(-1 if reverse else 1)>.98,('wall/opening normal',s,h,hit)
  samples.append(dict(kind='back' if reverse else 'front',s=s,height=h,material=material,depth=depth))
 for f in (.12,.25,.38,.62,.75,.88):
  wall(L*f,11.7,'white',0);wall(L*f,11.7,'white',-.3,True)
 for offset in (-.6,-.2,.2,.6):
  # The low pane probe also rejects the old solid 0.8 m roof parapet.
  for h in (11.55,12.1):
   wall(L/2+offset,h,'glass',-.08);wall(L/2+offset,h,'glass',-.10,True)
 wall(L/2+.86,11.8,'dark',.015)
 wall(L/2+.8,13.0,'white',0)
 wall(L/2+.2,13.0,'glass',-.08)
 for f in (.1,.25,.4,.5,.6,.75,.9):
  expected=11.6+2.8*(1-abs(2*f-1))
  hit=ray(point(L*f,-.15,16),Vector((0,0,-1)),8)
  assert hit and abs(hit[0].z-Z-expected)<tolerance and hit[1].z>0,('gable profile',f,expected,hit)
  samples.append(dict(kind='profile',fraction=f,expectedHeight=expected,actualHeight=hit[0].z-Z))
  assert ray(point(L*f,.7,expected+.2),-N,1.5) is None,('wall above gable profile',f)
 for f in (.15,.35,.65,.85):
  for d,h in ((-2,10.8),(1.2,7.2)):
   hit=ray(point(L*f,d,16),Vector((0,0,-1)),12)
   assert hit and abs(hit[0].z-Z-h)<tolerance and hit[1].z>.98,('unchanged flat roof/terrace',f,d,h,hit)
   samples.append(dict(kind='retained-roof',fraction=f,offset=d,expectedHeight=h))
 return dict(passed=True,probes=len(samples),samples=samples,toleranceMeters=tolerance)
report=dict(passed=False,scope='Estimated thin east gable screen on retained flat annex roof: 10.8 m base, 11.6 m shoulders, 14.4 m peak; true arched aperture with inset pane. Fixed front/back/profile and unchanged roof/terrace probes; no inferred whole pitched roof.')
try:
 bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'));report['source']=check([o for o in bpy.context.scene.objects if o.get('featureId')==ID],.006)
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update();report['base']=check([o for o in bpy.context.scene.objects if root(o)==CHUNK],.05)
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/f'{CHUNK}.glb'));bpy.context.view_layer.update();report['near']=check(list(bpy.context.scene.objects),.02)
 report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/models/base.glb',f'public/models/{CHUNK}.glb','public/data/buildings.json']};report['passed']=True
except Exception as e:report['failure']=str(e);raise
finally:
 (ROOT/f'docs/model-checks/refinement/{PREFIX}-geometry.json').write_text(json.dumps(report,indent=2)+'\n');print('Civil gable screen:',report['passed'],flush=True)
