"""Sports College and Animal Reproduction Institute facades."""

from functools import partial

from geometry import Mesh
from humanities_facades import finish
from south_gate import inscription

SPORTS, ANIMAL = 'way/948683812', 'way/880036336'
MODEL_IDS = (SPORTS, ANIMAL)


def surface(m, l, r, b, t, d, mat):
    m.face([(l, d, b), (r, d, b), (r, d, t), (l, d, t)], mat)


def window(m, x, h, w, height, glass, frame, fine, grille=False, *, jamb_back=-0.1095):
    bottom = h - height / 2
    top = h + height / 2
    surface(m, x - w / 2, x + w / 2, bottom, top, -0.108, glass)
    front = -0.1645
    for u in (x - w / 2, x + w / 2):
        m.box(u, (front + jamb_back) / 2, h, 0.05, jamb_back - front, height, frame)
    m.box(x, -0.137, h, 0.05, 0.055, height, frame)
    for v in (bottom, top):
        m.box(x, (front + jamb_back) / 2, v, w, jamb_back - front, 0.05, frame)
    m.box(x, -0.137, top - height * 0.32, w, 0.055, 0.05, frame)
    if fine and grille:
        for i in range(1, 8):
            surface(
                m,
                x - w / 2 + w * i / 8 - 0.009,
                x - w / 2 + w * i / 8 + 0.009,
                bottom,
                top,
                -0.17,
                frame,
            )
        m.box(x, -0.16, h, w, 0.035, 0.025, frame)


# Carry the outside frame through the stucco. The glazing and grille keep their offsets.
SPORTS_BACK = -0.015
sports_window = partial(window, jamb_back=SPORTS_BACK)


def sports_sill(wall, x, z, width, height, front, mat):
    wall.box(x, (front + SPORTS_BACK) / 2, z, width, SPORTS_BACK - front, height, mat)


def sports(b, z, C, detail):
    from college_facades import attach, wall_frame

    mesh = Mesh()
    ring = b['polygons'][0][0]
    salmon = finish(C, 'FacultySportsTerracotta', (0.46, 0.235, 0.173), 0.82)
    panel = finish(C, 'FacultySportsCreamStone', (0.58, 0.54, 0.435), 0.76)
    glazing = finish(C, 'FacultySportsGlazing', (0.092, 0.111, 0.123), 0.34, 0.17)
    shadow = finish(C, 'FacultySportsReveal', (0.13, 0.115, 0.098), 0.80)
    frame = finish(C, 'FacultySportsFrames', (0.30, 0.31, 0.30), 0.63)
    hood = finish(C, 'FacultySportsWindowHood', (0.53, 0.49, 0.435), 0.76)
    upper = finish(C, 'FacultySportsUpperStone', (0.48, 0.443, 0.39), 0.83)
    for edge in (0, 1, 2):
        wf = wall_frame(ring, edge)
        L = wf[3]
        wall = Mesh()
        surface(wall, -L / 2, L / 2, 0, 3.24, -0.027, salmon)
        # Flush roof screens replace the stock white rim on the photographed edges.
        # Both ground views show a break above the square recess beside the signed corner.
        surface(wall, -L / 2, L / 2, 3.24, 6.60, -0.036, upper)
        if edge == 0:
            for l, r, h in [(-L / 2, -L * 0.365, 6.84), (-L * 0.365, L / 2, 7.92)]:
                wall.box(
                    (l + r) / 2, 0.022, (h + 6.57) / 2, r - l, 0.14, h - 6.57, upper
                )
        else:
            wall.box(0, 0.022, 6.99, L, 0.14, 0.84, upper)
        if edge == 1:
            # Continuous stone surrounds and a recessed dark opening below the sign.
            for side in (-1, 1):
                width = (L - 2.95) / 2
                wall.box(
                    side * (1.475 + width / 2), -0.07, 1.56, width, 0.16, 3.12, panel
                )
                if detail:
                    for hh in (0.62, 1.24, 1.86, 2.48):
                        wall.box(
                            side * (1.475 + width / 2),
                            -0.153,
                            hh,
                            width,
                            0.012,
                            0.018,
                            shadow,
                        )
            sports_window(wall, 0, 1.48, 2.95, 2.96, glazing, frame, detail, True)
            wall.box(0, -0.14, 3.26, L, 0.30, 0.60, panel)
            if detail:
                wall.extend(
                    inscription(
                        '体育学院',
                        0,
                        -0.30,
                        3.27,
                        2.85,
                        0.44,
                        C['dark'],
                        False,
                        flat=True,
                    )
                )
            sports_window(wall, 0, 4.88, 2.85, 1.57, glazing, frame, detail, True)
            sports_window(wall, 0, 5.95, 1.00, 0.54, glazing, frame, detail)
        elif edge == 0:
            # Signed diagonal at the south end, then a small squared recess and four crowned lights.
            wall.box(0, -0.15, 3.02, L, 0.36, 0.51, salmon)
            for t in (0.13, 0.35, 0.57, 0.77):
                # This ring runs from north to south; wall_frame reverses it.
                x = (0.5 - t) * L
                sports_window(wall, x, 4.93, 1.90, 1.74, glazing, frame, detail, True)
                crown = [
                    (x - 1.08, -0.15, 5.82),
                    (x + 1.08, -0.15, 5.82),
                    (x, -0.16, 6.19),
                ]
                back = [(u, SPORTS_BACK, z) for u, _, z in crown]
                wall.face(crown, hood)
                for i in range(3):
                    j = (i + 1) % 3
                    wall.face([back[i], back[j], crown[j], crown[i]], hood)
                sports_sill(wall, x, 4.00, 2.10, 0.075, -0.24, hood)
            # Recess is visible in both the campus gallery and the independent street station.
            x = -L * 0.445
            surface(wall, x - 0.85, x + 0.85, 4.13, 5.75, -0.096, shadow)
            wall.box(x, -0.25, 4.10, 1.84, 0.47, 0.11, panel)
            wall.box(x, -0.25, 5.82, 1.88, 0.47, 0.14, hood)
            for t, w in ((0.20, 1.1), (0.49, 1.65), (0.65, 1.05), (0.82, 2.50)):
                sports_window(
                    wall, (0.5 - t) * L, 1.52, w, 1.67, glazing, frame, detail, True
                )
        else:
            for i in range(4):
                x = (i - 1.5) * L / 4.55
                sports_window(wall, x, 4.8, 1.65, 1.48, glazing, frame, detail, True)
            south_ground(wall, L, salmon, glazing, frame, detail)
        attach(mesh, wall, wf, z)
    return mesh


def animal(b, z, C, detail):
    from college_facades import attach, wall_frame

    mesh = Mesh()
    ring = b['polygons'][0][0]
    wallmat = finish(C, 'FacultyAnimalWallTile', (0.50, 0.337, 0.275), 0.83)
    endwall = finish(C, 'FacultyAnimalEndTile', (0.54, 0.398, 0.335), 0.79)
    course = finish(C, 'FacultyAnimalTileBand', (0.36, 0.289, 0.255), 0.79)
    base = finish(C, 'FacultyAnimalBrownPlinth', (0.275, 0.206, 0.17), 0.78)
    metal = finish(C, 'FacultyAnimalMetal', (0.55, 0.532, 0.424), 0.57, 0.15)
    edgecap = finish(C, 'FacultyAnimalCapping', (0.135, 0.118, 0.097), 0.64, 0.19)
    awning = finish(C, 'FacultyAnimalMetalSash', (0.111, 0.145, 0.109), 0.53, 0.21)
    glass = finish(C, 'FacultyAnimalWindow', (0.09, 0.104, 0.102), 0.4)
    frame = finish(C, 'FacultyAnimalFrame', (0.37, 0.343, 0.30), 0.64)
    for edge in (2, 7, 8):
        wf = wall_frame(ring, edge)
        L = wf[3]
        wall = Mesh()
        if edge == 2:
            surface(wall, -L / 2, L / 2, 0, 10.65, -0.032, endwall)
            for h in (0.47, 3.41, 6.70, 9.92):
                surface(wall, -L / 2, L / 2, h - 0.11, h + 0.11, -0.057, course)
            # One narrow stack on the plain east end, independent of long southern ranges.
            for h in (1.94, 5.15, 8.37):
                window(wall, -0.13, h, 1.68, 2.18, glass, frame, detail, True)
        else:
            surface(wall, -L / 2, L / 2, 0, 6.50, -0.038, wallmat)
            wall.box(0, -0.08, 0.48, L, 0.16, 0.96, base)
            wall.box(0, -0.22, 8.20, L + 0.43, 0.43, 3.32, metal)
            wall.box(0, -0.38, 6.54, L + 0.72, 0.79, 0.20, edgecap)
            wall.box(0, -0.27, 9.98, L + 0.58, 0.57, 0.12, edgecap)
            if detail:
                for i in range(1, round(L / 0.18)):
                    x = -L / 2 + i * 0.18
                    wall.face(
                        [
                            (x, -0.44, 6.57),
                            (x + 0.024, -0.458, 6.57),
                            (x + 0.024, -0.458, 9.91),
                            (x, -0.44, 9.91),
                        ],
                        metal,
                    )
            if edge == 7:
                for i in range(6):
                    x = (i - 2.5) * L / 6.4
                    for h in (2.03, 5.07):
                        window(wall, x, h, 1.31, 1.51, glass, frame, detail, True)
                    if i >= 2:
                        # Four dark top-hinged lights in the pale corrugated cladding.
                        u = (-0.176 + 0.153 * (i - 2)) * L
                        surface(wall, u - 0.68, u + 0.68, 8.12, 9.19, -0.46, edgecap)
                        for shift in (-0.335, 0.335):
                            wall.face(
                                [
                                    (u + shift - 0.322, -0.78, 8.11),
                                    (u + shift + 0.322, -0.78, 8.11),
                                    (u + shift + 0.322, -0.49, 9.17),
                                    (u + shift - 0.322, -0.49, 9.17),
                                ],
                                awning,
                            )
                for h in (2.92, 5.96):
                    wall.box(0, -0.39, h, L - 0.60, 0.78, 0.16, course)
            else:
                wall.box(0, -1.13, 3.32, 3.61, 2.26, 0.20, course)
                window(wall, 0, 1.50, 2.02, 2.99, glass, frame, detail)
        attach(mesh, wall, wf, z)
    return mesh


def south_ground(wall, length, salmon, glass, frame, detail):
    # Retain the old western bay beyond the photographed sector.
    sports_window(wall, -1.5 * length / 4.55, 1.66, 1.68, 1.28, glass, frame, detail)
    # Outer sill and head positions include the shallow stucco surrounds.
    for x, h, w, height in (
        (0.88, 1.20, 0.87, 1.72),
        (2.76, 1.23, 0.92, 1.66),
        (6.34, 1.29, 0.94, 1.68),
        (8.67, 1.34, 2.30, 1.65),
    ):
        sports_window(wall, x, h, w, height, glass, frame, detail, True)
        sports_sill(wall, x, h - height / 2 - 0.04, w + 0.20, 0.08, -0.305, salmon)
    # The band is visible from the left crop to the cream corner column.
    left = -3.4
    right = length / 2
    wall.box((left + right) / 2, -0.19, 2.81, right - left, 0.48, 0.72, salmon)


def build(b, z, C, detail, ordinary):
    ring = b['polygons'][0][0]
    assert (
        not b['form']['parts']
        and len(b['polygons']) == 1
        and len(b['polygons'][0]) == 1
    )
    changed = {0, 1, 2} if b['id'] == SPORTS else {7, 8}
    part = dict(
        polygons=b['polygons'],
        triangles=b['roofTriangles'],
        height=b['form']['height'],
        roof=b['form']['roof'],
        parapetEdges=[
            (a, c) for i, (a, c) in enumerate(zip(ring, ring[1:])) if i not in changed
        ],
    )
    local = {**b, 'form': {**b['form'], 'parts': [part]}}
    return ordinary(local, z, C, detail)
