"""Validate one explicitly located roof dome on an existing solid flat roof."""
import copy
import math
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union


def resolve_roof_dome(building, form, config):
    required = {'center', 'radius', 'drumHeight', 'rise'}
    if not isinstance(config, dict) or set(config) != required:
        raise ValueError('Roof dome requires center, radius, drumHeight and rise')
    center = config['center']
    if not isinstance(center, list) or len(center) != 2:
        raise ValueError('Roof dome center needs two coordinates')
    if any(type(v) not in (int, float) or not math.isfinite(v)
           for v in [*center, config['radius'], config['drumHeight'], config['rise']]):
        raise ValueError('Roof dome dimensions must be finite numbers')
    radius, drum, rise = (config[k] for k in ('radius', 'drumHeight', 'rise'))
    if not 1 <= radius <= 15 or not .1 <= drum <= 3 or not .25*radius <= rise <= 1.5*radius:
        raise ValueError('Roof dome dimensions are outside the supported range')
    if 'stairTower' in form:
        raise ValueError('An open stair tower cannot support a roof dome')
    parts = form['parts'] or [{'id': 'body', 'polygons': building['polygons'],
                              'height': form['height'], 'roof': form['roof']}]
    point = Point(center)
    supports = []
    for part in parts:
        shape = unary_union([Polygon(p[0], p[1:]) for p in part['polygons']])
        # Exact center-to-boundary clearance includes courtyards and avoids
        # approximating a circle by a polygon that can miss small intrusions.
        if (part['roof']['type'] == 'flat' and 'openBelow' not in part
                and shape.contains(point) and shape.boundary.distance(point) >= radius + .5):
            supports.append(part)
    if len(supports) != 1:
        raise ValueError('Roof dome needs one solid flat support with 0.5 m edge clearance')
    return {**copy.deepcopy(config), 'part': supports[0]['id'],
            'baseHeight': supports[0]['height']}
