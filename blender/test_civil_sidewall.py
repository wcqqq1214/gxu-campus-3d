"""Generated base/near side wall excludes intersecting default windows."""
import sys,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from generic_buildings import ordinary_building
from roof_crown import side_wall_blocks_window
root=Path(__file__).resolve().parents[1]
b=next(b for b in json.loads((root/'public/data/buildings.json').read_text()) if b['id']=='relation/12875606')
c=b['form']['roofCrown'];a=Vector((*c['corner'],0));v=Vector((*c['v'],0));n=Vector((v.y,-v.x,0))
C={name:i for i,name in enumerate(['stone','white','glass','shadeGlass','paleRoof','dark','pink','red'])}
# Sample coordinates are independent of the clipping implementation.
for detail in (False,True):
 m=ordinary_building(b,0,C,detail);tree=BVHTree.FromPolygons(m.v,m.f)
 for depth,h in [(6.334,1.848),(6.334,11.748),(10.557,1.848),(10.557,8.448)]:
  hit=tree.ray_cast(a+v*depth+n*.7+Vector((0,0,h)),-n,1)
  assert hit[0] and m.m[hit[2]]==C['white'] and abs((hit[0]-a).dot(n)-.08)<.001,(detail,depth,h,hit)
 _,start,end=next(p for p in m.parts if p[0]=='04_立面窗格')
 east_windows=[]
 for face,material in zip(m.f,m.m):
  if material not in (C['glass'],C['shadeGlass']) or not all(start<=i<end for i in face):continue
  pts=[Vector(m.v[i]) for i in face];center=sum(pts,Vector())/len(pts)
  if abs((center-a).dot(n))>.3:continue
  d=(center-a).dot(v)
  if 14<d<16:east_windows.append(center.z)
 assert east_windows,(detail,'unaffected east windows disappeared')
 assert min(east_windows)<3 and max(east_windows)>24,(detail,east_windows)
for depth,height,expected in [(6,12,True),(15,12,False),(6,36,False),(2,12,False)]:
 p=a+v*depth+n*.07
 assert side_wall_blocks_window(c,p.x,p.y,n.x,n.y,2.4,height-1,height+1)==expected
p=a+v*6+n*.07
assert not side_wall_blocks_window(c,p.x,p.y,-n.x,-n.y,2.4,11,13)
print('PASS both LODs: continuous white wall, no protruding covered windows, unaffected rows retained')
