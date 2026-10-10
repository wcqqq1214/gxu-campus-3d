"""Resolve roof-edge posts and beams with support and solid-intersection checks."""
import copy
import math
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union


def resolve_roof_edge_frames(building, form, config):
    from building_overrides import anchor
    if not isinstance(config, list) or not 1 <= len(config) <= 8:
        raise ValueError('Roof edge frames require 1–8 explicit frames')
    if any(k in form for k in ('stairTower', 'roofDome', 'roofEave', 'roofCrown', 'gableScreen')):
        raise ValueError('Roof edge frames cannot combine with another roof feature')
    parts = form['parts'] or [dict(id='body', polygons=building['polygons'],
                                  height=form['height'], roof=form['roof'])]
    fields = {'id', 'part', 'polygon', 'edge', 'from', 'to', 'inset', 'rise',
              'beamHeight', 'beamDepth', 'postWidth', 'postDepth', 'postCount'}
    numeric = fields-{'id', 'part', 'polygon', 'edge', 'postCount'}
    solids = []
    for volume in form.get('roofVolumes', []):
        shape = Polygon(volume['footprint']); base = volume['baseHeight']
        solids.append((shape, base, base+volume['rise']))
        if 'cap' in volume:
            cap = volume['cap']
            solids.append((shape.buffer(cap['overhang'], join_style=2),
                           base+volume['rise'], base+volume['rise']+cap['height']))
        if 'glazing' in volume:
            g = volume['glazing']
            # Conservative all-face envelope includes projecting window frames.
            solids.append((shape.buffer(g['projection'], join_style=2),
                           base+g['sill'], base+g['sill']+g['height']))
    result = []; ids = set()
    for c in config:
        if not isinstance(c, dict) or set(c) != fields:
            raise ValueError('Roof edge frame requires explicit identity, anchor and dimensions')
        if not isinstance(c['id'], str) or not c['id'].strip() or c['id'] in ids:
            raise ValueError('Roof edge frame IDs must be nonempty and unique')
        ids.add(c['id'])
        if (not isinstance(c['part'], str)
                or any(type(c[k]) is not int or c[k] < 0 for k in ('polygon', 'edge'))
                or type(c['postCount']) is not int or not 2 <= c['postCount'] <= 40):
            raise ValueError('Roof edge frame support, indices or post count invalid')
        if any(type(c[k]) not in (int, float) or not math.isfinite(c[k]) for k in numeric):
            raise ValueError('Roof edge frame dimensions must be finite numbers')
        if (not 0 <= c['from'] < c['to'] <= 1 or not .3 <= c['inset'] <= 20
                or not .8 <= c['rise'] <= 6 or not .15 <= c['beamHeight'] <= 1
                or c['beamHeight'] >= c['rise']-.3 or not .2 <= c['beamDepth'] <= 2
                or not .15 <= c['postWidth'] <= 1 or not .15 <= c['postDepth'] <= 1
                or c['postDepth'] > c['beamDepth']):
            raise ValueError('Roof edge frame dimensions outside supported bounds')
        support_parts = [p for p in parts if p['id'] == c['part']]
        if (len(support_parts) != 1 or support_parts[0]['roof']['type'] != 'flat'
                or 'inset' in support_parts[0]['roof'] or 'openBelow' in support_parts[0]):
            raise ValueError('Roof edge frame needs one solid flat support part')
        part = support_parts[0]
        a, b, normal, length = anchor(building, {'polygon':c['polygon'], 'ring':0, 'edge':c['edge']})
        u = [(b[k]-a[k])/length for k in (0, 1)]
        span = (c['to']-c['from'])*length
        if span/(c['postCount']-1) <= c['postWidth']+.1:
            raise ValueError('Roof edge frame posts leave no clear gap')
        def point(t, d):
            return [a[k]+u[k]*t*length-normal[k]*d for k in (0, 1)]
        def rectangle(center, width, depth):
            return Polygon([[center[k]+u[k]*dx+normal[k]*dy for k in (0, 1)]
                            for dx, dy in [(-width/2,-depth/2), (width/2,-depth/2),
                                           (width/2,depth/2), (-width/2,depth/2)]])
        center = point((c['from']+c['to'])/2, c['inset'])
        posts = [point(c['from']+(c['to']-c['from'])*i/(c['postCount']-1), c['inset'])
                 for i in range(c['postCount'])]
        base = part['height']; underside = base+c['rise']-c['beamHeight']
        beam = rectangle(center, span+c['postWidth'], c['beamDepth'])
        new_solids = [(beam, underside, base+c['rise'])]
        new_solids += [(rectangle(p,c['postWidth'],c['postDepth']),base,underside) for p in posts]
        support = unary_union([Polygon(p[0],p[1:]) for p in part['polygons']])
        if not support.boundary.buffer(1e-7).covers(LineString([point(c['from'],0),point(c['to'],0)])):
            raise ValueError('Roof edge frame anchor must lie on support boundary')
        if any(not support.buffer(-.1).buffer(1e-7).covers(shape) for shape, _, _ in new_solids):
            raise ValueError('Roof edge frame needs clearance from roof edges and courtyards')
        for shape, bottom, top in new_solids:
            for old, old_bottom, old_top in solids:
                if min(top, old_top)-max(bottom, old_bottom) > 1e-7 and shape.intersection(old).area > 1e-7:
                    raise ValueError('Roof edge frame intersects another roof solid')
        solids.extend(new_solids)
        result.append({**copy.deepcopy(c), 'center':center, 'width':span+c['postWidth'],
                       'angle':math.atan2(u[1],u[0]), 'baseHeight':base, 'posts':posts,
                       'footprint':[list(p) for p in beam.exterior.coords]})
    return result
