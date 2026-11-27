"""Linked wings, gallery blocks, the low hipped dorm and the East 18 tower."""

import math

from .walls import Edge, cap, cell, clockwise, projecting_window, sash
from .walls import gallery as build_gallery


def east7_wall(m, e, z, step, p, near):
    width = e.length
    for j in range(6):
        low = z + j * step
        wall = p['brick'] if j < 2 else p['cream']
        stripe = p['band'] if j < 2 else p['brick']
        sill = low + 0.66
        head = sill + 0.265 * step
        stripe_lo = low + 0.64 * step
        base = low
        if j == 0:
            e.rect(m, 0, width, low, low + 0.38, 0, p['plinth'])
            base = low + 0.38
        if j == 2:
            # A shallow projecting shoulder occurs at the change of finish.
            e.strip(m, 0, width, 0.095, 0, low, p['shade'], True)
            e.rect(m, 0, width, low, low + 0.14, 0.095, p['plinth'])
            e.strip(m, 0, width, 0.095, 0, low + 0.14, p['band'])
            for t in (0, width):
                side = Edge(e.p(t, 0, 0), e.p(t, 0.095, 0))
                side.rect(m, 0, 0.095, low, low + 0.14, 0, p['plinth'], t == width)
            base = low + 0.14
        for l, r, mid in [(0, 0.14, 0.078), (0.14, 0.25, 0.196), (0.25, 0.365, 0.304)]:
            cell(
                m,
                e,
                l * width,
                r * width,
                base,
                stripe_lo,
                (mid - 0.033) * width,
                (mid + 0.033) * width,
                sill,
                head,
                0,
                0.14,
                wall,
                p,
                near,
            )
        e.rect(m, 0.365 * width, width, base, stripe_lo, 0, wall)
        e.rect(m, 0, width, stripe_lo, stripe_lo + 0.055 * step, 0, stripe)
        e.rect(m, 0, width, stripe_lo + 0.055 * step, low + step, 0, wall)


def west7_floor(m, e, base, top, floor, p, near):
    wall = p['cream'] if floor >= 2 else p['brick']
    bottom = base
    if floor == 0:
        e.rect(m, 0, e.length, base, base + 0.38, 0, p['plinth'])
        bottom += 0.38
    left, right = 0.46 * e.length, 0.94 * e.length
    e.rect(m, 0, left, bottom, top, 0, wall)
    e.rect(m, right, e.length, bottom, top, 0, wall)
    for i in range(3):
        u = left + i * (right - left) / 3
        v = u + (right - left) / 3
        cell(
            m,
            e,
            u,
            v,
            bottom,
            top,
            u + 0.22 * (v - u),
            v - 0.22 * (v - u),
            base + 1.12,
            top - 0.88,
            0,
            0.14,
            wall,
            p,
            near,
        )


def wall_finish(mode, floor, p):
    if mode in ('plain', 'endCream', 'slant', 'slantEnd', 'framed'):
        return p['cream']
    if mode == 'combGallery':
        return p['shellPink']
    if mode.startswith('twoTone'):
        return p['brick' if floor < 2 else 'cream']
    if mode in ('tower', 'towerEnd'):
        if floor == 0:
            return p['plinth']
        return p['blueGrey' if mode == 'tower' else 'render']
    return p['brick']


def bay_layout(e, mode, floor):
    length = e.length
    gallery = mode in (
        'gallery',
        'twoToneGallery',
        'slant',
        'combGallery',
    ) and floor >= (2 if mode == 'twoToneGallery' else 1)
    if mode == 'gallery' and gallery:
        # The continuous south gallery ends at an individual brick window bay.
        width = min(3.15, length * 0.23)
        if e.end_at_start:
            return [(0, width, False), (width, length, True)]
        return [(0, length - width, True), (length - width, length, False)]
    pitch = {'combGallery': 4.1, 'towerEnd': 8}.get(mode, 13.7 if gallery else 4.4)
    count = max(1, round(length / pitch))
    return [
        (length * i / count, length * (i + 1) / count, gallery) for i in range(count)
    ]


def opening_dimensions(mode, gallery, balcony, tower):
    """Fraction of bay width, sill above slab, and head below slab."""
    if gallery:
        return (0.965, 1.16, 0.32) if mode == 'gallery' else (0.965, 1.0, 0.30)
    if balcony:
        return 0.63, 1.0, 0.33
    if tower:
        return 0.61, 0.82, 0.53
    if mode in ('stair', 'slantEnd'):
        return 0.24, 0.82, 0.53
    return 0.48, 0.82, 0.53


def facade(m, e, z, levels, storey, mode, P, detail):
    L = e.length
    for floor in range(levels):
        base = z + storey * floor
        top = base + storey
        exterior = wall_finish(mode, floor, P)
        if mode == 'west7':
            west7_floor(m, e, base, top, floor, P, detail)
        elif mode in ('blank', 'return7') and (
            L >= 3 or (mode == 'return7' and L >= 1)
        ):
            wall = P['cream'] if mode == 'return7' and floor >= 2 else exterior
            if floor == 0:
                e.rect(m, 0, L, base, base + 0.39, 0, P['plinth'])
                base += 0.39
            e.rect(m, 0, L, base, top, 0, wall)
        elif mode in ('blank', 'endCream', 'return7') or L < 3.0:
            e.rect(m, 0, L, base, top, 0, exterior)
        else:
            for col, (l, r, is_gallery) in enumerate(bay_layout(e, mode, floor)):
                step = r - l
                if (
                    mode == 'tower'
                    and e.ux > 0.99
                    and e.length > 30
                    and col == 2
                    and 1 <= floor <= 7
                ):
                    # The narrow lights occupy the third bay from the west.
                    continue
                balcony = mode == 'balconies' and col % 2 == 0 and floor > 0
                tower = mode == 'tower' and floor > 0
                ratio, sill_height, head_depth = opening_dimensions(
                    mode, is_gallery, balcony, tower
                )
                u = (r + l - ratio * step) / 2
                v = (r + l + ratio * step) / 2
                sill = base + sill_height
                lintel = top - head_depth
                for a, b, lo, hi in [
                    (l, u, base, top),
                    (v, r, base, top),
                    (u, v, base, sill - 0.99 if balcony else sill),
                    (u, v, lintel, top),
                ]:
                    e.rect(m, a, b, lo, hi, 0, exterior)
                if is_gallery or balcony:
                    gallery_depth = 0.82 if balcony else 1.12
                    build_gallery(
                        m,
                        e.subsection(u, v),
                        sill,
                        lintel,
                        gallery_depth,
                        P['cream'],
                        exterior,
                        P,
                        detail,
                        balcony,
                    )
                elif tower:
                    projecting_window(m, e.subsection(u, v), sill, lintel, P, detail)
                else:
                    e.reveal(m, u, v, sill, lintel, 0, -0.15, exterior)
                    if mode == 'framed':
                        sash(m, e, u, v, sill, lintel, -0.15, P, detail)
                    else:
                        e.rect(m, u, v, sill, lintel, -0.15, P['glass'])
                        if detail and v - u > 1.15:
                            t = (u + v) / 2
                            e.beam(
                                m,
                                t - 0.032,
                                t + 0.032,
                                sill,
                                lintel,
                                -0.12,
                                0.065,
                                P['band'],
                            )
        if mode not in ('tower', 'towerEnd') and L >= 3:
            e.beam(m, 0.025, L - 0.025, top - 0.11, top, 0.018, 0.065, P['band'])


def shell(m, ring, z, n, step, mode, P, detail, coping=0.42):
    r = clockwise(ring)
    cap(m, r, z + n * step, P['roof'])
    middle = (min(p[0] for p in r) + max(p[0] for p in r)) / 2
    for a, b in zip(r, r[1:] + r[:1]):
        e = Edge(a, b)
        e.end_at_start = abs(e.a[0] - middle) > abs(b[0] - middle)
        treatment = mode(e)
        if treatment == 'east7':
            east7_wall(m, e, z, step, P, detail)
        else:
            facade(m, e, z, n, step, treatment, P, detail)
        if e.length > 0.35:
            e.beam(
                m,
                0.02,
                e.length - 0.02,
                z + n * step,
                z + n * step + coping,
                -0.075,
                0.18,
                P['band'],
                close_bottom=treatment != 'east7',
            )


def comb(m, b, z, P, detail):
    # Split four mapped bars at the re-entrant corners of the existing polygon.
    # The long northern bar contains both 1B (west) and 1A (east).
    r = b['polygons'][0][0]

    def west(y):
        a, c = r[14], r[15]
        return [a[0] + (c[0] - a[0]) * (y - a[1]) / (c[1] - a[1]), y]

    # Interpolate the west corners along the same angled cross-axis as each wing.
    slope = (r[21][1] - r[22][1]) / (r[21][0] - r[22][0])

    def cross(p):
        x, y = west(p[1])
        for _ in range(3):
            y = p[1] + slope * (x - p[0])
            x, _ = west(y)
        return [x, y]

    bars = [
        r[15:23] + [cross(r[22])],
        [cross(r[23])] + r[23:26] + r[:3] + [cross(r[2])],
        [cross(r[3])] + r[3:9] + [cross(r[8])],
        [cross(r[9])] + r[9:15],
    ]
    for ring in bars:
        shell(
            m,
            ring,
            z,
            6,
            3.3,
            lambda e: (
                'combGallery'
                if e.length > 12 and e.ny < -0.76
                else 'plain'
                if e.length > 12
                else 'endCream'
            ),
            P,
            detail,
        )
    for low, high in [(22, 23), (2, 3), (8, 9)]:
        ring = [cross(r[low]), r[low], r[high], cross(r[high])]
        # The crossbars abut the wings. Emit exposed faces only.
        ring = clockwise(ring)
        cap(m, ring, z + 6.6, P['roof'])
        for a, c in zip(ring, ring[1:] + ring[:1]):
            edge = Edge(a, c)
            if abs(edge.uy) > 0.9:
                facade(m, edge, z, 2, 3.3, 'plain', P, detail)


def north_spine(m, e, z, p):
    pitch = e.length / round(e.length / 4.4)
    mid = 2.5 * pitch
    l = mid - 0.5 * pitch
    r = mid + 0.5 * pitch
    a = mid - 0.395 * pitch
    c = mid + 0.395 * pitch
    yellow = p['yellow']
    storey = 3.05
    full_a, full_c = a, c
    for floor in range(1, 8):
        lo = z + floor * storey
        hi = lo + storey
        projected = 2 <= floor <= 5
        a, c = (
            (full_a, full_c)
            if projected
            else (mid - 0.245 * pitch, mid + 0.245 * pitch)
        )
        e.rect(m, l, a, lo, hi, 0, p['blueGrey'])
        e.rect(m, c, r, lo, hi, 0, p['blueGrey'])
        depth = 0.68 if projected else 0.11
        if floor == 2:
            spine_cap(m, e, full_a, full_c, mid, pitch, lo, yellow, True)
        if floor == 6:
            spine_cap(m, e, full_a, full_c, mid, pitch, lo, yellow, False)
        if floor == 7:
            e.strip(m, a, c, depth, 0, hi, yellow)
        if floor == 1:
            e.strip(m, a, c, depth, 0, lo, yellow, ceiling=True)
        for t in (a, c):
            side = Edge(e.p(t, 0, 0), e.p(t, depth, 0))
            side.rect(m, 0, depth, lo, hi, 0, yellow, t == c)
        if projected:
            # Yellow forward fins wrap the deeply shaded center strip. They meet
            # the rear face along shared edges; the four narrow lights are cut into it.
            fin = (c - a) * 0.14
            for u, v in [(a, a + fin), (c - fin, c)]:
                e.rect(m, u, v, lo, hi, depth, yellow)
            for t in (a + fin, c - fin):
                side = Edge(e.p(t, 0.38, 0), e.p(t, depth, 0))
                side.rect(
                    m,
                    0,
                    depth - 0.38,
                    lo,
                    hi - (0.25 if floor == 5 else 0),
                    0,
                    yellow,
                    t == a + fin,
                )
            inner = a + fin
            outer = c - fin
            top = hi
            if floor == 5:
                top = hi - 0.25
                e.strip(m, inner, outer, 0.68, 0.38, top, yellow, ceiling=True)
                e.rect(m, inner, outer, top, hi, 0.68, yellow)
            center = (inner + outer) / 2
            u = center - 0.075 * (c - a)
            v = center + 0.075 * (c - a)
            sill = lo + 0.54 * storey
            head = sill + 0.27 * storey
            for lft, rgt, low, top in [
                (inner, u, lo, top),
                (v, outer, lo, top),
                (u, v, lo, sill),
                (u, v, head, top),
            ]:
                e.rect(m, lft, rgt, low, top, 0.38, yellow)
            e.reveal(m, u, v, sill, head, 0.38, 0.16, yellow)
            e.rect(m, u, v, sill, head, 0.16, p['blueGrey'])
        else:
            e.rect(m, a, c, lo, hi, depth, yellow)


def spine_cap(m, e, a, b, mid, pitch, h, mat, ceiling):
    fin = (b - a) * 0.14
    edges = sorted([a, a + fin, mid - 0.245 * pitch, mid + 0.245 * pitch, b - fin, b])
    for l, r in zip(edges, edges[1:]):
        t = (l + r) / 2
        outer = 0.68 if not ceiling or t < a + fin or t > b - fin else 0.38
        inner = 0.11 if abs(t - mid) < 0.245 * pitch else 0
        e.strip(m, l, r, outer, inner, h, mat, ceiling)


def low_hipped_block(m, ring, z, b, p, detail):
    footprint = clockwise(ring)
    roofline = z + b['height']
    for a, c in zip(footprint, footprint[1:] + footprint[:1]):
        e = Edge(a, c)
        n = 8 if e.length > 20 else 2
        e.rect(m, 0, e.length, z, z + 0.36, 0, p['plinth'])
        for f in range(2):
            low = z + f * b['height'] / 2
            high = low + b['height'] / 2
            top = high - (0.16 if f == 1 else 0.12)
            e.rect(m, 0, e.length, top, high, 0, p['band'])
            for c in range(n):
                l, r = e.length * c / n, e.length * (c + 1) / n
                mid = (l + r) / 2
                half = (0.235 if n == 8 else 0.15) * (r - l)
                cell(
                    m,
                    e,
                    l,
                    r,
                    low + (0.36 if f == 0 else 0),
                    top,
                    mid - half,
                    mid + half,
                    low + 0.87,
                    min(high - 0.61, roofline - 0.6),
                    0,
                    0.19,
                    p['cream'],
                    p,
                    detail,
                )

    # Eaves and short hips on the visible pale roof. Ridge rise is approximate.
    a, c, d, f = footprint

    def inset(p, q, t):
        return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)

    if math.dist(a, c) < math.dist(c, d):
        a, c, d, f = c, d, f, a
    start = inset(a, f, 0.5)
    end = inset(c, d, 0.5)
    left = (*inset(start, end, 0.10), roofline + 0.75)
    right = (*inset(start, end, 0.90), roofline + 0.75)
    A, B, D, F = [(*p, roofline) for p in (a, c, d, f)]
    for face in [(A, left, right, B), (B, right, D), (D, right, left, F), (F, left, A)]:
        m.face(list(face), p['band'])
