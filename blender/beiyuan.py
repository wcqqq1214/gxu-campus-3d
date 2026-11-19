"""Bei Yuan's east access galleries and the separate west service frontage."""

from pathlib import Path

from geometry import material
from south_gate import inscription


def finishes(e):
    for key, rgb, rough, metal in (
        ('beiFascia', (0.18, 0.22, 0.26), 0.54, 0.27),
        ('beiCap', (0.40, 0.44, 0.45), 0.55, 0.12),
        ('beiRail', (0.54, 0.58, 0.57), 0.30, 0.76),
        ('beiWindow', (0.054, 0.091, 0.12), 0.21, 0.47),
        ('beiTread', (0.40, 0.39, 0.36), 0.81, 0),
        ('beiConcrete', (0.57, 0.59, 0.59), 0.78, 0),
        ('beiHedge', (0.090, 0.073, 0.081), 0.94, 0),
        ('beiLeaf', (0.22, 0.29, 0.064), 0.92, 0),
        ('beiPlaque', (0.50, 0.36, 0.17), 0.59, 0.13),
        ('beiMaroon', (0.12, 0.050, 0.057), 0.66, 0),
        ('beiTile', (0.59, 0.49, 0.36), 0.67, 0),
    ):
        if key not in e.colors:
            e.colors[key] = material(key, rgb, rough, metal)


def panel_edge(e, width, out, bottom, seam, top):
    e.box(0, out / 2, (seam + bottom) / 2, width, out, seam - bottom, 'beiFascia')
    e.box(0, out / 2, (seam + top) / 2, width, out, top - seam, 'beiCap')
    if e.detail:
        count = round(width / 0.97)
        for i in range(1, count):
            e.trim(
                width * (i / count - 0.5),
                out + 0.012,
                (seam + bottom) / 2,
                0.021,
                0.018,
                seam - bottom,
                'dark',
            )


def glazed_stack(e, x, out, width, bottom, height):
    # Each dark strip has four lights vertically and three panes across.
    e.pane(x, out, bottom, width, height, 3, sash=False, glass='beiWindow')
    for row in range(1, 4):
        e.box(x, out + 0.109, bottom + height * row / 4, width, 0.053, 0.068, 'beiCap')


def west_front(e):
    finishes(e)
    half = 20.86
    panel_edge(e, 2 * half, 4.20, 3.716, 4.765, 5.928)
    for i in range(-2, 3):
        x = i * 8.29
        e.box(x, 3.72, 2.04, 0.59, 0.62, 3.36, 'beiConcrete')
        e.box(x, 3.72, 0.59, 0.60, 0.63, 0.44, 'stone')
    for hand in (-1, 1):
        e.box(hand * 13.98, 1.48, 2.03, 0.54, 0.58, 3.33, 'beiConcrete')
        for x in (4.1, 11.7, 18.2):
            e.pane(hand * x, 0.19, 0.40, 6.4, 2.82, 4, glass='residenceGlass')
        # End bays stand proud of the recessed shop openings beneath the canopy.
        side = e.length / 2
        e.box(
            hand * (side + half) / 2,
            1.0,
            e.height / 2,
            side - half,
            2.0,
            e.height,
            'beiConcrete',
        )
        e.box(hand * (side + half) / 2, 2.02, 0.23, side - half, 0.05, 0.46, 'stone')
        if e.detail:
            for z in (5.66, 10.32, 14.88):
                e.trim(hand * 26.67, 2.12, z, 4.04, 0.19, 0.12, 'beiCap')
            # Low rail beside the exposed pipework at the end of the west walk.
            x = hand * 22.16
            e.trim(x, 4.12, 0.21, 3.15, 1.35, 0.42, 'beiTread')
            for dx in (-1.39, 0, 1.39):
                e.trim(x + dx, 3.59, 0.85, 0.055, 0.055, 0.88, 'beiRail')
            e.trim(x, 3.59, 1.28, 2.85, 0.065, 0.065, 'beiRail')
            e.glazing.line(
                (x - 1.3, -4.14, 0.52), (x + 1.3, -4.14, 0.52), 0.13, e.colors['beiCap']
            )
        for bottom in (0.459, 6.257, 10.84, 15.42):
            glazed_stack(e, hand * 26.67, 2.15, 3.785, bottom, 3.899)
    for z in (6.56, 10.55, 14.52, 18.02):
        for i in range(-3, 4):
            x = i * 5.35
            e.pane(x, 0.12, z, 5.15, 1.38, 5, sash=False, glass='beiWindow')
        if e.detail and z < 18:
            for x in (-10.5, -3.55, 4.20, 11.75):
                e.trim(x, 0.59, z + 0.40, 0.84, 1.02, 0.70, 'beiCap')
                e.trim(x, 1.09, z + 0.44, 0.71, 0.06, 0.49, 'dark')
    # Upper walk, lower tread, and the drainage slots directly below the nosings.
    for width, depth, height, finish in (
        (43.16, 7.01, 0.186, 'beiTread'),
        (43.16, 6.736, 0.371, 'beiTread'),
        (43.14, 6.39, 0.378, 'beiTile'),
    ):
        e.box(0, depth / 2, height / 2, width, depth, height, finish)
    if e.detail:
        e.trim(0, 7.19, 0.014, 43.14, 0.26, 0.028, 'stone')
        for i in range(-107, 108):
            e.trim(i * 0.20, 7.19, 0.031, 0.075, 0.185, 0.008, 'dark')
        for i in range(-21, 22):
            e.trim(i * 0.98, 6.86, 0.187, 0.016, 0.23, 0.006, 'stone')


def stair_flight(e, x0, x1, out, width, z0, z1, solid, slab_depth=0.34):
    # Both runs meet the same landing. The inward run reverses behind the outer cheek.
    n = max(9, round((z1 - z0) / 0.17))
    for j in range(n):
        x = x0 + (x1 - x0) * (j + 0.5) / n
        top = z0 + (z1 - z0) * (j + 1) / n
        e.box(
            x,
            out - width / 2,
            top - 0.115,
            abs(x1 - x0) / n + 0.003,
            width,
            0.23,
            'beiTread',
        )
    for y in (out, out - width):
        e.structure.face(
            [(x0, -y, z0 - 0.27), (x1, -y, z1 - 0.27), (x1, -y, z1), (x0, -y, z0)],
            e.colors['beiConcrete'],
        )
    e.structure.face(
        [
            (x0, -out, z0 - 0.27),
            (x1, -out, z1 - 0.27),
            (x1, width - out, z1 - 0.27),
            (x0, width - out, z0 - 0.27),
        ],
        e.colors['beiConcrete'],
    )
    if solid:
        out += 0.025
        # The parapet follows the pitch. Its lower edge cuts back at the landing.
        for y in (out, out - 0.16):
            e.structure.face(
                [
                    (x0, -y, z0 - slab_depth),
                    (x1 + 0.25 * (1 if x1 > x0 else -1), -y, z1 - slab_depth),
                    (x1, -y, z1 + 1.24),
                    (x0, -y, z0 + 1.24),
                ],
                e.colors['beiConcrete'],
            )
        e.structure.face(
            [
                (x0, -out, z0 + 1.24),
                (x1, -out, z1 + 1.24),
                (x1, 0.16 - out, z1 + 1.24),
                (x0, 0.16 - out, z0 + 1.24),
            ],
            e.colors['beiCap'],
        )
    else:
        for dz in (0.48, 0.96):
            e.structure.line(
                (x0, -out, z0 + dz), (x1, -out, z1 + dz), 0.035, e.colors['beiRail']
            )
        for j in range(5):
            t = j / 4
            e.box(
                x0 + (x1 - x0) * t,
                out,
                z0 + (z1 - z0) * t + 0.48,
                0.048,
                0.05,
                0.96,
                'beiRail',
            )


def east_sign(e, z):
    # The university's 2024 photo shows a burgundy board with a light centre panel.
    e.box(-2.28, 4.70, z, 20.35, 0.17, 1.35, 'beiMaroon')
    e.box(-2.28, 4.81, z, 13.1, 0.075, 0.90, 'beiPlaque')
    for i, char in enumerate('北苑餐厅'):
        glyph = inscription(
            char,
            -2.28 + (i - 1.5) * 2.66,
            -4.87,
            z,
            1.05,
            0.70,
            e.colors['dark'],
            False,
            font_path=Path(__file__).parent / 'fonts/GXUDiningSans.ttf',
            flat=not e.detail,
        )
        e.glazing.extend(glyph)
    if e.detail:
        e.glazing.ellipsoid(
            -10.48, -4.80, z + 0.08, 0.32, 0.048, 0.34, e.colors['beiCap'], 16, 8
        )
        for offset in (-0.10, 0.10):
            e.trim(5.98, 4.80, z + offset, 1.53, 0.034, 0.055, 'beiCap')


def east_front(e):
    finishes(e)
    half, span, floor = 14.26, 4.65, 4.468
    for level in (1, 2, 3):
        top = 0.311 + level * floor
        if level == 1:
            panel_edge(e, 2 * half, span, top - 1.908, top - 0.862, top)
        else:
            e.box(0, span / 2, top - 0.30, 2 * half, span, 0.60, 'beiCap')
        for dz in (0.16, 0.44, 0.71, 1.11):
            e.box(0, span - 0.06, top + dz, 2 * half, 0.062, 0.058, 'beiRail')
        for i in range(15):
            e.box(
                half * (i / 7 - 1),
                span - 0.06,
                top + 0.56,
                0.066,
                0.075,
                1.13,
                'beiRail',
            )
        for hand in (-1, 1):
            for x in (4.6, 13.3):
                e.box(hand * x, 3.53, top - floor / 2, 0.55, 0.57, floor, 'beiConcrete')
            for x in (4.4, 11.5):
                e.pane(
                    hand * x, 0.14, top - floor + 0.36, 5.65, 2.90, 4, glass='beiWindow'
                )
    east_sign(e, 0.311 + floor + 0.49)
    for hand in (-1, 1):
        # Walkway-side raised bed and short metal barrier, visible again in 2024.
        e.box(hand * 18.35, 3.26, 0.27, 6.75, 1.60, 0.54, 'beiCap')
        e.box(hand * 18.35, 3.26, 0.54, 6.58, 1.46, 0.075, 'stone')
        if e.detail:
            for i in range(8):
                x = hand * (15.43 + i * 0.84)
                e.glazing.ellipsoid(
                    x, -3.22, 0.84, 0.66, 0.65, 0.44, e.colors['beiHedge'], 10, 6
                )
            for i in range(6):
                x = hand * (15.7 + i * 1.00)
                e.glazing.ellipsoid(
                    x, -3.78, 0.70, 0.55, 0.32, 0.22, e.colors['beiLeaf'], 10, 6
                )
        for post in (12.8, 14.55, 16.3):
            e.box(hand * post, 5.08, 0.56, 0.055, 0.065, 1.10, 'beiRail')
        for h in (0.40, 0.76, 1.08):
            e.box(hand * 14.55, 5.08, h, 3.54, 0.06, 0.064, 'beiRail')
        for base in (0.55, 5.00, 9.47, 13.90):
            e.pane(hand * 17.62, 0.16, base, 6.4, 3.58, 4, sash=True, glass='beiWindow')
        edge = e.length / 2
        e.box(
            hand * (edge + 20.70) / 2,
            1.23,
            e.height / 2,
            edge - 20.70,
            2.46,
            e.height,
            'beiConcrete',
        )
        e.box(hand * (edge + 20.70) / 2, 2.5, 0.27, edge - 20.70, 0.07, 0.54, 'stone')
        for bottom in (0.62, 5.44, 10.0, 14.55):
            glazed_stack(e, hand * 27.0, 2.55, 4.35, bottom, 3.57)
        for level in range(3):
            z = 0.311 + level * floor
            mid = 1.92 if level == 1 else 1.85
            slab = 0.68 if level == 1 else 0.34
            outer = 2.475
            start = hand * (13.70 if level == 1 else 12.6)
            turn = hand * (17.36 if level == 0 else 17.02)
            end = hand * 20.74
            stair_flight(e, start, turn, outer, 1.16, z, z + mid, level < 2, slab)
            stair_flight(e, turn, start, outer - 1.19, 1.16, z + mid, z + floor, False)
            e.box(
                (end + turn) / 2,
                outer / 2,
                z + mid - slab / 2,
                abs(end - turn),
                outer,
                slab,
                'beiConcrete',
            )
            height = 1.24 if level < 2 else 0.32
            e.box(
                (end + turn) / 2,
                outer - 0.08,
                z + mid + height / 2,
                abs(end - turn),
                0.16,
                height,
                'beiConcrete',
            )
            if level == 2:
                for h in (0.55, 0.90):
                    e.box(
                        (end + turn) / 2,
                        outer,
                        z + mid + h,
                        abs(end - turn),
                        0.055,
                        0.052,
                        'beiRail',
                    )
            e.box(start, outer / 2, z + floor - 0.13, 2.8, outer, 0.26, 'beiConcrete')
        for z in (
            1.52,
            3.18,
            4.82,
            6.46,
            8.13,
            9.78,
            11.42,
            13.07,
            14.73,
            16.38,
            18.02,
        ):
            e.box(hand * 23.4, 2.48, z, 5.40, 0.022, 0.020, 'beiFascia')
    for depth, h in [(5.65, 0.16), (5.35, 0.311)]:
        e.box(0, depth / 2, h / 2, 2 * half, depth, h, 'beiTread')
