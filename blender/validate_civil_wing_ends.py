"""Fixed-coordinate probes for the civil main building's north wing end windows."""
import bpy,sys,json,re,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-civil-wing-ends')
ID,CHUNK,Z='relation/12875606','chunk-n2-n3',4.06
WALLS=[([-528.934817691,-791.206900],[-514.429118852,-791.218032],5,.42,.4),
       ([-488.567119715,-787.366360],[-476.708146689,-787.377492],3,.55,.48)]

def root_name(obj):
 while obj.parent:obj=obj.parent
 return re.sub(r'\.\d+$','',obj.name)

def check(objects,tolerance,detail):
 trees=[]
 for obj in objects:
  if obj.type!='MESH':continue
  obj.data.calc_loop_triangles();tris=list(obj.data.loop_triangles)
  trees.append((BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],[tuple(t.vertices) for t in tris],all_triangles=True),[obj.data.materials[t.material_index].name.split('.')[0] for t in tris]))
 samples=[]
 for a,b,columns,wr,hr in WALLS:
  A=Vector((*a,0));B=Vector((*b,0));U=(B-A).normalized();N=Vector((-U.y,U.x,0));length=(B-A).length;bay=(length-1.1)/columns
  def probe(t,h,material,depth,kind):
   origin=A+U*t+N*.7+Vector((0,0,Z+h));hits=[]
   for tree,mats in trees:
    p,n,i,d=tree.ray_cast(origin,-N,1)
    if p is not None:hits.append((d,p,n,mats[i]))
   hit=min(hits,key=lambda x:x[0]) if hits else None
   assert hit and hit[3]==material,(kind,a,t,h,material,hit)
   actual=(hit[1]-A).dot(N)
   assert abs(actual-depth)<tolerance and hit[2].dot(N)>.99,(kind,'depth or normal',a,t,h,hit)
   samples.append(dict(kind=kind,wallStart=a,along=t,height=h,material=material,actualDepth=actual,normalDot=hit[2].dot(N)))
  for level in range(3):
   h=(level+.56)*3.6
   for col in range(columns):
    t=.55+(col+.5)*bay
    for sign in (-1,1):probe(t+sign*bay*wr*.22,h+.2,'glass',.25 if detail else .07,'window-glass')
    probe(t,h+hr*3.6/2+.22,'white',0,'wall-above-window')
    probe(t,h-hr*3.6/2-.22,'white',0,'wall-below-window')
   for col in range(columns+1):probe(.55+col*bay,h,'white',0,'white-wall-no-pilaster')
   for t in (.15,length-.15):probe(t,h,'white',0,'white-end-wall')
 return dict(passed=True,rayCount=len(samples),samples=samples,toleranceMeters=tolerance)

report=dict(passed=False,scope='Two north-facing end walls: full white finish and estimated five/three window columns, no continuous pilasters; all dimensions estimated, no whole-building acceptance.')
report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/models/base.glb',f'public/models/{CHUNK}.glb','public/data/buildings.json']}
try:
 bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
 report['source']=check([o for o in bpy.context.scene.objects if o.get('featureId')==ID],.006,True)
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update()
 report['base']=check([o for o in bpy.context.scene.objects if root_name(o)==CHUNK],.05,False)
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/f'{CHUNK}.glb'));bpy.context.view_layer.update()
 report['near']=check(list(bpy.context.scene.objects),.02,True)
 report['passed']=True
except Exception as error:report['failure']=str(error);raise
finally:
 (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print('Civil wing ends:',report['passed'],flush=True)
