"""Fit the farm-lane terrain to the surveyed-model carriageway triangles."""

import json
from copy import copy
from pathlib import Path

from geometry import Mesh
from shore_geometry import bounds, conform_edges, overlaps
from site_geometry import mesh_triangles
from west22_ground import split


def _area(points):
    """Signed double area, relative to the first vertex for short clipped edges."""
    if len(points) < 3:
        return 0.0
    ox, oy = points[0][:2]
    return sum(
        (a[0] - ox) * (b[1] - oy) - (b[0] - ox) * (a[1] - oy)
        for a, b in zip(points[1:], points[2:])
    )


def _cutter(triangle):
    a, b, c = triangle
    area = _area(triangle)
    dx = ((b[2] - a[2]) * (c[1] - a[1]) - (c[2] - a[2]) * (b[1] - a[1])) / area
    dy = ((b[0] - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (b[2] - a[2])) / area

    def height(pt):
        return a[2] + dx * (pt[0] - a[0]) + dy * (pt[1] - a[1])

    planes = [lambda p: p[2] - height(p) - 1e-8]
    for start, end in zip(triangle, triangle[1:] + triangle[:1]):
        ux, uy = end[0] - start[0], end[1] - start[1]
        planes.append(
            lambda p, x=start[0], y=start[1], u=ux, v=uy: (
                u * (p[1] - y) - v * (p[0] - x)
            )
        )
    return bounds(triangle), planes, height


def _lower_face(polygon, cutters):
    """Partition only where the road-bed cap is below the incoming terrain."""
    original = [polygon]
    finished = []
    for box, planes, height in cutters:
        remaining = []
        for face in original:
            if not overlaps(bounds(face), box):
                remaining.append(face)
                continue
            inside = face
            outside = []
            for plane in planes:
                inside, part = split(inside, plane)
                if abs(_area(inside)) < 1e-10:
                    break
                if abs(_area(part)) > 1e-10:
                    outside.append(part)
            if abs(_area(inside)) < 1e-10:
                remaining.append(face)
                continue
            remaining.extend(outside)
            finished.append([(x, y, height((x, y))) for x, y, _ in inside])
        original = remaining
    return finished + original if finished else []


def fit_farm_bed(terrain, roads, road_material):
    if getattr(terrain, 'north_farm_bed_fitted', False):
        return terrain
    data = json.loads(
        Path(__file__).with_name('road_review_north_bed.json').read_text()
    )
    expected = {tuple(map(tuple, f)) for f in data['sourceFaces']}
    # Guard the existing road elevations. Other review regions can freely modify
    # the same aggregated Mesh outside this group of triangles.
    for face, mat in zip(roads.f, roads.m):
        if mat == road_material and -785 < roads.v[face[0]][0] < -758:
            expected.discard(tuple(tuple(roads.v[i]) for i in face))
    if expected:
        raise ValueError('North farm-lane road triangle or elevation changed')
    cutters = [_cutter(t) for t in data['cutTriangles']]
    region = bounds([p for t in data['cutTriangles'] for p in t])
    result = copy(terrain)
    result.v = list(terrain.v)
    result.f, result.m, result.face_uvs = [], [], {}
    local = Mesh()
    for i, (face, mat) in enumerate(zip(terrain.f, terrain.m)):
        pts = [terrain.v[j] for j in face]
        if overlaps(bounds(pts), region):
            if i in terrain.face_uvs:
                raise ValueError('North farm bed requires existing planar terrain UVs')
            local.face(pts, mat)
        else:
            if i in terrain.face_uvs:
                result.face_uvs[len(result.f)] = terrain.face_uvs[i]
            result.f.append(face)
            result.m.append(mat)
    cut = Mesh()
    for indices, i in mesh_triangles(local):
        pts = [local.v[j] for j in indices]
        for poly in _lower_face(pts, cutters) or [pts]:
            for j in range(1, len(poly) - 1):
                tri = [poly[0], poly[j], poly[j + 1]]
                if abs(_area(tri)) > 1e-10:
                    cut.face(tri, local.m[i])
    # Equal edge subdivisions survive the production terrain quantizer. Limit
    # conformance to this local subset so other sites keep their own face UVs.
    result.extend(conform_edges(cut, region))
    result.north_farm_bed_fitted = True
    return result
