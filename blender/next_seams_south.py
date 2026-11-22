"""Lower false terrain needles at the maths centre's south entrance.

The independent outer apron (site-math-center-south-apron) was already exposed.
The occlusion affects the building chunk's stone entry steps and threshold.
The apron and the 0.02 m building datum remain fixed controls. Only terrain
above the bedding level is cut; roads, architecture, water, UVs and materials
are not changed. Official entrance reference:
https://gxcmr.gxu.edu.cn/info/1003/2227.htm
"""

import math
from copy import copy

from geometry import Mesh
from refine_roads_west import _bands, _source_uv, _split
from site_geometry import mesh_triangles

# Central entrance projection of way/759129515, with short side/slope feathers.
BOUNDS = (-229.0, -856.0, -215.0, -849.0)
BED = -0.02  # 40 mm below the unchanged 0.02 m building datum.
STEP = 0.5


def smooth(value):
    value = min(1.0, max(0.0, value))
    return value * value * (3.0 - 2.0 * value)


def weight(x, y):
    x0, y0, x1, y1 = BOUNDS
    return (
        smooth((x - x0) / 2.0)
        * smooth((x1 - x) / 2.0)
        * smooth((y - y0) / 3.5)
        * smooth((y1 - y) / 0.75)
    )


def cut_cells(poly):
    x0, y0, x1, y1 = BOUNDS
    for axis, cut, high in (
        (0, x0, True),
        (0, x1, False),
        (1, y0, True),
        (1, y1, False),
    ):
        low, upper = _split(poly, axis, cut)
        poly, outside = (upper, low) if high else (low, upper)
        if len(outside) >= 3:
            yield outside, False
        if len(poly) < 3:
            return
    xs = [i * STEP for i in range(math.ceil(x0 / STEP), math.floor(x1 / STEP) + 1)]
    ys = [i * STEP for i in range(math.ceil(y0 / STEP), math.floor(y1 / STEP) + 1)]
    for row in _bands(poly, 1, ys):
        for piece in _bands(row, 0, xs):
            yield piece, True


def local_faces(mesh):
    x0, y0, x1, y1 = BOUNDS
    local, selected = Mesh(), set()
    for i, face in enumerate(mesh.f):
        points = [mesh.v[j] for j in face]
        if (
            max(p[0] for p in points) <= x0
            or min(p[0] for p in points) >= x1
            or max(p[1] for p in points) <= y0
            or min(p[1] for p in points) >= y1
        ):
            continue
        local.face(points, mesh.m[i], _source_uv(mesh, i, points, True))
        selected.add(i)
    if not selected:
        raise ValueError('Missing maths centre south terrain')
    return local, selected


def apply(base, colors):
    terrain = base['terrain']
    if getattr(terrain, 'south_maths_apron_seam', False):
        return
    local, selected = local_faces(terrain)
    triangles = mesh_triangles(local)
    result = copy(terrain)
    result.v = list(terrain.v)
    result.f, result.m, result.face_uvs = [], [], {}
    for i, face in enumerate(terrain.f):
        if i not in selected:
            if i in terrain.face_uvs:
                result.face_uvs[len(result.f)] = terrain.face_uvs[i]
            result.f.append(face)
            result.m.append(terrain.m[i])
    for triangle, source_index in triangles:
        uv = local.face_uvs[source_index]
        poly = [(*local.v[j], *uv[local.f[source_index].index(j)]) for j in triangle]
        for piece, active in cut_cells(poly):
            vertices = []
            for x, y, z, *_ in piece:
                # A cut-only field cannot fill a real low terrace or raise a road bed.
                dz = -weight(x, y) * max(0.0, z - BED) if active else 0.0
                vertices.append((x, y, z + dz))
            for j in range(1, len(piece) - 1):
                corners = (0, j, j + 1)
                a, b, c = (vertices[k] for k in corners)
                ab, ac = (
                    [b[k] - a[k] for k in range(3)],
                    [c[k] - a[k] for k in range(3)],
                )
                cross = (
                    ab[1] * ac[2] - ab[2] * ac[1],
                    ab[2] * ac[0] - ab[0] * ac[2],
                    ab[0] * ac[1] - ab[1] * ac[0],
                )
                if sum(v * v for v in cross) < 1e-16:
                    continue
                result.face(
                    [vertices[k] for k in corners],
                    local.m[source_index],
                    [piece[k][3:] for k in corners],
                )
    result.south_maths_apron_seam = True
    base['terrain'] = result
