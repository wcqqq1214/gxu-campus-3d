"""Validate an attributed pitched-roof mesh against its unchanged part footprint.

Vertices use campus XY and height above the part body, never absolute elevation.
Shared indexed edges enforce continuity; projected faces must tile the footprint.
"""
import copy
import math
from collections import Counter

from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union


def resolve_roof_mesh(polygons, mesh, rise):
    if not isinstance(mesh, dict) or set(mesh) != {'vertices', 'triangles'}:
        raise ValueError('Explicit roof mesh needs vertices and triangles')
    vertices, indices = mesh['vertices'], mesh['triangles']
    if (not isinstance(vertices, list) or not 4 <= len(vertices) <= 128 or
            not isinstance(indices, list) or not indices or len(indices) % 3 or len(indices) > 768):
        raise ValueError('Explicit roof mesh exceeds bounded vertex/triangle counts')
    if any(not isinstance(v, list) or len(v) != 3 or
           any(type(n) not in (int, float) or not math.isfinite(n) for n in v) for v in vertices):
        raise ValueError('Explicit roof vertices must be finite XYZ triples')
    if len({(round(v[0], 7), round(v[1], 7)) for v in vertices}) != len(vertices):
        raise ValueError('Explicit roof cannot duplicate projected vertices')
    if any(v[2] < 0 or v[2] > rise for v in vertices) or abs(max(v[2] for v in vertices)-rise) > 1e-6:
        raise ValueError('Explicit roof heights must span zero to the declared rise')
    if any(type(i) is not int or not 0 <= i < len(vertices) for i in indices) or set(indices) != set(range(len(vertices))):
        raise ValueError('Explicit roof indices must use every declared vertex')
    footprint = unary_union([Polygon(p[0], p[1:]) for p in polygons])
    faces, edges, normalized = [], Counter(), []
    for offset in range(0, len(indices), 3):
        tri = indices[offset:offset+3]
        a, b, c = [vertices[i] for i in tri]
        area2 = (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
        if abs(area2) < 1e-8:
            raise ValueError('Explicit roof contains a degenerate projected face')
        if area2 < 0:
            tri.reverse()
        normalized.extend(tri)
        faces.append(Polygon([vertices[i][:2] for i in tri]))
        for i, j in zip(tri, tri[1:]+tri[:1]):
            edges[tuple(sorted((i, j)))] += 1
    projected = unary_union(faces)
    if (projected.symmetric_difference(footprint).area > 1e-5 or
            sum(p.area for p in faces)-projected.area > 1e-5):
        raise ValueError('Explicit roof projected faces must tile its footprint without overlap')
    rim = footprint.boundary.buffer(1e-6)
    for (i, j), count in edges.items():
        if count == 1:
            if not rim.covers(LineString([vertices[i][:2], vertices[j][:2]])):
                raise ValueError('Explicit roof has an unjoined interior edge')
            if abs(vertices[i][2]) > 1e-6 or abs(vertices[j][2]) > 1e-6:
                raise ValueError('Explicit roof eaves must meet the part wall at zero rise')
        elif count != 2:
            raise ValueError('Explicit roof has a non-manifold edge')
    return {'vertices': copy.deepcopy(vertices), 'triangles': normalized}
