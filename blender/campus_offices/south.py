"""Western entrance geometry for way/759132930. Units are campus metres."""

import math
from copy import deepcopy

from geometry import Mesh
from humanities_facades import finish

ID = 'way/759132930'
SOFFIT, TOP = 4.75, 10.69


def prepare(building, colors):
    b = deepcopy(building)
    f = b['form']
    portico = next(p for p in f['parts'] if p['id'] == 'west-low-portico')
    portico['height'] = TOP - 0.8
    opening = portico['openBelow']
    opening['clearHeight'] = SOFFIT
    finish(colors, 'officeSouthPinkStone', (0.46, 0.335, 0.266), 0.69)
    finish(colors, 'officeSouthWestGlass', (0.105, 0.135, 0.145), 0.28, 0.23)
    finish(colors, 'officeSouthDoorBronze', (0.073, 0.067, 0.065), 0.44, 0.20)
    finish(colors, 'officeSouthLobbyPanel', (0.55, 0.56, 0.49), 0.71)
    finish(colors, 'officeSouthLobbyLintel', (0.127, 0.117, 0.11), 0.74)
    for col in opening['columns']:
        col.update(
            finish='officeSouthPinkStone',
            base=dict(height=0.39, capHeight=0.10, projection=0.10),
            capital=dict(height=0.20, taperHeight=0.11, projection=0.075),
        )
    for face in f['facades']:
        if face['part'] == portico['id']:
            face.update(height=portico['height'], minimumHeight=SOFFIT)
        if face['part'] == 'main' and (
            face['edge'] in (1, 2, 5)
            or (face['edge'] is None and face['normal'][0] < -0.99)
        ):
            face['rule']['windows'] = False
    east_terrace(b)
    return b


def add_west(b, z, C, detail):
    m = Mesh()
    entry = b['form']['entrances'][0]
    cx, cy = entry['outerCenter']
    a = math.radians(entry['bearing'])
    sn, cs = math.sin(a), math.cos(a)

    def xyz(u, d, h):
        return cx - cs * u - sn * d, cy + sn * u - cs * d, z + h

    def box(u, d, h, w, depth, height, mat):
        m.box(*xyz(u, d, h), w, depth, height, mat, -a)

    def panel(u, d, bottom, w, height, mat):
        m.face(
            [
                xyz(u - w / 2, d, bottom),
                xyz(u + w / 2, d, bottom),
                xyz(u + w / 2, d, bottom + height),
                xyz(u - w / 2, d, bottom + height),
            ],
            mat,
        )

    wall = finish(C, 'officeSouthWestRender', (0.50, 0.485, 0.46), 0.83)
    cap = finish(C, 'officeSouthCoping', (0.38, 0.375, 0.36), 0.73)
    frame = finish(C, 'officeSouthAluminium', (0.49, 0.50, 0.49), 0.52, 0.28)
    pane = finish(C, 'officeSouthWestGlass', (0.105, 0.135, 0.145), 0.28, 0.23)
    # Upper two bands with six lights between the two raised ends.
    for h in (12.65, 15.87):
        panel(0, 4.32, h, 22.2, 2.21, pane)
        for hh in (h, h + 2.21):
            box(0, 4.26, hh, 22.25, 0.13, 0.11, frame)
        for i in range(1, 6):
            box(-11.1 + i * 3.7, 4.22, h + 1.1, 0.22, 0.22, 2.27, wall)
        if detail:
            box(0, 4.23, h + 1.52, 22.15, 0.12, 0.066, frame)
            for i in range(6):
                for j in (1, 2):
                    box(
                        -11.1 + (i + j / 3) * 3.7,
                        4.25,
                        h + 1.1,
                        0.055,
                        0.10,
                        2.14,
                        frame,
                    )
    for i in range(1, 6):
        box(-11.1 + i * 3.7, 4.22, 15.83, 0.19, 0.26, 8.25, wall)
    # The paired ends have narrow, faceted bay windows, a raised rectangular
    # head and a projecting flat coping. Side depth is estimated.
    for sign in (-1, 1):
        u = sign * 12.40
        box(u, 4.0, (SOFFIT + 25.40) / 2, 4.02, 7.30, 25.40 - SOFFIT, wall)
        box(sign * 13.9, 2.65, SOFFIT / 2, 2.0, 4.6, SOFFIT, wall)
        box(u, 4.0, 25.63, 4.83, 7.95, 0.46, cap)
        box(u, 4.0, 25.15, 4.30, 7.48, 0.15, wall)
        # Front shell of each oriel projects in three facets rather than
        # assuming a flat strip on the existing stair wall.
        profile = [(-0.98, 0.35), (-0.61, -0.20), (0.61, -0.20), (0.98, 0.35)]
        for (l, dl), (r, dr) in zip(profile, profile[1:]):
            m.face(
                [
                    xyz(u + l, dl, 2.85),
                    xyz(u + r, dr, 2.85),
                    xyz(u + r, dr, 19.35),
                    xyz(u + l, dl, 19.35),
                ],
                pane,
            )
        m.face([xyz(u + x, d, 19.35) for x, d in profile], cap)
        m.face([xyz(u + x, d, 2.85) for x, d in reversed(profile)], cap)
        for x, d in profile:
            box(u + x, d - 0.028, 11.10, 0.070, 0.08, 16.59, frame)
        for h in (2.87, 5.30, 7.62, 9.85, 12.18, 14.53, 16.85, 19.33):
            for (l, dl), (r, dr) in zip(profile, profile[1:]):
                m.face(
                    [
                        xyz(u + l, dl - 0.045, h - 0.052),
                        xyz(u + r, dr - 0.045, h - 0.052),
                        xyz(u + r, dr - 0.045, h + 0.052),
                        xyz(u + l, dl - 0.045, h + 0.052),
                    ],
                    frame,
                )
        box(u, 0.03, 2.80, 2.02, 0.81, 0.16, cap)
    # The rear lobby wall replaces the generic recessed glazing via its
    # building-specific hook. The original stair/landing generator still runs.
    return m


def lobby(m, entry, z, C):
    a = math.radians(entry['bearing'])
    cx, cy = entry['center']

    def box(u, h, w, height, depth, mat):
        x = cx - math.cos(a) * u + math.sin(a) * depth
        y = cy + math.sin(a) * u + math.cos(a) * depth
        m.box(x, y, z + h, w, 0.055, height, mat, -a)

    def mat(name):
        return C['officeSouth' + name]

    # In the 2025 view both side bays have pale lower panels and distinct
    # dark leaf openings. The upper strip spans all three bays.
    box(0, 2.66, 23.64, 4.12, 0.066, mat('LobbyLintel'))
    for u in (-7.95, 7.95):
        box(u, 1.73, 7.46, 2.22, 0.13, mat('LobbyPanel'))
        door_at = u + (2.23 if u < 0 else -0.24)
        box(door_at, 1.52, 1.10, 1.80, 0.175, mat('DoorBronze'))
        for i in range(7):
            box(u - 3.73 + i * 7.46 / 6, 1.73, 0.073, 2.24, 0.20, mat('DoorBronze'))
        box(u, 2.94, 7.47, 0.34, 0.14, mat('WestGlass'))
    box(0, 1.88, 7.14, 2.55, 0.15, mat('WestGlass'))
    for u in (-3.57, -2.13, 0, 2.13, 3.57):
        box(u, 1.88, 0.13, 2.57, 0.21, mat('DoorBronze'))
    for h in (0.66, 1.71, 3.15):
        box(0, h, 7.16, 0.125, 0.21, mat('DoorBronze'))
    for u in (-3.57, -1.19, 1.19, 3.57):
        box(u, 3.69, 0.09, 0.94, 0.17, mat('DoorBronze'))
    box(0, 3.22, 23.64, 0.15, 0.22, mat('DoorBronze'))


def east_terrace(b):
    from mathutils import Vector
    from mathutils.geometry import tessellate_polygon

    body = b['form']['parts'][0]
    # Preserve the long east ground edge. The upper wall returns behind the
    # third-floor terrace, with five-storey wings at both ends in 2019.
    ring = body['polygons'][0][0][:-1]
    north, south = ring[1], ring[2]

    def edge_at(y):
        t = (y - north[1]) / (south[1] - north[1])
        return [north[0] + t * (south[0] - north[0]), y]

    n = edge_at(-648.55)
    s = edge_at(-670.95)
    ni = [n[0] - 8.0, n[1]]
    si = [s[0] - 8.0, s[1]]
    outline = ring[:2] + [n, ni, si, s] + ring[2:]

    def set_ring(part, points):
        area = sum(
            a[0] * c[1] - c[0] * a[1] for a, c in zip(points, points[1:] + points[:1])
        )
        if area < 0:
            points = list(reversed(points))
        vertices = [Vector((x, y, 0)) for x, y in points]
        part['polygons'] = [[points + [points[0]]]]
        indices = []
        for a, b, c in tessellate_polygon([vertices]):
            up = (vertices[b] - vertices[a]).cross(vertices[c] - vertices[a]).z
            indices.extend((a, b, c) if up > 0 else (a, c, b))
        part['triangles'] = [indices]

    # Project-book roofline and window ribbons place the upper centre behind
    # the two west ends. Retain the existing recess at lobby level.
    old_n, old_s = ring[8], ring[7]
    new_n = [old_n[0] + 2.19, old_n[1]]
    new_s = [old_s[0] + 2.19, old_s[1]]
    outline = [new_n if q is old_n else new_s if q is old_s else q for q in outline]
    set_ring(body, outline)
    backing = dict(
        id='west-lobby-backing',
        height=TOP - 0.8,
        levels=2,
        roof={'type': 'flat', 'rise': 0},
        parapetEdges=[],
    )
    set_ring(backing, [old_s, new_s, new_n, old_n])
    b['form']['parts'].append(backing)
    low = dict(
        id='east-three-storey-terrace',
        levels=3,
        height=12.6,
        baseDepth=0.8,
        roof={'type': 'flat', 'rise': 0},
    )
    set_ring(low, [n, s, si, ni])
    low['parapetEdges'] = [[n, s]]
    b['form']['parts'].append(low)


def side_walls(b, z, C, detail):
    m = Mesh()
    gray = finish(C, 'officeSouthEastGray', (0.32, 0.309, 0.30), 0.82)
    band = finish(C, 'officeSouthEastBand', (0.58, 0.55, 0.50), 0.77)
    skirt = finish(C, 'officeSouthEastPlinth', (0.087, 0.083, 0.084), 0.69)
    frame = finish(C, 'officeSouthAluminium', (0.49, 0.50, 0.49), 0.52, 0.28)
    glass = finish(C, 'officeSouthWestGlass', (0.105, 0.135, 0.145), 0.28, 0.23)
    sill = finish(C, 'officeSouthGreenSill', (0.164, 0.197, 0.18), 0.68)
    wing_edge = (-670.95, -648.55)
    for face in b['form']['facades']:
        if face['part'] != 'main' or face['edge'] not in (1, 2):
            continue
        east = face['edge'] == 1
        x0, y0 = face['start']
        x1, y1 = face['end']
        nx, ny = face['normal']
        length = math.hypot(x1 - x0, y1 - y0)
        ux, uy = (x1 - x0) / length, (y1 - y0) / length
        theta = math.atan2(uy, ux)

        def box(u, offset, h, w, d, t, mat):
            m.box(
                x0 + ux * u + nx * offset,
                y0 + uy * u + ny * offset,
                z + h,
                w,
                d,
                t,
                mat,
                theta,
            )

        def sheet(u, offset, h, w, t, mat):
            points = [
                (
                    x0 + ux * (u + v) + nx * offset,
                    y0 + uy * (u + v) + ny * offset,
                    z + h + zz,
                )
                for v, zz in [(-w / 2, 0), (w / 2, 0), (w / 2, t), (-w / 2, t)]
            ]
            m.face(points[::-1], mat)

        intervals = [(0, length)]
        if east:
            intervals = [
                (0, (wing_edge[1] - y0) / uy),
                ((wing_edge[0] - y0) / uy, length),
            ]
        openings = (
            [2.15, 6.47, 9.14, 13.05, 16.97, 21.2, 25.3, 29.05, 32.95, 36.35, 39.45]
            if east
            else [2.65, 6.75, 11.3, 15.45, 20.3, 24.75, 28.85]
        )
        for j, (low, high) in enumerate(
            [(0, 4.8), (4.8, 8.7), (8.7, 12.6), (12.6, 16.5), (16.5, 20.4)]
        ):
            regions = intervals if j >= 3 else [(0, length)]
            for l, r in regions:
                mid = (l + r) / 2
                w = r - l
                sheet(mid, 0.025, low, w, high - low, gray)
                if j == 0:
                    sheet(mid, 0.048, 0, w, 1.08, skirt)
                band_base = high - 0.78
                band_top = high + (0.89 if j < 4 and not (east and j == 2) else 0.04)
                sheet(mid, 0.07, band_base, w, band_top - band_base, band)
                box(mid, 0.075, band_base, w, 0.16, 0.072, band)
                for idx, u in enumerate(openings):
                    if not l + 0.7 < u < r - 0.7:
                        continue
                    ww = 1.40 if not east or idx not in [1, 8] else 0.84
                    bottom = low + (1.15 if j == 0 else 0.90)
                    head = band_base - (0.10 if j == 0 else 0.035)
                    dh = head - bottom
                    sheet(u, 0.065, bottom, ww, dh, glass)
                    if j == 0:
                        sheet(u, 0.09, bottom, ww, 0.90, sill)
                    if not detail:
                        sheet(u, 0.10, head - 0.69, ww, 0.05, frame)
                        sheet(u, 0.10, bottom, 0.055, dh, frame)
                        continue
                    for off in [-ww / 2, 0, ww / 2]:
                        box(u + off, 0.095, bottom + dh / 2, 0.055, 0.06, dh, frame)
                    for hh in [bottom, head - (0.82 if j == 0 else 0.70), head] + (
                        [bottom + 0.90] if not j else []
                    ):
                        box(u, 0.10, hh, ww, 0.07, 0.058, frame)
                    if detail:
                        for t in (-0.33, -0.17, 0.17, 0.33):
                            box(
                                u + ww * t,
                                0.126,
                                bottom + dh / 2,
                                0.015,
                                0.025,
                                dh,
                                frame,
                            )
        if not east:
            # Narrow south service doorway and projecting flat cover, below
            # the south-east corner station. Detached equipment is omitted.
            u = 12.95
            box(u, 0.10, 1.46, 1.25, 0.14, 2.55, skirt)
            box(u, 0.76, 3.78, 4.5, 1.54, 0.26, band)
            for i in range(2):
                box(
                    u,
                    0.32 + i * 0.27,
                    0.1 + (1 - i) * 0.095,
                    1.75,
                    0.51,
                    0.2 + (1 - i) * 0.19,
                    band,
                )
    return m


def tune_bands(mesh, z):
    # Two current pale courses have measurable boundaries on the unshaded
    # half. Piecewise remapping retains inscription topology and grille relief.
    roof = TOP - 0.8
    old = [
        SOFFIT,
        SOFFIT + 0.17 * (roof - SOFFIT),
        SOFFIT + (roof - SOFFIT) / 3,
        SOFFIT + 0.82 * (roof - SOFFIT),
        roof,
        TOP,
    ]
    new = [SOFFIT, 5.80, 6.71, 9.02, roof, TOP]

    def height(v):
        h = v - z
        for a, b, c, d in zip(old, old[1:], new, new[1:]):
            if h <= b + 1.0e-6:
                return z + c + (h - a) * (d - c) / (b - a)
        return v

    mesh.v = [(x, y, height(h)) for x, y, h in mesh.v]
    return mesh
