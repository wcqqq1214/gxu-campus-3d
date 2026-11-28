"""Teaching animal hospital on Luban Road, fitted to the four mapped corners."""

from geometry import Mesh
from humanities_facades import finish
from south_gate import inscription

LENGTH = 53.32
DEPTH = 15.86
STOREY = 3.15
ROOF = 20.7


def glazing(
    mesh, x, y, bottom, width, height, panes, C, detail, *, rear=False, screened=False
):
    direction = 1 if rear else -1

    def panel(cx, cz, w, h, offset, finish):
        yy = y + offset * direction
        pts = [
            (cx - w / 2, yy, cz - h / 2),
            (cx + w / 2, yy, cz - h / 2),
            (cx + w / 2, yy, cz + h / 2),
            (cx - w / 2, yy, cz + h / 2),
        ]
        mesh.face(pts[::-1] if rear else pts, C[finish])

    panel(
        x,
        bottom + height / 2,
        width,
        height,
        0.025,
        'vetWestScreenBalanced' if screened else 'glass',
    )
    if detail:
        for i in range(panes + 1):
            panel(
                x - width / 2 + width * i / panes,
                bottom + height / 2,
                0.07,
                height,
                0.045,
                'white',
            )
        if screened:
            for sash in range(panes):
                for bar in range(1, 6):
                    cx = x - width / 2 + width * (sash + bar / 6) / panes
                    panel(cx, bottom + height / 2, 0.021, height, 0.067, 'paleRoof')
        for t in (0, 0.72, 1):
            panel(x, bottom + height * t, width, 0.07, 0.055, 'white')


def build(l, b, z, C, detail):
    m = Mesh()
    # x runs south along the street frontage, y east towards the lake.
    # Neutral screened-window appearance sampled separately from the entrance glass.
    finish(C, 'vetWestScreenBalanced', (0.410, 0.425, 0.414), 0.64)
    finish(C, 'vetCanopyPanel', (0.74, 0.75, 0.74), 0.48, 0.18)
    pocket_left, pocket_right, recess = 4.43, 8.23, 1.85
    outline = [
        (0, 0),
        (pocket_left, 0),
        (pocket_left, recess),
        (pocket_right, recess),
        (pocket_right, 0),
        (LENGTH, 0),
        (LENGTH, DEPTH),
        (0, DEPTH),
    ]
    for a, bxy in zip(outline, outline[1:] + outline[:1]):
        m.face([(*a, 0), (*bxy, 0), (*bxy, ROOF), (*a, ROOF)], C['white'])
    roof_tail = LENGTH - pocket_right
    m.box(
        pocket_right + roof_tail / 2,
        DEPTH / 2,
        ROOF + 0.08,
        roof_tail,
        DEPTH,
        0.16,
        C['paleRoof'],
    )
    m.box(
        pocket_right / 2,
        (DEPTH + recess) / 2,
        ROOF + 0.08,
        pocket_right,
        DEPTH - recess,
        0.16,
        C['paleRoof'],
    )
    pocket_width = pocket_right - pocket_left
    pocket_x = (pocket_left + pocket_right) / 2
    # The end landing is half a storey higher; the open frame rises above its ceiling.
    m.box(pocket_left / 2, 4, ROOF + 2.05, pocket_left, 8, 4.10, C['white'])
    m.box(
        pocket_x,
        (8 + recess) / 2,
        ROOF + 0.77,
        pocket_width,
        8 - recess,
        1.54,
        C['white'],
    )
    m.box(pocket_x, recess / 2, ROOF + 1.51, pocket_width, recess, 0.24, C['paleRoof'])
    m.box(pocket_right - 0.1, 0.10, ROOF + 2.05, 0.2, 0.22, 4.10, C['white'])
    m.box(pocket_x, 0.10, ROOF + 3.97, pocket_width, 0.22, 0.26, C['white'])
    m.box(34.6, DEPTH - 2.2, ROOF + 0.77, 8.0, 4.8, 1.54, C['white'])
    # The lower stair head window straddles the eaves.
    glazing(m, 36.65, DEPTH + 0.33, 19.68, 1.75, 0.94, 3, C, detail, rear=True)
    glazing(m, 31.9, DEPTH + 0.33, 20.46, 1.28, 1.38, 2, C, detail, rear=True)
    m.box(LENGTH / 2, -0.02, 0.78, LENGTH, 0.12, 1.56, C['metal'])
    for level in range(6):
        base = 1.6 + level * STOREY
        landing = base + 1.70
        m.box(LENGTH / 2, DEPTH, base + 2.94, LENGTH, 0.62, 0.19, C['paleRoof'])
        m.box(
            pocket_right + roof_tail / 2,
            0,
            base + 2.94,
            roof_tail,
            0.62,
            0.19,
            C['paleRoof'],
        )
        glazing(m, 2.2, 0, landing + 0.62, 2.3, 1.46, 2, C, detail)
        glazing(m, 50.8, 0, base + 0.62, 2.1, 1.46, 2, C, detail)
        # The north-end gallery has a recessed back wall and a vertical balustrade.
        m.box(pocket_x, recess / 2, landing, pocket_width, recess, 0.20, C['paleRoof'])
        for h in (0.15, 0.95):
            m.box(pocket_x, -0.04, landing + h, pocket_width, 0.065, 0.055, C['white'])
        count = 22 if detail else 11
        for i in range(count):
            xx = pocket_left + (i + 0.5) * pocket_width / count
            m.box(xx, -0.04, landing + 0.54, 0.037, 0.048, 0.83, C['paleRoof'])
        for bay in range(5):
            left = 8.4 + bay * 7.92 + 0.19
            right = left + 7.54
            if not level and bay == 3:
                right = 34.25
            if not level and bay == 4:
                left = 43.75
            glazing(
                m,
                (left + right) / 2,
                0,
                base + 0.54,
                right - left,
                2.12,
                6 if right - left > 5 else 3,
                C,
                detail,
                screened=True,
            )
            if right - left > 5:
                m.box(
                    (left + right) / 2,
                    -0.084,
                    base + 1.60,
                    0.22,
                    0.075,
                    2.15,
                    C['white'],
                )
            # Six horizontal rails are resolved in the opening-day photograph.
            if level or bay < 3:
                for h in (0.22, 0.39, 0.56, 0.73, 0.90, 1.12):
                    m.box(
                        (left + right) / 2,
                        -0.31,
                        base + h,
                        right - left,
                        0.062,
                        0.055,
                        C['white'],
                    )
                for i in range(5):
                    xx = left + (right - left) * i / 4
                    m.box(xx, -0.30, base + 0.65, 0.07, 0.065, 1.06, C['paleRoof'])
        for bay in range(14):
            x = 2 + (bay + 0.5) * 3.56
            if bay == 8:
                glazing(
                    m, 32.65, DEPTH, base + 0.53, 1.42, 1.42, 2, C, detail, rear=True
                )
                continue
            if bay == 9:
                glazing(
                    m, 37.36, DEPTH, base - 0.17, 1.95, 1.06, 3, C, detail, rear=True
                )
                continue
            if bay == 10:
                x += 0.8
            glazing(
                m,
                x,
                DEPTH,
                base + 0.62,
                3.32,
                1.72,
                3,
                C,
                detail,
                rear=True,
            )
        for x, sign in ((0, -1), (LENGTH, 1)):
            for y in (4.0, 10.9):
                m.box(x + sign * 0.025, y, base + 1.36, 0.07, 1.65, 1.45, C['glass'])
    for i in range(6):
        bottom = 4.5 if i == 4 else 1.6
        m.box(
            8.4 + i * 7.92,
            -0.16,
            (20.6 + bottom) / 2,
            0.34,
            0.55,
            20.6 - bottom,
            C['white'],
        )

    entry = 39.0
    glazing(m, entry, 0, 1.59, 8.65, 2.86, 8, C, detail)
    m.box(entry, -1.44, 4.89, 12.0, 3.1, 0.83, C['metal'])
    # Opening-day photograph: narrow vertical joints across the sign fascia.
    panel_count = 21 if detail else 1
    panel_width = 12.0 / panel_count
    for i in range(panel_count):
        left = entry - 6.0 + i * panel_width + 0.006
        right = left + panel_width - 0.012
        m.face(
            [
                (left, -2.998, 4.475),
                (right, -2.998, 4.475),
                (right, -2.998, 5.305),
                (left, -2.998, 5.305),
            ],
            C['vetCanopyPanel'],
        )
        if detail:
            # The underside photo resolves rows of joints continuing the fascia seams.
            for row in range(3):
                front = -2.99 + row * 3.1 / 3 + 0.006
                back = front + 3.1 / 3 - 0.012
                m.face(
                    [
                        (left, front, 4.469),
                        (left, back, 4.469),
                        (right, back, 4.469),
                        (right, front, 4.469),
                    ],
                    C['vetCanopyPanel'],
                )
    if detail:
        # One flush round fixture is visible above the entrance, centred under the canopy.
        m.cylinder(entry, -1.44, 4.446, 0.245, 0.046, C['metal'], n=24)
        m.cylinder(entry, -1.44, 4.418, 0.225, 0.012, C['white'], n=24)
    for side in (-1, 1):
        m.box(entry + side * 4.6, -0.23, 3.04, 0.58, 0.6, 2.92, C['paleRoof'])
        for y, h in ((-1, 1.58), (-4.9, 0.16)):
            m.box(entry + side * 5.2, y, h + 0.47, 0.08, 0.08, 0.94, C['metal'])
        m.line(
            (entry + side * 5.2, -4.9, 1.1),
            (entry + side * 5.2, -1, 2.52),
            0.052,
            C['metal'],
        )
        if detail:
            for i in range(1, 14):
                t = i / 14
                m.box(
                    entry + side * 5.2,
                    -4.9 + 3.9 * t,
                    0.63 + 1.42 * t,
                    0.034,
                    0.034,
                    0.94,
                    C['metal'],
                )
    m.box(entry, -0.55, 0.79, 10.6, 1.1, 1.58, C['paleRoof'])
    for i in range(10):
        h = 1.58 * (10 - i) / 10
        m.box(entry, -1.1 - (i + 0.5) * 0.4, h / 2, 10.6, 0.4, h, C['paleRoof'])
    if detail:
        m.extend(
            inscription(
                '广 西 大 学 教 学 动 物 医 院',
                entry,
                -3.01,
                4.89,
                8.6,
                0.74,
                C['gateRed'],
                False,
                flat=True,
            )
        )
    for x in range(15, 42, 3):
        m.box(x, 0.52, ROOF + 0.77, 0.08, 0.08, 1.54, C['metal'])
    m.box(28, 0.52, ROOF + 0.38, 27, 0.085, 0.08, C['metal'])
    m.extend(
        inscription(
            '广 西 大 学 动 物 医 院',
            28,
            0.43,
            ROOF + 1.32,
            27,
            1.95,
            C['gateRed'],
            False,
            flat=True,
        )
    )
    ring = b['polygons'][0][0][:-1]
    sw, se = sorted(sorted(ring, key=lambda p: p[1])[:2])
    nw, ne = sorted(sorted(ring, key=lambda p: p[1])[2:])

    def world(x, y, h):
        u, v = x / LENGTH, y / DEPTH
        return tuple(
            (1 - v) * ((1 - u) * nw[i] + u * sw[i]) + v * ((1 - u) * ne[i] + u * se[i])
            for i in (0, 1)
        ) + (z + h,)

    m.v = [world(*v) for v in m.v]
    return m
