"""A wide lower flight, terrace and offset narrow upper flight on one facade.

This describes the photographed exterior circulation, without inferring a new
door or altering the mapped building footprint. Dimensions need field evidence.
"""
import copy
import math
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union


def resolve_terraced_stairs(building, form, config):
    from building_overrides import anchor
    fields = {'polygon','ring','edge','t','width','baseHeight','intermediateHeight','landingHeight',
              'lowerRisers','upperRisers','tread','landingDepth','intermediateDepth','upperWidth','upperOffset'}
    if not isinstance(config, dict) or set(config) != fields:
        raise ValueError('Terraced stairs need a facade anchor and complete two-flight dimensions')
    if 'stairTower' in form:
        raise ValueError('Terraced stairs require a solid building support')
    a, b, normal, length = anchor(building, config, exterior=True)
    for key in fields - {'polygon','ring','edge','lowerRisers','upperRisers'}:
        if type(config[key]) not in (int, float) or not math.isfinite(config[key]):
            raise ValueError('Terraced stair dimensions must be finite numbers')
    for key in ('lowerRisers', 'upperRisers'):
        if type(config[key]) is not int or not 3 <= config[key] <= 16:
            raise ValueError('Each terraced stair flight requires 3–16 risers')
    c = config
    if not 0 < c['t'] < 1 or not 3 <= c['width'] <= 16 or c['width']/2 > min(c['t'],1-c['t'])*length:
        raise ValueError('Terraced stairs must fit within their facade')
    if not 1.2 <= c['upperWidth'] <= c['width']-1 or abs(c['upperOffset'])+c['upperWidth']/2 > c['width']/2-.2:
        raise ValueError('Upper stairs must fit on the lower terrace with side clearance')
    if (not .25 <= c['tread'] <= .4 or not .8 <= c['landingDepth'] <= 3 or
            not 1 <= c['intermediateDepth'] <= 3 or not 0 <= c['baseHeight'] <= 1 or
            not c['baseHeight'] < c['intermediateHeight'] < c['landingHeight'] <= 4.5):
        raise ValueError('Terraced stair heights and landings are outside supported bounds')
    rises = [(c['intermediateHeight']-c['baseHeight'])/c['lowerRisers'],
             (c['landingHeight']-c['intermediateHeight'])/c['upperRisers']]
    if any(not .12-1e-9 <= value <= .2+1e-9 for value in rises):
        raise ValueError('Terraced stair rises must be 0.12–0.20 m')
    tangent = [(b[k]-a[k])/length for k in (0,1)]
    center = [a[k]+(b[k]-a[k])*c['t'] for k in (0,1)]
    point = lambda u,v: [center[k]+tangent[k]*u+normal[k]*v for k in (0,1)]
    upper_front = c['landingDepth']+(c['upperRisers']-1)*c['tread']
    terrace_front = upper_front+c['intermediateDepth']
    front = terrace_front+(c['lowerRisers']-1)*c['tread']
    line = LineString([point(-c['width']/2,0),point(c['width']/2,0)])
    envelope = Polygon([point(-c['width']/2,0),point(c['width']/2,0),
                        point(c['width']/2,front),point(-c['width']/2,front)])
    body = unary_union([Polygon(p[0],p[1:]) for p in building['polygons']])
    if not body.boundary.buffer(1e-6).covers(line) or envelope.intersection(body).area > 1e-5:
        raise ValueError('Terraced stairs must attach without entering the original footprint')
    parts = form['parts'] or [dict(id='body', polygons=building['polygons'], height=form['height'])]
    supports = [p for p in parts if unary_union([Polygon(r[0],r[1:]) for r in p['polygons']]).boundary.buffer(1e-6).covers(line)]
    if len(supports) != 1 or 'openBelow' in supports[0] or supports[0]['height'] < c['landingHeight']+2.6:
        raise ValueError('Terraced stairs need one solid supporting facade above the upper landing')
    return {**copy.deepcopy(c),'center':center,'tangent':tangent,'normal':list(normal),
            'part':supports[0]['id'],'upperFront':upper_front,'terraceFront':terrace_front,'front':front,
            'footprint':[list(p) for p in envelope.exterior.coords]}


def validate_terraced_stairs_context(buildings):
    stairs = [(b['id'], Polygon(b['form']['terracedStairs']['footprint'])) for b in buildings
              if 'terracedStairs' in b.get('form',{})]
    for owner, footprint in stairs:
        for other in buildings:
            if other['id'] != owner:
                shape = unary_union([Polygon(p[0],p[1:]) for p in other['polygons']])
                if footprint.intersection(shape).area > 1e-5:
                    raise ValueError(f'{owner}: terraced stairs intersect building {other["id"]}')
            for entry in other.get('form',{}).get('entrances',[]):
                for kind in ('attachedPortico','stairFlight'):
                    if kind in entry and footprint.intersection(Polygon(entry[kind]['footprint'])).area > 1e-5:
                        raise ValueError(f'{owner}: terraced stairs intersect an entrance platform')
            for facade in other.get('form',{}).get('facades',[]):
                if 'attachedGallery' in facade and footprint.intersection(Polygon(facade['attachedGallery']['footprint'])).area > 1e-5:
                    raise ValueError(f'{owner}: terraced stairs intersect an attached gallery')
        if any(owner != other and footprint.intersection(shape).area > 1e-5 for other, shape in stairs):
            raise ValueError(f'{owner}: terraced stairs overlap another stair terrace')
