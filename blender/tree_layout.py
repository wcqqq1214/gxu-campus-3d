"""Ground tree anchors on the final terrain triangles used by the GLB exporter."""
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def ground_tree_rows(rows, vertices, faces):
    data = bpy.data.meshes.new('tree-ground-sampling')
    try:
        data.from_pydata(vertices, [], faces)
        data.calc_loop_triangles()
        ground = BVHTree.FromPolygons([v.co.copy() for v in data.vertices],
                                     [tuple(t.vertices) for t in data.loop_triangles], all_triangles=True)
        result = []
        for row in rows:
            x,y,h,typ = row[:4]
            hit = ground.ray_cast(Vector((x,y,200)), Vector((0,0,-1)), 400)[0]
            if hit is None:
                raise ValueError(f'Tree has no final terrain support: {x},{y}')
            result.append([x,y,h,typ,round(float(hit.z),6)])
        return result
    finally:
        bpy.data.meshes.remove(data)
