"""Known-volume fixtures for the actual source/decoded mesh audit primitive."""
import sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'blender'))
from tree_mesh_audit import check_meshes


def mesh(vertices,triangles):
    vertices=[Vector(v) for v in vertices]
    bounds=tuple(tuple(fn(v[k] for v in vertices) for k in range(3)) for fn in (min,max))
    return vertices,triangles,bounds


def cube(lo,hi):
    x,y,z=lo;X,Y,Z=hi
    vertices=[(x,y,z),(X,y,z),(X,Y,z),(x,Y,z),(x,y,Z),(X,y,Z),(X,Y,Z),(x,Y,Z)]
    triangles=[(0,2,1),(0,3,2),(4,5,6),(4,6,7),(0,1,5),(0,5,4),
               (1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)]
    return mesh(vertices,triangles)


tree=cube((-1,-1,2),(1,1,4))
rows=[[0,0,9,0,0]]
templates={'base':{0:tree},'near':{0:tree}}
road=mesh([(-5,-5,0),(5,-5,0),(5,5,0),(-5,5,0)],[(0,1,2),(0,2,3)])
assert check_meshes(rows,[('road',road)],templates)['passed'], 'High canopy over pavement is not an intersection'

wall=mesh([(0,-2,1),(0,2,1),(0,2,5),(0,-2,5)],[(0,1,2),(0,2,3)])
result=check_meshes(rows,[('pier',wall)],templates)
assert len(result['collisions'])==2 and all(h['collisionKind']=='surface-intersection' for h in result['collisions'])

enclosing=cube((-3,-3,0),(3,3,6))
contained=cube((-.2,-.2,2.5),(.2,.2,3.5))
forward=check_meshes(rows,[('enclosing',enclosing)],templates)
assert len(forward['collisions'])==2 and all(h['collisionKind']=='tree-component-inside-building' for h in forward['collisions'])
inverse=check_meshes(rows,[('lamp',contained)],templates)
assert len(inverse['collisions'])==2 and all(h['collisionKind']=='building-component-inside-tree' for h in inverse['collisions'])

other=cube((-1,-1,7),(1,1,9))
result=check_meshes(rows,[('pier',wall)],{'base':{0:tree},'near':{0:other}})
assert len(result['collisions'])==1 and result['collisions'][0]['treeLOD']=='base'

row=[300,-500,18,0,5]
enclosing=cube((290,-510,5),(310,-490,20))
result=check_meshes([row],[('translated',enclosing)],templates)
assert len(result['collisions'])==2
assert all(290<h['containmentWitness'][0]<310 and -510<h['containmentWitness'][1]<-490 and 5<h['containmentWitness'][2]<20 for h in result['collisions'])
print('5 site-tree audit groups passed',flush=True)
