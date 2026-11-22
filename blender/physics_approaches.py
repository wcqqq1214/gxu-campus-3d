"""East stair aprons at the physics building, in campus metres (east, north, up).

2019-03-05 Baidu stations 09007200121903051340349379B (220 degrees) and
09007200121903051340367259B (239 degrees) show two separate asphalt openings.
Toe datums follow the existing flights. The road crossfall and shoulder blend
are model fits; the panoramas supply no surveyed heights.
"""

from functools import lru_cache

from mathutils.bvhtree import BVHTree

from geometry import Mesh
from shore_geometry import bounds, conform_edges, overlaps, smooth, triangles_into
from site_geometry import mesh_triangles, split_convex

# Last riser ends, not last tread tops. Keep the two approaches distinct.
FLIGHTS = {
    'short': (-630.56, -858.64, 9.20, 6.335),
    'long': (-629.26, -837.25, 7.20, 5.978),
}
EXTENT = (-632.0, -889.0, -604.0, -807.0)
CORE = (-630.65, -863.55, -618.35, -833.0)
CROSSFALL = 0.04


def street_level(x, y):
    sx, sy, sw, sz = FLIGHTS['short']
    lx, ly, lw, lz = FLIGHTS['long']
    t = smooth((y - sy - sw / 2) / (ly - lw / 2 - sy - sw / 2))
    return (sz - CROSSFALL * (x - sx)) * (1 - t) + (lz - CROSSFALL * (x - lx)) * t


def end_blend(t):
    # Near-linear through most of the bounded return. A full smoothstep
    # concentrates the old DEM discrepancy into a short steep middle section.
    t = max(0.0, min(1.0, t))
    return 0.85 * t + 0.15 * smooth(t)


def graded_point(p, offset, soil_z):
    x, y, z = p
    a, b, c, d = EXTENT
    i, j, k, l = CORE
    weight = (
        smooth((x - a) / (i - a))
        * end_blend((y - b) / (j - b))
        * end_blend((d - y) / (d - l))
    )
    target = street_level(x, y) + offset
    if x > k:
        # A section goes from the corrected street shoulder to the actual soil
        # at the far boundary. Blending at the local DEM height instead would
        # compound its old steep crossfall. Keep any road/paint reveal at c.
        t = (x - k) / (c - k)
        height_at_boundary = soil_z(c, y) + z - soil_z(x, y)
        target = (street_level(k, y) + offset) * (1 - t) + height_at_boundary * t
    return x, y, z + weight * (target - z)


def rectangle(a, b, c, d):
    return [(a, b), (c, b), (c, d), (a, d)]


def grade_layer(mesh, colors, road, soil_z):
    """Re-triangulate only the bounded ground and keep adjacent faces and UVs."""
    area = rectangle(*EXTENT)
    result = Mesh()
    result.xy_uv_materials = mesh.xy_uv_materials.copy()
    result.ground_uv_bounds = mesh.ground_uv_bounds.copy()
    local = Mesh()
    original = {}
    for i, face in enumerate(mesh.f):
        pts = [mesh.v[k] for k in face]
        if overlaps(bounds(pts), EXTENT):
            original[i] = pts
        else:
            result.face(pts, mesh.m[i], mesh.face_uvs.get(i))
    a, b, c, d = EXTENT
    xs = sorted(
        {
            a,
            c,
            CORE[0],
            CORE[2],
            -629.26,
            -627.7,
            -626.4,
            -623,
            -620,
            -616,
            -613,
            -610,
            -607,
        }
    )
    ys = sorted(
        {b, d, CORE[1], CORE[3], *range(-887, -807, 4)}
        | {y + side * w / 2 for _, y, w, _ in FLIGHTS.values() for side in (-1, 1)}
    )
    paint = {colors['roadYellow'], colors['roadWhite']}
    for ids, fi in mesh_triangles(mesh):
        if fi not in original:
            continue
        material = mesh.m[fi]
        pts = [mesh.v[k] for k in ids]
        # XY area clippers omit buried vertical closures. Retain their source geometry.
        normal_z = (pts[1][0] - pts[0][0]) * (pts[2][1] - pts[0][1]) - (
            pts[1][1] - pts[0][1]
        ) * (pts[2][0] - pts[0][0])
        if abs(normal_z) < 1e-9:
            local.face(pts, material)
            continue
        kept, exterior = split_convex(pts, area)
        for part in exterior:
            triangles_into(local, part, material)
        if not kept:
            continue
        x0, y0, x1, y1 = bounds(kept)
        for left, right in zip(xs, xs[1:]):
            if left >= x1 or right <= x0:
                continue
            for lo, hi in zip(ys, ys[1:]):
                if lo >= y1 or hi <= y0:
                    continue
                poly, _ = split_convex(kept, rectangle(left, lo, right, hi))
                if len(poly) < 3:
                    continue
                finish = material
                if road and material == colors['curb']:
                    cx = sum(p[0] for p in poly) / len(poly)
                    if cx < -625 and any(
                        y - w / 2 <= lo and hi <= y + w / 2
                        for _, y, w, _ in FLIGHTS.values()
                    ):
                        finish = colors['asphalt']
                # Preserve paint above the running course. The lawn meets its
                # outer edge with a 4.5 cm kerb reveal in the corrected section.
                offset = (0.024 if material in paint else 0.0) if road else -0.045

                def level(p):
                    return graded_point(p, offset, soil_z)

                triangles_into(local, poly, finish, level)
    # Exterior terrain triangles also need the new vertices along the cut.
    # Without them a long west edge and its short neighbors quantize apart.
    result.extend(local if road else conform_edges(local, EXTENT))
    return result


def build_physics_approaches(base, colors):
    roads = base['roads']
    # Locate the westernmost actual road edge independently at each opening.
    nearby = [
        f
        for f in roads.f
        if overlaps(bounds([roads.v[i] for i in f]), (-629, -864, -625, -832))
    ]
    tree = BVHTree.FromPolygons(roads.v, nearby)

    def edge(toe, y):
        lo, hi = toe, -625.5
        if tree.ray_cast((hi, y, 20), (0, 0, -1))[0] is None:
            raise ValueError(f'Missing physics street at {hi}, {y}')
        for _ in range(20):
            x = (lo + hi) * 0.5
            if tree.ray_cast((x, y, 20), (0, 0, -1))[0] is None:
                lo = x
            else:
                hi = x
        return hi

    for name, (toe, cy, width, _) in FLIGHTS.items():
        walk = Mesh()
        ys = [cy + (i / 8 - 0.5) * width for i in range(9)]
        for lo, hi in zip(ys, ys[1:]):
            corners = [
                (toe - 0.035, lo),
                (edge(toe, lo) + 0.05, lo),
                (edge(toe, hi) + 0.05, hi),
                (toe - 0.035, hi),
            ]
            # The last 8 cm runs into the actual road with a buried 1 cm lip.
            left, right, upper, back = corners
            inner = [(right[0] - 0.08, lo), (upper[0] - 0.08, hi)]
            for part, offsets in [
                ([left, inner[0], inner[1], back], [0] * 4),
                ([inner[0], right, upper, inner[1]], [0, -0.012, -0.012, 0]),
            ]:
                walk.face(
                    [
                        (x, y, street_level(x, y) + dz)
                        for (x, y), dz in zip(part, offsets)
                    ],
                    colors['asphalt'],
                )
        # Low pale lawn edging is visible on the sides, with an open street end.
        for sign in (-1, 1):
            outer = cy + sign * (width / 2 + 0.12)
            inner = cy + sign * width / 2
            lo, hi = sorted((inner, outer))
            end = min(edge(toe, lo), edge(toe, hi)) - 0.04
            ring = [(toe, lo), (end, lo), (end, hi), (toe, hi)]
            top = [(x, y, street_level(x, y) + 0.065) for x, y in ring]
            low = [(x, y, street_level(x, y) - 0.060) for x, y in ring]
            walk.face(top, colors['curb'])
            for i in range(4):
                j = (i + 1) % 4
                walk.face([low[i], low[j], top[j], top[i]], colors['curb'])
        base['site-physics-east-' + name] = walk
    soil = base['terrain']
    faces = [f for f in soil.f if overlaps(bounds([soil.v[i] for i in f]), EXTENT)]
    ground = BVHTree.FromPolygons(soil.v, faces)

    @lru_cache(maxsize=4096)
    def soil_z(x, y):
        hit = ground.ray_cast((x, y, 40), (0, 0, -1))[0]
        if hit is None:
            raise ValueError(f'Missing soil at physics verge: {x}, {y}')
        return hit.z

    base['terrain'] = grade_layer(soil, colors, False, soil_z)
    base['roads'] = grade_layer(roads, colors, True, soil_z)
