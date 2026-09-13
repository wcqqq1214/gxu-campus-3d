"""Photo-attributed external porticos, without changing mapped building rings."""
import math

from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

from building_forms import positive


def resolve_attached_portico(building, entrance, config, edge_length, parts=()):
    keys = {'width', 'depth', 'platformHeight', 'clearHeight', 'slabThickness',
            'parapetHeight', 'columnWidth', 'columnInset', 'steps', 'tread', 'stepBaseHeight'}
    if not isinstance(config, dict) or set(config) != keys:
        raise ValueError('Attached portico requires explicit dimensions and step count')
    p = {key: positive(value, 'attached portico '+key)
         for key, value in config.items() if key not in ('steps', 'stepBaseHeight', 'parapetHeight')}
    parapet=config['parapetHeight']
    if type(parapet) not in (int,float) or not math.isfinite(parapet) or parapet<0 or 0<parapet<=.3:
        raise ValueError('Attached portico parapet must be absent or tall enough for its two open rows')
    p['parapetHeight']=float(parapet)
    base=config['stepBaseHeight']
    if type(base) not in (int,float) or not math.isfinite(base) or not 0 <= base < p['platformHeight']:
        raise ValueError('Attached portico step base must be finite, nonnegative and below platform')
    p['stepBaseHeight']=base
    if type(config['steps']) is not int or not 1 <= config['steps'] <= 12:
        raise ValueError('Attached portico steps must be an integer from 1 to 12')
    p['steps'] = config['steps']
    w, d, cw, inset = (p[key] for key in ('width', 'depth', 'columnWidth', 'columnInset'))
    if w/2 > min(entrance['t'], 1-entrance['t'])*edge_length:
        raise ValueError('Attached portico extends beyond its facade')
    if not cw/2 <= inset < min(w, d)/2-cw/2:
        raise ValueError('Attached portico columns overlap or leave the platform')
    if entrance['width']+.4 > w-2*inset-cw:
        raise ValueError('Attached portico columns obstruct the entrance width')
    top = p['clearHeight']+p['slabThickness']+p['parapetHeight']
    if not p['platformHeight']+2.8 < p['clearHeight'] < top < building['height']:
        raise ValueError('Attached portico vertical dimensions conflict with doorway or building')
    angle = math.radians(entrance['bearing'])
    n = [math.sin(angle), math.cos(angle)]
    tangent = [n[1], -n[0]]
    def point(u, v):
        return [entrance['center'][i]+tangent[i]*u+n[i]*v for i in (0, 1)]
    body = unary_union([Polygon(r[0], r[1:]) for r in building['polygons']])
    facade = LineString([point(-w/2, 0), point(w/2, 0)])
    footprint = Polygon([point(-w/2, 0), point(w/2, 0),
                         point(w/2, d+p['steps']*p['tread']),
                         point(-w/2, d+p['steps']*p['tread'])])
    if not body.boundary.buffer(.00001).covers(facade) or footprint.intersection(body).area > .00001:
        raise ValueError('Attached portico must meet the facade and remain outside every building ring')
    # A porch may straddle two solid height partitions, but its attachment
    # must fit beneath each local roof and cannot cross an open lower storey.
    for part in parts:
        shape=unary_union([Polygon(r[0],r[1:]) for r in part['polygons']])
        if facade.intersection(shape.buffer(.0000001)).length>.00001:
            if 'openBelow' in part or top>=part['height']:
                raise ValueError('Attached portico requires a solid facade taller than its canopy in every touched part')
    p['footprint'] = [list(x) for x in footprint.exterior.coords]
    p['columns'] = [point(u, v) for u in (-w/2+inset, w/2-inset) for v in (inset, d-inset)]
    return p
