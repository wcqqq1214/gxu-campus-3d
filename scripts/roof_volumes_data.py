"""Bounded rectangular rooftop masses, anchored to retained exterior edges."""
import copy
import math
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union


def resolve_roof_volumes(building, form, config):
    from building_overrides import anchor
    if not isinstance(config, list) or not 1 <= len(config) <= 12:
        raise ValueError('Roof volumes require 1–12 explicit rectangles')
    # These combinations need intersection handling before being supported.
    if any(k in form for k in ('stairTower', 'roofDome', 'roofEave', 'roofCrown', 'gableScreen')):
        raise ValueError('Roof volumes cannot combine with another roof feature')
    parts = form['parts'] or [dict(id='body', polygons=building['polygons'],
                                  height=form['height'], roof=form['roof'])]
    fields = {'id', 'part', 'polygon', 'edge', 'from', 'to', 'inset', 'depth', 'rise'}
    ids = set(); footprints = []; result = []
    for c in config:
        if not isinstance(c, dict) or not fields <= set(c) or set(c)-fields-{'cap', 'glazing'}:
            raise ValueError('Roof volume needs identity, support, edge and dimensions')
        if not isinstance(c['id'], str) or not c['id'].strip() or c['id'] in ids:
            raise ValueError('Roof volume IDs must be nonempty and unique')
        ids.add(c['id'])
        if not isinstance(c['part'], str):
            raise ValueError('Roof volume support must name a part')
        for key in ('polygon', 'edge'):
            if type(c[key]) is not int or c[key] < 0:
                raise ValueError('Roof volume anchor indices must be nonnegative integers')
        for key in ('from', 'to', 'inset', 'depth', 'rise'):
            if type(c[key]) not in (int, float) or not math.isfinite(c[key]):
                raise ValueError('Roof volume dimensions must be finite numbers')
        if not 0 <= c['from'] < c['to'] <= 1 or not .5 <= c['inset'] <= 50:
            raise ValueError('Roof volume interval or inset outside supported bounds')
        if not .2 <= c['depth'] <= 30 or not .2 <= c['rise'] <= 6:
            raise ValueError('Roof volume depth or rise outside supported bounds')
        supports = [p for p in parts if p['id'] == c['part']]
        if len(supports) != 1 or supports[0]['roof']['type'] != 'flat' or 'openBelow' in supports[0]:
            raise ValueError('Roof volume needs one solid flat support part')
        part = supports[0]
        if 'inset' in part['roof']:
            raise ValueError('Roof volumes on an inset coloured roof need separate support handling')
        a, b, normal, length = anchor(building, {'polygon': c['polygon'], 'ring': 0, 'edge': c['edge']})
        width = (c['to']-c['from'])*length
        if width < .2:
            raise ValueError('Roof volume is too narrow')
        if 'glazing' in c:
            g = c['glazing']
            if not isinstance(g, dict) or set(g) != {'faces', 'sill', 'height', 'margin', 'frameWidth', 'projection'}:
                raise ValueError('Roof glazing needs explicit faces and band dimensions')
            if (not isinstance(g['faces'], dict) or not g['faces']
                    or set(g['faces'])-{'outer', 'inner', 'start', 'end'}
                    or any(type(n) is not int or not 1 <= n <= 24 for n in g['faces'].values())):
                raise ValueError('Roof glazing faces need bounded integer pane counts')
            if any(type(g[k]) not in (int, float) or not math.isfinite(g[k])
                   for k in ('sill', 'height', 'margin', 'frameWidth', 'projection')):
                raise ValueError('Roof glazing dimensions must be finite numbers')
            if (not .1 <= g['sill'] or not .3 <= g['height']
                    or g['sill']+g['height'] > c['rise']-.1
                    or not .1 <= g['margin'] <= 2 or not .04 <= g['frameWidth'] <= .4
                    or not .03 <= g['projection'] <= .3 or 2*g['frameWidth'] >= g['height']):
                raise ValueError('Roof glazing band exceeds bounded wall area')
            for face, count in g['faces'].items():
                span = (width if face in ('outer', 'inner') else c['depth'])-2*g['margin']
                if (span-g['frameWidth'])/count <= g['frameWidth']+.1:
                    raise ValueError('Roof glazing panes leave no clear opening')
        u = [(b[k]-a[k])/length for k in (0, 1)]
        def point(t, d):
            return [a[k]+u[k]*t*length-normal[k]*d for k in (0, 1)]
        shape = Polygon([point(c['from'], c['inset']), point(c['to'], c['inset']),
                         point(c['to'], c['inset']+c['depth']), point(c['from'], c['inset']+c['depth'])])
        cap_shape = None
        if 'cap' in c:
            cap = c['cap']
            if (not isinstance(cap, dict) or set(cap) != {'overhang', 'height'}
                    or any(type(v) not in (int, float) or not math.isfinite(v) for v in cap.values())
                    or not .05 <= cap['overhang'] <= 1 or not .1 <= cap['height'] <= 1):
                raise ValueError('Roof volume cap needs bounded overhang and height')
            cap_shape = shape.buffer(cap['overhang'], join_style=2)
        support = unary_union([Polygon(p[0], p[1:]) for p in part['polygons']])
        edge = LineString([point(c['from'], 0), point(c['to'], 0)])
        if not support.boundary.buffer(1e-7).covers(edge):
            raise ValueError('Roof volume anchor must lie on its support boundary')
        if not support.buffer(-.5).buffer(1e-7).covers(shape):
            raise ValueError('Roof volume needs 0.5 m clearance from roof edges and courtyards')
        if cap_shape is not None and not support.buffer(-.5).buffer(1e-7).covers(cap_shape):
            raise ValueError('Roof volume cap needs 0.5 m clearance from roof edges and courtyards')
        solids = [(shape, part['height'], c['rise'])]
        if cap_shape is not None:
            solids.append((cap_shape, part['height']+c['rise'], c['cap']['height']))
        if 'glazing' in c:
            g = c['glazing']
            # Conservatively reserve projecting frames on all four faces.
            solids.append((shape.buffer(g['projection'], join_style=2),
                           part['height']+g['sill'], g['height']))
        for current, bottom, rise in solids:
            for old, height, old_rise in footprints:
                vertical_overlap = min(height+old_rise, bottom+rise)-max(height, bottom)
                if vertical_overlap > 1e-7 and old.intersection(current).area > 1e-7:
                    raise ValueError('Roof volumes overlap')
        footprints.extend(solids)
        result.append({**copy.deepcopy(c), 'center':point((c['from']+c['to'])/2, c['inset']+c['depth']/2),
                       'width':width, 'angle':math.atan2(u[1],u[0]), 'baseHeight':part['height'],
                       'footprint':[list(p) for p in shape.exterior.coords]})
        if 'glazing' in c:
            result[-1]['outwardNormal'] = list(normal)
    return result
