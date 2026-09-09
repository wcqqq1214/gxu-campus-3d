"""Validate saved geometry: real open library court and distinct architectural parts."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'))
bs=json.loads((ROOT/'public/data/buildings.json').read_text())
trees=json.loads((ROOT/'public/data/vegetation.json').read_text())
instances=[o for o in bpy.context.scene.objects if o.name.startswith('树木示意-')]
assert len(instances)==len(trees)
assert {(round(o.location.x,1),round(o.location.y,1)) for o in instances}=={(t[0],t[1]) for t in trees}
results={}
for key in ['library','international-residence']:
    o=next(o for o in bpy.context.scene.objects if o.get('landmark')==key)
    b=next(b for b in bs if b['landmark']==key);e=b['architecture'];groups=[g.name for g in o.vertex_groups]
    assert len(groups)==(12 if key=='library' else 8),(key,groups)
    assert len(o.data.vertices)>15000,(key,len(o.data.vertices))
    assert all(math.isfinite(v) for p in o.data.vertices for v in p.co)
    def ray(x,y):
        a=e['angle'];ox,oy=e['origin'];p=Vector((ox+x*math.cos(a)-y*math.sin(a),oy+x*math.sin(a)+y*math.cos(a),b['elevation']+150))
        hit,location,normal,face=o.ray_cast(p,Vector((0,0,-1)))
        return hit,float(location.z)-b['elevation']
    if key=='library':
        # Actual mapped inner ring has no roof spanning these sample locations.
        for x,y in [(0,-4),(5,-4),(0,-9),(8,-9)]:assert not ray(x,y)[0],('Courtyard filled',x,y)
        assert ray(-44,-15)[0] and ray(0,-30)[0] and ray(0,18)[0]
        assert ray(0,18)[1]>ray(0,-30)[1]+5
        assert 9.8<ray(0,32)[1]<10.5,'North portico canopy missing'
        assert .1<ray(0,38.9)[1]<.4,'North stairs missing'
        assert 10<ray(0,-39)[1]<15,'South portico must remain'
        # Door group is north of the mapped wall and includes six exact-size panes.
        gi=o.vertex_groups['10_北门感应玻璃门'].index
        vi={v.index for v in o.data.vertices if any(g.group==gi for g in v.groups)}
        glass_faces=[p for p in o.data.polygons if all(v in vi for v in p.vertices) and o.data.materials[p.material_index].name=='libraryGlass']
        assert len(glass_faces)==36,'Six closed glass-pane boxes expected'
        a=e['angle'];ox,oy=e['origin']
        def local(v):
            p=o.data.vertices[v].co;dx=p.x-ox;dy=p.y-oy
            return (dx*math.cos(a)+dy*math.sin(a),-dx*math.sin(a)+dy*math.cos(a),p.z-b['elevation'])
        for start in range(0,36,6):
            pts=[local(v) for face in glass_faces[start:start+6] for v in face.vertices]
            assert abs(max(p[0] for p in pts)-min(p[0] for p in pts)-1)<.001
            assert abs(max(p[2] for p in pts)-min(p[2] for p in pts)-2.25)<.001
            assert min(p[1] for p in pts)>27.3,'Door must face out of north wall'

    else:
        assert ray(-23,-10)[1]>78 and ray(4,16)[1]>78
        assert 12<ray(8,-14)[1]<16,'Recess above academic podium must remain open'
    results[key]={'vertices':len(o.data.vertices),'faces':len(o.data.polygons),'parts':groups,'passed':True}
(ROOT/'docs/model-checks/architecture-check.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(results,ensure_ascii=False),flush=True)
