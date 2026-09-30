"""Bounded foundation clearance on actual terrain and ordinary road triangles."""
from geometry import Mesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from functools import lru_cache
from site_geometry import mesh_triangles, split_convex, polygon_distance, ring_distance
from shore_geometry import bounds, overlaps, triangles_into, conform_edges


def masks_for(triangles):
    result = []
    for points in triangles:
        if sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(points,points[1:]+points[:1])) < 0:
            points = list(reversed(points))
        result.append((points,bounds(points)))
    return result


def clipped_mesh(mesh, masks, area, transform=None, ceiling=None):
    """Keep original planes outside the mask; optionally drop masked road tops."""
    selected = {i for i,f in enumerate(mesh.f)
                if overlaps(bounds([mesh.v[k] for k in f]),area)
                and (ceiling is None or max(mesh.v[k][2] for k in f)>ceiling+.0001)}
    if not selected:
        return mesh, {'affectedTriangles':0,'maximumLoweringMeters':0}
    result = Mesh(); affected = 0; maximum = 0
    for i,f in enumerate(mesh.f):
        if i not in selected:
            result.face([mesh.v[k] for k in f],mesh.m[i])
    for ids,face in mesh_triangles(mesh):
        if face not in selected:
            continue
        points = [mesh.v[k] for k in ids]; remaining = [points]; pieces = []
        for outline,bb in masks:
            leftovers = []
            for part in remaining:
                if not overlaps(bounds(part),bb):
                    leftovers.append(part); continue
                kept,outside = split_convex(part,outline)
                if len(kept)>=3:
                    pieces.append(kept)
                leftovers.extend(outside)
            remaining = leftovers
        for piece in remaining:
            triangles_into(result,piece,mesh.m[face])
        for piece in pieces:
            if transform:
                graded = [transform(p) for p in piece]
                maximum = max(maximum,max(p[2]-q[2] for p,q in zip(piece,graded)))
                triangles_into(result,graded,mesh.m[face])
        affected += bool(pieces)
    touched = bounds([mesh.v[k] for i in selected for k in mesh.f[i]])
    result = conform_edges(result,tuple(v+(-1 if i<2 else 1) for i,v in enumerate(touched)))
    return result, {'affectedTriangles':affected,'maximumLoweringMeters':maximum}


def simplify_local_planes(mesh, record):
    """Remove coplanar clipping diagonals, retaining every boundary vertex."""
    import bmesh
    from mathutils import Vector
    flat = {i for i,f in enumerate(mesh.f)
            if overlaps(bounds([mesh.v[k] for k in f]),record['bounds'])}
    if not flat:
        return mesh
    bm = bmesh.new(); vertices = {}; retained = []
    for i in flat:
        verts = []
        for k in mesh.f[i]:
            p = mesh.v[k]; key = tuple(round(x,6) for x in p)
            if key not in vertices: vertices[key] = bm.verts.new(Vector(p))
            verts.append(vertices[key])
        if len(set(verts))>=3:
            try:
                face = bm.faces.new(verts); face.material_index = mesh.m[i]
            except ValueError:
                retained.append(i)
        else:
            retained.append(i)
    bm.normal_update()
    edges = [e for e in bm.edges if len(e.link_faces)==2
             and e.link_faces[0].material_index==e.link_faces[1].material_index
             and e.link_faces[0].normal.dot(e.link_faces[1].normal)>0
             and e.link_faces[0].normal.cross(e.link_faces[1].normal).length < 1e-6]
    bmesh.ops.dissolve_edges(bm,edges=edges,use_verts=False,use_face_split=False)
    # Preserve every boundary vertex so adjacent retained triangles still meet.
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    result = Mesh()
    for i,f in enumerate(mesh.f):
        if i not in flat or i in retained: result.face([mesh.v[k] for k in f],mesh.m[i])
    for f in bm.faces:
        result.face([tuple(v.co) for v in f.verts],f.material_index)
    bm.free()
    return result


def build_foundations(data,terrain,roads):
    reports = []
    for record in data['foundations']:
        target = record['datum']+record['groundOffset']
        def grade(p):
            dcore = min(polygon_distance(p[:2],poly) for poly in record['corePolygons'])
            # Distance to every exterior and hole boundary makes all retained
            # road/site edges meet their unchanged ground plane continuously.
            dedge = min(ring_distance(p[:2],ring) for poly in record['gradingPolygons'] for ring in poly)
            weight = 1 if dcore < 1e-6 else dedge/(dcore+dedge)
            return p[0],p[1],p[2]-max(0,p[2]-target)*weight
        original = BVHTree.FromPolygons(terrain.v,[ids for ids,_ in mesh_triangles(terrain)],all_triangles=True)
        before = sum(len(f)-2 for f in terrain.f)+sum(len(f)-2 for f in roads.f)
        terrain,ground_report = clipped_mesh(terrain,masks_for(record['coreMasks']+record['transitionMasks']),
                                            record['bounds'],grade,ceiling=target)
        # Edge conformity adds points on graded triangle planes. Those planes
        # approximate a nonlinear field, so re-evaluate shared edge points from
        # original ground to prevent differing Z on opposite sides of a seam.
        @lru_cache(maxsize=None)
        def shared_point(x,y):
            hit=original.ray_cast(Vector((x,y,150)),Vector((0,0,-1)),300)[0]
            if hit is None:raise ValueError('Missing original foundation ground')
            return grade((x,y,hit.z))
        area=record['bounds']
        for i,(x,y,z) in enumerate(terrain.v):
            if area[0]-1e-5<=x<=area[2]+1e-5 and area[1]-1e-5<=y<=area[3]+1e-5:
                if min(polygon_distance((x,y),poly) for poly in record['gradingPolygons'])<1e-5:
                    terrain.v[i]=shared_point(x,y)
        terrain = simplify_local_planes(terrain,record)
        roads,road_report = clipped_mesh(roads,masks_for(record['roadTrimMasks']),record['roadTrimBounds'])
        after = sum(len(f)-2 for f in terrain.f)+sum(len(f)-2 for f in roads.f)
        reports.append({'id':record['id'],'terrain':ground_report,'roads':road_report,
                        'triangleDelta':after-before,'datum':record['datum'],'gradingBounds':record['bounds']})
    return terrain,roads,reports
