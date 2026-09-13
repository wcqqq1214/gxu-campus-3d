"""Join one mapped pavement to real road triangles and close exposed sides."""
import math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from geometry import Mesh
from site_geometry import mesh_triangles,split_convex,contact_road
from shore_geometry import conform_edges,smooth,bounds,overlaps,triangles_into

def clear_paving_ground(terrain,paving,record):
    """Lower only ground beneath the mapped paving, preserving both planes."""
    masks=[];clearance=record.get('groundClearance',.12)
    for ids,_ in mesh_triangles(paving):
        triangle=[paving.v[i] for i in ids]
        if (triangle[1][0]-triangle[0][0])*(triangle[2][1]-triangle[0][1])-(triangle[1][1]-triangle[0][1])*(triangle[2][0]-triangle[0][0])<0:triangle.reverse()
        normal=(Vector(triangle[1])-Vector(triangle[0])).cross(Vector(triangle[2])-Vector(triangle[0]))
        if abs(normal.z)>1e-9:masks.append((triangle,bounds(triangle),normal))
    selected={i for i,face in enumerate(terrain.f) if overlaps(bounds([terrain.v[k] for k in face]),record['bounds'])}
    result=Mesh();lowered=0;maximum=0
    for i,face in enumerate(terrain.f):
        if i not in selected:result.face([terrain.v[k] for k in face],terrain.m[i])
    for ids,face in mesh_triangles(terrain):
        if face not in selected:continue
        points=[terrain.v[i] for i in ids];remaining=[points];bb=bounds(points)
        for outline,area,normal in masks:
            if not remaining or not overlaps(bb,area):continue
            leftovers=[]
            for part in remaining:
                if not overlaps(bounds(part),area):leftovers.append(part);continue
                kept,outside=split_convex(part,outline);leftovers.extend(outside)
                if len(kept)<3:continue
                a=outline[0]
                def ceiling(p):return a[2]-(normal.x*(p[0]-a[0])+normal.y*(p[1]-a[1]))/normal.z-clearance
                # Split where the original terrain intersects the clearance
                # plane, so the minimum of two planes is represented exactly.
                sides=[[],[]]
                for p,q in zip(kept,kept[1:]+kept[:1]):
                    u,v=p[2]-ceiling(p),q[2]-ceiling(q);sides[int(u>0)].append(p)
                    if (u>0)!=(v>0):
                        t=u/(u-v);cross=tuple(p[k]+t*(q[k]-p[k]) for k in range(3))
                        for side in sides:side.append(cross)
                triangles_into(result,sides[0],terrain.m[face])
                if len(sides[1])>=3:
                    lowered+=1;maximum=max(maximum,max(p[2]-ceiling(p) for p in sides[1]))
                    triangles_into(result,[(p[0],p[1],ceiling(p)) for p in sides[1]],terrain.m[face])
            remaining=leftovers
        for part in remaining:triangles_into(result,part,terrain.m[face])
    if not lowered:return terrain,{'loweredPieces':0,'maximumLoweringMeters':0}
    touched=bounds([terrain.v[k] for i in selected for k in terrain.f[i]])
    result=conform_edges(result,tuple(v+(-1 if i<2 else 1) for i,v in enumerate(touched)))
    return result,{'loweredPieces':lowered,'maximumLoweringMeters':maximum,'pavingClearanceMeters':clearance}

def split_at_feather(piece,join,feather):
    """Keep triangles from carrying the join correction beyond its strip."""
    a=join['a'];nx,ny=join['inward'];sides=[[],[]]
    def signed(p):return (p[0]-a[0])*nx+(p[1]-a[1])*ny-feather
    for p,q in zip(piece,piece[1:]+piece[:1]):
        u,v=signed(p),signed(q);sides[int(u>=0)].append(p)
        if (u>=0)!=(v>=0):
            t=u/(u-v);cross=tuple(p[k]+t*(q[k]-p[k]) for k in range(3))
            for side in sides:side.append(cross)
    return [side for side in sides if len(side)>=3]

def build_pavings(data,C,terrain,roads,originals):
    output={};reports=[]
    ground=BVHTree.FromPolygons(terrain.v,[t for t,_ in mesh_triangles(terrain)],all_triangles=True)
    for record in data['pavings']:
        original=originals[record['surfaceId']];triangles=[[original.v[k] for k in ids] for ids,_ in mesh_triangles(original)]
        neighboring=BVHTree.FromPolygons(roads.v,[t for t,_ in mesh_triangles(roads)],all_triangles=True)
        def old_height(x,y):
            for a,b,c in triangles:
                den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
                if abs(den)<1e-12:continue
                u=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/den
                v=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/den;w=1-u-v
                if min(u,v,w)>=-1e-7:return u*a[2]+v*b[2]+w*c[2]
            raise ValueError(f'Missing original paving plane: {x}, {y}')
        def road_height(join,x,y):
            nx,ny=join['inward'];qx,qy=x-nx*.025,y-ny*.025
            hit,normal,_,_=neighboring.ray_cast(Vector((qx,qy,200)),Vector((0,0,-1)),400)
            if hit is None or abs(normal.z)<.5:raise ValueError('Missing actual road at paving join')
            return hit.z+(normal.x*(hit.x-x)+normal.y*(hit.y-y))/normal.z
        def top(x,y):
            result=old_height(x,y);weights=[]
            for join in record['joins']:
                a,b=join['a'],join['b'];dx,dy=b[0]-a[0],b[1]-a[1];t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy)))
                qx,qy=a[0]+t*dx,a[1]+t*dy;distance=math.hypot(x-qx,y-qy)
                weight=smooth(1-distance/record['joinFeather'])
                if weight:weights.append((weight,road_height(join,qx,qy)-old_height(qx,qy)))
            if weights:
                # At multiple joins normalize contributions rather than stacking.
                result+=sum(w*delta for w,delta in weights)/max(1,sum(w for w,_ in weights))
            return result
        paving=Mesh();step=record['meshStep']
        for tri in triangles:
            x0=min(p[0] for p in tri);x1=max(p[0] for p in tri);y0=min(p[1] for p in tri);y1=max(p[1] for p in tri)
            for ix in range(math.floor(x0/step),math.ceil(x1/step)):
                for iy in range(math.floor(y0/step),math.ceil(y1/step)):
                    x,y=ix*step,iy*step
                    piece,_=split_convex(tri,[(x,y),(x+step,y),(x+step,y+step),(x,y+step)])
                    pieces=[piece] if len(piece)>=3 else []
                    for join in record['joins']:
                        pieces=[part for piece in pieces for part in split_at_feather(piece,join,record['joinFeather'])]
                    for piece in pieces:
                        for i in range(1,len(piece)-1):
                            a,b,c=piece[0],piece[i],piece[i+1]
                            if abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))>1e-9:
                                paving.face([(p[0],p[1],top(p[0],p[1])) for p in [a,b,c]],C['path'])
        # Partial road openings also split the top edge, so compressed side and
        # top faces share the exact same boundary segments.
        for line in record['freeEdges']:
            paving.v.extend((x,y,top(x,y)) for x,y in line)
        paving=conform_edges(paving,record['bounds'])
        # Source storage uses float32. A subdivided original edge can arrive
        # from two slightly different planes; share one final vertex height.
        shared={}
        for x,y,z in paving.v:
            xy=tuple(Vector((x,y)));shared.setdefault(xy,z)
        paving.v=[(x,y,shared[tuple(Vector((x,y)))]) for x,y,z in paving.v]
        terrain,ground_report=clear_paving_ground(terrain,paving,record)
        side=Mesh();side_count=0
        ring=record['vertices'];ccw=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(ring,ring[1:]+ring[:1]))>0
        # Use the actual top mesh boundary stations to avoid new T junctions.
        all_xy={(round(p[0],6),round(p[1],6)):p[:2] for p in paving.v}
        for line in record['freeEdges']:
            for a,b in zip(line,line[1:]):
                dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy);ts={0.,1.}
                for x,y in all_xy.values():
                    t=((x-a[0])*dx+(y-a[1])*dy)/(length*length)
                    if 0<t<1 and abs((x-a[0])*dy-(y-a[1])*dx)/length<1e-5:ts.add(t)
                stations=[]
                for t in sorted(ts):
                    x,y=a[0]+t*dx,a[1]+t*dy;hit=ground.ray_cast(Vector((x,y,200)),Vector((0,0,-1)),400)[0]
                    if hit is None:raise ValueError('No terrain beneath paving edge')
                    z=top(x,y);bottom=min(hit.z-record['burial'],z-record['burial']);stations.append(((x,y,bottom),(x,y,z)))
                for a,b in zip(stations,stations[1:]):
                    face=[a[0],b[0],b[1],a[1]];side.face(face if ccw else list(reversed(face)),C['path']);side_count+=1
        mesh=Mesh();mesh.add_part('01_原轮廓铺面及局部接缝过渡',paving);mesh.add_part('02_露出边缘封口',side)
        output['paving-'+record['id']]=mesh
        for index,join in enumerate(record['joins']):
            a,b=join['a'],join['b'];length=math.dist(a,b);tx,ty=(b[0]-a[0])/length,(b[1]-a[1])/length;nx,ny=join['inward']
            def rectangle(extra):
                pts=[]
                for along,cross in [(-record['contactSideMargin']-extra,-record['contactDepth']-extra),(length+record['contactSideMargin']+extra,-record['contactDepth']-extra),(length+record['contactSideMargin']+extra,.05+extra),(-record['contactSideMargin']-extra,.05+extra)]:
                    pts.append((a[0]+along*tx+cross*nx,a[1]+along*ty+cross*ny))
                if sum(p[0]*q[1]-q[0]*p[1] for p,q in zip(pts,pts[1:]+pts[:1]))<0:pts.reverse()
                return pts
            roads,contact=contact_road(roads,mesh_triangles(roads),rectangle(0),rectangle(record['joinOverlap']),record['joinOverlap'],record['burial'])
            output[f"paving-{record['id']}-contact-{index}"]=contact
        reports.append({'id':record['id'],'areaMeters2':record['areaMeters2'],'topFaces':len(paving.f),'sideFaces':side_count,'joinFeatherMeters':record['joinFeather'],'originalFootprintPreserved':True,'terrainOutsideFootprintPreserved':True,'groundRepair':ground_report,'dimensionsEstimated':True})
    return terrain,roads,output,reports

def sync_source_pavings(base):
    import bpy
    collection=bpy.data.objects['roads'].users_collection[0]
    for old in list(bpy.context.scene.objects):
        if old.name.startswith('paving-'):
            data=old.data;bpy.data.objects.remove(old,do_unlink=True)
            if data.users==0:bpy.data.meshes.remove(data)
    for key,mesh in base.items():
        if key.startswith('paving-'):mesh.object(key,collection,{'layer':'roads'})
