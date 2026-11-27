"""Zhixing Academy on the Yueya Lake peninsula. Local -Y faces the approach."""

import math

from geometry import Mesh
from south_gate import inscription, prism


def roof(m, x, y, w, d, eave, rise, C, detail, turn=False):
    r = Mesh()
    h = d / 2
    for side in (-1, 1):
        a, b = -w / 2, w / 2
        edge = side * h
        face = [
            (a, edge, eave),
            (b, edge, eave),
            (b, 0, eave + rise),
            (a, 0, eave + rise),
        ]
        r.face(face if side < 0 else face[::-1], C['slate'])
        r.box(0, edge, eave - 0.09, w, 0.16, 0.18, C['white'])
        if detail:
            count = round(w / 0.27)
            for i in range(count):
                u = w * ((i + 0.5) / count - 0.5)
                r.line(
                    (u, edge, eave), (u, 0, eave + rise), 0.045, C['residencePodium'], 5
                )
    for side in (-1, 1):
        u = side * w / 2
        pts = [(u, -h, eave - 0.18), (u, h, eave - 0.18), (u, 0, eave + rise + 0.12)]
        r.face(pts if side > 0 else pts[::-1], C['bridgeConcrete'])
        for v in (-h, h):
            r.line((u, v, eave + 0.06), (u, 0, eave + rise + 0.2), 0.105, C['stone'])
    r.box(0, 0, eave + rise + 0.08, w + 0.12, 0.20, 0.2, C['slate'])
    if turn:
        r.rotate_z(0, 0, math.pi / 2)
    r.v = [(u + x, v + y, z) for u, v, z in r.v]
    m.extend(r)


def build(l, b, z, C, detail):
    m = Mesh()
    floor = z + 1.38
    # Both entrance views constrain the lift; a larger rise masks the plaque.
    transom_lift = 0.09
    screen_height = 4.10 + transom_lift
    stone, wood = C['bridgeConcrete'], C['wood']
    # A continuous plinth beds into the sloping baseline ground and pedestrian surface.
    m.box(0, 0.1, floor - 1.35, 28.6, 33.2, 2.7, stone)
    for side in (-1, 1):
        x = side * 10.45
        m.box(side * 12, 0, floor + 1.85, 4.3, 16.8, 3.7, stone)
        roof(m, x, 0, 17, 9.3, floor + 3.75, 1.55, C, detail, True)
        for y in (-6.9, 0, 6.9):
            m.cylinder(side * 6.5, y, floor + 1.84, 0.17, 3.68, wood)
    for x, w in [(-11.3, 7.3), (0, 15.3), (11.3, 7.3)]:
        roof(m, x, 12.8, w, 9.6, floor + (4.05 if x == 0 else 3.7), 1.85, C, detail)
    m.box(0, 14.25, floor + 2, 28.6, 5.8, 4, stone)
    for x in (-7, -3.5, 3.5, 7):
        m.cylinder(x, 9, floor + 2, 0.22, 4, stone)
    for side in (-1, 1):
        x = side * 7.5
        m.box(x, -12.9, floor + 1.95, 4.9, 7.7, 3.9, stone)
        roof(m, x, -12.9, 5.05, 8.8, floor + 4, 1.45, C, detail)
        m.box(x, -16.79, floor + 2, 1.45, 0.13, 2.15, C['gateRed'])
        m.box(x, -16.88, floor + 2, 1.24, 0.07, 1.92, C['glass'])
        m.box(x, -16.93, floor + 2.49, 1.24, 0.055, 0.065, C['gateRed'])
        m.box(x, -16.93, floor + 1.72, 0.055, 0.055, 1.38, C['gateRed'])
        for y in (-16, -9.8):
            height = 4.9 + (transom_lift if y == -16 else 0)
            m.cylinder(side * 3.15, y, floor + height / 2, 0.245, height, wood, 16)
            m.cylinder(side * 3.15, y, floor + 0.14, 0.34, 0.28, stone, 16)
    roof(m, 0, -12.95, 10.2, 9.1, floor + 5, 1.8, C, detail)
    m.box(0, -16, floor + transom_lift + 4.48, 3.48, 0.29, 0.9, wood)
    m.box(0, -16, floor + transom_lift + 4.95, 10, 0.26, 0.17, wood)
    if detail:
        for side in (-1, 1):
            for i in range(4):
                m.box(
                    side * (3.53 + i * 0.39),
                    -16,
                    floor + screen_height / 2,
                    0.079,
                    0.11,
                    screen_height,
                    wood,
                )
            for i in range(6):
                px = side * (1.89 + i * 0.56)
                m.box(px, -16, floor + transom_lift + 4.48, 0.052, 0.09, 0.86, wood)
                m.box(
                    px + side * 0.22,
                    -16,
                    floor + transom_lift + 4.35 + 0.25 * (i % 2),
                    0.44,
                    0.09,
                    0.05,
                    wood,
                )
            m.box(
                side * 3.325, -16, floor + transom_lift + 4.06, 3.07, 0.10, 0.07, wood
            )

    for i in range(3):
        top = floor - 0.15 * (i + 1)
        base = floor - 1.4
        m.box(0, -16.7 - i * 0.37, (base + top) / 2, 7.1, 0.42, top - base, stone)
    # Axis stone has an asymmetric shoulder and a flat inscription face in the gallery.
    outline = [
        (-1.3, 0),
        (1.24, 0),
        (1.18, 1.62),
        (0.72, 2.18),
        (0.16, 2.31),
        (-0.58, 1.94),
        (-0.86, 1.28),
        (-1.27, 0.85),
    ]
    prism(m, [(x, floor + h) for x, h in outline], 2.6, 0.88, C['gateStone'])
    if detail:
        for label, x, y, h, w, ht, mat in [
            ('院书行知', 0, -16.16, 4.48 + transom_lift, 3.1, 0.64, 'timeLetter'),
            ('劝', 0, 2.14, 1.5, 0.56, 0.56, 'gateRed'),
            ('学', 0, 2.14, 0.82, 0.56, 0.56, 'gateRed'),
        ]:
            m.extend(
                inscription(
                    label,
                    x,
                    y,
                    floor + h,
                    w,
                    ht,
                    C[mat],
                    False,
                    flat=True,
                    curve_resolution=2,
                )
            )
    m.rotate_z(0, 0, math.radians(67))
    cx, cy = l['center']
    m.v = [(x + cx, y + cy, h) for x, y, h in m.v]
    return m
