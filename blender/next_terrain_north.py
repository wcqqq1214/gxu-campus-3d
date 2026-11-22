"""Repair two independently verified ground contacts in the east residence area."""

from copy import copy
from math import hypot

from geometry import Mesh
from shore_geometry import bounds, overlaps
from site_geometry import mesh_triangles
from west22_ground import split

BEND = (-52.0, 411.0, -11.0, 448.0)
BED = (-138.0, 17.0, -123.0, 37.0)


def has_area(poly):
    if len(poly) < 3:
        return False
    origin = poly[0]
    area = sum(
        (b[0] - origin[0]) * (c[1] - origin[1])
        - (b[1] - origin[1]) * (c[0] - origin[0])
        for b, c in zip(poly[1:-1], poly[2:])
    )
    return abs(area) > 1e-8


def bend(poly):
    # The center of the bend is a continuous plane. Along its two approaches,
    # return to the actual incoming heights. Split the transition bands only.
    for axis, edge, sign in (
        (0, BEND[0], 1),
        (1, BEND[1], 1),
        (0, BEND[2], -1),
        (1, BEND[3], -1),
    ):
        poly, outside = split(poly, lambda p: sign * (p[axis] - edge))
        if has_area(outside):
            yield outside
        if not has_area(poly):
            return
    pieces = [poly]
    for axis, locations in [(1, range(411, 426, 2)), (0, range(-23, -10, 2))]:
        for location in locations:
            following = []
            for part in pieces:
                lo = min(p[axis] for p in part)
                hi = max(p[axis] for p in part)
                if lo + 1e-7 < location < hi - 1e-7:
                    following.extend(
                        v
                        for v in split(part, lambda p: p[axis] - location)
                        if has_area(v)
                    )
                else:
                    following.append(part)
            pieces = following
    for part in pieces:
        ring = []
        for x, y, z, *uv in part:
            factor = max(0, min(1, (y - 411) / 12, (-11 - x) / 12))
            target = (
                3.28
                + 0.015 * (x + 37.413)
                + 0.007 * (y - 431.841)
                - 0.025 * max(0, 425 - y)
            )
            ring.append((x, y, z + factor * (target - z), *uv))
        yield ring


def bed_planes():
    # Longitudinal and cross-grade fitted to the unchanged road triangles.
    # Bottom of the bed is capped 13 cm below the center tangent. A 1:2
    # shoulder returns to the original soil outside the five-metre carriageway.
    axis = (29.99, -90.93)
    length = hypot(*axis)
    ux, uy = axis[0] / length, axis[1] / length

    def frame(p):
        dx, dy = p[0] + 130.303, p[1] - 26.985
        return dx * ux + dy * uy, -dx * uy + dy * ux

    def elevation(p, du, dv, offset):
        u, v = frame(p)
        return 3.474 + (0.039 + du) * u + (0.090 + dv) * v + offset

    faces = [
        (0, 0, 0),
        (0, 0.5, -1.27),
        (0, -0.5, -1.27),
        (-0.5, 0, -2.0),
        (0.5, 0, -2.875),
    ]
    return [lambda p, f=f: elevation(p, *f) for f in faces]


def cut_bed(poly, planes):
    inside = poly
    outside = []
    for height in planes:
        inside, part = split(inside, lambda p: p[2] - height(p))
        if not has_area(inside):
            yield poly
            return
        if has_area(part):
            outside.append(part)
    yield from outside
    for index, height in enumerate(planes):
        part = inside
        for j, other in enumerate(planes):
            if j != index:
                part, _ = split(part, lambda p: height(p) - other(p))
                if not has_area(part):
                    break
        if has_area(part):
            yield [(p[0], p[1], height(p), *p[3:]) for p in part]


def replace_local(mesh, region, material, convert):
    # Leave original vertices, indices, explicit corner UVs and nonlocal
    # metadata available to other groups editing different parts of this Mesh.
    out = copy(mesh)
    out.v = list(mesh.v)
    out.f, out.m, out.face_uvs = [], [], {}
    local = Mesh()
    for i, (indices, mat) in enumerate(zip(mesh.f, mesh.m)):
        pts = [mesh.v[j] for j in indices] if mat == material else []
        uvs = mesh.face_uvs.get(i)
        if pts and overlaps(bounds(pts), region):
            local.face(pts, mat, uvs)
        else:
            if uvs is not None:
                out.face_uvs[len(out.f)] = uvs
            out.f.append(indices)
            out.m.append(mat)
    for tri, i in mesh_triangles(local):
        uvs = local.face_uvs.get(i)
        if uvs is None:
            points = [tuple(local.v[j]) for j in tri]
        else:
            corners = dict(zip(local.f[i], uvs))
            points = [(*local.v[j], *corners[j]) for j in tri]
        for piece in convert(points):
            for j in range(1, len(piece) - 1):
                face = [piece[0], piece[j], piece[j + 1]]
                if has_area(face):
                    out.face(
                        [p[:3] for p in face],
                        local.m[i],
                        [p[3:] for p in face] if uvs is not None else None,
                    )
    return out


def apply(base, colors):
    if getattr(base['terrain'], 'east_residence_beds_checked', False):
        return
    planes = bed_planes()
    roads = replace_local(base['roads'], BEND, colors['road'], bend)
    terrain = replace_local(
        base['terrain'], BED, colors['grass'], lambda poly: cut_bed(poly, planes)
    )
    terrain.east_residence_beds_checked = True
    base['roads'], base['terrain'] = roads, terrain
