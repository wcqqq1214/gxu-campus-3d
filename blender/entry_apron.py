"""Flatten only a short apron and taper its surrounding terrain to old planes."""
import math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from geometry import Mesh
from site_geometry import mesh_triangles
from paving_geometry import clear_paving_ground


def build_entry_apron(site,C,elevation,terrain,roads):
    angle=site['angle'];cs,sn=math.cos(angle),math.sin(angle);ox,oy=site['origin']
    def world(x,y):return ox+x*cs-y*sn,oy+x*sn+y*cs
    ground=BVHTree.FromPolygons(terrain.v,[ids for ids,_ in mesh_triangles(terrain)],all_triangles=True)
    z=elevation(*site['buildingCenter'])+site['stairBaseHeight'];clear=site['groundClearance']
    half=site['halfWidth'];front=site['startY'];end=site['endY'];feather=site['gradingFeather'];step=site['meshStep']
    def old(x,y):
        wx,wy=world(x,y);hit=ground.ray_cast(Vector((wx,wy,z+100)),Vector((0,0,-1)),200)[0]
        if hit is None:raise ValueError('Missing terrain at entrance apron')
        return hit.z
    def stations(breaks):
        values=[]
        for a,b in zip(breaks,breaks[1:]):
            count=max(1,math.ceil((b-a)/step));values.extend(a+(b-a)*i/count for i in range(count))
        return values+[breaks[-1]]
    xs=stations([-half-feather,-half,half,half+feather]);ys=stations(sorted({site.get('gradingStartY',0),front,end,end+feather}))
    grading=Mesh()
    def point(x,y):
        distance=max(0,abs(x)-half,y-end);t=min(1,distance/feather)
        weight=t*t*(3-2*t)
        # The clipping helper subtracts clearance. At the outer edge its
        # ceiling meets the old plane exactly, leaving no vertical trench.
        h=z*(1-weight)+(old(x,y)+clear)*weight
        return (*world(x,y),h)
    for x0,x1 in zip(xs,xs[1:]):
        for y0,y1 in zip(ys,ys[1:]):
            a,b,c,d=point(x0,y0),point(x1,y0),point(x1,y1),point(x0,y1)
            grading.face([a,b,c],C['grass']);grading.face([a,c,d],C['grass'])
    terrain,repair=clear_paving_ground(terrain,grading,{'bounds':site['gradingBounds'],'groundClearance':clear})
    surface=Mesh();sides=Mesh();ax=stations([-half,half]);ay=stations([front,end])
    for x0,x1 in zip(ax,ax[1:]):
        for y0,y1 in zip(ay,ay[1:]):
            surface.face([(*world(x0,y0),z),(*world(x1,y0),z),(*world(x1,y1),z),(*world(x0,y1),z)],C[site['material']])
    for a,b in [((-half,front),(-half,end)),((-half,end),(half,end)),((half,end),(half,front))]:
        pa,pb=(*world(*a),z),(*world(*b),z)
        sides.face([pa,pb,(*pb[:2],min(z-clear,old(*b))-.03),(*pa[:2],min(z-clear,old(*a))-.03)],C[site['material']])
    mesh=Mesh();mesh.add_part('01_入口短铺地',surface);mesh.add_part('02_铺地侧面收口',sides)
    return terrain,roads,{'site-'+site['id']:mesh},[{'id':site['id'],'apronElevation':z,'groundRepair':repair,'dimensionsEstimated':True,'roadConnection':False}]
