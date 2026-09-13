"""Real mesh clipping: local rise, retained planes, shore closure and ring winding."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'blender'))
from geometry import Mesh
from shore_geometry import build_shores,grade_mesh,grade,conform_edges
from site_geometry import mesh_triangles
shore=json.loads((root/'public/data/shores.json').read_text())['shores'][0]
terrain=Mesh();terrain.face([(-480,-750,0),(-360,-750,0),(-360,-600,0),(-480,-600,0)],0)
result,green,meshes,report=build_shores({'shores':[shore]},{'stone':0,'curb':0},terrain,Mesh())
def sample(mesh,x,y):
    bvh=BVHTree.FromPolygons(mesh.v,[t for t,_ in mesh_triangles(mesh)],all_triangles=True)
    hit=bvh.ray_cast(Vector((x,y,100)),Vector((0,0,-1)),200)[0];assert hit is not None,(x,y);return hit.z
# BVH ray intersection uses float32; from Z=100 its measured cancellation is
# 7.63e-6 m even on an unchanged Z=0 face. Keep the existing slope-scale limit.
for p in [(-475,-745),(-365,-605),(-435,-710)]:assert abs(sample(result,*p))<1e-5
# At a core segment midpoint, a small landward offset must have raised support.
a,b=shore['core'][:2];dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
x=(a[0]+b[0])/2-dy/length*.15;y=(a[1]+b[1])/2+dx/length*.15
crest=shore['waterLevel']+shore['freeboard']
assert abs(sample(result,x,y)-(crest-.04))<1e-5
wall=meshes['shore-'+shore['id']];assert abs(sample(wall,x,y)-crest)<1e-5
# Clipping masks may have either triangle winding.
reverse={**shore,'gradingMasks':[list(reversed(t)) for t in shore['gradingMasks']]}
again,_=grade_mesh(terrain,reverse,crest-.04);assert abs(sample(again,x,y)-sample(result,x,y))<1e-6
# Original sloped planes remain exact outside the mask.
slope=Mesh();slope.face([(-480,-750,-1),(-360,-750,1),(-360,-600,1),(-480,-600,-1)],0)
changed,_=grade_mesh(slope,shore,crest-.04)
for p in [(-475,-745),(-365,-605),(-435,-710)]:assert abs(sample(changed,*p)-sample(slope,*p))<1e-5
# A non-axis-aligned T junction opens under independent coordinate rounding.
# This reproduces the shipping Draco failure without depending on its binary.
tjunction=Mesh();a=(0,0,0);b=(10,3,0);p=(3.7,1.11,0);d=(10,-10,0)
tjunction.face([a,b,(0,10,0)],0);tjunction.face([a,d,p],0);tjunction.face([p,d,b],0)
def quantized(mesh):
    return BVHTree.FromPolygons([tuple(round(c/.1)*.1 for c in v) for v in mesh.v],
                               [t for t,_ in mesh_triangles(mesh)],all_triangles=True)
origin=Vector((3.7,1.105,100));down=Vector((0,0,-1))
assert quantized(tjunction).ray_cast(origin,down,200)[0] is None
assert quantized(conform_edges(tjunction,(-1,-11,11,11))).ray_cast(origin,down,200)[0] is not None
# Conforming a neighboring non-planar quad must retain its original diagonal.
quad=Mesh();quad.face([(0,0,0),(10,0,0),(10,10,5),(0,10,0)],0)
quad.face([(5,0,0),(6,-2,0),(4,-2,0)],0)
conformed=conform_edges(quad,(-1,-3,11,11))
for x in [1,3,7,9]:
    for y in [1.3,3.3,7.3,9.3]:assert abs(sample(quad,x,y)-sample(conformed,x,y))<2e-5
print('6 shore geometry cases passed: land rise and wall closure, outside water/land preserved, winding independence, original slope preserved, quantized T junction closure, non-planar neighbor preservation',flush=True)
