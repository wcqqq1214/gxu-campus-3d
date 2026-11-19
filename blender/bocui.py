"""North frontage of Bocui, measured against the dining guide and the 2026 courtyard photograph."""

from pathlib import Path

from geometry import MATERIALS, material, tile_material
from south_gate import inscription

PORTALS = ((-3.12, -0.19), (0.19, 3.12))
WINDOWS = ((3.80, 6.68), (7.25, 10.36), (10.92, 14.09), (14.65, 17.82))


def finishes(e):
    palette = {
        'boSand': ((0.64, 0.46, 0.30), 0.50, 0.06),
        'boSeam': ((0.235, 0.19, 0.151), 0.73, 0),
        'boCornice': ((0.88, 0.86, 0.74), 0.48, 0.08),
        'boBronze': ((0.076, 0.052, 0.048), 0.42, 0.24),
        'boWindow': ((0.122, 0.146, 0.15), 0.16, 0.42),
        'boShadow': ((0.15, 0.18, 0.19), 0.59, 0),
        'boInterior': ((0.65, 0.69, 0.67), 0.38, 0.09),
        'boSash': ((0.32, 0.31, 0.29), 0.33, 0.57),
        'boThreshold': ((0.42, 0.40, 0.37), 0.55, 0.04),
        'boApron': ((0.65, 0.62, 0.56), 0.64, 0.01),
        'boSkirt': ((0.34, 0.339, 0.32), 0.63, 0.02),
        'boStripEdge': ((0.43, 0.45, 0.46), 0.31, 0.25),
        'boCurtain': ((0.45, 0.52, 0.56), 0.85, 0),
        'boRose': ((0.66, 0.43, 0.37), 0.67, 0),
    }
    for name, props in palette.items():
        if name not in e.colors:
            e.colors[name] = material(name, *props)
    for name, alpha in [('boLeaf', 0.27), ('boPVC', 0.47)]:
        if name not in e.colors:
            idx = material(name, (0.31, 0.37, 0.41), 0.19, 0.16)
            e.colors[name] = idx
            mat = MATERIALS[idx]
            mat.node_tree.nodes.get('Principled BSDF').inputs[
                'Alpha'
            ].default_value = alpha
            mat.diffuse_color = (0.31, 0.37, 0.41, alpha)
    tile_material(e.colors, 'boUpperTile', 'dong-porcelain.png', (0.78, 0.73, 0.67))


def casement(e, left, right, bottom, top, out, count, *, upper=False):
    width, height = right - left, top - bottom
    mid = (left + right) / 2
    e.box(mid, out, (bottom + top) / 2, width, 0.085, height, 'boWindow')
    for x in (left, right):
        e.box(x, out + 0.045, (bottom + top) / 2, 0.046, 0.10, height, 'boSash')
    for z in (bottom, top):
        e.box(mid, out + 0.049, z, width, 0.10, 0.047, 'boSash')
    if not e.detail:
        return
    cross = bottom + height * (0.72 if upper else 0.25)
    e.trim(mid, out + 0.080, cross, width, 0.046, 0.045, 'boSash')
    for i in range(count):
        x = left + width * (i + 0.5) / count
        if i:
            e.trim(
                left + width * i / count,
                out + 0.082,
                (bottom + top) / 2,
                0.041,
                0.052,
                height,
                'boSash',
            )
        if upper:
            for side in (-1, 1):
                e.trim(
                    x + side * width / count * 0.37,
                    out + 0.058,
                    (top + bottom) / 2,
                    width / count * 0.18,
                    0.018,
                    height - 0.12,
                    'boCurtain',
                )


def doorway(e, l, r, *, strips, half_opening=0.84):
    x = (l + r) / 2
    e.box(x, 0.11, 1.53, r - l, 0.11, 2.63, 'boShadow')
    e.box(x, 0.71, 3.071, r - l, 0.14, 0.482, 'boBronze')
    for hand in (-1, 1):
        end = x + hand * (r - l) / 2
        e.box(end, 0.77, 1.525, 0.064, 0.13, 2.61, 'boBronze')
        jamb = x + hand * half_opening
        e.box(jamb, 0.81, 1.525, 0.058, 0.09, 2.61, 'boBronze')
        e.box(
            (jamb + end) / 2,
            0.744,
            1.51,
            abs(end - jamb) - 0.062,
            0.045,
            2.49,
            'boWindow',
        )
        e.box(
            (jamb + end) / 2,
            0.77,
            1.31,
            abs(end - jamb) - 0.07,
            0.033,
            0.10,
            'diningLetterRed',
        )
        # Glass pivots outward. Link the bar and handle to the actual swung leaf.
        a = (jamb, -0.81)
        b = (jamb + hand * 0.20, -1.61)
        v = [(*a, 0.236), (*b, 0.236), (*b, 2.80), (*a, 2.80)]
        e.glazing.face(v if hand < 0 else v[::-1], e.colors['boLeaf'])
        for v1, v2 in zip(v, v[1:] + v[:1]):
            e.glazing.line(v1, v2, 0.025, e.colors['boBronze'])
        if e.detail:
            e.glazing.face(
                [(*a, 1.25), (*b, 1.25), (*b, 1.35), (*a, 1.35)],
                e.colors['boStripEdge'],
            )
            hx, hy = b[0] - hand * 0.035, b[1] + 0.12
            e.glazing.line((hx, hy, 0.96), (hx, hy, 1.47), 0.019, e.colors['boSash'])
    e.box(x, 0.77, 0.226, r - l, 0.28, 0.038, 'boThreshold')
    if strips:
        e.box(x, 0.27, 2.76, 1.77, 0.12, 0.08, 'boSash')
        for i in range(5):
            u = x + (i - 2) * 0.35
            # A slightly bowed PVC strip catches daylight at its transparent edges.
            profile = [(-0.18, 0.012), (-0.11, -0.009), (0.12, 0.004), (0.18, 0.016)]
            for (a, da), (b, db) in zip(profile, profile[1:]):
                e.glazing.face(
                    [
                        (u + a, -0.35 + da, 0.248),
                        (u + b, -0.35 + db, 0.248),
                        (u + b, -0.32 + db, 2.73),
                        (u + a, -0.32 + da, 2.73),
                    ],
                    e.colors['boPVC'],
                )
            if e.detail:
                e.trim(u - 0.177, 0.354, 1.48, 0.013, 0.012, 2.45, 'boStripEdge')


def apron(e, left, right):
    # Low threshold, pale landing and darker granite strip. The outer paving
    # falls almost flush with the road in both unobstructed entrance views.
    middle = (left + right) / 2
    for near, far, back, front, finish in (
        (0.0, 0.93, 0.212, 0.212, 'boThreshold'),
        (0.93, 4.23, 0.198, 0.142, 'boApron'),
        (4.23, 6.68, 0.137, 0.035, 'boSkirt'),
    ):
        e.structure.face(
            [
                (left, -far, front),
                (right, -far, front),
                (right, -near, back),
                (left, -near, back),
            ],
            e.colors[finish],
        )
        e.box(
            middle, far, (front - 0.05) / 2, right - left, 0.022, front + 0.05, finish
        )
        if e.detail:
            count = round((right - left) / 0.90)
            for j in range(1, count):
                u = left + (right - left) * j / count
                e.glazing.face(
                    [
                        (u - 0.004, -far, front + 0.002),
                        (u + 0.004, -far, front + 0.002),
                        (u + 0.004, -near, back + 0.002),
                        (u - 0.004, -near, back + 0.002),
                    ],
                    e.colors['boThreshold'],
                )
            for j in range(1, round((far - near) / 0.47)):
                t = j / round((far - near) / 0.47)
                e.trim(
                    middle,
                    near + (far - near) * t,
                    back + (front - back) * t + 0.003,
                    right - left,
                    0.01,
                    0.005,
                    'boThreshold',
                )


def cast_name(e, text, layout):
    for char, (x, z, width, height) in zip(text, layout, strict=True):
        g = inscription(
            char,
            0,
            -2.558,
            z,
            1.4,
            height,
            e.colors['diningLetterRed'],
            False,
            flat=not e.detail,
            font_path=Path(__file__).parent / 'fonts/GXUDiningSans.ttf',
        )
        size = max(v[0] for v in g.v) - min(v[0] for v in g.v)
        g.v = [(x + a * width / size, y, h) for a, y, h in g.v]
        e.glazing.extend(g)


def upper_front(e, left, right):
    roof = e.height
    e.cladding(left, right, 4.55, roof, 0.031, 'boUpperTile', 1.15)
    for lo, hi in [(-8.18, 0.58), (10.43, 18.55)]:
        e.box(
            (lo + hi) / 2,
            0.39,
            (roof + 4.55) / 2,
            hi - lo,
            0.78,
            roof - 4.55,
            'boCornice',
        )
        e.cladding(lo, hi, 4.55, roof, 0.784, 'boUpperTile', 1.15)
        e.box((lo + hi) / 2, 0.49, roof - 0.11, hi - lo + 0.14, 1.0, 0.23, 'boCornice')
    for level in range(5):
        z = 4.87 + level * 3.25
        for l, r in [(-7.52, -3.82), (-3.14, -0.25), (11.08, 14.25), (14.85, 17.99)]:
            casement(e, l, r, z + 0.24, z + 2.15, 0.806, 4, upper=True)
        for l, r in [
            (1.32, 3.30),
            (4.1, 6.08),
            (6.54, 8.48),
            (19.1, 20.7),
            (21.1, 22.8),
            (23.2, 24.63),
        ]:
            casement(e, l, r, z + 0.30, z + 1.93, 0.091, 2, upper=True)
        for l, r in [
            (0.62, 3.32),
            (8.66, 10.43),
            (18.55, 20.68),
            (23.03, min(right, 25.0)),
        ]:
            if r - l < 0.3:
                continue
            base = z + 0.08
            e.box((l + r) / 2, 0.80, base, r - l, 1.58, 0.16, 'boRose')
            for h in (base + 0.19, base + 0.76):
                e.box((l + r) / 2, 1.55, h, r - l, 0.064, 0.050, 'boSash')
            if e.detail:
                for j in range(1, 6):
                    e.trim(
                        (l + r) / 2,
                        1.55,
                        base + 0.18 + j * 0.095,
                        r - l,
                        0.035,
                        0.019,
                        'boSash',
                    )
                for x in (l + 0.04, r - 0.04):
                    e.trim(x, 1.55, base + 0.43, 0.042, 0.055, 0.71, 'boSash')
        for l, r in [(-8.18, 0.58), (10.43, 18.55)]:
            e.box((l + r) / 2, 0.81, z + 2.72, r - l, 0.06, 0.15, 'boRose')


def bocui(e, offset):
    finishes(e)
    left, right = -e.length / 2 - offset, e.length / 2 - offset
    upper_front(e, left, right)
    mid = (left + right) / 2
    hl, hr = 18.35, min(right - 0.18, 23.05)
    for a, b in [(left, -3.12), (-0.19, 0.19), (3.12, hl), (hr, right)]:
        e.box((a + b) / 2, 0.33, 1.76, b - a, 0.66, 3.52, 'boSand')
    # At both double doors the backing is recessed behind the open leaves.
    # Cover only the opaque panels on the door plane, keeping the glass immediately in front.
    for l, r in PORTALS:
        e.box((l + r) / 2, 0.30, 3.39, r - l, 0.60, 0.16, 'boSand')
        if e.detail:
            e.trim((l + r) / 2 - 0.24, 0.213, 1.87, 0.94, 0.02, 0.34, 'boInterior')
            e.trim((l + r) / 2 + 0.39, 0.213, 2.47, 0.57, 0.02, 0.041, 'boCornice')
        doorway(e, l, r, strips=True)
    for l, r in WINDOWS:
        casement(e, l, r, 1.23, 3.05, 0.68, 4)
    casement(e, -9.92, -8.73, 1.23, 3.00, 0.68, 2)
    e.box(-6.58, 0.68, 1.39, 0.99, 0.08, 2.36, 'boBronze')
    e.box(-6.58, 0.732, 1.39, 0.88, 0.036, 2.23, 'boSand')
    e.box(-6.19, 0.76, 1.23, 0.038, 0.066, 0.16, 'boBronze')
    # The hotel shares the canopy but has its own entrance west of the dining-room windows.
    doorway(e, hl, hr, strips=False, half_opening=1.15)
    e.box((hl + hr) / 2, 0.71, 3.37, hr - hl, 0.14, 0.13, 'boBronze')
    e.box(mid, 1.265, 4.006, right - left, 2.53, 1.184, 'boCornice')
    e.box(mid, 1.275, 4.603, right - left + 0.04, 2.55, 0.075, 'boCornice')
    cast_name(
        e,
        '博萃餐厅',
        [
            (-3.703, 4.007, 0.767, 0.759),
            (-1.233, 4.040, 0.784, 0.790),
            (1.285, 4.050, 0.774, 0.770),
            (3.828, 4.026, 0.731, 0.734),
        ],
    )
    cast_name(
        e,
        '博萃楼宾馆',
        [(x, 4.02, 0.78, 0.77) for x in (13.84, 16.01, 18.20, 20.36, 22.54)],
    )
    if e.detail:
        # Paired horizontal joints stop at the openings; no seams cross glazing.
        intervals = [
            (left, -9.92),
            (-8.73, -7.11),
            (-6.03, -3.12),
            (-0.19, 0.19),
            (3.12, 3.80),
        ]
        intervals.extend((a[1], b[0]) for a, b in zip(WINDOWS, WINDOWS[1:]))
        for l, r in intervals:
            for z in (1.17, 1.36, 2.86, 3.05):
                e.trim((l + r) / 2, 0.668, z, r - l, 0.012, 0.013, 'boSeam')
        for x in (-2.7, -0.45, 1.92, 4.3):
            e.glazing.cylinder(x, -1.84, 3.408, 0.061, 0.014, e.colors['white'], n=12)
    apron(e, left, right)
