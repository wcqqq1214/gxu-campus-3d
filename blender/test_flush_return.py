"""Check the new portal return before the full campus export."""
import sys,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from generic_buildings import ordinary_building
root=Path(__file__).resolve().parents[1]
b=next(b for b in json.loads((root/'public/data/buildings.json').read_text()) if b['id']=='relation/12875606')
r=b['form']['entrances'][0]['flushEntrance']['returnGlazing'];a=Vector((*r['corner'],0));v=Vector((*r['tangent'],0));n=Vector((*r['normal'],0))
C={name:i for i,name in enumerate(['stone','white','glass','shadeGlass','paleRoof','dark','pink','red'])}
for detail in (False,True):
 m=ordinary_building(b,0,C,detail);tree=BVHTree.FromPolygons(m.v,m.f)
 for d,h,material,projection in [(.7,1.5,'glass',.08),(2.5,5.3,'glass',.08),(.3,1.5,'stone',.27),(1.9,5.3,'stone',.27),(.7,3.6,'stone',.27),(1,1.5,'white',.14)]:
  hit=tree.ray_cast(a+v*d+n*.7+Vector((0,0,h)),-n,1)
  assert hit[0] and m.m[hit[2]]==C[material] and abs((hit[0]-a).dot(n)-projection)<.002 and hit[1].dot(n)>.999,(detail,d,h,material,hit)
 for h,direction,expected in [(8.8,-1,7.8),(6.2,1,7.2)]:
  hit=tree.ray_cast(a+v*2+n*.8+Vector((0,0,h)),Vector((0,0,direction)),2)
  assert hit[0] and abs(hit[0].z-expected)<.001 and hit[1].z*direction<-.999,(detail,'canopy',hit)
print('PASS both LODs: return glass/piers/beam and canopy top/underside normals')
