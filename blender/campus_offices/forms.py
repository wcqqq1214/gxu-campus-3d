"""Retarget old facade segments after physical subdivision of their host volumes."""

import json
import math
from functools import lru_cache
from pathlib import Path

P = Path(__file__).resolve().parent


@lru_cache
def parts(name):
    return json.loads((P / name).read_text())


def graduate(b):
    fresh = parts('graduate-parts.json')
    form = b['form']
    facades = []

    def along(p):
        return (p[0] - 575.6) * (-0.718) + (p[1] + 518.72) * 0.696

    for f in form['facades']:
        if f['part'] != 'diagonal':
            facades.append(f)
            continue
        a, bp = f['start'], f['end']
        u, v = along(a), along(bp)
        cuts = [0.0, 1.0]
        if (u - 5.9) * (v - 5.9) < 0:
            cuts.insert(1, (5.9 - u) / (v - u))
        for lo, hi in zip(cuts, cuts[1:]):
            start = [x + (y - x) * lo for x, y in zip(a, bp)]
            end = [x + (y - x) * hi for x, y in zip(a, bp)]
            low = along([(x + y) / 2 for x, y in zip(start, end)]) > 5.9
            if low and f['edge'] == 11:
                continue
            # The short ends near the new open return belong to the low gallery.
            facades.append(
                {
                    **f,
                    'start': start,
                    'end': end,
                    'part': 'observed-gallery' if low else 'diagonal',
                    'height': 7.45 if low else 19.8,
                    'levels': 2 if low else 6,
                }
            )
    return {
        **b,
        'form': {
            **form,
            'parts': fresh + [p for p in form['parts'] if p['id'] != 'diagonal'],
            'facades': facades,
            'entrances': [],
        },
    }


def animal(b):
    form = b['form']
    fresh = parts('animal-parts.json')
    return {
        **b,
        'form': {
            **form,
            'parts': [p for p in form['parts'] if p['id'] != 'side-wings'] + fresh,
        },
    }


def civic_front(b):
    form = b['form']
    key = b['id'].split('/')[-1]
    if key == '759337787':
        return {
            **b,
            'form': {
                **form,
                'entrances': [],
                'parts': [{**p, 'wallFinish': 'Office rose'} for p in form['parts']],
            },
        }
    faces = []
    for f in form['facades']:
        if (f['part'], f['edge']) in {('east-ridge', 5), ('middle', 3)}:
            f = {**f, 'rule': {**f['rule'], 'windows': False}}
        faces.append(f)
    return {**b, 'form': {**form, 'facades': faces}}


def security(b):
    form = b['form']
    roof = form['roof']
    g = roof['geometry']
    # The book fixes the triangular vent and roof pitch on the short end.
    # Keep the original eave footprint and west hip. The nearer ridge ends sooner.
    verts = []
    for x, y, h in g['vertices']:
        if h > 0 and x > -336:
            x += 2.35
        if h == 0:
            # The published photograph shows a tiled lip beyond both wall planes.
            x += math.copysign(0.38, x + 337.72)
            y += math.copysign(0.38, y + 783.39)
        verts.append([x, y, h * 4.80 / roof['rise']])
    new_roof = {**roof, 'rise': 4.80, 'geometry': {**g, 'vertices': verts}}
    return {**b, 'form': {**form, 'roof': new_roof}}
