"""Drape courtyard paving over exact terrain triangles, keeping tree-pit holes."""
import math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from geometry import Mesh
from site_geometry import mesh_triangles, split_convex


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
    return terrain, roads, {'site-'+site['id']: mesh}, [{'id': site['id'],
        'pavingFaces': len(surface.f), 'edgeFaces': len(sides.f), 'terrainChanged': False,
        'surfaceOffsetMeters': offset, 'groundBasis': 'Exact current terrain triangle planes; no surveyed courtyard elevation.'}]
