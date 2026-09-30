"""Bounded foundation clearance on actual terrain and ordinary road triangles."""
from geometry import Mesh
from site_geometry import mesh_triangles, split_convex, polygon_distance, ring_distance
from shore_geometry import bounds, overlaps, triangles_into, conform_edges


def masks_for(triangles):
    result = []
    for points in triangles:
        if sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(points,points[1:]+points[:1])) < 0:
            points = list(reversed(points))
        result.append((points,bounds(points)))
    return result


def clipped_mesh(mesh, masks, area, retain_masked=False, ceiling=None):
    """Clip and conform original planes; retain masked terrain or drop road tops.

    Grading must happen after conformity, so inserted points are interpolated
    from the original surface rather than a piecewise approximation of a grade.
    """
    selected = {i for i,f in enumerate(mesh.f)
                if overlaps(bounds([mesh.v[k] for k in f]),area)
                and (ceiling is None or max(mesh.v[k][2] for k in f)>ceiling+.0001)}
    if not selected:
        return mesh, {'affectedTriangles':0,'maximumLoweringMeters':0}
    result = Mesh(); affected = 0
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
            if retain_masked:
                triangles_into(result,piece,mesh.m[face])
        affected += bool(pieces)
    if not affected:
        # Bounding-box overlap alone must not retriangulate a retained road.
        return mesh, {'affectedTriangles':0,'maximumLoweringMeters':0}
    touched = bounds([mesh.v[k] for i in selected for k in mesh.f[i]])
    result = conform_edges(result,tuple(v+(-1 if i<2 else 1) for i,v in enumerate(touched)))
    return result, {'affectedTriangles':affected,'maximumLoweringMeters':0}


def simplify_local_planes(mesh, record, *, normal_tolerance=1e-6, weld_distance=0):
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
    if weld_distance:
        bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=weld_distance)
    bm.normal_update()
    edges = [e for e in bm.edges if len(e.link_faces)==2
             and e.link_faces[0].material_index==e.link_faces[1].material_index
             and e.link_faces[0].normal.dot(e.link_faces[1].normal)>0
             and e.link_faces[0].normal.cross(e.link_faces[1].normal).length < normal_tolerance]
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
        before = sum(len(f)-2 for f in terrain.f)+sum(len(f)-2 for f in roads.f)
        terrain,ground_report = clipped_mesh(terrain,masks_for(record['coreMasks']+record['transitionMasks']),
                                            record['bounds'],retain_masked=True,ceiling=target)
        # Conform while faces still carry their original planes. Each new
        # edge point then retains its own surface height, even where two
        # surfaces share XY coordinates at different elevations.
        area=record['bounds'];maximum=0
        for i,p in enumerate(terrain.v):
            x,y,z=p
            if area[0]-1e-5<=x<=area[2]+1e-5 and area[1]-1e-5<=y<=area[3]+1e-5:
                # Preserve the edge through float32 coordinate roundoff.
                if min(ring_distance((x,y),ring) for poly in record['gradingPolygons'] for ring in poly)<1e-4:
                    continue
                if min(polygon_distance((x,y),poly) for poly in record['gradingPolygons'])<1e-5:
                    q=grade(p);terrain.v[i]=q;maximum=max(maximum,z-q[2])
        ground_report['maximumLoweringMeters']=maximum
        simplification=record.get('meshSimplification',{})
        terrain = simplify_local_planes(terrain,record,
            normal_tolerance=simplification.get('normalTolerance',1e-6),
            weld_distance=simplification.get('weldDistance',0))
        roads,road_report = clipped_mesh(roads,masks_for(record['roadTrimMasks']),record['roadTrimBounds'])
        after = sum(len(f)-2 for f in terrain.f)+sum(len(f)-2 for f in roads.f)
        reports.append({'id':record['id'],'terrain':ground_report,'roads':road_report,
                        'triangleDelta':after-before,'datum':record['datum'],'gradingBounds':record['bounds']})
    return terrain,roads,reports
