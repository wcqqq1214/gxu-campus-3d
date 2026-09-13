"""Real facade regression, LOD-only intersection and harmless vertical overhang."""
import bpy, json, math, sys
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'blender'),str(ROOT/'scripts')]
from tree_clearance import filter_building_collisions
from vegetation_layout import tree_rotation


def template(world, row, name, faces=None):
    x,y,h,typ,z=row;scale=h/9;c=math.cos(tree_rotation(x,y));s=math.sin(tree_rotation(x,y))
    local=[((c*(a-x)+s*(b-y))/scale,(-s*(a-x)+c*(b-y))/scale,(v-z)/scale) for a,b,v in world]
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(local,[],faces or [(0,1,2)])
    return SimpleNamespace(data=mesh)


# Three actual triangle vertices from the pre-fix laboratory source intersection.
row=[-317.1,-926.9,16.5,0,3.413376]
witness={'treeTriangle':[[-311.76641845703125,-922.9832763671875,12.286910057067871],[-313.2596130371094,-922.0103759765625,10.88373851776123],[-313.12261962890625,-921.7911987304688,12.286910057067871]],
         'buildingTriangle':[[-312.2654113769531,-924.6655883789062,11.831000328063965],[-312.2654113769531,-922.5841674804688,11.831000328063965],[-312.2654113769531,-922.5841674804688,13.8015718460083]]}
obstacle=SimpleNamespace(v=witness['buildingTriangle'],f=[(0,1,2)])
near=template(witness['treeTriangle'],row,'real-laboratory-crown')
high_world=[(x,y,z+30) for x,y,z in witness['treeTriangle']]
above=template(high_world,row,'crown-above-roof')
mesh_count=len(bpy.data.meshes)
kept,report=filter_building_collisions([row],{'near':[near]},[('lab','near',obstacle)])
assert not kept and report['removed'][0]['buildingId']=='lab'
kept,report=filter_building_collisions([row],{'near':[above]},[('low-roof','base',obstacle)])
assert kept==[row], 'A projected overlap above the building is not a collision'
kept,report=filter_building_collisions([row],{'near':[above],'base':[near]},[('lab','near',obstacle)])
assert not kept and report['removed'][0]['treeLOD']=='base'
kept,report=filter_building_collisions([row],{'near':[near]},[('lab','base',obstacle)])
assert not kept and report['removed'][0]['buildingLOD']=='base'
survivor=[row[0]+100,row[1],row[2],row[3],row[4]]
rows=[row,survivor];original=json.loads(json.dumps(rows))
kept,_=filter_building_collisions(rows,{'near':[near]},[('lab','near',obstacle)])
assert kept==[survivor] and rows==original and kept[0] is survivor
again,_=filter_building_collisions(kept,{'near':[near]},[('lab','near',obstacle)])
assert again==kept
assert len(bpy.data.meshes)==mesh_count, 'Temporary triangulation meshes leaked'
print('5 tree-clearance cases passed: real facade, vertical separation, both LOD directions, stable survivor/idempotence',flush=True)

# Containment has no crossing triangles: a surface-only BVH check misses it.
from geometry import Mesh
row=[0,0,9,0,0]
room=Mesh();room.box(0,0,4,10,10,10,0)
crown=Mesh();crown.box(0,0,4,2,2,2,0)
inside=template(crown.v,row,'inside-closed-room',crown.f)
kept,report=filter_building_collisions([row],{'near':[inside]},[('closed-room','base',room)])
assert not kept, 'Tree entirely inside a closed building was retained'
assert report['removed'][0]['collisionKind']=='tree-component-inside-building'

huge=Mesh();huge.box(0,0,4,20,20,20,0)
enclosing=template(huge.v,row,'crown-enclosing-building',huge.f)
kept,report=filter_building_collisions([row],{'base':[enclosing]},[('closed-room','near',room)])
assert not kept, 'A building entirely inside a closed crown was retained'
assert report['removed'][0]['collisionKind']=='building-component-inside-tree'

# A courtyard is a hole in a connected watertight ring, not an occupied AABB.
ring=Mesh()
outer=[(-5,-5),(5,-5),(5,5),(-5,5)]
inner=[(-2,-2),(2,-2),(2,2),(-2,2)]
for i in range(4):
 j=(i+1)%4;a,b=outer[i],outer[j];c,d=inner[i],inner[j]
 for face in [[(*a,0),(*b,0),(*b,8),(*a,8)],
              [(*d,0),(*c,0),(*c,8),(*d,8)],
              [(*a,8),(*b,8),(*d,8),(*c,8)],
              [(*c,0),(*d,0),(*b,0),(*a,0)]]:ring.face(face,0)
kept,_=filter_building_collisions([row],{'near':[inside]},[('courtyard','base',ring)])
assert kept==[row], 'Open courtyard was filled by the containment check'

open_room=Mesh();open_room.box(0,0,4,10,10,10,0);open_room.f.pop(0)
kept,report=filter_building_collisions([row],{'near':[inside]},[('open-bottom','base',open_room)])
assert kept==[row], 'An open surface must not be automatically capped'
assert report['testedOpenBuildingComponents']>0, 'Uncovered open components must be reported'

# Face orientation is not guaranteed across hand-built primitives.
room.f=[tuple(reversed(f)) if i%2 else f for i,f in enumerate(room.f)]
kept,_=filter_building_collisions([row],{'near':[inside]},[('mixed-winding','base',room)])
assert not kept, 'Inconsistent input face winding hid a closed building'

portico=Mesh();portico.box(-4,0,4,1,8,8,0);portico.box(4,0,4,1,8,8,0);portico.box(0,0,9,10,8,1,0)
kept,_=filter_building_collisions([row],{'near':[inside]},[('open-portico','base',portico)])
assert kept==[row], 'Open passage between separate solids was filled'

# Disconnected foliage must each be checked, not just vertex zero of the tree.
mixed=Mesh();mixed.box(20,0,4,2,2,2,0);mixed.extend(crown)
mixed_template=template(mixed.v,row,'disconnected-crowns',mixed.f)
kept,_=filter_building_collisions([row],{'near':[mixed_template]},[('closed-room','base',room)])
assert not kept, 'A contained second crown component was missed'
room.f+=room.f[:]
kept,_=filter_building_collisions([row],{'near':[inside]},[('duplicate-faces','base',room)])
assert not kept, 'Coincident duplicate faces defeated shell detection'

offset=[381.3,-531.6,18.7,0,-2.1]
placed_room=Mesh();placed_room.box(offset[0],offset[1],7,10,10,10,0)
placed_crown=Mesh();placed_crown.box(offset[0],offset[1],7,2,2,2,0)
small=template(placed_crown.v,offset,'transformed-contained',placed_crown.f)
kept,_=filter_building_collisions([offset],{'near':[small]},[('placed-room','base',placed_room)])
assert not kept, 'Translation, ground height or tree scaling broke containment'
placed_crown=Mesh();placed_crown.box(offset[0],offset[1],7,20,20,20,0)
large=template(placed_crown.v,offset,'transformed-enclosing',placed_crown.f)
kept,_=filter_building_collisions([offset],{'base':[large]},[('placed-room','near',placed_room)])
assert not kept, 'Inverse tree transform broke reverse containment'
print('10 containment cases passed: both directions, courtyard, open bottom, mixed winding, portico, disconnected foliage, duplicate faces and transformed instances',flush=True)

# The acceleration index must agree with scanning every shell, including
# negative cells, cell boundaries and a shell too large to insert in the grid.
from tree_clearance import triangulate
from mesh_volumes import MeshVolumes
scattered=Mesh()
for x in [-65,-16,17,65]:scattered.box(x,-16,4,12,12,8,0)
massive=Mesh();massive.box(0,0,4,600,600,600,0)
for mesh in [scattered,massive]:
 vertices,triangles=triangulate(mesh.v,mesh.f);volumes=MeshVolumes(vertices,triangles)
 points=[(x,y,z) for x in [-310,-70,-65,-16,-10,0,16,17,21,65,71,310]
         for y in [-310,-22,-16,-10,0,310] for z in [-310,0,4,8,310]]
 for point in points:
  brute=any(shell.contains(point) for shell in volumes.shells)
  assert (volumes.witness_inside([point]) is not None)==brute, ('Spatial index changed containment',point)
 query=((-20,-20,0),(20,20,10))
 expected=[p for p in volumes.representatives if all(query[0][k]<=p[k]<=query[1][k] for k in range(3))]
 assert sorted(volumes.representatives_in_bounds(query))==sorted(expected)
print('2 spatial-index equivalence cases passed',flush=True)
