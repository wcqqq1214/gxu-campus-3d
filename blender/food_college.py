"""East entrance of the light industry and food college, gallery 4 and panoramas."""

import math

from college_details import ellipse, pane, sign
from geometry import Mesh

BUILDING_ID = 'way/759080588'


def food_college(b, z, C, detail):
    m = Mesh()
    # Six main registers are visible on the long wing. The two setbacks
    # flanking the entrance have different roof levels in the east photo.
    blocks = [
        (-659.0, -607.03, -1123.96, -1101.44, 20.6),
        (-607.03, -593.96, -1120.21, -1101.46, 17.0),
        (-593.96, -572.42, -1120.21, -1109.53, 17.0),
        (-593.96, -572.42, -1109.53, -1100.47, 19.1),
        (-593.96, -571.94, -1100.47, -1088.47, 19.1),
        (-572.42, -571.08, -1120.21, -1109.53, 17.0),
    ]
    for left, right, south, north, height in blocks:
        m.box(
            (left + right) / 2,
            (south + north) / 2,
            z + (height - 0.5) / 2,
            right - left,
            north - south,
            height + 0.5,
            C['tenWall'],
        )
        m.box(
            (left + right) / 2,
            (south + north) / 2,
            z + height + 0.10,
            right - left + 0.10,
            north - south + 0.10,
            0.20,
            C['gateTrim'],
        )
    f = Mesh()
    # The front steps on the footprint include the canopy. Keep the ground
    # opening and the four upper loggias empty in front of their glazing.
    centre = -1105.0
    facade_x = -569.20
    back_x = -572.38
    balcony_back = -570.36
    m.box(
        (balcony_back + back_x) / 2,
        centre,
        z + 10.30,
        balcony_back - back_x,
        8.14,
        13.06,
        C['tenWall'],
    )
    for y in (centre - 4.96, centre + 4.96):
        m.box(-570.75, y, z + 10.55, 3.28, 1.88, 13.88, C['libraryStone'])
    m.box(-571.05, centre, z + 18.55, 4.32, 11.82, 3.42, C['tenWall'])
    for h, d, w in [(20.29, 4.65, 12.03), (20.62, 5.0, 12.38)]:
        m.box(-571.05, centre, z + h, d, w, 0.25, C['gateTrim'])
    for y in (centre - 3.5, centre, centre + 3.5):
        f.box(-568.82, y, z + 18.25, 0.22, 1.76, 1.76, C['libraryStone'])
        f.box(-568.68, y, z + 18.25, 0.12, 1.45, 1.45, C['dark'])
        ellipse(f, -568.60, y, z + 18.25, 1.23, 1.23, (1, 0), C['metal'])
        ellipse(f, -568.57, y, z + 18.25, 0.99, 0.99, (1, 0), C['tenGlass'])
        if detail:
            for side in (-1, 1):
                f.line(
                    (-568.53, y - 0.65, z + 18.25 - side * 0.65),
                    (-568.53, y + 0.65, z + 18.25 + side * 0.65),
                    0.035,
                    C['white'],
                )
    for level in range(4):
        base = z + 3.77 + 3.26 * level
        m.box(-570.80, centre, base + 0.08, 3.24, 8.12, 0.18, C['gateStone'])
        m.box(facade_x, centre, base + 0.60, 0.25, 8.12, 1.08, C['tenWall'])
        m.box(facade_x + 0.01, centre, base + 1.13, 0.30, 8.18, 0.11, C['gateTrim'])
        pane(
            f,
            balcony_back,
            centre,
            base + 1.92,
            7.94,
            2.18,
            (1, 0),
            C,
            detail,
            C['tenGlass'],
        )
        for off in (-3, -2, -1, 1, 2, 3):
            f.box(
                balcony_back + 0.25,
                centre + off,
                base + 1.92,
                0.08,
                0.07,
                2.17,
                C['white'],
            )
        pane(f, -571.92, -1093.35, base + 1.86, 1.20, 1.52, (1, 0), C, detail)
        for x, cy, w in [(-571.05, -1115.88, 8.55), (-571.92, -1094.47, 11.97)]:
            m.box(x + 0.06, cy, base + 1.11, 0.17, w, 0.17, C['libraryStone'])
    # The southern flank has ground plus four upper rows in the Foundation
    # photograph. The six rows to the west remain at their original spacing.
    for x0, x1, y, n, levels in [
        (-659, -607.03, -1123.99, 13, 6),
        (-607.03, -571.08, -1120.23, 9, 5),
    ]:
        for k in range(levels):
            for j in range(n):
                x = x0 + (j + 0.5) * (x1 - x0) / n
                pane(f, x, y, z + 1.87 + k * 3.26, 2.35, 1.82, (0, -1), C, detail)
    # At 331° the white rooftop enclosure extends behind part of the
    # five-storey wing. Its return depth and use are not visible.
    m.box(-582.8, -1117.12, z + 18.47, 17.6, 4.45, 2.94, C['white'])
    m.box(-582.8, -1117.12, z + 20.03, 18.04, 4.85, 0.20, C['libraryStone'])
    for x, width in ((-585.8, 1.36), (-578.55, 2.28)):
        pane(f, x, -1119.38, z + 18.37, width, 1.10, (0, -1), C, detail)
    # The south street view shows horizontal sills and a narrow ribbed panel
    # at the junction of the two wings.
    for k in range(1, 5):
        m.box(
            -584.54, -1120.51, z + k * 3.26 - 0.15, 26.85, 0.63, 0.40, C['libraryStone']
        )
    for j in range(5):
        m.box(
            -605.87 + j * 1.77, -1120.57, z + 8.48, 0.33, 0.83, 16.86, C['libraryStone']
        )
    # Independent 252°, 302° and 325° views show a deep, dark door band,
    # an open passage between two square columns, and returns at both ends.
    canopy_front = -564.94
    reach = canopy_front - back_x
    xmid = (canopy_front + back_x) / 2
    m.box(xmid, centre, z + 3.77, reach, 15.65, 0.40, C['libraryStone'])
    m.box(xmid, centre, z + 4.02, reach + 0.18, 15.88, 0.27, C['huicuiWall'])
    m.box(xmid, centre, z + 4.23, reach + 0.42, 16.16, 0.17, C['libraryStone'])
    m.box(xmid, centre, z, reach, 14.64, 0.27, C['gateStone'])
    # Darker facing at both sides of the shelter; the south bay is blind and
    # the north bay has a small service vent below its stack of narrow windows.
    for x, cy, width in ((-571.08, -1115.9, 8.5), (-571.94, -1094.4, 11.82)):
        m.box(x + 0.08, cy, z + 1.84, 0.15, width, 3.68, C['huicuiWall'])
        if detail:
            for height in (0.55, 1.1, 1.65, 2.2, 2.75, 3.3):
                m.box(x + 0.16, cy, z + height, 0.024, width, 0.020, C['gateJoint'])
    m.box(-571.75, -1093.5, z + 1.53, 0.09, 0.65, 0.36, C['dark'])
    for side in (-1, 1):
        y = centre + side * 4.92
        m.box(canopy_front - 1.0, y, z + 1.89, 0.74, 0.75, 3.56, C['huicuiWall'])
        m.box(canopy_front - 1.0, y, z + 0.31, 0.84, 0.83, 0.47, C['gateStone'])
        m.box(back_x + 0.72, y, z + 1.94, 1.45, 1.06, 3.54, C['huicuiWall'])
        if detail:
            for k in range(3):
                f.box(
                    back_x + 1.49, y, z + 1.36 + k * 0.46, 0.06, 0.67, 0.28, C['metal']
                )
    f.box(back_x + 0.12, centre, z + 1.89, 0.26, 9.04, 3.47, C['dark'])
    for j in range(6):
        y = centre + (j - 2.5) * 1.46
        f.box(back_x + 0.28, y, z + 1.44, 0.09, 1.39, 2.40, C['huicuiFrame'])
        f.box(back_x + 0.29, y, z + 3.04, 0.10, 1.39, 0.65, C['libraryMullion'])
        if detail:
            f.box(back_x + 0.35, y + 0.48, z + 1.33, 0.07, 0.04, 0.36, C['metal'])
    if detail:
        sign(
            f,
            '轻工与食品工程学院',
            canopy_front + 0.15,
            centre,
            z + 3.91,
            8.3,
            0.45,
            C['dark'],
            math.pi / 2,
        )
        sign(
            f,
            '轻工与食品工程学院',
            -568.49,
            centre,
            z + 21.35,
            11.15,
            0.91,
            C['gateRed'],
            math.pi / 2,
        )
    m.add_part('轻工学院东门与窗格', f)
    return m
