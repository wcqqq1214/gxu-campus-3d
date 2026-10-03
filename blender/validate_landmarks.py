"""Geometric regression checks against the saved source, not just catalogue flags."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'blender'))
from south_gate_site import CROSSING_CENTRES, REPAIR_BOUNDS, SITE, ground
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
architecture={g.index for g in gate.vertex_groups if g.name.startswith(('门柱','中央门','西侧门','东侧门'))}
xs=[v.co.x for v in gate.data.vertices if any(g.group in architecture for g in v.groups)]
assert abs(min(xs)-g['bounds'][0])<.2 and abs(max(xs)-g['bounds'][2])<.2,'Gate no longer fits mapped width'
def hit(dx,height):return bvh.ray_cast(Vector((x+dx*scale,y-6,z+height*scale)),Vector((0,1,0)),12)[0]
for dx in [-23.5,0,23.5]:assert hit(dx,5) is None,f'Portal {dx} is obstructed'
for dx in [-31,-16,16,31]:assert hit(dx,5) is not None,f'Missing pier {dx}'
assert hit(0,13) is not None,'Missing main lintel'
assert hit(-23.5,9) is not None and hit(23.5,9) is not None,'Missing side lintels'
assert len(gate.vertex_groups)>=11,'Editable architectural parts are missing'
red=[p for p in gate.data.polygons if gate.data.materials[p.material_index].name=='gateRed']
assert len(red)>100,'Inscription is not geometric lettering'
# Equal front/rear pairs are user-confirmed, not inferred from perspective.
depth_scale=(g['bounds'][3]-g['bounds'][1])/5.3
def gate_point(dx,dy,height):
    return Vector(((g['bounds'][0]+g['bounds'][2])/2+dx*scale,
                   (g['bounds'][1]+g['bounds'][3])/2+dy*depth_scale,z+.45+height*scale))
lantern_openings=0
height_differences=[];pair_dimensions=[]
for i,px in enumerate([-31,-16,16,31]):
    high=abs(px)==16;ph=16.0 if high else 11.4;tops=[];dimensions=[]
    for sy in [-1,1]:
        size=1.18 if high else .94
        height=ph+.20+1.40*size
        for axis in ['x','y']:
            a=gate_point(px-size if axis=='x' else px,sy*1.20-size*scale/depth_scale if axis=='y' else sy*1.20,height)
            b=gate_point(px+size if axis=='x' else px,sy*1.20+size*scale/depth_scale if axis=='y' else sy*1.20,height)
            assert bvh.ray_cast(a,(b-a).normalized(),(b-a).length)[0] is None,('Blocked lantern arch',px,sy,axis)
            shoulder=Vector((0,.25*size*scale,0)) if axis=='x' else Vector((.25*size*scale,0,0))
            assert bvh.ray_cast(a+shoulder,(b-a).normalized(),(b-a).length)[0] is not None,('Missing curved arch shoulder',px,sy,axis)
            lantern_openings+=2
        top=bvh.ray_cast(gate_point(px,sy*1.20,ph+4),Vector((0,0,-1)),4*scale)[0]
        assert top is not None,('Missing lantern roof',px,sy)
        tops.append(top.z)
        group=gate.vertex_groups[f'小亭-{i+1:02}-'+('前' if sy<0 else '后')].index
        vs=[v.co for v in gate.data.vertices if any(g.group==group for g in v.groups)]
        assert vs,('Missing pavilion geometry',px,sy)
        dimensions.append([max(v[k] for v in vs)-min(v[k] for v in vs) for k in range(3)])
    assert abs(tops[0]-tops[1])<.001,('Unequal paired roof elevations',px,tops)
    assert all(abs(a-b)<.001 for a,b in zip(*dimensions)),('Unequal paired pavilion dimensions',px,dimensions)
    pair_dimensions.append([[round(v,4) for v in d] for d in dimensions])
    height_differences.append(round(tops[0]-tops[1],3))
# The display is placed on paving in world metres, independently of gate scale.
site_group=next(group.index for group in gate.vertex_groups if group.name.startswith('门前盆栽'))
site_vertices=[v.co for v in gate.data.vertices if any(item.group==site_group for item in v.groups)]
assert site_vertices
assert min(v.y for v in site_vertices)>y-40 and max(v.y for v in site_vertices)<y-30
assert min(v.x for v in site_vertices)>x-6 and max(v.x for v in site_vertices)<x+3
# Road-level clearance: cast down inside each lane and the open photo apron.
road=bpy.data.objects['roads']
rays=BVHTree.FromPolygons([v.co for v in road.data.vertices],[p.vertices for p in road.data.polygons])
for dx,dy in [(-6,-16),(3,-16),(-10,-34),(6,-34),(-4,0),(4,0)]:
    p,n,index,_=rays.ray_cast(Vector((x+dx,y+dy,15)),Vector((0,0,-1)),30)
    assert p is not None and road.data.materials[road.data.polygons[index].material_index].name=='asphalt',('Lane interrupted',dx,dy)
    obstacle=bvh.ray_cast(Vector((x+dx,y+dy,p.z+2)),Vector((0,0,-1)),1.8)[0]
    assert obstacle is None,('Pot or railing obstructs lane',dx,dy)
for dx in [-3.5,-1.5,.5]:
    p,n,index,_=bvh.ray_cast(Vector((x+dx,y-42,10)),Vector((0,0,-1)),20)
    assert p is not None and gate.data.materials[gate.data.polygons[index].material_index].name.startswith('gatePaving'),('Photo apron blocked',dx)
# Every terracotta pot must sit on the stone island (check its bottom cap).
island_group=next(group.index for group in gate.vertex_groups if group.name.startswith('门前铺装'))
island_indices={v.index for v in gate.data.vertices if any(item.group==island_group for item in v.groups)}
island_faces=[tuple(p.vertices) for p in gate.data.polygons if all(i in island_indices for i in p.vertices)]
island_bvh=BVHTree.FromPolygons([v.co for v in gate.data.vertices],island_faces)
# The rounded nose must finish before the street, rather than extend as a strip.
for dx,dy,expected in [(-1.5,-44,True),(-4,-42,True),(3,-42,False),(-1.5,-47,False),(0,-15,False)]:
    p=island_bvh.ray_cast(Vector((x+dx,y+dy,10)),Vector((0,0,-1)),20)[0]
    assert (p is not None)==expected,('Wrong rounded island footprint',dx,dy)
# Read the saved mesh: all three lamps sit below the ceiling and above traffic.
lamp_bottoms=[]
for dx in [-9.2,0,9.2]:
    origin=gate_point(dx,0,5)
    p=bvh.ray_cast(origin,Vector((0,0,1)),10*scale)[0]
    assert p is not None and z+.45+9.7*scale<p.z<z+.45+10.6*scale,('Missing or low drum lamp',dx,p)
    lamp_bottoms.append(round(p.z,4))
pot_bottoms={}
for p in gate.data.polygons:
    if gate.data.materials[p.material_index].name!='gatePot':continue
    vs=[gate.data.vertices[i].co for i in p.vertices]
    if max(v.z for v in vs)-min(v.z for v in vs)>1e-6:continue
    c=sum(vs,Vector())/len(vs);key=(round(c.x,2),round(c.y,2))
    if key not in pot_bottoms or c.z<pot_bottoms[key].z:pot_bottoms[key]=c
pot_gaps=[]
for c in pot_bottoms.values():
    p=island_bvh.ray_cast(c+Vector((0,0,1)),Vector((0,0,-1)),2)[0]
    assert p is not None,('Pot outside the paved island',tuple(c))
    gap=c.z-p.z;pot_gaps.append(gap)
    assert -.035<gap<.035,('Pot floats or sinks into paving',tuple(c),gap)
# The broad intersection must be continuous asphalt where the former two
# centreline ribbons left a false grass median. Check independent interior points.
for dx,dy in [(-1,-65),(-12,-70),(-25,-65),(18,-67),(29,-70)]:
    p,_,index,_=rays.ray_cast(Vector((x+dx,y+dy,15)),Vector((0,0,-1)),30)
    assert p is not None and road.data.materials[road.data.polygons[index].material_index].name=='asphalt',('False island in junction',dx,dy)
# The true median tip south of the crossing must remain outside the traced road.
# New northern join is checked across the original road surface.
max_seam=0
for xx in [-6,-3,0,3]:
    heights=[]
    for delta in [-.005,.005]:
        p=rays.ray_cast(Vector((x+xx,y+REPAIR_BOUNDS[3]+delta,15)),Vector((0,0,-1)),30)[0]
        assert p is not None,('Road seam has a hole',xx)
        heights.append(p.z)
    max_seam=max(max_seam,abs(heights[0]-heights[1]))
assert max_seam<.035,('Road seam step',max_seam)
# Read back the saved crossing paint and asphalt gaps along its oblique extent.
crossing_hits=[]
for dx,dy in CROSSING_CENTRES:
    p,_,index,_=rays.ray_cast(Vector((x+dx,y+dy,15)),Vector((0,0,-1)),30)
    assert p is not None and road.data.materials[road.data.polygons[index].material_index].name=='roadWhite',('Missing crossing stripe',dx,dy)
    crossing_hits.append(p)
    assert bvh.ray_cast(Vector((x+dx,y+dy,p.z+2)),Vector((0,0,-1)),1.9)[0] is None,('Crossing obstructed',dx,dy)
for dx,dy in SITE['crossingGapCenters']:
    p,_,index,_=rays.ray_cast(Vector((x+dx,y+dy,15)),Vector((0,0,-1)),30)
    assert p is not None and road.data.materials[road.data.polygons[index].material_index].name=='asphalt',('Crossing gap not asphalt',dx,dy)
# Its right end must lie farther south; do not regress to a horizontal strip.
left=[v.y for v in crossing_hits if v.x<x-14];right=[v.y for v in crossing_hits if v.x>x+9]
assert left and right and sum(left)/len(left)-sum(right)/len(right)>8,'Crossing lost its diagonal alignment'
# Previously installed barriers stood at y - 5.6 across these two approaches.
for side in [-1,1]:
    for dx in [10.3+i*.5 for i in range(18)]:
        px=x+side*dx;py=y-5.6
        assert bvh.ray_cast(Vector((px,py,ground(px,py)+2)),Vector((0,0,-1)),1.7)[0] is None,('Side-gate barrier remains',side,dx)
report={'huixueFront':'east','huixueDoorVertices':len(doors),'gateOpenPassages':3,'gatePiers':4,'gateEditableGroups':len(gate.vertex_groups),'gateVertices':len(gate.data.vertices),'gateFaces':len(gate.data.polygons),'gateInscriptionFaces':len(red),'gateLanternOpenings':lantern_openings,'frontRearLanternHeightDifferencesMeters':height_differences,'checks':'passed'}
report['pottedDisplayOnPavedIsland']=True
report['pairedLanternDimensionsMeters']=pair_dimensions
report['drumLampBottomElevationsMeters']=lamp_bottoms
report['roundedIslandNose']=True
report['crosswalkStripes']=len(CROSSING_CENTRES)
report['siteImageryCapturedAt']=SITE['capturedAt']
report['continuousStreetJunction']=True
report['sideGateApproachesWithoutBarriers']=True
report['potsOnPaving']=len(pot_bottoms)
report['maximumPotGapMeters']=round(max(abs(g) for g in pot_gaps),4)
report['maximumRoadSeamMeters']=round(max_seam,4)
report['clearApproachLanes']=6
report['openPhotoApron']=True
(ROOT/'docs/model-checks/geometry-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report),flush=True)
