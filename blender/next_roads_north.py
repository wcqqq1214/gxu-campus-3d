"""Fit the lakeside carriageway and its support to one local vertical displacement field."""

import json
from bisect import bisect_right
from copy import copy
from pathlib import Path


def _split(polygon, distance):
    """Partition an ordered face, linearly interpolating XYZ and the original UVs."""
    if not polygon:
        return [], []
    distances = [distance(point) for point in polygon]
    if min(distances) >= -1e-10:
        return [], polygon
    if max(distances) <= 1e-10:
        return polygon, []
    low, high = [], []
    for i, (point, current) in enumerate(zip(polygon, distances)):
        previous = distances[i - 1]
        if (previous < -1e-10 and current > 1e-10) or (
            previous > 1e-10 and current < -1e-10
        ):
            t = previous / (previous - current)
            hit = tuple(a + t * (b - a) for a, b in zip(polygon[i - 1], point))
            low.append(hit)
            high.append(hit)
        if current <= 1e-10:
            low.append(point)
        if current >= -1e-10:
            high.append(point)
    return low, high


def _feet(row):
    y, x, dz, west, east = row
    return [x - west, x - 5.35, x + 5.35, x + east], [0.0, dz, dz, 0.0]


def _strip(poly, a, b):
    """Within a station interval use two planes per band, shared by road and soil."""
    left, za = _feet(a)
    right, zb = _feet(b)
    height = b[0] - a[0]

    def cut(x0, x1):
        return lambda pt: pt[0] - (x0 + (x1 - x0) * (pt[1] - a[0]) / height)

    outside, rest = _split(poly, cut(left[0], right[0]))
    if outside:
        yield outside
    for j in range(3):
        band, rest = _split(rest, cut(left[j + 1], right[j + 1]))
        if not band:
            continue
        # A diagonal from the southwest to the northeast corner defines both planes.
        lower_x, higher_x = _split(band, cut(left[j], right[j + 1]))
        for part, slope in (
            (lower_x, (zb[j + 1] - zb[j]) / (right[j + 1] - right[j])),
            (higher_x, (za[j + 1] - za[j]) / (left[j + 1] - left[j])),
        ):
            if part:
                diagonal = cut(left[j], right[j + 1])
                yield [
                    (
                        x,
                        y,
                        z
                        + za[j]
                        + (zb[j + 1] - za[j]) * (y - a[0]) / height
                        + slope * diagonal((x, y)),
                        u,
                        v,
                    )
                    for x, y, z, u, v in part
                ]
    if rest:
        yield rest


def _pieces(triangle, rows, levels):
    south, rest = _split(triangle, lambda p: p[1] - levels[0])
    if south:
        yield south
    if not rest:
        return
    start = max(0, bisect_right(levels, min(pt[1] for pt in rest)) - 1)
    for i in range(start, len(rows) - 1):
        if not rest:
            return
        band, rest = _split(rest, lambda p: p[1] - levels[i + 1])
        if band:
            yield from _strip(band, rows[i], rows[i + 1])
    if rest:
        yield rest


def _fit(mesh, rows, colors, materials):
    import bpy

    levels = [r[0] for r in rows]
    xmin = min(r[1] - r[3] for r in rows)
    xmax = max(r[1] + r[4] for r in rows)
    paint = {colors[m] for m in materials}
    result = copy(mesh)
    result.v = mesh.v.copy()
    result.f, result.m, result.face_uvs = [], [], {}
    for i, (face, mat) in enumerate(zip(mesh.f, mesh.m)):
        pts = [mesh.v[k] for k in face] if mat in paint else []
        if (
            not pts
            or all(y <= levels[0] for x, y, z in pts)
            or all(y >= levels[-1] for x, y, z in pts)
            or all(x <= xmin for x, y, z in pts)
            or all(x >= xmax for x, y, z in pts)
        ):
            active = False
        else:
            ymin, ymax = min(pt[1] for pt in pts), max(pt[1] for pt in pts)
            first = max(0, bisect_right(levels, ymin) - 1)
            last = min(len(rows), bisect_right(levels, ymax) + 1)
            stations = rows[first:last]
            active = not (
                max(pt[0] for pt in pts) < min(r[1] - r[3] for r in stations)
                or min(pt[0] for pt in pts) > max(r[1] + r[4] for r in stations)
            )
        if not active:
            if i in mesh.face_uvs:
                result.face_uvs[len(result.f)] = mesh.face_uvs[i]
            result.f.append(face)
            result.m.append(mat)
            continue

        # Affected carriageway and grass faces use the existing horizontal metre projection.
        uvs = mesh.face_uvs.get(i, [(x / 4, y / 4) for x, y, z in pts])
        corners = [(*pt, *uv) for pt, uv in zip(pts, uvs)]
        indices = [(0, 1, 2)]
        if len(face) != 3:
            temp = bpy.data.meshes.new('north-grade-tessellation')
            try:
                temp.from_pydata(pts, [], [tuple(range(len(pts)))])
                temp.calc_loop_triangles()
                indices = [tuple(t.vertices) for t in temp.loop_triangles]
            finally:
                bpy.data.meshes.remove(temp)
        for tri in indices:
            for piece in _pieces([corners[j] for j in tri], rows, levels):
                for j in range(1, len(piece) - 1):
                    vertices = (piece[0], piece[j], piece[j + 1])
                    result.face(
                        [q[:3] for q in vertices], mat, [q[3:] for q in vertices]
                    )
    result.north_lakeside_grade_v4 = True
    return result


def apply(base, colors):
    """Run after the six v3 refinements. Keep both surfaces on the same displacement planes."""
    rows = json.loads(
        Path(__file__).with_name('next_roads_north_profile.json').read_text()
    )
    layers = {'roads': ('asphalt', 'curb', 'roadYellow'), 'terrain': ('grass',)}
    # Existing soil crosses the western lane near y=876. Keep the small bedding relief
    # on the ground layer and fade it out before the adjacent curb transitions.
    soil = []
    for y, x, dz, west, east in rows:
        relief = 0.20 * max(0.0, min(1.0, (y - 871.0) / 2.0, (881.0 - y) / 4.0))
        soil.append((y, x, dz - relief, west, east))
    fitted = {
        k: _fit(base[k], soil if k == 'terrain' else rows, colors, materials)
        for k, materials in layers.items()
        if not getattr(base[k], 'north_lakeside_grade_v4', False)
    }
    base.update(fitted)
