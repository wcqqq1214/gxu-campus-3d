"""An evidenced corner curtain crown and tapered screen, supported by a flat roof."""
import copy
import math
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union


def resolve_roof_crown(building, form, config):
    fields = {'part', 'polygon', 'vertex', 'width', 'depth', 'rise', 'glassBottom',
              'glassTop', 'frontEnd', 'sideEnd', 'columns', 'sideColumns', 'rows',
              'screenRise', 'screenBottomDepth', 'screenTopDepth', 'screenThickness'}
    if not isinstance(config, dict) or not fields <= set(config) or set(config)-fields-{'sideWall'}:
        raise ValueError('Roof crown needs complete corner, glazing and screen dimensions')
    if any(k in form for k in ('stairTower', 'roofDome', 'roofEave')):
        raise ValueError('Roof crown conflicts with another roof feature')
    for key in ('polygon', 'vertex', 'columns', 'sideColumns', 'rows'):
        if type(config[key]) is not int or config[key] < 0:
            raise ValueError('Roof crown indices/counts must be nonnegative integers')
    for key in fields - {'part', 'polygon', 'vertex', 'columns', 'sideColumns', 'rows'}:
        if type(config[key]) not in (int, float) or not math.isfinite(config[key]):
            raise ValueError('Roof crown dimensions must be finite numbers')
    parts = form['parts'] or [dict(id='body', polygons=building['polygons'], height=form['height'], roof=form['roof'])]
    matches = [p for p in parts if p['id'] == config['part']]
    if len(matches) != 1 or matches[0]['roof']['type'] != 'flat' or 'openBelow' in matches[0]:
        raise ValueError('Roof crown needs one solid flat support part')
    part = matches[0]; c = config
    try:
        ring = building['polygons'][c['polygon']][0][:-1]
        a = ring[c['vertex']]; following = ring[(c['vertex']+1) % len(ring)]; previous = ring[(c['vertex']-1) % len(ring)]
    except IndexError as error:
        raise ValueError('Roof crown corner does not exist') from error
    width_limit, depth_limit = math.dist(a, following), math.dist(a, previous)
    u = [(following[k]-a[k])/width_limit for k in (0, 1)]
    v = [(previous[k]-a[k])/depth_limit for k in (0, 1)]
    if abs(sum(u[k]*v[k] for k in (0, 1))) > .02:
        raise ValueError('Roof crown needs a nearly rectangular convex corner')
    if not 4 <= c['width'] <= min(25, width_limit) or not 2 <= c['depth'] <= min(8, depth_limit):
        raise ValueError('Roof crown body must fit its corner edges')
    if not 1 <= c['rise'] <= 9 or not c['rise']+.5 <= c['screenRise'] <= 12:
        raise ValueError('Roof crown and taller screen rises outside supported bounds')
    if not c['depth']+.5 <= c['screenTopDepth'] < c['screenBottomDepth'] <= min(15, depth_limit):
        raise ValueError('Roof screen must taper behind the glazed crown')
    if not .15 <= c['screenThickness'] <= .6:
        raise ValueError('Roof screen thickness outside supported bounds')
    if not part['height']-.6 <= c['glassBottom'] <= part['height'] or not part['height'] < c['glassTop'] <= part['height']+c['rise']-.1:
        raise ValueError('Roof crown glazing must join the roof and fit its raised body')
    if not 1 <= c['frontEnd'] <= c['width']-.1 or not 1 <= c['sideEnd'] <= c['depth']-.1+1e-8:
        raise ValueError('Roof crown glazing must leave solid edge returns')
    if any(not 1 <= c[k] <= 16 for k in ('columns', 'sideColumns', 'rows')):
        raise ValueError('Roof crown glazing counts outside supported bounds')
    if min((c['frontEnd']-.24)/c['columns'], (c['sideEnd']-.24)/c['sideColumns'],
           (c['glassTop']-c['glassBottom']-.14)/c['rows']) < .28:
        raise ValueError('Roof crown glazing cells too small')
    point = lambda s, t: [a[k]+u[k]*s+v[k]*t for k in (0, 1)]
    footprint = Polygon([point(0,0), point(c['width'],0), point(c['width'],c['depth']),
                         point(c['screenThickness'],c['depth']),
                         point(c['screenThickness'],c['screenBottomDepth']), point(0,c['screenBottomDepth'])])
    support = unary_union([Polygon(p[0],p[1:]) for p in part['polygons']])
    if not support.buffer(1e-7).covers(footprint):
        raise ValueError('Roof crown leaves its support or enters a courtyard')
    side_wall = None
    if 'sideWall' in c:
        sw = c['sideWall']
        if not isinstance(sw, dict) or set(sw) != {'baseHeight', 'projection'}:
            raise ValueError('Side wall needs base height and outward projection')
        if any(type(value) not in (int, float) or not math.isfinite(value) for value in sw.values()):
            raise ValueError('Side wall dimensions must be finite numbers')
        if not -.5 <= sw['baseHeight'] <= part['height']-1 or not .02 <= sw['projection'] <= min(.12,c['screenThickness']/2):
            raise ValueError('Side wall base/projection outside supported bounds')
        slope = (c['screenBottomDepth']-c['screenTopDepth'])/c['screenRise']
        bottom_depth = c['screenBottomDepth']+(part['height']-sw['baseHeight'])*slope
        if bottom_depth > min(depth_limit,18):
            raise ValueError('Extended side wall exceeds its corner edge')
        backing = Polygon([point(0,c['depth']),point(c['screenThickness'],c['depth']),
                           point(c['screenThickness'],bottom_depth),point(0,bottom_depth)])
        line = LineString([point(0,c['depth']),point(0,bottom_depth)])
        if not support.buffer(1e-7).covers(backing) or not support.boundary.buffer(1e-7).covers(line):
            raise ValueError('Extended side wall must follow one complete solid facade')
        side_wall = {**copy.deepcopy(sw), 'bottomDepth':bottom_depth}
    # Delete only the portions of the old roof parapet under the new body/screen.
    edges = part.get('parapetEdges', [(p,q) for poly in part['polygons'] for r in poly for p,q in zip(r,r[1:])])
    retained = []
    for p,q in edges:
        line = LineString([p,q]).difference(footprint.buffer(1e-7))
        pieces = [line] if line.geom_type == 'LineString' else list(getattr(line, 'geoms', []))
        retained.extend([list(s.coords[0]), list(s.coords[-1])] for s in pieces if s.geom_type == 'LineString' and s.length > .01)
    result = {**copy.deepcopy(c), 'corner':list(a), 'u':u, 'v':v, 'baseHeight':part['height'],
              'footprint':[list(p) for p in footprint.exterior.coords], 'retainedParapetEdges':retained}
    if side_wall is not None:
        result['sideWall'] = side_wall
    return result
