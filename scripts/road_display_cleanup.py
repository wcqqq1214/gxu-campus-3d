"""Bounded display-only road trimming, shared by full and incremental models.

No GIS or Blender dependency: clipping interpolates XYZ and optional loop UVs.
Mapped road data remains available for provenance and physical-site contracts.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_cuts(root=ROOT, ids=None, filename='road-display-cleanup.json'):
    data = json.loads((root / 'data' / filename).read_text())
    if data['version'] != 1:
        raise ValueError('Unsupported road display cleanup version')
    result = []
    for item in data['cuts']:
        if 'polygon' in item:
            points = item['polygon']
            if len(points) < 3 or any(len(p) != 2 or not all(math.isfinite(v) for v in p) for p in points):
                raise ValueError('Invalid display cut polygon')
            for a, b, c in zip(points, points[1:]+points[:1], points[2:]+points[:2]):
                if (b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0]) <= 0:
                    raise ValueError('Display cut polygon must be strictly convex and counterclockwise')
            result.append({**item, 'bounds': [min(p[0] for p in points), min(p[1] for p in points),
                                            max(p[0] for p in points), max(p[1] for p in points)]})
            continue
        x, y = item['origin']
        dx, dy = item['outward']
        width, length = item['halfWidth'], item['length']
        if (not all(math.isfinite(v) for v in (x, y, dx, dy, width, length))
                or width <= 0 or length <= 0 or math.hypot(dx, dy) < 1e-8):
            raise ValueError('Invalid road display cut dimensions')
        scale = math.hypot(dx, dy)
        dx, dy = dx / scale, dy / scale
        # Counterclockwise rectangle extends only outward from its cut plane.
        points = [(x + dx*s - dy*t, y + dy*s + dx*t)
                  for s, t in [(0, -width), (length, -width),
                               (length, width), (0, width)]]
        result.append({**item, 'polygon': points,
                       'bounds': [min(p[0] for p in points), min(p[1] for p in points),
                                  max(p[0] for p in points), max(p[1] for p in points)]})
    if len({c['id'] for c in result}) != len(result):
        raise ValueError('Duplicate road display cut ID')
    if ids is not None:
        unknown = set(ids) - {c['id'] for c in result}
        if unknown:
            raise ValueError(f'Unknown road display cuts: {sorted(unknown)}')
        result = [c for c in result if c['id'] in ids]
    return result


def area(poly):
    return abs(sum(a[0]*b[1] - b[0]*a[1]
                   for a, b in zip(poly, poly[1:] + poly[:1]))) / 2


def clip_edge(poly, a, b, inside):
    result = []
    sign = 1 if inside else -1
    for p, q in zip(poly, poly[1:] + poly[:1]):
        dp = ((b[0]-a[0])*(p[1]-a[1]) - (b[1]-a[1])*(p[0]-a[0])) * sign
        dq = ((b[0]-a[0])*(q[1]-a[1]) - (b[1]-a[1])*(q[0]-a[0])) * sign
        if dp >= 0:
            result.append(p)
        if (dp > 0 > dq) or (dp < 0 < dq):
            t = dp / (dp-dq)
            result.append(tuple(u + (v-u)*t for u, v in zip(p, q)))
    # Shared cut vertices must not leave zero-length edges or sliver faces.
    clean = []
    for p in result:
        if not clean or math.dist(p[:2], clean[-1][:2]) > 1e-9:
            clean.append(p)
    if len(clean) > 1 and math.dist(clean[0][:2], clean[-1][:2]) < 1e-9:
        clean.pop()
    return clean


def subtract(poly, mask):
    """Subtract a convex CCW mask; retain untouched polygons verbatim."""
    edges = list(zip(mask, mask[1:] + mask[:1]))
    intersection = poly
    for a, b in edges:
        intersection = clip_edge(intersection, a, b, True)
        if len(intersection) < 3:
            return [poly]
    if area(intersection) < 1e-9:
        return [poly]
    result, remaining = [], poly
    for a, b in edges:
        outside = clip_edge(remaining, a, b, False)
        if len(outside) >= 3 and area(outside) > 1e-9:
            result.append(outside)
        remaining = clip_edge(remaining, a, b, True)
        if len(remaining) < 3:
            break
    return result


def trim_mesh(mesh, cuts):
    """Trim final aggregated ordinary roads, preserving all unrelated faces."""
    if mesh.parts:
        raise ValueError('Trim aggregated roads after named parts have been merged')
    out = type(mesh)()
    out.v = list(mesh.v)
    out.ground_uv_bounds = list(mesh.ground_uv_bounds)
    out.xy_uv_materials = set(mesh.xy_uv_materials)
    source_uvs = getattr(mesh, 'source_uvs', None)
    if source_uvs is not None:
        out.source_uvs = []
    out.source_face_indices = []
    out.changed_materials = set()
    report = {cut['id']: {'changedFaces': 0, 'removedArea': 0.0} for cut in cuts}
    for index, (face, mat) in enumerate(zip(mesh.f, mesh.m)):
        points = [tuple(mesh.v[i]) for i in face]
        if source_uvs is not None:
            points = [p + tuple(uv) for p, uv in zip(points, source_uvs[index])]
        pieces = [points]
        for cut in cuts:
            x0, y0, x1, y1 = cut['bounds']
            next_pieces = []
            for poly in pieces:
                if (max(p[0] for p in poly) <= x0 or min(p[0] for p in poly) >= x1
                        or max(p[1] for p in poly) <= y0 or min(p[1] for p in poly) >= y1):
                    next_pieces.append(poly)
                    continue
                parts = subtract(poly, cut['polygon'])
                if parts != [poly]:
                    report[cut['id']]['changedFaces'] += 1
                    report[cut['id']]['removedArea'] += area(poly) - sum(area(p) for p in parts)
                next_pieces.extend(parts)
            pieces = next_pieces
        if pieces == [points]:
            out.f.append(face)
            out.m.append(mat)
            out.source_face_indices.append(index)
            if source_uvs is not None:
                out.source_uvs.append(source_uvs[index])
        else:
            out.changed_materials.add(mat)
            for poly in pieces:
                out.face([p[:3] for p in poly], mat)
                out.source_face_indices.append(index)
                if source_uvs is not None:
                    out.source_uvs.append([p[3:] for p in poly])
    return out, report
