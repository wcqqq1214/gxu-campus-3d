"""Measured north wings and entrance, south lane, and their continuous masonry returns."""

from .alumni_walls import Wall
from .mesh_parts import remove_faces

# Segments are taken from the mapped outline; their knots retain the OSM wall direction.
NORTH = [
    (12.823, -618.984, 42.522, -619.017, 16.5),
    (42.532, -614.921, 59.028, -614.943, 19.8),
    (59.018, -618.026, 88.399, -618.060, 16.5),
]
SOUTH = [
    (9.705, -630.773, 43.9, -630.814, 16.5),
    (43.9, -630.814, 60.5, -630.834, 19.8),
    (60.5, -630.834, 92.338, -630.873, 16.5),
]


def replace_walls(mesh, z, C, M, detail):
    # Discard the photo overlays AND the underlying shell face. Peripheral floor
    # plates and the protected four-storey east corner stay in the previous mesh.
    obsolete = [
        (a, b)
        for name, a, b in mesh.parts
        if name in ('实拍可见立面', '多角度屋体、窗框与门厅')
    ]
    faces = [
        i for i, f in enumerate(mesh.f) if not any(a <= f[0] < b for a, b in obsolete)
    ]
    mesh.f = [mesh.f[i] for i in faces]
    mesh.m = [mesh.m[i] for i in faces]
    mesh.face_uvs = {
        j: mesh.face_uvs[i] for j, i in enumerate(faces) if i in mesh.face_uvs
    }

    def replaced(pts, mat):
        xs, ys, hs = zip(*pts)
        l, r = min(xs), max(xs)
        a, b = min(ys), max(ys)
        h0, h1 = min(hs) - z, max(hs) - z
        # North-facing yard return in the 196-degree foreground. The eastern tip
        # starts at 104.9; retain that entire four-storey facade and its rails.
        if (
            l >= 88.40 - 0.02
            and r <= 104.90 + 0.01
            and a >= -606.88
            and b <= -604.75
            and h1 <= 16.54
        ):
            if not (r - l < 0.015 and b - a > 0.8 and h1 - h0 > 3):
                return True
        # The gallery shoulder is blank on 078/079; retire the generic window boxes.
        if (
            l > 8.15
            and r < 9.79
            and a > -630.81
            and b < -627.40
            and h1 - h0 < 3.1
            and mat in (C['white'], C['Office opening'])
        ):
            return True
        for segments, normal in ((NORTH, 1), (SOUTH, -1)):
            for x0, y0, x1, y1, top in segments:
                if l < x0 - 1.55 or r > x1 + 1.55:
                    continue
                # Existing photo layers and projecting generic sills extend beyond endpoints.
                surface = (y0 + y1) / 2
                if normal == 1 and a >= surface - 0.075 and b <= surface + 3.05:
                    pass
                elif normal == -1 and a >= surface - 3.1 and b <= surface + 0.075:
                    pass
                else:
                    continue
                if (
                    h1 > top + 0.025
                    and (a < surface - 0.065 or b > surface + 0.065)
                    and h0 >= top - 0.023
                ):
                    continue
                if r - l < 0.018 and b - a > 1.70 and h1 - h0 > 8:
                    continue
                return True
        # Generic protruding frames on the two blank portal returns visible from 218°.
        for x, low, high, out in [
            (59.023, -618.03, -614.94, 1),
            (42.527, -619.02, -614.92, -1),
        ]:
            if (
                a >= low - 0.03
                and b <= high + 0.03
                and all(0.025 < (u - x) * out < 1.65 for u in xs)
                and h1 - h0 < 4.5
            ):
                return True
        return False

    remove_faces(mesh, replaced)
    # Photo-derived paint replaces the old uniformly lit amber outside the held east tip.
    for i, face in enumerate(mesh.f):
        if mesh.m[i] == C['Office gold'] and max(mesh.v[j][0] for j in face) < 104.85:
            mesh.m[i] = M['plaster']
    eastcols = [60.65, 64.82, 68.87, 73.12, 77.14, 81.25]
    westcols = [15.23, 19.42, 23.66, 27.91, 32.1, 36.26, 40.39]

    def rows(w, cols, floors, pitch=3.25, sill=1.12, width=1.56, opened=(), vents=True):
        for col, x in enumerate(cols):
            for j in range(floors):
                h = sill + j * pitch
                u = x - w.start[0]
                leaf = next((side for c, k, side in opened if (c, k) == (col, j)), 0)
                w.aperture(u, width, h, h + 2.02, 'window', leaf)
                if j and vents:
                    w.aperture(u, 0.24, h - 0.50, h - 0.34, 'vent')

    def make(section, n):
        x, y, xx, yy, top = section
        return Wall((x, y), (xx, yy), (0, n), z, M, detail)

    def portal(w, n):
        offset = w.start[0]

        def pos(x):
            return x - offset

        rows(
            w,
            [45.26, 56.45],
            6,
            pitch=3.17,
            sill=1.15,
            width=1.64,
            vents=False,
            opened=[(0, 2, 1), (0, 5, 1), (1, 1, -1)]
            if n < 0
            else [(0, 0, 1), (0, 2, 1), (1, 4, -1)],
        )
        bays = [(48.53, 1.24), (50.90, 2.16), (53.20, 1.29)]
        for ix, (x, width) in enumerate(bays):
            w.aperture(
                pos(x),
                width,
                0.085,
                2.75,
                'diamond' if n > 0 and ix == 1 else 'glazed' if n < 0 else 'door',
            )
            for low in (3.63, 6.78, 9.93, 13.04, 15.76, 18.0):
                w.aperture(pos(x), width, low, min(low + 1.77, 19.55), 'screen')
        for x in (47.42, 49.51, 52.23, 54.30):
            w.pier(pos(x), 0.07, 19.67, 0.21, 0.16)
        for x in (47.42, 54.30):
            w.pier(pos(x), 0.07, 19.69, 0.068, 0.185, 'cream')
        w.box(
            w.trim,
            pos(46.37),
            pos(55.47),
            3.12,
            3.24,
            -0.14,
            1.10 if n > 0 else 1.58,
            'sill',
        )
        w.box(
            w.trim,
            pos(46.57),
            pos(55.24),
            -0.02,
            0.079,
            -0.03,
            1.31 if n > 0 else 1.85,
            'foot',
        )
        return pos(47.40), pos(54.33)

    for j, section in enumerate(NORTH):
        w = make(section, 1)
        entry = None
        if j == 1:
            entry = portal(w, 1)
        else:
            if j == 2:
                rows(
                    w,
                    eastcols,
                    5,
                    opened=[
                        (0, 1, -1),
                        (1, 2, 1),
                        (2, 0, -1),
                        (2, 2, 1),
                        (3, 1, 1),
                        (3, 2, 1),
                        (4, 1, 1),
                        (5, 0, -1),
                        (5, 3, 1),
                    ],
                )
                for level in range(5):
                    for xx in (83.61, 84.93, 86.25, 87.57):
                        lo = 2.1 + level * 2.99
                        w.aperture(xx - w.start[0], 1.01, lo, lo + 1.21, 'screen')
                for x in (67.05, 75.42, 83.01):
                    w.pipe(x - w.start[0], 16.3)
            else:
                rows(
                    w,
                    westcols,
                    5,
                    opened=[(2, 3, 1), (3, 1, -1), (5, 3, -1), (6, 1, 1)],
                )
                for x in (21.53, 33.95):
                    w.pipe(x - w.start[0], 16.3)
        w.build(mesh, section[-1], ['北面西长翼', '北主门厅', '北面东长翼'][j], entry)
    # South lane: 018° resolves six consecutive bays, 074°/077° the bays west of the door.
    for j, section in enumerate(SOUTH):
        w = make(section, -1)
        entry = None
        if j == 1:
            entry = portal(w, -1)
        else:
            if j == 2:
                cols = [
                    62.8,
                    65.55,
                    68.30,
                    71.05,
                    73.8,
                    76.55,
                    79.30,
                    82.05,
                    84.80,
                    87.55,
                    90.30,
                ]
            else:
                cols = [
                    11.68,
                    14.66,
                    17.65,
                    20.64,
                    23.63,
                    26.62,
                    29.61,
                    32.60,
                    35.59,
                    38.58,
                    41.57,
                ]
            rows(
                w,
                cols,
                5,
                pitch=3.17,
                width=1.26,
                sill=1.12,
                opened=[
                    (0, 2, -1),
                    (0, 3, -1),
                    (1, 1, 1),
                    (2, 2, 1),
                    (2, 3, 1),
                    (4, 2, 1),
                    (6, 1, 1),
                    (7, 0, -1),
                    (7, 3, 1),
                ],
            )
            for i in (1, 4, 7):
                w.pipe(cols[i] + 1.40 - w.start[0], 16.38)
        w.build(
            mesh, section[-1], ['巷侧西长翼', '巷侧玻璃门厅', '巷侧东长翼'][j], entry
        )

    yard = Wall((88.409, -606.772), (104.90, -606.79), (0, 1), z, M, detail)
    for j in range(5):
        lo = 1.56 + 3.10 * j
        for x in (89.70, 90.91, 92.12):
            yard.aperture(x - 88.409, 1.02, lo, lo + 1.13, 'screen')
        for x in (97.60, 99.36, 101.13, 103.20):
            yard.aperture(x - 88.409, 1.13, 1.12 + 3.15 * j, 3.06 + 3.15 * j, 'window')
        if j:
            yard.aperture(
                94.68 - 88.409, 2.40, 0.29 + 3.15 * j, 2.82 + 3.15 * j, 'balcony'
            )
        else:
            yard.aperture(94.68 - 88.409, 1.10, 0.035, 2.67, 'door')
    yard.build(mesh, 16.5, '东北院落转角之前的北墙', entry=(5.69, 6.80))
