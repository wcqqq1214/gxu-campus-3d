"""Add the photographed permanent components to this building's normal near/base Mesh."""

import json
import math
from functools import lru_cache
from pathlib import Path

from geometry import Mesh, material

P = Path(__file__).resolve().parent
PALETTE = {
    'pinkband': 'a37f7d',
    'tile': '805248',
    'cream': 'e7e3d7',
    'ochre': 'd7aa79',
    'salmon': 'e2bdad',
    'gold': 'd5aa59',
    'sand': 'e5c09a',
    'rose': 'b5998f',
    'base': '645c53',
    'stone': 'aba198',
    'door': '383633',
    'opening': '485054',
    'frame': 'd6d3c4',
    'recess': '655b4d',
    'brick': '944f44',
    'teal': '42695e',
    'iron': '656665',
    'lattice': '694934',
}
PALETTE.update(
    ivory='dfd5b8',
    ceramic='ccc9bd',
    wood='684b3a',
    lintel='c5b9a6',
    grill='b6b5a9',
    deep='554d49',
    animalWest='f5d6ab',
    animalMiddle='ecd0a7',
    animalCourse='e8cda4',
)


@lru_cache(maxsize=1)
def measured():
    return json.loads((P / 'measured.json').read_text())


def palette(C):
    for k, c in PALETTE.items():
        key = 'Office ' + k
        if key not in C:
            rgb = [int(c[i : i + 2], 16) / 255 for i in (0, 2, 4)]
            C[key] = material(
                key,
                [
                    ((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92
                    for x in rgb
                ],
            )


def relief(key, z, C, detail):
    mesh = Mesh()
    record = measured()[key]
    for item in record['layers']:
        kind = item['kind']
        if not detail and kind in ('iron', 'frame'):
            continue
        nx, ny = item['normal']
        dist = item['relief']
        points = item['points']

        def verts(offset):
            return [(x + nx * offset, y + ny * offset, h + z) for x, y, h in points]

        # Build the front and edge returns. The backing is the host wall.
        cap = verts(dist)
        inner = verts(
            max(0.015, dist - 0.07)
            if kind
            in (
                'opening',
                'frame',
                'iron',
                'lattice',
                'teal',
                'grill',
                'wood',
                'lintel',
            )
            else 0.02
        )
        ax, ay, az = cap[0]
        bx, by, bz = cap[1]
        cx, cy, cz = cap[2]
        outward = ((by - ay) * (cz - az) - (bz - az) * (cy - ay)) * nx + (
            (bz - az) * (cx - ax) - (bx - ax) * (cz - az)
        ) * ny
        if outward < 0:
            cap.reverse()
            inner.reverse()
        mat = C['Office ' + kind]
        mesh.face(cap, mat)
        # Slender grille and sash strips keep their visible fronts in the overview.
        if (
            not detail
            and key in {'759096563', '1501460942'}
            and kind in {'grill', 'wood'}
        ):
            continue
        for i, b in enumerate(cap):
            j = (i + 1) % len(cap)
            mesh.face([inner[i], inner[j], cap[j], b], mat)
    return mesh


# Body material identity is retained on unseen faces unless more than one source confirms the finish.
TINT = {
    '957503108': ('stone', 'cream'),
    '759337807': ('stone', 'cream'),
    '759096563': ('stone', 'salmon'),
    '759147086': ('pink', 'gold'),
    '759132932': ('stone', 'ochre'),
}


def shape_body(mesh, b, C, z):
    key = b['id'].split('/')[-1]
    if key in TINT:
        old, new = TINT[key]
        mesh.m = [C['Office ' + new] if v == C[old] else v for v in mesh.m]
    # Remove the old generic windows, sill returns and protruding canopies only on
    # observed, resurfaced patches. Preserve the backing shell and unseen elevations.
    keep = []
    sheets = [
        l
        for l in measured()[key]['layers']
        if l['kind']
        in (
            'cream',
            'gold',
            'salmon',
            'ochre',
            'rose',
            'sand',
            'animalWest',
            'animalMiddle',
        )
        and len(l['points']) >= 4
    ]
    regions = []
    for sheet in sheets:
        nx, ny = sheet['normal']
        pts = sheet['points']
        tx, ty = -ny, nx
        u = [x * tx + y * ty for x, y, h in pts]
        h = [p[2] for p in pts]
        if max(u) - min(u) < 4 or max(h) - min(h) < 3:
            continue
        regions.append(
            (
                nx,
                ny,
                tx,
                ty,
                pts[0][0] * nx + pts[0][1] * ny,
                min(u),
                max(u),
                min(h),
                max(h),
            )
        )
    for i, face in enumerate(mesh.f):
        pts = [mesh.v[j] for j in face]
        x = sum(q[0] for q in pts) / len(pts)
        y = sum(q[1] for q in pts) / len(pts)
        h = sum(q[2] for q in pts) / len(pts) - z
        covered = False
        for nx, ny, tx, ty, d, u0, u1, h0, h1 in regions:
            u = x * tx + y * ty
            off = x * nx + y * ny - d
            if (
                u0 - 0.15 < u < u1 + 0.15
                and h0 - 0.2 < h < h1 + 0.2
                and 0.009 < off < 2.65
            ):
                covered = True
                break
        if not covered:
            keep.append(i)
    mesh.f = [mesh.f[i] for i in keep]
    mesh.m = [mesh.m[i] for i in keep]
    mesh.face_uvs = {
        j: mesh.face_uvs[i] for j, i in enumerate(keep) if i in mesh.face_uvs
    }
    import bisect

    used = sorted({i for f in mesh.f for i in f})
    remap = {old: new for new, old in enumerate(used)}
    mesh.v = [mesh.v[i] for i in used]
    mesh.f = [tuple(remap[j] for j in f) for f in mesh.f]
    mesh.parts = [
        (name, bisect.bisect_left(used, l), bisect.bisect_left(used, r))
        for name, l, r in mesh.parts
    ]


def structures(key, z, C, detail):
    m = Mesh()

    def box(x, y, h, w, d, height, kind, angle=0):
        m.box(x, y, z + h, w, d, height, C['Office ' + kind], angle)

    if key == '759337787':
        # Two independently visible round supports and layered fascia around the east corner.
        # Projection along the oblique return is estimated; the supported canopy joins the old shell.
        start = (-475.35, -622.43)
        end = (-480.15, -616.61)
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = math.hypot(dx, dy)
        theta = math.atan2(dy, dx)
        nx, ny = dy / length, -dx / length
        mid = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
        for cx, cy in (start, end):
            m.cylinder(
                cx, cy, z + 2.99, 0.32, 4.45, C['Office stone'], 20 if detail else 12
            )
            m.cylinder(
                cx, cy, z + 0.78, 0.39, 0.22, C['Office base'], 20 if detail else 12
            )
            m.cylinder(
                cx, cy, z + 5.18, 0.39, 0.24, C['Office stone'], 20 if detail else 12
            )
        for h, d, width, thick, material in [
            (5.36, 3.35, length + 2.0, 0.42, 'stone'),
            (5.64, 3.52, length + 2.12, 0.15, 'cream'),
            (5.85, 3.40, length + 2.0, 0.28, 'rose'),
        ]:
            box(
                mid[0] - nx * 0.83,
                mid[1] - ny * 0.83,
                h,
                width,
                d,
                thick,
                material,
                theta,
            )
        for j in range(4):
            box(
                mid[0] - nx * (0.55 + j * 0.17),
                mid[1] - ny * (0.55 + j * 0.17),
                0.10 + 0.17 * j,
                length + 2.45 - 0.12 * j,
                4.05 - 0.34 * j,
                0.20,
                'stone',
                theta,
            )
    if key == '1501460949':
        # Rounded north cornice caps and vertical piers, visible above the buses.
        for x, y, radius in [(604.53, -607.70, 1.07), (600.79, -607.75, 0.89)]:
            box(x, y, 11.29, radius * 1.6, 0.45, 9.8, 'cream')
            m.cylinder(
                x, y, z + 16.08, radius, 1.04, C['Office cream'], 24 if detail else 12
            )
            m.cylinder(
                x,
                y,
                z + 15.52,
                radius * 0.96,
                0.13,
                C['Office ochre'],
                24 if detail else 12,
            )
    if key == '759096577':
        # Both visible ridge ends are cut back from the short ends of the existing
        # three-storey courtyard wing. Ridge depth and far slope remain estimates.
        a, b = 519.05, 550.12
        front, back = -476.26, -486.84
        outline = [(a, front), (b, front), (b, back), (a, back)]
        lo = [(x, y, z + 9.96) for x, y in outline]
        mid = (front + back) * 0.5
        rl = (a + 3.5, mid, z + 12.65)
        rr = (b - 3.5, mid, z + 12.65)
        for q in [
            (lo[0], lo[1], rr, rl),
            (lo[1], lo[2], rr),
            (lo[2], lo[3], rl, rr),
            (lo[3], lo[0], rl),
        ]:
            m.face(q, C['Office tile'])
    if key == '759132932':
        for y in [-723.67, -735.06]:
            for lo, top in [(1.45, 3.13), (4.64, 6.57)]:
                # Write the face below the existing window reveals; windows remain in front.
                box(-102.04, y, (lo + top) / 2, 56.35, 0.045, top - lo, 'brick')
            box(-102.04, y, 0.24, 56.35, 0.05, 0.48, 'base')
    if key == '957503108':
        # Return the visible gable into the old roof, joining the end face to a solid mass.
        pts = [(-561.0, 14.85), (-551.7, 18.25), (-544.3, 14.85)]
        a = [(-394.15, y, z + h) for y, h in pts]
        c = [(-396.20, y, z + h) for y, h in pts]
        m.face(a, C['Office cream'])
        m.face(c[::-1], C['Office cream'])
        for i in range(3):
            j = (i + 1) % 3
            m.face([a[i], c[i], c[j], a[j]], C['Office cream'])
    if key == '1501460942':
        origin = (575.6, -518.72)
        n = (0.696, 0.718)
        t = (-0.718, 0.696)

        def pt(u, d, h):
            return (
                origin[0] + u * t[0] + d * n[0],
                origin[1] + u * t[1] + d * n[1],
                z + h,
            )

        def patch(coords, kind):
            m.face([pt(*p) for p in coords], C['Office ' + kind])

        # Five rounded parapets; the open backs are joined to the wall. The observed
        # radius in the plane of the facade is better constrained than the projection.
        for sill in [3.25, 6.50, 9.80, 13.1, 16.4]:
            r = 1.82
            depth = 1.20
            steps = 18 if detail else 9
            ring = [
                (
                    r * math.cos(math.pi * i / steps),
                    0.30 + depth * math.sin(math.pi * i / steps),
                )
                for i in range(steps + 1)
            ]
            patch([(u, v, sill - 0.16) for u, v in ring], 'stone')
            patch([(u, v, sill) for u, v in ring[::-1]], 'cream')
            for (u, v), (x, y) in zip(ring, ring[1:]):
                patch(
                    [
                        (u, v, sill - 0.15),
                        (x, y, sill - 0.15),
                        (x, y, sill + 1.07),
                        (u, v, sill + 1.07),
                    ],
                    'cream',
                )
                inner = lambda a, b: (a * 0.94, 0.30 + (b - 0.30) * 0.87)
                iu, iv = inner(u, v)
                ix, iy = inner(x, y)
                patch(
                    [
                        (u, v, sill + 1.07),
                        (x, y, sill + 1.07),
                        (ix, iy, sill + 1.07),
                        (iu, iv, sill + 1.07),
                    ],
                    'cream',
                )
                patch(
                    [
                        (iu, iv, sill + 1.07),
                        (ix, iy, sill + 1.07),
                        (ix, iy, sill),
                        (iu, iv, sill),
                    ],
                    'cream',
                )
        for u1, u2 in [(5.9, 13.35), (13.67, 18.48), (18.80, 22.2)]:
            patch(
                [
                    (u1, 0.30, 0.15),
                    (u2, 0.30, 0.15),
                    (u2, 0.30, 7.50),
                    (u1, 0.30, 7.50),
                ],
                'cream',
            )
            for h in [0.66, 4.19]:
                height = 1.48 if h < 2 else 1.36
                patch(
                    [
                        (u1 + 0.18, 0.32, h),
                        (u2 - 0.18, 0.32, h),
                        (u2 - 0.18, 0.32, h + height),
                        (u1 + 0.18, 0.32, h + height),
                    ],
                    'opening',
                )
                for j in range(1, 6 if detail else 3):
                    a = u1 + (u2 - u1) * j / (6 if detail else 3)
                    patch(
                        [
                            (a - 0.024, 0.34, h),
                            (a + 0.024, 0.34, h),
                            (a + 0.024, 0.34, h + 1.48),
                            (a - 0.024, 0.34, h + 1.48),
                        ],
                        'frame',
                    )
        patch(
            [
                (5.9, 0.30, 7.5),
                (22.2, 0.30, 7.5),
                (22.2, -2.25, 7.5),
                (5.9, -2.25, 7.5),
            ],
            'stone',
        )
    return m
