"""Decode the shipped Draco GLB and verify paint survives quantization."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'public/models/base.glb'))
bpy.context.view_layer.update()
vertices=[];faces=[]
for obj in bpy.context.scene.objects:
    if obj.type!='MESH':continue
    parent=obj
    while parent and parent.get('layer')!='sports':parent=parent.parent
    if parent is None:continue
    offset=len(vertices)
    vertices.extend([obj.matrix_world@v.co for v in obj.data.vertices])
    faces.extend([tuple(i+offset for i in p.vertices) for p in obj.data.polygons])
assert vertices,'Exported sports layer missing'
bvh=BVHTree.FromPolygons(vertices,faces)
report=[]
for f in json.loads((ROOT/'public/data/sports.json').read_text()):
    c,s=math.cos(f['rotation']),math.sin(f['rotation']);cx,cy=f['center'];offsets=[]
    inner=f['outerRadius']-f['laneCount']*f['laneWidth']
    for lane in range(f['laneCount']+1):
        x=inner+lane*f['laneWidth']
        for y in [-18,18]:
            hit=bvh.ray_cast(Vector((cx+x*c-y*s,cy+x*s+y*c,100)),Vector((0,0,-1)),200)[0]
            assert hit is not None
            offset=hit.z-f['elevation']-.46
            assert .025<offset<.045,f"{f['id']} lane {lane}: paint collapsed into track ({offset})"
            offsets.append(offset)
    report.append({'id':f['id'],'decodedLaneSamples':len(offsets),'minimumPaintOffsetMeters':round(min(offsets),4),'maximumPaintOffsetMeters':round(max(offsets),4),'result':'passed'})
(ROOT/'docs/model-checks/sports-export-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report),flush=True)
