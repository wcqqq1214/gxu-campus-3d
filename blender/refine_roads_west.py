"""Tie the west market crossing to the north residential lane, in campus metres."""

from bisect import bisect_left
from copy import copy
from functools import lru_cache
from math import ceil, floor

from mathutils.geometry import normal

from geometry import Mesh
from site_geometry import mesh_triangles

# The market-front ground model fixes the southern road at 4.265 m. The
# northern tie is sampled from the same lane in the reviewed mesh. These
# are relative model heights; the photographs establish the continuous road.
BOUNDS = (-616.0, -233.0, -559.0, -200.0)
AXIS_X = -587.65
SOUTH_Z = 4.265
NORTH_Z = 7.70


def _smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3.0 - 2.0 * x)


def _axis_height(y):
    # Integrate a continuous grade between the unchanged ties. The steeper
    # southern reach gains enough height before it meets the transverse lane.
    d = min(28.0, max(0.0, y - BOUNDS[1]))
    inlet, first, end = 1.8, 0.1585, 0.016
    late = (NORTH_Z - SOUTH_Z - first * (13.5 - inlet / 2) - end * 2.5) / 12.0

    def ramp(start, length):
        q = max(0.0, d - start)
        return q * q / (2 * length) if q < length else q - length / 2

    return (
        SOUTH_Z
        + first * ramp(0, inlet)
        + (late - first) * ramp(10, 7)
        + (end - late) * ramp(23, 5)
    )


@lru_cache(maxsize=16000)
def _grade(x, y):
    south = BOUNDS[1]
    target = _axis_height(y)
    dx = abs(x - AXIS_X)
    branch_y = -220.302 + 0.020 * (x - AXIS_X)
    offset = y - branch_y
    reach = 15.0 if x < AXIS_X else 26.0
    along = _smooth((reach - dx) / (reach - 3.0))
    # The west arm abuts dormitory 2 on its north edge. The east arm has
    # an open verge and more room to return to the retained ground.
    north = 6.0 if x > AXIS_X else min(6.0, -218.48 - branch_y)
    across = _smooth((offset + 7.0) / 4.0) * _smooth(
        (north - offset) / max(0.7, north - 2.2)
    )
    branch_z = _axis_height(branch_y) + 0.03 * offset
    target += across * _smooth((dx - 2.0) / 5.0) * (branch_z - target)
    lane = _smooth((y + 228.0) / 8.0)
    outer = (28.0 if x < AXIS_X else 27.0) * (1.0 - lane) + 7.0 * lane
    inner = 7.0 * (1.0 - lane) + 3.1 * lane
    w = _smooth((outer - abs(x - AXIS_X)) / (outer - inner))
    w = max(w, along * across)
    w *= _smooth((y - south) / 1.1) * _smooth((-204.95 - y) / 8.0)
    return w, target


def _split(poly, axis, cut):
    low, high = [], []
    for a, b in zip(poly, poly[1:] + poly[:1]):
        da, db = a[axis] - cut, b[axis] - cut
        if da <= 0:
            low.append(a)
        if da >= 0:
            high.append(a)
        if da * db < 0:
            t = da / (da - db)
            p = tuple(v + t * (w - v) for v, w in zip(a, b))
            low.append(p)
            high.append(p)
    return low, high


def _bands(poly, axis, cuts):
    for cut in cuts:
        if min(p[axis] for p in poly) >= cut:
            continue
        if max(p[axis] for p in poly) <= cut:
            break
        part, poly = _split(poly, axis, cut)
        if len(part) >= 3:
            yield part
        if len(poly) < 3:
            return
    yield poly


def _cells(triangle):
    # Partition the outside only at the envelope: no grid propagated across
    # a long triangle or into a neighbouring district.
    x0, y0, x1, y1 = BOUNDS
    current = triangle
    for axis, cut, keep_high in (
        (0, x0, True),
        (0, x1, False),
        (1, y0, True),
        (1, y1, False),
    ):
        low, high = _split(current, axis, cut)
        current, outside = (high, low) if keep_high else (low, high)
        if len(outside) >= 3:
            yield outside, False
        if len(current) < 3:
            return
    rows = set(range(ceil(y0 / 2) * 2, floor(y1) + 1, 2))
    rows.update(i / 2 for i in range(-448, -432))
    rows.add(-218.48)  # Stop the west verge before the retained dormitory pad.
    for row in _bands(current, 1, sorted(rows)):
        for cell in _bands(row, 0, range(ceil(x0 / 2) * 2, floor(x1) + 1, 2)):
            yield cell, True


def _subtract(poly, clip):
    """Subtract one convex XY footprint; interpolate source Z and UV at cuts."""
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(clip, clip[1:] + clip[:1]))
    winding = 1 if area >= 0 else -1
    current = poly
    pieces = []
    for a, b in zip(clip, clip[1:] + clip[:1]):
        if len(current) < 3:
            break
        dx, dy = b[0] - a[0], b[1] - a[1]
        if abs(dx) + abs(dy) < 1e-9:
            continue
        sides = [winding * (dx * (p[1] - a[1]) - dy * (p[0] - a[0])) for p in current]
        if max(sides) <= 1e-9:
            return pieces + [current]
        if min(sides) >= -1e-9:
            continue
        inside, outside = [], []
        for i, pt in enumerate(current):
            j = (i + 1) % len(current)
            other = current[j]
            d, e = sides[i], sides[j]
            (inside if d >= 0 else outside).append(pt)
            if (d < 0) != (e < 0):
                t = d / (d - e)
                edge = tuple(u + t * (v - u) for u, v in zip(pt, other))
                inside.append(edge)
                outside.append(edge)
        if len(outside) >= 3:
            pieces.append(outside)
        current = inside
    return pieces


def _disjoint_cells(tri, covered):
    for ring, inside in _cells(tri):
        cx = sum(p[0] for p in ring) / len(ring)
        cy = sum(p[1] for p in ring) / len(ring)
        if covered is None or not inside or not (-592 < cx < -584 and -224 < cy < -216):
            yield ring, inside
            continue
        # Three OSM service polygons overlap in this junction. Give their
        # shared footprint one pavement face at the continuous target level.
        previous = covered.setdefault((floor(cx / 2), floor(cy / 2)), [])
        pieces = [ring]
        for occupied in previous:
            pieces = [p for old in pieces for p in _subtract(old, occupied)]
        previous.append(ring)
        for piece in pieces:
            yield piece, True


def _source_uv(mesh, i, pts, is_ground):
    explicit = mesh.face_uvs.get(i)
    if explicit is not None:
        return explicit
    # Match Mesh.object's default planar projection on the original polygon.
    # A new triangle on a gentler grade must not flip its texture axes.
    center = tuple(sum(p[k] for p in pts) / len(pts) for k in (0, 1))
    planar = mesh.m[i] in mesh.xy_uv_materials or (
        is_ground
        and any(
            x0 <= center[0] <= x1 and y0 <= center[1] <= y1
            for x0, y0, x1, y1 in mesh.ground_uv_bounds
        )
    )
    n = normal(pts)
    axis = 2 if planar else max(range(3), key=lambda k: abs(n[k]))
    u, v = (k for k in range(3) if k != axis)
    return [(p[u] / 4, p[v] / 4) for p in pts]


def _refit(mesh, is_ground, road_material):
    x0, y0, x1, y1 = BOUNDS
    local = Mesh()
    edited = set()
    for i, face in enumerate(mesh.f):
        pts = [mesh.v[k] for k in face]
        if (
            max(p[0] for p in pts) > x0
            and min(p[0] for p in pts) < x1
            and max(p[1] for p in pts) > y0
            and min(p[1] for p in pts) < y1
        ):
            local.face(pts, mesh.m[i], _source_uv(mesh, i, pts, is_ground))
            edited.add(i)

    # Preserve vertex sharing, parts, explicit UVs and the original ordering
    # on all retained faces. Drop only vertices orphaned by this local edit.
    rest = copy(mesh)
    orphans = {k for i in edited for k in mesh.f[i]}
    for i, face in enumerate(mesh.f):
        if i not in edited:
            orphans.difference_update(face)
    removed = sorted(orphans)
    rest.v = [v for i, v in enumerate(mesh.v) if i not in orphans]
    rest.f, rest.m, rest.face_uvs = [], [], {}
    for i, face in enumerate(mesh.f):
        if i in edited:
            continue
        if i in mesh.face_uvs:
            rest.face_uvs[len(rest.f)] = mesh.face_uvs[i]
        rest.f.append(tuple(k - bisect_left(removed, k) for k in face))
        rest.m.append(mesh.m[i])
    rest.parts = [
        (name, a - bisect_left(removed, a), b - bisect_left(removed, b))
        for name, a, b in mesh.parts
    ]
    covered = {}
    for ids, fi in mesh_triangles(local):
        explicit = local.face_uvs.get(fi)
        uv = dict(zip(local.f[fi], explicit)) if explicit else {}
        tri = [(*local.v[i], *uv.get(i, ())) for i in ids]
        masks = covered if not is_ground and local.m[fi] == road_material else None
        for ring, inside in _disjoint_cells(tri, masks):
            out = []
            for x, y, z, *_ in ring:
                if inside:
                    w, target = _grade(x, y)
                    z += w * (target - (0.13 if is_ground else 0.0) - z)
                out.append((x, y, z))
            for j in range(1, len(out) - 1):
                corners = (0, j, j + 1)
                a, b, c = [out[k] for k in corners]
                # The selected crossing and its bed are surface sheets.
                if (
                    abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
                    < 1e-10
                ):
                    continue
                rest.face(
                    [a, b, c],
                    local.m[fi],
                    [ring[k][3:] for k in corners] if explicit else None,
                )
    return rest


def apply(base, colors):
    """Apply immediately after apply_north_roads(base, C)."""
    if getattr(base['roads'], '_west_market_graded', False) and getattr(
        base['terrain'], '_west_market_graded', False
    ):
        return
    roads = _refit(base['roads'], False, colors['road'])
    terrain = _refit(base['terrain'], True, colors['road'])
    roads._west_market_graded = terrain._west_market_graded = True
    base.update(roads=roads, terrain=terrain)
