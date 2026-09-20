"""Probe circular glazing, square-corner exclusion and radial reveals after rotation."""
import sys,json,copy,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from geometry import Mesh
from facade_panels import add_panels
from facade_bands import frame
b=next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']=='relation/12875606')
f=next(f for f in b['form']['facades'] if 'roundWindowWalls' in f)
C={'white':0,'glass':1};checks=0
for angle in (0,.61):
 for reverse in (False,True):
  facade=copy.deepcopy(f);length=math.dist(f['start'],f['end']);u=(math.cos(angle),math.sin(angle));n=(-u[1],u[0])
  facade['start']=[0,0];facade['end']=[length*v for v in u];facade['normal']=n
  if reverse:facade['start'],facade['end']=facade['end'],facade['start']
  mesh=Mesh();add_panels(mesh,facade,0,C);tree=BVHTree.FromPolygons(mesh.v,mesh.f)
  length,u,n,_,point=frame(facade);u=Vector((*u,0));n=Vector((*n,0));p=facade['rule']['panels'][0]
  w=(p['to']-p['from'])*length
  for opening in p['openings']:
   x,y=point(p['from']+opening['t']*w/length,0);center=Vector((x,y,opening['height']))
   for dx,dh,material,depth in [(0,0,1,.04),(.4,0,1,.04),(0,.4,1,.04),(.45,.45,0,.15),(.65,0,0,.15),(0,.65,0,.15)]:
    q,normal,index,_=tree.ray_cast(center+u*dx+Vector((0,0,dh))+n*.5,-n,1)
    assert q is not None and mesh.m[index]==material and abs((q-center).dot(n)-depth)<1e-5 and normal.dot(n)>.999,(angle,reverse,dx,dh,q,normal)
    checks+=1
   for theta in [math.tau*(i+.5)/32 for i in range(0,32,4)]:
    radial=u*math.cos(theta)+Vector((0,0,math.sin(theta)))
    q,normal,index,distance=tree.ray_cast(center+n*.1,radial,1)
    assert q is not None and mesh.m[index]==0 and abs(distance-.55*math.cos(math.pi/32))<1e-5 and normal.dot(radial)<-.999,(angle,reverse,theta,q,normal)
    checks+=1
print('PASS round windows:',checks,'checks; both facade directions and rotations')
