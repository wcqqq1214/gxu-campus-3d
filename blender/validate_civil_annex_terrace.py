"""Fixed map-space probes for the estimated east annex setback and roof terrace."""
import bpy,sys,json,re,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-civil-annex-terrace')
ID,CHUNK,Z='relation/12875606','chunk-n2-n3',4.06
A=Vector((-512.5723073303868,-846.9559559997294,0))
B=Vector((-512.5928245849979,-863.6539559998882,0))
V=(B-A).normalized();E=Vector((-V.y,V.x,0))

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
 def point(along,inward,height):
  return A+V*along-E*inward+Vector((0,0,Z+height))
 def roof(along,inward,height,kind):
  hit=ray(point(along,inward,14),Vector((0,0,-1)),15)
  assert hit and abs(hit[0].z-Z-height)<tolerance and hit[1].z>.98,(kind,along,inward,height,hit)
  samples.append(dict(kind=kind,along=along,inward=inward,height=height,actualHeight=hit[0].z-Z))
 for along in (2,5,8,11,14):
  for inward in (.6,1.6,2.6):roof(along,inward,7.2,'terrace-floor')
  roof(along,4.2,10.8,'retained-upper-roof')
  roof(along,0,8.0,'outer-terrace-parapet')
  roof(along,3.2,11.6,'upper-roof-parapet')
  for height in (8.4,9.4,10.4):
   assert ray(point(along,-.5,height),-E,2.8) is None,('old upper wall still fills terrace',along,height)
   samples.append(dict(kind='removed-front-upper-wall',along=along,height=height))
  hit=ray(point(along,2.3,10.65),-E,1.2)
  assert hit and hit[2]=='stone' and abs((hit[0]-A).dot(-E)-3.2)<tolerance and hit[1].dot(E)>.98,('setback wall plane/normal',along,hit)
  samples.append(dict(kind='setback-upper-wall',along=along,inward=3.2))
 # Three estimated glazed openings, sampled off mullions, on the recessed wall.
 # The edge runs south to north; fractions are fixed independently of JSON.
 length=16.69828756
 for f in (.145,.455,.765):
  along=length*(1-f)
  for height in (8.6,9.8):
   hit=ray(point(along,2.6,height),-E,1)
   assert hit and hit[2]=='glass' and abs((hit[0]-A).dot(-E)-3.16)<tolerance and hit[1].dot(E)>.98,('recessed glazing',along,height,hit)
   samples.append(dict(kind='upper-glazing',along=along,height=height))
 # Lower front wall stays on the original ground edge; no floating upper body.
 for along in (2,8,14):
  hit=ray(point(along,-.5,3.6),-E,1)
  assert hit and hit[2]=='stone' and abs((hit[0]-A).dot(E))<tolerance and hit[1].dot(E)>.98,('retained lower front',along,hit)
  samples.append(dict(kind='retained-lower-front',along=along,height=3.6))
 return dict(passed=True,rayCount=len(samples),samples=samples,toleranceMeters=tolerance)

report=dict(passed=False,scope='Estimated east annex upper setback 3.2 m; terrace floor 7.2 m and parapet 8.0 m; retained upper roof 10.8 m and parapet 11.6 m; three glazed groups. No measured dimensions or inferred complete pitched roof.')
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
 print('Civil annex terrace:',report['passed'],flush=True)
