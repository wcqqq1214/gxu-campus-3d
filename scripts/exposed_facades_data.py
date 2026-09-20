"""Explicit upper walls on a shared boundary between solid, unequal parts.

Anchors index the named part, never the mapped ground outline. Reuse the
ordinary facade validator on that part before admitting a shared step wall.
"""
import copy

from shapely.geometry import LineString, Polygon
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
        if not isinstance(config, dict) or set(config) != {'part', 'adjacentPart', 'polygon', 'ring', 'edge', 'rule'}:
            raise ValueError('Exposed facade needs two parts, a part-local anchor and a rule')
        if any(not isinstance(config[k], str) or config[k] not in parts for k in ('part', 'adjacentPart')):
            raise ValueError('Exposed facade references an unknown part')
        high, low = (parts[config[k]] for k in ('part', 'adjacentPart'))
        if (high['height'] <= low['height'] or any('openBelow' in p or p['roof']['type'] != 'flat' for p in (high, low))):
            raise ValueError('Exposed facade needs a higher solid part beside a lower flat-roofed solid part')
        local = {**building, 'polygons': high['polygons']}
        a, b, _, _ = anchor(local, config, exterior=True)
        key = (config['part'], config['polygon'], config['ring'], config['edge'])
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
        anchored = {**copy.deepcopy(rule), **{k: config[k] for k in ('polygon', 'ring', 'edge')}}
        local_form = {'parts': [], 'height': high['height'], 'levels': high['levels'], 'roof': high['roof']}
        validated = resolve_facades(local, local_form, [anchored])
        facade = next(f for f in validated if all(f[k] == config[k] for k in ('polygon', 'ring', 'edge')))
        # Generic flat roofs include an 0.8 m parapet. Explicit details cannot
        # occupy either the lower body or its parapet; nothing is silently cut.
        minimum = low['height'] + .8
        fh = high['height']/high['levels']
        band = rule.get('windowBands')
        if band and (band['firstLevel']+.56-band['heightRatio']/2)*fh-.06 < minimum:
            raise ValueError('Exposed window band intersects the lower roof or parapet')
        if any(p['bottom']-p['frameWidth']/2 < minimum for p in rule.get('panels', [])):
            raise ValueError('Exposed panel intersects the lower roof or parapet')
        corridor = rule.get('openCorridor')
        if corridor:
            if corridor['firstLevel']*fh-.18 < minimum:
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
        result.append(facade)
    return result
