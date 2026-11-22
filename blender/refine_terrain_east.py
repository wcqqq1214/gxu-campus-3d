"""Bed the east track's existing unbacked apron in the terrain mesh."""

import json
from copy import copy
from pathlib import Path

from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt, normal

from geometry import Mesh
from site_geometry import inside, mesh_triangles, ring_distance


def apply(base, colors):
    soil = base['terrain']
    if getattr(soil, 'east_track_bedded', False):
        return
    data = json.loads(
        Path(__file__).with_name('terrain_east_track_rim.json').read_text()
    )
    outer, rim, inset, core = data['rings']
    top = data['rimZ']
    xmin, ymin = map(min, zip(*outer))
    xmax, ymax = map(max, zip(*outer))
    local = Mesh()
    selected = []
    # Keep incoming face order, materials, and UV metadata outside the working set.
    for i, (face, mat) in enumerate(zip(soil.f, soil.m)):
        if mat != colors['grass']:
            continue
        pts = [soil.v[j] for j in face]
        if (
            max(p[0] for p in pts) < xmin
            or min(p[0] for p in pts) > xmax
            or max(p[1] for p in pts) < ymin
            or min(p[1] for p in pts) > ymax
        ):
            continue
        uvs = soil.face_uvs.get(i)
        if uvs is None:
            # Inherit the original face's projection, including explicit ground zones.
            cx = sum(p[0] for p in pts) / len(pts)
            cy = sum(p[1] for p in pts) / len(pts)
            ground = any(
                x0 <= cx <= x1 and y0 <= cy <= y1
                for x0, y0, x1, y1 in soil.ground_uv_bounds
            )
            n = normal([Vector(p) for p in pts])
            axis = (
                2
                if ground or mat in soil.xy_uv_materials
                else max(range(3), key=lambda k: abs(n[k]))
            )
            axes = [k for k in range(3) if k != axis]
            uvs = [(p[axes[0]] / 4, p[axes[1]] / 4) for p in pts]
        local.face(pts, mat, uvs)
        selected.append(i)
    if not selected:
        raise ValueError('Missing east track terrain')
    triangles = mesh_triangles(local)
    coords = []
    by_xy = {}

    def vertex(p):
        xy = tuple(p[:2])
        if xy not in by_xy:
            by_xy[xy] = len(coords)
            coords.append(xy)
        return by_xy[xy]

    faces = [[vertex(local.v[j]) for j in ids] for ids, _ in triangles]
    edges = []
    for ring in (outer, rim, inset, core):
        ids = [vertex(p) for p in ring]
        edges.extend(zip(ids, ids[1:] + ids[:1]))
    # The breaklines and the original terrain edges share intersection
    # vertices. Use a local origin to retain precision at short clipped edges.
    positions, _, pieces, original_verts, _, parents = delaunay_2d_cdt(
        [Vector((x - xmin, y - ymin)) for x, y in coords], edges, faces, 1, 1e-7, True
    )
    xy = [
        coords[src[0]] if src else (p.x + xmin, p.y + ymin)
        for p, src in zip(positions, original_verts)
    ]
    field = []
    for p in xy:
        distance = ring_distance(p, rim)
        if distance < 2e-5:
            field.append((1.0, top))
        elif inside(p, core) or ring_distance(p, core) < 2e-5:
            field.append((0.0, top))
        elif inside(p, inset):
            # Rejoin the original soil before reaching the retained football pitch.
            toe_distance = ring_distance(p, core)
            weight = toe_distance / (toe_distance + ring_distance(p, inset))
            field.append((weight, top - 0.025))
        elif inside(p, rim):
            # Keep paint, lanes and apron above the substrate; meet only the rim.
            field.append((1.0, top - 0.025 * min(1.0, distance / 0.45)))
        elif inside(p, outer):
            edge_distance = ring_distance(p, outer)
            field.append((edge_distance / (edge_distance + distance), top))
        else:
            field.append((0.0, top))

    cut = Mesh()
    for piece, source in zip(pieces, parents):
        if len(source) != 1:
            raise ValueError('East track terrain has overlapping or unowned faces')
        ids, fi = triangles[source[0]]
        a, b, c = [local.v[j] for j in ids]
        uvs = local.face_uvs[fi]
        au, bu, cu = [uvs[local.f[fi].index(j)] for j in ids]
        det = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        pts, tex = [], []
        for j in piece:
            x, y = xy[j]
            u = ((x - a[0]) * (c[1] - a[1]) - (y - a[1]) * (c[0] - a[0])) / det
            v = ((b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0])) / det
            z = a[2] + u * (b[2] - a[2]) + v * (c[2] - a[2])
            weight, target = field[j]
            pts.append((x, y, z + weight * max(0.0, target - z)))
            tex.append(
                tuple(au[k] + u * (bu[k] - au[k]) + v * (cu[k] - au[k]) for k in (0, 1))
            )
        cut.face(pts, local.m[fi], tex)
    result = copy(soil)
    result.v = list(soil.v)
    result.f, result.m, result.face_uvs = [], [], {}
    removed = set(selected)
    for i, (face, mat) in enumerate(zip(soil.f, soil.m)):
        if i in removed:
            continue
        if i in soil.face_uvs:
            result.face_uvs[len(result.f)] = soil.face_uvs[i]
        result.f.append(face)
        result.m.append(mat)
    result.extend(cut)
    result.east_track_bedded = True
    base['terrain'] = result
