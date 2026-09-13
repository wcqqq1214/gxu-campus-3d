"""Check flat apron, lower-only grading, exterior preservation and rotations."""
import math,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from geometry import Mesh
from entry_apron import build_entry_apron
from site_geometry import mesh_triangles
for angle in (0,math.pi/2,.543):
 c,s=math.cos(angle),math.sin(angle)
 def world(x,y):return x*c-y*s,x*s+y*c
 def original(x,y):return 1+.02*x+.01*y
 terrain=Mesh();terrain.face([(x,y,original(x,y)) for x,y in [(-20,-20),(20,-20),(20,20),(-20,20)]],0)
 extent=[world(x,y) for x,y in [(-5.1,0),(5.1,0),(5.1,4.62),(-5.1,4.62)]]
 site=dict(id='test',angle=angle,origin=[0,0],buildingCenter=[0,0],stairBaseHeight=.04,groundClearance=.12,halfWidth=3.1,startY=1.22,endY=2.62,gradingFeather=2,meshStep=.5,material='path',gradingBounds=[min(p[0] for p in extent),min(p[1] for p in extent),max(p[0] for p in extent),max(p[1] for p in extent)])
 result,_,meshes,_=build_entry_apron(site,{'grass':0,'path':1},lambda x,y:0,terrain,Mesh())
 tree=BVHTree.FromPolygons(result.v,[ids for ids,_ in mesh_triangles(result)],all_triangles=True)
 def height(x,y):return tree.ray_cast(Vector((*world(x,y),10)),Vector((0,0,-1)),20)[0].z
 for x in (-2.8,0,2.8):
  for y in (.45,1.06,2):assert abs(height(x,y)+.08)<1e-4,('buried entry/apron',angle,x,y,height(x,y))
 for x,y in [(-6,1),(6,1),(0,5),(0,-1),(-5.1,2),(5.1,2),(0,4.62)]:
  assert abs(height(x,y)-original(*world(x,y)))<1e-4,('outside changed',angle,x,y)
 for x in range(-6,7):
  for i in range(12):
   y=i*.5
   assert height(x,y)<=original(*world(x,y))+1e-4,'terrain raised'
 mesh=meshes['site-test'];apron=BVHTree.FromPolygons(mesh.v,mesh.f)
 for x in (-2.8,0,2.8):
  h=apron.ray_cast(Vector((*world(x,2),10)),Vector((0,0,-1)),20)[0].z
  assert abs(h-.04)<1e-4,'apron surface height'
site.update(startY=0,endY=1,gradingStartY=-1.8,gradingBounds=[-5.1,-1.8,5.1,3],angle=0)
terrain=Mesh();terrain.face([(-20,-20,1),(20,-20,1),(20,20,1),(-20,20,1)],0)
result,_,_,_=build_entry_apron(site,{'grass':0,'path':1},lambda x,y:0,terrain,Mesh())
tree=BVHTree.FromPolygons(result.v,[ids for ids,_ in mesh_triangles(result)],all_triangles=True)
for x in (-2.8,0,2.8):
 for y in (-1.6,-.9,-.2,.2,.8):
  h=tree.ray_cast(Vector((x,y,10)),Vector((0,0,-1)),20)[0].z
  assert abs(h+.08)<1e-4,'gallery floor buried'
print('Passed apron and terrain at 0/90/31.11 degrees; exact exterior planes and lower-only field')
