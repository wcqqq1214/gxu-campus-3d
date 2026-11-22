"""Ease the graduate-school access bend and bed its grass-side kerb in V4."""

import math
from copy import copy

from mathutils.bvhtree import BVHTree

from next_terrain_east import local_faces, smooth
from refine_roads_west import _bands, _split
from site_geometry import mesh_triangles

BOUNDS = (558, -522, 598, -482)
STEP = 1
AXIS = (
    (569.323, -454.931),
    (569.5, -501.07),
    (571.01, -505.08),
    (573.75, -508.65),
    (576.82, -510.91),
    (580.14, -512.27),
    (604.35, -512.12),
)
# Actual exterior face of the graduate-school diagonal wing.
WALL = ((556.356, -500.049), (584.875, -527.712))


def project(x, y):
    prior = 0.0
    nearest = None
    for a, b in zip(AXIS, AXIS[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        t = max(0.0, min(1.0, ((x - a[0]) * dx + (y - a[1]) * dy) / length**2))
        cx, cy = a[0] + t * dx, a[1] + t * dy
        d = math.hypot(x - cx, y - cy)
        if nearest is None or d < nearest[0]:
            nearest = (d, prior + t * length, cx, cy)
        prior += length
    return nearest


def offsets(x, y, road, terrain):
    dist, station, cx, cy = project(x, y)
    wx, wy = WALL[0]
    dx, dy = WALL[1][0] - wx, WALL[1][1] - wy
    wall_distance = (dx * (y - wy) - dy * (x - wx)) / math.hypot(dx, dy)
    # Keep an unchanged collar at both actual walls and the V4 paved square.
    med_distance = math.hypot(max(0.0, x - 564.625), max(0.0, -490.699 - y))
    weight = (
        smooth((9.0 - dist) / 4.6)
        * smooth((station - 29) / 8)
        * smooth((75 - station) / 8)
        * smooth((wall_distance - 1.45) / 1.5)
        * smooth((med_distance - 1.45) / 1.5)
        * smooth((-484 - y) / 4)
    )
    if weight <= 0:
        return (0.0, 0.0)

    def at(tree, px, py):
        q = tree.ray_cast((px, py, 60), (0, 0, -1), 120)[0]
        return q.z if q is not None else None

    # Outside the asphalt, tie the bank to the nearest inboard course, then
    # feather to the retained soil. The existing structure fixes the two ends.
    factor = min(1.0, 3.25 / max(dist, 1e-9))
    rx, ry = cx + (x - cx) * factor, cy + (y - cy) * factor
    top = at(road, rx, ry)
    if top is None:
        top = at(road, cx, cy)
    if top is None:
        raise ValueError('East bend carriageway missing')
    # Shift the entire section together, keeping its kerb and marking offsets.
    target = 4.78 - 0.067 * (rx - 569.436) + 0.092 * (ry + 484.808)
    dz = weight * (target - top)
    # Take the lowest local clearance across the whole support of this knot,
    # including adjacent paved areas beyond the mapped road ribbon.
    clearances = []
    for i in range(-3, 4):
        for j in range(-3, 4):
            px, py = x + i / 3, y + j / 3
            rz = at(road, px, py)
            gz = at(terrain, px, py)
            if rz is not None and gz is not None:
                clearances.append(rz - gz)
    if clearances:
        fill = min(clearances) - 0.12
    else:
        rz = at(road, cx + (x - cx) * factor, cy + (y - cy) * factor)
        gz = at(terrain, x, y)
        fill = (
            max(0.0, (rz if rz is not None else top) - gz - 0.18)
            if gz is not None
            else 0.0
        )
    return dz, dz + weight * fill


def cells(poly):
    x0, y0, x1, y1 = BOUNDS
    for axis, cut, keep_high in (
        (0, x0, True),
        (0, x1, False),
        (1, y0, True),
        (1, y1, False),
    ):
        low, high = _split(poly, axis, cut)
        poly, rest = (high, low) if keep_high else (low, high)
        if len(rest) >= 3:
            yield rest, False
        if len(poly) < 3:
            return
    for row in _bands(poly, 1, range(y0 + STEP, y1, STEP)):
        for cell in _bands(row, 0, range(x0 + STEP, x1, STEP)):
            mx = sum(p[0] for p in cell) / len(cell)
            my = sum(p[1] for p in cell) / len(cell)
            ix = math.floor(mx / STEP) * STEP
            iy = math.floor(my / STEP) * STEP
            tagged = [(*p, p[0] - ix - p[1] + iy) for p in cell]
            if min(p[-1] for p in tagged) < 0 < max(p[-1] for p in tagged):
                for part in _split(tagged, 5, 0.0):
                    yield [p[:5] for p in part], True
            else:
                yield cell, True


def apply(base, colors):
    if getattr(base['terrain'], 'graduate_bend_fitted', False):
        return
    nodes = ['roads', 'terrain']
    local = [local_faces(base[key], BOUNDS, key == 'terrain') for key in nodes]
    tris = [mesh_triangles(m) for m, _ in local]
    trees = []
    for (m, _), tri, mats in zip(
        local, tris, ({'asphalt', 'roadYellow', 'curb', 'path'}, {'grass'})
    ):
        allowed = {colors[k] for k in mats}
        trees.append(
            BVHTree.FromPolygons(
                m.v, [f for f, i in tri if m.m[i] in allowed], all_triangles=True
            )
        )
    x0, y0, x1, y1 = BOUNDS
    grid = {
        (x, y): offsets(x, y, *trees) if x0 < x < x1 and y0 < y < y1 else (0.0, 0.0)
        for x in range(x0, x1 + 1, STEP)
        for y in range(y0, y1 + 1, STEP)
    }
    changed = {}
    for layer, (name, (m, ids), triangles) in enumerate(zip(nodes, local, tris)):
        src = base[name]
        dst = copy(src)
        dst.v = list(src.v)
        dst.f = []
        dst.m = []
        dst.face_uvs = {}
        for i, (f, mat) in enumerate(zip(src.f, src.m)):
            if i in ids:
                continue
            if i in src.face_uvs:
                dst.face_uvs[len(dst.f)] = src.face_uvs[i]
            dst.f.append(f)
            dst.m.append(mat)
        for f, i in triangles:
            uvs = dict(zip(m.f[i], m.face_uvs[i]))
            original = [(*m.v[j], *uvs[j]) for j in f]
            for piece, active in cells(original):
                verts = []
                for x, y, z, u, v in piece:
                    if active:
                        ix = min(x1 - STEP, max(x0, math.floor(x / STEP) * STEP))
                        iy = min(y1 - STEP, max(y0, math.floor(y / STEP) * STEP))
                        a, b = (x - ix) / STEP, (y - iy) / STEP
                        sw, ne = grid[ix, iy][layer], grid[ix + STEP, iy + STEP][layer]
                        if a >= b:
                            z += (
                                (1 - a) * sw
                                + (a - b) * grid[ix + STEP, iy][layer]
                                + b * ne
                            )
                        else:
                            z += (
                                (1 - b) * sw
                                + (b - a) * grid[ix, iy + STEP][layer]
                                + a * ne
                            )
                    verts.append((x, y, z))
                for j in range(1, len(verts) - 1):
                    indices = (0, j, j + 1)
                    a, b, c = (verts[k] for k in indices)
                    ab = [v - u for u, v in zip(a, b)]
                    ac = [v - u for u, v in zip(a, c)]
                    if (
                        max(
                            abs(ab[h - 1] * ac[h - 2] - ab[h - 2] * ac[h - 1])
                            for h in range(3)
                        )
                        <= 1e-10
                    ):
                        continue
                    dst.face(
                        [verts[k] for k in indices],
                        m.m[i],
                        [piece[k][3:] for k in indices],
                    )
        changed[name] = dst
    changed['terrain'].graduate_bend_fitted = True
    base.update(changed)
