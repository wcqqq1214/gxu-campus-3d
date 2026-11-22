"""Street-view-located pedestrian edges in east campus, in project metres.

Each strip starts on the existing outside curb edge. Stations increase north
for Teaching Six / the residential street and east for Medicine. Widths and
vertical transitions are conservative model fits to the archived panoramas.
"""

import math
from copy import copy
from functools import lru_cache

from mathutils.bvhtree import BVHTree

from civil_forecourt_grade import grade_mesh
from geometry import Mesh, tile_material
from site_geometry import mesh_triangles

# (station, approximate outside curb coordinate). Actual XYZ comes from the Mesh.
# Openings are pedestrian/vehicle crossings visible in the same station series.
STREETS = (
    {
        'id': 'teaching',
        'axis': 1,
        'edge': [(-214.0, 349.32), (-89.0, 324.02)],
        'width': 2.9,
        'curb': 0.16,
        'rise': 0.13,
        'openings': [(-214.0, -212.4), (-166.3, -151.0), (-92.6, -89.0)],
        'pits': [(-99.7, 1.35), (-116.5, 1.40), (-171.5, 1.40), (-191.1, 1.40)],
        'pitSize': (1.05, 1.00),
        'pitRim': 0,
        'tint': (0.34, 0.25, 0.20),
    },
    {
        'id': 'medical',
        'axis': 0,
        'edge': [(466.4, -459.18), (564.9, -458.94)],
        'width': 3.05,
        'curb': 0.78,
        'rise': 0.035,
        'openings': [(466.4, 470.5), (527.8, 535.2), (563.2, 564.9)],
        'pits': [(499.0, 1.70), (517.4, 1.60), (521.7, 1.70), (561.3, 1.60)],
        'pitSize': (0.92, 0.88),
        'pitRim': 0,
        'tint': (0.34, 0.27, 0.25),
    },
    {
        'id': 'residence',
        'axis': 1,
        'edge': [(274.1, 341.24), (283.2, 344.7), (294, 345.83), (325.8, 345.58)],
        'width': 4.3,
        'curb': 0.17,
        'rise': 0.105,
        'openings': [(274.1, 275.4), (324.6, 325.8)],
        'pits': [
            (281.5, 1.48),
            (293.4, 1.48),
            (300.0, 1.48),
            (308.6, 1.48),
            (323.1, 1.48),
        ],
        'pitSize': (1.28, 1.20),
        'pitRim': 0.10,
        'tint': (0.42, 0.18, 0.15),
    },
)


def _bounds(section):
    edge = section['edge']
    s0, s1 = edge[0][0] - 1, edge[-1][0] + 1
    c0 = min(c for _, c in edge) - section['width'] - 2
    c1 = max(c for _, c in edge) + 2
    return (s0, c0, s1, c1) if section['axis'] == 0 else (c0, s0, c1, s1)


def _local(mesh, bounds, material=None, selected=None):
    x0, y0, x1, y1 = bounds
    result = Mesh()
    for i, (face, mat) in enumerate(zip(mesh.f, mesh.m)):
        if material is not None and mat != material:
            continue
        pts = [mesh.v[k] for k in face]
        if (
            max(p[0] for p in pts) >= x0
            and min(p[0] for p in pts) <= x1
            and max(p[1] for p in pts) >= y0
            and min(p[1] for p in pts) <= y1
        ):
            result.face(pts, mat, mesh.face_uvs.get(i))
            if selected is not None:
                selected.add(i)
    return result


def _curb_profile(mesh, section):
    axis = section['axis']
    ends = section['edge']
    segments = []
    for f in mesh.f:
        pts = [(mesh.v[k][axis], mesh.v[k][1 - axis], mesh.v[k][2]) for k in f]
        for a, b in zip(pts, pts[1:] + pts[:1]):
            if abs(a[0] - b[0]) > 1e-8:
                segments.append(sorted((a, b)))

    @lru_cache(None)
    def edge(s):
        a, b = next((a, b) for a, b in zip(ends, ends[1:]) if a[0] <= s <= b[0])
        expected = a[1] + (b[1] - a[1]) * (s - a[0]) / (b[0] - a[0])
        hits = []
        for lo, hi in segments:
            if lo[0] - 1e-8 <= s <= hi[0] + 1e-8:
                t = (s - lo[0]) / (hi[0] - lo[0])
                c = lo[1] + t * (hi[1] - lo[1])
                if abs(c - expected) < 1.2:
                    hits.append((c, lo[2] + t * (hi[2] - lo[2])))
        if not hits:
            raise ValueError(f'East road {section["id"]} missing curb at {s}')
        return min(hits)

    return edge, segments


def _grade_ground(terrain, extent, target, step):
    # Retain the other districts' faces, original UV coordinates and vertex ranges.
    # Only triangulate the existing faces touching this strip.
    selected = set()
    local = _local(terrain, extent, selected=selected)
    x0, y0, x1, y1 = extent
    profile = dict(
        extent=extent, core=[x0 + 0.3, y0 + 0.3, x1 - 0.3, y1 - 0.3], meshStep=step
    )
    result = grade_mesh(local, profile, target_height=target)
    keep = [i for i in range(len(terrain.f)) if i not in selected]
    terrain.face_uvs = {
        j: terrain.face_uvs[i] for j, i in enumerate(keep) if i in terrain.face_uvs
    }
    terrain.f = [terrain.f[i] for i in keep]
    terrain.m = [terrain.m[i] for i in keep]
    terrain.extend(result)


def _service_crossings(base):
    # Two measured positive intersections, confined to the existing service lanes.
    # Lower only the underlying terrain; the road vertices, texture and joins persist.
    repairs = (
        ((7.0, 116.0, 24.5, 129.0), (-30.12, 110.25), (26.49, 125.35)),
        ((210.3, 150.0, 221.0, 164.0), (219.90, 146.25), (207.23, 175.54)),
    )
    for extent, a, b in repairs:
        dx, dy = b[0] - a[0], b[1] - a[1]
        ground = _local(base['terrain'], extent)
        roads = _local(base['roads'], extent)

        def tree(m):
            return BVHTree.FromPolygons(
                m.v, [tri for tri, _ in mesh_triangles(m)], all_triangles=True
            )

        gt, rt = tree(ground), tree(roads)

        def target(x, y):
            old = gt.ray_cast((x, y, 100), (0, 0, -1))[0].z
            t = ((x - a[0]) * dx + (y - a[1]) * dy) / (dx * dx + dy * dy)
            cx, cy = a[0] + t * dx, a[1] + t * dy
            cross = math.hypot(x - cx, y - cy)
            fade = max(0.0, min(1.0, (4.5 - cross) / 1.15))
            if not fade:
                return old
            # Sample just inside the mapped five-metre lane for the narrow
            # shoulder outside it. This keeps the edge on the same road plane.
            inset = min(1.0, 2.0 / max(cross, 0.001))
            h = rt.ray_cast(
                (cx + (x - cx) * inset, cy + (y - cy) * inset, 100), (0, 0, -1)
            )[0]
            if h is None:
                raise ValueError('Missing east residential service-lane surface')
            return old + fade * min(0.0, h.z - 0.13 - old)

        _grade_ground(base['terrain'], extent, target, 0.5)


def _walk(base, colors, spec):
    local = _bounds(spec)
    curb = _local(base['roads'], local, colors['curb'])
    edge, segments = _curb_profile(curb, spec)
    ground = _local(base['terrain'], local)
    tree = BVHTree.FromPolygons(
        ground.v, [tri for tri, _ in mesh_triangles(ground)], all_triangles=True
    )
    start, end = spec['edge'][0][0], spec['edge'][-1][0]
    width, lip = spec['width'], spec['curb']
    rim = spec['pitRim']
    hs, hd = (v * 0.5 for v in spec['pitSize'])
    rows = {start, end, *range(math.ceil(start), math.ceil(end))}
    # Preserve the source curb's bends and changes of grade at their actual stations.
    rows.update(p[0] for seg in segments for p in seg if start < p[0] < end)
    cols = {0.0, lip, width, width / 2}
    for s, d in spec['pits']:
        rows.update(s + k for k in (-hs - rim, -hs, hs, hs + rim))
        cols.update(d + k for k in (-hd - rim, -hd, hd, hd + rim))
    for a, b in spec['openings']:
        rows.update(max(start, min(end, v)) for v in (a - 1.3, a, b, b + 1.3))
    medical = spec['id'] == 'medical'
    joints = []
    if medical:
        for i in range(math.ceil((end - start) / 0.58)):
            s = start + 0.58 * i
            if s + 0.015 < end:
                rows.update((s, s + 0.015))
                joints.append((s, s + 0.015))
    rows, cols = sorted(rows), sorted(cols)
    # Merge coincident station coordinates from shared source triangle edges.
    rows = [s for i, s in enumerate(rows) if not i or s - rows[i - 1] > 1e-7]
    out = Mesh()
    tile = 'roadEast' + spec['id'].title()
    tile_material(colors, tile, 'road-east-' + spec['id'] + '.jpg', spec['tint'])

    @lru_cache(None)
    def point(s, d):
        c, z = edge(s)
        x, y = (s, c - d) if spec['axis'] == 0 else (c - d, s)
        hit = tree.ray_cast((x, y, 150), (0, 0, -1))[0]
        if hit is None:
            raise ValueError(f'Missing east street ground at {x}, {y}')
        gap = min(max(a - s, s - b, 0) for a, b in spec['openings'])
        lift = spec['rise'] * min(1, gap / 1.3)
        # Keep the threshold at the road datum and follow the original outside ground.
        top = z + lift + d * 0.012
        top = max(top, hit.z + 0.023 * min(1, d / 0.25))
        return (x, y, top), hit.z

    def panel(s, d):
        for u, v in spec['pits']:
            if abs(s - u) < hs and abs(d - v) < hd:
                return 'soil'
            if rim and abs(s - u) < hs + rim and abs(d - v) < hd + rim:
                return 'curb'
        if d < lip:
            if medical and any(a <= s <= b for a, b in joints):
                return 'road'
            return 'curb'
        if any(a <= s <= b for a, b in spec['openings']):
            return 'road'
        return tile

    for a, b in zip(rows, rows[1:]):
        for d, e in zip(cols, cols[1:]):
            material = panel((a + b) / 2, (d + e) / 2)
            ring = [(a, d), (b, d), (b, e), (a, e)]
            if spec['axis'] == 0:
                ring.reverse()
            pts = [point(*q)[0] for q in ring]
            if material == 'soil':
                pts = [
                    (x, y, max(point(*q)[1] + 0.008, z - 0.065))
                    for (x, y, z), q in zip(pts, ring)
                ]
            mat = colors['bark' if material == 'soil' else material]
            out.face(
                pts,
                mat,
                [(s / 0.86, c / 0.86) for s, c in ring] if material == tile else None,
            )
            for i, (q, n) in enumerate(zip(ring, ring[1:] + ring[:1])):
                s, off = q
                if (s == n[0] and s in (start, end)) or (
                    off == n[1] and off in (0, width)
                ):
                    low = [
                        min(point(*v)[1] - 0.03, point(*v)[0][2] - 0.012)
                        for v in (q, n)
                    ]
                elif material == 'soil':
                    continue
                else:
                    s_mid, d_mid = (s + n[0]) / 2, (off + n[1]) / 2
                    if not any(
                        (abs(abs(s_mid - u) - hs) < 1e-6 and abs(d_mid - v) < hd)
                        or (abs(abs(d_mid - v) - hd) < 1e-6 and abs(s_mid - u) < hs)
                        for u, v in spec['pits']
                    ):
                        continue
                    low = [
                        max(point(*v)[1] + 0.008, point(*v)[0][2] - 0.065)
                        for v in (q, n)
                    ]
                p1, p2 = pts[i], pts[(i + 1) % 4]
                out.face([p2, p1, (*p1[:2], low[0]), (*p2[:2], low[1])], colors['curb'])
    # Build up the garden-side shoulder to the walking surface. The road and
    # nearby buildings have separate datums, so limit the outer transition.
    outside = 0.80 if medical else 2.6
    extent = tuple(v + sign * 3.1 for v, sign in zip(local, (-1, -1, 1, 1)))
    original = _local(base['terrain'], extent)
    soil = BVHTree.FromPolygons(
        original.v, [tri for tri, _ in mesh_triangles(original)], all_triangles=True
    )

    def bed(x, y):
        old = soil.ray_cast((x, y, 150), (0, 0, -1))[0].z
        s, c = (x, y) if spec['axis'] == 0 else (y, x)
        along = max(start, min(end, s))
        d = edge(along)[0] - c
        blend = min(
            1.0,
            max(0.0, (width + outside - d) / outside),
            max(0.0, 1 - abs(s - along) / 2.2),
            max(0.0, (d + 0.35) / 0.35),
        )
        if not blend:
            return old
        cross = max(0.0, min(width, d))
        top = point(along, cross)[0][2]
        depth = 0.045 if cross >= width - 0.25 else 0.16
        return old + blend * max(0.0, top - depth - old)

    _grade_ground(base['terrain'], extent, bed, 0.8)
    return out


def apply_roads(base, C):
    """Attach three local pedestrian edges after build_physics_street_grade."""
    keys = ['site-road-east-' + s['id'] for s in STREETS]
    if all(k in base for k in keys):
        return
    terrain = copy(base['terrain'])
    terrain.v = terrain.v.copy()
    work = {'terrain': terrain, 'roads': base['roads']}
    _service_crossings(work)
    additions = {k: _walk(work, C, s) for k, s in zip(keys, STREETS)}
    base.update(terrain=terrain, **additions)
