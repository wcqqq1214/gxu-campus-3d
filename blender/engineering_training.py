"""Visible north and curved west frontage of the engineering training centre.

Geolocated 2019 street views show a two-storey light facade with a curved
canopy at its north-west corner. Canopy depth and individual bays are estimated.
"""

import math

from college_details import pane
from geometry import Mesh

BUILDING_ID = 'way/759079685'


def add_training_front(b, result, z, C, detail):
    if abs(b['bounds'][0] + 268.77) > 1:
        raise ValueError('Training centre footprint changed; recheck references')
    body, glazing = Mesh(), Mesh()
    # North wall faces the mechanical college courtyard.
    for x in (-255, -250.4, -245.8, -241.2, -236.6, -232, -227.4, -222.8, -218.2):
        for height in (1.75, 5.0):
            if height < 2 and x == -227.4:
                continue
            glazing.box(x, -1043.40, z + height, 3.15, 0.12, 2.0, C['glass'])
            if detail:
                glazing.box(x, -1043.31, z + height, 0.06, 0.08, 2.0, C['white'])
    # Outline follows the three straight segments in the mapped curved corner.
    inner = [
        (-268.76, -1057.70),
        (-265.68, -1051.01),
        (-262.75, -1047.67),
        (-257.33, -1043.47),
    ]
    outer = [(x - 2.6, y + 2.0) for x, y in inner]
    for a, b0, c, d in zip(inner, inner[1:], outer[1:], outer):
        dx, dy = c[0] - d[0], c[1] - d[1]
        span = math.hypot(dx, dy)
        angle = math.atan2(dy, dx)
        # Bronze roof grid over translucent panels; the lower curved beam is
        # open above and below. Two full-height piers are visible in the court.
        body.face([(x, y, z + 6.75) for x, y in (a, b0, c, d)], C['gateTrim'])
        for height, depth, thickness, mat in (
            (6.74, 0.22, 0.30, 'wood'),
            (3.26, 0.44, 0.44, 'residenceStone'),
        ):
            body.box(
                (c[0] + d[0]) / 2,
                (c[1] + d[1]) / 2,
                z + height,
                span + 0.07,
                depth,
                thickness,
                C[mat],
                angle,
            )
        for t in (0, 0.33, 0.66):
            x, y = a[0] + t * dx, a[1] + t * dy
            body.line((x, y, z + 6.65), (x - 2.6, y + 2, z + 6.65), 0.10, C['wood'])
        body.line(
            (a[0] - 1.3, a[1] + 1, z + 6.65),
            (b0[0] - 1.3, b0[1] + 1, z + 6.65),
            0.08,
            C['wood'],
        )
    for x, y in outer[1:3]:
        body.box(x, y, z + 3.28, 0.48, 0.57, 6.56, C['residenceStone'])
    for x, y in (inner[0], inner[-1]):
        body.box(x, y, z + 3.38, 1.28, 1.30, 6.76, C['residencePodium'])
    glazing.box(-227.4, -1043.36, z + 1.68, 4.38, 0.24, 3.32, C['dark'])
    # Workshop glazing follows the corner rather than stopping at the bend.
    for a, c in zip(inner, inner[1:]):
        dx, dy = c[0] - a[0], c[1] - a[1]
        length = math.hypot(dx, dy)
        for t in (0.25, 0.75):
            for h in (1.7, 4.98):
                pane(
                    glazing,
                    a[0] + dx * t,
                    a[1] + dy * t,
                    z + h,
                    length * 0.40,
                    2.1,
                    (-dy / length, dx / length),
                    C,
                    detail,
                )
    result.add_part('工程训练中心弧形廊架', body)
    result.add_part('工程训练中心北立面', glazing)
    return result
