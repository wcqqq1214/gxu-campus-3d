"""Fit the west avenue and the bollard walk to their retained pavement ends."""

from copy import copy
from functools import lru_cache

from geometry import Mesh
from materials_north_road import split
from refine_roads_west import _source_uv
from refine_terrain_west import hit_z, sample, submesh
from site_geometry import mesh_triangles

AVENUE = (-471.0, -678.0, -450.0, -609.0)
WALK = (-414.0, -638.0, -399.0, -596.0)
BOXES = (AVENUE, WALK)


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def axis_x(i, y):
    if i == 0:
        return -460.643 - 0.00867 * (y + 645.341)
    return -406.893 - 0.01346 * (y + 599.586)


def patches(road, colors):
    street = sample(submesh(road, AVENUE))
    ends = [hit_z(street, axis_x(0, y), y, 20) for y in (AVENUE[1], AVENUE[3])]
    walk = submesh(road, WALK)
    asphalt = Mesh()
    for face, mat in zip(walk.f, walk.m):
        if mat == colors['asphalt']:
            asphalt.face([walk.v[j] for j in face], mat)
    main = sample(asphalt)
    path = sample(walk)
    start = hit_z(path, axis_x(1, WALK[1]), WALK[1], 20)

    def tie_profile(tree, axis, y, span):
        center = axis_x(axis, y)
        levels = [hit_z(tree, center + dx, y, 20) for dx in (-span, 0, span)]

        def relief(dx):
            dx = max(-span, min(span, dx))
            return abs(dx) / span * (levels[0 if dx < 0 else 2] - levels[1])

        return relief

    south = tie_profile(street, 0, AVENUE[1], 3.6)
    north = tie_profile(street, 0, AVENUE[3], 3.6)
    walk_end = tie_profile(path, 1, WALK[1], 2.3)

    @lru_cache(maxsize=2048)
    def seam(x):
        # Read the transverse asphalt within the actual opening, avoiding the
        # kerb caps on either side when extending the join into the earth verge.
        x = max(-409.37, min(-404.47, x))
        a, b = -600.0, -597.5
        for _ in range(21):
            y = (a + b) / 2
            if hit_z(main, x, y, 20) is None:
                a = y
            else:
                b = y
        return b, hit_z(main, x, b + 0.0015, 20)

    def avenue(x, y, z, ground):
        dx = abs(x - axis_x(0, y))
        w = (
            smooth((y - AVENUE[1]) / (12 if ground else 4))
            * smooth((AVENUE[3] - y) / (12 if ground else 4))
            * smooth((9.0 - dx) / 4.4)
        )
        h = ends[0] + (ends[1] - ends[0]) * (y - AVENUE[1]) / (AVENUE[3] - AVENUE[1])
        # Modest estimated crown; the real centre and both kerb lines are continuous.
        crown = -0.012 * min(dx, 4.0)
        h += crown
        lateral = x - axis_x(0, y)
        h += (south(lateral) - crown) * smooth(1 - (y - AVENUE[1]) / 20)
        h += (north(lateral) - crown) * smooth(1 - (AVENUE[3] - y) / 22)
        return z + w * (h - (0.045 if ground else 0.0) - z)

    def entrance(x, y, z, ground):
        ey, ez = seam(x)
        dx = abs(x - axis_x(1, y))
        w = smooth((y - WALK[1]) / (10 if ground else 4)) * smooth((6.5 - dx) / 3.75)
        approach = (y - WALK[1]) / (ey - WALK[1])
        h = start + (ez - start) * approach
        h += walk_end(x - axis_x(1, y)) * smooth(1 - (y - WALK[1]) / 22)
        if y > ey:
            # The original service stub continues underneath the main street.
            # Settle it back under the asphalt; keep that street and its kerbs intact.
            h = ez - 0.035 * (y - ey)
            w *= smooth(1 - (y - ey) / 1.4)
        return z + w * (h - (0.045 if ground else 0.0) - z)

    return (avenue, entrance), seam


def cut_pieces(triangle, i, seam):
    x0, y0, x1, y1 = BOXES[i]
    inside = [triangle]
    for axis, limit, sign in ((0, x0, 1), (0, x1, -1), (1, y0, 1), (1, y1, -1)):
        keep = []
        for part in inside:
            for q in split(part, lambda p: sign * (p[axis] - limit)):
                if sign * (sum(p[axis] for p in q) / len(q) - limit) < 0:
                    yield q, False
                else:
                    keep.append(q)
        inside = keep
    stations = (
        (
            -676,
            -674,
            -672,
            -670,
            -668,
            -666,
            -658,
            -648,
            -638,
            -628,
            -624,
            -621,
            -619,
            -617,
            -615,
            -613,
            -611,
        )
        if i == 0
        else (-636, -634, -632, -630, -628, -622, -616, -614, -607, -603, -600)
    )
    for y in stations:
        inside = [q for part in inside for q in split(part, lambda p: p[1] - y)]
    offsets = (
        (-9, -7, -4.6, 0, 4.6, 7, 9)
        if i == 0
        else (-6.5, -4.7, -2.75, 0, 2.75, 4.7, 6.5)
    )
    for dx in offsets:
        inside = [
            q
            for part in inside
            for q in split(part, lambda p: p[0] - axis_x(i, p[1]) - dx)
        ]
    if i == 1:
        for dy in (0.0, 0.7, 1.4):
            inside = [
                q
                for part in inside
                for q in split(part, lambda p: p[1] - seam(p[0])[0] - dy)
            ]
    for q in inside:
        yield q, True


def rebuild(mesh, colors, fields, seam, ground):
    crops = [Mesh(), Mesh()]
    selected = []
    for fi, face in enumerate(mesh.f):
        pts = [mesh.v[j] for j in face]
        xs, ys, _ = zip(*pts)
        for i, (x0, y0, x1, y1) in enumerate(BOXES):
            if min(xs) >= x1 or max(xs) <= x0 or min(ys) >= y1 or max(ys) <= y0:
                continue
            if ground and mesh.m[fi] != colors['grass']:
                continue
            if not ground and i == 1 and mesh.m[fi] != colors['road']:
                continue
            crops[i].face(pts, mesh.m[fi], _source_uv(mesh, fi, pts, ground))
            selected.append(fi)
            break
    omit = set(selected)
    result = copy(mesh)
    result.v = mesh.v.copy()
    result.f = []
    result.m = []
    result.face_uvs = {}
    for fi, (face, mat) in enumerate(zip(mesh.f, mesh.m)):
        if fi not in omit:
            if fi in mesh.face_uvs:
                result.face_uvs[len(result.f)] = mesh.face_uvs[fi]
            result.f.append(face)
            result.m.append(mat)
    for i, local in enumerate(crops):
        for ids, fi in mesh_triangles(local):
            uv = dict(zip(local.f[fi], local.face_uvs[fi]))
            poly = [(*local.v[j], *uv[j]) for j in ids]
            for ring, inside in cut_pieces(poly, i, seam):
                pts = [
                    (x, y, fields[i](x, y, z, ground) if inside else z)
                    for x, y, z, u, v in ring
                ]
                for j in range(1, len(pts) - 1):
                    indices = (0, j, j + 1)
                    a, b, c = [pts[k] for k in indices]
                    ab = [b[k] - a[k] for k in range(3)]
                    ac = [c[k] - a[k] for k in range(3)]
                    if any(
                        abs(ab[k] * ac[(k + 1) % 3] - ac[k] * ab[(k + 1) % 3]) > 1e-10
                        for k in range(3)
                    ):
                        result.face(
                            [pts[k] for k in indices],
                            local.m[fi],
                            [ring[k][3:] for k in indices],
                        )
    return result


def apply(base, colors):
    if getattr(base['roads'], 'west_v5_joined', False):
        return
    fields, seam = patches(base['roads'], colors)
    roads = rebuild(base['roads'], colors, fields, seam, False)
    terrain = rebuild(base['terrain'], colors, fields, seam, True)
    roads.west_v5_joined = True
    base.update(roads=roads, terrain=terrain)
