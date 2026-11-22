"""Clear local grass intrusions beneath four photographed paved approaches."""

from copy import copy
from functools import lru_cache
from math import ceil

from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import normal

from geometry import Mesh
from materials_north_road import split
from refine_terrain_west import local_faces, submesh
from site_geometry import mesh_triangles

# Absolute XY clipping bounds (metres), including the perimeter transition.
# Each bound encloses the measured grass/road intersection, not the whole way.
PATCHES = {
    'way/685682496': (-464.2, -640.0, -456.9, -631.1),
    'way/699156923': (-411.3, -606.1, -401.4, -596.0),
    'way/759096587': (-655.8, -556.4, -642.5, -545.8),
    'way/759345905': (-595.6, -8.4, -587.1, 5.5),
}
BED = 0.055
SHOULDER = 1.3


def road_surface(road, box, materials):
    local = submesh(road, box)
    facets = []
    for ids, fi in mesh_triangles(local):
        if local.m[fi] not in materials:
            continue
        a, b, c = [local.v[i] for i in ids]
        ab = Vector(b) - Vector(a)
        ac = Vector(c) - Vector(a)
        n = ab.cross(ac)
        if n.z > 1e-8:
            facets.append((ids, a, n))
    if not facets:
        raise ValueError(f'Missing paved road in west terrain patch {box}')
    flat = BVHTree.FromPolygons(
        [(x, y, 0) for x, y, z in local.v],
        [ids for ids, a, n in facets],
        all_triangles=True,
    )

    # Subdivide along the actual carriageway facets. A long diagonal can span
    # both sides of a sunken panel even when its two end samples are clear.
    edges = {}
    for ids, _, _ in facets:
        for i, j in zip(ids, (*ids[1:], ids[0])):
            a, b = local.v[i], local.v[j]
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = (dx * dx + dy * dy) ** 0.5
            if length < 1e-6:
                continue
            left, bottom = min(a[0], b[0]), min(a[1], b[1])
            right, top = max(a[0], b[0]), max(a[1], b[1])
            if right < box[0] or left > box[2] or top < box[1] or bottom > box[3]:
                continue
            nx, ny = dy / length, -dx / length
            if nx < -1e-8 or (abs(nx) < 1e-8 and ny < 0):
                nx, ny = -nx, -ny
            offset = nx * a[0] + ny * a[1]
            key = tuple(round(k, 7) for k in (nx, ny, offset))
            edges[key] = (nx, ny, offset)

    @lru_cache(maxsize=8192)
    def envelope(x, y):
        _, _, _, distance = flat.find_nearest((x, y, 0))
        # All incident surfaces supply a ceiling at coincident edges, including
        # neighbouring road panels that meet at different elevations.
        nearest = flat.find_nearest_range((x, y, 0), distance + 0.0003)
        values = []
        for q, _, i, _ in nearest:
            _, a, n = facets[i]
            values.append(a[2] - ((q.x - a[0]) * n.x + (q.y - a[1]) * n.y) / n.z)
        edge = min(x - box[0], box[2] - x, y - box[1], box[3] - y)
        weight = max(0.0, min(1.0, edge / SHOULDER, 1 - distance / SHOULDER))
        return min(values) - BED, weight

    return envelope, edges.values()


def pieces(poly, box, edges):
    # Only the interior needs a metre-scale sample lattice. Outside polygons
    # retain the incoming surface; an untouched parent is retained verbatim.
    inner, outside = [poly], []
    for axis, limit, sign in (
        (0, box[0], 1),
        (0, box[2], -1),
        (1, box[1], 1),
        (1, box[3], -1),
    ):
        keep = []
        for part in inner:
            for q in split(part, lambda p: sign * (p[axis] - limit)):
                if sign * (sum(v[axis] for v in q) / len(q) - limit) < 0:
                    outside.append(q)
                else:
                    keep.append(q)
        inner = keep
    for axis in (0, 1):
        start, end = box[axis], box[axis + 2]
        steps = ceil((end - start) / 2.4)
        for i in range(1, steps):
            line = start + (end - start) * i / steps
            inner = [q for part in inner for q in split(part, lambda p: p[axis] - line)]
    for nx, ny, offset in edges:
        inner = [
            q
            for part in inner
            for q in split(part, lambda p: nx * p[0] + ny * p[1] - offset)
        ]
    return outside + inner


def original_uvs(soil, i, pts):
    if i in soil.face_uvs:
        return soil.face_uvs[i]
    cx, cy = [sum(p[k] for p in pts) / len(pts) for k in (0, 1)]
    ground = any(
        x0 <= cx <= x1 and y0 <= cy <= y1 for x0, y0, x1, y1 in soil.ground_uv_bounds
    )
    n = normal([Vector(v) for v in pts])
    axis = (
        2
        if ground or soil.m[i] in soil.xy_uv_materials
        else max(range(3), key=lambda k: abs(n[k]))
    )
    u, v = [k for k in (0, 1, 2) if k != axis]
    return [(pt[u] / 4, pt[v] / 4) for pt in pts]


def lower_patch(soil, road, colors, box):
    ceiling, edges = road_surface(road, box, {colors['road'], colors['asphalt']})
    local = Mesh()
    source = []
    for i, pts in local_faces(soil, box):
        if soil.m[i] == colors['grass']:
            local.face(pts, soil.m[i], original_uvs(soil, i, pts))
            source.append(i)
    replacement = {}
    changed = set()
    for ids, fi in mesh_triangles(local):
        original = source[fi]
        uv = dict(zip(local.f[fi], local.face_uvs[fi]))
        poly = [(*local.v[i], *uv[i]) for i in ids]
        for part in pieces(poly, box, edges):
            pts = []
            for x, y, z, u, v in part:
                target, w = ceiling(x, y)
                dz = w * min(0.0, target - z)
                if dz < -1e-8:
                    changed.add(original)
                pts.append((x, y, z + dz))
            replacement.setdefault(original, []).append((pts, [q[3:] for q in part]))
    if not changed:
        return soil
    result = copy(soil)
    result.v = list(soil.v)
    result.f, result.m, result.face_uvs = [], [], {}
    for i, (face, mat) in enumerate(zip(soil.f, soil.m)):
        if i in changed:
            for pts, uv in replacement[i]:
                result.face(pts, mat, uv)
        else:
            if i in soil.face_uvs:
                result.face_uvs[len(result.f)] = soil.face_uvs[i]
            result.f.append(face)
            result.m.append(mat)
    return result


def apply(base, colors):
    """Keep the driving surface, kerbs and walkways at their incoming elevations."""
    soil = base['terrain']
    if getattr(soil, 'west_intrusions_cleared', False):
        return
    for box in PATCHES.values():
        soil = lower_patch(soil, base['roads'], colors, box)
    soil.west_intrusions_cleared = True
    base['terrain'] = soil
