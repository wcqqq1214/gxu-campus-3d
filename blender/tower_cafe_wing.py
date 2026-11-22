"""West-end café around the independent historic tower.

The 2021 walk-through supplies the stair, inner glazing and window seating.
The 2022 aerial supplies the deck outline and planting. Dimensions and the
entrance bearing are estimates in the campus coordinate system.
"""

import math

from dining_interiors import interior_finish, warm_lamp
from geometry import MATERIALS, Mesh, tile_material

TOWER = (239.90, 50.12)
WELL = 4.55
ROOF_WELL = 3.99
BAYS = 26
STAIR_SWEEP = math.radians(135.25)
DOOR_BAY = 21
DOOR_ANGLE = math.tau * DOOR_BAY / BAYS


def polar(radius, angle, z):
    return (TOWER[0] + radius * math.cos(angle), TOWER[1] + radius * math.sin(angle), z)


def roof_point(radius, angle, z):
    # The photographed deck collar is slightly oval relative to the curtain wall.
    return (
        TOWER[0] + 0.08 + 1.05 * radius * math.cos(angle) + 0.20 * math.sin(angle),
        TOWER[1] - 0.015 + 0.95 * radius * math.sin(angle),
        z,
    )


def deck_collar(m, aperture, angles, top, thickness, deck, soffit):
    """Bridge the mapped slab triangles to the rounded, projecting opening."""
    lip = []
    for i, outer in enumerate(aperture):
        j = (i + 1) % len(aperture)
        sweep = (angles[j] - angles[i]) % math.tau
        for k in range(4):
            panel = []
            for t in (k / 4, (k + 1) / 4):
                angle = angles[i] + sweep * t
                edge = tuple(a + (b - a) * t for a, b in zip(outer, aperture[j]))
                panel.append(((*edge, top), roof_point(ROOF_WELL + 0.03, angle, top)))
            (a, b), (c, d) = panel
            m.face([a, c, d, b], deck)
            m.face([(x, y, top - thickness) for x, y, _ in (b, d, c, a)], soffit)
            lip.append(b[:2])
    return lip


def pane_material(c):
    if 'cafeClearPane' not in c:
        idx = interior_finish(c, 'cafeClearPane', (0.68, 0.78, 0.77), 0.18)
        mat = MATERIALS[idx]
        mat.diffuse_color = (0.68, 0.78, 0.77, 0.10)
        mat.node_tree.nodes.get('Principled BSDF').inputs['Alpha'].default_value = 0.10
        mat.surface_render_method = 'DITHERED'
        mat.use_backface_culling = False
    return c['cafeClearPane']


def stair(c, z, rise, detail):
    m = Mesh()
    ink = interior_finish(c, 'cafeStairSteel', (0.031, 0.032, 0.033), 0.47, 0.48)
    copper = interior_finish(c, 'cafeCopperRail', (0.46, 0.136, 0.048), 0.28, 0.53)
    tread = ink
    if detail:
        tile_material(c, 'cafeChequerPlate', 'tower-cafe-tread.png', (0.12, 0.12, 0.12))
        tread = c['cafeChequerPlate']
    clear = pane_material(c)
    steps, sweep = 26, STAIR_SWEEP
    inner, outer = 2.416, 3.629
    # Climbing counterclockwise keeps the brick shaft on the left.
    for i in range(steps):
        a = DOOR_ANGLE - sweep * (1 - i / steps)
        b = a + sweep / steps
        lo, hi = z + rise * i / steps, z + rise * (i + 1) / steps
        corners = [
            polar(r, ang, hi)
            for r, ang in [(inner, a), (outer, a), (outer, b), (inner, b)]
        ]
        m.face(
            corners,
            tread,
            [(x / 0.19, y / 0.19) for x, y, _ in corners] if detail else None,
        )
        riser = [polar(inner, a, lo), polar(outer, a, lo), corners[1], corners[0]]
        m.face(
            riser,
            tread,
            [
                (0, 0),
                ((outer - inner) / 0.19, 0),
                ((outer - inner) / 0.19, (hi - lo) / 0.19),
                (0, (hi - lo) / 0.19),
            ]
            if detail
            else None,
        )
        # Folded steel stringers follow the pitch continuously on both sides.
        for r in (inner - 0.026, outer + 0.026):
            m.face(
                [
                    polar(r, a, max(z, lo - 0.15)),
                    polar(r, b, max(z, hi - 0.15)),
                    polar(r, b, hi + 0.18),
                    polar(r, a, lo + 0.18),
                ],
                ink,
            )
            m.line(polar(r, a, lo + 0.18), polar(r, b, hi + 0.18), 0.016, ink, 8)
        for r in (inner, outer):
            m.face(
                [
                    polar(r, a, max(z, lo - 0.15)),
                    polar(r, b, max(z, hi - 0.15)),
                    polar(r, b, hi),
                    polar(r, a, hi),
                ],
                ink,
            )
            rail_r = r
            hand = 1.25
            m.face(
                [
                    polar(rail_r, a, lo + 0.09),
                    polar(rail_r, b, hi + 0.09),
                    polar(rail_r, b, hi + hand - 0.065),
                    polar(rail_r, a, lo + hand - 0.065),
                ],
                clear,
            )
            if i % 3 == 0:
                ang = a + (b - a) * 0.75
                m.line(
                    polar(rail_r, ang, hi),
                    polar(rail_r, ang, lo + hand + 0.75 * rise / steps),
                    0.035,
                    copper,
                    10,
                )
    # A shared ring at each cross-section keeps the copper handrail continuous.
    for r in (inner, outer):
        previous = None
        for i in range(steps * 2 + 1):
            t = i / (steps * 2)
            angle = DOOR_ANGLE - sweep * (1 - t)
            center = polar(r, angle, z + rise * t + 1.25)
            ring = []
            for j in range(20):
                theta = math.tau * j / 20
                lateral = 0.044 * math.cos(theta)
                ring.append(
                    (
                        center[0] + lateral * math.cos(angle),
                        center[1] + lateral * math.sin(angle),
                        center[2] + 0.044 * math.sin(theta),
                    )
                )
            if previous:
                for j in range(20):
                    k = (j + 1) % 20
                    m.face([previous[j], previous[k], ring[k], ring[j]], copper)
            previous = ring
    # A level, pie-shaped landing continues tangentially into two open window bays.
    a, b = DOOR_ANGLE, DOOR_ANGLE + 2 * math.tau / BAYS
    for j in range(2):
        s, t = a + (b - a) * j / 2, a + (b - a) * (j + 1) / 2
        pts = [
            polar(r, ang, z + rise + 0.006)
            for r, ang in [(inner, s), (WELL + 0.07, s), (WELL + 0.07, t), (inner, t)]
        ]
        m.face(
            pts, tread, [(x / 0.19, y / 0.19) for x, y, _ in pts] if detail else None
        )
        m.line(
            polar(inner, s, z + rise + 1.25),
            polar(inner, t, z + rise + 1.25),
            0.044,
            copper,
        )
    m.line(
        polar(inner, b, z + rise + 1.25), polar(WELL, b, z + rise + 1.25), 0.044, copper
    )
    m.face(
        [
            polar(inner, b, z + rise),
            polar(WELL, b, z + rise),
            polar(WELL, b, z + rise + 1.18),
            polar(inner, b, z + rise + 1.18),
        ],
        clear,
    )
    return m


def inner_windows(c, z, height, detail):
    m = Mesh()
    frame = interior_finish(c, 'cafeWindowFrame', (0.055, 0.048, 0.043), 0.38, 0.40)
    glass = pane_material(c)
    # The six photographed lounge bays vary slightly in width along the curve.
    offsets = {
        14: -0.01,
        15: 0.025,
        16: 0.008,
        17: -0.008,
        18: -0.044,
        19: -0.05,
        20: 0.073,
    }
    angles = [math.tau * (i + offsets.get(i, 0)) / BAYS for i in range(BAYS + 1)]
    for i, (a, b) in enumerate(zip(angles, angles[1:])):
        if i != DOOR_BAY + 1:
            m.line(polar(WELL, a, z), polar(WELL, a, z + height), 0.054, frame)
        if i in (DOOR_BAY, DOOR_BAY + 1):
            continue
        m.face(
            [
                polar(WELL, a, z),
                polar(WELL, b, z),
                polar(WELL, b, z + height),
                polar(WELL, a, z + height),
            ],
            glass,
        )
        for h in (0.04, 1.07, height - 0.045):
            m.line(
                polar(WELL, a, z + h),
                polar(WELL, b, z + h),
                0.033 if h == 1.07 else 0.045,
                c['metal'] if h == 1.07 else frame,
            )
    return m


def window_seats(c, z, ceiling):
    m = Mesh()
    seat = interior_finish(c, 'cafeUpholstery', (0.70, 0.64, 0.50), 0.88)
    wood = interior_finish(c, 'cafeTableOak', (0.45, 0.277, 0.142), 0.49)
    brass = interior_finish(c, 'cafeTableBase', (0.32, 0.216, 0.114), 0.4, 0.30)
    cushion = interior_finish(c, 'cafeSeatCushion', (0.59, 0.46, 0.32), 0.89)
    blue = interior_finish(c, 'cafeBlueThrow', (0.43, 0.58, 0.65), 0.91)
    lamp = warm_lamp(c)
    for i in (9.15, 11.5, 13.85, 16.3, 18.2, 19.95, 24.0):
        angle = math.tau * i / BAYS
        x, y, _ = polar(WELL + 1.41, angle, z)
        m.cylinder(x, y, z + 0.36, 0.23, 0.72, brass, 18, topr=0.11)
        m.cylinder(x, y, z + 0.745, 0.47, 0.055, wood, 32)
        for side in (-1, 1):
            cx = x - side * 0.80 * math.sin(angle)
            cy = y + side * 0.80 * math.cos(angle)
            m.ellipsoid(cx, cy, z + 0.42, 0.34, 0.34, 0.10, cushion, 20, 10)
            for j in range(12):
                a = angle + side * math.pi / 2 + (j / 12 - 0.5) * math.pi
                b = a + math.pi / 12
                h1 = 0.63 + 0.22 * math.sin(math.pi * j / 12)
                h2 = 0.63 + 0.22 * math.sin(math.pi * (j + 1) / 12)
                m.face(
                    [
                        (cx + 0.33 * math.cos(a), cy + 0.33 * math.sin(a), z + 0.42),
                        (cx + 0.33 * math.cos(b), cy + 0.33 * math.sin(b), z + 0.42),
                        (cx + 0.39 * math.cos(b), cy + 0.39 * math.sin(b), z + h2),
                        (cx + 0.39 * math.cos(a), cy + 0.39 * math.sin(a), z + h1),
                    ],
                    seat,
                )
                m.line(
                    (cx + 0.39 * math.cos(a), cy + 0.39 * math.sin(a), z + h1),
                    (cx + 0.39 * math.cos(b), cy + 0.39 * math.sin(b), z + h2),
                    0.027,
                    seat,
                    10,
                )
            if i in (16.3, 18.2):
                pillow = Mesh()
                pillow.ellipsoid(cx, cy, z + 0.64, 0.24, 0.108, 0.18, blue, 18, 10)
                pillow.rotate_z(cx, cy, angle)
                m.extend(pillow)
            for dx in (-0.21, 0.21):
                for dy in (-0.21, 0.21):
                    m.line(
                        (cx + dx * 1.2, cy + dy * 1.2, z),
                        (cx + dx, cy + dy, z + 0.40),
                        0.018,
                        wood,
                    )
    # Equally spaced pendants are independent of the table and mullion spacing.
    for i in range(6, 21):
        angle = (i + 0.29) * math.tau / 22
        if DOOR_ANGLE < angle < DOOR_ANGLE + 2 * math.tau / BAYS:
            continue
        x, y, _ = polar(WELL + 0.58, angle, z)
        m.line((x, y, z + 2.37), (x, y, ceiling), 0.008, c['dark'])
        m.ellipsoid(x, y, z + 2.26, 0.095, 0.095, 0.095, lamp, 18, 10)
    # Window-side palms seen beside the lounge chairs and the opposite return.
    leaf = interior_finish(c, 'cafePalmLeaf', (0.052, 0.15, 0.040), 0.70)
    for radius, angle in [(7.65, 4.38), (6.05, 5.28)]:
        x, y, _ = polar(radius, angle, z)
        m.cylinder(x, y, z + 0.235, 0.18, 0.47, c['white'], 18, topr=0.24)
        for j in range(13):
            a = j * 2.40
            height = 1.0 + 0.40 * math.sin(j * 1.8)
            path = []
            for k in range(9):
                t = k / 8
                path.append(
                    (
                        x + 0.74 * t * math.cos(a),
                        y + 0.74 * t * math.sin(a),
                        z + 0.45 + height * (1.7 * t - 0.85 * t * t),
                    )
                )
            for k, (u, v) in enumerate(zip(path, path[1:])):
                m.line(u, v, 0.009, leaf)
                spread = 0.16 * math.sin(math.pi * (k + 0.6) / 8)
                for side in (-1, 1):
                    m.face(
                        [
                            u,
                            v,
                            (
                                v[0] + spread * math.cos(a + side * 0.96),
                                v[1] + spread * math.sin(a + side * 0.96),
                                v[2] - 0.065,
                            ),
                        ],
                        leaf,
                    )
    return m


def roof_terrace(c, z):
    m = Mesh()
    earth = interior_finish(c, 'cafeTerraceBed', (0.20, 0.22, 0.082), 0.94)
    paving = interior_finish(c, 'cafeInsetPaving', (0.185, 0.156, 0.137), 0.83)
    # Crescent at the western tip, low masonry lip with planting inside.
    # Paired outer and inner edges follow the curved tip in the aerial.
    outer = [
        [228.98, 52.63],
        [228.26, 52.08],
        [227.48, 51.3],
        [226.5, 50.02],
        [225.85, 48.89],
        [225.32, 47.59],
        [225.0, 46.44],
        [225.18, 45.17],
        [225.76, 43.83],
        [226.72, 42.75],
        [227.96, 42.04],
        [229.06, 41.62],
        [229.82, 41.55],
        [230.93, 41.92],
    ]
    inner = [
        [228.98, 52.63],
        [228.66, 51.87],
        [228.19, 50.83],
        [227.82, 49.82],
        [227.67, 48.77],
        [227.63, 47.91],
        [227.59, 46.85],
        [227.71, 45.66],
        [228.05, 44.97],
        [228.43, 44.38],
        [229.06, 43.67],
        [229.77, 43.15],
        [230.42, 42.6],
        [230.93, 41.92],
    ]
    foliage = interior_finish(c, 'cafeLowFoliage', (0.24, 0.30, 0.086), 0.95)
    for i in range(len(outer) - 1):
        profile = [
            (*point, z + 0.39)
            for point in (outer[i], outer[i + 1], inner[i + 1], inner[i])
        ]
        m.face(profile, earth)
        for j, k in ((0, 1), (2, 3)):
            m.face(
                [(*profile[j][:2], z), (*profile[k][:2], z), profile[k], profile[j]],
                c['white'],
            )
            m.line(profile[j], profile[k], 0.095, c['stone'], 10)
        if 1 <= i < len(outer) - 2:
            for t in (0.28, 0.53, 0.75):
                x = outer[i][0] * (1 - t) + inner[i][0] * t
                y = outer[i][1] * (1 - t) + inner[i][1] * t
                m.ellipsoid(x, y, z + 0.42, 0.34, 0.32, 0.16, foliage, 8, 5)
    for dx, dy in [(-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)]:
        x = 244.22 + dx * 1.54 + dy * 0.63
        y = 41.24 + dx * -0.80 + dy * 2.05
        m.box(x, y, z + 0.012, 1.35, 1.35, 0.024, paving, -0.480)
    for i in range(BAYS * 2):
        a, b = math.tau * i / (BAYS * 2), math.tau * (i + 1) / (BAYS * 2)
        m.line(
            roof_point(ROOF_WELL + 0.07, a, z + 0.92),
            roof_point(ROOF_WELL + 0.07, b, z + 0.92),
            0.037,
            c['metal'],
        )
        if i % 2 == 0:
            m.line(
                roof_point(ROOF_WELL + 0.07, a, z),
                roof_point(ROOF_WELL + 0.07, a, z + 0.92),
                0.028,
                c['metal'],
            )
    return m
