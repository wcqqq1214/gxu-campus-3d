"""Explicit two-storey gallery additions attached outside mapped wall lines."""
import copy
import math
from shapely.geometry import Polygon
from shapely.ops import unary_union


def resolve_attached_gallery(building, facade, part, config):
    keys = {'depth', 'endInset', 'railHeight', 'balusterWidth', 'balusterSpacing',
            'roofDrop', 'slabThickness', 'upperOpenings'}
    if not isinstance(config, dict) or set(config) != keys:
        raise ValueError('Attached gallery needs explicit dimensions and upper openings')
    limits = {'depth': (.8, 4), 'endInset': (0, .5), 'railHeight': (.6, 1.2),
              'balusterWidth': (.08, .18), 'balusterSpacing': (.22, .6),
              'roofDrop': (.1, .5), 'slabThickness': (.12, .3)}
    for key, (lo, hi) in limits.items():
        value = config[key]
        if type(value) not in (int, float) or not math.isfinite(value) or not lo <= value <= hi:
            raise ValueError('Invalid attached gallery ' + key)
    if facade['levels'] != 2 or 'openBelow' in part or facade['ring'] != 0:
        raise ValueError('Attached gallery requires a solid two-storey exterior wall')
    if part.get('roof', {}).get('type') != 'hipped':
        raise ValueError('Attached gallery currently joins a hipped roof eave')
    a, b, n = facade['start'], facade['end'], facade['normal']
    length = math.dist(a, b)
    u = [(b[k] - a[k]) / length for k in (0, 1)]
    inset = config['endInset']
    if length - 2 * inset < 2 or config['balusterSpacing'] < config['balusterWidth'] + .12:
        raise ValueError('Attached gallery needs usable width and railing gaps')
    def point(t, depth):
        return [a[k] + u[k] * t + n[k] * depth for k in (0, 1)]
    outer = [point(inset,config['depth']),point(length-inset,config['depth'])]
    if inset == 0:
        # The two neighbouring mapped returns bound this recessed bay. Use
        # their actual directions, including oblique sub-centimetre offsets,
        # so roofs and walls meet them without a fabricated side gap.
        ring=building['polygons'][facade['polygon']][0][:-1];ei=facade['edge']
        outer=[]
        for end,neighbor in [(a,ring[(ei-1)%len(ring)]),(b,ring[(ei+2)%len(ring)])]:
            vector=[neighbor[k]-end[k] for k in (0,1)]
            reach=sum(vector[k]*n[k] for k in (0,1))
            if reach < config['depth']+.05:
                raise ValueError('Zero-inset gallery requires two enclosing mapped wing walls')
            outer.append([end[k]+vector[k]*config['depth']/reach for k in (0,1)])
    footprint = Polygon([point(inset,0),point(length-inset,0),outer[1],outer[0]])
    body = unary_union([Polygon(p[0], p[1:]) for p in building['polygons']])
    if footprint.intersection(body).area > 1e-5:
        raise ValueError('Attached gallery crosses the mapped building or its wings')
    h = facade['height']; floor = h / 2
    ceiling = h - config['roofDrop'] - config['slabThickness']
    if ceiling - floor - config['railHeight'] < 1.3:
        raise ValueError('Attached gallery roof leaves insufficient open height')
    openings = config['upperOpenings']
    if not isinstance(openings, list) or not openings:
        raise ValueError('Attached gallery needs sourced upper opening positions')
    intervals = []
    for opening in openings:
        if not isinstance(opening, dict) or set(opening) != {'t', 'width', 'bottom', 'top', 'kind'}:
            raise ValueError('Invalid attached gallery opening fields')
        if opening['kind'] not in ('door', 'window'):
            raise ValueError('Invalid attached gallery opening kind')
        for key in ('t', 'width', 'bottom', 'top'):
            if type(opening[key]) not in (int, float) or not math.isfinite(opening[key]):
                raise ValueError('Invalid attached gallery opening number')
        lo = opening['t'] * length - opening['width']/2 - .07
        hi = opening['t'] * length + opening['width']/2 + .07
        if opening['width'] < .5 or not inset <= lo < hi <= length-inset:
            raise ValueError('Attached gallery opening leaves its rear wall')
        if not floor <= opening['bottom'] < opening['top'] <= h-.3:
            raise ValueError('Attached gallery opening leaves the upper storey')
        if opening['top'] - opening['bottom'] < 1 or (opening['kind'] == 'door' and opening['bottom'] != floor):
            raise ValueError('Attached gallery opening has invalid height')
        if any(min(hi, right) > max(lo, left) for left, right in intervals):
            raise ValueError('Attached gallery openings overlap')
        intervals.append((lo, hi))
    return {**copy.deepcopy(config), 'footprint': [list(p) for p in footprint.exterior.coords],
            'floorHeight': floor, 'boundedEnds':inset==0,
            'outerOffsets':[sum((end[k]-a[k])*u[k] for k in (0,1)) for end in outer]}


def validate_gallery_context(buildings):
    occupied = []
    for building in buildings:
        for facade in building.get('form', {}).get('facades', []):
            if 'attachedGallery' not in facade:
                continue
            shape = Polygon(facade['attachedGallery']['footprint'])
            for other in buildings:
                if other['id'] != building['id'] and any(shape.intersection(Polygon(p[0], p[1:])).area > 1e-5 for p in other['polygons']):
                    raise ValueError('Attached gallery crosses another building')
                for entry in other.get('form', {}).get('entrances', []):
                    for kind in ('attachedPortico', 'stairFlight'):
                        if kind in entry and shape.intersection(Polygon(entry[kind]['footprint'])).area > 1e-5:
                            raise ValueError('Attached gallery crosses an entrance')
            if any(shape.intersection(other).area > 1e-5 for other in occupied):
                raise ValueError('Attached galleries overlap')
            occupied.append(shape)
