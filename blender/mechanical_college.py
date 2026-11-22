"""Mechanical college: south entrance and stepped volumes from exterior views.

The six-storey west end, south sign wall and two-sided entrance canopy are
constrained by the university photograph and geolocated street views. Heights,
transition positions and details obscured by trees are approximate.
"""

import math

from college_details import flight, pane
from geometry import Mesh

BUILDING_ID = 'way/759079683'


def mechanical_college(b, z, C, detail):
    if abs(b['bounds'][0] + 281.54) > 1 or abs(b['bounds'][1] + 1024.99) > 1:
        raise ValueError('Mechanical footprint changed; recheck photo anchors')
    m, body, roof, facade = Mesh(), Mesh(), Mesh(), Mesh()
    wall, white, glass, dark, pink = (
        C[k] for k in ('tenTrim', 'white', 'tenGlass', 'dark', 'pink')
    )
    # Mapped west block and progressively narrower east wings; heights are photo estimates.
    for x0, x1, y0, y1, height in [
        (-281.52, -261.35, -1024.97, -1003.39, 22.2),
        (-261.35, -246.61, -1024.97, -1019.96, 4.06),
        (-261.35, -184.07, -1019.96, -1003.43, 18.7),
        (-184.07, -150.97, -1019.99, -1008.68, 18.7),
    ]:
        body.box(
            (x0 + x1) / 2,
            (y0 + y1) / 2,
            z + (height - 0.5) / 2,
            x1 - x0,
            y1 - y0,
            height + 0.5,
            wall,
        )
        roof.box(
            (x0 + x1) / 2,
            (y0 + y1) / 2,
            z + height + 0.15,
            x1 - x0,
            y1 - y0,
            0.3,
            C['paleRoof'],
        )
    # Five upper rows over the ground level on the photographed south facade.
    for x0, x1, y, rows, height in [
        (-280.8, -266.64, -1025, 5, 22.2),
        (-261.32, -151.5, -1020.02, 4, 18.7),
    ]:
        n = max(1, round((x1 - x0) / 3.6))
        for floor in range(rows):
            level = z + 5.6 + floor * 3.35
            for j in range(n):
                x = x0 + (j + 0.5) * (x1 - x0) / n
                facade.box(x, y - 0.09, level, 2.25, 0.12, 1.7, glass)
                body.box(x, y - 0.07, level - 1.15, 2.25, 0.14, 0.5, pink)
                if detail:
                    facade.box(x, y - 0.17, level, 0.06, 0.08, 1.7, white)
                    facade.box(x, y - 0.17, level, 2.25, 0.08, 0.055, white)
                    if x0 < -280:
                        for dx in (-0.82, -0.54, -0.27, 0.27, 0.54, 0.82):
                            facade.box(
                                x + dx,
                                y - 0.22,
                                level,
                                0.035,
                                0.045,
                                1.69,
                                C['courtMetal'],
                            )
            # The horizontal joints stop at the sides of the uninterrupted
            # white name pier in the university's full-resolution front photo.
            body.box(
                (x0 + x1) / 2,
                y - 0.13,
                z + 4 + floor * 3.35,
                x1 - x0,
                0.28,
                0.16,
                white,
            )
    # The sign pier is on the south elevation, not on the west end.
    # The three geolocated name-pier rays intersect x=-265 to -263. The
    # lower canopy continues farther east than the six-storey street wall.
    body.box(-264, -1025.08, z + 13.1, 5.31, 0.17, 18.2, white)
    if detail:
        from south_gate import inscription

        for i, char in enumerate('机械工程学院'):
            body.extend(
                inscription(
                    char,
                    -264,
                    -1025.19,
                    z + 18 - i * 1.8,
                    1.2,
                    1.25,
                    C['timeLetter'],
                    True,
                    flat=True,
                    curve_resolution=2,
                )
            )
    # Corner canopy returns around the west elevation. The primary door faces south.
    body.box(-265, -1026.45, z + 4.0, 32.5, 3.1, 0.42, wall)
    body.box(-282.85, -1015, z + 4.0, 2.7, 19.8, 0.42, wall)
    corner = (-281.40, -1024.92)
    for j in range(12):
        angles = [math.pi + j * math.pi / 24, math.pi + (j + 1) * math.pi / 24]
        arc = [
            (corner[0] + 2.83 * math.cos(a), corner[1] + 3.05 * math.sin(a))
            for a in angles
        ]
        for h in (3.79, 4.21):
            body.face([(x, y, z + h) for x, y in (corner, *arc)], wall)
        body.face(
            [
                (*arc[0], z + 3.79),
                (*arc[1], z + 3.79),
                (*arc[1], z + 4.21),
                (*arc[0], z + 4.21),
            ],
            wall,
        )
    x_door = -268.35
    facade.box(x_door, -1025.13, z + 2.03, 9.12, 0.12, 3.16, dark)
    for dx in (-3.32, -1.10, 1.10, 3.32):
        facade.box(x_door + dx, -1025.23, z + 1.78, 2.07, 0.11, 2.44, C['tenGlass'])
        facade.box(
            x_door + dx, -1025.23, z + 3.31, 2.07, 0.11, 0.44, C['libraryMullion']
        )
    # The street view shows broad shallow steps and a second horizontal sign.
    body.box(x_door, -1026.51, z + 0.26, 11.2, 3.03, 0.52, C['gateStone'])
    flight(body, x_door, -1028.025, z, 11.2, 3, 0.36, 0.52 / 3, C['gateStone'])
    body.box(x_door, -1027.99, z + 4.05, 15.2, 0.26, 0.52, C['gateStone'])
    for x in (-279.1, -276.5, -274.4, -261.8, -259.1, -256.4, -253.7, -251.0):
        pane(facade, x, -1025.0, z + 1.91, 0.98, 2.85, (0, -1), C, detail)
    if detail:
        body.extend(
            inscription(
                '机械工程学院',
                x_door,
                -1028.15,
                z + 4.56,
                8.3,
                0.8,
                dark,
                True,
                flat=True,
                curve_resolution=2,
            )
        )
    for x in (x_door - 2.8, x_door + 2.8):
        body.cylinder(x, -1027.18, z + 2.13, 0.36, 3.27, C['libraryStone'], 16)
        body.cylinder(x, -1027.18, z + 0.58, 0.42, 0.14, C['libraryStone'], 16)
    facade.box(-281.63, -1015, z + 1.75, 0.12, 5.0, 3.0, dark)
    for y in (-1022, -1018.5, -1011.5, -1008):
        body.box(-283.3, y, z + 1.95, 0.4, 0.4, 3.9, white)
    for floor in range(5):
        for y in (-1022, -1018.7, -1015.4, -1012.1, -1008.8, -1005.5):
            facade.box(-281.62, y, z + 5.6 + floor * 3.35, 0.12, 1.9, 1.7, glass)
    # Street view 5 looks east at the west entrance and stacked open galleries.
    for floor in range(5):
        level = z + 4.13 + floor * 3.35
        body.box(-282.23, -1015.0, level, 1.5, 13.9, 0.22, white)
        body.box(-282.93, -1015.0, level + 0.49, 0.14, 13.9, 0.79, wall)
        for y in (-1021.84, -1008.16):
            body.box(-282.23, y, level + 0.49, 1.45, 0.14, 0.79, wall)
    m.add_part('01_主体轮廓', body)
    m.add_part('02_屋面', roof)
    m.add_part('机械学院窗格与入口', facade)
    return m
