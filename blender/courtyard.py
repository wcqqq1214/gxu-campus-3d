"""Drape courtyard paving over exact terrain triangles, keeping tree-pit holes."""
import math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from geometry import Mesh
from site_geometry import mesh_triangles, split_convex, ring_distance


def build_courtyard(site, C, elevation, terrain, roads):
    triangles = mesh_triangles(terrain)
    ground = BVHTree.FromPolygons(terrain.v, [ids for ids, _ in triangles], all_triangles=True)
    vs, ts = site['pavingMesh']['vertices'], site['pavingMesh']['triangles']
    offset = site['surfaceOffset']; surface = Mesh(); sides = Mesh()
    bounds = site['gradingBounds']
    nearby = [[terrain.v[i] for i in ids] for ids, _ in triangles
              if max(terrain.v[i][0] for i in ids) >= bounds[0]
              and min(terrain.v[i][0] for i in ids) <= bounds[2]
              and max(terrain.v[i][1] for i in ids) >= bounds[1]
              and min(terrain.v[i][1] for i in ids) <= bounds[3]]
    for k in range(0, len(ts), 3):
        outline = [vs[i] for i in ts[k:k+3]]
        a, b, c = outline
        if (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]) < 0:
            outline.reverse()
        for tri in nearby:
            clipped, _ = split_convex(tri, outline)
            for j in range(1, len(clipped)-1):
                p, q, r = clipped[0], clipped[j], clipped[j+1]
                if abs((q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])) > 1e-9:
                    surface.face([(v[0], v[1], v[2]+offset) for v in [p, q, r]], C[site['material']])
    # Split each exposed edge at terrain triangle boundaries. Both top and
    # side then follow the same piecewise plane, including the tree-pit edges.
    def cross(a, b): return a[0]*b[1]-a[1]*b[0]
    def height(p):
        hit = ground.ray_cast(Vector((*p, 200)), Vector((0, 0, -1)), 400)[0]
        if hit is None: raise ValueError('Missing courtyard terrain')
        return hit.z
    for ring in [site['pavingPolygon'], *site['pavingHoles']]:
        for a, b in zip(ring, ring[1:]):
            delta = (b[0]-a[0], b[1]-a[1]); stations = {0., 1.}
            for tri in nearby:
                for c, d in zip(tri, tri[1:]+tri[:1]):
                    edge = (d[0]-c[0], d[1]-c[1]); denominator = cross(delta, edge)
                    if abs(denominator) < 1e-12: continue
                    diff = (c[0]-a[0], c[1]-a[1])
                    t, u = cross(diff, edge)/denominator, cross(diff, delta)/denominator
                    if 0 < t < 1 and 0 <= u <= 1: stations.add(t)
            points = [(a[0]+delta[0]*t, a[1]+delta[1]*t) for t in sorted(stations)]
            for p, q in zip(points, points[1:]):
                if math.dist(p, q) < 1e-7: continue
                hp, hq = height(p), height(q)
                sides.face([(*p, hp+offset), (*q, hq+offset), (*q, hq-.03), (*p, hp-.03)], C[site['material']])
    mesh = Mesh(); mesh.add_part('01_庭院铺地', surface); mesh.add_part('02_外缘与树池收口', sides)
    if site.get('type')=='forecourt-paths':
        # Bury a short overlap in the unchanged road to cover independent
        # Draco-node quantization. The visible paving remains on the same plane.
        lip=Mesh(); sv=site['seamMesh']['vertices']; st=site['seamMesh']['triangles']
        for k in range(0,len(st),3):
            outline=[sv[i] for i in st[k:k+3]]
            a,b,c=outline
            if (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])<0:outline.reverse()
            for tri in nearby:
                clipped,_=split_convex(tri,outline)
                for j in range(1,len(clipped)-1):
                    points=[clipped[0],clipped[j],clipped[j+1]]
                    a,b,c=points
                    if abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))<1e-9:continue
                    lip.face([(p[0],p[1],p[2]+offset-site['joinBurial']*min(1,ring_distance(p[:2],site['pavingPolygon'])/site['joinOverlap'])) for p in points],C[site['material']])
        mesh.add_part('03_园路接缝浅埋搭接',lip)
    report = {'id': site['id'],
        'pavingFaces': len(surface.f), 'edgeFaces': len(sides.f), 'terrainChanged': False,
        'surfaceOffsetMeters': offset, 'groundBasis': 'Exact current terrain triangle planes; no surveyed courtyard elevation.'}
    if site.get('stairConnection'):
        connection, detail = build_stair_connection(site, C, elevation, height, nearby)
        mesh.add_part('03_庭院与楼梯接面', connection)
        report['stairConnection'] = detail
    return terrain, roads, {'site-'+site['id']: mesh}, [report]


def build_stair_connection(site, C, elevation, ground_height, terrain_triangles):
    """Match both existing edges; split the court seam at its terrain vertices."""
    c = site['stairConnection']; sections = c['sections']; half = c['width']/2
    origin, tangent = c['origin'], c['tangent']
    def cross(a, b): return a[0]*b[1]-a[1]*b[0]
    stations = {s['station'] for s in sections}
    count = math.ceil(c['width']/.2)
    stations.update(-half+c['width']*i/count for i in range(count+1))
    for tri in terrain_triangles:
        for a, b in zip(tri, tri[1:]+tri[:1]):
            edge = [b[i]-a[i] for i in (0, 1)]
            denominator = cross(tangent, edge)
            if abs(denominator) < 1e-12: continue
            delta = [a[i]-origin[i] for i in (0, 1)]
            s, t = cross(delta, edge)/denominator, cross(delta, tangent)/denominator
            if -half < s < half and 0 <= t <= 1: stations.add(s)
    platform = elevation(*c['hostCenter'])+c['platformOffset']
    rows = []
    for station in sorted(stations):
        left, right = next((a, b) for a, b in zip(sections, sections[1:]) if a['station']-1e-8 <= station <= b['station']+1e-8)
        t = (station-left['station'])/(right['station']-left['station'])
        start, end = [[a+(b-a)*t for a, b in zip(left[key], right[key])] for key in ('start', 'end')]
        rows.append([(*start, ground_height(start)+site['surfaceOffset']), (*end, platform)])
    mesh = Mesh(); slopes = []; clearance = []
    for left, right in zip(rows, rows[1:]):
        if math.dist(left[0], right[0]) < 1e-7: continue
        for face in [(left[0], left[1], right[0]), (left[1], right[1], right[0])]:
            mesh.face(face, C[site['material']])
            # Dense barycentric probes catch a terrain ridge under the short fill.
            for i in range(9):
                for j in range(9-i):
                    p = [face[0][k]*(1-(i+j)/8)+face[1][k]*i/8+face[2][k]*j/8 for k in (0, 1, 2)]
                    clearance.append(p[2]-ground_height(p[:2]))
        for start, end in (left, right): slopes.append(abs(end[2]-start[2])/math.dist(start[:2], end[:2]))
    if min(clearance) < .02 or max(slopes) > .12:
        raise ValueError('Courtyard connection is buried or has excessive model grade')
    # End caps are embedded in the two existing surfaces; only the short sides
    # are exposed. Their bottoms extend into the original terrain.
    for a, b in [rows[0], list(reversed(rows[-1]))]:
        mesh.face([a, (*a[:2], ground_height(a[:2])-.03),
                   (*b[:2], ground_height(b[:2])-.03), b], C[site['material']])
    return mesh, dict(faces=len(mesh.f), minimumTerrainClearanceMeters=min(clearance),
                     maximumGrade=max(slopes), platformHeightMeters=platform,
                     widthMeters=c['width'], areaMeters2=c['areaMeters2'],
                     note='Estimated model continuity only; no surveyed slope or accessibility claim.')
