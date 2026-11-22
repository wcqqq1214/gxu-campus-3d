"""College elevations registered to their mapped walls and documented viewpoints."""

import math

from geometry import Mesh

MEDICINE = 'way/759096577'
SPORTS = 'way/948683812'
SPORTS_WING = 'way/948683813'
LIFE = 'relation/12874251'
LAB = 'relation/20369638'
HALL = 'way/1502723420'
EAST_GYM = 'way/759193120'
REPRODUCTION_INSTITUTE = 'way/880036336'


def wall_frame(ring, edge):
    """Return midpoint and tangent. Local -Y always faces the street."""
    a, b = ring[edge : edge + 2]
    if sum(p[0] * q[1] - p[1] * q[0] for p, q in zip(ring, ring[1:])) < 0:
        a, b = b, a
    return (
        (a[0] + b[0]) / 2,
        (a[1] + b[1]) / 2,
        math.atan2(b[1] - a[1], b[0] - a[0]),
        math.dist(a, b),
    )


def attach(mesh, wall, frame, z):
    x, y, angle, _ = frame
    wall.rotate_z(0, 0, angle)
    wall.v = [(x + u, y + v, z + h) for u, v, h in wall.v]
    mesh.extend(wall)


def pane(m, x, h, w, height, C, detail, *, bars=False):
    m.box(x, -0.075, h, w, 0.12, height, C['glass'])
    if detail:
        for i in range(-2, 3) if bars else (0,):
            m.box(x + i * w / 6, -0.155, h, 0.045, 0.06, height, C['metal'])
        for i in (-1, 0, 1):
            m.box(x, -0.155, h + i * height / 4, w, 0.06, 0.045, C['metal'])


def medicine(b, z, C, detail):
    m = Mesh()
    m.roof(534.60, -481.56, z + b['form']['height'], 31.1, 10.5, 1.05, C['red'])
    end = Mesh()
    end.roof(555.32, -479.46, z + b['form']['height'], 22.4, 10.3, 1.05, C['red'])
    end.rotate_z(555.32, -479.46, math.pi / 2)
    m.extend(end)
    frame = wall_frame(b['polygons'][0][0], 3)
    wall = Mesh()
    wall.box(0, -0.055, 0.21, frame[3], 0.11, 0.42, C['dark'])
    for bay in range(8):
        x = (bay - 3.5) * 3.85
        for floor in range(3):
            pane(wall, x, 1.66 + 3.3 * floor, 1.64, 1.53, C, detail, bars=True)
    if detail:
        for x, floor in [(-5.0, 1), (-5.0, 2), (1.1, 1), (1.1, 0), (9.2, 0)]:
            wall.box(x, -0.23, 1.10 + 3.3 * floor, 0.76, 0.47, 0.53, C['paleRoof'])
    attach(m, wall, frame, z)
    return m


def sports(b, z, C, detail):
    """The sign and stepped window face the diagonal corner beside the sculpture."""
    from south_gate import inscription

    m = Mesh()
    for edge in (0, 1, 2):
        frame = wall_frame(b['polygons'][0][0], edge)
        wall = Mesh()
        length = frame[3]
        wall.box(0, -0.021, 1.52, length, 0.042, 3.04, C['pink'])
        if edge == 1:
            for x in (-1.78, 1.78):
                wall.box(x, -0.12, 1.52, 0.60, 0.24, 3.04, C['stone'])
            pane(wall, 0, 1.35, 2.75, 2.70, C, detail, bars=True)
            wall.box(0, -0.23, 3.25, 4.15, 0.44, 0.51, C['stone'])
            if detail:
                wall.extend(
                    inscription(
                        '体育学院',
                        0,
                        -0.47,
                        3.25,
                        2.85,
                        0.44,
                        C['dark'],
                        False,
                        flat=True,
                    )
                )
            pane(wall, 0, 4.76, 2.85, 1.42, C, detail, bars=True)
            pane(wall, 0, 5.65, 1.15, 0.45, C, detail)
        else:
            for i in range(4):
                x = (i - 1.5) * length / 4.55
                pane(wall, x, 4.8, 1.65, 1.48, C, detail, bars=True)
                pane(wall, x, 1.66, 1.68, 1.28, C, detail)
        attach(m, wall, frame, z)
    return m


def sports_wing_shell(body, ring, z, depth, height, wall, roof):
    # Four-sided footprint. Leave the east face free down to grade for both doors.
    body.face([(x, y, z + height) for x, y in reversed(ring[:-1])], roof)
    for edge, (a, b) in enumerate(zip(ring, ring[1:])):
        top = z if edge == 1 else z + height
        body.face([(*b, z - depth), (*a, z - depth), (*a, top), (*b, top)], wall)


def sports_sash(wall, x, width, sill, head, C, detail):
    """Paired top-hung lights and fine horizontal grilles seen from the east."""
    h = head - sill
    half = width / 2
    wall.box(x, 0.20, (head + sill) / 2, width, 0.04, h, C['dark'])
    wall.box(x, 0.11, (head + sill) / 2, 0.055, 0.07, h, C['metal'])
    foot = sill + h * 0.24
    hinge = sill + h * 0.64
    for level in (foot, hinge):
        wall.box(x, 0.09, level, width, 0.065, 0.064, C['metal'])
    # Two awning sashes tilt out from their upper hinges.
    for mid in (x - half / 2, x + half / 2):
        left, right = mid - half / 2 + 0.026, mid + half / 2 - 0.026
        wall.face(
            [
                (left, -0.21, foot),
                (right, -0.21, foot),
                (right, 0.08, hinge),
                (left, 0.08, hinge),
            ],
            C['glass'],
        )
        wall.box(mid, -0.21, foot, right - left, 0.055, 0.058, C['metal'])
        if detail:
            for u in (left, right):
                wall.line((u, -0.21, foot), (u, 0.08, hinge), 0.022, C['metal'], 4)
    if detail:
        for n in range(1, 18):
            t = n / 18
            y = -0.24 + 0.29 * (t - 0.24) / 0.40 if 0.24 < t < 0.64 else 0.08
            wall.box(x, y, sill + t * h, width, 0.026, 0.026, C['metal'])


def sports_wing(b, z, C, detail):
    ring = b['polygons'][0][0]
    m = Mesh()
    frame = wall_frame(ring, 1)
    wall = Mesh()
    length = frame[3]
    bay = length / 6
    width = bay * 0.50
    plinth = 3.18
    sill, lower_head, upper_sill, head = 1.43, 4.28, 4.60, 7.40

    def panel(left, right, bottom, top, material):
        wall.face(
            [(left, 0, bottom), (right, 0, bottom), (right, 0, top), (left, 0, top)],
            material,
        )

    def reveal(left, right, bottom, top, depth, finish):
        # Jambs, threshold and soffit run back to the glazing plane.
        front = [(left, 0, bottom), (right, 0, bottom), (right, 0, top), (left, 0, top)]
        back = [(u, depth, h) for u, _, h in front]
        for i in range(4):
            j = (i + 1) % 4
            wall.face([front[i], front[j], back[j], back[i]], finish)

    for i in range(6):
        x = (i - 2.5) * bay
        left, right = x - width / 2, x + width / 2
        for a, e in ((x - bay / 2, left), (right, x + bay / 2)):
            panel(a, e, 0, plinth, C['pink'])
            panel(a, e, plinth, 8.6, C['white'])
        panel(left, right, head, 8.6, C['white'])
        reveal(left, right, upper_sill, head, 0.20, C['white'])
        sports_sash(wall, x, width, upper_sill, head, C, detail)
        # Narrow jambs tie both window banks together around the light cross-band.
        jamb_bottom = upper_sill if i in (0, 4) else sill
        for u in (left - 0.045, right + 0.045):
            wall.box(
                u,
                -0.025,
                (head + jamb_bottom) / 2,
                0.09,
                0.07,
                head - jamb_bottom,
                C['white'],
            )
        wall.box(x, -0.055, upper_sill - 0.035, width + 0.18, 0.13, 0.07, C['white'])

        if i in (0, 4):
            door_height, recess = 2.77, 0.46
            door_width = 2.59  # Estimated clear width of both mapped openings.
            dl, dr = x - door_width / 2, x + door_width / 2
            panel(left, dl, 0, door_height, C['pink'])
            panel(dr, right, 0, door_height, C['pink'])
            panel(left, right, door_height, plinth, C['pink'])
            panel(left, right, plinth, upper_sill, C['white'])
            reveal(dl, dr, 0, door_height, recess, C['pink'])
            wall.box(
                x,
                recess + 0.025,
                door_height / 2,
                door_width,
                0.05,
                door_height,
                C['dark'],
            )
            for offset in (-0.46, 0, 0.46):
                wall.box(
                    x + offset * door_width / 2,
                    recess - 0.04,
                    1.06,
                    0.055,
                    0.07,
                    2.12,
                    C['metal'],
                )
            wall.box(x, recess - 0.04, 2.12, door_width, 0.07, 0.075, C['metal'])
            wall.box(x, -0.58, 3.37, 4.16, 1.20, 0.27, C['paleRoof'])
        else:
            panel(left, right, 0, sill, C['pink'])
            panel(left, right, lower_head, upper_sill, C['white'])
            reveal(left, right, sill, lower_head, 0.20, C['pink'])
            sports_sash(wall, x, width, sill, lower_head, C, detail)
            # Projecting sill narrows below the opening in both oblique views.
            w = width / 2 + 0.11
            wall.face(
                [
                    (x - w + 0.27, -0.19, sill - 0.48),
                    (x + w - 0.27, -0.19, sill - 0.48),
                    (x + w, -0.48, sill),
                    (x - w, -0.48, sill),
                ],
                C['pink'],
            )
            for sign in (-1, 1):
                u = x + sign * w
                wall.face(
                    [
                        (u - sign * 0.27, 0, sill - 0.48),
                        (u - sign * 0.27, -0.19, sill - 0.48),
                        (u, -0.48, sill),
                        (u, 0, sill),
                    ],
                    C['pink'],
                )
            wall.face(
                [
                    (x - w + 0.27, 0, sill - 0.48),
                    (x + w - 0.27, 0, sill - 0.48),
                    (x + w - 0.27, -0.19, sill - 0.48),
                    (x - w + 0.27, -0.19, sill - 0.48),
                ],
                C['pink'],
            )
            wall.box(x, -0.23, sill, w * 2, 0.50, 0.055, C['pink'])
        if i < 5:
            u = x + bay / 2
            wall.face(
                [
                    (u, -0.065, 4.04),
                    (u + 0.70, -0.065, 4.74),
                    (u, -0.065, 5.44),
                    (u - 0.70, -0.065, 4.74),
                ],
                C['red'],
            )
    wall.box(0, -0.36, 8.39, length + 0.4, 0.76, 0.40, C['white'])
    wall.v = [(x, y, h * b['form']['height'] / 8.6) for x, y, h in wall.v]
    attach(m, wall, frame, z)
    # The north end is blind and carries a round red medallion high on the wall.
    frame = wall_frame(ring, 0)
    end = Mesh()
    end_plinth = plinth * b['form']['height'] / 8.6
    end.box(0, -0.03, end_plinth / 2, frame[3], 0.06, end_plinth, C['pink'])
    disk = [
        (
            0.62 * math.cos(i * math.tau / 24),
            -0.095,
            6.03 + 0.62 * math.sin(i * math.tau / 24),
        )
        for i in range(24)
    ]
    roof_height = b['form']['height']
    end.face(
        [(x, y, roof_height + 1.32 + (h - 6.03) * 1.25) for x, y, h in disk], C['red']
    )
    attach(m, end, frame, z)
    a, c, d, e = ring[:4]
    near_peak = ((a[0] + c[0]) / 2, (a[1] + c[1]) / 2, z + roof_height + 1.6)
    far_peak = ((d[0] + e[0]) / 2, (d[1] + e[1]) / 2, z + roof_height + 1.6)
    a, c, d, e = [(x, y, z + roof_height) for x, y in (a, c, d, e)]
    m.face([a, c, near_peak], C['white'])
    m.face([e, far_peak, d], C['white'])
    m.face([a, near_peak, far_peak, e], C['paleRoof'])
    m.face([near_peak, c, d, far_peak], C['paleRoof'])
    return m


def life_sciences(b, z, C, detail):
    ring = b['polygons'][0][0]
    m = Mesh()
    frame = wall_frame(ring, 11)
    front = Mesh()
    for floor in range(5):
        h = (floor + 0.52) * 3.96
        spans = [(0, 53)] if floor >= 3 else [(-21, 12), (21, 12)]
        for x, w in spans:
            front.box(x, -0.095, h, w, 0.15, 1.95, C['glass'])
            front.box(x, -0.21, h + 1.04, w + 0.18, 0.48, 0.12, C['stone'])
            if detail:
                for j in range(round(w / 1.45)):
                    front.box(
                        x - w / 2 + (j + 0.5) * 1.45,
                        -0.20,
                        h,
                        0.06,
                        0.06,
                        1.96,
                        C['metal'],
                    )
    # Raised porch, grey round shafts and broad steps visible from both ends.
    for i in range(6):
        front.box(
            0,
            -5.2 + i * 0.27,
            (i + 1) * 0.09,
            36.5,
            10.4 - i * 0.54,
            (i + 1) * 0.18,
            C['stone'],
        )
    for x in (-15.5, -9.3, -3.1, 3.1, 9.3, 15.5):
        front.cylinder(x, -6.8, 3.82, 0.62, 5.5, C['stone'], n=16)
    front.box(0, -3.92, 6.67, 40.2, 7.85, 0.42, C['white'])
    front.box(0, -4.13, 7.15, 41.2, 8.34, 0.68, C['dark'])
    # Flared fascia in the official front view.
    below = [
        (-20.6, -8.3, 7.45),
        (20.6, -8.3, 7.45),
        (20.6, 0.1, 7.45),
        (-20.6, 0.1, 7.45),
    ]
    above = [
        (-22.0, -9.15, 8.92),
        (22.0, -9.15, 8.92),
        (22.0, 0.1, 8.92),
        (-22.0, 0.1, 8.92),
    ]
    for i in range(4):
        j = (i + 1) % 4
        front.face([below[i], below[j], above[j], above[i]], C['dark'])
    front.face(above, C['dark'])
    # Behind the shafts the glazing is two tall bays high, with dark transoms.
    front.box(0, -0.1, 3.7, 26.6, 0.18, 5.4, C['residenceGlass'])
    for x in (-10.6, -5.3, 0, 5.3, 10.6):
        front.box(x, -0.23, 3.7, 0.15, 0.12, 5.4, C['metal'])
    front.box(0, -0.22, 4.64, 26.6, 0.13, 0.14, C['metal'])
    # The published front image has a narrow vertical window bay at its west end.
    for h in (2.05, 5.3, 8.6, 11.9, 15.2, 18.15):
        pane(front, -30.4, h, 1.92, 2.02, C, detail)

    top = b['form']['height']
    front.box(25, 3.3, top + 3.28, 5.25, 5.0, 6.56, C['white'])
    front.box(25, 3.3, top + 6.90, 6.03, 5.78, 0.68, C['paleRoof'])
    front.box(25, 0.77, top + 3.6, 3.35, 0.12, 4.0, C['glass'])
    front.box(27.66, 3.3, top + 3.6, 0.12, 3.18, 4.0, C['glass'])
    attach(m, front, frame, z)
    # The curved lower wing has a dark upper gallery, broad ground-level piers
    # and railings that follow the arc. The tall return behind it has strip windows.
    for edge in range(3, 11):
        band = Mesh()
        f = wall_frame(ring, edge)
        for h, clear_height in ((2.4, 3.65), (7.02, 2.65)):
            band.box(0, -0.085, h, f[3], 0.16, clear_height, C['residenceGlass'])
        if edge in (3, 6, 9):
            band.box(0, -0.20, 2.40, min(1.1, f[3] * 0.36), 0.35, 3.85, C['white'])
        if detail:
            for h in (10.35, 10.68):
                band.box(0, -0.04, h, f[3], 0.08, 0.055, C['metal'])
            band.box(0, -0.04, 10.19, 0.055, 0.07, 1.04, C['metal'])
        attach(m, band, f, z)
    teaching = next(p for p in b['form']['parts'] if p['id'] == 'teaching')
    face = wall_frame(teaching['polygons'][0][0], 2)
    side = Mesh()
    for h in (12.7, 16.25):
        pane(side, 0, h, face[3] * 0.82, 2.06, C, detail, bars=True)
    attach(m, side, face, z)
    return m


def experiment_center(b, z, C, detail):
    """Continuous strip glazing follows the three curved and straight elevations."""
    m = Mesh()
    for face in b['form']['facades']:
        if face['part'].endswith('-link'):
            continue
        a, q = face['start'], face['end']
        length = math.dist(a, q)
        if length < 0.32:
            continue
        nx, ny = face['normal']
        cx, cy = (a[0] + q[0]) / 2, (a[1] + q[1]) / 2
        angle = math.atan2(q[1] - a[1], q[0] - a[0])
        floor = 0
        for height in face['floorHeights']:
            if floor >= face.get('minimumHeight', 0):
                h = floor + height * 0.52
                m.box(
                    cx + nx * 0.08,
                    cy + ny * 0.08,
                    z + h,
                    length - 0.10,
                    0.15,
                    height * 0.55,
                    C['residenceGlass'],
                    angle,
                )
                if detail:
                    bays = max(1, round(length / 2.6))
                    for j in range(bays):
                        t = (j + 0.5) / bays
                        m.box(
                            a[0] + (q[0] - a[0]) * t + nx * 0.17,
                            a[1] + (q[1] - a[1]) * t + ny * 0.17,
                            z + h,
                            0.055,
                            0.08,
                            height * 0.55,
                            C['metal'],
                            angle,
                        )
            floor += height
    return m


def lecture_hall(b, z, C, detail):
    m = Mesh()
    ring = b['polygons'][0][0]
    height = b['form']['height']
    for edge in range(len(ring) - 1):
        frame = wall_frame(ring, edge)
        wall = Mesh()
        length = frame[3]
        # The south forecourt photograph shows a pale lower wall around the
        # paired doors. The glass and its mullions continue above this bay.
        sill = 5.9 if edge in (7, 8, 9) else 0.275
        head = height - 0.275
        wall.box(
            0, -0.08, (sill + head) / 2, length, 0.16, head - sill, C['residenceGlass']
        )
        if edge in (7, 9):
            wall.box(0, -0.08, sill / 2, length, 0.16, sill, C['white'])
        if edge == 8:
            hall_south_doors(wall, length, sill, C, detail)
        if detail:
            bays = max(1, round(length / 2.15))
            for j in range(bays):
                wall.box(
                    ((j + 0.5) / bays - 0.5) * length,
                    -0.17,
                    (sill + head) / 2,
                    0.11,
                    0.14,
                    head - sill,
                    C['metal'],
                )
        attach(m, wall, frame, z)
    # The contractor's design perspective shows one shallow convex cap with
    # a thin rim. Keep the previous estimated span and overall height.
    from roof_dome import add_roof_dome

    add_roof_dome(
        m,
        {
            'center': (160.5, 534.8),
            'radius': 29.3,
            'baseHeight': height,
            'drumHeight': 0.22,
            'rise': 1.68,
        },
        z,
        C['paleRoof'],
        segments=96 if detail else 48,
    )
    return m


def hall_south_doors(wall, width, sill, C, detail):
    """Recess the two visible south doors behind the face of the pale surround."""
    threshold = 0.30
    head = threshold + 2.15
    half = width / 2
    for left, right in ((-half, -2.45), (-0.85, 0.85), (2.45, half)):
        wall.box(
            (left + right) / 2, -0.21, head / 2, right - left, 0.42, head, C['white']
        )
    wall.box(0, -0.21, (head + sill) / 2, width, 0.42, sill - head, C['white'])
    for center in (-1.65, 1.65):
        wall.box(
            center,
            -0.055,
            (head + threshold) / 2,
            1.60,
            0.10,
            head - threshold,
            C['glass'],
        )
        if detail:
            wall.box(
                center,
                -0.125,
                (head + threshold) / 2,
                0.045,
                0.045,
                head - threshold,
                C['metal'],
            )
    # The threshold meets the existing exported terrain at its south edge.
    # These three elevations are model tie-ins, not a survey of the forecourt.
    stations = ((-half, 0.272), (0, 0.281), (half, 0.281))
    for (left, outer_left), (right, outer_right) in zip(stations, stations[1:]):
        front_left = (left, -1.34, outer_left)
        front_right = (right, -1.34, outer_right)
        back_left = (left, 0, threshold)
        back_right = (right, 0, threshold)
        wall.face([front_left, front_right, back_right], C['stone'])
        wall.face([front_left, back_right, back_left], C['stone'])


def agriculture_east_approach(wall, x, C):
    """East doorway, brick walk and flush shoulder at Gujiang Road."""
    from geometry import tile_material

    tile_material(
        C, 'studentTowerMasonry', 'tower-cafe-brick.png', (0.37, 0.145, 0.075)
    )
    for sign in (-1, 1):
        wall.box(x + sign * 1.54, -0.57, 0.225, 0.23, 1.04, 0.45, C['residencePodium'])

    def point(u, depth, lift=0):
        # Match the two existing road crossfalls, including the outer curb bevel.
        road = 0.414 + 0.025 * min(u, 1.05) + 0.010 * max(0, u - 1.05)
        fraction = max(0, min(1, (depth - 1.02) / 7.15))
        top = 0.074 + (road + 0.007 - 0.074) * fraction
        if depth >= 8.30:
            bevel = 0.411 + 0.033 * u - 0.212 * (depth - 8.43)
            top = min(road + 0.001, bevel) + 0.007
        if depth >= 8.475:
            top = min(0.405 + 0.033 * u, 0.43 + 0.011 * u) + 0.002
        # Allow for the two quantized meshes where the shoulder crosses the curb.
        top += 0.004 * max(0, min(1, (depth - 8.17) / 0.13))
        return (x + u, -depth, top + lift)

    def strip(depth0, depth1, left0, right0, left1, right1, material, lift=0):
        a, b = point(left0, depth0, lift), point(right0, depth0, lift)
        c, d = point(left1, depth1, lift), point(right1, depth1, lift)
        for tri in ([a, c, d], [a, d, b]):
            uv = None
            if material == 'studentTowerMasonry':
                uv = [((u - x) / 0.84, v / 0.80) for u, v, _ in tri]
            wall.face(tri, C[material], uvs=uv)

    def riser(a, b, reverse=False):
        if reverse:
            a, b = b, a
        wall.face([b, a, (*a[:2], -0.10), (*b[:2], -0.10)], C['gateJoint'])

    # Image-space picks are the brick returns, not the painted line on the road.
    # Positions are relative to the door axis; the opening drifts to the south.
    rows = (
        (1.02, -1.67, 1.67),
        (3.60, -2.50, 0.20),
        (5.55, -2.62, -0.16),
        (6.30, -2.73, -0.25),
        (6.52, -2.82, -0.26),
        (6.65, -2.92, -0.24),
        (6.75, -3.05, -0.20),
    )
    for a, b in ((-4.85, -1.67), (1.67, 4.85)):
        strip(0.12, 1.02, a, b, a, b, 'gateJoint')
    for (v0, l0, r0), (v1, l1, r1) in zip(rows, rows[1:]):
        strip(v0, v1, l0, r0, l1, r1, 'bridgeConcrete')
        for sign, a, b, pit in [
            (-1, l0, l1, (-4.20, -3.15)),
            (1, r0, r1, (0.70, 1.80)),
        ]:
            outer = sign * 4.85
            if v0 < 3.60:
                strip(
                    v0,
                    v1,
                    min(outer, a),
                    max(outer, a),
                    min(outer, b),
                    max(outer, b),
                    'gateJoint',
                )
                continue
            lip0, lip1 = a + sign * 0.14, b + sign * 0.14
            strip(
                v0,
                v1,
                min(a, lip0),
                max(a, lip0),
                min(b, lip1),
                max(b, lip1),
                'gateJoint',
                0.12,
            )
            left0, right0 = sorted((outer, lip0))
            left1, right1 = sorted((outer, lip1))
            spans = [(left0, right0, left1, right1)]
            if 5.55 <= v0 < 6.52:
                spans = [
                    (left0, pit[0], left1, pit[0]),
                    (pit[1], right0, pit[1], right1),
                ]
                for side in pit:
                    riser(point(side, v0, 0.12), point(side, v1, 0.12), side == pit[0])
                if v0 == 5.55:
                    riser(point(pit[0], v0, 0.12), point(pit[1], v0, 0.12))
                if v1 == 6.52:
                    riser(point(pit[1], v1, 0.12), point(pit[0], v1, 0.12))
            for limits in spans:
                strip(v0, v1, *limits, 'studentTowerMasonry', 0.12)
            riser(point(a, v0, 0.12), point(b, v1, 0.12), sign < 0)
            riser(point(outer, v1, 0.12), point(outer, v0, 0.12), sign < 0)
            if v0 == 3.60:
                riser(point(outer, v0, 0.12), point(a, v0, 0.12), sign < 0)
            if v1 == 6.75:
                riser(point(b, v1, 0.12), point(outer, v1, 0.12), sign < 0)

    # Beyond the photographed curb, the road shoulder stays flush all the
    # way to the mapped asphalt. Sample the change of plane across its width.
    lateral = (-4.85, -3.05, -2.30, -1.15, -0.20, 0, 0.575, 1.05, 2.30, 4.85)
    depths = (6.75, 8.17, 8.30, 8.36, 8.40, 8.44, 8.475)
    for v0, v1 in zip(depths, depths[1:]):
        for a, b in zip(lateral, lateral[1:]):
            strip(v0, v1, a, b, a, b, 'asphalt')
        for side in (lateral[0], lateral[-1]):
            riser(point(side, v0), point(side, v1), side > 0)


def agriculture_wings(m, b, z, C, detail):
    ring = b['polygons'][0][0]
    form = b['form']
    entries = {e['id']: e for e in form['entrances']}
    # Older prepared data has no side-door anchors.
    if 'east-wing-door' not in entries or 'west-north-door' not in entries:
        return
    from geometry import material, tile_material

    tile_material(C, 'dongWestTile', 'dong-west-tile.png', (0.66, 0.56, 0.47))
    if 'collegePlinthStone' not in C:
        C['collegePlinthStone'] = material(
            'collegePlinthStone', (0.25, 0.21, 0.16), 0.92
        )
    for key, edge in [('east-wing-door', 4), ('west-north-door', 15)]:
        side = Mesh()
        frame = wall_frame(ring, edge)
        width = frame[3]
        wall_height = next(f['height'] for f in form['facades'] if f['edge'] == edge)
        # These end and side walls show small square tiles, clearly visible on
        # the sunlit west gable. Keep the UV scale independent of the wall size.
        surface = [
            (-width / 2, 1.04),
            (width / 2, 1.04),
            (width / 2, wall_height),
            (-width / 2, wall_height),
        ]
        side.face(
            [(u, -0.014, h) for u, h in surface],
            C['dongWestTile'],
            uvs=[(u / 0.72, h / 0.72) for u, h in surface],
        )
        door = entries[key]
        x = (0.5 - door['t']) * width
        for sign in (-1, 1):
            side.box(x + sign * 0.42, -0.17, 1.49, 0.83, 0.07, 2.20, C['dark'])
        east_door = key == 'east-wing-door'
        if east_door:
            agriculture_east_approach(side, x, C)
        for step in range(3):
            h = 0.39 - step * ((0.39 - 0.074) / 3 if east_door else 0.13)
            side.box(
                x,
                -0.28 - 0.30 * step,
                h / 2,
                door['width'] + 0.45,
                0.34,
                h,
                C['gateJoint' if east_door else 'stone'],
            )
        # The dark stone plinth stops at the actual doorway.
        for left, right in (
            (-width / 2, x - door['width'] / 2),
            (x + door['width'] / 2, width / 2),
        ):
            side.box(
                (left + right) / 2,
                -0.055,
                0.52,
                right - left,
                0.10,
                1.04,
                C['collegePlinthStone'],
            )
            if detail:
                for course in (0.34, 0.68):
                    side.box(
                        (left + right) / 2,
                        -0.116,
                        course,
                        right - left,
                        0.018,
                        0.025,
                        C['slate'],
                    )
                for row in range(3):
                    offset = 0.38 if row % 2 else 0.76
                    while left + offset < right:
                        side.box(
                            left + offset,
                            -0.118,
                            0.17 + row * 0.34,
                            0.022,
                            0.021,
                            0.31,
                            C['slate'],
                        )
                        offset += 0.76
        if key == 'east-wing-door':
            # The southernmost bay is a stair landing above the door. The east
            # elevation then repeats narrow paired sashes between projecting piers.
            spacing = 3.13
            for bay in range(15):
                center = x + spacing * bay
                if center + 1.36 >= width / 2:
                    break
                for storey in range(5):
                    if bay == 0 and storey == 0:
                        continue
                    height = 3.3 * storey + 1.89
                    pane(side, center, height, 2.44, 1.63, C, detail)
                    side.box(center, -0.21, height + 0.88, 2.70, 0.44, 0.13, C['stone'])
                    if detail and storey < 2:
                        for bar in range(-5, 6):
                            side.box(
                                center + bar * 0.20,
                                -0.206,
                                height,
                                0.029,
                                0.06,
                                1.60,
                                C['metal'],
                            )
                    if detail and bay % 3 == 1 and storey in (1, 2):
                        side.box(
                            center + 0.56,
                            -0.32,
                            height - 1.20,
                            0.80,
                            0.5,
                            0.51,
                            C['paleRoof'],
                        )
                side.box(center + 1.46, -0.12, 8.05, 0.27, 0.25, 16.10, C['stone'])
        else:
            # The north end of the west wing has blank returns on either side
            # of four stacked landings. The highest slab is near the roof line.
            center = 1.25
            span = 6.40
            depth = 1.55
            for level in (1, 2, 3, 4):
                h = level * 3.3
                side.box(center, -depth / 2, h - 0.14, span, depth, 0.28, C['stone'])
                if level < 4:
                    side.box(
                        center - 0.98, -0.07, h + 1.13, 1.42, 0.14, 2.26, C['dark']
                    )
                    side.box(
                        center + 1.41, -0.07, h + 1.48, 1.06, 0.14, 1.38, C['glass']
                    )
                for rail in (0.36, 0.63, 0.92):
                    side.box(center, -depth, h + rail, span, 0.055, 0.052, C['metal'])
                    for sign in (-1, 1):
                        side.box(
                            center + sign * span / 2,
                            -depth / 2,
                            h + rail,
                            0.055,
                            depth,
                            0.052,
                            C['metal'],
                        )
                for post in range(5):
                    side.box(
                        center + (post / 4 - 0.5) * span,
                        -depth,
                        h + 0.47,
                        0.064,
                        0.064,
                        0.94,
                        C['dark'],
                    )
        attach(m, side, frame, z)


def agriculture(b, z, C, detail):
    """South portico, rooftop script and grille banks in the college front photograph."""
    from geometry import material
    from south_gate import inscription

    if 'collegeBronze' not in C:
        C['collegeBronze'] = material('collegeBronze', (0.60, 0.39, 0.10), 0.37, 0.55)
    m = Mesh()
    frame = wall_frame(b['polygons'][0][0], 9)
    front = Mesh()
    # The LED display hangs under the canopy; the bronze name rises above it.
    front.box(0, 0.8, 3.13, 8.1, 0.20, 0.46, C['dark'])
    if detail:
        front.extend(
            inscription('农学院', 0, -0.25, 4.87, 8.05, 1.48, C['collegeBronze'], False)
        )
    # The admissions film shows a dark inset surface inside a pale coping.
    w = frame[3]
    d = b['form']['entrances'][0]['recess']
    front.box(0, d / 2, 4.035, w - 0.26, d - 0.30, 0.06, C['dark'])
    front.box(0, 0, 3.76, w + 0.18, 0.24, 0.70, C['stone'])
    front.box(0, -0.035, 4.10, w + 0.30, 0.32, 0.15, C['paleRoof'])
    for x in (-w / 2, w / 2):
        front.box(x, d / 2, 4.10, 0.19, d, 0.16, C['paleRoof'])
    if detail:
        entry = b['form']['entrances'][0]
        for i in range(9):
            x = (i / 8 - 0.5) * (w - 0.20)
            front.box(x, -0.126, 3.75, 0.016, 0.018, 0.54, C['slate'])
        for x in (-8.25, -4.63, 4.63, 8.25):
            front.box(x, 0.44, 3.21, 0.98, 0.98, 0.33, C['stone'])
            front.box(x, 0.43 + d / 2, 3.29, 0.32, d - 0.50, 0.21, C['stone'])
        for x in (-4.63, 4.63):
            front.box(x, -0.025, 1.87, 0.29, 0.075, 1.75, C['collegeBronze'])
        for x in (-8.25, 8.25):
            front.box(x, -0.06, 2.23, 0.34, 0.15, 0.20, C['collegeBronze'])
        # Inset glazed leaves, headlight and the piers on the rear door line.
        half = entry['width'] / 2
        for x in (-half, -half / 2, 0, half / 2, half):
            front.box(x, d - 0.16, 1.85, 0.095, 0.11, 2.79, C['metal'])
        front.box(0, d - 0.16, 2.67, entry['width'], 0.11, 0.11, C['metal'])
        for x in (-half - 0.28, half + 0.28):
            front.box(x, d - 0.18, 1.91, 0.46, 0.51, 2.9, C['stone'])
    attach(m, front, frame, z)
    # The west roof falls twice in the anniversary aerial. Represent the dark
    # waterproof surface on the intermediate range and the two low terrace covers.
    west = next((p for p in b['form']['parts'] if p['id'] == 'west-four-storeys'), None)
    if west:
        for poly, triangles in zip(west['polygons'], west['triangles']):
            pts = [v for ring in poly for v in ring[:-1]]
            for a in range(0, len(triangles), 3):
                m.face(
                    [
                        (*pts[n], z + west['height'] + 0.035)
                        for n in triangles[a : a + 3]
                    ],
                    C['dark'],
                )
        terrace = next(p for p in b['form']['parts'] if p['id'] == 'west-front-terrace')
        cover = Mesh()
        face = wall_frame(terrace['polygons'][0][0], 0)
        for at, depth in ((-4.8, 3.4), (4.9, 4.1)):
            cover.box(
                at, depth, terrace['height'] + 0.74, 1.95, 1.5, 1.4, C['paleRoof']
            )
            cover.box(at, depth, terrace['height'] + 1.5, 2.16, 1.7, 0.14, C['dark'])
        attach(m, cover, face, z)
    # Air conditioners appear between upper windows, above the continuous ledges.
    # Only a sparse sample is modelled, not equipment on every window.
    if detail:
        for edge in (7, 11):
            side = Mesh()
            frame = wall_frame(b['polygons'][0][0], edge)
            # On the photographed straight wings the lower two rows carry
            # projecting metal grilles, with paired stacks of split AC units.
            facade = next(
                f
                for f in b['form']['facades']
                if f.get('edge') == edge and f['part'] == 'main-five-storeys'
            )
            panels = facade['rule'].get('panels', [])
            for panel in panels:
                if panel.get('type') != 'glazing' or panel['bottom'] > 10:
                    continue
                x = (0.5 - (panel['from'] + panel['to']) / 2) * frame[3]
                width = (panel['to'] - panel['from']) * frame[3]
                for j in range(1, 8):
                    side.box(
                        x + (j / 8 - 0.5) * width,
                        -0.22,
                        (panel['top'] + panel['bottom']) / 2,
                        0.034,
                        0.10,
                        panel['top'] - panel['bottom'],
                        C['metal'],
                    )
            for fraction, floor in [(-0.34, 2), (-0.15, 3), (0.14, 2), (0.35, 1)]:
                side.box(
                    fraction * frame[3],
                    -0.27,
                    3.3 * floor + 0.85,
                    0.80,
                    0.46,
                    0.53,
                    C['paleRoof'],
                )
            attach(m, side, frame, z)
    agriculture_wings(m, b, z, C, detail)
    return m


def animal_science(b, z, C, detail):
    from south_gate import inscription

    m = Mesh()
    frame = wall_frame(b['polygons'][0][0], 11)
    front = Mesh()
    front.box(0, -0.33, 3.81, frame[3] + 0.12, 0.66, 1.28, C['paleRoof'])
    front.box(0, 0.65, 2.88, 8.1, 0.15, 0.57, C['dark'])
    for x in (-4.7, 4.7):
        front.box(x, 0.45, 1.66, 0.64, 0.64, 2.68, C['paleRoof'])
    if 'collegeBronze' not in C:
        from geometry import material

        C['collegeBronze'] = material('collegeBronze', (0.60, 0.39, 0.10), 0.37, 0.55)

    if detail:
        front.extend(
            inscription(
                '动物科学技术学院',
                0,
                -0.70,
                3.83,
                10.20,
                0.68,
                C['collegeBronze'],
                False,
                flat=True,
            )
        )
    attach(m, front, frame, z)
    return m


def forestry(b, z, C, detail):
    # Two perforated fascia courses and a broad raised cap in the 26° view.
    m = Mesh()
    entry = b['form']['entrances'][0]
    portico = entry['attachedPortico']
    angle = wall_frame(b['polygons'][0][0], 5)[2]
    w, d = portico['width'], portico['depth']
    frame = (*entry['center'], angle, w)
    front = Mesh()
    from geometry import material

    if 'forestrySandstone' not in C:
        C['forestrySandstone'] = material('forestrySandstone', (0.56, 0.43, 0.28), 0.86)
    sand = C['forestrySandstone']
    soffit = portico['clearHeight']
    top = soffit + portico['slabThickness'] + portico['parapetHeight']
    # The photograph shows two deep horizontal openings between solid stone rails.
    for height in (soffit + 0.22, (soffit + top) / 2, top - 0.12):
        front.box(0, -d - 0.04, height, w + 0.18, 0.40, 0.36, sand)
        for x in (-w / 2, w / 2):
            front.box(x, -d / 2, height, 0.32, d, 0.36, sand)
    front.box(0, -d / 2 - 0.33, top + 0.17, w + 1.7, d + 2.0, 0.28, sand)
    for x in (
        -w / 2 + portico['columnInset'],
        -w * 0.32,
        w * 0.32,
        w / 2 - portico['columnInset'],
    ):
        front.box(
            x,
            -d + portico['columnInset'],
            (top + portico['platformHeight']) / 2,
            portico['columnWidth'] + 0.05,
            portico['columnWidth'] + 0.05,
            top - portico['platformHeight'],
            sand,
        )
        if detail:
            front.box(
                x,
                -d + portico['columnInset'] - portico['columnWidth'] / 2 - 0.04,
                2.30,
                0.22,
                0.07,
                1.90,
                C['dark'],
            )
    # The blue glass strip behind the doorway separates the two tiled wings.
    front.box(0, -0.42, 12.1, 4.65, 0.18, 11.8, C['residenceGlass'])
    for x in (-1.15, 0, 1.15):
        front.box(x, -0.55, 12.1, 0.045, 0.12, 11.8, C['metal'])
    for h in (7.4, 9.7, 12.0, 14.3, 16.6):
        front.box(0, -0.55, h, 4.65, 0.12, 0.08, C['metal'])
    for x in (-1.54, 0, 1.54):
        front.box(x, -0.17, 1.99, 0.085, 0.14, 2.71, C['metal'])
    front.box(0, -0.16, 2.81, 4.2, 0.15, 0.09, C['metal'])
    # Long barred bays and blue tile courses flank the portico in the close view.
    edge_frame = wall_frame(b['polygons'][0][0], 5)
    wall = Mesh()
    for bay in range(12):
        x = (bay - 5.5) * edge_frame[3] / 12
        wx = edge_frame[0] + x * math.cos(edge_frame[2])
        wy = edge_frame[1] + x * math.sin(edge_frame[2])
        if math.dist((wx, wy), entry['center']) < w / 2 + 0.6:
            continue
        pane(wall, x, 2.02, edge_frame[3] / 12 - 0.38, 1.82, C, detail, bars=True)
    for h in (3.25, 6.6, 9.85, 13.15, 16.48):
        wall.box(0, -0.17, h, edge_frame[3], 0.33, 0.16, C['slate'])
    attach(m, wall, edge_frame, z)
    attach(m, front, frame, z)
    return m


def mathematics(b, z, C, detail):
    # East gable viewed from the footpath at 269 degrees: tiled and blind
    # down to a contrasting grey block plinth. Rear returns retain existing data.
    m = Mesh()
    frame = wall_frame(b['polygons'][0][0], 4)
    wall = Mesh()
    wall.box(0, -0.055, 0.56, frame[3], 0.11, 1.12, C['paleRoof'])
    if detail:
        for row in range(4):
            wall.box(0, -0.112, 0.06 + row * 0.29, frame[3], 0.016, 0.021, C['dark'])
            for j in range(8):
                x = (j - 3.75 + (row % 2) * 0.5) * frame[3] / 8
                wall.box(x, -0.115, 0.19 + row * 0.29, 0.019, 0.017, 0.27, C['dark'])
    attach(m, wall, frame, z)
    portal = wall_frame(b['polygons'][0][0], 7)
    entry = next(e for e in b['form']['entrances'] if e['primary'])
    doors = Mesh()
    bay = entry['width'] / entry['doorFrame']['bays']
    floor = entry['landingHeight']
    for center in (-bay, 0, bay):
        doors.box(center, -0.24, floor + 1.30, 0.06, 0.08, 2.60, C['metal'])
        doors.box(center, -0.24, floor + 2.15, bay - 0.55, 0.08, 0.07, C['metal'])
        if detail:
            for offset in (-0.12, 0.12):
                doors.box(
                    center + offset, -0.30, floor + 1.05, 0.035, 0.08, 0.42, C['metal']
                )
    # In the 2022 and 2024 front views the pale stone piers continue through
    # the salmon spandrels. Only the three south-facing bays are documented.
    grid = next(f['rule']['windowGrid'] for f in b['form']['facades'] if f['edge'] == 7)
    spacing = (portal[3] - 2 * grid['edgeInset']) / grid['columns']
    for level in (1, 2, 3, 4):
        for column in (-1, 0, 1):
            doors.box(
                column * spacing,
                -0.035,
                level * 3.3 + 0.25,
                spacing - 0.42,
                0.06,
                0.52,
                C['pink'],
            )
    attach(m, doors, portal, z)
    return m


def east_gym(b, z, C, detail):
    """Long elevations have portholes below a clerestory; the south door has a swept canopy."""
    m = Mesh()
    ring = b['polygons'][0][0]
    height = b['form']['height']
    for edge in (0, 2):
        wall = Mesh()
        frame = wall_frame(ring, edge)
        length = frame[3]
        wall.box(0, -0.04, 6.1, length, 0.08, 12.2, C['stone'])
        for i in range(14):
            x = (i - 6.5) * length / 14
            if abs(x) > 7.5:
                for h in (1.9, 5.6, 9.4):
                    pane(wall, x, h, 5.2, 1.8, C, detail)
                    wall.box(x, -0.21, h + 1.12, 5.55, 0.42, 0.26, C['pink'])
            points = [
                (
                    x + 0.92 * math.cos(t * math.tau / 24),
                    -0.11,
                    14.1 + 0.92 * math.sin(t * math.tau / 24),
                )
                for t in range(24)
            ]
            wall.face(points, C['glass'])
            if detail:
                wall.box(x, -0.14, 14.1, 1.82, 0.06, 0.07, C['metal'])
                wall.box(x, -0.14, 14.1, 0.07, 0.06, 1.82, C['metal'])
            pane(wall, x, height - 1.15, length / 14 - 0.24, 1.95, C, detail)
        wall.box(0, -0.70, height + 0.12, length + 1.7, 2.0, 0.38, C['paleRoof'])
        if edge == 2:
            for x in (-7.25, 7.25):
                wall.box(x, -0.29, height / 2, 2.6, 0.58, height, C['stone'])
                wall.cylinder(x * 0.76, -3.05, 4.23, 0.5, 8.46, C['pink'], 20)
            for x in (-3.7, 0, 3.7):
                pane(wall, x, 1.85, 3.65, 3.64, C, detail)
                pane(wall, x, 5.8, 3.65, 3.9, C, detail)
            for i in range(4):
                wall.box(
                    0,
                    -1.1 - i * 0.35,
                    0.30 - i * 0.075,
                    13.8,
                    2.2 + i * 0.70,
                    0.60 - i * 0.15,
                    C['stone'],
                )
            # Viewed from the track, the lower edge curves down at midspan.
            for j in range(16):
                a, c = -9 + j * 1.125, -9 + (j + 1) * 1.125
                ha, hc = 8.0 + 1.6 * (a / 9) ** 2, 8.0 + 1.6 * (c / 9) ** 2
                for y1, y2, dz1, dz2 in [
                    (-4.5, -4.5, 0, 0.64),
                    (-4.5, 0, 0.64, 0.64),
                    (0, -4.5, 0, 0),
                ]:
                    wall.face(
                        [
                            (a, y1, ha + dz1),
                            (c, y1, hc + dz1),
                            (c, y2, hc + dz2),
                            (a, y2, ha + dz2),
                        ],
                        C['white'],
                    )
                if j in (0, 15):
                    x, h = (a, ha) if j == 0 else (c, hc)
                    wall.face(
                        [
                            (x, -4.5, h),
                            (x, 0, h),
                            (x, 0, h + 0.64),
                            (x, -4.5, h + 0.64),
                        ],
                        C['white'],
                    )
        attach(m, wall, frame, z)
    return m


def reproduction_institute(b, z, C, detail):
    """The southwest range has two masonry floors and a pale metal upper enclosure."""
    m = Mesh()
    ring = b['polygons'][0][0]
    for edge in (7, 8):
        frame = wall_frame(ring, edge)
        wall = Mesh()
        length = frame[3]
        wall.box(0, -0.045, 3.25, length, 0.09, 6.50, C['pink'])
        wall.box(0, -0.10, 0.47, length, 0.20, 0.94, C['stone'])
        wall.box(0, -0.20, 8.2, length + 0.45, 0.4, 3.4, C['paleRoof'])
        wall.box(0, -0.32, 6.5, length + 0.65, 0.65, 0.22, C['dark'])
        wall.box(0, -0.24, 9.93, length + 0.52, 0.48, 0.18, C['dark'])
        if edge == 7:
            for i in range(6):
                x = (i - 2.5) * length / 6.4
                for h in (2.1, 5.05):
                    pane(wall, x, h, 1.43, 1.56, C, detail, bars=True)
                if i >= 2:
                    wall.box(x, -0.36, 8.00, 1.00, 0.4, 0.84, C['metal'])
            for h in (2.97, 5.98):
                wall.box(0, -0.26, h, length - 0.75, 0.52, 0.17, C['stone'])
        else:
            wall.box(0, -0.9, 3.26, 3.55, 1.8, 0.24, C['stone'])
            pane(wall, 0, 1.5, 2.2, 3.0, C, detail)
        attach(m, wall, frame, z)
    return m


BUILDERS = {
    MEDICINE: medicine,
    SPORTS: sports,
    SPORTS_WING: sports_wing,
    LIFE: life_sciences,
    LAB: experiment_center,
    HALL: lecture_hall,
    'way/759185166': agriculture,
    'relation/11564704': animal_science,
    'relation/11564703': forestry,
    'way/759129516': mathematics,
    EAST_GYM: east_gym,
    REPRODUCTION_INSTITUTE: reproduction_institute,
}
PHOTO_EDGES = {
    MEDICINE: {3},
    SPORTS: {0, 1, 2},
    SPORTS_WING: {0, 1},
    LIFE: set(range(3, 12)),
    'way/759129516': {4},
    EAST_GYM: {0, 2},
    REPRODUCTION_INSTITUTE: {7, 8},
}
