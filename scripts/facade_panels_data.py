"""Bounded, attributed upper-facade glazing and decorative screens."""
import math


def overlaps(a, b):
    return a[0] < b[1] and a[1] > b[0] and a[2] < b[3] and a[3] > b[2]


def validate_panels(panels, length, height, levels, band=None, ledges=None):
    if not isinstance(panels, list) or not 1 <= len(panels) <= 32:
        raise ValueError('Facade panels require 1–32 explicit rectangles')
    fields = {'id', 'type', 'from', 'to', 'bottom', 'top', 'columns', 'rows', 'frameWidth', 'depth'}
    ids = set(); rectangles = []
    for p in panels:
        expected = fields | ({'openings'} if isinstance(p, dict) and p.get('type') == 'round-window-wall' else set())
        if not isinstance(p, dict) or set(p) != expected:
            raise ValueError('Facade panel needs explicit bounds, type and frame dimensions')
        if not isinstance(p['id'], str) or not p['id'].strip() or p['id'] in ids:
            raise ValueError('Facade panel IDs must be nonempty and unique within the facade')
        ids.add(p['id'])
        if p['type'] not in ('glazing', 'lattice', 'solid', 'round-window-wall'):
            raise ValueError('Unknown facade panel type')
        for k in ('from', 'to', 'bottom', 'top', 'frameWidth', 'depth'):
            if type(p[k]) not in (int, float) or not math.isfinite(p[k]):
                raise ValueError('Facade panel dimensions must be finite numbers')
        for k in ('columns', 'rows'):
            if type(p[k]) is not int or not 1 <= p[k] <= 16:
                raise ValueError('Facade panel cell counts must be integers from 1 to 16')
        if p['type'] in ('solid', 'round-window-wall') and (p['columns']!=1 or p['rows']!=1):
            raise ValueError('Solid panels cannot define glazing or lattice cells')
        # This first contract intentionally covers upper solid walls. Ground
        # doors, porticos and open corridors need their existing dedicated rules.
        if not 0 < p['from'] < p['to'] < 1 or not 3.2 <= p['bottom'] < p['top'] <= height-.1:
            raise ValueError('Facade panel must fit inside an upper solid facade')
        if not .04 <= p['frameWidth'] <= .2 or not .06 <= p['depth'] <= .25:
            raise ValueError('Facade panel frame/depth outside supported bounds')
        w = (p['to']-p['from'])*length; h = p['top']-p['bottom']; fw = p['frameWidth']
        if min((w-2*fw)/p['columns'], (h-2*fw)/p['rows']) < max(.2, 4*fw):
            raise ValueError('Facade panel leaves insufficient clear cells')
        if p['type'] == 'round-window-wall':
            validate_round_openings(p, w)
        rectangle = (p['from']*length, p['to']*length, p['bottom'], p['top'])
        if any(overlaps(rectangle, other) for other in rectangles):
            raise ValueError('Facade panels overlap')
        rectangles.append(rectangle)
        if ledges:
            for top in ledges['tops']:
                if overlaps(rectangle, (ledges['from']*length, ledges['to']*length, top-ledges['thickness'], top)):
                    raise ValueError('Facade panel overlaps a horizontal ledge')
        if band:
            fh = height/levels
            for level in range(band['firstLevel'], band.get('lastLevel', int(levels)-1)+1):
                # Include the near frame and upper projecting ledge.
                low = (level+.56-band['heightRatio']/2)*fh-.06
                high = (level+.56+band['heightRatio']/2)*fh+.12+band['thickness']
                if overlaps(rectangle, (band['from']*length-.06, band['to']*length+.06, low, high)):
                    raise ValueError('Facade panel overlaps a window band or ledge')


def validate_round_openings(panel, width):
    openings = panel['openings']; clearance = panel['frameWidth']; circles = []
    if not isinstance(openings, list) or not 1 <= len(openings) <= 16:
        raise ValueError('Round window wall requires 1–16 openings')
    for opening in openings:
        if not isinstance(opening, dict) or set(opening) != {'t', 'height', 'radius'}:
            raise ValueError('Round opening requires position, height and radius')
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in opening.values()):
            raise ValueError('Round opening dimensions must be finite numbers')
        x, y, r = opening['t']*width, opening['height'], opening['radius']
        if not .15 <= r <= 2 or not r+clearance <= x <= width-r-clearance or not panel['bottom']+r+clearance <= y <= panel['top']-r-clearance:
            raise ValueError('Round opening must fit inside its wall with frame clearance')
        if any(math.hypot(x-a, y-b) < r+c+clearance for a,b,c in circles):
            raise ValueError('Round openings overlap or leave insufficient wall')
        circles.append((x,y,r))


def resolve_round_window_walls(panels, length):
    """Triangulate white wall minus circular apertures; keep input rules intact.

    Coordinates are metres along the panel and above its bottom. Each circle
    uses 32 edges at both LODs; this is shallow exterior glazing, not an interior.
    """
    import numpy as np
    import mapbox_earcut as earcut
    result = {}
    for p in panels:
        if p['type'] != 'round-window-wall':
            continue
        w = (p['to']-p['from'])*length; h = p['top']-p['bottom']
        rings = [[[0,0],[w,0],[w,h],[0,h]]]
        for opening in p['openings']:
            x, y, r = opening['t']*w, opening['height']-p['bottom'], opening['radius']
            rings.append([[x+r*math.cos(-i*math.tau/32), y+r*math.sin(-i*math.tau/32)] for i in range(32)])
        xy = [v for ring in rings for v in ring]
        triangles = earcut.triangulate_float64(np.asarray(xy), np.cumsum([len(r) for r in rings], dtype=np.uint32)).tolist()
        result[p['id']] = {'rings': rings, 'triangles': triangles}
    return result
