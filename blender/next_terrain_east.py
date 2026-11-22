"""Refit two verified continuous approaches east of the campus centre."""

import math
from copy import copy

from mathutils.bvhtree import BVHTree

from geometry import Mesh
from refine_roads_west import _bands, _source_uv, _split
from site_geometry import mesh_triangles

# West wall lane; walkway across the dining forecourt. Both stop before the
# next unchanged junction or stair. Heights and tangent grades are model ties.
LANE = (452, -550, 470, -498)
WALK = (573, -484, 604, -469)


def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3.0 - 2.0 * t)


def profile(u, length, south, north, inlet, outlet):
    t = min(1.0, max(0.0, u / length))
    return (
        south
        + (north - south) * smooth(t)
        + length * t * (1.0 - t) * (inlet * (1.0 - t) - outlet * t)
    )


def displacement(box, x, y, sample, soil):
    if box == LANE:
        along = y + 550
        axis = 463.605 - (y + 527.353) * 0.03195
        offset = x - axis
        cx, cy = axis + max(-3.2, min(3.2, offset)), y
        target = profile(along, 52, 2.84, 7.68, 0.030, 0.062)
        weight = (
            smooth(along / 5)
            * smooth((52 - along) / 5)
            * smooth((x - 452) / 6)
            * smooth((470 - x) / 2.0)
        )
    else:
        along = x - 573
        axis = -476.516 + (x - 569.405) * 0.00095
        offset = y - axis
        cx, cy = x, axis + max(-0.9, min(0.9, offset))
        target = profile(along, 31, 4.43, 0.93, -0.16, 0.020)
        weight = (
            smooth(along / 2.5)
            * smooth((31 - along) / 2.5)
            * smooth((y + 484) / 5.5)
            * smooth((-469 - y) / 5.5)
        )
    if not weight:
        return 0.0
    # Sample the continuous road sheet. Some paint strips replace asphalt triangles.
    road_z = sample('pavement', cx, cy)
    existing = sample('grass', x, y) if soil else road_z
    # Slight crossfall is confined to the model fit. Preserve surface thickness
    # and marking separation by translating every road layer by the same field.
    bed_clearance = 0.22 if box == LANE else 0.14
    if soil and box == WALK:
        # The mapped path overlaps the wider square. Immediately beyond the
        # path edges, the square's own triangles can be lower. Bed the lower
        # pavement as well, including knots just inside a path edge.
        levels = [
            sample('pavement', x, sy, optional=True)
            for sy in (y, axis - 1.6, axis + 1.6)
        ]
        lowest = min([road_z] + [z for z in levels if z is not None])
        bed_clearance += road_z - lowest
    return weight * (
        target + 0.012 * offset - (bed_clearance if soil else 0.0) - existing
    )


def cut_cells(poly, box):
    x0, y0, x1, y1 = box
    for axis, cut, high in (
        (0, x0, True),
        (0, x1, False),
        (1, y0, True),
        (1, y1, False),
    ):
        low, upper = _split(poly, axis, cut)
        poly, outside = (upper, low) if high else (low, upper)
        if len(outside) >= 3:
            yield outside, None
        if len(poly) < 3:
            return
    for row in _bands(poly, 1, range(y0 + 1, y1)):
        for piece in _bands(row, 0, range(x0 + 1, x1)):
            yield piece, True


def local_faces(mesh, box, ground):
    x0, y0, x1, y1 = box
    patch, indices = Mesh(), set()
    for i, face in enumerate(mesh.f):
        pts = [mesh.v[j] for j in face]
        if (
            max(p[0] for p in pts) <= x0
            or min(p[0] for p in pts) >= x1
            or max(p[1] for p in pts) <= y0
            or min(p[1] for p in pts) >= y1
        ):
            continue
        patch.face(pts, mesh.m[i], _source_uv(mesh, i, pts, ground))
        indices.add(i)
    return patch, indices


def fit(road, soil, colors, box):
    layers = [local_faces(road, box, False), local_faces(soil, box, True)]
    tris = [mesh_triangles(local) for local, _ in layers]
    materials = [
        {colors['asphalt'], colors['path'], colors['roadYellow'], colors['curb']},
        {colors['grass']},
    ]
    trees = {}
    for k, ((local, _), tri, mats) in enumerate(zip(layers, tris, materials)):
        faces = [f for f, i in tri if local.m[i] in mats]
        trees[('pavement', 'grass')[k]] = BVHTree.FromPolygons(
            local.v, faces, all_triangles=True
        )

    def sample(key, x, y, optional=False):
        hit = trees[key].ray_cast((x, y, 80), (0, 0, -1), 150)[0]
        if hit is None:
            if optional:
                return None
            raise ValueError(f'Missing {key} at ({x:.3f}, {y:.3f})')
        return hit.z

    results = []
    for k, (mesh, (local, ids), triangles) in enumerate(
        zip((road, soil), layers, tris)
    ):
        # The same sampled displacement acts on coincident pavement layers.
        # Bilinear interpolation also ties independent source triangles at cuts.
        x0, y0, x1, y1 = box
        field = {
            (x, y): displacement(box, x, y, sample, k == 1)
            for x in range(x0, x1 + 1)
            for y in range(y0, y1 + 1)
        }

        def dz(x, y):
            ix = min(x1 - 1, max(x0, math.floor(x)))
            iy = min(y1 - 1, max(y0, math.floor(y)))
            u, v = x - ix, y - iy
            return (1 - v) * ((1 - u) * field[ix, iy] + u * field[ix + 1, iy]) + v * (
                (1 - u) * field[ix, iy + 1] + u * field[ix + 1, iy + 1]
            )

        result = copy(mesh)
        result.v = list(mesh.v)
        result.f = []
        result.m = []
        result.face_uvs = {}
        for i, face in enumerate(mesh.f):
            if i not in ids:
                if i in mesh.face_uvs:
                    result.face_uvs[len(result.f)] = mesh.face_uvs[i]
                result.f.append(face)
                result.m.append(mesh.m[i])
        for face, fi in triangles:
            uv = local.face_uvs[fi]
            poly = [(*local.v[j], *uv[local.f[fi].index(j)]) for j in face]
            for piece, active in cut_cells(poly, box):
                vertices = [
                    (x, y, z + (dz(x, y) if active else 0.0)) for x, y, z, _, _ in piece
                ]
                for i in range(1, len(piece) - 1):
                    corners = (0, i, i + 1)
                    a, b, c = [vertices[j] for j in corners]
                    # Keep vertical road kerbs alongside horizontal surfaces.
                    ab = [p - q for p, q in zip(b, a)]
                    ac = [p - q for p, q in zip(c, a)]
                    if (
                        max(
                            abs(ab[j - 1] * ac[j - 2] - ab[j - 2] * ac[j - 1])
                            for j in range(3)
                        )
                        < 1e-10
                    ):
                        continue
                    result.face(
                        [vertices[j] for j in corners],
                        local.m[fi],
                        [piece[j][3:] for j in corners],
                    )
        results.append(result)
    return results


def apply(base, colors):
    if getattr(base['terrain'], 'east_approach_grades', False):
        return
    road, soil = base['roads'], base['terrain']
    for box in (LANE, WALK):
        road, soil = fit(road, soil, colors, box)
    soil.east_approach_grades = True
    base.update(roads=road, terrain=soil)
