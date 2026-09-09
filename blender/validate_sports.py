"""Check saved sports geometry through ray casts, not catalogue flags alone."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'))
fields=json.loads((ROOT/'public/data/sports.json').read_text())
report=[]
for field in fields:
    obj=next(o for o in bpy.context.scene.objects if o.get('sportsId')==field['id'])
    bvh=BVHTree.FromPolygons([v.co for v in obj.data.vertices],[p.vertices for p in obj.data.polygons])
    cx,cy=field['center'];c=math.cos(field['rotation']);s=math.sin(field['rotation'])
    def hit(x,y):
        return bvh.ray_cast(Vector((cx+x*c-y*s,cy+x*s+y*c,100)),Vector((0,0,-1)),200)
    hits=[]
    for x in range(-28,29,4):
        for y in range(-46,47,4):
            loc,normal,index,distance=hit(x,y)
            assert loc is not None
            assert abs(loc.z-field['elevation']-.468)<.06,'Field obstructed or uneven'
            assert normal.z>.9,'Field face has wrong winding'
            hits.append(loc.z)
    inner=field['outerRadius']-field['laneCount']*field['laneWidth']
    for lane in range(field['laneCount']):
        radius=inner+(lane+.5)*field['laneWidth']
        for theta in [i*math.pi/24 for i in range(25)]:
            loc,normal,index,distance=hit(radius*math.cos(theta),field['straightHalfLength']+radius*math.sin(theta))
            assert loc is not None and abs(loc.z-field['elevation']-.46)<.015
    goalgroup=obj.vertex_groups['两端球门网架与角旗'].index
    goalvertices=[v.co for v in obj.data.vertices if any(g.group==goalgroup for g in v.groups)]
    assert max(v.z for v in goalvertices)-field['elevation']>2.9
    assert len(obj.vertex_groups)==6
    report.append({'id':field['id'],'sampledFieldRays':len(hits),'fieldSurfaceSpreadMeters':round(max(hits)-min(hits),4),'curvedLaneRays':200,'editableGroups':len(obj.vertex_groups),'vertices':len(obj.data.vertices),'faces':len(obj.data.polygons),'result':'passed'})
stand=next(o for o in bpy.context.scene.objects if o.get('featureId')=='way/948683815')
assert len(stand.vertex_groups)==3
(ROOT/'docs/model-checks/sports-geometry-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report),flush=True)
