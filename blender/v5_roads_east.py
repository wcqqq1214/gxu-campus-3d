"""Round the two pedestrian curb returns at the Teaching Six motor entrance."""

from bisect import bisect_right
from copy import copy
from math import pi, sin, sqrt

from geometry import Mesh
from west22_ground import split

NODE = 'site-road-east-teaching'
START, END = -168.0, -149.0
SOUTH, NORTH = -166.3, -151.0
LIP = 0.16
RISE = 0.13
# Photo-fit radii in project metres. The two original threshold stations and
# the native road-contact XY/Z locate the opening; neither moves.
RETURNS = ((SOUTH, 1, 0.85), (NORTH, -1, 0.75))


def _bracket(keys, value):
    i = max(0, min(len(keys) - 2, bisect_right(keys, value) - 1))
    a, b = keys[i : i + 2]
    return a, b, max(0.0, min(1.0, (value - a) / (b - a)))


def _mix(a, b, t):
    return a + (b - a) * t


def _return_offset(s, end, direction, radius, inset):
    # Offset measured from the outer street edge into the sidewalk.
    t = max(0.0, direction * (s - end) + radius)
    return radius - sqrt(max(0.0, (radius - inset) ** 2 - t * t))


def _top_parts(a, b, d, e):
    rect = [(a, d), (b, d), (b, e), (a, e)]
    mid = (a + b) / 2
    if SOUTH < mid < NORTH:
        return [(rect, 'road', False)]
    end, direction, radius = RETURNS[0 if mid < SOUTH else 1]

    def cut(poly, inset):
        da = _return_offset(a, end, direction, radius, inset)
        db = _return_offset(b, end, direction, radius, inset)
        return split(poly, lambda p: p[1] - _mix(da, db, (p[0] - a) / (b - a)))

    raised, apron = cut(rect, 0.0)
    if direction * (mid - end) >= -LIP:
        return [(apron, 'road', False), (raised, 'curb', True)]
    brick, curb = cut(raised, LIP)
    return [
        (apron, 'road', False),
        (curb, 'curb', True),
        (brick, 'roadEastTeaching', True),
    ]


def _area(poly):
    if len(poly) < 3:
        return 0.0
    a = poly[0]
    return (
        abs(
            sum(
                (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
                for b, c in zip(poly[1:], poly[2:])
            )
        )
        / 2
    )


def apply(base, colors):
    """Replace only the native strip's two corners and intervening flush threshold."""
    mesh = base[NODE]
    if getattr(mesh, 'teaching_curb_returns', False):
        return
    selected = set()
    rows = {}
    for i, face in enumerate(mesh.f):
        pts = [mesh.v[k] for k in face]
        ys = [v[1] for v in pts]
        if min(ys) < START or max(ys) > END:
            continue
        selected.add(i)
        for x, s, z in pts:
            rows.setdefault(s, {}).setdefault(x, []).append(z)

    stations = sorted(rows)
    if not stations or stations[0] != START or stations[-1] != END:
        raise ValueError('Teaching Six sidewalk boundary stations are missing')
    edges = {s: max(row) for s, row in rows.items()}
    sections = {
        s: {round(edges[s] - x, 7): (min(z), max(z)) for x, z in row.items()}
        for s, row in rows.items()
    }
    cols = sorted(sections[START])
    if any(sorted(row) != cols for row in sections.values()):
        raise ValueError('Unexpected Teaching Six strip cross-section')
    width = cols[-1]
    knots = set(stations)
    for end, direction, radius in RETURNS:
        for inset in (0.0, LIP):
            for step in range(9):
                angle = pi * step / 16
                knots.add(end + direction * (-radius + (radius - inset) * sin(angle)))
    bands = []
    for s in sorted(knots):
        if not bands or s - bands[-1] > 1e-7:
            bands.append(s)

    def point(q, raised=False, bottom=False):
        s, d = q
        lo, hi, t = _bracket(stations, s)
        c, e, u = _bracket(cols, d)
        index = 0 if bottom else 1
        x = _mix(edges[lo], edges[hi], t) - d
        z0 = _mix(sections[lo][c][index], sections[lo][e][index], u)
        z1 = _mix(sections[hi][c][index], sections[hi][e][index], u)
        z = _mix(z0, z1, t)
        if not bottom:
            old_lift = RISE * min(1.0, max(SOUTH - s, s - NORTH, 0.0) / 1.3)
            z += (RISE if raised else 0.0) - old_lift
        return x, s, z

    patch = Mesh()
    for a, b in zip(bands, bands[1:]):
        for d, e in zip(cols, cols[1:]):
            for poly, material, raised in _top_parts(a, b, d, e):
                if _area(poly) < 1e-10:
                    continue
                pts = [point(q, raised) for q in poly]
                uvs = (
                    [(s / 0.86, offset / 0.86) for s, offset in poly]
                    if material == 'roadEastTeaching'
                    else None
                )
                patch.face(pts, colors[material], uvs)
                for j, (p, q) in enumerate(zip(poly, poly[1:] + poly[:1])):
                    if abs(p[0] - q[0]) + abs(p[1] - q[1]) < 1e-8:
                        continue
                    outside = abs(p[1] - q[1]) < 1e-7 and (
                        abs(p[1]) < 1e-7 or abs(p[1] - width) < 1e-7
                    )
                    if outside:
                        low1, low2 = point(p, bottom=True), point(q, bottom=True)
                    elif raised and material == 'curb' and _is_return_face(p, q, a, b):
                        low1, low2 = point(p), point(q)
                    else:
                        continue
                    patch.face(
                        [pts[(j + 1) % len(poly)], pts[j], low1, low2], colors['curb']
                    )

    out = copy(mesh)
    out.v = mesh.v.copy()
    keep = [i for i in range(len(mesh.f)) if i not in selected]
    out.f = [mesh.f[i] for i in keep]
    out.m = [mesh.m[i] for i in keep]
    out.face_uvs = {
        j: mesh.face_uvs[i] for j, i in enumerate(keep) if i in mesh.face_uvs
    }
    out.parts = mesh.parts.copy()
    out.ground_uv_bounds = mesh.ground_uv_bounds.copy()
    out.xy_uv_materials = mesh.xy_uv_materials.copy()
    out.extend(patch)
    out.teaching_curb_returns = True
    base[NODE] = out


def _is_return_face(p, q, a, b):
    mid = (a + b) / 2
    end, direction, radius = RETURNS[0 if mid < SOUTH else 1]
    if abs(p[0] - end) < 1e-7 and abs(q[0] - end) < 1e-7:
        return min(p[1], q[1]) >= radius - 1e-7
    da = _return_offset(a, end, direction, radius, 0.0)
    db = _return_offset(b, end, direction, radius, 0.0)
    return max(da, db) > 1e-7 and all(
        abs(v[1] - _mix(da, db, (v[0] - a) / (b - a))) < 1e-7 for v in (p, q)
    )
