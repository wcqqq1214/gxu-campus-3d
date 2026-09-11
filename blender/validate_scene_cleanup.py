import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parents[1]
checks=[('north park',0,1450),('west lake',-1150,800),('west branch',-1050,-412),('east branch',1050,-50),('south branch',-700,-1400),('south-east tail',305,-1150),('external courts west',-643,206),('external court east',-263,264)]
def check(label):
 vs=[];fs=[]
 for o in bpy.context.scene.objects:
  if o.type!='MESH':continue
  root=o
  while root.parent:root=root.parent
  layer=o.get('layer',root.get('layer'))
  if layer not in ('roads','water','green','sports'):continue
  off=len(vs);vs.extend([o.matrix_world@v.co for v in o.data.vertices]);fs.extend([tuple(off+i for i in p.vertices) for p in o.data.polygons])
 bv=BVHTree.FromPolygons(vs,fs)
 for name,x,y in checks:
  assert bv.ray_cast(Vector((x,y,100)),Vector((0,0,-1)),200)[0] is None,(label,name)
 return {'representation':label,'emptyLocationsChecked':len(checks)}
bpy.ops.wm.open_mainfile(filepath=str(R/'blender/gxu-campus.blend'))
assert sum(bool(o.get('basketballCourt')) for o in bpy.data.objects)==31
report=[check('editable source')]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(R/'public/models/base.glb'))
report.append(check('base GLB'))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(R/'public/models/infra-road-00.glb'))
ys=[(o.matrix_world@v.co).y for o in bpy.context.scene.objects if o.type=='MESH' for v in o.data.vertices]
assert min(ys)>-970,min(ys)
report.append({'representation':'near road GLB','minimumNorthCoordinate':min(ys)})
(R/'docs/model-checks/scene-cleanup-geometry.json').write_text(json.dumps(report,indent=2)+'\n')
print(report,flush=True)
