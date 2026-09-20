"""Ray-test folded courtyard slabs/rails, cap closure and untouched roof in both LODs."""
import sys,math,copy
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from generic_buildings import ordinary_building
C={n:i for i,n in enumerate(['stone','pink','white','glass','dark','shadeGlass','paleRoof','red'])}
outer=[[0,0],[30,0],[30,20],[0,20],[0,0]]
hole=[[5,5],[25,5],[25,15],[5,15],[5,5]]
tri=[0,1,5,0,5,4,1,2,6,1,6,5,2,3,7,2,7,6,3,0,4,3,4,7]
profile=[[0,0],[.2,0],[.3,.4],[.7,.4],[.8,0],[1,0]]
checks=0
for angle in (0,.61):
 rot=lambda p:[p[0]*math.cos(angle)-p[1]*math.sin(angle),p[0]*math.sin(angle)+p[1]*math.cos(angle)]
 for reverse in (False,True):
  ring=list(reversed(hole)) if reverse else hole
  indices=[{4:4,5:7,6:6,7:5}.get(i,i) for i in tri] if reverse else tri
  f={'part':'body','polygon':0,'ring':1,'edge':3 if reverse else 0,'start':rot([25,5] if reverse else [5,5]),'end':rot([5,5] if reverse else [25,5]),'normal':rot([0,1]),'height':26.4,'levels':8,'rule':{'windows':False,'balconies':False,'openCorridor':{'depth':1.6,'firstLevel':1,'endInset':.4,'railHeight':.95,'frontProfile':profile}}}
  b={'id':'fixture','name':'fixture','category':'academic','tags':{},'polygons':[[list(map(rot,outer)),list(map(rot,ring))]],'roofTriangles':[indices],'form':{'version':1,'height':26.4,'levels':8,'archetype':'generic','parts':[],'roof':{'type':'flat','rise':0},'entrances':[],'facades':[f]}}
  a=Vector((*rot([5,5]),0));u=Vector((*rot([1,0]),0));n=Vector((*rot([0,1]),0))
  point=lambda t,d,h:a+u*t-n*d+Vector((0,0,h))
  for detail in (False,True):
   m=ordinary_building(b,0,C,detail);tree=BVHTree.FromPolygons(m.v,m.f)
   def hit(t,d,h,direction,limit=3):return tree.ray_cast(point(t,d,h),direction,limit)
   for fraction,depth in [(.1,0),(.25,.2),(.5,.4),(.75,.2),(.9,0)]:
    t=.4+19.2*fraction
    for level in (1,4,7):
     floor=level*3.3
     p,normal,i,_=hit(t,-.5,floor+.5,-n)
     assert p is not None and abs((p-a).dot(n)+depth)<1e-5 and normal.dot(n)>.97,(angle,reverse,detail,'rail',p,normal)
     for h,dz,expected in [(floor+.3,-1,floor),(floor-.4,1,floor-.18)]:
      p,normal,i,_=hit(t,depth+.3,h,Vector((0,0,dz)))
      assert p is not None and abs(p.z-expected)<1e-5 and normal.z*dz<-.99,(angle,reverse,detail,'slab',p,expected)
     assert hit(t,-.05,floor+1.4,-n,.9)[0] is None,'Flush wall blocks the recessed gallery'
     checks+=4
   # First slab notch caps the retained ground floor; later notches stay open.
   p,normal,i,_=hit(10,.2,3.5,Vector((0,0,-1)),.6)
   assert p is not None and abs(p.z-3.12)<1e-5 and normal.z>.99
   assert hit(10,.2,6.8,Vector((0,0,-1)),.5)[0] is None
   # Straight roof slab/underside and original courtyard remain intact.
   p,normal,i,_=hit(10,.2,27,Vector((0,0,-1)))
   assert p is not None and abs(p.z-26.4)<1e-5 and normal.z>.99
   p,normal,i,_=hit(10,.2,26,Vector((0,0,1)),.4)
   assert p is not None and abs(p.z-26.22)<1e-5 and normal.z<-.99
   assert tree.ray_cast(Vector((*rot([15,10]),30)),Vector((0,0,-1)),31)[0] is None
   checks+=5
print('PASS profiled courtyard gallery:',checks,'checks; two LODs, both ring windings and rotated facade')
