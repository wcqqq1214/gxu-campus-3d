"""Explicit shared step walls and glazing behind an open portico.

Anchors index the named part, never the mapped ground outline. Reuse the
ordinary facade validator on that part before admitting a shared step wall.
"""
import copy
import math

from shapely.geometry import LineString, Polygon, Point
from shapely.ops import unary_union


def resolve_exposed_facades(building, form, rules):
    from building_overrides import anchor, resolve_facades

    if not isinstance(rules, list) or not rules:
        raise ValueError('Exposed facades need a nonempty explicit list')
    if 'floorHeights' in form:
        raise ValueError('Exposed facades currently require equal storeys')
    parts = {p['id']: p for p in form['parts']}
    footprint = unary_union([Polygon(p[0], p[1:]) for p in building['polygons']])
    result, seen, recesses = [], set(), []
    # Include existing exterior recesses in corner-overlap validation.
    def recess_strip(facade):
        c = facade['rule']['openCorridor']
        a, b, n = facade['start'], facade['end'], facade['normal']
        length = LineString([a, b]).length
        u = [(b[k]-a[k])/length for k in (0, 1)]
        ends = [[p[k]+sign*u[k]*c['endInset'] for k in (0, 1)]
                for p, sign in ((a, 1), (b, -1))]
        return Polygon(ends + [[p[k]-n[k]*c['depth'] for k in (0, 1)] for p in reversed(ends)])
    for f in form.get('facades', []):
        if 'openCorridor' in f['rule']:
            recesses.append(recess_strip(f))
    for config in rules:
        required = {'part', 'adjacentPart', 'polygon', 'ring', 'edge', 'rule'}
        if not isinstance(config, dict) or not required <= set(config) or set(config)-required-{'region'}:
            raise ValueError('Exposed facade needs two parts, a part-local anchor and a rule')
        if any(not isinstance(config[k], str) or config[k] not in parts for k in ('part', 'adjacentPart')):
            raise ValueError('Exposed facade references an unknown part')
        under_portico = config.get('region') == 'under-portico'
        above_portico = config.get('region') == 'above-portico'
        if 'region' in config and not (under_portico or above_portico):
            raise ValueError('Unknown exposed facade region')
        high, low = (parts[config[k]] for k in ('part', 'adjacentPart'))
        if under_portico or above_portico:
            if ('openBelow' in high or 'openBelow' not in low or
                    ('slattedRoof' in low['openBelow'] and
                     not low['openBelow']['slattedRoof'].get('solidBays')) or
                    low['roof']['type'] != 'flat' or high['roof']['type'] not in ('flat','profiled')):
                raise ValueError('Under-portico glazing needs a solid wall beside an open flat slab')
        elif (high['height'] <= low['height'] or any('openBelow' in p or p['roof']['type'] != 'flat' for p in (high, low))):
            raise ValueError('Exposed facade needs a higher solid part beside a lower flat-roofed solid part')
        local = {**building, 'polygons': high['polygons']}
        a, b, _, _ = anchor(local, config, exterior=True)
        key = (config['part'], config['polygon'], config['ring'], config['edge'], config.get('region'))
        if key in seen:
            raise ValueError('Duplicate exposed facade')
        seen.add(key)
        line = LineString([a, b])
        lower = unary_union([Polygon(p[0], p[1:]) for p in low['polygons']])
        if not lower.boundary.buffer(1e-7).covers(line) or line.intersection(footprint.boundary).length > 1e-6:
            raise ValueError('Exposed facade must be a complete internal shared part edge')
        rule = config['rule']
        if (not isinstance(rule, dict) or not rule or
                set(rule)-{'windows', 'balconies', 'windowBands', 'panels', 'openCorridor'} or
                rule.get('balconies') is not False):
            raise ValueError('Exposed facade supports bounded windows, panels and recesses without balconies')
        if (under_portico or above_portico) and (set(rule) != {'windows', 'balconies', 'panels'} or
                              rule.get('windows') is not False or
                              not isinstance(rule['panels'], list) or
                              any(not isinstance(p, dict) or p.get('type') not in ('glazing', 'solid') for p in rule['panels'])):
            raise ValueError('Under-portico walls support only explicit glazing and solid panels, without automatic windows or doors')
        minimum = low['openBelow']['floorHeight']+.1 if under_portico else low['height']+.8
        if above_portico:
            # An open slab has no generic 0.8m parapet. Keep the explicit
            # upper wall separate from glazing underneath the same roof.
            minimum = low['height']+.1
            if low['roof'].get('rim'):
                raise ValueError('Above-portico panels require a roof without a projecting rim')
        anchored = {**copy.deepcopy(rule), **{k: config[k] for k in ('polygon', 'ring', 'edge')}}
        local_form = {'parts': [], 'height': high['height'], 'levels': high['levels'], 'roof': high['roof']}
        validated = resolve_facades(local, local_form, [anchored],
                                    panel_minimum_bottom=minimum if under_portico or above_portico else 3.2)
        facade = next(f for f in validated if all(f[k] == config[k] for k in ('polygon', 'ring', 'edge')))
        # Generic flat roofs include an 0.8 m parapet. Explicit details cannot
        # occupy either the lower body or its parapet; nothing is silently cut.
        if under_portico:
            maximum = low['openBelow']['clearHeight']-.1
            for panel in rule['panels']:
                if panel['top'] > maximum:
                    raise ValueError('Under-portico glazing intersects the slab underside')
                # Keep all frame depth within the porch and away from supports.
                n = facade['normal']; start, end = facade['start'], facade['end']
                points = [[start[k]+(end[k]-start[k])*t for k in (0,1)]
                          for t in (panel['from'], panel['to'])]
                strip = Polygon(points + [[p[k]+n[k]*(panel['depth']+.05) for k in (0,1)]
                                          for p in reversed(points)])
                if strip.difference(lower).area > 1e-6:
                    raise ValueError('Under-portico frame leaves the open slab footprint')
                for column in low['openBelow']['columns']:
                    radius = (column['width']/2 if column.get('shape') == 'cylinder'
                              else math.hypot(column['width'], column['depth'])/2)
                    spread=0
                    if 'base' in column and panel['bottom']<low['openBelow']['floorHeight']+column['base']['height']:
                        spread=column['base']['projection']+.03
                    if 'capital' in column and panel['top']>low['openBelow']['clearHeight']-column['capital']['height']:
                        spread=max(spread,column['capital']['projection'])
                    radius+=spread
                    if strip.distance(Point(column['center'])) < radius:
                        raise ValueError('Under-portico glazing overlaps a support column')
        fh = high['height']/high['levels']
        band = rule.get('windowBands')
        if band and (band['firstLevel']+.56-band['heightRatio']/2)*fh-.06 < minimum:
            raise ValueError('Exposed window band intersects the lower roof or parapet')
        if not under_portico and any(p['bottom']-p['frameWidth']/2 < minimum for p in rule.get('panels', [])):
            raise ValueError('Exposed panel intersects the lower roof or parapet')
        corridor = rule.get('openCorridor')
        if corridor:
            if corridor['firstLevel']*fh-corridor.get('firstSlabThickness', .18) < minimum:
                raise ValueError('Exposed recess intersects the lower roof or parapet')
            for opening in corridor.get('openings', []):
                if any(level*fh+opening.get('sill', 0)-.12 < minimum for level in opening['levels']):
                    raise ValueError('Exposed opening intersects the lower roof or parapet')
            strip = recess_strip(facade)
            if any(strip.intersection(other).area > 1e-5 for other in recesses):
                raise ValueError('Exposed recess overlaps another facade recess')
            recesses.append(strip)
        facade.update(polygon=None, ring=None, edge=None, part=high['id'],
                      adjacentPart=low['id'], partAnchor={k: config[k] for k in ('polygon', 'ring', 'edge')},
                      minimumHeight=minimum)
        if under_portico:
            facade.update(region='under-portico', maximumHeight=maximum)
        if above_portico:
            facade.update(region='above-portico', maximumHeight=high['height']-.1)
        result.append(facade)
    return result
