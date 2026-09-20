"""Fixed-coordinate probes for the civil main building's existing grid glass winding."""
import bpy,sys,json,re,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-civil-wing-ends-grid-winding')
ID,CHUNK,Z='relation/12875606','chunk-n2-n3',4.06
FIXTURES=[{'id': 'way/759129516', 'chunk': 'chunk-n1-n3', 'elevation': 2.38, 'facades': [{'start': [-272.93077627413, -868.0510959998603], 'end': [-265.0, -868.0604532172121], 'normal': [0.0011798606486164757, 0.9999993039641826], 'height': 16.5, 'levels': 5.0, 'rule': {'polygon': 0, 'ring': 0, 'edge': 1, 'part': 'west-five', 'balconies': False, 'windowGrid': {'columns': 2, 'firstLevel': 0, 'edgeInset': 0.45, 'widthRatio': 0.68, 'heightRatio': 0.6, 'pilasterWidth': 0.28, 'pilasterDepth': 0.15, 'paneRows': 2}}}, {'start': [-269.3505153860546, -883.7472159997801], 'end': [-279.4655217912047, -883.7360840000456], 'normal': [-0.0011005423572785474, -0.9999993944030765], 'height': 16.5, 'levels': 5.0, 'rule': {'polygon': 0, 'ring': 0, 'edge': 7, 'balconies': False, 'windowGrid': {'columns': 3, 'firstLevel': 1, 'edgeInset': 0.45, 'widthRatio': 0.65, 'heightRatio': 0.65, 'pilasterWidth': 0.28, 'pilasterDepth': 0.15, 'paneRows': 2}}}, {'start': [-283.1073344416553, -867.4054399998294], 'end': [-272.93077627413, -867.4165719999594], 'normal': [0.0010938858980194918, 0.999999401706642], 'height': 16.5, 'levels': 5.0, 'rule': {'polygon': 0, 'ring': 0, 'edge': 11, 'part': 'west-five', 'balconies': False, 'windowGrid': {'columns': 2, 'firstLevel': 0, 'edgeInset': 0.45, 'widthRatio': 0.68, 'heightRatio': 0.6, 'pilasterWidth': 0.28, 'pilasterDepth': 0.15, 'paneRows': 2}}}]}, {'id': 'relation/11564704', 'chunk': 'chunk-p0-n1', 'elevation': 3.9, 'facades': [{'start': [307.0407116662392, -252.57394800007617], 'end': [293.4172547634234, -255.3012879999136], 'normal': [0.196299433186587, -0.9805439982635276], 'height': 23.1, 'levels': 7.0, 'rule': {'polygon': 0, 'ring': 0, 'edge': 11, 'balconies': False, 'windowGrid': {'columns': 8, 'firstLevel': 1, 'edgeInset': 0.22, 'widthRatio': 0.78, 'heightRatio': 0.55, 'pilasterWidth': 0.18, 'pilasterDepth': 0.28, 'paneRows': 4}}}]}]

def root_name(obj):
 while obj.parent:obj=obj.parent
 return re.sub(r'\.\d+$','',obj.name)

def check(objects,fixture,tolerance,detail):
 trees=[]
 for obj in objects:
  if obj.type!='MESH':continue
  obj.data.calc_loop_triangles();tris=list(obj.data.loop_triangles)
  trees.append((BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],[tuple(t.vertices) for t in tris],all_triangles=True),[obj.data.materials[t.material_index].name.split('.')[0] for t in tris]))
 samples=[]
 for f in fixture['facades']:
  A=Vector((*f['start'],0));B=Vector((*f['end'],0));U=(B-A).normalized();N=Vector((*f['normal'],0));length=(B-A).length
  g=f['rule']['windowGrid'];bay=(length-2*g['edgeInset'])/g['columns'];fh=f['height']/f['levels'];ww=bay*g['widthRatio'];wh=fh*g['heightRatio']
  for level in range(max(1,g['firstLevel']),int(f['levels'])):
   for col in range(g['columns']):
    for sign in (-1,1):
     t=g['edgeInset']+(col+.5)*bay+sign*ww*.2;h=(level+.56)*fh+wh*.13
     origin=A+U*t+N*.7+Vector((0,0,fixture['elevation']+h));hits=[]
     for tree,mats in trees:
      p,n,i,d=tree.ray_cast(origin,-N,1)
      if p is not None:hits.append((d,p,n,mats[i]))
     hit=min(hits,key=lambda x:x[0]) if hits else None
     assert hit and hit[3]=='glass',(fixture['id'],f['rule']['edge'],level,col,hit)
     depth=(hit[1]-A).dot(N);dot=hit[2].dot(N)
     assert abs(depth-(.25 if detail else .07))<tolerance and dot>.99,('outward-grid-glass',fixture['id'],level,col,depth,dot)
     samples.append(dict(edge=f['rule']['edge'],level=level,column=col,side=sign,depth=depth,outwardNormalDot=dot))
 return dict(passed=True,rayCount=len(samples),samples=samples,toleranceMeters=tolerance)

report=dict(passed=False,scope='Outward glass normals on all four pre-existing windowGrid facades, upper floors; prior parameters frozen at commit 291f640. Positions and source/near appearance retained.')
report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/models/base.glb']+[f"public/models/{f['chunk']}.glb" for f in FIXTURES]}
try:
 bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
 report['source']={f['id']:check([o for o in bpy.context.scene.objects if o.get('featureId')==f['id']],f,.006,True) for f in FIXTURES}
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update()
 report['base']={f['id']:check([o for o in bpy.context.scene.objects if root_name(o)==f['chunk']],f,.05,False) for f in FIXTURES}
 report['near']={}
 for f in FIXTURES:
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/f"{f['chunk']}.glb"));bpy.context.view_layer.update()
  report['near'][f['id']]=check(list(bpy.context.scene.objects),f,.02,True)
 report['passed']=True
except Exception as error:report['failure']=str(error);raise
finally:
 (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print('Existing grid normals:',report['passed'],flush=True)
