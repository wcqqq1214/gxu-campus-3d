"""A bounded stone shore and graded land, sampling final terrain triangles."""
import math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from geometry import Mesh
from site_geometry import mesh_triangles, split_convex, polygon_distance


def nearest(path,x,y):
    best=(math.inf,0);along=0
    for a,b in zip(path,path[1:]):
        dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
        t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/(length*length)))
        distance=math.hypot(x-a[0]-dx*t,y-a[1]-dy*t)
        if distance<best[0]:best=(distance,along+t*length)
        along+=length
    return best


def smooth(value):
    value=max(0,min(1,value));return value*value*(3-2*value)


def grade(shore,point,target):
    x,y,z=point;distance,along=nearest(shore['path'],x,y)
    weight=smooth((shore['landWidth']-distance)/(shore['landWidth']-shore['capWidth']))
    weight*=smooth(along/shore['endFeather'])*smooth((shore['pathLength']-along)/shore['endFeather'])
    if shore['safetyPolygons']:
        distance=min(polygon_distance((x,y),p) for p in shore['safetyPolygons'])
        weight*=smooth(distance/shore['safetyFeather'])
    return x,y,z+max(0,target-z)*weight


def bounds(points):return min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)


def overlaps(a,b):return a[2]>=b[0] and a[0]<=b[2] and a[3]>=b[1] and a[1]<=b[3]


def triangles_into(mesh,points,material,transform=lambda p:p):
    for i in range(1,len(points)-1):
        a,b,c=points[0],points[i],points[i+1]
        if abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))>1e-9:
            mesh.face([transform(a),transform(b),transform(c)],material)


def conform_edges(mesh,area):
    """Split T junctions before Draco rounds long and subdivided edges apart.

    All incident faces must share the same XY edge segments. Interpolate each
    face's Z so intentional water-side steps and unchanged outside planes remain.
    A center fan preserves every collinear boundary vertex in the triangulation.
    """
    cell=2.;epsilon=1e-5;points={};buckets={}
    for x,y,z in mesh.v:
        if area[0]-epsilon<=x<=area[2]+epsilon and area[1]-epsilon<=y<=area[3]+epsilon:
            key=(round(x,6),round(y,6));points.setdefault(key,(x,y))
    for xy in points.values():buckets.setdefault((math.floor(xy[0]/cell),math.floor(xy[1]/cell)),[]).append(xy)
    result=Mesh();local=set();faces=[]
    for i,face in enumerate(mesh.f):
        original=[mesh.v[k] for k in face]
        if overlaps(bounds(original),area):local.add(i)
        else:result.face(original,mesh.m[i])
    # A terrain quad can be non-planar. Preserve Blender's original diagonal;
    # adding a center directly to that quad would change the untouched slope.
    faces=[([mesh.v[k] for k in ids],mesh.m[i]) for ids,i in mesh_triangles(mesh) if i in local]
    for original,mat in faces:
        ring=[];changed=False
        for a,b in zip(original,original[1:]+original[:1]):
            ring.append(a);dx,dy=b[0]-a[0],b[1]-a[1];length2=dx*dx+dy*dy
            if length2<epsilon**2:continue
            cuts=[]
            for ix in range(math.floor((min(a[0],b[0])-epsilon)/cell),math.floor((max(a[0],b[0])+epsilon)/cell)+1):
                for iy in range(math.floor((min(a[1],b[1])-epsilon)/cell),math.floor((max(a[1],b[1])+epsilon)/cell)+1):
                    for x,y in buckets.get((ix,iy),[]):
                        t=((x-a[0])*dx+(y-a[1])*dy)/length2
                        if epsilon<t<1-epsilon and abs((x-a[0])*dy-(y-a[1])*dx)<epsilon*math.sqrt(length2):
                            cuts.append((t,(x,y,a[2]+t*(b[2]-a[2]))))
            last=-1.
            for t,p in sorted(cuts):
                if t-last>epsilon:ring.append(p);changed=True;last=t
        if not changed:result.face(original,mat);continue
        # Each fan stays on the original triangle plane.
        center=tuple(sum(p[k] for p in original)/len(original) for k in range(3))
        for a,b in zip(ring,ring[1:]+ring[:1]):triangles_into(result,[center,a,b],mat)
    return result


def grade_mesh(mesh,shore,target):
    if not mesh.f:return mesh,0
    masks=[]
    for triangle in shore['gradingMasks']:
        a,b,c=triangle
        if (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])<0:triangle=list(reversed(triangle))
        masks.append((triangle,bounds(triangle)))
    selected={i for i,face in enumerate(mesh.f) if overlaps(bounds([mesh.v[k] for k in face]),shore['gradingBounds'])}
    result=Mesh();affected=0
    for i,face in enumerate(mesh.f):
        if i not in selected:result.face([mesh.v[k] for k in face],mesh.m[i])
    for ids,face in mesh_triangles(mesh):
        if face not in selected:continue
        points=[mesh.v[k] for k in ids];remaining=[points];pieces=[]
        bb=bounds(points)
        for outline,area in masks:
            if not remaining or not overlaps(bb,area):continue
            leftovers=[]
            for part in remaining:
                if not overlaps(bounds(part),area):leftovers.append(part);continue
                kept,outside=split_convex(part,outline)
                if len(kept)>=3:pieces.append(kept)
                leftovers.extend(outside)
            remaining=leftovers
        for part in remaining:triangles_into(result,part,mesh.m[face])
        for part in pieces:triangles_into(result,part,mesh.m[face],lambda p:grade(shore,p,target))
        affected+=bool(pieces)
    # Include untouched neighboring faces that share a newly subdivided edge.
    if affected:
        touched=bounds([mesh.v[k] for i in selected for k in mesh.f[i]])
        result=conform_edges(result,tuple(v+(-1 if i<2 else 1) for i,v in enumerate(touched)))
    return result,affected


def core_stations(shore):
    sign=shore['outwardSign'];path=shore['core'];directions=[]
    for a,b in zip(path,path[1:]):
        dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy);directions.append((-dy/length*sign,dx/length*sign))
    miters=[directions[0]]
    for a,b in zip(directions,directions[1:]):
        den=1+a[0]*b[0]+a[1]*b[1];miters.append(((a[0]+b[0])/den,(a[1]+b[1])/den))
    miters.append(directions[-1]);result=[]
    for i,(a,b) in enumerate(zip(path,path[1:])):
        steps=math.ceil(math.dist(a,b)/shore['meshStep'])
        for j in range(steps):
            t=j/steps;result.append(([a[k]*(1-t)+b[k]*t for k in range(2)],[miters[i][k]*(1-t)+miters[i+1][k]*t for k in range(2)]))
    result.append((path[-1],miters[-1]));return result


def build_shores(data,C,terrain,green):
    meshes={};reports=[]
    for shore in data['shores']:
        before=BVHTree.FromPolygons(terrain.v,[t for t,_ in mesh_triangles(terrain)],all_triangles=True)
        crest=shore['waterLevel']+shore['freeboard']
        terrain,changed=grade_mesh(terrain,shore,crest-.04)
        green,green_changed=grade_mesh(green,shore,crest-.03)
        stations=core_stations(shore);rows=[]
        for xy,normal in stations:
            pair=[]
            for distance in [0,shore['capWidth']]:
                x,y=[xy[k]+normal[k]*distance for k in range(2)]
                hit=before.ray_cast(Vector((x,y,200)),Vector((0,0,-1)),400)[0]
                if hit is None:raise ValueError('Missing original terrain below shore wall')
                # The wall seals to original ground as well as reaching below water.
                bottom=min(hit.z-.08,shore['waterLevel']-.25)
                pair.append(((x,y,bottom),(x,y,crest)))
            rows.append(pair)
        wall=Mesh();cap=Mesh();foot=Mesh();ends=Mesh()
        for a,b in zip(rows,rows[1:]):
            # Front faces water; cap and rear close the full stone volume.
            wall.face([a[0][0],b[0][0],b[0][1],a[0][1]],C['stone'])
            wall.face([b[1][0],a[1][0],a[1][1],b[1][1]],C['stone'])
            cap.face([a[0][1],b[0][1],b[1][1],a[1][1]],C['curb'])
            foot.face([b[0][0],a[0][0],a[1][0],b[1][0]],C['stone'])
        a,b=rows[0],rows[-1]
        ends.face([a[0][0],a[0][1],a[1][1],a[1][0]],C['stone'])
        ends.face([b[0][1],b[0][0],b[1][0],b[1][1]],C['stone'])
        mesh=Mesh();mesh.add_part('01_砌石岸壁',wall);mesh.add_part('02_岸顶压石',cap);mesh.add_part('03_埋入地形墙脚',foot);mesh.add_part('04_岸段两端收口',ends)
        meshes['shore-'+shore['id']]=mesh
        reports.append({'id':shore['id'],'crestElevation':crest,'lengthMeters':shore['coreLength'],'changedTerrainTriangles':changed,'changedGreenTriangles':green_changed,'wallFaces':len(mesh.f),'waterLevelPreserved':shore['waterLevel'],'dimensionsEstimated':True})
    return terrain,green,meshes,reports


def sync_source_shores(base,include_terrain=False):
    """Synchronize shore-dependent ground after an existing bounded base rebuild."""
    import bpy
    collection=bpy.data.objects['terrain'].users_collection[0]
    keys=['green']+(['terrain'] if include_terrain else [])+[k for k in base if k.startswith('shore-')]
    for old in list(bpy.context.scene.objects):
        if old.name.startswith('shore-') and old.name not in base:
            data=old.data;bpy.data.objects.remove(old,do_unlink=True)
            if data.users==0:bpy.data.meshes.remove(data)
    for key in keys:
        old=bpy.data.objects.get(key)
        if old:
            data=old.data;bpy.data.objects.remove(old,do_unlink=True)
            if data.users==0:bpy.data.meshes.remove(data)
        layer='water' if key.startswith('shore-') else key
        base[key].object(key,collection,{'layer':layer})
