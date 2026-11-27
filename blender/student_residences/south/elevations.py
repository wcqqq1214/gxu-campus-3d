"""Public elevations of the eight West Campus South apartments (campus metres)."""

import math

from geometry import material

from .panels import Plate

# Long-elevation balcony bays as (fraction from west, width in metres).
# The westernmost north balcony of South 2 is laid out with the primary facade.
BAYS = {
    (1, 'S'): [(0.07, 4.1), (0.35, 5.6), (0.64, 5.6), (0.93, 4.1)],
    (2, 'N'): [(0.32, 4.45), (0.56, 4.65), (0.78, 4.1), (0.945, 3.65)],
    (2, 'S'): [(0.06, 4.65), (0.49, 7.10), (0.94, 4.65)],
    (3, 'N'): [(0.10, 3.45), (0.38, 4.25), (0.67, 4.25), (0.91, 3.45)],
    (4, 'N'): [(0.17, 3.6), (0.48, 4.8), (0.78, 3.7)],
    (5, 'N'): [(0.14, 3.65), (0.43, 4.10), (0.70, 4.1), (0.91, 3.2)],
    (7, 'N'): [(0.16, 3.25), (0.50, 3.8), (0.83, 3.25)],
    (7, 'S'): [(0.085, 3.25), (0.50, 4.85), (0.915, 3.25)],
    (9, 'S'): [(0.16, 3.2), (0.83, 3.2)],
    (9, 'W'): [(0.82, 3.1)],
    (9, 'E'): [(0.83, 3.1)],
    (10, 'N'): [(0.19, 3.05), (0.84, 3.05)],
}
# Individual short-wall groups. Fractions on BOTH end walls run from south to north.
# Columns supplied as (location, whole masonry opening width, height, pane arrangement).
ENDS = {
    (1, 'W'): [],  # Paired west-end lights belong to the primary facade.
    (1, 'E'): [(0.49, 1.56, 1.36, 'pair'), (0.84, 1.14, 1.65, 'single')],
    (2, 'W'): [],
    (2, 'E'): [(0.78, 2.08, 0.82, 'slot')],
    (3, 'W'): [(0.71, 1.37, 1.26, 'pair')],
    (3, 'E'): [(0.75, 1.39, 1.33, 'pair')],
    (4, 'W'): [(0.79, 1.80, 0.84, 'slot')],
    (4, 'E'): [(0.53, 1.11, 1.48, 'single'), (0.85, 2.0, 0.83, 'slot')],
    (5, 'W'): [],
    (5, 'E'): [],
    (7, 'W'): [(0.61, 1.32, 1.13, 'pair')],
    (7, 'E'): [(0.62, 1.48, 1.12, 'pair')],
    (9, 'W'): [(0.55, 0.87, 1.44, 'single')],
    (9, 'E'): [(0.52, 1.04, 1.44, 'single')],
    (10, 'W'): [(0.71, 1.27, 1.19, 'pair')],
    (10, 'E'): [(0.64, 1.51, 1.18, 'pair')],
    (9, 'notchN'): [(0.48, 1.26, 0.64, 'slot')],
    (9, 'notchE'): [],
    (9, 'notchW'): [],
}
# Slight forward masonry strips between balconies, independently visible on the north of 3/4/5.
NORTH_PIERS = {
    3: (0.24, 0.54, 0.80),
    4: (0.045, 0.33, 0.65, 0.94),
    5: (0.29, 0.565, 0.825),
    7: (0.32, 0.68),
}


def palette(C, number):
    def finish(key, rgb):
        name = 'southExterior_' + key
        if name not in C:
            C[name] = material(name, rgb, 0.84)
        return C[name]

    return dict(
        wall=C['southDorm_sand' if number in (3, 5, 10) else 'southDorm_buff'],
        base=finish('mineralBase', (0.315, 0.287, 0.248)),
        joint=finish('renderJoint', (0.337, 0.286, 0.228)),
        wash=finish('lowerWarmRender', (0.435, 0.348, 0.269)),
        soffit=C['southDorm_cream'],
        cap=C['southDorm_concrete'],
        frame=finish('matteFrame', (0.48, 0.47, 0.414)),
        glass=C['southDorm_glass'],
    )


class Wall:
    def __init__(self, a, b, side, datum, palette, mesh):
        ax = 0 if side in 'NS' else 1
        if a[ax] > b[ax]:
            a, b = b, a
        self.a = a
        dx, dy = b[0] - a[0], b[1] - a[1]
        self.length = math.hypot(dx, dy)
        self.tx, self.ty = dx / self.length, dy / self.length
        self.sign = 1 if side in 'ES' else -1
        self.nx, self.ny = self.sign * self.ty, -self.sign * self.tx
        self.z = datum
        self.p = palette
        self.m = mesh

    def coords(self, u, d, h):
        return (
            self.a[0] + u * self.tx + d * self.nx,
            self.a[1] + u * self.ty + d * self.ny,
            self.z + h,
        )

    def face(self, points, finish):
        points = points if self.sign == 1 else points[::-1]
        self.m.face([self.coords(*v) for v in points], self.p[finish])

    def rect(self, a, b, lo, hi, finish='wall', d=0):
        if b - a > 1e-7 and hi - lo > 1e-7:
            self.face([(a, d, lo), (b, d, lo), (b, d, hi), (a, d, hi)], finish)

    def aperture(self, a, b, lo, hi, kind, detail, d):
        # There is no wall face behind the opening. Four returns connect the opening
        # to its inset sash. Frames, panes and the middle pier partition one plane.
        back = d - (0.155 if kind == 'slot' else 0.13)
        outline = [(a, lo), (b, lo), (b, hi), (a, hi)]
        for i, (s, t) in enumerate(outline):
            u, v = outline[(i + 1) % 4]
            self.face(
                [(s, d, t), (u, d, v), (u, back, v), (s, back, t)],
                'cap' if i == 0 else 'soffit',
            )
        if not detail:
            if kind in ('slot', 'pair'):
                mid = (a + b) / 2
                half = 0.20 if kind == 'pair' else 0.16
                self.rect(a, mid - half, lo, hi, 'glass', back)
                self.rect(
                    mid - half,
                    mid + half,
                    lo,
                    hi,
                    'wall' if kind == 'pair' else 'frame',
                    back,
                )
                self.rect(mid + half, b, lo, hi, 'glass', back)
            else:
                self.rect(a, b, lo, hi, 'glass', back)
            return
        border = 0.057
        self.rect(a, b, lo, lo + border, 'frame', back)
        self.rect(a, b, hi - border, hi, 'frame', back)
        self.rect(a, a + border, lo + border, hi - border, 'frame', back)
        self.rect(b - border, b, lo + border, hi - border, 'frame', back)
        if kind in ('pair', 'slot') or b - a > 1.12:
            mid = (a + b) / 2
            post = 0.22 if kind == 'pair' else 0.17 if kind == 'slot' else 0.026
            self.rect(a + border, mid - post, lo + border, hi - border, 'glass', back)
            self.rect(
                mid - post,
                mid + post,
                lo + border,
                hi - border,
                'wall' if kind == 'pair' else 'frame',
                back,
            )
            self.rect(mid + post, b - border, lo + border, hi - border, 'glass', back)
        else:
            self.rect(a + border, b - border, lo + border, hi - border, 'glass', back)

    def section(self, a, b, bottom, top, opening, detail, d=0, first=False):
        # Thin, flush render joints divide floor lifts. The darker plinth is part of
        # the wall surface, so no coplanar strips sit behind the returns or balconies.
        start = bottom
        if first:
            self.rect(a, b, bottom, 0.48, 'base', d)
            start = 0.48
        joint = 0.032 if detail else 0.0
        if opening:
            center, width, lo, hi, kind = opening
            l, r = center - width / 2, center + width / 2
            self.rect(a, b, start, lo, 'wall', d)
            self.rect(a, l, lo, hi, 'wall', d)
            self.rect(r, b, lo, hi, 'wall', d)
            self.aperture(l, r, lo, hi, kind, detail, d)
            start = hi
        self.rect(a, b, start, top - joint, 'wall', d)
        self.rect(a, b, top - joint, top, 'joint', d)

    def ledge(self, l, r, depth, h, thick):
        # Cantilever attached at depth zero; the concealed rear face is omitted.
        self.face([(l, 0, h), (r, 0, h), (r, depth, h), (l, depth, h)], 'soffit')
        self.face(
            [
                (l, depth, h + thick),
                (r, depth, h + thick),
                (r, 0, h + thick),
                (l, 0, h + thick),
            ],
            'cap',
        )
        self.rect(l, r, h, h + thick, 'cap', depth)
        self.face(
            [(l, 0, h), (l, depth, h), (l, depth, h + thick), (l, 0, h + thick)], 'cap'
        )
        self.face(
            [(r, depth, h), (r, 0, h), (r, 0, h + thick), (r, depth, h + thick)], 'cap'
        )

    def railing(self, l, r, depth, h, open_front, detail, north_tip):
        # A U section. The small perforations run all the way through the front.
        thick = 0.14
        inner = depth - thick

        def rim(a, b, lo, hi):
            self.rect(a, b, lo, hi, 'wall', depth)
            self.face(
                [(b, inner, lo), (a, inner, lo), (a, inner, hi), (b, inner, hi)],
                'soffit',
            )

        top = h + 0.85
        for x, xi, reverse in [(l, l + thick, False), (r, r - thick, True)]:
            outside = [(x, 0, h), (x, depth, h), (x, depth, top), (x, 0, top)]
            inside = [(xi, inner, h), (xi, 0, h), (xi, 0, top), (xi, inner, top)]
            cap = [(x, 0, top), (x, inner, top), (xi, inner, top), (xi, 0, top)]
            for face, mat in [(outside, 'wall'), (inside, 'soffit'), (cap, 'cap')]:
                self.face(face[::-1] if reverse else face, mat)
        # Front regions facing the court and the balcony floor respectively.
        self.rect(l, l + thick, h, top, 'wall', depth)
        self.rect(r - thick, r, h, top, 'wall', depth)
        al, ar = l + thick, r - thick
        if open_front:
            low, high = h + 0.20, top - 0.13
            rim(al, ar, h, low)
            rim(al, ar, high, top)
            holes = max(3, round((ar - al) / (0.52 if detail else 1.65)))
            pitch = (ar - al) / holes
            for i in range(holes):
                start = al + i * pitch
                a, b = start + 0.22 * pitch, start + 0.78 * pitch
                rim(start, a, low, high)
                rim(b, start + pitch, low, high)
                hole = [(a, low), (b, low), (b, high), (a, high)]
                for k, (u, z0) in enumerate(hole):
                    v, z1 = hole[(k + 1) % 4]
                    self.face(
                        [
                            (u, depth, z0),
                            (v, depth, z1),
                            (v, inner, z1),
                            (u, inner, z0),
                        ],
                        'soffit',
                    )
        elif north_tip:
            # The end stack on South 9 is solid toward the north with three openings toward the south.
            def xyz(u, d, z):
                return self.coords(self.sign * u, d, z)

            plate = Plate(self.m, xyz, inner, depth, self.p['wall'], self.p['cap'])
            split = al + (ar - al) * 0.44
            plate.rectangle(*sorted((self.sign * split, self.sign * ar)), h, top)
            plate.perforated(
                *sorted((self.sign * al, self.sign * split)), h, top, 3, False
            )
        else:
            rim(al, ar, h, top)
        self.face(
            [(l, depth, top), (r, depth, top), (r, inner, top), (l, inner, top)], 'cap'
        )


def edge_side(a, c, bounds, number):
    x0, y0, x1, y1 = bounds
    if (
        number == 9
        and y1 - 5 < (a[1] + c[1]) / 2 < y1 - 0.5
        and min(a[0], c[0]) > x0 + 3
        and max(a[0], c[0]) < x1 - 3
    ):
        if abs(a[1] - c[1]) < 0.06:
            return 'notchN'
        return 'notchE' if a[0] < (x0 + x1) / 2 else 'notchW'
    for side, axis, v in [('W', 0, x0), ('E', 0, x1), ('S', 1, y0), ('N', 1, y1)]:
        if max(abs(a[axis] - v), abs(c[axis] - v)) < 0.06:
            return side
    return ''


def _blind_west_two(w, b):
    # The 92/98 degree west views show a darker apron, a low belt and floor seams.
    # Build the face as one extruded profile; the horizontal bevels meet edge to edge.
    height = b['height']
    fh = height / int(b['levels'])
    sections = [
        (-0.5, 0.032),
        (0.53, 0.032),
        (0.58, 0.0),
        (2.39, 0.0),
        (2.415, -0.014),
        (2.435, 0.0),
        (2.64, 0.0),
        (2.665, 0.028),
        (2.73, 0.028),
        (2.754, 0.0),
    ]
    materials = [
        'base',
        'cap',
        'wash',
        'joint',
        'joint',
        'wash',
        'soffit',
        'wash',
        'cap',
    ]
    for k in range(1, int(b['levels'])):
        h = k * fh
        sections.extend(
            [
                (h - 0.022, 0.0),
                (h - 0.007, -0.017),
                (h + 0.008, -0.017),
                (h + 0.023, 0.0),
            ]
        )
        materials.extend(['wall', 'joint', 'joint', 'soffit'])
    sections.append((height, 0.0))
    materials.append('wall')
    for ((lo, d0), (hi, d1)), mat in zip(zip(sections, sections[1:]), materials):
        w.face([(0, d0, lo), (w.length, d0, lo), (w.length, d1, hi), (0, d1, hi)], mat)
        # Return projecting profiles at the two corners, without overlapping the adjacent walls.
        if max(d0, d1) > 0.0:
            for u, rev in [(0, False), (w.length, True)]:
                poly = [(u, 0, lo), (u, d0, lo), (u, d1, hi), (u, 0, hi)]
                clean = []
                for pt in poly:
                    if not clean or clean[-1] != pt:
                        clean.append(pt)
                if clean[0] == clean[-1]:
                    clean.pop()
                w.face(clean[::-1] if rev else clean, mat)


def elevation(w, number, side, b, detail):
    if (number, side) == (2, 'W'):
        _blind_west_two(w, b)
        return
    length = w.length
    bays = [(f * length, width) for f, width in BAYS.get((number, side), ())]
    ends = ENDS.get((number, side))
    windows = [
        (f * length, width, height, kind, 0.0)
        for f, width, height, kind in (ends or ())
    ]
    segments = [(x - width / 2, x + width / 2) for x, width in bays]
    piers = NORTH_PIERS.get(number, ()) if side == 'N' else ()
    lower = 4.75 if (number, side) == (2, 'N') else 0.0
    if ends is None:
        for a, c in zip(
            [lower] + [r for l, r in segments], [l for l, r in segments] + [length]
        ):
            if c - a < 1.5:
                continue
            pilaster = [v * length for v in piers if a + 0.82 < v * length < c - 0.82]
            count = max(1, round((c - a) / 3.4))
            centers = pilaster or [
                a + (j + 0.5) * (c - a) / count for j in range(count)
            ]
            for x in centers:
                windows.append(
                    (
                        x,
                        min(1.42, (c - a) / count * 0.62),
                        1.58,
                        'single',
                        0.32 if pilaster else 0.0,
                    )
                )
    for x, width in bays:
        windows.append((x, min(2.0, width * 0.48), 1.66, 'single', 0.0))
    # Subdivide at the window groups so genuine masonry projections can return
    # into the main plane between openings rather than intersect the wall behind.
    cuts = {0.0, length}
    for x, width, wh, kind, proj in windows:
        margin = 0.28 if proj else 0.08
        cuts.update(
            [max(0.0, x - width / 2 - margin), min(length, x + width / 2 + margin)]
        )
    cuts = sorted(cuts)
    height = b['height']
    floor = height / int(b['levels'])
    for a, c in zip(cuts, cuts[1:]):
        aperture = next((v for v in windows if a <= v[0] < c), None)
        d = aperture[4] if aperture else 0.0
        if d:
            for u, rev in [(a, False), (c, True)]:
                pts = [(u, 0, -0.5), (u, d, -0.5), (u, d, height), (u, 0, height)]
                w.face(pts[::-1] if rev else pts, 'wall')
            w.face(
                [(a, d, height), (c, d, height), (c, 0, height), (a, 0, height)], 'cap'
            )
        for k in range(int(b['levels'])):
            base = k * floor
            opening = None
            if aperture:
                x, width, wh, kind, _ = aperture
                # Keep the existing separate entry mesh untouched and avoid placing
                # a ground-floor opening behind its portal.
                world = w.coords(x, 0, 0)
                blocked = not k and any(
                    math.dist(world[:2], e['center'])
                    < e.get('width', 2.2) * 0.5 + width * 0.5 + 0.40
                    for e in b.get('form', {}).get('entrances', [])
                    if 'center' in e
                )
                if not blocked:
                    center = base + floor * (0.61 if kind == 'slot' else 0.54)
                    opening = (x, width, center - wh / 2, center + wh / 2, kind)
            w.section(
                a, c, base if k else -0.5, base + floor, opening, detail, d, not k
            )
    for x, width in bays:
        depth = {
            1: 1.05,
            2: 1.11,
            3: 0.97,
            4: 1.03,
            5: 1.10,
            7: 0.98,
            9: 0.89,
            10: 0.96,
        }[number]
        l, r = x - width / 2, x + width / 2
        for k in range(1, int(b['levels'])):
            h = k * floor + 0.02
            w.ledge(l, r, depth, h, 0.15)
            w.railing(
                l,
                r,
                depth,
                h + 0.15,
                number in (1, 3, 4, 7),
                detail,
                number == 9 and side in ('E', 'W'),
            )
        w.ledge(l - 0.05, r + 0.05, depth + 0.08, height - 0.14, 0.14)
