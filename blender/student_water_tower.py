"""Historic tower beside the student centre, from visible south-facing evidence.

GXU gallery + BV1US4y1V7dg 00:31 establish brick shaft / wider dark tank.
Dimensions are photo-scaled estimates; the mapped circle anchors tank width.
Unseen rear openings are not duplicated from the visible south elevation.
"""

import math

from geometry import MATERIALS, Mesh, material, tile_material

TOWER_ID = 'way/955987491'


def water_tower(b, z, C, detail):
    for name, colour in [
        ('studentTowerBrick', (0.50, 0.22, 0.105)),
        ('studentTowerTank', (0.22, 0.205, 0.18)),
    ]:
        if name not in C:
            C[name] = next((i for i, m in enumerate(MATERIALS) if m.name == name), None)
            if C[name] is None:
                C[name] = material(name, colour)
    m = Mesh()
    x, y = b['center']
    h = b['height']
    radius = min(b['bounds'][2] - b['bounds'][0], b['bounds'][3] - b['bounds'][1]) / 2
    shaft = radius * 0.65
    neck = h * 0.84
    tank_bottom = h * 0.865
    brick = C['studentTowerBrick']
    tank = C['studentTowerTank']
    # Weathered rim and masonry bands appear much darker than the red shaft.
    weathered = (0.092, 0.063, 0.048, 1)
    mat = MATERIALS[tank]
    mat.diffuse_color = weathered
    mat.node_tree.nodes.get('Principled BSDF').inputs[
        'Base Color'
    ].default_value = weathered
    n = 48 if detail else 24
    if detail:
        tile_material(
            C, 'studentTowerMasonry', 'tower-cafe-brick.png', (0.37, 0.145, 0.075)
        )
        for i in range(n):
            a, b = math.tau * i / n, math.tau * (i + 1) / n
            points = [
                (x + shaft * math.cos(t), y + shaft * math.sin(t), z + h)
                for t, h in ((a, 0), (b, 0), (b, neck), (a, neck))
            ]
            m.face(
                points,
                C['studentTowerMasonry'],
                [
                    (u * 12 / n, h / 0.64)
                    for u, h in ((i, 0), (i + 1, 0), (i + 1, neck), (i, neck))
                ],
            )
        m.cylinder(x, y, z + neck - 0.03, shaft, 0.06, brick, n)
    else:
        m.cylinder(x, y, z + neck / 2, shaft, neck, brick, n)
    for fraction in (0.14, 0.35, 0.53, 0.70, 0.835):
        m.cylinder(x, y, z + h * fraction, shaft + 0.024, 0.09, tank, n)
    m.cylinder(
        x,
        y,
        z + (neck + tank_bottom) / 2,
        shaft,
        tank_bottom - neck,
        tank,
        n,
        topr=radius,
    )
    m.cylinder(x, y, z + (tank_bottom + h) / 2, radius, h - tank_bottom, tank, n)
    for level in (tank_bottom, h - 0.10):
        m.cylinder(x, y, z + level, radius + 0.10, 0.20, tank, n)
    # Four narrow openings visible on the near/south shaft, not generic floors.
    for fraction in (0.205, 0.39, 0.575, 0.76):
        bearing = math.radians(17) if fraction == 0.205 else 0
        xx, yy = (
            x + (shaft + 0.035) * math.sin(bearing),
            y - (shaft + 0.035) * math.cos(bearing),
        )
        height = 1.94 if fraction == 0.205 else 1.35
        m.box(xx, yy, z + h * fraction, 0.52, 0.07, height, C['dark'], bearing)
        if detail:
            edge = C['stone'] if fraction != 0.205 else tank
            for side in (-1, 1):
                m.box(
                    xx + side * 0.30 * math.cos(bearing),
                    yy + side * 0.30 * math.sin(bearing),
                    z + h * fraction,
                    0.075,
                    0.09,
                    height + 0.08,
                    edge,
                    bearing,
                )
            m.box(
                xx,
                yy,
                z + h * fraction + height / 2 + 0.04,
                0.79,
                0.125,
                0.11,
                edge,
                bearing,
            )
    # Gallery photo shows rooftop telecom rods; simplified, not a surveyed array.
    m.cylinder(x, y, z + h + 0.7, 0.18, 1.4, C['metal'], 12)
    for angle in (0, math.tau / 3, math.tau * 2 / 3):
        ax = x + 0.48 * math.cos(angle)
        ay = y + 0.48 * math.sin(angle)
        m.line((x, y, z + h + 0.35), (ax, ay, z + h + 1.2), 0.045, C['metal'])
        m.box(ax, ay, z + h + 2, 0.16, 0.20, 1.3, C['white'], angle)
    return m
