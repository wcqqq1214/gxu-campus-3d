"""Seat the former Xingjian gym's athletics field on its own five-sided site."""

from copy import copy
from math import hypot

from geometry import Mesh
from shore_geometry import bounds, conform_edges, overlaps
from site_geometry import mesh_triangles
from west22_ground import split

# The original sports-ground boundary, in campus metres, counterclockwise.
RING = (
    (-359.6220289961371, 1221.5215463392965),
    (-321.0070237858766, 1217.0514489897766),
    (-231.446, 1208.44),
    (-227.115, 1271.893),
    (-347.312, 1285.993),
)
BOX = bounds(RING)
EDGES = []
for a, b in zip(RING, RING[1:] + RING[:1]):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = hypot(dx, dy)
    EDGES.append((-dy / length, dx / length, a))


def formation(x, y):
    # A single estimated plane, anchored to the existing external approach grades.
    # It falls 1.2 m per 100 m to the west and 0.6 m per 100 m to the south.
    return -2.33 + 0.012 * (x + 290.462) + 0.006 * (y - 1247.804)


def valid(poly):
    if len(poly) < 3:
        return False
    a = poly[0]
    return (
        abs(
            sum(
                (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])
                for b, c in zip(poly[1:-1], poly[2:])
            )
        )
        > 1e-8
    )


def edge_distance(edge, p):
    nx, ny, a = edge
    return nx * (p[0] - a[0]) + ny * (p[1] - a[1])


def partition(poly, offset):
    """Cut/fill with a continuous lower envelope. No displacement at the site edge."""
    for edge in EDGES:
        poly, outside = split(poly, lambda p: edge_distance(edge, p))
        if valid(outside):
            yield outside
        if not valid(poly):
            return

    def delta(p):
        return formation(*p[:2]) + offset - p[2]

    up, down = split(poly, delta)
    if max(abs(delta(p)) for p in poly) < 1e-9:
        yield poly
        return
    for sign, face in [(1, up), (-1, down)]:
        if not valid(face):
            continue
        # At a given point, the smallest allowance controls the elevation.
        limits = [lambda p: sign * delta(p)]
        limits.extend(lambda p, e=e: 0.112 * edge_distance(e, p) for e in EDGES)
        for i, limit in enumerate(limits):
            fragment = face
            for j, other in enumerate(limits):
                if i == j:
                    continue
                fragment, _ = split(fragment, lambda p: other(p) - limit(p))
                if not valid(fragment):
                    break
            if valid(fragment):
                yield [(x, y, z + sign * limit((x, y, z))) for x, y, z in fragment]


def grade_ground(mesh, material=None):
    # Keep global vertices/UV dictionaries/metadata; operate on a small local mesh.
    result = copy(mesh)
    result.v = list(mesh.v)
    result.f, result.m, result.face_uvs = [], [], {}
    local = Mesh()
    for i, (face, mat) in enumerate(zip(mesh.f, mesh.m)):
        pts = [mesh.v[j] for j in face]
        if (material is None or material == mat) and overlaps(bounds(pts), BOX):
            if i in mesh.face_uvs:
                raise ValueError(
                    'Xingjian sports ground no longer uses planar UV mapping'
                )
            local.face(pts, mat)
        else:
            if i in mesh.face_uvs:
                result.face_uvs[len(result.f)] = mesh.face_uvs[i]
            result.f.append(face)
            result.m.append(mat)
    cut = Mesh()
    for tri, i in mesh_triangles(local):
        for poly in partition(
            [local.v[j] for j in tri], 0 if material is None else 0.14
        ):
            for k in range(1, len(poly) - 1):
                triangle = [poly[0], poly[k], poly[k + 1]]
                if valid(triangle):
                    cut.face(triangle, local.m[i])
    if cut.f:
        # Reconcile collinear edge cuts before Draco position quantization.
        repaired = conform_edges(cut, bounds(cut.v))
        result.extend(repaired)
    return result


def apply(base, colors):
    terrain, sports = base['terrain'], base['north-campus-sports']
    if getattr(terrain, 'xingjian_athletics_graded', False):
        return
    running = colors['track']
    apron = colors['trackApron']
    pitch = colors['pitch']
    markings = colors['sportWhite']
    running_z = {
        round(sports.v[j][2], 6)
        for face, mat in zip(sports.f, sports.m)
        if mat == running
        for j in face
    }
    if len(running_z) != 1:
        raise ValueError('Expected the original horizontal Xingjian track')
    datum = running_z.pop()

    # The original apron contains both the complete hardstand and a separate
    # 1.88 m breasting strip. The graded hardstand supplies that strip's surface.
    surface = Mesh()
    surface.xy_uv_materials = sports.xy_uv_materials.copy()
    surface.ground_uv_bounds = list(sports.ground_uv_bounds)
    for i, (face, mat) in enumerate(zip(sports.f, sports.m)):
        pts = [sports.v[j] for j in face]
        if mat == apron and len(face) == 4:
            continue
        if mat in (running, pitch, markings):
            pts = [(x, y, formation(x, y) + 0.19 + (z - datum)) for x, y, z in pts]
        surface.face(pts, mat, sports.face_uvs.get(i))
    graded = grade_ground(terrain)
    graded_sports = grade_ground(surface, apron)
    graded.xingjian_athletics_graded = True
    base['terrain'], base['north-campus-sports'] = graded, graded_sports
