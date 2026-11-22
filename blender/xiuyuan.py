"""Xiuyuan dining hall, seen from the west forecourt. All distances are in metres."""

import math

from geometry import material
from south_gate import inscription

ARC_HALF = 7.10
WINDOW_BASES = (6.93, 11.03, 15.13)
WINDOW_HEIGHT = 2.484
LANDING = 2.027
LANDING_END = 15.39
LANDING_DEPTH = 5.826
FRONT_HALF = 10.255
RUN = 4.835
RISERS = 16
CANOPY_TOP = 6.173


def arc(x):
    return 0.05 + 1.79 * (1 - (x / ARC_HALF) ** 2)


def solid_band(
    e, left, right, front_left, front_right, back, bottom, top, finish, soffit=None
):
    """Closed trapezoidal slab with a straight rear edge and a faceted front."""
    front = [(left, -front_left), (right, -front_right)]
    back_edge = [(right, back), (left, back)]
    ring = front + back_edge
    m = e.structure
    mat = e.colors[finish]
    m.face([(x, y, top) for x, y in ring], mat)
    m.face(
        [(x, y, bottom) for x, y in reversed(ring)], e.colors[soffit] if soffit else mat
    )
    for a, b in zip(ring, ring[1:] + ring[:1]):
        m.face([(*a, bottom), (*b, bottom), (*b, top), (*a, top)], mat)


def curtain(e):
    # In the guide the curved lights run continuously past the letters. Narrow
    # gasket joints, three rows of lights and outward-opening vents catch the sky.
    bays = 12
    for i in range(bays):
        a = ARC_HALF * (2 * i / bays - 1)
        b = ARC_HALF * (2 * (i + 1) / bays - 1)
        da, db = arc(a), arc(b)
        for level, z in enumerate(WINDOW_BASES):
            top = z + WINDOW_HEIGHT
            solid_band(e, a, b, da, db, 0.15, z - 0.14, top + 0.09, 'xiuGasket')
            for bottom, upper in ((z - 0.15, z), (top, top + 0.12)):
                solid_band(
                    e,
                    a,
                    b,
                    da + 0.085,
                    db + 0.085,
                    0.18,
                    bottom,
                    upper,
                    'xiuTerracotta',
                )
            if level < 2:
                solid_band(
                    e,
                    a,
                    b,
                    da - 0.015,
                    db - 0.015,
                    0.18,
                    top + 0.12,
                    WINDOW_BASES[level + 1] - 0.15,
                    'xiuIvory',
                )
            else:
                solid_band(
                    e, a, b, da - 0.02, db - 0.02, 0.18, top + 0.12, 18.36, 'xiuIvory'
                )
            if level == 2:
                solid_band(
                    e,
                    a,
                    b,
                    da + 0.47,
                    db + 0.47,
                    0.03,
                    top + 0.14,
                    top + 0.37,
                    'xiuIvory',
                    'xiuSoffit',
                )
            # Keep one glass span per bay at distance, with the identical outer envelope.
            cols, rows = (2, 3) if e.detail else (1, 1)
            for col in range(cols):
                x0 = a + (b - a) * col / cols + 0.012
                x1 = a + (b - a) * (col + 1) / cols - 0.012
                d0 = da + (db - da) * (x0 - a) / (b - a) + 0.018
                d1 = da + (db - da) * (x1 - a) / (b - a) + 0.018
                for row in range(rows):
                    z0 = z + WINDOW_HEIGHT * row / rows + 0.011
                    z1 = z + WINDOW_HEIGHT * (row + 1) / rows - 0.011
                    vent = (
                        level > 0
                        and row == 0
                        and col == 0
                        and i in (1, 3, 4, 6, 8, 10, 11)
                    )
                    lower = 0.21 if vent else 0
                    corners = [
                        (x0, -d0 - lower, z0),
                        (x1, -d1 - lower, z0),
                        (x1, -d1, z1),
                        (x0, -d0, z1),
                    ]
                    e.glazing.face(corners, e.colors['xiuBlueGlass'])
                    if vent:
                        # Open hopper lights expose a dark grille just below the pane.
                        for j in range(1, 5):
                            t = j / 5
                            xx = x0 + t * (x1 - x0)
                            yy = -d0 - t * (d1 - d0)
                            e.glazing.line(
                                (xx, yy - lower, z0),
                                (xx, yy, z0 - 0.07),
                                0.013,
                                e.colors['xiuGasket'],
                            )
                        e.glazing.line(
                            corners[0], corners[1], 0.025, e.colors['xiuGasket']
                        )
                        for idx in (0, 1):
                            xx, yy, zz = corners[idx]
                            e.glazing.line(
                                (xx, yy, zz),
                                (xx, yy + lower, zz - 0.07),
                                0.019,
                                e.colors['xiuGasket'],
                            )
        # Apron from the canopy soffit up to the first glazed ribbon.
        solid_band(
            e, a, b, da - 0.02, db - 0.02, 0.2, 5.23, WINDOW_BASES[0] - 0.15, 'xiuIvory'
        )


def wings(e):
    half = e.length / 2
    e.box(0, -3.98, 18.62, e.length, 8.16, 4.26, 'xiuIvory')
    for hand in (-1, 1):
        for z in WINDOW_BASES:
            for start, stop in ((ARC_HALF + 0.47, 10.30), (10.97, half - 0.51)):
                x = hand * (start + stop) / 2
                e.pane(x, 0.14, z, stop - start, WINDOW_HEIGHT, 3, glass='xiuBlueGlass')
                if e.detail:
                    e.glazing.box(
                        x,
                        -0.269,
                        z + WINDOW_HEIGHT * 0.275,
                        stop - start,
                        0.037,
                        0.045,
                        e.colors['xiuAluminium'],
                    )
                e.glazing.box(
                    x,
                    -0.269,
                    z + WINDOW_HEIGHT * 0.81,
                    stop - start,
                    0.037,
                    0.052,
                    e.colors['xiuAluminium'],
                )
            for zz in (z - 0.08, z + WINDOW_HEIGHT + 0.04):
                e.box(
                    hand * (half + ARC_HALF) / 2,
                    0.13,
                    zz,
                    half - ARC_HALF,
                    0.40,
                    0.14,
                    'xiuTerracotta',
                )
        # The same tall glazed end bays are visible from both side approaches.
        for z0, z1 in ((2.75, 6.92), (7.04, 11.00), (11.12, 15.08), (15.20, 17.68)):
            x = hand * (half + 0.018)
            y0, y1 = 0.87, 7.68
            corners = [(x, y0, z0), (x, y1, z0), (x, y1, z1), (x, y0, z1)]
            e.glazing.face(
                corners if hand > 0 else corners[::-1], e.colors['xiuBlueGlass']
            )
            for i in range(7):
                y = y0 + i * (y1 - y0) / 6
                e.glazing.box(
                    x, y, (z0 + z1) / 2, 0.052, 0.048, z1 - z0, e.colors['xiuAluminium']
                )
            for zz in (z0, z0 + (z1 - z0) * 0.50, z1):
                e.glazing.box(
                    x,
                    (y0 + y1) / 2,
                    zz,
                    0.062,
                    y1 - y0,
                    0.052,
                    e.colors['xiuAluminium'],
                )
        e.box(hand * (half + 0.035), 2.3, 1.49, 0.070, 4.62, 0.25, 'xiuPlinth')
        e.glazing.box(
            hand * (half + 0.08), 4.1, 0.79, 0.06, 7.0, 0.89, e.colors['xiuGasket']
        )
        if e.detail:
            for j in range(8):
                e.glazing.box(
                    hand * (half + 0.13),
                    1.12 + j * 0.86,
                    0.78,
                    0.058,
                    0.049,
                    0.89,
                    e.colors['xiuAluminium'],
                )
        for z in (18.70, 19.20, 19.70):
            e.box(hand * (half - 1.12), 0.28, z, 2.22, 0.56, 0.15, 'xiuAluminium')
    # Setback clerestory under the projecting curved roof, visible above the three bands.
    for i in range(16):
        a, b = -12.1 + i * 1.5125, -12.1 + (i + 1) * 1.5125
        z0 = 20.74
        z1 = 23.36
        e.box((a + b) / 2, -3.22, (z0 + z1) / 2, b - a + 0.01, 4.4, z1 - z0, 'xiuIvory')
        e.pane(
            (a + b) / 2,
            -0.94,
            21.12,
            b - a - 0.10,
            1.54,
            1,
            sash=False,
            glass='xiuClerestory',
        )
        da = 3.2 - 0.016 * a * a
        db = 3.2 - 0.016 * b * b
        solid_band(e, a, b, da, db, 5.2, 23.36, 23.74, 'xiuAluminium')


def entrance(e):
    for start, stop in ((-10.10, -4.04), (-2.91, 2.94), (4.05, 10.12)):
        width = stop - start
        x = (start + stop) / 2
        top = 5.12
        e.box(x, 0.15, (top + LANDING) / 2, width, 0.19, top - LANDING, 'xiuGasket')
        for i in range(4):
            x0 = start + i * width / 4 + 0.035
            x1 = start + (i + 1) * width / 4 - 0.035
            for lo, hi in ((LANDING + 0.055, 4.54), (4.60, top - 0.055)):
                e.glazing.box(
                    (x0 + x1) / 2,
                    -0.263,
                    (lo + hi) / 2,
                    x1 - x0,
                    0.033,
                    hi - lo,
                    e.colors['xiuDoorGlass'],
                )
            if e.detail:
                for xx in (x0, x1):
                    e.glazing.box(
                        xx,
                        -0.292,
                        (top + LANDING) / 2,
                        0.049,
                        0.052,
                        top - LANDING,
                        e.colors['xiuBronze'],
                    )
                e.glazing.box(
                    (x0 + x1) / 2,
                    -0.292,
                    4.57,
                    x1 - x0,
                    0.050,
                    0.047,
                    e.colors['xiuBronze'],
                )
            if e.detail:
                for left, right, h0, h1 in (
                    (x0, (x0 + x1) / 2, 3.02, 2.78),
                    ((x0 + x1) / 2, x1, 2.78, 3.02),
                ):
                    e.glazing.face(
                        [
                            (left, -0.286, h0),
                            (right, -0.286, h1),
                            (right, -0.286, h1 + 0.057),
                            (left, -0.286, h0 + 0.057),
                        ],
                        e.colors['xiuDoorStripe'],
                    )
                pull = x1 - 0.12 if i % 2 == 0 else x0 + 0.12
                e.glazing.box(
                    pull, -0.32, 3.08, 0.030, 0.072, 0.43, e.colors['xiuAluminium']
                )
    for side in (-1, 1):
        e.door(side * 12.8, 0.15, LANDING, 3.05, 3.03)
    # Segmented silver cladding follows the canopy edge, independent of the window curve.
    for j in range(16):
        a = -1 + j / 8
        b = -1 + (j + 1) / 8
        x0 = -0.037 + 5.929 * a
        x1 = -0.037 + 5.929 * b
        d0 = 4.003 - 1.341 * a * a + 0.13 * a
        d1 = 4.003 - 1.341 * b * b + 0.13 * b
        solid_band(
            e,
            x0,
            x1,
            d0,
            d1,
            0.10,
            CANOPY_TOP - 0.616,
            CANOPY_TOP,
            'xiuCanopy',
            'xiuSoffit',
        )
        if e.detail:
            e.glazing.line(
                (x0, -d0, CANOPY_TOP - 0.62),
                (x0, -0.53, CANOPY_TOP - 0.62),
                0.012,
                e.colors['xiuGasket'],
            )
            e.glazing.line(
                (x0, -d0 - 0.014, CANOPY_TOP - 0.15),
                (x1, -d1 - 0.014, CANOPY_TOP - 0.15),
                0.008,
                e.colors['xiuGasket'],
            )
            e.glazing.line(
                (x0, -d0 - 0.012, CANOPY_TOP - 0.59),
                (x0, -d0 - 0.012, CANOPY_TOP - 0.025),
                0.009,
                e.colors['xiuGasket'],
            )
    for c, x, z, width, height in [
        ('秀', -5.327, 7.747, 2.062, 1.218),
        ('苑', -2.1, 7.497, 1.869, 1.126),
        ('餐', 0.912, 7.499, 1.656, 1.22),
        ('厅', 3.668, 7.46, 1.50, 1.256),
    ]:
        glyph = inscription(
            c, 0, 0, 0, 2.0, height, e.colors['xiuGold'], False, flat=not e.detail
        )
        span = max(q[0] for q in glyph.v) - min(q[0] for q in glyph.v)
        glyph.v = [
            (x + u * width / span, v - arc(x + u * width / span) - 0.15, z + h)
            for u, v, h in glyph.v
        ]
        e.glazing.extend(glyph)


def stairs(e):
    e.box(
        0,
        LANDING_DEPTH / 2,
        LANDING / 2,
        2 * LANDING_END,
        LANDING_DEPTH,
        LANDING,
        'xiuStone',
    )
    # The broad middle flight runs west. The narrower north and south flights turn
    # through ninety degrees onto the same flush landing.
    for hand in (-1, 0, 1):
        width = 2 * FRONT_HALF if hand == 0 else LANDING_DEPTH

        def point(u, v, z, hand=hand):
            if hand == 0:
                return (u, -LANDING_DEPTH - v, z)
            return (hand * (LANDING_END + v), -(u + width / 2), z)

        def block(u, v, z, w, d, h, mat, mesh):
            xx, yy, zz = point(u, v, z)
            mesh.box(
                xx,
                yy,
                zz,
                w if hand == 0 else d,
                d if hand == 0 else w,
                h,
                e.colors[mat],
            )

        for i in range(RISERS):
            z = LANDING * (RISERS - i) / RISERS
            going = RUN / RISERS
            block(
                0,
                (i + 0.5) * going,
                z / 2,
                width - 0.27,
                going,
                z,
                'xiuStone',
                e.structure,
            )
            if e.detail:
                block(
                    0,
                    (i + 0.98) * going,
                    z - 0.012,
                    width - 0.27,
                    0.022,
                    0.025,
                    'xiuNosing',
                    e.glazing,
                )
                if hand == 0 and i in (1, 3, 5):
                    # Short brass safety strips are centred just right of the main doors.
                    block(
                        4.60,
                        (i + 1) * going + 0.005,
                        z - 0.056,
                        0.55,
                        0.010,
                        0.083,
                        'xiuGold',
                        e.glazing,
                    )
                    for mark in range(6):
                        block(
                            4.40 + mark * 0.078,
                            (i + 1) * going + 0.013,
                            z - 0.056,
                            0.036,
                            0.007,
                            0.039,
                            'xiuBronze',
                            e.glazing,
                        )
                n = math.ceil(width / 0.95)
                for j in range(n):
                    u = -width / 2 + (0.25 + 0.5 * (i % 2) + j) * width / n
                    block(
                        u,
                        (i + 0.5) * going,
                        z + 0.001,
                        0.011,
                        going,
                        0.004,
                        'xiuJoint',
                        e.glazing,
                    )
                    block(
                        u,
                        (i + 1) * going + 0.002,
                        z - LANDING / (2 * RISERS),
                        0.012,
                        0.005,
                        LANDING / RISERS - 0.008,
                        'xiuJoint',
                        e.glazing,
                    )
        for side in (-1, 1):
            u = side * width / 2
            for du in (-0.14, 0.14):
                coords = [
                    point(u + du, v, h)
                    for v, h in [(0, 0), (RUN, 0), (RUN, 1.03), (0, LANDING + 1.03)]
                ]
                e.structure.face(coords, e.colors['xiuCheek'])
            for v, h in ((0, LANDING + 1.03), (RUN, 1.03)):
                e.structure.face(
                    [
                        point(u + du, v, zz)
                        for du, zz in [(-0.14, 0), (0.14, 0), (0.14, h), (-0.14, h)]
                    ],
                    e.colors['xiuCheek'],
                )
            corners = [
                point(u + du, v, z)
                for du, v, z in [
                    (-0.19, 0, LANDING + 1.03),
                    (0.19, 0, LANDING + 1.03),
                    (0.19, RUN, 1.03),
                    (-0.19, RUN, 1.03),
                ]
            ]
            e.structure.face(corners, e.colors['xiuNosing'])
            if e.detail:
                # Block courses in the sloping cheek face. Each joint terminates at
                # its own height instead of running through the cap.
                face_u = u + side * 0.145
                for j in range(1, 12):
                    v = j * RUN / 12
                    h = 1.03 + LANDING * (1 - v / RUN)
                    e.glazing.line(
                        point(face_u, v, 0.10),
                        point(face_u, v, h - 0.055),
                        0.006,
                        e.colors['xiuJoint'],
                    )
                for z in (0.36, 0.69, 1.02, 1.35, 1.68, 2.01, 2.34, 2.67):
                    end = RUN * min(1, (1.03 + LANDING - z) / LANDING)
                    e.glazing.line(
                        point(face_u, 0, z),
                        point(face_u, end, z),
                        0.007,
                        e.colors['xiuJoint'],
                    )
            if e.detail:
                for j in range(1, 11):
                    t = j / 11
                    e.glazing.line(
                        point(u - 0.19, RUN * t, LANDING * (1 - t) + 1.033),
                        point(u + 0.19, RUN * t, LANDING * (1 - t) + 1.033),
                        0.009,
                        e.colors['xiuJoint'],
                    )
    for hand in (-1, 1):
        length = LANDING_END - FRONT_HALF
        e.box(
            hand * (LANDING_END + FRONT_HALF) / 2,
            LANDING_DEPTH,
            LANDING + 0.51,
            length,
            0.29,
            1.02,
            'xiuCheek',
        )
        e.box(
            hand * (LANDING_END + FRONT_HALF) / 2,
            LANDING_DEPTH,
            LANDING + 1.015,
            length,
            0.38,
            0.065,
            'xiuNosing',
        )
        # Dark retaining blocks and the low planted strip beneath each wing cheek.
        e.box(
            hand * (LANDING_END + FRONT_HALF) / 2,
            LANDING_DEPTH + 0.035,
            LANDING / 2,
            length,
            0.07,
            LANDING,
            'xiuPlinth',
        )
        if e.detail:
            for h in (0.32, 0.65, 0.98, 1.31, 1.64):
                e.glazing.box(
                    hand * (LANDING_END + FRONT_HALF) / 2,
                    -LANDING_DEPTH - 0.077,
                    h,
                    length,
                    0.016,
                    0.017,
                    e.colors['xiuJoint'],
                )
            for n in range(11):
                x = hand * (FRONT_HALF + 0.42 + (0.43 * n))
                e.glazing.ellipsoid(
                    x,
                    -LANDING_DEPTH - 1.20,
                    0.28,
                    0.48,
                    0.40,
                    0.27 + 0.035 * (n % 3),
                    e.colors['xiuShrub'],
                    12,
                    8,
                )


def xiuyuan(e):
    for key, rgb, roughness, metal in (
        ('xiuIvory', (0.70, 0.65, 0.53), 0.79, 0.0),
        ('xiuTerracotta', (0.48, 0.25, 0.15), 0.73, 0.0),
        ('xiuBlueGlass', (0.12, 0.27, 0.39), 0.13, 0.67),
        ('xiuClerestory', (0.105, 0.125, 0.135), 0.34, 0.40),
        ('xiuGasket', (0.036, 0.048, 0.053), 0.68, 0.11),
        ('xiuAluminium', (0.53, 0.57, 0.58), 0.39, 0.48),
        ('xiuCanopy', (0.60, 0.63, 0.64), 0.23, 0.62),
        ('xiuSoffit', (0.17, 0.16, 0.14), 0.67, 0.12),
        ('xiuBronze', (0.19, 0.16, 0.105), 0.40, 0.48),
        ('xiuGold', (0.86, 0.60, 0.22), 0.32, 0.56),
        ('xiuDoorGlass', (0.052, 0.077, 0.083), 0.18, 0.57),
        ('xiuDoorStripe', (0.27, 0.048, 0.045), 0.60, 0.05),
        ('xiuPlinth', (0.15, 0.16, 0.16), 0.86, 0.02),
        ('xiuShrub', (0.115, 0.18, 0.060), 0.89, 0.0),
        ('xiuStone', (0.56, 0.46, 0.33), 0.82, 0.0),
        ('xiuCheek', (0.58, 0.56, 0.53), 0.78, 0.0),
        ('xiuNosing', (0.68, 0.62, 0.53), 0.67, 0.0),
        ('xiuJoint', (0.22, 0.20, 0.18), 0.88, 0.0),
    ):
        if key not in e.colors:
            e.colors[key] = material(key, rgb, roughness, metal)
    curtain(e)
    wings(e)
    entrance(e)
    stairs(e)
