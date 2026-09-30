"""Ground a mapped service road on actual terrain, keeping existing contacts."""
import math
from functools import lru_cache
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from geometry import Mesh
from site_geometry import mesh_triangles,split_convex,inside
from shore_geometry import bounds,overlaps,triangles_into,conform_edges,smooth
from foundation_geometry import masks_for,clipped_mesh,simplify_local_planes


def build_service_road(record,C,terrain,roads):
    ground_faces=mesh_triangles(terrain)
    ground=BVHTree.FromPolygons(terrain.v,[ids for ids,_ in ground_faces],all_triangles=True)
    old_road=BVHTree.FromPolygons(roads.v,[ids for ids,_ in mesh_triangles(roads)],all_triangles=True)
    masks=masks_for(record['masks'])
    contacts=[(a,b) for line in record['contacts'] for a,b in zip(line,line[1:]) if math.dist(a,b)>1e-4]
    def contains(x,y):
        return any(inside((x,y),poly[0]) and not any(inside((x,y),h) for h in poly[1:]) for poly in record['polygons'])
    def contact(x,y):
        best=None
        for a,b in contacts:
            dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
            t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/length**2))
            qx,qy=a[0]+t*dx,a[1]+t*dy;distance=math.hypot(x-qx,y-qy)
            if best is None or distance<best[0]:
                nx,ny=-dy/length,dx/length
                if contains((a[0]+b[0])/2+nx*.03,(a[1]+b[1])/2+ny*.03):nx,ny=-nx,-ny
                inset=min(.1,.04/length);sample_t=max(inset,min(1-inset,t))
                best=(distance,a[0]+sample_t*dx,a[1]+sample_t*dy,nx,ny)
        return best
    @lru_cache(maxsize=None)
    def levels(x,y):
        point=Vector((x,y,150));down=Vector((0,0,-1))
        g=ground.ray_cast(point,down,300)[0]
        if g is None:raise ValueError('Missing service-road terrain')
        d,qx,qy,nx,ny=contact(x,y)
        z=g.z+record['offset'];weight=smooth(1-d/record['joinFeather'])
        if weight:
            # Sample inside the retained neighbor. The old target can be buried
            # at the exact shared edge, so a ray on that edge is ambiguous.
            old,normal,_,_=old_road.ray_cast(Vector((qx+nx*.03,qy+ny*.03,150)),down,300)
            if old is None:
                # At a contact endpoint, step along its edge into the retained
                # surface before extrapolating the sampled plane back.
                for sign in (-1,1):
                    sx,sy=qx+nx*.03-sign*ny*.05,qy+ny*.03+sign*nx*.05
                    if contains(sx,sy):continue
                    old,normal,_,_=old_road.ray_cast(Vector((sx,sy,150)),down,300)
                    if old is not None:break
            if old is None or abs(normal.z)<1e-6:raise ValueError(f'Missing retained service-road contact plane: {x,y,qx,qy,nx,ny}')
            contact_z=old.z+(normal.x*(old.x-x)+normal.y*(old.y-y))/normal.z
            z+=max(0,contact_z-z)*weight
        return z,g.z
    top=Mesh()
    # Terrain creases, rather than an unrelated meter grid, determine road
    # triangles. Only the short contact transitions receive extra stations.
    for ids,_ in ground_faces:
        points=[terrain.v[k] for k in ids]
        if not overlaps(bounds(points),record['bounds']):continue
        for mask_index,(outline,bb) in enumerate(masks):
            if not overlaps(bounds(points),bb):continue
            kept,_=split_convex(points,outline)
            core=mask_index<record.get('coreMaskCount',0)
            triangles_into(top,[(p[0],p[1],p[2]+record['offset'] if core else levels(p[0],p[1])[0]) for p in kept],C['road'])
    raw_triangles=len(top.f)
    top=conform_edges(top,record['bounds'])
    conformed_triangles=len(top.f)
    # All duplicate XY stations sample the same field, including T junctions.
    top.v=[(x,y,z if any(inside((x,y),p[0]) and not any(inside((x,y),h) for h in p[1:]) for p in record.get('corePolygons',[])) else levels(x,y)[0]) for x,y,z in top.v]
    top=simplify_local_planes(top,record,normal_tolerance=1e-4,weld_distance=.0001)
    side=Mesh();stations={tuple(round(p[k],6) for k in range(2)):p[:2] for p in top.v}
    for line in record['freeEdges']:
        for a,b in zip(line,line[1:]):
            dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
            if length<1e-6:continue
            values={0.,1.}
            for x,y in stations.values():
                t=((x-a[0])*dx+(y-a[1])*dy)/(length*length)
                if 0<t<1 and abs((x-a[0])*dy-(y-a[1])*dx)/length<.00015:values.add(t)
            row=[]
            previous=-1.
            for t in sorted(values):
                if (t-previous)*length<.0001:continue
                previous=t
                x,y=a[0]+t*dx,a[1]+t*dy;z,g=levels(x,y)
                row.append(((x,y,g-record['burial']),(x,y,z)))
            for a,b in zip(row,row[1:]):side.face([a[0],b[0],b[1],a[1]],C['road'])
    before=sum(len(f)-2 for f in roads.f)
    # Retain existing vertical paving/road closures, which have no XY area.
    # The mapped target contributes tops only; clipping a neighboring vertical
    # face with the planar polygon routine would silently discard that face.
    tops=Mesh();vertical=Mesh()
    for i,f in enumerate(roads.f):
        points=[roads.v[k] for k in f]
        area=abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(points,points[1:]+points[:1])))
        (vertical if area<1e-8 or roads.m[i]!=C['road'] else tops).face(points,roads.m[i])
    roads,removed=clipped_mesh(tops,masks_for(record.get('cutMasks',record['masks'])),record['bounds'])
    roads.extend(vertical)
    roads.extend(top);roads.extend(side)
    return roads,{'surfaceId':record['surfaceId'],'rawTopTriangles':raw_triangles,'conformedTopTriangles':conformed_triangles,'roadTopTriangles':sum(len(f)-2 for f in top.f),
        'sideTriangles':sum(len(f)-2 for f in side.f),'triangleDelta':sum(len(f)-2 for f in roads.f)-before,
        'removed':removed,'terrainUnchanged':True,'repairArea':record['repairArea']}
