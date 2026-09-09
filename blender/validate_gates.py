"""Ray-test actual edited source geometry in compass coordinates."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'))
landmarks=json.loads((ROOT/'public/data/landmarks.json').read_text());report={}
for l in landmarks:
    if l.get('placeKind')!='gate':continue
    matches=[o for o in bpy.context.scene.objects if o.get('landmark')==l['id']]
    assert len(matches)==1,(l['id'],'duplicate/missing source object')
    o=matches[0];a=math.radians(180-l['frontBearing']);cx,cy=l['center'];z=l['elevation']+.24
    def world(x,y,h):
        if l['id']=='east-gate':x*=l['gateWidth']/35;h*=l['height']/11
        return Vector((cx+x*math.cos(a)-y*math.sin(a),cy+x*math.sin(a)+y*math.cos(a),z+h))
    def hit(x,h):
        start=world(x,-7,h);end=world(x,7,h)
        return o.ray_cast(start,(end-start).normalized(),distance=14)[0]
    for x in ([0,-12,12] if l['id']=='east-gate' else [0]):assert not hit(x,2.5),(l['id'],'blocked passage',x)
    if l['id']=='east-gate':
        for x in [-16,-8,8,16]:assert hit(x,3),(l['id'],'missing pier',x)
        assert hit(0,9.8),'missing east entablature'
    assert len(o.vertex_groups)>=4
    report[l['id']]={'passagesClear':True,'frontBearing':l['frontBearing'],'vertices':len(o.data.vertices),
                     'faces':len(o.data.polygons),'editableGroups':[g.name for g in o.vertex_groups],
                     'appearance':'provisional' if l['id']=='new-east-gate' else 'photo-based, estimated dimensions'}
(ROOT/'docs/model-checks/gates-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
