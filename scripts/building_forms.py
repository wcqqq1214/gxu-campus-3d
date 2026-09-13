"""Resolve ordinary building form once, independently of rendering detail.

All coordinates are campus east/north meters. Height is the wall/body height;
roof rise is additional and explicitly estimated unless separately supplied.
No footprint, height or entrance here constitutes a new real-world survey.
"""
import math
import json
from pathlib import Path
import numpy as np
import mapbox_earcut as earcut
from shapely.geometry import Polygon, MultiPoint, Point
from shapely.ops import triangulate


def positive(value, label):
    if isinstance(value, bool):
        raise ValueError(f'{label} must be positive and finite')
    try:
        value = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f'{label} must be positive and finite') from error
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f'{label} must be positive and finite')
    return value


def infer_archetype(b):
    tags = b['tags']; name = b['name']; kind = tags.get('building')
    if any(word in name for word in ('餐厅', '食堂')):
        return 'canteen'
    if kind == 'dormitory' or '宿舍' in name:
        return 'dormitory'
    if kind in ('apartments', 'residential') or '公寓' in name:
        return 'residential-block'
    if '教学' in name:
        return 'teaching-block'
    return 'generic'


def fallback_entrances(polygons):
    entrances = []
    for index, poly in enumerate(polygons):
        ring = poly[0]
        a, b = max(zip(ring, ring[1:]), key=lambda edge: math.dist(*edge))
        dx, dy = b[0]-a[0], b[1]-a[1]
        length = math.hypot(dx, dy)
        sign = 1 if sum(a[0]*b[1]-b[0]*a[1] for a, b in zip(ring, ring[1:])) > 0 else -1
        nx, ny = dy/length*sign, -dx/length*sign
        entrances.append({'id': f'fallback-{index}', 'polygon': index,
                          'center': [(a[0]+b[0])/2, (a[1]+b[1])/2],
                          'bearing': math.degrees(math.atan2(nx, ny)) % 360,
                          'width': min(2.2, length*.65), 'primary': index == 0,
                          'basis': '最长外边中点的示意入口，位置与朝向待逐栋核对',
                          'status': 'estimated'})
    return entrances


def roof_geometry(polygons, kind, rise):
    """Rotation-independent, footprint-clipped hip/gable roof surfaces.

    Rectangles use a few planar roof faces. Irregular hip roofs use a bounded
    distance-to-eave surface on a 4 m sample lattice, clipped to the footprint;
    pitch and plateau are schematic, while mapped concavities/courts stay open.
    """
    vertices, triangles = [], []

    def face(points):
        start = len(vertices); vertices.extend(points)
        triangles.extend([start, start+1, start+2])
        if len(points) == 4:
            triangles.extend([start, start+2, start+3])

    for rings in polygons:
        poly = Polygon(rings[0], rings[1:])
        rect = poly.minimum_rotated_rectangle
        is_rectangle = len(rings) == 1 and len(rings[0]) == 5 and poly.symmetric_difference(rect).area / poly.area < .005
        if is_rectangle:
            points = rings[0][:-1]
            if sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points, points[1:]+points[:1])) < 0:
                points = points[::-1]
            # The mapped longest side, rather than the world X axis, sets ridge direction.
            i = max(range(4), key=lambda k: math.dist(points[k], points[(k+1) % 4]))
            a, b, c, d = [points[(i+k) % 4] for k in range(4)]
            left = [(a[k]+d[k])/2 for k in range(2)]
            right = [(b[k]+c[k])/2 for k in range(2)]
            inset = min(.24, math.dist(a, d)/(2*math.dist(left, right))) if kind == 'hipped' else 0
            p = [left[k]*(1-inset)+right[k]*inset for k in range(2)] + [rise]
            q = [right[k]*(1-inset)+left[k]*inset for k in range(2)] + [rise]
            a, b, c, d = [list(p)+[0] for p in (a, b, c, d)]
            for f in ((a,b,q,p),(b,c,q),(c,d,p,q),(d,a,p)):
                face(list(f))
            continue
        if kind != 'hipped':
            raise ValueError('A non-rectangular gabled roof needs explicit building parts')
        # Uniform samples are transformed into the building's local frame so
        # rotating the building does not change its roof sampling pattern.
        corners = list(rect.exterior.coords)
        a, b = max(zip(corners, corners[1:]), key=lambda e: math.dist(*e))
        angle = math.atan2(b[1]-a[1], b[0]-a[0]); ca, sa = math.cos(angle), math.sin(angle)
        ox, oy = poly.centroid.coords[0]
        def world(x, y): return (ox+x*ca-y*sa, oy+x*sa+y*ca)
        local = [( (x-ox)*ca+(y-oy)*sa, -(x-ox)*sa+(y-oy)*ca) for x,y in corners[:-1]]
        samples = [tuple(p) for ring in rings for p in ring[:-1]]
        for x in np.arange(min(p[0] for p in local), max(p[0] for p in local), 4):
            for y in np.arange(min(p[1] for p in local), max(p[1] for p in local), 4):
                point = world(x, y)
                if poly.contains(Point(point)): samples.append(point)
        for tri in triangulate(MultiPoint(samples)):
            clipped = tri.intersection(poly)
            pieces = [clipped] if clipped.geom_type == 'Polygon' else [p for p in getattr(clipped, 'geoms', []) if p.geom_type == 'Polygon']
            for piece in pieces:
                if piece.area < 1e-8: continue
                loops = [list(piece.exterior.coords)[:-1]] + [list(r.coords)[:-1] for r in piece.interiors]
                xy = [p for loop in loops for p in loop]
                indices = earcut.triangulate_float64(np.asarray(xy), np.cumsum([len(r) for r in loops], dtype=np.uint32))
                for i in range(0, len(indices), 3):
                    pts = [xy[int(k)] for k in indices[i:i+3]]
                    face([[x, y, min(rise, poly.boundary.distance(Point(x, y))*.6)] for x, y in pts])
    return {'vertices': vertices, 'triangles': triangles}


def resolve_form(b):
    height = positive(b['height'], f"{b['id']} height")
    levels = positive(b.get('levels', max(1, round(height/3.3))), f"{b['id']} levels")
    shape = b['tags'].get('roof:shape', 'flat')
    supported = shape in ('flat', 'hipped', 'gabled')
    roof = {'type': shape if supported else 'flat', 'rise': 0,
            'basis': 'OSM roof:shape；坡度及屋脊高度为示意估算' if shape != 'flat' and supported else '默认平顶，未获得逐栋屋顶形制资料',
            'status': 'osm-shape-estimated-dimensions' if supported and shape != 'flat' else 'estimated'}
    if not supported:
        roof['unresolvedShape'] = shape
    if roof['type'] != 'flat':
        roof['rise'] = 2.3
        roof['geometry'] = roof_geometry(b['polygons'], roof['type'], roof['rise'])
    return {'version': 1, 'archetype': infer_archetype(b), 'levels': levels,
            'height': height, 'parts': [], 'roof': roof,
            'entrances': fallback_entrances(b['polygons'])}


def prepare_existing_forms():
    """Update only ordinary forms on the current, already-normalized snapshot.

    Full prepare_geodata also calls resolve_form. This incremental entry point
    deliberately leaves terrain, road patches, surfaces and source dates alone.
    """
    # Keep the S1 CLI compatible without accidentally discarding S2 overrides.
    from building_overrides import prepare_existing_overrides
    prepare_existing_overrides()


if __name__ == '__main__':
    prepare_existing_forms()
