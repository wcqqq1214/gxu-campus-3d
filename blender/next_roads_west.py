"""Regrade four photographed west-campus road reaches without changing their plan."""

import json
from bisect import bisect_left
from copy import copy
from functools import lru_cache
from math import ceil, floor
from pathlib import Path

from geometry import Mesh
from refine_roads_west import _bands, _source_uv, _split
from site_geometry import mesh_triangles

# The bounds include the shoulders, the sports-field gate and the entire
# transition to the retained surface. Coordinates are campus metres.
AREAS = {
    'huixian': (-403, -255, -327, -223),
    'materials': (-624, -882, -586, -866),
    'east-turn': (-622, -803, -589, -782),
    'platform-west': (-739, -835, -705, -770),
}


def _smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3.0 - 2.0 * t)


@lru_cache(maxsize=1)
def _profiles():
    path = Path(__file__).with_name('next_roads_west_profiles.json')
    return {r['name']: r for r in json.loads(path.read_text())}


def _delta(name, x, y):
    r = _profiles()[name]
    axial = (x, y)[r['axis']] - r['start']
    if axial <= 0 or axial >= len(r['offset']) - 1:
        return 0.0
    if name == 'huixian':
        lateral = y - (-234.473 + 0.0196 * (x + 380.308))
    elif name == 'materials':
        lateral = y - (-874.563 + 0.00869 * (x + 622.606))
    elif name == 'east-turn':
        lateral = y - (-793.2 + 0.0253 * (x + 625.0))
    else:
        lateral = (x - (-723.463 - 0.18574 * (y + 796.526))) / 1.0171
    verge = r['verge']
    if name == 'materials' and lateral < 0:
        verge = min(verge, 874.563 - 869.73 + 0.00869 * (x + 622.606))
    weight = _smooth((verge - abs(lateral)) / (verge - r['halfWidth']))
    if name == 'platform-west' and lateral > 0:
        # The eastbound service road joins the west edge of the platform here.
        cross_y = -801.604 + 0.014 * (x + 722.474)
        arm = _smooth((16 - lateral) / 13) * _smooth((6.5 - abs(y - cross_y)) / 3.5)
        weight = max(weight, arm)
    j = floor(axial)
    a, b = r['offset'][j : j + 2]
    dz = (a + (b - a) * (axial - j)) * weight
    if name == 'huixian':
        # Beyond the painted carriageway the gated lane climbs onto the road.
        # Carry its wheel tracks through the short overlay at the old edge.
        dx = abs(x - (-380.308 - 0.0138 * (y + 234.473)))
        gate = _smooth((5.2 - dx) / 2.6)
        bump = _smooth((y + 253) / 13) * _smooth((-235.2 - y) / 4.6)
        dz += 0.20 * gate * bump
        if y < -248.5:
            dz *= _smooth((x + 383.3) / 1.05)
        # Keep the existing planted tree at the southern shoulder seated.
        dz *= _smooth(((x + 340.7) ** 2 + (y + 242.8) ** 2) / 3.0)
    return dz


def _cells(poly, box):
    x0, y0, x1, y1 = box
    for axis, cut, high in (
        (0, x0, True),
        (0, x1, False),
        (1, y0, True),
        (1, y1, False),
    ):
        left, right = _split(poly, axis, cut)
        poly, outside = (right, left) if high else (left, right)
        if len(outside) >= 3:
            yield outside, False
        if len(poly) < 3:
            return
    # At existing building toes, keep the tie exact between adjacent cells.
    rows = sorted(
        {
            *range(ceil(y0 / 2) * 2, ceil(y1), 2),
            *(q for q in (-879.34, -250.45, -222.4) if y0 < q < y1),
        }
    )
    for row in _bands(poly, 1, rows):
        for cell in _bands(row, 0, range(ceil(x0 / 2) * 2, ceil(x1), 2)):
            yield cell, True


def _regrade(mesh, ground):
    selected = set()
    crops = {n: Mesh() for n in AREAS}
    for fi, f in enumerate(mesh.f):
        pts = [mesh.v[i] for i in f]
        x, y, _ = zip(*pts)
        xmin, xmax, ymin, ymax = min(x), max(x), min(y), max(y)
        for name, (x0, y0, x1, y1) in AREAS.items():
            if xmin < x1 and xmax > x0 and ymin < y1 and ymax > y0:
                crops[name].face(pts, mesh.m[fi], _source_uv(mesh, fi, pts, ground))
                selected.add(fi)
                break
    out = copy(mesh)
    used = {i for fi in selected for i in mesh.f[fi]}
    for fi, f in enumerate(mesh.f):
        if fi not in selected:
            used.difference_update(f)
    dropped = sorted(used)
    out.v = [p for i, p in enumerate(mesh.v) if i not in used]
    out.parts = [
        (n, a - bisect_left(dropped, a), b - bisect_left(dropped, b))
        for n, a, b in mesh.parts
    ]
    out.f, out.m, out.face_uvs = [], [], {}
    for fi, f in enumerate(mesh.f):
        if fi not in selected:
            if fi in mesh.face_uvs:
                out.face_uvs[len(out.f)] = mesh.face_uvs[fi]
            out.f.append(tuple(i - bisect_left(dropped, i) for i in f))
            out.m.append(mesh.m[fi])
    for name, local in crops.items():
        for ids, fi in mesh_triangles(local):
            uv = dict(zip(local.f[fi], local.face_uvs[fi]))
            triangle = [(*local.v[i], *uv[i]) for i in ids]
            for ring, inside in _cells(triangle, AREAS[name]):
                points = [
                    (x, y, z + (_delta(name, x, y) if inside else 0))
                    for x, y, z, *_ in ring
                ]
                for j in range(1, len(points) - 1):
                    ijk = (0, j, j + 1)
                    a, b, c = [points[k] for k in ijk]
                    u, v = ([q[i] - a[i] for i in range(3)] for q in (b, c))
                    if (
                        sum(
                            (u[i] * v[(i + 1) % 3] - v[i] * u[(i + 1) % 3]) ** 2
                            for i in range(3)
                        )
                        > 1e-18
                    ):
                        out.face([a, b, c], local.m[fi], [ring[k][3:] for k in ijk])
    return out


def apply(base, colors):
    if getattr(base['roads'], '_west_v4_graded', False):
        return
    roads, terrain = _regrade(base['roads'], False), _regrade(base['terrain'], True)
    roads._west_v4_graded = True
    base.update(roads=roads, terrain=terrain)
