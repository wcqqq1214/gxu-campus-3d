"""Wall recolouring must not move geometry; grid glazing must face out in both LODs."""
import math,sys,copy
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from geometry import Mesh
from facade_finish import apply_wall_finish
from facade_windows import add_grid_windows,add_grid_pilasters
checks=0
for angle in (0,.61):
 rot=lambda p:[p[0]*math.cos(angle)-p[1]*math.sin(angle),p[0]*math.sin(angle)+p[1]*math.cos(angle)]
 for reverse in (False,True):
  ring=list(map(rot,[[0,0],[10,0],[10,10],[0,10],[0,0]]));a,c=ring[:2]
  f=dict(start=c if reverse else a,end=a if reverse else c,normal=rot([0,-1]),height=10.8,levels=3,rule=dict(windowGrid=dict(columns=3,firstLevel=0,edgeInset=.55,widthRatio=.5,heightRatio=.4,pilasterWidth=0,pilasterDepth=0,paneRows=1)))
  m=Mesh();m.extrude([[ring]],[[0,1,2,0,2,3]],-.5,11.3,0,1);before=copy.deepcopy((m.v,m.f,m.m));apply_wall_finish(m,f,0,2)
  assert (m.v,m.f)==before[:2] and sum(x!=y for x,y in zip(before[2],m.m))==1;checks+=1
  normal=Vector((*f['normal'],0));u=Vector((f['end'][0]-f['start'][0],f['end'][1]-f['start'][1],0)).normalized();start=Vector((*f['start'],0))
  for detail in (False,True):
   windows=Mesh();add_grid_pilasters(windows,f,0,{'white':2,'glass':3});assert not windows.f;checks+=1
   add_grid_windows(windows,f,0,{'white':2,'glass':3},detail);tree=BVHTree.FromPolygons(windows.v,windows.f)
   for level in range(3):
    for col in range(3):
     p=start+u*(.55+(col+.5)*8.9/3+.3)+Vector((0,0,(level+.56)*3.6+.2))
     hit,n,i,d=tree.ray_cast(p+normal*.7,-normal,1)
     assert hit is not None and windows.m[i]==3 and n.dot(normal)>.999
     assert abs((hit-p).dot(normal)-(.25 if detail else .07))<1e-5
     checks+=1
print('PASS wall finishes and grid normals:',checks,'checks')
