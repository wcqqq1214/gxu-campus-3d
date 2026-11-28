"""West entrance of Dongyuan, reconstructed from the May 2016 courtyard panoramas."""

import math
from pathlib import Path

from geometry import material, tile_material
from south_gate import inscription

LANDING = 0.32
FIRST_STEP = 0.178
LANDING_DEPTH = 1.897
STEP_DEPTH = 2.09
SOFFIT = 3.152
CANOPY_TOP = 3.99
FONT = Path(__file__).parent / 'fonts/GXUDiningSans.ttf'


def finishes(e):
    tile_material(e.colors, 'dongWestTile', 'dong-west-tile.png', (0.66, 0.56, 0.47))
    for name, rgb, roughness, metal in (
        ('dongGlass', (0.105, 0.14, 0.155), 0.22, 0.40),
        ('dongNorthLight', (0.245, 0.248, 0.245), 0.25, 0.22),
        ('dongAperture', (0.055, 0.056, 0.053), 0.68, 0.04),
        ('dongShadow', (0.035, 0.039, 0.038), 0.82, 0.02),
        ('dongCurtain', (0.40, 0.24, 0.25), 0.80, 0),
        ('dongSash', (0.57, 0.56, 0.52), 0.40, 0.50),
        ('dongRose', (0.56, 0.26, 0.23), 0.70, 0),
        ('dongGranite', (0.30, 0.272, 0.239), 0.42, 0.09),
        ('dongNosing', (0.57, 0.53, 0.46), 0.51, 0.06),
        ('dongReveal', (0.255, 0.199, 0.159), 0.61, 0.10),
        ('dongRed', (0.46, 0.042, 0.043), 0.46, 0.23),
        ('dongGold', (0.73, 0.47, 0.17), 0.30, 0.55),
        ('dongStrips', (0.039, 0.045, 0.032), 0.145, 0.43),
        ('dongUnit', (0.67, 0.64, 0.55), 0.66, 0.11),
    ):
        if name not in e.colors:
            e.colors[name] = material(name, rgb, roughness, metal)


def pane(e, left, right, bottom, top, cols, *, grille=False, ribbon=0):
    w, h = right - left, top - bottom
    x, z = (left + right) / 2, (bottom + top) / 2
    g, c = e.glazing, e.colors
    # Sheet glass sits behind the sliding sashes, inset from the projecting stone sill.
    g.box(x, -0.115, z, w, 0.030, h, c['dongShadow' if top < 3.1 else 'dongGlass'])
    e.box(x, 0.138, bottom - 0.053, w + 0.24, 0.275, 0.10, 'paleRoof')
    if not e.detail:
        return
    pitch = w / cols
    for i in range(cols):
        u = left + (i + 0.5) * pitch
        if ribbon == 3 and i % 5 in (1, 2, 4):
            g.box(u, -0.137, z - 0.11, pitch - 0.05, 0.013, h - 0.38, c['dongCurtain'])
        if ribbon == 2 and i in (3, 5, 9, 11, 15, 17):
            g.box(u, -0.141, z - 0.15, pitch - 0.042, 0.014, h - 0.40, c['dongShadow'])
    for i in range(cols + 1):
        g.box(left + i * pitch, -0.165, z, 0.042, 0.048, h, c['dongSash'])
    for ratio in (0.018, 0.77, 0.985):
        g.box(x, -0.171, bottom + ratio * h, w, 0.049, 0.040, c['dongSash'])
    if ribbon:
        g.box(x, -0.17, bottom + h * 0.866, w, 0.05, 0.037, c['dongSash'])
        # Two central braced bays stay visible even when the sliding lights are open.
        for i in (8, 9):
            a, b = left + i * pitch, left + (i + 1) * pitch
            for lo, hi in ((bottom + 0.08, top - 0.38), (top - 0.38, bottom + 0.08)):
                g.line((a, -0.177, lo), (b, -0.177, hi), 0.014, c['dongSash'])
    if grille:
        n = max(3, round(w / 0.146))
        for i in range(1, n):
            g.box(left + w * i / n, -0.206, z, 0.019, 0.022, h - 0.04, c['dongSash'])
        for ratio in (0.35, 0.68):
            g.box(x, -0.211, bottom + h * ratio, w, 0.027, 0.025, c['dongSash'])


def upper_window(e, x, z, width, height):
    # Both archive views show an undivided transom over two sliding lights.
    # The tiled face is at 0.045; the rear track sits inside that face.
    left, right = x - width / 2, x + width / 2
    head = z + height
    transom = z + height * 0.73
    nose = 0.148
    back = 0.014
    for u in (left - 0.034, right + 0.034):
        e.box(u, nose / 2, z + height / 2, 0.068, nose, height, 'paleRoof')
    e.box(x, nose / 2, head + 0.034, width + 0.136, nose, 0.068, 'paleRoof')
    e.box(x, 0.095, z - 0.035, width + 0.17, 0.19, 0.07, 'paleRoof')

    # Three separate lights, with the nearer sliding leaf on its own track.
    for lo, hi, sill, top, out in (
        (left, right, transom, head, back),
        (left, x, z, transom, back),
        (x, right, z, transom, 0.041),
    ):
        e.glazing.face(
            [(lo, -out, sill), (hi, -out, sill), (hi, -out, top), (lo, -out, top)],
            e.colors['dongNorthLight'],
        )
    if e.detail:
        e.trim(x, 0.059, transom, width, 0.04, 0.045, 'dongSash')
        e.trim(x, 0.055, (z + transom) / 2, 0.048, 0.055, transom - z, 'dongSash')


def north_window(e, x, z, width, height):
    # The dark aperture rim is coplanar at the front. The glass and sliding rails
    # are inset behind the narrow jambs; their reveals read strongly from the corner.
    l, r = x - width / 2, x + width / 2
    top = z + height
    g, c = e.glazing, e.colors
    rim = c['dongAperture']
    g.face([(l, -0.175, z), (r, -0.175, z), (r, -0.175, top), (l, -0.175, top)], rim)
    glass = c['dongGlass']
    g.face(
        [
            (l + 0.048, -0.180, z + 0.055),
            (r - 0.048, -0.180, z + 0.055),
            (r - 0.048, -0.180, top - 0.055),
            (l + 0.048, -0.180, top - 0.055),
        ],
        glass,
    )
    for u in (l - 0.046, r + 0.046):
        e.box(u, 0.197, z + height / 2, 0.092, 0.142, height + 0.13, 'paleRoof')
    e.box(x, 0.19, top + 0.034, width + 0.18, 0.13, 0.068, 'paleRoof')
    if e.detail:
        g.box(x, -0.212, z + height * 0.46, 0.047, 0.044, height * 0.88, c['dongSash'])
        g.box(x, -0.215, z + height * 0.73, width - 0.06, 0.047, 0.046, c['dongSash'])


def portal(e, left, right, top, folding):
    width = right - left
    x = (right + left) / 2
    # Granite jambs frame two folding security gates and the central strip curtain.
    for u in (left - 0.135, right + 0.135):
        e.box(u, 0.15, (LANDING + top) / 2, 0.27, 0.22, top - LANDING, 'dongReveal')
    e.box(x, 0.15, top + 0.105, width + 0.54, 0.22, 0.21, 'dongReveal')
    g, c = e.glazing, e.colors
    g.box(x, -0.116, (LANDING + top) / 2, width, 0.028, top - LANDING, c['dongShadow'])
    if not folding:
        g.box(x, -0.154, 2.649, width - 0.025, 0.040, 0.506, c['dongRed'])
        if e.detail:
            for text, u, z, w, h in [
                ('家', x - 1.03, 2.65, 0.38, 0.38),
                ('的温暖和味道', x + 0.25, 2.67, 1.70, 0.23),
            ]:
                g.extend(inscription(text, u, -0.186, z, w, h, c['dongGold'], False))
        if e.detail:
            for u in (left + 0.15, right - 0.15):
                g.box(u, -0.193, 1.35, 0.24, 0.046, 2.04, c['dongSash'])
                for j in range(7):
                    g.box(
                        u + (j - 3) * 0.030,
                        -0.221,
                        1.35,
                        0.009,
                        0.018,
                        2.04,
                        c['dongReveal'],
                    )
            for z in (2.40, 2.894):
                g.box(x, -0.186, z, width - 0.016, 0.015, 0.022, c['dongGold'])
        for i in range(16 if e.detail else 2):
            n = 16 if e.detail else 2
            u = left + width * i / n
            g.face(
                [
                    (u, -0.144, LANDING),
                    (u + width / n - 0.009, -0.175, LANDING + 0.018),
                    (u + width / n, -0.162, 2.365),
                    (u, -0.162, 2.365),
                ],
                c['dongStrips'],
            )
        for u in (left + 0.10, x, right - 0.10):
            g.box(u, -0.186, 1.351, 0.066, 0.058, 2.06, c['dongSash'])
        return
    if e.detail:
        half_cells = 20
        for j in range(half_cells + 1):
            u = left + j * width / half_cells
            g.box(
                u,
                -0.168,
                (LANDING + top) / 2,
                0.028,
                0.049,
                top - LANDING,
                c['dongSash'],
            )
        for z in (0.57, 1.18, 1.79, 2.50):
            for j in range(half_cells):
                u = left + j * width / half_cells
                rise = 0.17 if j % 2 == 0 else -0.17
                for dz in (rise, -rise):
                    g.line(
                        (u, -0.184, z - dz),
                        (u + width / half_cells, -0.184, z + dz),
                        0.013,
                        c['dongSash'],
                        n=4,
                    )
    for z in (0.37, 2.39, top - 0.03):
        g.box(x, -0.19, z, width, 0.07, 0.062, c['dongSash'])


def cast_letter(e, char, x, y, z, width, height, finish):
    glyph = inscription(
        char,
        0,
        y,
        0,
        2,
        height,
        e.colors[finish],
        False,
        flat=not e.detail,
        font_path=FONT,
    )
    span = max(v[0] for v in glyph.v) - min(v[0] for v in glyph.v)
    glyph.v = [(x + u * width / span, v, z + h) for u, v, h in glyph.v]
    e.glazing.extend(glyph)


def canopy_depth(x):
    return 2.123 - 0.319 * (x / 10.25) ** 2


def canopy(e):
    c = e.colors
    for j in range(10):
        a, b = -10.28 + j * 2.056, -10.28 + (j + 1) * 2.056
        da, db = canopy_depth(a), canopy_depth(b)
        ring = [(a, -da), (b, -db), (b, 0), (a, 0)]
        for z, pts, finish in (
            (CANOPY_TOP, ring, 'paleRoof'),
            (SOFFIT, reversed(ring), 'dongReveal'),
        ):
            e.structure.face([(*v, z) for v in pts], c[finish])
        for v, w in zip(ring, ring[1:] + ring[:1]):
            corners = [(*v, SOFFIT), (*w, SOFFIT), (*w, CANOPY_TOP), (*v, CANOPY_TOP)]
            span = math.dist(v, w)
            e.structure.face(
                corners,
                c['dongWestTile'],
                [
                    (a / 1.5, 0),
                    ((a + span) / 1.5, 0),
                    ((a + span) / 1.5, (CANOPY_TOP - SOFFIT) / 1.5),
                    (a / 1.5, (CANOPY_TOP - SOFFIT) / 1.5),
                ],
            )
        if e.detail:
            e.glazing.line(
                (a, -da - 0.025, CANOPY_TOP - 0.085),
                (b, -db - 0.025, CANOPY_TOP - 0.085),
                0.033,
                c['dongReveal'],
            )
    for u in (-8.6, -5.3, -1.8, 1.8, 5.3, 8.6):
        e.box(u, 0.94, SOFFIT - 0.095, 0.20, 1.88, 0.19, 'paleRoof')
    for char, u, z, w, h in [
        ('东', -4.18, 5.038, 0.89, 1.032),
        ('苑', -1.455, 5.037, 0.885, 1.073),
        ('餐', 1.324, 4.984, 0.931, 1.099),
        ('厅', 4.105, 4.9, 0.821, 1.014),
    ]:
        depth = canopy_depth(u) - 0.19
        cast_letter(e, char, u, -depth, z, w, h, 'dongRed')
        if e.detail:
            for dx in (-0.23, 0.23):
                e.glazing.line(
                    (u + dx, -depth + 0.10, 4.02),
                    (u + dx, -depth + 0.10, 4.96),
                    0.022,
                    c['dongSash'],
                )
    if e.detail:
        for caption, center in [
            ('自选快餐', -3.5),
            ('风味小吃', -1.18),
            ('精品美食', 1.18),
            ('宴席包厢', 3.5),
        ]:
            for i, char in enumerate(caption):
                u = center + (i - 1.5) * 0.44
                e.glazing.extend(
                    inscription(
                        char,
                        u,
                        -canopy_depth(u) - 0.033,
                        3.57,
                        0.23,
                        0.28,
                        c['dongGold'],
                        False,
                    )
                )


def landing(e):
    span = 29.24
    for depth, height in [(STEP_DEPTH, FIRST_STEP), (LANDING_DEPTH, LANDING)]:
        e.box(0, depth / 2, height / 2, span, depth, height, 'dongGranite')
        if e.detail:
            e.glazing.box(
                0,
                -depth - 0.004,
                height - 0.012,
                span,
                0.017,
                0.022,
                e.colors['dongNosing'],
            )
    if e.detail:
        for i in range(-15, 16):
            e.glazing.box(
                i * 0.91,
                -LANDING_DEPTH / 2,
                LANDING + 0.001,
                0.009,
                LANDING_DEPTH,
                0.003,
                e.colors['dongReveal'],
            )
            e.glazing.box(
                i * 0.91 + 0.45,
                -(LANDING_DEPTH + STEP_DEPTH) / 2,
                FIRST_STEP + 0.001,
                0.009,
                STEP_DEPTH - LANDING_DEPTH,
                0.003,
                e.colors['dongReveal'],
            )


def window_units(e):
    # A close-set line of outdoor units sits against the barred second-storey ribbon.
    for x, z in [
        *((-9.1 + i * 1.16, 4.37) for i in range(17)),
        (-8, 10.59),
        (7.48, 10.59),
    ]:
        e.box(x, 0.64, z, 0.85, 0.50, 0.58, 'dongUnit')
        if e.detail:
            e.glazing.face(
                [
                    (
                        x - 0.15 + 0.20 * math.cos(a * math.tau / 16),
                        -0.897,
                        z + 0.20 * math.sin(a * math.tau / 16),
                    )
                    for a in range(16)
                ],
                e.colors['dongReveal'],
            )
            for j in range(-3, 4):
                h = j * 0.044
                w = 2 * math.sqrt(0.20**2 - h * h)
                e.glazing.box(
                    x - 0.15, -0.905, z + h, w, 0.013, 0.015, e.colors['dongUnit']
                )


def west_front(e):
    finishes(e)
    half = e.length / 2
    e.cladding(-half, half, 0, e.height, 0.045, 'dongWestTile', repeat=1.5)
    # A raised parapet with a shallow central arch and two glazed corner shafts.
    profile = [
        (-half, 15.30),
        (-half + 1.35, 16.76),
        (-14.0, 16.76),
        (-13.5, 14.83),
        (-6.8, 14.83),
        (-4.1, 15.73),
        (-1.8, 16.06),
        (0, 16.15),
        (1.8, 16.06),
        (4.1, 15.73),
        (6.8, 14.83),
        (13.5, 14.83),
        (14.0, 16.76),
        (half - 1.35, 16.76),
        (half, 15.30),
    ]
    for (a, h), (b, k) in zip(profile, profile[1:]):
        for y in (-0.046, 0.27):
            pts = [(a, y, e.height), (b, y, e.height), (b, y, k), (a, y, h)]
            e.structure.face(
                pts if y < 0 else pts[::-1],
                e.colors['dongWestTile'],
                [(u / 1.5, z / 1.5) for u, _, z in (pts if y < 0 else pts[::-1])],
            )
        e.structure.face(
            [(a, -0.046, h), (b, -0.046, k), (b, 0.27, k), (a, 0.27, h)],
            e.colors['paleRoof'],
        )
    for x, h in [profile[0], profile[-1]]:
        e.structure.face(
            [(x, -0.046, e.height), (x, 0.27, e.height), (x, 0.27, h), (x, -0.046, h)],
            e.colors['paleRoof'],
        )
    for z in (14.96, 15.24, 15.52):
        e.box(0, 0.18, z, 1.32, 0.43, 0.13, 'paleRoof')
    for i, (l, r, lo, hi) in enumerate(
        [
            (-9.47, 9.39, 4.482, 6.501),
            (-9.426, 9.302, 8.014, 9.753),
            (-9.472, 9.27, 11.251, 13.031),
        ],
        1,
    ):
        pane(e, l, r, lo, hi, 20, grille=i == 1, ribbon=i)
    for z in (7.20, 10.48, 13.55):
        e.box(0, 0.067, z, 26.75, 0.047, 0.25, 'dongRose')
    for hand in (-1, 1):
        for l, r, b, t in [
            (10.94, 12.18, 4.105, 6.377),
            (10.88, 12.11, 7.502, 9.797),
            (10.92, 12.04, 10.869, 13.119),
            (10.314, 12.883, 1.188, 3.002),
        ]:
            l, r = sorted((l * hand, r * hand))
            pane(e, l, r, b, t, 2, grille=b < 5)
        # Full-height glazed inset at each return is independent of the narrow window stack.
        l, r = sorted((14.47 * hand, 16.06 * hand))
        for i in range(4):
            pane(e, l, r, 1.1 + i * 3.70, 4.72 + i * 3.70, 2, grille=i == 1)
        for u in (l - 0.21, r + 0.21):
            e.box(u, 0.19, 8.34, 0.42, 0.40, 16.68, 'paleRoof')
        for l, r, b, t in [
            (1.908, 2.838, 1.181, 2.899),
            (3.725, 4.651, 1.174, 2.919),
            (8.395, 9.306, 1.223, 2.937),
        ]:
            l, r = sorted((hand * l, hand * r))
            pane(e, l, r, b, t, 1, grille=True)
        # Tiled trough just outside the canopy, with a thin rim and two open supports.
        u = hand * 11.7
        for dx in (-1.32, 1.32):
            e.box(u + dx, 0.34, 0.58, 0.12, 0.65, 0.52, 'white')
        e.box(u, 0.34, 0.91, 3.5, 0.67, 0.16, 'white')
        for out in (0.05, 0.67):
            e.box(u, out, 1.05, 3.50, 0.065, 0.21, 'white')
    if e.detail:
        e.glazing.box(3.28, -0.17, 1.59, 0.37, 0.10, 0.43, e.colors['dongShadow'])
        for z in (1.54, 1.60):
            e.glazing.box(3.28, -0.224, z, 0.16, 0.01, 0.014, e.colors['dongSash'])
    portal(e, -8.092, -4.972, 2.989, True)
    portal(e, -1.513, 1.515, 2.916, False)
    portal(e, 4.997, 8.009, 2.938, True)
    canopy(e)
    landing(e)
    window_units(e)
