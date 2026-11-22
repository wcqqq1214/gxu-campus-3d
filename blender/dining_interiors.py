"""Photographed indoor dining entrances, independent of the exterior wall finish."""

import math
from pathlib import Path

from geometry import MATERIALS, Mesh, material
from south_gate import inscription

DINING_SANS = Path(__file__).parent / 'fonts/GXUDiningSans.ttf'


def interior_finish(c, key, rgb, roughness, metal=0):
    if key not in c:
        c[key] = material(key, rgb, roughness, metal)
    return c[key]


def warm_lamp(c):
    if 'diningLamp' not in c:
        idx = interior_finish(c, 'diningLamp', (0.96, 0.74, 0.39), 0.34)
        shader = MATERIALS[idx].node_tree.nodes.get('Principled BSDF')
        shader.inputs['Emission Color'].default_value = (1, 0.67, 0.33, 1)
        shader.inputs['Emission Strength'].default_value = 0.85
    return c['diningLamp']


def beiyuan_entry(c, detail):
    m = Mesh()
    # The two-level sign and glass doors look into the hall from the indoor corridor.
    wine = interior_finish(c, 'beiyuanMaroon', (0.083, 0.023, 0.028), 0.71)
    gold = interior_finish(c, 'beiyuanSignCream', (0.77, 0.58, 0.29), 0.59)
    ink = interior_finish(c, 'diningSignInk', (0.029, 0.022, 0.020), 0.46)
    m.box(0, 1.65, -0.04, 11, 11, 0.08, c['white'])
    m.box(0, 0, 3.56, 9.0, 0.28, 1.44, wine)
    if 'diningDoorGlass' not in c:
        idx = interior_finish(c, 'diningDoorGlass', (0.42, 0.56, 0.53), 0.19)
        shader = MATERIALS[idx].node_tree.nodes.get('Principled BSDF')
        shader.inputs['Alpha'].default_value = 0.22
        MATERIALS[idx].diffuse_color = (0.42, 0.56, 0.53, 0.22)
    # Clipped corners, ochre plaque, dark lettering and a separate red floor marker.
    for depth, scale, finish in [(-0.154, 1.012, c['wood']), (-0.174, 1.0, gold)]:
        corners = [
            (-2.58, 0.37),
            (-2.65, 0.29),
            (-2.65, -0.29),
            (-2.58, -0.37),
            (2.58, -0.37),
            (2.65, -0.29),
            (2.65, 0.29),
            (2.58, 0.37),
        ]
        m.face(
            [(x * scale * 0.94, depth, 3.56 + h * scale * 1.081) for x, h in corners],
            finish,
        )
    # The four block letters have different widths on the clipped ochre plaque.
    for char, x, width in [
        ('北', -1.62, 0.64),
        ('苑', -0.71, 0.64),
        ('餐', 0.23, 0.64),
        ('厅', 1.15, 0.62),
    ]:
        glyph = inscription(
            char,
            0,
            -0.20,
            3.56,
            0.83,
            0.65,
            ink,
            False,
            flat=not detail,
            font_path=DINING_SANS,
            stroke_offset=0.012,
        )
        cast = max(v[0] for v in glyph.v) - min(v[0] for v in glyph.v)
        glyph.v = [(x + u * width / cast, v, h) for u, v, h in glyph.v]
        m.extend(glyph)
    m.box(1.87, -0.21, 3.56, 0.26, 0.06, 0.55, c['gateRed'])
    for char, h in [('二', 3.68), ('楼', 3.45)]:
        m.extend(
            inscription(
                char,
                1.87,
                -0.25,
                h,
                0.18,
                0.18,
                c['white'],
                False,
                flat=not detail,
                font_path=DINING_SANS,
            )
        )
    for x in (-4.44, -3.52, -1.12, 1.18, 3.50, 4.50):
        m.box(x, 0, 1.42, 0.085, 0.14, 2.84, c['metal'])
    # Narrow fixed sidelights and two pairs of doors opening towards the hall.
    for side in (-1, 1):
        x = 4.01 if side > 0 else -3.99
        width = 0.98 if side > 0 else 0.86
        m.box(x, 0, 1.55, width, 0.055, 2.50, c['diningDoorGlass'])
        m.box(x, -0.032, 0.15, width, 0.12, 0.30, c['white'])
        for h in (0.28, 1.30, 2.80):
            m.box(x, -0.063, h, width, 0.07, 0.055, c['metal'])
        if detail:
            for dx in (-0.26, -0.09, 0.09, 0.26):
                m.box(x + dx, 0.018, 0.78, 0.018, 0.030, 0.92, c['metal'])
            m.box(
                x, -0.074, 1.93 if side > 0 else 2.36, 0.49, 0.018, 0.52, c['blueRoof']
            )
            for line in range(4):
                m.box(
                    x,
                    -0.087,
                    (1.80 if side > 0 else 2.23) + line * 0.079,
                    0.31,
                    0.012,
                    0.017,
                    c['white'],
                )
        for hinge, direction in [(1.18, 1), (3.49, -1)]:
            length = 1.16
            dx = direction * side * length * math.cos(math.radians(78))
            dy = length * math.sin(math.radians(78))
            m.box(
                side * hinge + dx / 2,
                dy / 2,
                1.40,
                length,
                0.04,
                2.75,
                c['diningDoorGlass'],
                math.atan2(dy, dx),
            )
            if detail:
                for h in (0.15, 1.46, 2.74):
                    m.line(
                        (side * hinge, -0.025, h),
                        (side * hinge + dx, dy - 0.025, h),
                        0.026 if h != 1.46 else 0.049,
                        wine if h == 1.46 else c['metal'],
                    )
                m.line(
                    (side * hinge + dx, dy, 0.09),
                    (side * hinge + dx, dy, 2.74),
                    0.022,
                    c['metal'],
                )
        m.box(side * 2.85, -1.08, 0.018, 2.02, 1.80, 0.036, wine)
    m.box(0, -0.015, 2.825, 9.0, 0.16, 0.10, c['metal'])
    m.box(0, 0.02, 0.024, 7.06, 0.33, 0.048, c['metal'])
    m.box(0, -0.018, 4.72, 11.0, 0.34, 0.90, c['white'])
    for x in (-2.18, 2.20):
        m.box(x, 3.84, 1.54, 0.34, 0.48, 3.08, c['white'])
    if detail:
        # Through the open leaves the reference shows a bright central aisle with
        # parallel ceiling lights, square columns and dark dining tables on both sides.
        m.box(0, 3.3, 2.99, 8.1, 6.75, 0.12, c['white'])
        for x in (-1.15, -0.38, 0.38, 1.15):
            m.box(x, 3.38, 2.91, 0.12, 6.54, 0.03, c['white'])
        m.box(0, 6.56, 1.43, 8.09, 0.13, 2.86, c['white'])
        for x in (-2.60, 0, 2.6):
            m.box(x, 6.44, 1.26, 2.31, 0.09, 0.85, c['wood'])
            m.box(x, 6.36, 1.70, 2.40, 0.28, 0.065, c['metal'])
            m.box(x, 6.41, 2.02, 2.29, 0.08, 0.26, wine)
        for x in (-2.80, 2.80):
            for y in (2.75, 4.2, 5.65):
                m.box(x, y, 0.76, 1.32, 0.72, 0.055, c['wood'])
                for dx in (-0.51, 0.51):
                    m.box(x + dx, y, 0.38, 0.055, 0.49, 0.76, c['dark'], bottom=False)
        # The circular emblem is left of the plaque; a two-row board is on its right.
        m.ellipsoid(-3.59, -0.157, 3.72, 0.216, 0.025, 0.216, c['metal'], 20, 12)
        m.ellipsoid(-3.59, -0.182, 3.72, 0.156, 0.016, 0.156, ink, 16, 12)
        m.box(3.64, -0.164, 3.10, 1.11, 0.035, 0.36, ink)
        for row in range(2):
            for col in range(5):
                m.box(
                    3.19 + col * 0.22,
                    -0.192,
                    3.02 + row * 0.16,
                    0.16,
                    0.018,
                    0.076,
                    gold,
                )
        for x in (-2.15, 2.18):
            for y in (2.75, 4.40, 5.95):
                m.box(x, y, 1.22, 0.43, 0.46, 2.44, c['white'])
                m.box(x, y - 0.245, 1.72, 0.24, 0.031, 0.33, c['timeLetter'])
        for x in (-0.85, 0, 0.85):
            m.box(x, 3.20, 2.89, 0.105, 5.96, 0.025, warm_lamp(c))
        for x in (-1.12, 1.12):
            m.box(x + 0.07, -0.13, 1.12, 0.035, 0.09, 0.48, c['metal'])
        for x in (-3.86, 3.86):
            m.box(x, -0.10, 1.65, 0.30, 0.03, 0.46, c['blueRoof'])
        for y in (-3.58, -2.33, -1.08, 0.17, 1.42):
            m.box(0, y, 0.006, 10.9, 0.012, 0.009, c['metal'])
        for x in (-3, -1.5, 0, 1.5, 3):
            m.box(x, -0.9, 0.004, 0.012, 5.2, 0.008, c['metal'])
    return m


def tower_cafe(c, detail):
    m = Mesh()
    oak = interior_finish(c, 'cafeOak', (0.31, 0.112, 0.033), 0.60)
    shadow = interior_finish(c, 'cafeShadow', (0.045, 0.026, 0.018), 0.63)
    lamp = warm_lamp(c)
    m.box(0, 0, 2.88, 6.7, 0.26, 1.04, oak)
    if detail:
        for i in range(93):
            m.box((i - 46) * 0.071, -0.140, 2.88, 0.012, 0.022, 1.02, shadow)
    # Warm outline around individually spaced dark faces, above the black window header.
    for i, char in enumerate('老水塔咖啡'):
        x = -0.87 + i * 0.66
        m.extend(
            inscription(
                char,
                x,
                -0.206,
                2.68,
                0.60,
                0.40,
                shadow,
                False,
                flat=not detail,
                font_path=DINING_SANS,
                outline=(0.023, lamp),
            )
        )
    en = inscription(
        'Old Water Tower Café',
        0,
        -0.176,
        0,
        3.3,
        0.20,
        oak,
        False,
        flat=not detail,
        font_path=DINING_SANS,
        outline=(0.008, lamp),
    )
    xmin, xmax = min(u for u, _, _ in en.v), max(u for u, _, _ in en.v)
    en.v = [
        (x * 2.22 / (xmax - xmin) + 0.18 * h + 0.02, y, 3.08 + h) for x, y, h in en.v
    ]
    m.extend(en)
    m.box(0, -0.12, 2.33, 6.7, 0.18, 0.11, shadow)
    for x in (-2.65, -1.33, 0, 1.33, 2.65):
        m.box(x, 0.23, 1.17, 1.27, 0.08, 2.33, c['glass'])
        m.box(x - 0.64, 0.16, 1.17, 0.07, 0.10, 2.34, c['dark'])
    # The bar looks through a black-framed transom and a pair of tall casements.
    for x in (-1.72, -0.96, -0.11, 0.80, 1.82):
        m.box(x, 0.102, 1.15, 0.078, 0.10, 2.30, shadow)
    m.box(0, 0.102, 1.98, 5.55, 0.10, 0.093, shadow)
    m.box(0, -0.46, 0.385, 5.53, 0.72, 0.77, c['wood'])
    m.box(0, -0.46, 0.795, 5.61, 0.79, 0.09, c['dark'])
    for x in (-0.775, 1.035):
        m.cylinder(x, -0.42, 2.11, 0.016, 0.58, c['metal'], 8)
        m.ellipsoid(x, -0.42, 1.774, 0.142, 0.142, 0.142, lamp, 16, 10)
    if detail:
        # Four pale beverage dispensers and their two-tier rack are visible through the bar.
        for x in (-1.035, -0.755, -0.475, -0.195):
            m.cylinder(x, -0.42, 1.00, 0.128, 0.31, c['paleRoof'], 16)
            m.cylinder(x, -0.42, 1.171, 0.135, 0.042, shadow, 16)
            m.box(x, -0.552, 1.00, 0.035, 0.07, 0.095, shadow)
        # Only the top of the dispenser tray clears the 0.84 m counter surface.
        m.face(
            [
                (-1.23, -0.625, 0.843),
                (-0.01, -0.625, 0.843),
                (-0.01, -0.155, 0.843),
                (-1.23, -0.155, 0.843),
            ],
            c['metal'],
        )
        for x in (-1.18, -0.06):
            m.box(x, -0.39, 0.81, 0.035, 0.42, 0.12, c['metal'])
        m.box(1.42, -0.38, 1.04, 0.88, 0.38, 0.39, shadow)
        m.box(1.42, -0.59, 1.06, 0.77, 0.06, 0.080, c['metal'])
        for x in (0.64, 2.30):
            m.cylinder(x, -0.42, 1.02, 0.11, 0.34, c['metal'], 12)
    return m
