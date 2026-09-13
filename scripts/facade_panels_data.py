"""Bounded, attributed upper-facade glazing and decorative screens."""
import math


def overlaps(a, b):
    return a[0] < b[1] and a[1] > b[0] and a[2] < b[3] and a[3] > b[2]


def validate_panels(panels, length, height, levels, band=None):
    if not isinstance(panels, list) or not 1 <= len(panels) <= 32:
        raise ValueError('Facade panels require 1–32 explicit rectangles')
    fields = {'id', 'type', 'from', 'to', 'bottom', 'top', 'columns', 'rows', 'frameWidth', 'depth'}
    ids = set(); rectangles = []
    for p in panels:
        if not isinstance(p, dict) or set(p) != fields:
            raise ValueError('Facade panel needs explicit bounds, type and frame dimensions')
        if not isinstance(p['id'], str) or not p['id'].strip() or p['id'] in ids:
            raise ValueError('Facade panel IDs must be nonempty and unique within the facade')
        ids.add(p['id'])
        if p['type'] not in ('glazing', 'lattice'):
            raise ValueError('Unknown facade panel type')
        for k in ('from', 'to', 'bottom', 'top', 'frameWidth', 'depth'):
            if type(p[k]) not in (int, float) or not math.isfinite(p[k]):
                raise ValueError('Facade panel dimensions must be finite numbers')
        for k in ('columns', 'rows'):
            if type(p[k]) is not int or not 1 <= p[k] <= 16:
                raise ValueError('Facade panel cell counts must be integers from 1 to 16')
        # This first contract intentionally covers upper solid walls. Ground
        # doors, porticos and open corridors need their existing dedicated rules.
        if not 0 < p['from'] < p['to'] < 1 or not 3.2 <= p['bottom'] < p['top'] <= height-.1:
            raise ValueError('Facade panel must fit inside an upper solid facade')
        if not .04 <= p['frameWidth'] <= .2 or not .06 <= p['depth'] <= .25:
            raise ValueError('Facade panel frame/depth outside supported bounds')
        w = (p['to']-p['from'])*length; h = p['top']-p['bottom']; fw = p['frameWidth']
        if min((w-2*fw)/p['columns'], (h-2*fw)/p['rows']) < max(.2, 4*fw):
            raise ValueError('Facade panel leaves insufficient clear cells')
        rectangle = (p['from']*length, p['to']*length, p['bottom'], p['top'])
        if any(overlaps(rectangle, other) for other in rectangles):
            raise ValueError('Facade panels overlap')
        rectangles.append(rectangle)
        if band:
            fh = height/levels
            for level in range(band['firstLevel'], int(levels)):
                # Include the near frame and upper projecting ledge.
                low = (level+.56-band['heightRatio']/2)*fh-.06
                high = (level+.56+band['heightRatio']/2)*fh+.12+band['thickness']
                if overlaps(rectangle, (band['from']*length-.06, band['to']*length+.06, low, high)):
                    raise ValueError('Facade panel overlaps a window band or ledge')

