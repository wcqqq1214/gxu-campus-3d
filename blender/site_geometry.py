"""Grade a small forecourt against real terrain and road triangles, both LODs."""
import bisect,math,bpy
from functools import lru_cache
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from geometry import Mesh

def mesh_triangles(mesh):
    data=bpy.data.meshes.new('site-sampling')
    data.from_pydata(mesh.v,[],mesh.f);data.calc_loop_triangles()
    triangles=[(tuple(t.vertices),t.polygon_index) for t in data.loop_triangles]
    bpy.data.meshes.remove(data)
    return triangles

def inside(p,ring):
    x,y=p;result=False
    for a,b in zip(ring,ring[1:]+ring[:1]):
        if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:result=not result
    return result

def ring_distance(p,ring):
    best=math.inf
    for a,b in zip(ring,ring[1:]+ring[:1]):
        dx=b[0]-a[0];dy=b[1]-a[1];d=dx*dx+dy*dy
        t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/d)) if d else 0
        best=min(best,math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy))
    return best

def polygon_distance(p,rings):
    if inside(p,rings[0]) and not any(inside(p,r) for r in rings[1:]):return 0
    return min(ring_distance(p,r) for r in rings)

def split_convex(points,outline):
    """Partition a 3D triangle by a convex XY mask, interpolating its plane."""
    current=list(points);outside=[]
    for a,b in zip(outline,outline[1:]+outline[:1]):
        if not current:break
        def side(p):return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])
        positive=[];negative=[]
        for p,q in zip(current,current[1:]+current[:1]):
            u,v=side(p),side(q)
            (positive if u>=0 else negative).append(p)
            if (u>=0)!=(v>=0):
                t=u/(u-v);cross=tuple(p[k]+(q[k]-p[k])*t for k in range(3))
                positive.append(cross);negative.append(cross)
        if len(negative)>=3:outside.append(negative)
        current=positive
    return current,outside

def contact_road(roads,triangles,outline,outer_outline,overlap,burial):
    """Move only original contact-band triangles to a small, precise node."""
    contact=Mesh();rest=Mesh();xmin=min(p[0] for p in outer_outline);xmax=max(p[0] for p in outer_outline)
    ymin=min(p[1] for p in outer_outline);ymax=max(p[1] for p in outer_outline);selected=set()
    for ids,face in triangles:
        points=[roads.v[i] for i in ids]
        if max(p[0] for p in points)>=xmin and min(p[0] for p in points)<=xmax and max(p[1] for p in points)>=ymin and min(p[1] for p in points)<=ymax:selected.add(face)
    for i,face in enumerate(roads.f):
        if i not in selected:rest.face([roads.v[k] for k in face],roads.m[i])
    for ids,face in triangles:
        if face not in selected:continue
        kept,removed=split_convex([roads.v[i] for i in ids],outline)
        expanded,_=split_convex([roads.v[i] for i in ids],outer_outline)
        _,aprons=split_convex(expanded,outline)
        aprons=[[(p[0],p[1],p[2]-burial*min(1,ring_distance(p[:2],outline)/overlap)) for p in ring] for ring in aprons]
        for mesh,pieces in [(contact,[kept]+aprons),(rest,removed)]:
            for piece in pieces:
                for j in range(1,len(piece)-1):
                    a,b,c=piece[0],piece[j],piece[j+1]
                    if abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))>1e-9:
                        mesh.face([a,b,c],roads.m[face])
    return rest,contact

def sync_source_sites(base):
    """Keep editable site meshes paired with a regenerated base export."""
    import bpy
    collection=bpy.data.objects['roads'].users_collection[0]
    for old in list(bpy.context.scene.objects):
        if old.get('siteId') or old.name.startswith('site-'):
            data=old.data;bpy.data.objects.remove(old,do_unlink=True)
            if data is not None and data.users==0:bpy.data.meshes.remove(data)
    for key,mesh in base.items():
        if key.startswith('site-'):
            mesh.object(key,collection,{'layer':'roads','siteId':key[5:]})


def build_sites(data,C,elevation,terrain,roads):
    meshes={};reports=[]
    for site in data['sites']:
        if site.get('type') in ('entry-apron','gallery-apron'):
            from entry_apron import build_entry_apron
            terrain,roads,added,rows=build_entry_apron(site,C,elevation,terrain,roads)
        elif site.get('type') in ('side-connection','front-connection'):
            from side_connection import build_side_connection
            terrain,roads,added,rows=build_side_connection(site,C,elevation,terrain,roads)
        else:terrain,roads,added,rows=build_single_site({'sites':[site]},C,elevation,terrain,roads)
        meshes.update(added);reports.extend(rows)
    return terrain,roads,meshes,reports

def build_single_site(data,C,elevation,terrain,roads):
    """Roads are assembled before grading, so existing road surfaces stay fixed.

    Only affected original terrain faces are replaced. Their actual Blender
    triangles are subdivided with barycentric coordinates: outside the local
    grading halo every point remains on the old triangle plane. Shared edges
    use the same subdivision count, including the old quad diagonal.
    """
    if not data['sites']:return terrain,roads,{},[]
    if len(data['sites'])!=1:raise ValueError('Only one site grading field is supported')
    old_triangles=mesh_triangles(terrain)
    road_triangles=mesh_triangles(roads)
    ground=BVHTree.FromPolygons(terrain.v,[t for t,_ in old_triangles],all_triangles=True)
    road=BVHTree.FromPolygons(roads.v,[t for t,_ in road_triangles],all_triangles=True)
    samplers=[];meshes={};reports=[]
    for site in data['sites']:
        angle=site['angle'];cs=math.cos(angle);sn=math.sin(angle);ox,oy=site['origin']
        def world(x,y):return ox+x*cs-y*sn,oy+x*sn+y*cs
        def local(x,y):return (x-ox)*cs+(y-oy)*sn,-(x-ox)*sn+(y-oy)*cs
        z=elevation(*site['buildingCenter']);columns=site['columns'];xs=[p[0] for p in columns]
        start=site['startY'];clearance=site['groundClearance'];feather=site['gradingFeather']
        def road_level(x,y):
            # Query just inside the existing road, then extrapolate its plane
            # back to the exact shared edge. No synthetic +0.40 m site offset.
            wx,wy=world(x,y);qx,qy=world(x,y+.025)
            hit,normal,_,_=road.ray_cast(Vector((qx,qy,z+100)),Vector((0,0,-1)),200)
            if hit is None or abs(normal.z)<.5:raise ValueError('Missing road surface at site join')
            return hit.z+(normal.x*(hit.x-wx)+normal.y*(hit.y-wy))/normal.z
        ends=[road_level(x,y) for x,y in columns]
        def end_at(x):
            x=max(xs[0],min(xs[-1],x));i=min(len(xs)-2,max(0,bisect.bisect_right(xs,x)-1))
            t=(x-xs[i])/(xs[i+1]-xs[i])
            return columns[i][1]*(1-t)+columns[i+1][1]*t,ends[i]*(1-t)+ends[i+1]*t
        def level(x,y):
            end,h=end_at(x);t=max(0,min(1,(y-start)/(end-start)))
            return z+(h-z)*t
        core=site['gradingCore'];exclusions=site['gradingExclusions']
        def graded(x,y,original):
            lx,ly=local(x,y)
            distance=0 if inside((lx,ly),core) else ring_distance((lx,ly),core)
            weight=max(0,1-distance/feather)
            if not weight:return original
            # Preserve building foundations, even when the halo extends under
            # a neighbouring wing; gently taper within 0.75 m of its boundary.
            if exclusions:weight*=min(1,min(polygon_distance((lx,ly),p) for p in exclusions)/.75)
            target=min(original,level(lx,ly)-clearance)
            return original+(target-original)*weight
        samplers.append((site,graded))
        mesh=Mesh();surface=Mesh();edge=Mesh();join=Mesh()
        rows=max(1,math.ceil(max(y-start for _,y in columns)/site['meshStep']))
        def point(i,j):
            x,end=columns[i];t=j/rows;y=start+(end-start)*t
            wx,wy=world(x,y);return (wx,wy,z+(ends[i]-z)*t)
        for i in range(len(columns)-1):
            for j in range(rows):
                a,b,c,d=point(i,j),point(i+1,j),point(i+1,j+1),point(i,j+1)
                surface.face([a,b,c],C[site['material']]);surface.face([a,c,d],C[site['material']])
        @lru_cache(None)
        def bottom(p):
            hit=ground.ray_cast(Vector((p[0],p[1],z+100)),Vector((0,0,-1)),200)[0]
            if hit is None:raise ValueError('Missing terrain under site')
            return p[0],p[1],min(p[2]-.04,graded(p[0],p[1],hit.z)-.03)
        # Side faces close down into the graded terrain; road edge stays open.
        boundary=[(point(0,j+1),point(0,j)) for j in range(rows)]
        boundary += [(point(len(columns)-1,j),point(len(columns)-1,j+1)) for j in range(rows)]
        boundary += [(point(i,0),point(i+1,0)) for i in range(len(columns)-1)]
        for a,b in boundary:edge.face([a,b,bottom(b),bottom(a)],C[site['material']])
        # A buried 20 cm lip prevents a hairline after independent Draco
        # quantization of the small forecourt and campus-wide road meshes.
        # It slopes below the old pavement; it is not another visible road.
        for i in range(len(columns)-1):
            a,b=point(i,rows),point(i+1,rows);far=[]
            for k in [i,i+1]:
                x,y=columns[k];y+=site['joinOverlap'];wx,wy=world(x,y)
                far.append((wx,wy,road_level(x,y)-clearance))
            join.face([a,b,far[1],far[0]],C[site['material']])
        # The old curb/asphalt seam also crosses this contact band. Give it the
        # small site's quantization range, without changing road height or
        # materials. Original visible triangles are partitioned; a buried lip
        # also closes the far edge against the coarser campus-wide road node.
        x0=xs[0]-site['roadContactSideMargin'];x1=xs[-1]+site['roadContactSideMargin']
        slope=(columns[-1][1]-columns[0][1])/(xs[-1]-xs[0])
        y0=columns[0][1]+slope*(x0-xs[0]);y1=columns[-1][1]+slope*(x1-xs[-1])
        outline=[world(x0,y0-.15),world(x1,y1-.15),world(x1,y1+site['roadContactDepth']),world(x0,y0+site['roadContactDepth'])]
        overlap=site['joinOverlap'];xa=x0-overlap;xb=x1+overlap
        ya=y0-slope*overlap;yb=y1+slope*overlap;depth=site['roadContactDepth']
        outer=[world(xa,ya-.15-overlap),world(xb,yb-.15-overlap),world(xb,yb+depth+overlap),world(xa,ya+depth+overlap)]
        roads,contact=contact_road(roads,road_triangles,outline,outer,overlap,clearance)
        mesh.add_part('01_道路至台阶铺地',surface);mesh.add_part('02_铺地侧面收口',edge);mesh.add_part('03_路边埋入接缝',join)
        mesh.add_part('04_主路接口原铺面',contact)
        meshes['site-'+site['id']]=mesh
        reports.append({'id':site['id'],'stairBaseElevation':z,'roadEdgeElevations':ends,
                        'pavingFaces':len(surface.f),'relocatedRoadFaces':len(contact.f),'source':'actual terrain/road mesh triangles',
                        'estimatedDimensions':True})
    site,graded=samplers[0];bounds=site['gradingBounds'];n=site['terrainSubdivisions']
    affected=set()
    for ids,face in old_triangles:
        p=[terrain.v[i] for i in ids]
        if max(v[0] for v in p)>=bounds[0] and min(v[0] for v in p)<=bounds[2] and max(v[1] for v in p)>=bounds[1] and min(v[1] for v in p)<=bounds[3]:affected.add(face)
    result=Mesh()
    for i,face in enumerate(terrain.f):
        if i not in affected:result.face([terrain.v[k] for k in face],terrain.m[i])
    changed=[]
    for ids,face in old_triangles:
        if face not in affected:continue
        a,b,c=[terrain.v[i] for i in ids]
        def vertex(i,j):
            p=tuple(a[k]+(b[k]-a[k])*i/n+(c[k]-a[k])*j/n for k in range(3))
            h=graded(p[0],p[1],p[2]);changed.append(p[2]-h)
            return p[0],p[1],h
        grid={(i,j):vertex(i,j) for i in range(n+1) for j in range(n+1-i)}
        for i in range(n):
            for j in range(n-i):
                result.face([grid[i,j],grid[i+1,j],grid[i,j+1]],terrain.m[face])
                if i+j<n-1:result.face([grid[i+1,j],grid[i+1,j+1],grid[i,j+1]],terrain.m[face])
    reports[0].update(replacedOriginalTerrainFaces=len(affected),maxTerrainLowering=max(changed,default=0),
                      addedTerrainFaces=len(result.f)-len(terrain.f))
    return result,roads,meshes,reports
