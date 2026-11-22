"""South portico and stepped returns of Cuiyuan. Dimensions estimated from photographs."""

from geometry import material
from south_gate import inscription


def finishes(e):
    palette = {
        'cuiStone': ((0.65, 0.585, 0.54), 0.68, 0.04),
        'cuiTrim': ((0.79, 0.76, 0.70), 0.50, 0.10),
        'cuiJoint': ((0.39, 0.365, 0.34), 0.80, 0),
        'cuiSafetyStripe': ((0.365, 0.033, 0.035), 0.6, 0),
        'cuiSash': ((0.29, 0.29, 0.26), 0.38, 0.42),
        'cuiGlass': ((0.138, 0.154, 0.14), 0.19, 0.30),
        'cuiCurtain': ((0.54, 0.52, 0.41), 0.87, 0),
        'cuiCurtainFold': ((0.40, 0.40, 0.31), 0.81, 0),
        'cuiGold': ((0.82, 0.61, 0.23), 0.30, 0.60),
        'cuiCanopy': ((0.49, 0.50, 0.51), 0.39, 0.43),
        'cuiDoor': ((0.051, 0.057, 0.053), 0.21, 0.25),
        'cuiTread': ((0.46, 0.44, 0.40), 0.65, 0.02),
    }
    for name, (color, roughness, metallic) in palette.items():
        if name not in e.colors:
            e.colors[name] = material(name, color, roughness, metallic)


def window(e, x, width, bottom, top, *, curtains, lights):
    height = top - bottom
    e.box(x, 0.145, bottom + height / 2, width, 0.07, height, 'cuiGlass')
    e.box(x, 0.205, bottom - 0.053, width + 0.12, 0.26, 0.106, 'cuiTrim')
    for side in (-1, 1):
        e.box(
            x + side * width / 2,
            0.196,
            bottom + height / 2,
            0.065,
            0.08,
            height,
            'cuiSash',
        )
    if not e.detail:
        return
    cell = width / lights
    for i in range(lights):
        center = x - width / 2 + cell * (i + 0.5)
        if i:
            e.trim(
                center - cell / 2,
                0.21,
                bottom + height / 2,
                0.054,
                0.07,
                height,
                'cuiSash',
            )
        if curtains:
            # Raised valance, alternating folds and pinched sides behind the sash.
            for hand in (-1, 1):
                a = center + hand * (cell / 2 - 0.035)
                b = center + hand * (0.09 + 0.033 * (i % 3))
                tie = a - hand * cell * 0.16
                e.glazing.face(
                    [
                        (a, -0.185, top - 0.44),
                        (b, -0.185, top - 0.44),
                        (tie, -0.188, bottom + 0.41),
                        (a, -0.185, bottom + 0.12),
                    ],
                    e.colors['cuiCurtain'],
                )
                e.glazing.face(
                    [
                        ((a + b) / 2, -0.189, top - 0.44),
                        (b, -0.189, top - 0.44),
                        (tie, -0.19, bottom + 0.41),
                    ],
                    e.colors['cuiCurtainFold'],
                )
        else:
            for bar in range(1, 7):
                e.trim(
                    center + cell * (bar / 7 - 0.5),
                    0.224,
                    bottom + height / 2,
                    0.015,
                    0.025,
                    height,
                    'cuiSash',
                )
    for fraction in (0.38, 0.70, 0.81) if curtains else (0.30, 0.73, 0.84):
        e.trim(x, 0.225, bottom + height * fraction, width, 0.046, 0.038, 'cuiSash')


def lined_pier(e, x):
    e.box(x, 0.31, 3.84, 0.82, 0.64, 7.68, 'cuiStone')
    if e.detail:
        for row in range(1, 11):
            e.trim(x, 0.634, 0.70 * row, 0.81, 0.012, 0.012, 'cuiJoint')


def lintel(e, width):
    e.box(0, 0.33, 8.687, width, 0.68, 2.03, 'cuiStone')
    e.box(0, 0.41, 9.705, width + 0.20, 0.84, 0.17, 'cuiTrim')
    e.box(0, 0.41, 7.671, width + 0.24, 0.84, 0.25, 'cuiTrim')
    if e.detail:
        count = max(2, round(width / 1.15))
        for i in range(1, count):
            e.trim(
                width * (i / count - 0.5), 0.675, 8.69, 0.014, 0.014, 1.78, 'cuiJoint'
            )


def condensers(e, xs):
    if not e.detail:
        return
    for x in xs:
        e.trim(x, 0.43, 0.80, 0.91, 0.53, 1.20, 'cuiTrim')
        for z in (0.52, 1.08):
            # Fan axes face the courtyard; the feet stand clear of the paving.
            e.glazing.line(
                (x, -0.70, z), (x, -0.72, z), 0.219, e.colors['cuiJoint'], 16
            )
            for i in range(5):
                e.trim(x, 0.73, z + (i - 2) * 0.072, 0.34, 0.016, 0.013, 'cuiSash')
        for side in (-0.30, 0.30):
            e.trim(x + side, 0.45, 0.10, 0.12, 0.43, 0.20, 'cuiSash')


def doors(e):
    width, bottom, top = 6.35, 0.36, 3.70
    e.box(0, 0.13, (bottom + top) / 2, width, 0.08, top - bottom, 'cuiDoor')
    for hand in (-1, 1):
        # The fixed sidelights and closed leaves reflect more sky than the open aisle.
        e.box(hand * 2.00, 0.182, 1.47, 2.26, 0.026, 2.18, 'cuiGlass')
    cell = width / 8
    for i in range(9):
        x = (i - 4) * cell
        # The central pair was open in the guide and both street viewpoints.
        low = 2.60 if i == 4 else bottom
        e.box(x, 0.21, (top + low) / 2, 0.055, 0.08, top - low, 'cuiSash')
    for z in (2.60, 3.24, top):
        e.box(0, 0.21, z, width, 0.09, 0.065, 'cuiSash')
    for side in (-1, 1):
        e.box(side * 0.85, 0.25, 1.05, 0.040, 0.06, 0.32, 'cuiTrim')
        if e.detail:
            e.trim(side * 2.06, 0.22, 1.29, 1.95, 0.025, 0.046, 'cuiSafetyStripe')


def cui(e):
    finishes(e)
    w = e.length
    e.box(0, 0.045, 3.85, w, 0.09, 7.70, 'cuiStone')
    for x in (-7.24, 0, 7.24):
        width = 6.35 if x == 0 else 6.13
        window(e, x, width, 5.29, 7.45, curtains=True, lights=6)
        if x:
            window(e, x, width, 0.48, 3.66, curtains=False, lights=6)
    for x in (-10.87, -3.67, 3.67, 10.88):
        lined_pier(e, x)
    lintel(e, w)
    for x in (-10.65, -3.63, 3.65, 10.76):
        for dx in (-0.26, 0.26):
            e.box(x + dx, 0.68, 8.70, 0.275, 0.04, 1.58, 'cuiSash')
            if e.detail:
                for j in range(4):
                    e.trim(
                        x + dx, 0.706, 8.77 + j * 0.18, 0.285, 0.02, 0.038, 'cuiTrim'
                    )
    # The cast strokes sit proud of the pale fascia on shallow mounting pins.
    letters = zip(
        '萃苑餐厅',
        (-2.64, -0.95, 0.80, 2.63),
        (8.65, 8.58, 8.61, 8.62),
        (1.02, 1.04, 1.07, 1.00),
        strict=True,
    )
    for char, x, z, width in letters:
        e.box(x, 0.75, z, 0.08, 0.17, 0.08, 'cuiJoint')
        e.glazing.extend(
            inscription(
                char,
                x,
                -0.85,
                z,
                width,
                1.18,
                e.colors['cuiGold'],
                False,
                stroke_offset=0.002,
                flat=not e.detail,
            )
        )

    # Three continuous nosings beneath the deep landing. The lower tread meets the asphalt.
    for out, z in ((4.05, 0.12), (3.84, 0.24), (3.64, 0.36)):
        e.box(0, out / 2, z / 2 - 0.015, 7.23, out, z + 0.03, 'cuiTread')
    doors(e)
    depth, width = 3.70, 7.84
    e.box(0, depth / 2, 4.414, width, depth, 0.77, 'cuiCanopy')
    if e.detail:
        for i in range(1, 7):
            x = width * (i / 7 - 0.5)
            e.trim(x, depth + 0.012, 4.414, 0.018, 0.018, 0.75, 'cuiJoint')
            e.trim(x, depth / 2, 4.023, 0.016, depth, 0.014, 'cuiJoint')
        for x in (-3.65, 3.65):
            e.glazing.line(
                (x, -0.64, 6.76), (x, -3.47, 4.81), 0.030, e.colors['cuiSash']
            )
        for x in (-10.34, 10.40):
            e.glazing.cylinder(x, -0.49, 3.85, 0.067, 7.5, e.colors['cuiTrim'])
    condensers(e, [-9.36, -8.18, -6.95, -5.77, -4.60, 4.94, 8.82, 9.95])


def wing(e, edge):
    """Two-storey bays step back along the mapped wings on both sides of the portico."""
    finishes(e)
    w = e.length
    e.box(0, 0.043, 3.82, w, 0.086, 7.64, 'cuiStone')
    lintel(e, w)
    width = max(0.66, w - 0.84)
    lights = max(2, round(width / 1.06))
    # Looking west from the 2025 forecourt photo, the return window has a
    # deeper head and the broad adjoining bay drops closer to the sill band.
    upper = {
        8: (-0.035, width - 0.25, 5.10, 7.42),
        7: (-0.12, width - 0.33, 5.23, 7.12),
    }.get(edge, (0, width, 5.29, 7.45))
    window(e, *upper, curtains=True, lights=lights)
    window(e, 0, width, 0.45, 3.66, curtains=False, lights=lights)
    for x in (-w / 2 + 0.18, w / 2 - 0.18):
        e.box(x, 0.18, 3.84, 0.35, 0.36, 7.68, 'cuiTrim')
    if w > 6:
        condensers(e, [-w * 0.34, -w * 0.20, w * 0.25])


def upper_court(e, left, right):
    """Exposed face of the taller north block above the south dining rooms."""
    finishes(e)
    span = right - left
    for level in range(4):
        bottom = 9.93 + 3.80 * level
        for i in range(13):
            x = left + span * (i + 0.5) / 13
            width = span / 13 * 0.76
            e.box(x, 0.08, bottom + 1.10, width, 0.18, 2.20, 'cuiDoor')
            e.box(x, 0.21, bottom + 0.49, width, 0.25, 0.98, 'pink')
            if e.detail:
                e.trim(x, 0.29, bottom + 1.27, width, 0.055, 0.046, 'cuiSash')
                for dx in (-0.33, 0.33):
                    e.trim(
                        x + dx * width,
                        0.28,
                        bottom + 1.09,
                        0.035,
                        0.045,
                        0.38,
                        'cuiSash',
                    )
                if i % 2 == 1:
                    for z in (bottom + 0.47, bottom + 1.22):
                        e.trim(x - width * 0.60, 0.27, z, 0.78, 0.48, 0.63, 'cuiTrim')
                        e.glazing.line(
                            (x - width * 0.60, -0.52, z),
                            (x - width * 0.60, -0.54, z),
                            0.21,
                            e.colors['cuiJoint'],
                            12,
                        )
