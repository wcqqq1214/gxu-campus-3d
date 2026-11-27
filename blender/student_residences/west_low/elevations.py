import math

from geometry import MATERIALS, material

from .surface import Surface


def _direction(w):
    if abs(w.nx) > 0.96:
        return 'E' if w.nx > 0 else 'W'
    if abs(w.ny) > 0.96:
        return 'N' if w.ny > 0 else 'S'
    return ''


def finish_kind(n, w):
    side = _direction(w)
    if n == 1:
        if side == 'W' and w.length > 10:
            return 'one-west'
        if side == 'E' and w.length > 5:
            return 'one-east'
    if n == 6:
        if side == 'W' and w.length > 8:
            return 'round-west'
        if side == 'E' and 4 < w.length < 7:
            return 'annex-end'
    if 7 <= n <= 12 and side == 'N' and w.length > 16:
        return 'gallery-end'
    if 7 <= n <= 12 and side in ('W', 'E') and w.length > 9:
        return 'base'
    if n == 8 and side == 'S' and w.length > 50:
        return 'eight'
    if n in (13, 14):
        if side in ('E', 'W'):
            return 'brick-end'
        if (n == 13 and side == 'S') or (n == 14 and side == 'N'):
            return 'court'
        if n == 14 and side == 'S':
            return 'bays'
    if n == 15 and side in ('E', 'W'):
        return 'base'
    return None


def _shell(m, pts, wall, C, caps=(0, -1), bottom=True):
    """Closed slab/rail along a broken or curved front profile with no internal caps."""
    for a, b in zip(pts, pts[1:]):
        (u, d, inner, lo, hi), (v, e, inner2, lo2, hi2) = a, b
        m.face([(u, d, lo), (v, e, lo2), (v, e, hi2), (u, d, hi)], wall)
        m.face(
            [(v, inner2, lo2), (u, inner, lo), (u, inner, hi), (v, inner2, hi2)], wall
        )
        m.face(
            [(u, d, hi), (v, e, hi2), (v, inner2, hi2), (u, inner, hi)],
            C['dormStonePale'],
        )
        if bottom:
            m.face(
                [(u, inner, lo), (v, inner2, lo2), (v, e, lo2), (u, d, lo)],
                C['dormConcreteLight'],
            )
    for idx in caps:
        u, d, inner, lo, hi = pts[idx]
        vs = [(u, inner, lo), (u, d, lo), (u, d, hi), (u, inner, hi)]
        m.face(vs if idx == 0 else vs[::-1], wall)


def _round_end(m, zheight, levels, C, detail):
    # Public view from the west shows a narrow turn at the south half of
    # the end. Its mapped west edge stays the datum for the back of the recess.
    w = m.w
    L = w.length
    story = zheight / levels

    def along(frac):
        return frac if w.ty > 0 else 1 - frac

    curve = [
        (
            along(i / 24) * L,
            -0.18 + 1.48 * math.sqrt(max(0, 1 - ((i / 24 - 0.26) / 0.245) ** 2)),
        )
        for i in range(25)
    ]
    curve.sort()
    for level in range(levels):
        lo = level * story
        hi = lo + story
        color = C['dormRose'] if level < 2 else C['white']
        if level == 0:
            m.plinth(0, L, 0.37, C, detail, True)
        start = lo if level else 0.43
        opening = L * (0.77 if w.ty > 0 else 0.23)
        back = -0.47 if level else 0
        # Slim shaded recess behind the rounded tip, plus the solid side
        # return with the one narrow window evidenced on the opposite end.
        join = L * 0.54 if w.ty > 0 else L * 0.46
        left, right = (join, L) if w.ty > 0 else (0, join)
        mx, my = (0, join) if w.ty > 0 else (join, L)
        m.panel(mx, my, start, hi, C['dormRecess'] if level else color, back)
        m.window(
            left,
            right,
            start,
            hi,
            opening - 0.53,
            opening + 0.53,
            lo + 0.93,
            lo + 2.41,
            color,
            C,
            detail,
            back,
        )
        if not level:
            continue
        m.side(0, 0, back, lo, hi, color)
        m.side(L, back, 0, lo, hi, color)
        _shell(m, [(u, d, -0.53, lo + 0.014, lo + 0.17) for u, d in curve], color, C)
        _shell(
            m,
            [(u, d, d - 0.14, lo + 0.17, lo + 1.02) for u, d in curve],
            C['dormRose'] if level < 2 else C['white'],
            C,
            bottom=False,
        )
    _shell(
        m,
        [(u, d, -0.53, zheight - 0.12, zheight + 0.08) for u, d in curve],
        C['white'],
        C,
    )


def _brick_end(m, n, h, levels, C, detail):
    L = m.w.length
    story = h / levels
    # A narrow return opens towards the shared court. The two west ends
    # have opposite handedness. The east ends are solid in the public views.
    court_at_end = (m.w.ty > 0) == (n == 14)
    notch = min(1.78, L * 0.20) if _direction(m.w) == 'W' else 0
    a = notch if not court_at_end else 0
    b = L - notch if court_at_end else L
    warm = C['courtBrick']
    for i in range(levels):
        lo = i * story
        hi = lo + story
        start = lo if i else 0.96
        if not i:
            m.plinth(a, b, 0.90, C, detail, True, C['courtStone'])
        if notch:
            centers = [a + (b - a) * f for f in (0.12, 0.83)]
            left = a
            for u in centers:
                m.panel(left, u - 0.08, start, hi - 0.17, warm)
                m.side(u - 0.08, 0, 0.065, start, hi - 0.17, C['dormStonePale'])
                m.panel(u - 0.08, u + 0.08, start, hi - 0.17, C['dormStonePale'], 0.065)
                m.side(u + 0.08, 0.065, 0, start, hi - 0.17, C['dormStonePale'])
                left = u + 0.08
            m.panel(left, b, start, hi - 0.17, warm)
        else:
            for left, right, col in [
                (a, a + 0.16, C['dormStonePale']),
                (a + 0.16, b - 0.16, warm),
                (b - 0.16, b, C['dormStonePale']),
            ]:
                m.panel(left, right, start, hi - 0.17, col)
        m.panel(a, b, hi - 0.17, hi, C['white'])
        if notch:
            u, v = (b, L) if court_at_end else (0, a)
            m.panel(u, v, lo, hi, C['dormConcreteLight'], -0.87)
            m.side(b if court_at_end else a, 0, -0.87, lo, hi, warm)
            _shell(m, [(k, 0.025, -0.87, lo, lo + 0.16) for k in (u, v)], C['white'], C)
            m.panel(u, v, lo + 0.16, lo + 0.90, warm)
    # Existing broad overhang and roof cap belong to the previous model.


def _corridor(m, n, h, levels, C, detail):
    L = m.w.length
    story = h / levels
    # The public view along the court shows the slab ends, infilled
    # balcony fronts, then the shaded outer building wall behind.
    count = round(L / (3.65 if n == 13 else 3.85))
    inset = -0.90
    margin = 0.86
    for i in range(levels):
        base = i * story
        for j in range(count):
            a = L * j / count
            b = L * (j + 1) / count
            width = b - a
            m.window(
                a,
                b,
                base,
                base + story,
                a + 0.20 * width,
                b - 0.20 * width,
                base + 1.00,
                base + 2.61,
                C['dormRecess'],
                C,
                detail,
                inset,
            )
            if j > 0:
                u = a
                m.side(
                    u - 0.085,
                    0.07,
                    inset,
                    base + 0.19,
                    base + story,
                    C['dormBrickClay'],
                )
                m.side(
                    u + 0.085,
                    inset,
                    0.07,
                    base + 0.19,
                    base + story,
                    C['dormBrickClay'],
                )
                m.panel(
                    u - 0.085, u + 0.085, base + 0.19, base + story, C['dormRose'], 0.07
                )
            # Unequal masonry infill and an open portion along each bay are
            # visible on both sides of the court in the west oblique view.
            start = max(a, margin)
            end = min(b, L - margin)
            if n == 13 and i == 0 and j == count // 2:
                continue
            u = start + 0.08
            v = u + (end - start) * 0.63
            _shell(
                m,
                [(k, 0.11, -0.035, base + 0.16, base + 0.92) for k in (u, v)],
                C['dormBrickClay'],
                C,
                bottom=False,
            )
            m.panel(start, end, base + 0.97, base + 1.03, C['metal'], 0.11)
            if detail:
                for x in (start + 0.035, end - 0.035):
                    m.panel(
                        x - 0.024, x + 0.024, base + 0.16, base + 0.97, C['metal'], 0.11
                    )
        # Long slabs meet the side-return slab at the west end. The grade
        # opening in the short block is part of the preserved baseline.
        spans = [(margin, L - margin)]
        if n == 13 and i == 0:
            spans = [
                (margin, L * (count // 2) / count),
                (L * (count // 2 + 1) / count, L - margin),
            ]
        for a, b in spans:
            _shell(
                m, [(u, 0.11, inset, base, base + 0.16) for u in (a, b)], C['white'], C
            )


def _south_windows(m, h, levels, C, detail):
    L = m.w.length
    story = h / levels
    count = round(L / 3.65)
    width = L / count
    warm = C['courtBrick']
    for level in range(levels):
        lo = level * story
        head = lo + story * 0.78
        sill = lo + story * 0.34
        hi = lo + story
        for bay in range(count):
            a = bay * width
            b = a + width
            c = (a + b) / 2
            if not level and abs(c - L / 2) < width * 0.76:
                # Preserve the pre-existing middle ground-floor assembly without
                # projecting a new bay across it.
                m.panel(a, b, -0.55, 0.88, C['courtStone'])
                m.panel(a, b, 0.88, hi - 0.15, warm)
                m.panel(a, b, hi - 0.15, hi, C['white'])
                continue
            half = 0.35 * width
            # The ground photo shows bay sides continuing through the stone
            # base. The upper wall and glazing follow the same canted outline.
            pairs = [
                (a, 0),
                (c - half, 0),
                (c - half * 0.72, 0.42),
                (c + half * 0.72, 0.42),
                (c + half, 0),
                (b, 0),
            ]
            for j, ((u, d), (v, e)) in enumerate(zip(pairs, pairs[1:])):

                def rib(z1, z2, mat):
                    m.face([(u, d, z1), (v, e, z1), (v, e, z2), (u, d, z2)], mat)

                start = lo
                if not level:
                    rib(-0.55, 0.02, C['courtStone'])
                    start = 0.88
                    if not detail:
                        rib(0.02, 0.88, C['courtStone'])
                    else:
                        for row in range(3):
                            lower = 0.02 + row * 0.86 / 3
                            upper = lower + 0.86 / 3
                            rib(lower, lower + 0.014, C['dormConcrete'])
                            x = u
                            while x < v - 0.000001:
                                y = min(v, x + (0.37 if row % 2 and x == u else 0.74))
                                joint = min(0.014, y - x)
                                for startx, endx, mat in (
                                    (x, x + joint, C['dormConcrete']),
                                    (x + joint, y, C['courtStone']),
                                ):
                                    if endx - startx < 0.000001:
                                        continue
                                    d0 = d + (e - d) * (startx - u) / (v - u)
                                    d1 = d + (e - d) * (endx - u) / (v - u)
                                    m.face(
                                        [
                                            (startx, d0, lower + 0.014),
                                            (endx, d1, lower + 0.014),
                                            (endx, d1, upper),
                                            (startx, d0, upper),
                                        ],
                                        mat,
                                    )
                                x = y
                rib(start, sill, warm)
                if j in (0, 4):
                    rib(sill, head, warm)
                else:
                    rib(sill, sill + 0.065, C['metal'])
                    if detail and j == 2:
                        m.panel(
                            u, c - 0.032, sill + 0.065, head - 0.07, C['dormWindow'], d
                        )
                        m.panel(
                            c - 0.032,
                            c + 0.032,
                            sill + 0.065,
                            head - 0.07,
                            C['metal'],
                            d,
                        )
                        m.panel(
                            c + 0.032, v, sill + 0.065, head - 0.07, C['dormWindow'], d
                        )
                    else:
                        rib(sill + 0.065, head - 0.07, C['dormWindow'])
                    rib(head - 0.07, head, C['white'])
                rib(head, hi - 0.15, warm)
                rib(hi - 0.15, hi, C['white'])


def _eight(m, h, levels, C, detail):
    L = m.w.length
    story = h / levels
    count = 13
    for level in range(levels):
        lo = level * story
        hi = lo + story
        warm = level < 2
        col = C['dormRose'] if warm else C['white']
        for i in range(count):
            a = L * i / count
            b = L * (i + 1) / count
            width = b - a
            if i == count // 2:
                # A full-height break separates the flanking rows. Its width is
                # estimated from the public oblique view and the West 7 facade.
                m.panel(a, b, lo, hi, C['dormRecess'], -1.21)
                m.side(a, 0, -1.21, lo, hi, col)
                m.side(b, -1.21, 0, lo, hi, col)
                continue
            inset = -0.92
            pier = 0.49 if warm else 0.25
            m.window(
                a,
                b,
                lo,
                hi,
                a + 0.30 * width,
                b - 0.21 * width,
                lo + 1.09,
                lo + 2.48,
                C['dormConcreteLight'],
                C,
                detail,
                inset,
            )
            for u, v in ((a, a + pier / 2), (b - pier / 2, b)):
                m.panel(u, v, lo + 0.16, hi, col)
            u = a + pier / 2
            v = b - pier / 2
            m.side(u, 0, inset, lo + 0.16, hi, col)
            m.side(v, inset, 0, lo + 0.16, hi, col)
            caps = ([0] if i in (0, count // 2 + 1) else []) + (
                [-1] if i in (count - 1, count // 2 - 1) else []
            )
            _shell(
                m,
                [(k, 0.027, inset, lo, lo + 0.16) for k in (a, b)],
                C['white'],
                C,
                caps,
            )
            width = v - u
            x1 = u if warm else u + 0.21 * width
            x2 = v if warm else v - 0.21 * width
            _shell(
                m,
                [(k, 0.01, -0.12, lo + 0.16, lo + 1.03) for k in (x1, x2)],
                C['dormRose'] if warm else C['dormButter'],
                C,
                bottom=False,
            )
            if not warm:
                m.panel(u, v, lo + 1.03, lo + 1.10, C['metal'], 0.01)
        if not level:
            m.panel(0, L, -0.55, 0, C['dormConcrete'])


def terminal(w, b, n):
    ends = [w.x, w.x + w.tx * w.length]
    outer = min(
        range(2),
        key=lambda i: min(abs(ends[i] - b['bounds'][0]), abs(ends[i] - b['bounds'][2])),
    )
    width = {7: 2.55, 8: 2.71, 9: 2.74, 10: 2.65, 11: 2.68, 12: 2.78}[n]
    return (0, width) if outer == 0 else (w.length - width, w.length)


def _gallery_end(m, b, n, h, levels, C, detail):
    w = m.w
    a, c = terminal(w, b, n)
    story = h / levels
    edge = c if a == 0 else a
    for i in range(levels):
        lo = i * story
        hi = lo + story
        u = (a + c) / 2
        col = C['dormRose'] if i < 2 else C['white']
        half = (c - a) * (0.235 if i >= 2 else 0.27)
        m.window(
            a,
            c,
            lo if i else -0.55,
            hi - 0.12,
            u - half,
            u + half,
            lo + 0.85,
            lo + 2.44,
            col,
            C,
            detail,
            0.13,
        )
        m.panel(
            a, c, hi - 0.12, hi, C['dormBlush'] if i < 2 else C['dormStonePale'], 0.13
        )
        if a == 0:
            m.side(edge, 0.13, -0.98, lo, hi, col)
            m.side(a, 0, 0.13, lo, hi, col)
        else:
            m.side(edge, -0.98, 0.13, lo, hi, col)
            m.side(c, 0.13, 0, lo, hi, col)


def finishes(new, targets, b, z, n, C, detail):
    h = b['height']
    levels = int(b['levels'])
    levelh = h / levels
    for w, k in targets:
        m = Surface(w, new, z)
        L = w.length
        if k == 'gallery-end':
            _gallery_end(m, b, n, h, levels, C, detail)
        elif k == 'one-west':
            u = 0.57 * L
            m.window(
                0,
                L,
                0.14,
                levelh,
                u - 0.56,
                u + 0.56,
                0.70,
                2.64,
                C['dormRose'],
                C,
                detail,
            )
        elif k == 'base':
            high = {7: 0.36, 8: 0.41, 9: 0.33, 10: 0.31, 11: 0.31, 12: 0.43, 15: 1.02}[
                n
            ]
            stone = n in (8, 12, 15)
            m.plinth(0, L, high, C, detail, stone)
            m.panel(0, L, high + 0.06, levelh, C['dormRose'])
            # The painted base rises above the second white floor stripe.
            lift = {7: 0.57, 8: 0.50, 9: 0.49, 10: 0.63, 11: 0.47, 12: 0.60, 15: 0.35}[
                n
            ]
            m.panel(0, L, 2 * levelh, 2 * levelh + lift, C['dormRose'])
            m.panel(0, L, 2 * levelh + lift, 3 * levelh, C['white'])
        elif k == 'eight':
            _eight(m, h, levels, C, detail)
        elif k == 'brick-end':
            _brick_end(m, n, h, levels, C, detail)
        elif k == 'court':
            _corridor(m, n, h, levels, C, detail)
        elif k == 'bays':
            _south_windows(m, h, levels, C, detail)
        elif k == 'round-west':
            _round_end(m, h, levels, C, detail)
        elif k == 'annex-end':
            for i in range(levels):
                lo = i * levelh
                hi = lo + levelh
                if not i:
                    m.plinth(0, L, 0.48, C, detail, True)
                color = C['dormRose'] if i < 2 else C['white']
                u = L * 0.5
                m.window(
                    0,
                    L,
                    lo if i else 0.54,
                    hi - 0.11,
                    u - 0.56,
                    u + 0.56,
                    lo + 1.02,
                    lo + 2.42,
                    color,
                    C,
                    detail,
                )
                m.panel(0, L, hi - 0.11, hi, C['dormStonePale'])


def court_palette(C):
    # Brick and stone estimated from the dated street photographs. The
    # in-memory material registry is the same registry used by Mesh.object.
    extended = dict(C)
    for key, name, srgb in (
        ('courtBrick', 'WestCourt_PeachBrick', (193, 137, 119)),
        ('courtStone', 'WestCourt_GreyPlinth', (100, 95, 91)),
    ):
        slot = next((i for i, m in enumerate(MATERIALS) if m.name == name), None)
        if slot is None:
            rgb = [((v / 255 + 0.055) / 1.055) ** 2.4 for v in srgb]
            slot = material(name, tuple(rgb), 0.88)
        extended[key] = slot
    return extended
