"""Joined ground-level perimeter roads, with disjoint pavement and curb polygons."""
import math,bpy
from geometry import Mesh
from functools import lru_cache
from mathutils import Vector
from mathutils.bvhtree import BVHTree

def surroundings_mesh(data,C,elevation,terrain_mesh):
    mesh=Mesh()
    # Match Blender/glTF's actual quad tessellation, not BVH's polygon fan.
    ground_data=bpy.data.meshes.new('road-ground-sampling')
    ground_data.from_pydata(terrain_mesh.v,[],terrain_mesh.f)
    ground_data.calc_loop_triangles()
    ground=BVHTree.FromPolygons(terrain_mesh.v,[tuple(t.vertices) for t in ground_data.loop_triangles],all_triangles=True)
    bpy.data.meshes.remove(ground_data)
    @lru_cache(maxsize=None)
    def road_height(x,y):
        z=elevation(x,y)
        hit=ground.ray_cast(Vector((x,y,z+100)),Vector((0,0,-1)),200)[0]
        return max(z,hit.z if hit is not None else z)+.4
    for layer in data['layers']:
        v,t=layer['vertices'],layer['triangles'];part=Mesh()
        def drape(points,depth=0):
            if depth<8 and max(math.dist(a,b) for a,b in zip(points,points[1:]+points[:1]))>35:
                a,b,c=points;ab=tuple((a[k]+b[k])/2 for k in [0,1]);bc=tuple((b[k]+c[k])/2 for k in [0,1]);ca=tuple((c[k]+a[k])/2 for k in [0,1])
                for tri in [[a,ab,ca],[ab,b,bc],[ca,bc,c],[ab,bc,ca]]:drape(tri,depth+1)
            else:part.face([(x,y,road_height(x,y)) for x,y in points],C[layer['material']])
        for i in range(0,len(t),3):drape([v[k] for k in t[i:i+3]])
        mesh.add_part(layer['id'],part)
    return mesh
