"""An inset edge rim following the supporting flat or explicit roof surface."""
import math
import numpy as np
import mapbox_earcut as earcut
from shapely.geometry import Polygon, LineString
from shapely.geometry.polygon import orient
from shapely.ops import unary_union


def resolve_roof_rim(part, config):
    if not isinstance(config, dict) or set(config) != {'edges', 'width', 'height'}:
        raise ValueError('Roof rim needs edges, width and height')
    if part['roof']['type'] not in ('flat', 'profiled') or 'slattedRoof' in part.get('openBelow', {}):
        raise ValueError('Roof rim requires a continuous flat or profiled support')
    for key, bounds in [('width', (.15, .8)), ('height', (.1, .8))]:
        value = config[key]
        if type(value) not in (float, int) or not math.isfinite(value) or not bounds[0] <= value <= bounds[1]:
            raise ValueError('Roof rim dimension outside supported range: ' + key)
    edges = config['edges']
    if not isinstance(edges, list) or not 1 <= len(edges) <= 32:
        raise ValueError('Roof rim requires 1–32 exterior edge anchors')
    selected, seen = [], set()
    for edge in edges:
        if (not isinstance(edge, list) or len(edge) != 2 or
                any(type(i) is not int or i < 0 for i in edge) or tuple(edge) in seen):
            raise ValueError('Roof rim anchors must be unique polygon/edge pairs')
        seen.add(tuple(edge))
        try:
            ring = part['polygons'][edge[0]][0]
            line = LineString([ring[edge[1]], ring[edge[1]+1]])
        except IndexError as error:
            raise ValueError('Roof rim edge does not exist') from error
        if line.length < .01:
            raise ValueError('Roof rim edge is degenerate')
        selected.append(line.buffer(config['width'], cap_style=3, join_style=2))
    shape = unary_union([Polygon(p[0], p[1:]) for p in part['polygons']])
    band = shape.intersection(unary_union(selected))
    if band.is_empty or shape.difference(band).area < .1:
        raise ValueError('Roof rim must leave an open central roof surface')
    if part['roof']['type'] == 'profiled':
        mesh = part['roof']['geometry']
        supports = [[mesh['vertices'][k] for k in mesh['triangles'][i:i+3]]
                    for i in range(0, len(mesh['triangles']), 3)]
    else:
        supports = []
        for poly, indices in zip(part['polygons'], part['triangles']):
            points = [p+[0] for ring in poly for p in ring[:-1]]
            supports.extend([points[k] for k in indices[i:i+3]] for i in range(0, len(indices), 3))
    tops, walls, coverage = [], [], []
    rim = band.boundary.buffer(1e-6)
    for a, b, c in supports:
        denominator = (b[0]-a[0])*(c[1]-a[1])-(c[0]-a[0])*(b[1]-a[1])
        def at(p, rise=0):
            u = ((p[0]-a[0])*(c[1]-a[1])-(c[0]-a[0])*(p[1]-a[1]))/denominator
            v = ((b[0]-a[0])*(p[1]-a[1])-(p[0]-a[0])*(b[1]-a[1]))/denominator
            return [*p, a[2]+u*(b[2]-a[2])+v*(c[2]-a[2])+rise]
        clipped = Polygon([a[:2], b[:2], c[:2]]).intersection(band)
        pieces = [clipped] if clipped.geom_type == 'Polygon' else list(getattr(clipped, 'geoms', []))
        for piece in pieces:
            if piece.geom_type != 'Polygon' or piece.area < 1e-9:
                continue
            piece = orient(piece)
            coverage.append(piece)
            rings = [list(piece.exterior.coords)[:-1]] + [list(r.coords)[:-1] for r in piece.interiors]
            points = [list(p) for ring in rings for p in ring]
            indices = earcut.triangulate_float64(np.asarray(points), np.cumsum([len(r) for r in rings], dtype=np.uint32))
            tops.extend([at(points[k], config['height']) for k in indices[i:i+3]] for i in range(0, len(indices), 3))
            for ring in rings:
                for p, q in zip(ring, ring[1:]+ring[:1]):
                    if math.dist(p, q) > 1e-6 and rim.covers(LineString([p, q])):
                        walls.append([at(p), at(q), at(q, config['height']), at(p, config['height'])])
    if band.symmetric_difference(unary_union(coverage)).area > 1e-5:
        raise ValueError('Roof rim is not fully supported by the roof mesh')
    return {'tops': tops, 'walls': walls, 'areaMeters2': band.area}
