"""Geometric regression checks against the saved source, not just catalogue flags."""
import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'))
catalog=json.loads((ROOT/'public/data/landmarks.json').read_text())
objects={o.get('landmark'):o for o in bpy.context.scene.objects if o.get('landmark')}
hui=objects['huixue'];l=next(l for l in catalog if l['id']=='huixue')
doors=[v.co for p in hui.data.polygons if hui.data.materials[p.material_index].name=='wood' for v in [hui.data.vertices[i] for i in p.vertices]]
assert doors,'Missing Huixue entrance doors'
assert min(v.x for v in doors)>l['bounds'][2]-10,'Entrance is not on the east face'
assert abs(sum(v.y for v in doors)/len(doors)-l['center'][1])<1,'Entrance moved away from east centreline'
gate=objects['south-gate'];g=next(l for l in catalog if l['id']=='south-gate');x,y=g['center'];z=g['elevation']
bvh=BVHTree.FromPolygons([v.co for v in gate.data.vertices],[p.vertices for p in gate.data.polygons])
scale=(g['bounds'][2]-g['bounds'][0])/66.65
xs=[v.co.x for v in gate.data.vertices]
assert abs(min(xs)-g['bounds'][0])<.2 and abs(max(xs)-g['bounds'][2])<.2,'Gate no longer fits mapped width'
def hit(dx,height):return bvh.ray_cast(Vector((x+dx*scale,y-6,z+height*scale)),Vector((0,1,0)),12)[0]
for dx in [-23.5,0,23.5]:assert hit(dx,5) is None,f'Portal {dx} is obstructed'
for dx in [-31,-16,16,31]:assert hit(dx,5) is not None,f'Missing pier {dx}'
assert hit(0,13) is not None,'Missing main lintel'
assert hit(-23.5,9) is not None and hit(23.5,9) is not None,'Missing side lintels'
assert len(gate.vertex_groups)>=11,'Editable architectural parts are missing'
red=[p for p in gate.data.polygons if gate.data.materials[p.material_index].name=='gateRed']
assert len(red)>100,'Inscription is not geometric lettering'
report={'huixueFront':'east','huixueDoorVertices':len(doors),'gateOpenPassages':3,'gatePiers':4,'gateEditableGroups':len(gate.vertex_groups),'gateVertices':len(gate.data.vertices),'gateFaces':len(gate.data.polygons),'gateInscriptionFaces':len(red),'checks':'passed'}
(ROOT/'docs/model-checks/geometry-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report),flush=True)
