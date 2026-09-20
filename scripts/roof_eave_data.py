"""Resolve a canted roof eave on a documented solid part's outer edge."""
import copy
import math
from shapely.geometry import Polygon
from shapely.ops import unary_union


def resolve_roof_eave(building, form, config):
    required = {'part', 'polygon', 'edge', 'backDepth', 'projection', 'sideOverhang', 'rise', 'capThickness'}
    if not isinstance(config, dict) or set(config) != required:
        raise ValueError('Roof eave requires a part edge and complete profile dimensions')
    if any(k in form for k in ('stairTower', 'roofDome')):
        raise ValueError('Roof eave cannot combine with a stair tower or roof dome')
    if not isinstance(config['part'], str) or not config['part']:
        raise ValueError('Roof eave requires a named support part')
    for key in ('polygon', 'edge'):
        if type(config[key]) is not int or config[key] < 0:
            raise ValueError('Roof eave indices must be nonnegative integers')
    bounds = {'backDepth': (.25, 2), 'projection': (.3, 3),
              'sideOverhang': (0, 2), 'rise': (.3, 3), 'capThickness': (.1, .5)}
    for key, (low, high) in bounds.items():
        value = config[key]
        if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError('Roof eave dimension outside supported range: ' + key)
    parts = form['parts'] or [{'id': 'body', 'polygons': building['polygons'],
                              'height': form['height'], 'roof': form['roof']}]
    matches = [p for p in parts if p['id'] == config['part']]
    if len(matches) != 1 or matches[0]['roof']['type'] != 'flat' or 'openBelow' in matches[0]:
        raise ValueError('Roof eave needs one solid flat support part')
    part = matches[0]
    try:
        ring = part['polygons'][config['polygon']][0]
        a, b = ring[config['edge']], ring[config['edge'] + 1]
    except IndexError as error:
        raise ValueError('Roof eave edge does not exist') from error
    length = math.dist(a, b)
    if not 3 <= length <= 40:
        raise ValueError('Roof eave edge must be 3–40 metres long')
    tx, ty = (b[0]-a[0])/length, (b[1]-a[1])/length
    sign = 1 if Polygon(ring).exterior.is_ccw else -1
    nx, ny = sign*ty, -sign*tx
    point = lambda u, v: [a[0]+tx*u+nx*v, a[1]+ty*u+ny*v]
    support = Polygon([point(0, 0), point(length, 0),
                       point(length, -config['backDepth']), point(0, -config['backDepth'])])
    shape = unary_union([Polygon(p[0], p[1:]) for p in part['polygons']])
    if not shape.buffer(1e-7).covers(support):
        raise ValueError('Roof eave support crosses a courtyard or leaves the solid roof')
    side = config['sideOverhang']
    envelope = Polygon([point(-side, -config['backDepth']), point(length+side, -config['backDepth']),
                        point(length+side, config['projection']), point(-side, config['projection'])])
    for other in parts:
        if other is part or other['height'] < part['height'] - 1e-6:
            continue
        other_shape = unary_union([Polygon(p[0], p[1:]) for p in other['polygons']])
        if envelope.intersection(other_shape).area > 1e-6:
            raise ValueError('Roof eave conflicts with an equal or taller adjacent part')
    return {**copy.deepcopy(config), 'start': list(a), 'end': list(b),
            'normal': [nx, ny], 'baseHeight': part['height'], 'length': length}
