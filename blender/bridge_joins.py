"""Terrain-matched transition finishes, sharing the old ramp cross-section at entry."""
import math,bpy
from functools import lru_cache
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from geometry import Mesh

def bridge_join_mesh(data,C,elevation,terrain):
    ground_data=bpy.data.meshes.new('join-ground');ground_data.from_pydata(terrain.v,[],terrain.f);ground_data.calc_loop_triangles()
    ground=BVHTree.FromPolygons(terrain.v,[tuple(t.vertices) for t in ground_data.loop_triangles],all_triangles=True);bpy.data.meshes.remove(ground_data)
    axis=data['axis'];lengths=[0]
    for a,b in zip(axis,axis[1:]):lengths.append(lengths[-1]+math.dist(a,b))
    ramp=data['ramp'];rlen=[0]
    for a,b in zip(ramp,ramp[1:]):rlen.append(rlen[-1]+math.dist(a[:2],b[:2]))
    def smooth(t):
        t=max(0,min(1,t));return t*t*(3-2*t)
    @lru_cache(None)
    def level(x,y,material):
        best=None
        for i,(a,b) in enumerate(zip(axis,axis[1:])):
            dx=b[0]-a[0];dy=b[1]-a[1];t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy)))
            px=a[0]+dx*t;py=a[1]+dy*t;dist=math.hypot(x-px,y-py)
            item=(dist,lengths[i]+t*(lengths[i+1]-lengths[i]),px,py)
            if best is None or item[0]<best[0]:best=item
        lateral,d,px,py=best;z=elevation(x,y)+.4
        hit=ground.ray_cast(Vector((x,y,z+100)),Vector((0,0,-1)),200)[0]
        natural=max(z,hit.z+.4 if hit is not None else z)
        if d<rlen[-1]:
            i=next(i for i in range(len(rlen)-1) if d<=rlen[i+1]);t=(d-rlen[i])/(rlen[i+1]-rlen[i])
            h=ramp[i][2]*(1-t)+ramp[i+1][2]*t;n=ramp[i][3]*(1-t)+ramp[i+1][3]*t
        else:h=n=elevation(px,py)+.4
        weight=smooth(d/lengths[-1]);height=h+(natural-n)*weight
        if hit is not None and (d>=rlen[-1] or lateral>8.8):height=max(height,hit.z+.12)
        if material=='path':height+=(data['walkStart']-data['start'][2])*(1-smooth(d/rlen[-1]))
        if material=='curb':height+=.15*(1-smooth(d/rlen[-1]))
        if material=='grass':height-=.4
        return height
    mesh=Mesh()
    for layer in data['layers']:
        part=Mesh();v,t=layer['vertices'],layer['triangles'];mat=layer['material']
        for i in range(0,len(t),3):part.face([(v[k][0],v[k][1],level(*v[k],mat)+layer.get('zOffset',0)) for k in t[i:i+3]],C[mat])
        mesh.add_part(layer['id'],part)
    return mesh
