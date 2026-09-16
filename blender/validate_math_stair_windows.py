"""Verify photo-constrained sparse stair-wall glazing, including blank wall areas."""
import bpy,sys,json,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-math-stair')
b=next(x for x in json.loads((ROOT/'public/data/buildings.json').read_text()) if x['id']=='way/759129515')
f=next(x for x in b['form']['facades'] if x['edge']==15 and x['part']=='west-stair')
a=Vector((*f['start'],b['elevation']));edge=Vector((*f['end'],b['elevation']))-a;n=Vector((*f['normal'],0))
def root_name(o):
 while o.parent:o=o.parent
 return o.name

def check(objects,tolerance):
 trees=[]
 for o in objects:
  if o.type!='MESH':continue
  trees.append((BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons]),[o.data.materials[p.material_index].name.split('.')[0] for p in o.data.polygons]))
 samples=[]
 def probe(kind,t,z,material,distance):
  p=a+edge*t+Vector((0,0,z))+n*.8
  hits=[]
  for tree,mats in trees:
   h=tree.ray_cast(p,-n,1.2)
   if h[0] is not None:hits.append((h[3],mats[h[2]]))
  actual=min(hits,default=None)
  assert actual and actual[1]==material and abs(actual[0]-distance)<tolerance,(kind,t,z,actual,material,distance)
  samples.append(dict(kind=kind,fraction=t,height=z,firstMaterial=actual[1],distanceMeters=actual[0]))
 # Acceptance stations are fixed estimates, not read from the new panel list.
 for base in (3.4,6.05,8.7):
  for bottom in (base,base+.55):
   for t in (.13,.32):
    probe('small-window-pane',t,bottom+.175,'glass',.76)
    probe('small-window-frame',t-.043+.02/edge.length,bottom+.175,'white',.69)
 for t in (.5,.72,.9):
  for z in (1.8,3.6,5.0,6.8,8.3,9.5):probe('retained-solid-wall',t,z,'stone',.8)
 return dict(passed=True,windowCount=12,toleranceMeters=tolerance,samples=samples)
report=dict(passed=False,buildingId=b['id'],checkedRoot=str(TARGET),dimensionStatus='photo-constrained estimates; shallow exterior glazing, not through-holes')
try:
 bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
 report['source']=check([o for o in bpy.context.scene.objects if o.get('featureId')==b['id']],.012)
 for label,file,tol in [('base','base.glb',.035),('near',b['chunk']+'.glb',.02)]:
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/file));bpy.context.view_layer.update()
  report[label]=check([o for o in bpy.context.scene.objects if label!='base' or root_name(o)==b['chunk']],tol)
 report['passed']=True
except Exception as error:report['failure']=str(error)
finally:
 report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/data/models.json','public/models/base.glb','public/models/'+b['chunk']+'.glb']}
 (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print('Math stair windows:',report['passed'],report.get('failure',''),flush=True)
if not report['passed']:raise RuntimeError(report['failure'])
