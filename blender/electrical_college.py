"""Electrical engineering building, south street front and east stair galleries."""

import math

from college_details import ellipse, pane, shell
from geometry import Mesh

BUILDING_ID = 'way/759096561'


def electrical_college(b, z, C, detail):
    m = shell(b, z, 33, C['gateTrim'], C['paleRoof'])
    # The retained east shell soffit is above the street by up to a metre.
    # Continue only the exposed three wall segments down to their bedding.
    ring = b['polygons'][0][0]
    ne, se = ring[:2]
    for a, c in (
        (ne, se),
        (se, (-315.0, se[1] + 0.011)),
        ((-315.0, ne[1] + 0.011), ne),
    ):
        m.face(
            [(*a, z - 0.5), (*c, z - 0.5), (*c, z - 2.55), (*a, z - 2.55)],
            C['bridgeConcrete'],
        )
    f = Mesh()
    for level in range(10):
        h = z + (level + 0.54) * 3.3
        for j in range(13):
            x = -362.5 + j * 4.12
            if level == 0 and x < -358:
                continue
            pane(f, x, -824.32, h, 2.7, 1.83, (0, -1), C, detail)
            if level > 0:
                m.box(x - 1.87, -824.63, h, 0.22, 0.83, 3.26, C['gateTrim'])
        if level:
            m.box(-337.8, -824.83, h - 1.55, 53.2, 1.26, 0.18, C['gateStone'])
            m.box(-337.8, -825.46, h - 1.42, 53.2, 0.14, 0.31, C['gateTrim'])
            m.box(-337.8, -825.46, h - 0.58, 53.2, 0.12, 0.10, C['metal'])
            for j in range(27):
                m.box(-363.8 + j * 2, -825.46, h - 0.93, 0.07, 0.07, 0.77, C['metal'])
            if detail:
                for j in range(1, 152):
                    m.box(
                        -364.25 + j * 0.35,
                        -825.46,
                        h - 0.94,
                        0.035,
                        0.04,
                        0.73,
                        C['metal'],
                    )
    # Both end towers flank the south facade. The east-facing openings appear
    # next to alternating open slots on the projected landings (gallery 1).
    for x, nx in ((-307.45, 1), (-368.22, -1)):
        if nx > 0:
            # Two street views show a continuous grey course on the round foot.
            # Keep the original 32-sided perimeter and roof level. The apron
            # meets the visible east side below the old cylinder bottom.
            rings = [
                [
                    (
                        x + 2.46 * math.cos(i * math.tau / 32),
                        -821.94 + 2.46 * math.sin(i * math.tau / 32),
                        h,
                    )
                    for i in range(32)
                ]
                for h in (z - 2.55, z - 1.30, z + 33.26)
            ]
            for low, high, finish in zip(
                rings, rings[1:], ('bridgeConcrete', 'gateTrim')
            ):
                for i in range(32):
                    j = (i + 1) % 32
                    m.face([low[i], low[j], high[j], high[i]], C[finish])
            m.face(rings[-1], C['gateTrim'])
            m.face(rings[0][::-1], C['bridgeConcrete'])
        else:
            m.cylinder(x, -821.94, z + 16.63, 2.46, 33.26, C['gateTrim'], 32)
        # Straight solid return between the rounded nose and the gallery.
        # In the south street photograph the bright uprights run roof to pavement.
        m.box(x - nx * 1.92, -823.1, z + 16.56, 3.82, 2.58, 33.12, C['gateTrim'])
        for k in range(8):
            h = z + 4.56 + k * 3.47
            ellipse(f, x + nx * 2.47, -821.94, h, 1.16, 1.48, (nx, 0), C['metal'])
            ellipse(f, x + nx * 2.50, -821.94, h, 0.93, 1.23, (nx, 0), C['dark'])
            if detail:
                m.box(x + nx * 2.52, -821.94, h, 0.09, 0.07, 1.18, C['metal'])
    for k in range(9):
        h = z + 4.4 + k * 3.43
        for wall, normal in ((-306.42, 1), (-369.27, -1)):
            face = wall + normal * 1.82
            m.box(
                wall + normal * 0.8, -813.5, h - 1.27, 2.32, 10.0, 0.28, C['gateTrim']
            )
            for j in range(4):
                m.box(
                    face, -817.72 + j * 2.48, h - 0.63, 0.23, 1.26, 1.14, C['gateTrim']
                )
            m.box(face, -813.5, h - 0.09, 0.24, 9.98, 0.21, C['gateTrim'])
            m.box(face, -813.5, h - 0.98, 0.24, 9.98, 0.56, C['gateTrim'])
            if k == 8:
                # The upper landing is glazed beneath a solid fascia; both
                # the eastern 281 degree and western 58 degree views show it.
                m.box(face, -813.5, h + 0.84, 0.19, 9.78, 1.58, C['residenceGlass'])
                for j in range(7):
                    m.box(
                        face + normal * 0.15,
                        -818.34 + j * 1.61,
                        h + 0.84,
                        0.11,
                        0.09,
                        1.60,
                        C['metal'],
                    )
                m.box(
                    wall + normal * 0.84,
                    -813.5,
                    z + 33.16,
                    2.56,
                    10.68,
                    0.53,
                    C['gateTrim'],
                )
    # In the frontal street view the middle seven top bays stand forward
    # of both end bays. Each has a soffit, side cheeks and a solid sill.
    for j in range(3, 10):
        x = -362.5 + j * 4.12
        m.box(x - 1.99, -825.9, z + 31.33, 0.29, 3.24, 3.36, C['gateTrim'])
        m.box(x, -825.9, z + 29.85, 4.12, 3.24, 0.39, C['gateTrim'])
        m.box(x, -827.39, z + 30.42, 4.12, 0.27, 1.18, C['gateTrim'])
        m.box(x, -825.9, z + 33.06, 4.12, 3.24, 0.34, C['gateTrim'])
        pane(f, x, -826.88, z + 31.96, 3.48, 1.77, (0, -1), C, detail, C['tenGlass'])
    m.box(-323.50, -825.9, z + 31.33, 0.29, 3.24, 3.36, C['gateTrim'])
    # The west tower street view shows glazing below the projecting fascia.
    m.box(-361.4, -825.40, z + 3.72, 8.9, 2.68, 0.56, C['gateTrim'])
    m.box(-361.4, -824.53, z + 1.58, 7.6, 0.37, 3.12, C['libraryMullion'])
    for x in (-363.94, -361.40, -358.86):
        pane(
            f, x, -824.73, z + 1.60, 2.32, 2.80, (0, -1), C, detail, C['residenceGlass']
        )
    m.add_part('电气端塔圆窗与南立面', f)
    return m
