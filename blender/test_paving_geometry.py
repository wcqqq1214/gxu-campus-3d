import sys,copy
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'blender'))
from geometry import Mesh
from paving_geometry import build_pavings
from site_geometry import mesh_triangles
r={'id':'test','surfaceId':'way/1','vertices':[[0,0],[10,0],[10,6],[0,6]],'bounds':[0,0,10,6],'areaMeters2':60,'joinFeather':3,'meshStep':2,'contactDepth':1,'contactSideMargin':.5,'joinOverlap':.15,'burial':.06,'joins':[{'a':[0,6],'b':[0,0],'inward':[1,0]}],'freeEdges':[[[0.02,0],[10,0],[10,6],[0.02,6]]]}
def quad(coords):
 m=Mesh();m.face(coords,0);return m
def tree(m):return BVHTree.FromPolygons(m.v,[t for t,_ in mesh_triangles(m)],all_triangles=True)
def height(b,x,y):
 hit=b.ray_cast(Vector((x,y,10)),Vector((0,0,-1)),20)[0];assert hit is not None;return hit.z
for reverse in [False,True]:
 terrain=quad([(-5,-5,0),(15,-5,0),(15,10,0),(-5,10,0)])
 roads=quad([(-3,-2,1),(0,-2,1),(0,8,1),(-3,8,1)])
 original=quad([(0,0,.4),(10,0,.4),(10,6,.4),(0,6,.4)])
 record=copy.deepcopy(r)
 if reverse:
  record['vertices'].reverse();record['freeEdges']=[list(reversed(line)) for line in record['freeEdges']]
 before=copy.deepcopy((terrain.v,terrain.f))
 ground,rest,meshes,report=build_pavings({'pavings':[record]},{'path':0},terrain,roads,{'way/1':original})
 p=tree(meshes['paving-test']);road=tree(meshes['paving-test-contact-0'])
 assert abs(height(p,0,3)-1)<1e-5
 assert abs(height(p,.001,3)-1)<.001
 for x in [3,3.001,3.5,5]:assert abs(height(p,x,3)-.4)<1e-5
 assert abs(height(road,-.3,3)-1)<1e-5
 assert (terrain.v,terrain.f)==before
 assert ground is terrain
 hit,normal,_,_=p.ray_cast(Vector((10.2,3,.2)),Vector((-1,0,0)),.4)
 assert hit is not None and normal.x>.9,(reverse,normal)
 assert report[0]['sideFaces']>0
print('2 paving geometry cases passed: actual join level, retained interior and terrain, open road contact, outward side closure, both windings',flush=True)

# Reproduce the actual interior terrain spike while keeping the whole edge low.
terrain=Mesh()
corners=[(-5,-5),(15,-5),(15,11),(-5,11)]
for a,b in zip(corners,corners[1:]+corners[:1]):
 terrain.face([(*a,0),(*b,0),(5,3,.6)],0)
ground,_,meshes,report=build_pavings({'pavings':[r]},{'path':0},terrain,roads,{'way/1':original})
assert abs(height(tree(ground),5,3)-.28)<1e-5
assert abs(height(tree(terrain),5,3)-.6)<1e-5
assert abs(height(tree(ground),14,3)-height(tree(terrain),14,3))<1e-5
assert report[0]['groundRepair']['loweredPieces']>0
print('Interior terrain spike cleared beneath unchanged paving; safe ground retained',flush=True)

# Actual clipped sliver: its float32 normal chooses XZ instead of ground XY.
import bpy
from geometry import material
mat=material('ground-uv-test',(1,1,1));m=Mesh()
m.face([(-6.464242458343506,-644.2694702148438,5.675299167633057),(-6.0974578857421875,-644.30322265625,5.664182662963867),(-6.097454071044922,-644.30322265625,5.664182186126709)],mat)
m.ground_uv_bounds=[(-26,-670,16,-643)]
o=m.object('corrected-local-ground',bpy.context.scene.collection,{'layer':'terrain'})
for loop,uv in zip(o.data.loops,o.data.uv_layers.active.data):
 co=o.data.vertices[loop.vertex_index].co;assert abs(uv.uv.y-co.y/4)<1e-6
m.ground_uv_bounds=[(0,0,1,1)]
o=m.object('preserved-outside-projection',bpy.context.scene.collection,{'layer':'terrain'})
for loop,uv in zip(o.data.loops,o.data.uv_layers.active.data):
 co=o.data.vertices[loop.vertex_index].co;assert abs(uv.uv.y-co.z/4)<1e-6
print('Actual ground sliver uses XY UVs locally; outside projection remains unchanged',flush=True)

# Discontinuous old triangulation must not survive a grounded service repair.
terrain=quad([(-5,-5,0),(15,-5,0),(15,10,0),(-5,10,0)])
roads=quad([(-3,-2,.4),(0,-2,.4),(0,8,.4),(-3,8,.4)])
original=Mesh();original.face([(0,0,1),(10,0,1),(10,6,1)],0);original.face([(0,0,.4),(10,6,.4),(0,6,.4)],0)
record={**r,'groundedService':{'offset':.12},'meshStep':1}
ground,rest,meshes,_=build_pavings({'pavings':[record]},{'path':0,'road':0},terrain,roads,{'way/1':original})
p=tree(meshes['paving-test'])
for x,y in [(5,2.9),(5,3.1),(8,2),(8,5)]:assert abs(height(p,x,y)-.12)<1e-5
assert abs(height(p,0,3)-.4)<1e-5
print('Grounded service repair removes an old 0.6 m triangle discontinuity while retaining its road join',flush=True)

# A terrain crease inside a grid cell must survive in the new road surface.
terrain=Mesh();peak=(5.3,3.2,.2)
corners=[(-5,-5,0),(15,-5,0),(15,10,0),(-5,10,0)]
for a,b in zip(corners,corners[1:]+corners[:1]):terrain.face([a,b,peak],0)
ground,_,meshes,_=build_pavings({'pavings':[record]},{'path':0,'road':0},terrain,roads,{'way/1':original})
assert abs(height(tree(meshes['paving-test']),5.3,3.2)-.32)<1e-5
print('Grounded road follows an off-grid terrain crease without interpolation sag',flush=True)

from paving_geometry import split_grounded_road_exports
roads=quad([(-20,-20,.3),(30,-20,.3),(30,30,.3),(-20,30,.3)])
roads.face([(10,0,0),(10,6,0),(10,6,.3),(10,0,.3)],0)
before=copy.deepcopy((roads.v,roads.f,roads.m))
split=split_grounded_road_exports({'roads':roads},[record])
assert (roads.v,roads.f,roads.m)==before
combined=Mesh()
for mesh in split.values():combined.extend(mesh)
for x in [-6,-5.1,-5,-4.9,5,14.9,15,15.1,16]:
 assert abs(height(tree(combined),x,3)-.3)<1e-5
patch=split['paving-test-export']
assert max(v[0] for v in patch.v)-min(v[0] for v in patch.v)<21
hit=tree(patch).ray_cast(Vector((10.2,3,.15)),Vector((-1,0,0)),.4)[0]
assert hit is not None,'Local export must retain the vertical edge closure'
print('Local road export retains surface/vertical closure, bounds quantization, and leaves source intact',flush=True)

from paving_geometry import clear_paving_ground
terrain=quad([(0,0,4),(10,0,4),(10,6,4),(0,6,4)])
for error,should_keep in [(.00005,True),(.001,False)]:
 pavement=quad([(0,0,4.12-error),(10,0,4.12-error),(10,6,4.12-error),(0,6,4.12-error)])
 result,report=clear_paving_ground(terrain,pavement,record)
 assert (result is terrain)==should_keep,(error,report)
 if should_keep:assert 0<report['ignoredRoundoffLoweringMeters']<=.0001
 else:assert report['maximumLoweringMeters']>.0001
print('Grounded-road float32 noise preserves original terrain; real clearance intrusion still lowers it',flush=True)
