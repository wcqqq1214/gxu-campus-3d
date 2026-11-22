"""Street threshold of the two-flight east stair at way/957404989 (campus metres)."""

from functools import lru_cache

from mathutils.bvhtree import BVHTree

from geometry import Mesh
from shore_geometry import bounds, overlaps, smooth
from site_geometry import mesh_triangles

# Frozen stair-interface.json; u points downhill onto the road, v north across the tread.
TOE = (-627.77, -831.85, 6.00)
EAST = (0.9996797880281931, 0.02530457286552966)
HALF_WIDTH = 3.61
LONG_SITE = 'site-physics-east-long'
# The southern extension restores the curb formerly opened for the displaced stair.
U_CUTS = (-2.0, -0.65, 0.0, 0.38, 0.95, 1.65, 2.50)
V_CUTS = (-9.50, -4.80, -4.20, -HALF_WIDTH, HALF_WIDTH, 4.20, 4.80)


def _xy(u, v):
    return TOE[0] + EAST[0] * u - EAST[1] * v, TOE[1] + EAST[1] * u + EAST[0] * v


def _uv(x, y):
    dx, dy = x - TOE[0], y - TOE[1]
    return dx * EAST[0] + dy * EAST[1], -dx * EAST[1] + dy * EAST[0]


def _split_at(poly, axis, cut):
    """Clip in the stair frame. Interpolate any per-corner texture coordinates as well."""
    left, right = [], []
    for a, b in zip(poly, poly[1:] + poly[:1]):
        da = _uv(*a[:2])[axis] - cut
        db = _uv(*b[:2])[axis] - cut
        if da <= 1e-9:
            left.append(a)
        if da >= -1e-9:
            right.append(a)
        if min(da, db) < -1e-9 and max(da, db) > 1e-9:
            t = da / (da - db)
            edge = tuple(c + t * (d - c) for c, d in zip(a, b))
            left.append(edge)
            right.append(edge)
    return left, right


def _strips(poly, axis, cuts):
    remaining = poly
    for cut in cuts:
        part, remaining = _split_at(remaining, axis, cut)
        if len(part) >= 3:
            yield part
        if len(remaining) < 3:
            return
    yield remaining


def _refit(mesh, colors, edge_at, road):
    limits = bounds(
        [_xy(u, v) for u in (U_CUTS[0], U_CUTS[-1]) for v in (V_CUTS[0], V_CUTS[-1])]
    )
    result, local = Mesh(), Mesh()
    result.ground_uv_bounds = list(mesh.ground_uv_bounds)
    result.xy_uv_materials = set(mesh.xy_uv_materials)
    for i, face in enumerate(mesh.f):
        pts = [mesh.v[k] for k in face]
        dest = local if overlaps(bounds(pts), limits) else result
        dest.face(pts, mesh.m[i], mesh.face_uvs.get(i))

    for ids, fi in mesh_triangles(local):
        points = [local.v[k] for k in ids]
        tex = local.face_uvs.get(fi)
        if tex:
            uv_by_vertex = dict(zip(local.f[fi], tex))
            points = [(*pt, *uv_by_vertex[k]) for pt, k in zip(points, ids)]
        for row in _strips(points, 1, V_CUTS):
            for poly in _strips(row, 0, U_CUTS):
                material = local.m[fi]
                mid_x, mid_y = (sum(p[j] for p in poly) / len(poly) for j in (0, 1))
                mid_u, mid_v = _uv(mid_x, mid_y)
                if road and U_CUTS[0] < mid_u < U_CUTS[-1]:
                    if abs(mid_v) <= HALF_WIDTH and material == colors['curb']:
                        material = colors['asphalt']
                    elif (
                        V_CUTS[0] < mid_v < -HALF_WIDTH
                        and material == colors['asphalt']
                    ):
                        # Legacy grading preserved the curb triangles, changing only their
                        # material across the old mouth. Recover the 0.30 m edge strip.
                        if mid_u < edge_at(round(mid_v, 4)) + 0.30:
                            material = colors['curb']
                vertices = []
                for x, y, z, *_ in poly:
                    u, v = _uv(x, y)
                    weight = smooth((4.8 - abs(v)) / (4.8 - HALF_WIDTH))
                    weight *= smooth((u + 2.0) / 1.35) * smooth((2.5 - u) / 2.12)
                    # Sheet falls east from the last riser; keep soil below the pavement.
                    level = TOE[2] - 0.02 * u - (0 if road else 0.045)
                    vertices.append((x, y, z + weight * (level - z)))
                for j in range(1, len(poly) - 1):
                    ii = (0, j, j + 1)
                    a, b, c = (vertices[k] for k in ii)
                    # Skip collapsed cuts while retaining upright curb closure faces.
                    ab, ac = (
                        [b[k] - a[k] for k in range(3)],
                        [c[k] - a[k] for k in range(3)],
                    )
                    if (
                        sum(
                            (ab[k] * ac[(k + 1) % 3] - ac[k] * ab[(k + 1) % 3]) ** 2
                            for k in range(3)
                        )
                        > 1e-18
                    ):
                        result.face(
                            [a, b, c],
                            material,
                            [poly[k][3:] for k in ii] if tex else None,
                        )
    return result


def build_physics_street_grade(base, C):
    """Run immediately after build_physics_approaches, before road export splitting."""
    roads = base['roads']
    site = bounds([_xy(u, v) for u in (-2, 3) for v in (-10, 6)])
    faces = [
        face for face in roads.f if overlaps(bounds([roads.v[i] for i in face]), site)
    ]
    surface = BVHTree.FromPolygons(roads.v, faces)

    @lru_cache(maxsize=1024)
    def edge_at(v):
        low, high = -1.0, 1.5
        for _ in range(20):
            u = (low + high) / 2
            hit = surface.ray_cast((*_xy(u, v), 15), (0, 0, -1), 16)[0]
            if hit is None:
                low = u
            else:
                high = u
        return high

    lip = Mesh()
    for i in range(8):
        a = HALF_WIDTH * (i / 4 - 1)
        b = HALF_WIDTH * ((i + 1) / 4 - 1)
        ea, eb = edge_at(a), edge_at(b)
        # Only the measured gap between the straight riser and the oblique street.
        # The far 3 cm is buried so separate quantized meshes cannot show a crack.
        for lo, hi, end_drop in [
            ((-0.025, -0.025), (ea, eb), 0),
            ((ea, eb), (ea + 0.03, eb + 0.03), 0.008),
        ]:
            ring = [
                (lo[0], a, 0),
                (hi[0], a, end_drop),
                (hi[1], b, end_drop),
                (lo[1], b, 0),
            ]
            lip.face(
                [(*_xy(u, v), TOE[2] - 0.02 * u - dz) for u, v, dz in ring],
                C['asphalt'],
            )
    base['roads'] = _refit(roads, C, edge_at, True)
    base['terrain'] = _refit(base['terrain'], C, edge_at, False)
    base[LONG_SITE] = lip
