"""Synthetic sloped-road joins and local terrain clearance for a turned path."""
import sys,copy
from pathlib import Path
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from geometry import Mesh
from side_connection import build_side_connection
from site_geometry import mesh_triangles

ring=[[-3,4],[3,4],[3,9],[-18,9],[-18,5],[-3,5]]
triangles=tessellate_polygon([[Vector((*p,0)) for p in ring]])
indices=[v for tri in triangles for v in tri]
site={'id':'test','angle':0,'origin':[0,0],'buildingCenter':[0,0],'stairBaseHeight':0,
      'columns':[[-18,5],[-18,6],[-18,7],[-18,8],[-18,9]],'entry':{'attachedPortico':{'width':6}},
      'leadDistance':3,'startY':4,'meshStep':1,'localMesh':{'vertices':ring,'triangles':indices},
      'localPolygon':ring+[ring[0]],'gradingBounds':[-18,4,3,9],'groundClearance':.12,
      'material':'asphalt','roadContactSideMargin':.5,'roadContactDepth':1,'joinOverlap':.2}
def tree(m):return BVHTree.FromPolygons(m.v,[ids for ids,_ in mesh_triangles(m)],all_triangles=True)
def height(t,x,y):
    h=t.ray_cast(Vector((x,y,5)),Vector((0,0,-1)),10)[0];assert h is not None,(x,y);return h.z
for ground_height in [-.05,.25]:
    terrain=Mesh();terrain.face([(-25,-5,ground_height),(10,-5,ground_height),(10,15,ground_height),(-25,15,ground_height)],0)
    roads=Mesh();roads.face([(x,y,.4+.02*y) for x,y in [(-22,0),(-18,0),(-18,12),(-22,12)]],0)
    before=copy.deepcopy((roads.v,roads.f,terrain.v,terrain.f))
    ground,rest,meshes,report=build_side_connection(site,{'asphalt':0},lambda x,y:0,terrain,roads)
    mesh=meshes['site-test'];path=tree(mesh);final=tree(ground)
    for x in [-2.9,0,2.9]:assert abs(height(path,x,4))<1e-5
    for y in [5.1,6,7,8,8.9]:
        assert abs(height(path,-18,y)-(.4+.02*y))<.0001
        assert abs(height(path,-18.3,y)-(.4+.02*y))<.0001
    for x,y in [(0,4.4),(-2,6),(-8,7),(-17,8)]:assert height(final,x,y)<=height(path,x,y)-.1199
    assert abs(height(final,5,6)-ground_height)<1e-5
    assert abs(height(final,-10,3)-ground_height)<1e-5
    assert (roads.v,roads.f,terrain.v,terrain.f)==before
    assert report[0]['sideFaces']>0
print('2 turned-path cases passed: stair base, inclined road contact, local terrain clearance and preserved outside ground',flush=True)

ring=[[-4,2],[4,2],[4,12],[-4,12]]
indices=[v for tri in tessellate_polygon([[Vector((*p,0)) for p in ring]]) for v in tri]
front={**site,'type':'front-connection','columns':[[-4,12],[-2,12],[0,12],[2,12],[4,12]],
       'entry':{'stairFlight':{'width':8}},'startY':2,'meshStep':2,
       'localMesh':{'vertices':ring,'triangles':indices},'localPolygon':ring+[ring[0]],'gradingBounds':[-4,2,4,12]}
for ground_height in [-.05,.25]:
    terrain=Mesh();terrain.face([(-10,-5,ground_height),(10,-5,ground_height),(10,20,ground_height),(-10,20,ground_height)],0)
    roads=Mesh();roads.face([(x,y,.4+.02*x) for x,y in [(-8,12),(8,12),(8,18),(-8,18)]],0)
    before=copy.deepcopy((roads.v,roads.f,terrain.v,terrain.f))
    ground,rest,meshes,report=build_side_connection(front,{'asphalt':0},lambda x,y:0,terrain,roads)
    path=tree(meshes['site-test']);final=tree(ground)
    for x in [-3.9,0,3.9]:
        assert abs(height(path,x,2))<1e-5
        assert abs(height(path,x,12.3)-(.4+.02*x))<.0001
    for x,y in [(-3,3),(1,6),(3,11)]:assert height(final,x,y)<=height(path,x,y)-.1199
    assert abs(height(final,6,7)-ground_height)<1e-5
    assert (roads.v,roads.f,terrain.v,terrain.f)==before
print('2 forward-path cases passed: full stair width, tilted road contact and unchanged outside terrain',flush=True)

# A buried contact lip may have a dominant Y normal, but it must retain
# the original road's world XY mapping. Unmarked vertical faces stay local.
import bpy
from geometry import MATERIALS
MATERIALS[:]=[bpy.data.materials.new('road-uv-test'),bpy.data.materials.new('wall-uv-test')]
m=Mesh();m.face([(0,0,0),(1,0,0),(1,.1,-.2)],0);m.face([(0,0,0),(0,1,0),(0,1,2)],1)
m.xy_uv_materials={0};obj=m.object('contact-uv',bpy.context.scene.collection)
for p in obj.data.polygons:
    for i in p.loop_indices:
        co=obj.data.vertices[obj.data.loops[i].vertex_index].co;uv=obj.data.uv_layers.active.data[i].uv
        expected=(co.x/4,co.y/4) if p.material_index==0 else (co.y/4,co.z/4)
        assert max(abs(uv[k]-expected[k]) for k in range(2))<1e-7
print('Contact UV regression passed: XY road texture and preserved unmarked vertical projection',flush=True)
