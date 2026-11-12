"""Historic tower beside the student centre, from visible south-facing evidence.

GXU gallery + BV1US4y1V7dg 00:31 establish brick shaft / wider dark tank.
Dimensions are photo-scaled estimates; the mapped circle anchors tank width.
Unseen rear openings are not duplicated from the visible south elevation.
"""

import math

from geometry import MATERIALS, Mesh, material

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
    n = 48 if detail else 24
    m.cylinder(x, y, z + neck / 2, shaft, neck, brick, n)
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
        m.box(x, y - shaft - 0.015, z + h * fraction, 0.52, 0.07, 1.35, C['dark'])
        if detail:
            for side in (-1, 1):
                m.box(
                    x + side * 0.30,
                    y - shaft - 0.06,
                    z + h * fraction,
                    0.09,
                    0.12,
                    1.53,
                    C['stone'],
                )
    # Gallery photo shows rooftop telecom rods; simplified, not a surveyed array.
    m.cylinder(x, y, z + h + 0.7, 0.18, 1.4, C['metal'], 12)
    for angle in (0, math.tau / 3, math.tau * 2 / 3):
        ax = x + 0.48 * math.cos(angle)
        ay = y + 0.48 * math.sin(angle)
        m.line((x, y, z + h + 0.35), (ax, ay, z + h + 1.2), 0.045, C['metal'])
        m.box(ax, ay, z + h + 2, 0.16, 0.20, 1.3, C['white'], angle)
    # Low circular guard visible at the one-storey platform; no slab over void.
    ring = radius + 0.43
    deck = 4.4
    for i in range(n):
        a = math.tau * i / n
        c = math.tau * (i + 1) / n
        m.line(
            (x + ring * math.cos(a), y + ring * math.sin(a), z + deck + 0.95),
            (x + ring * math.cos(c), y + ring * math.sin(c), z + deck + 0.95),
            0.04,
            C['metal'],
        )
        if i % (2 if detail else 1) == 0:
            m.cylinder(
                x + ring * math.cos(a),
                y + ring * math.sin(a),
                z + deck + 0.475,
                0.035,
                0.95,
                C['metal'],
                6,
            )
    return m
