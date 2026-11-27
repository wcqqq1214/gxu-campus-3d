"""Recessed entries and roof returns of the President’s Office and Junwu Hall."""

from math import hypot

from geometry import Mesh
from humanities_facades import finish

from .civic import build as civic_build
from .facade_solids import Facade, cut, opening, recess_shell

MODEL_IDS = ('way/957503108', 'way/759337787')


def finish_bay(m, C, f, l, r, floor, depth, hand, measured=None):
    # Wall panels surround real door and window reveals. Door and window heads differ.
    span = r - l
    lo = floor + 0.07
    hi = floor + 3.25
    if span < 2.55:
        holes = [(0.5, min(1.02, span - 0.43), lo, lo + 2.08, 'A deep door')]
    else:
        holes = [
            (0.27, span * 0.335, lo + 0.66, lo + 2.52, 'A gallery glass'),
            (0.75, span * 0.247, lo, lo + 2.10, 'A deep door'),
        ]
    edges = []
    for center, width, sill, head, mat in holes:
        u = l + span * (center if hand else 1 - center)
        edges.append((u - width / 2, u + width / 2, sill, head, mat))
    if measured is not None:
        edges = [
            (x0, x1, floor + sill, floor + head, mat)
            for x0, x1, sill, head, mat in measured
        ]
    cur = l
    for x0, x1, sill, head, mat in sorted(edges):
        if cur < x0:
            f.box(m, C, cur, x0, -depth - 0.22, -depth, lo, hi, 'A shade')
        if sill > lo:
            f.box(m, C, x0, x1, -depth - 0.22, -depth, lo, sill, 'A shade')
        f.box(m, C, x0, x1, -depth - 0.22, -depth, head, hi, 'A shade')
        f.box(m, C, x0, x1, -depth - 0.21, -depth - 0.15, sill, head, mat)
        if mat == 'A gallery glass':
            mid = (x0 + x1) / 2
            f.box(
                m,
                C,
                mid - 0.025,
                mid + 0.025,
                -depth - 0.15,
                -depth - 0.095,
                sill,
                head,
                'A sash',
            )
            f.box(
                m,
                C,
                x0,
                x1,
                -depth - 0.15,
                -depth - 0.09,
                head - 0.45,
                head - 0.395,
                'A sash',
            )
        cur = x1
    if cur < r:
        f.box(m, C, cur, r, -depth - 0.22, -depth, lo, hi, 'A shade')


def gallery(mesh, C, f, a, b, posts, detail):
    depth = 1.48
    floors = (3.55, 6.92, 10.32)
    mesh = cut(mesh, f, (a, b, -depth - 0.24, 1.18, 3.38, 13.55))
    m = Mesh()
    recess_shell(m, f, C, a, b, depth, 0.34, 3.41, 13.53, 'cream', back=False)
    bounds = [a, *posts, b]
    fixed = None
    if f.nx > 0.9:
        fixed = [
            (-4.11, -2.55, 0.72, 2.86, 'A gallery glass'),
            (-1.62, -0.60, 0.08, 2.61, 'A deep door'),
            (0.91, 1.71, 0.10, 2.50, 'A deep door'),
            (3.85, 5.23, 0.72, 2.85, 'A gallery glass'),
            (5.36, 5.94, 0.08, 2.62, 'A deep door'),
        ]
    elif f.nx < -0.9:
        fixed = [
            (2.16, 3.18, 0.80, 3.05, 'A gallery glass'),
            (4.50, 5.40, 0.10, 3.08, 'A deep door'),
        ]
    for floor in floors:
        if fixed:
            finish_bay(m, C, f, a, b, floor, depth, True, fixed)
        f.box(m, C, a, b, -depth, 0.42, floor - 0.12, floor + 0.07, 'stone')
        f.box(m, C, a, b, 0.22, 0.46, floor - 0.13, floor + 0.02, 'cream')
        for i, (l, r) in enumerate(zip(bounds, bounds[1:])):
            if not fixed:
                finish_bay(m, C, f, l, r, floor, depth, i % 2 == 0)
            f.box(m, C, l, r, 0.11, 0.30, floor + 0.89, floor + 1.05, 'cream')
            f.box(m, C, l, r, 0.13, 0.32, floor + 0.08, floor + 0.25, 'cream')
            count = max(4, round((r - l) / 0.42))
            for j in range(1, count):
                u = l + (r - l) * j / count
                f.box(
                    m,
                    C,
                    u - 0.055,
                    u + 0.055,
                    0.165,
                    0.275,
                    floor + 0.25,
                    floor + 0.89,
                    'ceramic',
                )
                if detail:
                    f.box(
                        m,
                        C,
                        u - 0.083,
                        u + 0.083,
                        0.14,
                        0.30,
                        floor + 0.29,
                        floor + 0.47,
                        'cream',
                    )
        for p in posts:
            f.box(
                m,
                C,
                p - 0.16,
                p + 0.16,
                -0.18,
                0.34,
                floor + 0.07,
                min(13.53, floor + 3.25),
                'cream',
            )
    mesh.add_part('实测凹廊、后墙窗及透空栏杆', m)
    return mesh


def president(mesh, z, C, detail):
    east = Facade(-394.26, -553.2, 1, 0, z)
    mesh = gallery(mesh, C, east, -5.80, 6.04, [-0.40, 1.72], detail)
    south = Facade(-420.75, -561.20, 0, -1, z)
    mesh = gallery(mesh, C, south, -5.80, 6.20, [-1.98, 1.85], detail)
    west = Facade(-438.92, -551.45, -1, 0, z)
    mesh = gallery(mesh, C, west, -0.05, 5.42, [], detail)
    # The west photograph shows continuous end piers beside the gallery.
    for l, r in ((-2.53, -0.05), (5.42, 6.42)):
        mesh = cut(mesh, west, (l, r, -0.18, 0.96, 3.37, 13.64))
        pier = Mesh()
        west.box(pier, C, l, r, -0.18, 0.12, 3.37, 13.64, 'cream')
        mesh.add_part('西廊实墙侧垛', pier)
    # 303-degree oblique resolves ground openings below the gallery, above the planting bed.
    for l, r in ((-3.7, -2.22), (-0.65, 0.68), (2.28, 3.48)):
        mesh = cut(mesh, east, (l, r, -0.26, 0.80, 0.44, 2.50))
        wall = Mesh()
        recess_shell(wall, east, C, l, r, 0.23, 0.17, 0.46, 2.46, 'cream')
        opening(wall, east, C, l + 0.04, r - 0.04, 0.49, 2.41, -0.23, 2, detail)
        mesh.add_part('东山墙首层深窗', wall)
    # The eastern gable photograph shows a layered course returning around the corner.
    m = Mesh()
    for bottom, thickness, depth in [
        (13.74, 0.11, 0.48),
        (14.05, 0.23, 0.50),
        (14.43, 0.12, 0.58),
    ]:
        east.box(m, C, -8.24, 8.60, 0.30, depth, bottom, bottom + thickness, 'ceramic')
        Facade(-394.26, -561.24, 0, -1, z).box(
            m, C, -8.9, 0.0, 0.12, depth, bottom, bottom + thickness, 'ceramic'
        )
    mesh.add_part('东山墙转角叠檐', m)
    return mesh


def vestibule(mesh, f, C, a, b, top, detail, canopy):
    bottom = 0.68
    depth = 0.94
    mesh = cut(mesh, f, (a, b, -depth - 0.10, 1.02, bottom - 0.04, top + 0.07))
    m = Mesh()
    recess_shell(m, f, C, a, b, depth, 0.24, bottom, top, 'stone')
    width = b - a
    left = a + 0.205 * width
    right = b - 0.205 * width
    opening(m, f, C, left, right, bottom + 0.02, top - 0.12, -depth, 4, detail, True)
    for l, r in ((a + 0.13, left - 0.24), (right + 0.24, b - 0.13)):
        opening(m, f, C, l, r, bottom + 0.02, top - 0.12, -depth, 1, detail)
    for u in (left - 0.12, right + 0.12):
        f.box(m, C, u - 0.12, u + 0.12, -depth, 0.12, bottom, top, 'stone')
    # Real flight across the entrance. Separate non-overlapping treads with seated risers.
    for j in range(6):
        face = 0.24 + j * 0.28
        f.box(
            m,
            C,
            a - 0.14,
            b + 0.14,
            face,
            face + 0.28,
            -0.028,
            bottom * (6 - j) / 6,
            'stone',
        )
    for u in [a - 0.23, b + 0.23]:
        for j in range(6):
            v = 0.24 + j * 0.28
            f.box(
                m,
                C,
                u - 0.12,
                u + 0.12,
                v,
                v + 0.28,
                0.005,
                bottom * (6 - j) / 6 + 0.22,
                'base',
            )
    if canopy:
        f.box(m, C, a - 0.20, b + 0.20, -0.02, 1.14, top + 0.08, top + 0.31, 'stone')
        f.box(m, C, a - 0.23, b + 0.23, 0.98, 1.18, top + 0.31, top + 0.82, 'base')
    mesh.add_part('内退门扇、门框与整幅石阶', m)
    return mesh


def junwu(mesh, z, C, detail):
    # The 2025 courtyard photograph supports the tile family on inward-facing walls.
    # Keep each existing opening and the warm pink courses. The exact photographed bay is unlocated.
    surfaces = [
        ((-488.00, -642.67), (-487.98, -629.46)),
        ((-487.98, -629.46), (-496.43, -621.89)),
        ((-496.43, -621.89), (-511.34, -621.88)),
        ((-511.34, -621.88), (-511.37, -651.56)),
    ]
    for index, (face, mat) in enumerate(zip(mesh.f, mesh.m)):
        if mat != C['Office rose']:
            continue
        pts = [mesh.v[i] for i in face]
        if max(p[2] for p in pts) - min(p[2] for p in pts) < 0.15:
            continue
        for (x, y), (bx, by) in surfaces:
            dx, dy = bx - x, by - y
            L = hypot(dx, dy)
            tx, ty = dx / L, dy / L
            if all(
                abs((p[0] - x) * ty - (p[1] - y) * tx) < 0.32
                and -0.30 < (p[0] - x) * tx + (p[1] - y) * ty < L + 0.3
                for p in pts
            ):
                mesh.m[index] = C['Office A court tile']
                break
    north = Facade(-521.05, -606.47, 0, 1, z)
    # New 214-degree station resolves four adjacent bays and grill depth at street level.
    wing = Facade(-495.75, -606.49, 0, 1, z)
    m = Mesh()
    bays = ((0.84, 3.43), (4.72, 7.76), (8.74, 11.33), (12.34, 14.27))
    for lo, hi, sill, head in ((0.78, 3.65, 1.17, 3.29), (4.26, 7.82, 5.39, 7.49)):
        mesh = cut(mesh, wing, (0.28, 14.70, -0.30, 0.83, lo, hi))
        cursor = 0.28
        for a, b in bays:
            wing.box(m, C, cursor, a, -0.31, 0.10, lo, hi, 'rose')
            wing.box(m, C, a, b, -0.31, 0.10, lo, sill, 'rose')
            wing.box(m, C, a, b, -0.31, 0.10, head, hi, 'rose')
            opening(m, wing, C, a, b, sill, head, -0.29, 4, detail)
            if lo < 1:
                for j in range(1, 12 if detail else 6):
                    u = a + (b - a) * j / (12 if detail else 6)
                    wing.box(
                        m,
                        C,
                        u - 0.017,
                        u + 0.017,
                        -0.07,
                        -0.024,
                        sill + 0.03,
                        head - 0.04,
                        'iron',
                    )
                wing.box(m, C, a, b, -0.05, -0.015, sill + 0.75, sill + 0.79, 'iron')
            cursor = b
        wing.box(m, C, cursor, 14.70, -0.31, 0.10, lo, hi, 'rose')
    for u in (4.08, 8.24, 11.84):
        wing.box(m, C, u - 0.22, u + 0.22, 0.11, 0.37, 0.32, 8.00, 'stone')
    mesh.add_part('北翼成组深窗、壁柱与首层格栅', m)
    mesh = vestibule(mesh, north, C, -4.05, 4.16, 3.16, detail, False)
    east = Facade(-474.49, -647.65, 1, 0, z)
    mesh = vestibule(mesh, east, C, -3.66, 3.62, 3.18, detail, True)
    # Cut the ground floor out of the mapped diagonal instead of resting a canopy on a flat wall.
    p = (-475.35, -622.43)
    q = (-480.15, -616.61)
    dx, dy = q[0] - p[0], q[1] - p[1]
    span = hypot(dx, dy)
    f = Facade((p[0] + q[0]) / 2, (p[1] + q[1]) / 2, dy, -dx, z)
    a, b = -span / 2 - 0.48, span / 2 + 0.48
    mesh = cut(mesh, f, (a, b, -1.88, 1.35, 0.65, 5.29))
    m = Mesh()
    recess_shell(m, f, C, a, b, 1.78, 0.16, 0.70, 5.28, 'rose')
    # University bulletin 2024-10: upper lights independent of the stone door surround.
    opening(m, f, C, a + 0.18, b - 0.18, 3.18, 5.18, -1.78, 7, False)
    for l, r in ((a + 0.18, -2.28), (2.28, b - 0.18)):
        opening(m, f, C, l, r, 0.78, 3.19, -1.78, 2, False)
    f.box(m, C, -2.28, 2.28, -1.74, -1.40, 2.94, 3.23, 'A door surround')
    for u in (-2.17, 2.17):
        f.box(m, C, u - 0.11, u + 0.11, -1.74, -1.40, 0.75, 2.94, 'A door surround')
    f.box(m, C, -2.06, 2.06, -1.77, -1.71, 0.77, 2.94, 'A entry glass')
    for i in range(5):
        u = -2.06 + i * 1.03
        f.box(m, C, u - 0.014, u + 0.014, -1.71, -1.68, 0.77, 2.94, 'iron')
    if detail:
        for u in (-1.12, -0.93, 0.93, 1.12):
            f.box(m, C, u - 0.016, u + 0.016, -1.66, -1.62, 1.42, 2.04, 'frame')
            for h in (1.44, 2.02):
                f.box(
                    m,
                    C,
                    u - 0.017,
                    u + 0.017,
                    -1.70,
                    -1.62,
                    h - 0.018,
                    h + 0.018,
                    'frame',
                )
    for u in (-span / 2, span / 2):
        for center, radius, height, mat in [
            (0.81, 0.43, 0.23, 'stone'),
            (2.99, 0.34, 4.13, 'ceramic'),
            (5.14, 0.42, 0.23, 'stone'),
        ]:
            m.cylinder(
                *f.point(u, 0, center),
                radius,
                height,
                C['Office ' + mat],
                24 if detail else 12,
            )
    # Suspended upper wall over the columns, seen in the east panorama.
    # Embed its inner return into the existing upper wing, with no shared outer face.
    f.box(m, C, a - 0.24, b + 0.24, -1.9, 0.64, 5.99, 13.03, 'rose')
    for h, advance, thick, mat in [
        (6.10, 0.77, 0.14, 'base'),
        (7.93, 0.74, 0.13, 'pinkband'),
        (10.84, 0.74, 0.10, 'pinkband'),
        (13.06, 0.82, 0.20, 'stone'),
    ]:
        f.box(m, C, a - 0.29, b + 0.29, -0.14, advance, h, h + thick, mat)
    mesh.add_part('东北角架空门廊、悬挑上层与柱础', m)
    return mesh


def build(b, datum, C, detail, ordinary):
    mesh = civic_build(b, datum, C, detail, ordinary)
    for name, rgb, rough, metal in [
        ('A shade', (0.19, 0.158, 0.127), 0.91, 0),
        ('A deep door', (0.044, 0.034, 0.028), 0.66, 0.02),
        ('A gallery glass', (0.059, 0.067, 0.069), 0.39, 0.14),
        ('A sash', (0.17, 0.165, 0.148), 0.58, 0.13),
        ('A court tile', (0.70, 0.66, 0.62), 0.80, 0),
        ('A door surround', (0.47, 0.413, 0.348), 0.59, 0.12),
        ('A entry glass', (0.093, 0.124, 0.135), 0.29, 0.32),
    ]:
        finish(C, 'Office ' + name, rgb, rough, metal)
    return (president if b['id'] == MODEL_IDS[0] else junwu)(mesh, datum, C, detail)
