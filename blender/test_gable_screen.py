"""Probe the opening, curved shoulders, closure and face winding after rotation."""
import sys,json,copy,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from geometry import Mesh
from gable_screen import add_gable_screen
from site_geometry import mesh_triangles
c=next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']=='relation/12875606')['form']['gableScreen']
for angle in (0,.71):
 g=copy.deepcopy(c)
 for key in ('start','end','tangent','normal'):
  x,y=g[key];g[key]=[x*math.cos(angle)-y*math.sin(angle),x*math.sin(angle)+y*math.cos(angle)]
 m=Mesh();add_gable_screen(m,g,0,dict(white=0,dark=1,glass=2))
 triangles=mesh_triangles(m);tree=BVHTree.FromPolygons(m.v,[t for t,_ in triangles],all_triangles=True)
 a,u,n=g['start'],g['tangent'],g['normal'];length=g['length'];base=g['baseHeight']
 def point(s,d,h):return Vector((a[0]+u[0]*s+n[0]*d,a[1]+u[1]*s+n[1]*d,base+h))
 def ray(s,h,material,depth,reverse=False):
  start=point(s,-.7 if reverse else .7,h);direction=Vector((*n,0))*(1 if reverse else -1)
  hit,normal,index,distance=tree.ray_cast(start,direction,1.5)
  assert hit is not None,(s,h)
  assert m.m[triangles[index][1]]==material,(s,h,material,m.m[triangles[index][1]])
  assert abs((hit-point(s,0,h)).dot(Vector((*n,0)))-depth)<.0002
  assert normal.dot(Vector((*n,0)))*(-1 if reverse else 1)>.99
 for s in (length*.2,length*.8):
  ray(s,1.2,0,0);ray(s,1.2,0,-.3,True)
 ray(length/2+.2,1.0,2,-.08);ray(length/2+.2,1.0,2,-.10,True)
 ray(length/2+.86,1.0,1,.015)
 ray(length/2+.8,2.2,0,0)  # above the curved edge, inside a rectangular cutout
 ray(length/2+.2,2.2,2,-.08)
 for fraction,expected in ((.25,2.2),(.5,3.6),(.75,2.2)):
  hit,normal,_,_=tree.ray_cast(point(length*fraction,-.15,5),Vector((0,0,-1)),6)
  assert hit is not None and abs(hit.z-base-expected)<.0002 and normal.z>0
 assert tree.ray_cast(point(length*.25,.7,2.4),Vector((-n[0],-n[1],0)),1.5)[0] is None
print('Gable screen: real arched opening, inset pane, frame, profile/closure and both face normals pass at two rotations',flush=True)
