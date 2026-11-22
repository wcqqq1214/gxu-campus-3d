"""Restore the fenced residential lane end and the Gujiang Road gate crossing."""

from copy import copy
from math import hypot

from geometry import Mesh
from shore_geometry import bounds, overlaps
from site_geometry import mesh_triangles
from west22_ground import split


def _area(poly):
    if len(poly) < 3:
        return 0.0
    origin = poly[0]
    total = [0.0, 0.0, 0.0]
    for b, c in zip(poly[1:], poly[2:]):
        x, y, z = (b[i] - origin[i] for i in range(3))
        u, v, w = (c[i] - origin[i] for i in range(3))
        total[0] += y * w - z * v
        total[1] += z * u - x * w
        total[2] += x * v - y * u
    return hypot(*total) / 2


def _evaluate(plane, point):
    a, b, c, d = plane
    return a * point[0] + b * point[1] + c * point[2] + d


def _adjust(poly, planes, sign):
    # Modify only where every plane gives a positive offset. Intersections
    # carry original UVs. The least plane defines the offset on each facet.
    if any(all(_evaluate(q, p) <= 1e-8 for p in poly) for q in planes):
        return [poly]
    inside, parts = poly, []
    for plane in planes:
        inside, outside = split(inside, lambda p: _evaluate(plane, p))
        if _area(outside) > 1e-10:
            parts.append(outside)
        if _area(inside) <= 1e-10:
            return [poly]
    for i, q in enumerate(planes):
        facet = inside
        for j, v in enumerate(planes):
            if i == j:
                continue
            # A vertical face may lie entirely on a shared field edge.
            delta = tuple(b - a for a, b in zip(q, v))
            if all(abs(_evaluate(delta, p)) < 1e-9 for p in facet):
                if j < i:
                    facet = []
                    break
                continue
            facet, _ = split(facet, lambda p: _evaluate(delta, p))
            if len(facet) < 3:
                break
        if _area(facet) > 1e-10:
            parts.append(
                [(p[0], p[1], p[2] + sign * _evaluate(q, p), *p[3:]) for p in facet]
            )
    return parts


def _fenced_end(bed):
    # Continue the existing high-side service plane measured at x=144..152.
    # Tie back just beyond the end cap without crossing the inter-yard fence.
    h = 5.229 - bed
    return (
        (-0.0018, -0.049, -1, h + 0.0018 * 145 - 0.049 * 909.875),
        (2.8, 0, -1, h - 2.8 * 139.27 + 0.16),
        (-2.0, 0, -1, h + 2.0 * 144.6 + 0.16),
        (0, 5.0, -1, h + 5.0 * 912.43 + 0.16),
        (0, -5.0, -1, h - 5.0 * 907.31 + 0.16),
    )


def _gate(sign):
    # Distance east of the through-road datum at the zebra crossing. Keep
    # that datum fixed. Tilt pavement, markings and bed by the same amount.
    # Both tapers end before the adjacent building footprints.
    cross_y = 0.18
    intercept = -379.70 + cross_y * 332.40

    def cross(slope, offset):
        return slope, slope * cross_y, 0, slope * intercept + offset

    limits = (
        (0, 0.050, 0, 0.050 * 363.0),
        (0, -0.065, 0, -0.065 * 307.0),
    )
    if sign > 0:
        return (cross(0.18, 0), (0, 0, 0, 1.55), cross(-0.52, 0.52 * 16.0), *limits)
    return (cross(-0.17, 0), (0, 0, 0, 0.70), cross(0.11, 0.11 * 10.3), *limits)


def _mesh(mesh, road_material, bed):
    if getattr(mesh, 'east_gate_and_fenced_end', False):
        return mesh
    yard = (136.7, -913.8, 147.0, -905.8)
    gate = (363.0, -363.0, 402.0, -307.0)
    fields = ((yard, _fenced_end(bed), 1), (gate, _gate(1), 1), (gate, _gate(-1), -1))
    candidates = {}
    ngons = Mesh()
    polygon_refs = []
    for i, (face, mat) in enumerate(zip(mesh.f, mesh.m)):
        pts = [mesh.v[j] for j in face]
        box = bounds(pts)
        active = [
            (planes, sign)
            for extent, planes, sign in fields
            if overlaps(box, extent) and (extent != yard or bed or mat == road_material)
        ]
        if not active:
            continue
        uvs = mesh.face_uvs.get(i) or [(x / 4, y / 4) for x, y, _ in pts]
        original = [(*p, *uv) for p, uv in zip(pts, uvs)]
        candidates[i] = (original, active)
        if len(face) > 3:
            polygon_refs.append((i, len(ngons.v)))
            ngons.face(pts, mat)

    # Retain Blender's existing diagonal on non-planar road/DEM quads.
    # Otherwise the unmodified part of a clipped quad may change elevation.
    triangles = {}
    if ngons.f:
        for tri, index in mesh_triangles(ngons):
            i, start = polygon_refs[index]
            original = candidates[i][0]
            triangles.setdefault(i, []).append([original[j - start] for j in tri])

    replacements = {}
    for i, (original, active) in candidates.items():
        pieces = triangles.get(i, [original])
        result = []
        changed = False
        for piece in pieces:
            parts = [piece]
            for planes, sign in active:
                parts = [
                    patch for poly in parts for patch in _adjust(poly, planes, sign)
                ]
            changed |= len(parts) != 1 or parts[0] is not piece
            result.extend(parts)
        if changed:
            replacements[i] = result
    if not replacements:
        return mesh
    result = copy(mesh)
    result.v = mesh.v.copy()
    result.f, result.m, result.face_uvs = [], [], {}
    for i, (face, mat) in enumerate(zip(mesh.f, mesh.m)):
        if i in replacements:
            for patch in replacements[i]:
                result.face([p[:3] for p in patch], mat, [p[3:] for p in patch])
        else:
            if i in mesh.face_uvs:
                result.face_uvs[len(result.f)] = mesh.face_uvs[i]
            result.f.append(face)
            result.m.append(mat)
    result.east_gate_and_fenced_end = True
    return result


def apply(base, colors):
    """Grade the two local road surfaces together with the existing earth bed."""
    road = _mesh(base['roads'], colors['road'], 0.0)
    soil = _mesh(base['terrain'], None, 0.15)
    base.update(roads=road, terrain=soil)
