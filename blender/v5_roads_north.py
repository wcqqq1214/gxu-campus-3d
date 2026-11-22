"""Refit both lanes of the north farm road, including its eastern approach and roadbed."""

import json
from bisect import bisect_left, bisect_right
from copy import copy
from pathlib import Path

from next_roads_north import _split


def _within_station_interval(polygon, south, north):
    ya, lower = south
    yb, upper = north
    height = yb - ya

    def boundary(xa, xb):
        return lambda point: point[0] - xa - (xb - xa) * (point[1] - ya) / height

    outside, rest = _split(polygon, boundary(lower[0][0], upper[0][0]))
    if outside:
        yield outside
    for j in range(len(lower) - 1):
        if not rest:
            break
        (xa, za), (xb, zb) = lower[j : j + 2]
        (xc, zc), (xd, zd) = upper[j : j + 2]
        band, rest = _split(rest, boundary(xb, xd))
        if not band:
            continue
        diagonal = boundary(xa, xd)
        west, east = _split(band, diagonal)
        for piece, gradient in (
            (west, (zd - zc) / (xd - xc)),
            (east, (zb - za) / (xb - xa)),
        ):
            if piece:
                yield [
                    (
                        x,
                        y,
                        z
                        + za
                        + (zd - za) * (y - ya) / height
                        + gradient * diagonal((x, y)),
                        u,
                        v,
                    )
                    for x, y, z, u, v in piece
                ]
    if rest:
        yield rest


def _pieces(triangle, rows, levels):
    below, rest = _split(triangle, lambda v: v[1] - levels[0])
    if below:
        yield below
    if not rest:
        return
    start = max(0, bisect_right(levels, min(v[1] for v in rest)) - 1)
    for i in range(start, len(rows) - 1):
        if not rest:
            return
        polygon, rest = _split(rest, lambda v: v[1] - levels[i + 1])
        if polygon:
            yield from _within_station_interval(polygon, rows[i], rows[i + 1])
    if rest:
        yield rest


def _triangles(points):
    if len(points) == 3:
        return [(0, 1, 2)]
    import bpy

    mesh = bpy.data.meshes.new('north-farm-grade-tessellation')
    try:
        mesh.from_pydata(points, [], [tuple(range(len(points)))])
        mesh.calc_loop_triangles()
        return [tuple(t.vertices) for t in mesh.loop_triangles]
    finally:
        bpy.data.meshes.remove(mesh)


def _fit(mesh, rows, materials):
    levels = [y for y, _ in rows]
    west = [v[0][0] for _, v in rows]
    east = [v[-1][0] for _, v in rows]
    xmin, xmax = min(west), max(east)
    result = copy(mesh)
    result.v = mesh.v.copy()
    result.f, result.m, result.face_uvs = [], [], {}
    for i, (face, mat) in enumerate(zip(mesh.f, mesh.m)):
        active = False
        if mat in materials:
            points = [mesh.v[j] for j in face]
            xx, yy, _ = zip(*points)
            if (
                max(yy) > levels[0]
                and min(yy) < levels[-1]
                and min(xx) < xmax
                and max(xx) > xmin
            ):
                lo = max(0, bisect_left(levels, min(yy)) - 1)
                hi = min(len(rows), bisect_right(levels, max(yy)) + 1)
                active = max(xx) >= min(west[lo:hi]) and min(xx) <= max(east[lo:hi])
        if not active:
            if i in mesh.face_uvs:
                result.face_uvs[len(result.f)] = mesh.face_uvs[i]
            result.f.append(face)
            result.m.append(mat)
            continue
        uvs = mesh.face_uvs.get(i, [(x / 4, y / 4) for x, y, _ in points])
        corners = [(*pt, *uv) for pt, uv in zip(points, uvs)]
        for tri in _triangles(points):
            for polygon in _pieces([corners[j] for j in tri], rows, levels):
                for j in range(1, len(polygon) - 1):
                    triangle = (polygon[0], polygon[j], polygon[j + 1])
                    result.face(
                        [v[:3] for v in triangle], mat, [v[3:] for v in triangle]
                    )
    result.north_farm_grade_v5 = True
    return result


def apply(base, colors):
    """Run after the complete v4 surface construction and before tree contact updates."""
    field = json.loads(
        Path(__file__).with_name('v5_roads_north_field.json').read_text()
    )
    masks = {'roads': ('asphalt', 'road', 'curb', 'roadYellow'), 'terrain': ('grass',)}
    # The west curb by the farm turn touches the old soil mesh. Leave a few
    # centimetres below this isolated kerb after whole-campus quantization.
    soil = []
    for y, row in field:
        section = list(row)
        for j, (x, dz) in enumerate(row[1:-1], start=1):
            relief = (
                0.05
                * max(0.0, 1.0 - abs(y - 782.54) / 4.0)
                * max(0.0, 1.0 - abs(x + 139.97) / 7.5)
            )
            section[j] = (x, dz - relief)
        soil.append((y, section))
    replacements = {
        key: _fit(
            base[key], soil if key == 'terrain' else field, {colors[m] for m in names}
        )
        for key, names in masks.items()
        if not getattr(base[key], 'north_farm_grade_v5', False)
    }
    if 'roads' in replacements:
        replacements['roads'] = _junction(replacements['roads'], colors)
    base.update(replacements)


def _junction(mesh, colors):
    """Retain the axial road at the tunnel exit and stitch the two side approaches."""
    patches = json.loads(
        Path(__file__).with_name('v5_roads_north_junction.json').read_text()
    )
    result = copy(mesh)
    result.v = mesh.v.copy()
    result.f, result.m, result.face_uvs = [], [], {}
    matched = set()
    for i, (face, mat) in enumerate(zip(mesh.f, mesh.m)):
        key = None
        if mat == colors['road']:
            pts = [mesh.v[j] for j in face]
            if (
                min(q[1] for q in pts) < 1207
                and max(q[1] for q in pts) > 1198
                and min(q[0] for q in pts) < -209
                and max(q[0] for q in pts) > -224
            ):
                key = '|'.join(','.join(f'{v:.7f}' for v in pt) for pt in pts)
        if key in patches:
            if i in mesh.face_uvs:
                raise ValueError('North gate side-road UV projection has changed')
            matched.add(key)
            for tri in patches[key]:
                result.face(tri, mat)
        else:
            if i in mesh.face_uvs:
                result.face_uvs[len(result.f)] = mesh.face_uvs[i]
            result.f.append(face)
            result.m.append(mat)
    if matched != patches.keys():
        raise ValueError('North gate side-road source faces have changed')
    return result
