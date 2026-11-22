"""Street-view detail for laboratory buildings in the engineering precinct."""

from college_details import flight, pane, shell
from geometry import Mesh

LIGHTNING = 'way/759079684'
INORGANIC = 'way/759080586'
ENERGY = 'way/759079682'


def lightning_lab(b, z, C, detail):
    m = shell(b, z, 11.6, C['huicuiWall'], C['paleRoof'])
    f = Mesh()
    for x in (-145.49, -140.23, -134.88):
        for k in range(4):
            if abs(x + 140.23) < 1 and k < 2:
                continue
            h = z + 1.61 + k * 2.73
            pane(f, x, -981.58, h, 2.82, 1.90, (0, 1), C, detail)
            if detail:
                for dx in (-0.9, -0.45, 0.45, 0.9):
                    f.box(x + dx, -981.32, h, 0.047, 0.046, 1.88, C['metal'])
    for px in (-147.92, -142.87, -137.63, -132.1):
        m.box(px, -981.44, z + 5.78, 0.46, 0.43, 11.56, C['wallStone'])
    m.box(-140.22, -981.45, z + 2.76, 4.8, 0.27, 5.48, C['wood'])
    m.box(-140.22, -981.26, z + 2.76, 0.09, 0.10, 5.43, C['metal'])
    m.box(-140.22, -981.24, z + 3.68, 4.70, 0.09, 0.12, C['dark'])
    m.box(-140.22, -980.53, z + 5.68, 5.93, 2.3, 0.34, C['libraryStone'])
    # Metal verticals and a low continuous sill visible on the east/west
    # sides are left to the generic rows where trees hide their exact run.
    m.add_part('防雷实验室北侧工业门与高窗', f)
    return m


def inorganic_lab(b, z, C, detail):
    # The construction section gives 0.45 m outside-to-floor difference,
    # 4 m first storey, five at 3.8 m, deck +23.00, parapet +24.40.
    m = shell(b, z, 23.45, C['tenWall'], C['paleRoof'])
    import math

    ring = b['polygons'][0][0]
    for a, c in zip(ring, ring[1:]):
        length = math.dist(a, c)
        m.box(
            (a[0] + c[0]) / 2,
            (a[1] + c[1]) / 2,
            z + 24.15,
            length,
            0.22,
            1.4,
            C['tenWall'],
            math.atan2(c[1] - a[1], c[0] - a[0]),
        )
    # In the mirrored plan, axis 1 is at the east. The lift and fan house
    # straddle the connector between the two roofs, not the whole seventh floor.
    m.box(-527.85, -1072.22, z + 25.18, 10.72, 12.85, 3.46, C['tenWall'])
    m.box(-527.85, -1072.22, z + 27.02, 11.04, 13.15, 0.24, C['paleRoof'])
    for x, y, w, d in ((-509.8, -1074.2, 7.4, 2.0), (-555.3, -1072.8, 4.8, 2.6)):
        m.box(x, y, z + 24.43, w, d, 1.96, C['libraryStone'])
    for x, y, w in (
        (-514.9, -1074.0, 9.6),
        (-505.8, -1071.7, 7.2),
        (-548.5, -1073.3, 8.5),
        (-548.9, -1076.0, 7.3),
    ):
        m.box(x, y, z + 24.20, w, 0.72, 1.50, C['gateStone'])
    f = Mesh()
    # North entrance at x~-523 is seen from (-523.1,-1053.7).
    for k in range(6):
        h = z + (0.45 if k == 0 else 4.45 + (k - 1) * 3.8) + 1.90
        for x0, x1, y, n in (
            (-569.3, -535.2, -1068.2, 9),
            (-535.1, -507.4, -1062.97, 7),
        ):
            for j in range(n):
                x = x0 + (j + 0.5) * (x1 - x0) / n
                if k == 0 and abs(x + 523) < 6:
                    continue
                pane(f, x, y, h, 2.15, 2.07, (0, 1), C, detail)
                if y > -1064 and abs(x + 523) < 6.6 and k >= 2:
                    m.box(x - 1.68, y + 0.38, h, 0.28, 0.87, 3.8, C['gateStone'])
            m.box(
                (x0 + x1) / 2, y + 0.21, h - 1.28, x1 - x0, 0.55, 0.25, C['gateStone']
            )
    m.box(-523, -1061.85, z + 3.73, 14.5, 2.8, 0.73, C['libraryStone'])
    for x in (-529.25, -523, -516.75):
        m.box(x, -1060.74, z + 1.85, 0.75, 0.8, 3.24, C['huicuiWall'])
    f.box(-523, -1062.8, z + 1.77, 6, 0.18, 2.82, C['dark'])
    m.box(-523, -1061.65, z + 0.27, 14.5, 2.8, 0.54, C['gateStone'])
    flight(m, -523, -1060.25, z, 14.5, 3, 0.35, 0.18, C['gateStone'], north=True)
    for k in range(1, 6):
        h = z + 4.45 + (k - 1) * 3.80
        m.box(-498.49, -1072.75, h, 1.34, 7.0, 0.25, C['gateTrim'])
        m.box(-497.88, -1072.75, h + 0.47, 0.13, 7.0, 0.78, C['tenWall'])
    # Sheet 7 is the 17.4 m infill between grids 10 and 14 on the back
    # of the block. Only this elevation receives the five documented lights.
    for k in range(6):
        floor = 0.45 if k == 0 else 4.45 + (k - 1) * 3.8
        for j in range(5):
            x = -549.15 + j * 2.83
            pane(
                f,
                x,
                -1085.98,
                z + floor + 0.9 + 1.17,
                1.80,
                2.34,
                (0, -1),
                C,
                detail,
                C['tenGlass'],
            )
    m.box(-541.9, -1086.04, z + 0.59, 17.35, 0.22, 1.18, C['huicuiWall'])
    m.box(-523, -1060.53, z + 4.34, 14.65, 0.48, 1.35, C['libraryStone'])
    for px in (-529.4, -525.2, -520.7, -516.6):
        m.box(px, -1060.68, z + 5.48, 0.42, 0.49, 1.5, C['gateStone'])
    m.box(-523, -1060.66, z + 6.36, 14.68, 0.60, 0.32, C['gateStone'])
    m.add_part('北门与实验楼窗格', f)
    return m


def energy_center(b, z, C, detail):
    """Campus map locates the centre between the language building and mechanical.
    Use the older street views for the two/three-storey height break only."""
    m = Mesh()
    f = Mesh()
    # West gallery block and lower eastern red-tile wing overlap at the party wall.
    m.box(-262.93, -974.65, z + 5.05, 39.1, 13.51, 10.90, C['tenWall'])
    m.box(-224.49, -974.65, z + 3.43, 37.8, 13.51, 7.66, C['pink'])
    m.box(-199.81, -976.63, z + 3.43, 12.86, 9.67, 7.66, C['pink'])
    m.box(-262.93, -974.65, z + 10.60, 39.9, 14.25, 0.28, C['gateTrim'])
    for x, y, w, d in (
        (-224.47, -974.64, 38.3, 14.2),
        (-199.81, -976.64, 13.48, 10.42),
    ):
        m.roof(x, y, z + 7.26, w, d, 1.75, C['red'])
    for k in range(3):
        h = z + 1.76 + 3.47 * k
        m.box(-262.93, -967.01, h - 1.72, 38.8, 2.08, 0.19, C['gateStone'])
        for j in range(7):
            x = -279.8 + 5.64 * j
            m.box(x, -966.35, h, 0.56, 0.64, 3.46, C['red'])
            pane(f, x + 1.95, -967.89, h, 2.6, 1.67, (0, 1), C, detail)
            if k:
                m.box(x + 2.80, -966.36, h - 0.78, 5.5, 0.15, 0.15, C['white'])
                for n in range(9):
                    m.cylinder(
                        x + 0.58 + n * 0.56, -966.36, h - 1.17, 0.10, 0.7, C['white'], 6
                    )
        for j in range(10):
            pane(f, -280.4 + j * 3.84, -981.48, h, 1.80, 1.6, (0, -1), C, detail)
    for j in range(9):
        for k in range(2):
            pane(
                f,
                -241.27 + j * 4.08,
                -967.92,
                z + 1.68 + k * 3.55,
                1.6,
                1.68,
                (0, 1),
                C,
                detail,
            )
    for k in range(2):
        for j in range(12):
            pane(
                f,
                -241.1 + j * 4.02,
                -981.48,
                z + 1.68 + k * 3.55,
                1.65,
                1.68,
                (0, -1),
                C,
                False,
            )
        for y in (-971.6, -975.35, -979.0):
            pane(f, -282.49, y, z + 1.68 + k * 3.55, 1.62, 1.68, (-1, 0), C, False)
    for px in (-202.9, -198.0):
        pane(f, px, -971.78, z + 5.25, 1.28, 1.67, (0, 1), C, detail)
    f.box(-199.9, -971.69, z + 1.52, 1.62, 0.16, 2.93, C['wood'])
    m.box(-199.9, -971.22, z + 3.17, 2.81, 1.24, 0.20, C['libraryStone'])
    m.add_part('红楼外廊与东翼', f)
    return m


FOOD_ANNEX = 'way/759080587'
ELECTRIC_CENTER = 'relation/20510975'
ENVIRONMENT = 'way/759170251'


def food_annex(b, z, C, detail):
    """Former inorganic building north of the food college. North side observable."""
    m = Mesh()
    f = Mesh()
    for xmin, xmax, ymin, ymax, h in (
        (-652.52, -632.79, -1081.56, -1065.15, 14.8),
        (-632.79, -598.87, -1083.68, -1065.18, 14.8),
        (-598.87, -590.18, -1083.69, -1076.78, 7.2),
    ):
        m.box(
            (xmin + xmax) / 2,
            (ymin + ymax) / 2,
            z + (h - 0.5) / 2,
            xmax - xmin,
            ymax - ymin,
            h + 0.5,
            C['tenWall'],
        )
        m.box(
            (xmin + xmax) / 2,
            (ymin + ymax) / 2,
            z + h + 0.12,
            xmax - xmin + 0.4,
            ymax - ymin + 0.45,
            0.24,
            C['gateStone'],
        )
    for j in range(14):
        x = -650.64 + j * 3.79
        for k in range(4):
            pane(f, x, -1065.12, z + 1.83 + k * 3.63, 2.12, 1.82, (0, 1), C, detail)
        m.box(x - 1.57, -1065.00, z + 8.13, 0.36, 0.42, 13.1, C['gateStone'])
    # In the oblique street view the east end has broad horizontal windows;
    # a short low return meets the higher block.
    for k in (1, 2, 3):
        h = z + 1.83 + k * 3.63
        # Window ribbons return around the projecting east-end family of bays.
        pane(f, -598.15, -1069.35, h, 5.72, 2.41, (1, 0), C, detail)
        m.box(-598.53, -1069.35, h - 1.52, 1.19, 6.65, 0.62, C['tenWall'])
        m.box(-598.53, -1069.35, h + 1.37, 1.29, 6.76, 0.25, C['gateTrim'])
        for y in (-1072.38, -1066.32):
            pane(f, -598.5, y, h, 0.67, 2.4, (0, 1 if y > -1070 else -1), C, detail)
    # The 288° and 300° views across the food college forecourt show a
    # lower box in front of two upper ribbon lights. Their shared jamb
    # triangulates to about (-593.2, -1078.2), inside the annex footprint.
    # The depth of the back wall and the end behind the trees are estimated.
    m.box(-596.03, -1080.24, z + 6.81, 5.68, 6.90, 13.62, C['tenWall'])
    m.box(-596.03, -1080.24, z + 13.68, 5.93, 7.11, 0.22, C['libraryStone'])
    for height in (9.13, 12.23):
        for x, y, width in ((-593.15, -1077.53, 1.44), (-598.82, -1074.58, 4.33)):
            f.box(x + 0.05, y, z + height, 0.13, width, 2.17, C['dark'])
            f.box(x + 0.14, y + width * 0.10, z + height, 0.10,
                  width * 0.73, 2.01, C['libraryGlass'])
            if detail:
                for j in range(4):
                    f.box(x + 0.21, y + (j - 1.5) * width * 0.21,
                          z + height, 0.05, 0.05, 2.06, C['metal'])
            m.box(x + 0.04, y, z + height - 1.19, 0.44, width + 0.10,
                  0.25, C['tenWall'])
    # A wide metal-framed ground light sits under the blind apron of the
    # low east tip. The service opening alongside it is visible in low-0.
    f.box(-590.14, -1081.03, z + 1.48, 0.18, 4.94, 2.57, C['huicuiFrame'])
    for j in range(6):
        f.box(-590.02, -1083.38 + j * 0.94, z + 1.48, 0.08, 0.06, 2.59, C['metal'])
    f.box(-590.01, -1081.03, z + 1.94, 0.08, 4.96, 0.065, C['metal'])
    m.box(-590.06, -1081.03, z + 2.88, 0.54, 5.15, 0.18, C['libraryStone'])
    f.box(-590.04, -1077.47, z + 4.83, 0.16, 0.67, 1.24, C['dark'])
    # Ground-level double door below the east return, visible on the 231° view.
    f.box(-598.70, -1069.75, z + 1.53, 0.26, 3.02, 3.05, C['wood'])
    f.box(-598.51, -1069.75, z + 1.53, 0.10, 0.09, 3.05, C['dark'])
    for x in (-597.1, -593.7):
        for k in range(2):
            pane(f, x, -1076.76, z + 1.65 + k * 3.52, 2.12, 1.73, (0, 1), C, detail)
    m.add_part('原无机楼北立面与低翼', f)
    return m


def electric_center(b, z, C, detail):
    """Rounded west head of the eastern experimental centre; the court stays open."""
    import math

    m = shell(b, z, 21.20, C['tenWall'], C['paleRoof'])
    f = Mesh()
    ring = b['polygons'][0][0]
    for i, (a, c) in enumerate(zip(ring, ring[1:])):
        if i not in (*range(0, 11), 16, 17):
            continue
        dx, dy = c[0] - a[0], c[1] - a[1]
        length = math.hypot(dx, dy)
        nx, ny = -dy / length, dx / length
        x, y = (a[0] + c[0]) / 2, (a[1] + c[1]) / 2
        angle = math.atan2(dy, dx)
        if i in (7, 8, 9, 10):
            for k in range(6):
                for j in range(3):
                    t = (j + 0.5) / 3
                    pane(
                        f,
                        a[0] + t * dx,
                        a[1] + t * dy,
                        z + 1.84 + k * 3.43,
                        1.64,
                        1.36,
                        (nx, ny),
                        C,
                        detail,
                    )
            continue
        # Continuous greenish glazing and white slab edges along the mapped arc.
        for k in range(1, 6):
            h = z + 1.87 + k * 3.42
            f.box(
                x + nx * 0.10,
                y + ny * 0.10,
                h,
                length + 0.03,
                0.22,
                2.82,
                C['residenceGlass'],
                angle,
            )
            m.box(
                x + nx * 0.26,
                y + ny * 0.26,
                h - 1.48,
                length + 0.35,
                0.64,
                0.39,
                C['gateTrim'],
                angle,
            )
            if detail:
                for t in (0.25, 0.75):
                    f.box(
                        a[0] + dx * t + nx * 0.25,
                        a[1] + dy * t + ny * 0.25,
                        h,
                        0.065,
                        0.06,
                        2.82,
                        C['metal'],
                        angle,
                    )
        m.box(
            x + nx * 0.18,
            y + ny * 0.18,
            z + 21.28,
            length + 0.28,
            0.48,
            0.23,
            C['gateTrim'],
            angle,
        )
    # The 108° and 82° close views show the lowest curved window bank behind
    # vertical blinds and a two-level open metal frame over the northern lane.
    for i in (0, 1, 2, 3, 4, 5, 6, 16, 17):
        a, c = ring[i], ring[i + 1]
        dx, dy = c[0] - a[0], c[1] - a[1]
        length = math.hypot(dx, dy)
        nx, ny = -dy / length, dx / length
        angle = math.atan2(dy, dx)
        x, y = (a[0] + c[0]) / 2, (a[1] + c[1]) / 2
        m.box(
            x + nx * 0.14,
            y + ny * 0.14,
            z + 2.0,
            length,
            0.31,
            2.9,
            C['huicuiWall'],
            angle,
        )
        if detail:
            for j in range(max(2, round(length / 0.26))):
                t = (j + 0.5) / max(2, round(length / 0.26))
                f.box(
                    a[0] + dx * t + nx * 0.32,
                    a[1] + dy * t + ny * 0.32,
                    z + 2.0,
                    0.048,
                    0.07,
                    2.9,
                    C['gateJoint'],
                    angle,
                )
    # Street geometry locates the frame just north of the junction between
    # the curved end and straight flank. Post spacing and overhang are estimates.
    front_posts = [(626.6, -621.1), (624.8, -614.1), (637.4, -610.4)]
    for x, y in front_posts:
        m.cylinder(x, y, z + 4.75, 0.28, 9.50, C['courtMetal'], 16)

    def beam(a, c, h):
        dx, dy = c[0] - a[0], c[1] - a[1]
        m.box(
            (a[0] + c[0]) / 2,
            (a[1] + c[1]) / 2,
            z + h,
            math.hypot(dx, dy),
            0.38,
            0.52,
            C['courtMetal'],
            math.atan2(dy, dx),
        )

    for h in (3.83, 7.28):
        beam(front_posts[0], front_posts[1], h)
        beam(front_posts[1], front_posts[2], h)
        beam(front_posts[2], (640.7, -617.8), h)
    beam(front_posts[1], (639.2, -618.6), 7.28)
    m.add_part('新东园实验中心弧形层带', f)
    return m


def environment_center(b, z, C, detail):
    """Long lab aligned to the rotated street grid; two independently located doors."""
    import math

    m = shell(b, z, 25.1, C['tenWall'], C['paleRoof'])
    f = Mesh()
    r = b['polygons'][0][0]
    a, e = r[3], r[0]
    dx, dy = e[0] - a[0], e[1] - a[1]
    angle = math.atan2(dy, dx)
    length = math.hypot(dx, dy)
    depth = math.dist(r[2], r[3])

    # Build in the local street frame (+Y toward the north frontage).
    def box(s, t, h, w, d, ht, mat):
        f.box(a[0] + s, a[1] + t, z + h, w, d, ht, C[mat])

    for k in range(7):
        h = 1.91 + 3.56 * k
        for j in range(24):
            s = (j + 0.5) * length / 24
            for side in (1, -1):
                t = 0 if side == 1 else -depth
                door = 55 if side == 1 else 54
                if k == 0 and abs(s - door) < 7:
                    continue
                pane(f, a[0] + s, a[1] + t, z + h, 2.82, 1.93, (0, side), C, detail)
        for side in (1, -1):
            box(
                length / 2,
                (0.16 if side == 1 else -depth - 0.16),
                h - 1.24,
                length,
                0.45,
                0.19,
                'libraryStone',
            )
    for j in range(13):
        box(1.5 + j * (length - 3) / 12, 0.22, 14.2, 0.46, 0.66, 21.3, 'libraryStone')
    for side, s, t, width in ((1, 55, 0, 14.2), (-1, 54, -depth, 13.3)):
        box(s, t + side * 1.32, 3.93, width, 3.13, 0.55, 'gateStone')
        box(s, t + side * 1.22, 0.25, width, 2.55, 0.50, 'gateStone')
        for px in (s - width * 0.41, s + width * 0.41):
            box(px, t + side * 2.55, 2.06, 0.68, 0.75, 3.2, 'libraryStone')
        pane(f, a[0] + s, a[1] + t, z + 1.94, 4.1, 2.83, (0, side), C, detail)
        flight(
            f,
            a[0] + s,
            a[1] + t + side * 2.495,
            z,
            width,
            3,
            0.32,
            0.50 / 3,
            C['gateStone'],
            north=side == 1,
        )
    # The north porch has a deep fascia, open upper lights and two plaque
    # piers. Visible rectangles are represented without inventing unit names.
    box(55, 2.70, 4.32, 14.3, 0.53, 1.06, 'libraryStone')
    box(55, 2.70, 5.54, 6.9, 0.51, 0.29, 'gateStone')
    for shift in (-3.28, -1.03, 1.03, 3.28):
        box(55 + shift, 2.70, 5.02, 0.28, 0.46, 0.9, 'gateStone')
    for shift in (-5.73, 5.73):
        box(55 + shift, 2.64, 2.08, 1.60, 0.81, 2.83, 'huicuiFrame')
        for j in range(2):
            for k in range(4):
                box(
                    55 + shift + (j - 0.5) * 0.65,
                    3.065,
                    2.89 - k * 0.38,
                    0.60,
                    0.05,
                    0.30,
                    'timeLetter',
                )
    # The open west-end stair is visible from both the northern and southern lanes.
    for k in range(6):
        for half in (0, 1):
            base = k * 3.56 + half * 1.78
            x = a[0] - 2.5 - half * 1.6
            for j in range(11):
                t = -depth * 0.5 + (j - 5) * 0.32 * (1 if half == 0 else -1)
                f.box(
                    x,
                    a[1] + t,
                    z + base + (j + 1) * 1.78 / 11,
                    1.56,
                    0.34,
                    0.20,
                    C['gateStone'],
                )
            t = -depth * 0.5 + (1.94 if half == 0 else -1.94)
            box(-3.14, t, base + 1.78, 6.55, 1.0, 0.24, 'gateStone')
            box(
                -3.14,
                t + (0.45 if half == 0 else -0.45),
                base + 2.20,
                6.55,
                0.14,
                0.77,
                'tenWall',
            )
    box(55, -depth / 2, 25.86, 10.1, 7.1, 1.52, 'libraryStone')
    box(55, -depth / 2, 26.75, 12.5, 9.4, 0.26, 'gateTrim')
    f.rotate_z(a[0], a[1], angle)
    m.add_part('环境楼双面门廊与西端楼梯', f)
    return m
