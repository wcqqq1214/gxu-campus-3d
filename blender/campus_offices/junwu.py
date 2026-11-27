"""Jun Wu Hall entrance. Campus metres, including both LODs and the complete unedited wings."""

from math import hypot
from pathlib import Path

import bpy

from geometry import MATERIALS, Mesh
from humanities_facades import finish

HERE = Path(__file__).resolve().parent
from .entrances import build as build_entrance
from .facade_solids import Facade, cut

# Axes of the three surveyed glazing planes. The east return is aligned with the east wing.
E = (-477.42, -624.52)
K = (-477.47, -619.28)
R = (-483.56, -613.94)
W = (-487.60, -613.94)
C1 = (-477.09, -618.48)
C2 = (-482.90, -612.84)
FLOOR = 0.745


def frame(a, b, z):
    dx, dy = b[0] - a[0], b[1] - a[1]
    return Facade(*a, dy, -dx, z), hypot(dx, dy)


def cross(f, u, n):
    return f.point(u, n, 0)[:2]


def prism(m, poly, bottom, top, z, mat):
    """Closed extruded polygon with optional nonhorizontal top, in counterclockwise order."""
    hs = [top] * len(poly) if isinstance(top, (float, int)) else list(top)
    area = sum(p[0] * q[1] - p[1] * q[0] for p, q in zip(poly, poly[1:] + poly[:1]))
    if area < 0:
        poly = list(reversed(poly))
        hs.reverse()
    lo = [(*p, z + bottom) for p in poly]
    hi = [(*p, z + h) for p, h in zip(poly, hs)]
    m.face(lo[::-1], mat)
    m.face(hi, mat)
    for i in range(len(poly)):
        j = (i + 1) % len(poly)
        m.face((lo[i], lo[j], hi[j], hi[i]), mat)


def pane(m, f, C, l, r, b, t, v, kind='JW glass'):
    # One optical interface per pane. The separately modelled sash supplies its perimeter depth.
    m.face(
        [f.point(l, v, b), f.point(r, v, b), f.point(r, v, t), f.point(l, v, t)],
        C['Office ' + kind],
    )


def glazing(m, f, L, C, door=False, lights=4, detail=True):
    base = 0.84
    top = 7.03
    mid = 2.95 if not door else 3.47
    upper = 5.00
    bars = [i * L / lights for i in range(lights + 1)]
    a, b = 1.82, 7.12
    for left, right in zip(bars, bars[1:]):
        for h0, h1 in [(mid, upper), (upper, top)]:
            pane(m, f, C, left, right, h0, h1, -0.085)
    # Trim lower sidelight panes to meet the outside of the portal frame.
    lower = [(0, a), (b, L)] if door else [(0, L)]
    for l, r in lower:
        for x0, x1 in zip(bars, bars[1:]):
            x0 = max(l, x0)
            x1 = min(r, x1)
            if x1 > x0:
                pane(m, f, C, x0, x1, base, mid, -0.085)
    for x in bars:
        lo = mid if door and a + 0.001 < x < b - 0.001 else base
        f.box(m, C, x - 0.031, x + 0.031, -0.115, 0.018, lo, top, 'JW silver')
    for h in (base, mid, upper, top):
        spans = lower if door and h in (base, mid) else [(0, L)]
        for l, r in spans:
            f.box(m, C, l, r, -0.115, 0.021, h - 0.029, h + 0.029, 'JW silver')
    if not door:
        return
    jamb = 0.23
    head = 0.35
    for l, r in ((a, a + jamb), (b - jamb, b)):
        f.box(m, C, l, r, -0.27, 0.025, FLOOR, mid, 'JW portal')
    f.box(m, C, a + jamb, b - jamb, -0.27, 0.025, mid - head, mid, 'JW portal')
    lo, hi = a + jamb, b - jamb
    w = (hi - lo) / 4
    for i in range(4):
        x = lo + i * w
        pane(
            m,
            f,
            C,
            x + 0.008,
            x + w - 0.008,
            FLOOR + 0.022,
            mid - head - 0.02,
            -0.22,
            'JW door glass',
        )
        if detail:
            f.box(
                m,
                C,
                x,
                x + 0.016,
                -0.24,
                -0.209,
                FLOOR + 0.025,
                mid - head - 0.02,
                'JW silver',
            )
            p = x + w * (0.85 if i % 2 == 0 else 0.15)
            for h in (1.54, 2.33):
                f.box(
                    m,
                    C,
                    p - 0.017,
                    p + 0.017,
                    -0.22,
                    -0.098,
                    h - 0.02,
                    h + 0.02,
                    'JW silver',
                )
            f.box(m, C, p - 0.018, p + 0.018, -0.13, -0.093, 1.53, 2.345, 'JW silver')


def build(b, datum, C, detail, ordinary):
    mesh = build_entrance(b, datum, C, detail, ordinary)
    for name, rgb, rough, metal, alpha in [
        ('JW column', (0.44, 0.378, 0.347), 0.45, 0.05, 1),
        ('JW base stone', (0.324, 0.268, 0.236), 0.48, 0.07, 1),
        ('JW plinth', (0.16, 0.149, 0.14), 0.78, 0, 1),
        ('JW tile', (0.55, 0.46, 0.38), 0.8, 0, 1),
        ('JW paving', (0.445, 0.398, 0.355), 0.76, 0, 1),
        ('JW tread', (0.365, 0.309, 0.261), 0.69, 0.02, 1),
        ('JW nosing', (0.48, 0.422, 0.367), 0.60, 0.02, 1),
        ('JW silver', (0.62, 0.646, 0.642), 0.35, 0.53, 1),
        ('JW shadow', (0.235, 0.194, 0.168), 0.84, 0, 1),
        ('JW soffit', (0.53, 0.495, 0.457), 0.85, 0, 1),
        ('JW portal', (0.47, 0.421, 0.369), 0.5, 0.12, 1),
        ('JW glass', (0.115, 0.178, 0.188), 0.24, 0.24, 0.67),
        ('JW door glass', (0.095, 0.141, 0.145), 0.20, 0.22, 0.52),
    ]:
        key = 'Office ' + name
        idx = finish(C, key, rgb, rough, metal)
        if alpha < 1:
            mat = MATERIALS[idx]
            mat.diffuse_color = (*rgb, alpha)
            mat.node_tree.nodes.get('Principled BSDF').inputs[
                'Alpha'
            ].default_value = alpha
            mat.surface_render_method = 'DITHERED'
    for name, filename in [
        ('JW tile', 'portico-tile.png'),
        ('JW plinth', 'portico-plinth.png'),
    ]:
        mat = MATERIALS[C['Office ' + name]]
        if not any(n.type == 'TEX_IMAGE' for n in mat.node_tree.nodes):
            tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
            tex.image = bpy.data.images.load(str(HERE / filename), check_existing=True)
            tex.image.pack()
            mat.node_tree.links.new(
                tex.outputs['Color'],
                mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'],
            )
    # Sweeps the complete old stage, double column sets, canopy, angled infill, old layered
    # east glass, roof parts and all intersecting ordinary walls in this one corner.
    east = Facade(-487.60, -625.55, 1, 0, datum)
    mesh = cut(mesh, east, (0, 35, 0, 44, -5.0, 21.0))
    # The obsolete raised pink surround reaches y=-627.94. The neighbouring historic
    # measured panel at y=-639.17 remains outside both replacement prisms.
    pier_cut = Facade(-477.60, -628.52, 1, 0, datum)
    mesh = cut(mesh, pier_cut, (0, 4.13, 0, 9, -5, 21))
    Cmat = lambda n: C['Office ' + n]
    z = datum
    front, L = frame(K, R, z)
    side, side_len = frame(E, K, z)
    ret, ret_len = frame(R, W, z)
    inner = (-487.60, -625.55)
    S = (-476.48, -625.55)
    B = (-487.60, -610.05)
    body = Mesh()
    for points in (
        [inner, S, (-476.48, E[1]), E],
        [W, (-487.60, -610.05), (-487.48, -610.17), (-487.48, -613.94)],
    ):
        prism(body, points, -1.1, 0.97, z, Cmat('JW base stone'))
        prism(body, points, 0.97, 7.23, z, Cmat('JW tile'))
    # Two solid tiled cheeks around the narrow vertical recess; the spandrels and panes
    # are physically behind the outer tile and flush stone dado. They join the existing wing.
    pier = Facade(-472.10, -628.52, 1, 0, z)
    for u0, u1 in ((0, 1.78), (2.66, 4.09)):
        pier.box(body, C, u0, u1, -5.50, 0, -1.10, 1.49, 'JW plinth')
        pier.box(body, C, u0, u1, -5.50, 0, 1.49, 13.92, 'JW tile')
        pier.box(body, C, u0, u1, -5.50, 0.025, 13.92, 14.0, 'JW portal')
    pier.box(body, C, 1.78, 2.66, -5.50, 0, -1.10, 1.49, 'JW plinth')
    for lo, hi, mat in (
        (1.49, 1.92, 'JW glass'),
        (1.92, 2.28, 'JW soffit'),
        (2.28, 3.27, 'JW glass'),
        (3.27, 3.62, 'JW soffit'),
        (3.62, 4.86, 'JW glass'),
        (4.86, 5.4, 'JW soffit'),
        (5.4, 6.90, 'JW glass'),
        (6.90, 7.47, 'JW soffit'),
        (7.47, 9.41, 'JW glass'),
        (9.41, 10.05, 'JW soffit'),
        (10.05, 12.25, 'JW glass'),
        (12.25, 13.92, 'JW tile'),
    ):
        pier.box(body, C, 1.78, 2.66, -0.52, -0.43, lo, hi, mat)
        if mat == 'JW glass':
            for a0 in (1.81, 2.63):
                pier.box(
                    body, C, a0 - 0.015, a0 + 0.015, -0.43, -0.38, lo, hi, 'JW silver'
                )
            pier.box(body, C, 1.79, 2.65, -0.43, -0.375, lo, lo + 0.028, 'JW silver')
    pier.box(body, C, 1.78, 2.66, -5.5, 0, 13.92, 14.0, 'JW portal')
    pier.box(body, C, 1.78, 2.66, -1.00, -0.94, 1.49, 13.92, 'JW shadow')
    # Backing walls sit inside the recess, leaving a real void behind each change of plane.
    for a, bp in [
        ((-480.15, -625.55), (-480.15, -621.0)),
        ((-480.15, -621.0), (-484.62, -617.02)),
        ((-484.62, -617.02), (-487.6, -617.02)),
    ]:
        f, ln = frame(a, bp, z)
        f.box(body, C, 0, ln, -0.13, 0, FLOOR, 7.25, 'JW shadow')

    # The original corner contacts the surrounding footprint at S and B on both cut planes.
    # Vary the projection at the two mitres; all three faces of each band share vertices.
    def outline(proj):
        return [
            inner,
            S,
            (S[0] + 0.14 * proj, S[1]),
            (-476.50 + 1.08 * proj, -620.38 + 2.26 * proj),
            (-485.74 + 0.32 * proj, -611.77 + 0.65 * proj),
            B,
        ]

    def slab(lo, hi, advance, mat):
        ps = outline(advance)
        if advance == 0:
            ps.pop(2)
        prism(body, ps, lo, hi, z, Cmat(mat))

    slab(7.19, 7.43, 1.05, 'JW soffit')
    slab(7.43, 7.54, 1.15, 'JW silver')
    slab(7.54, 7.65, 1.02, 'JW shadow')
    slab(7.65, 7.83, 1.095, 'JW base stone')
    slab(7.83, 8.03, 1.01, 'JW portal')
    slab(8.03, 13.16, 0.81, 'JW tile')
    for low, high, advance in [
        (9.16, 9.23, 0.88),
        (11.44, 11.52, 0.88),
        (13.16, 13.29, 0.95),
    ]:
        slab(low, high, advance, 'JW base stone')
    slab(13.29, 13.92, 0.77, 'JW tile')
    slab(13.92, 14.0, 0.86, 'JW portal')
    mesh.add_part('东北三折挑檐与连续侧墙', body)
    glazing_mesh = Mesh()
    glazing(glazing_mesh, side, side_len, C, lights=4, detail=detail)
    glazing(glazing_mesh, front, L, C, door=True, lights=7, detail=detail)
    glazing(glazing_mesh, ret, ret_len, C, lights=3, detail=detail)
    # Ceiling reveal behind the curtain wall and plinth below the glazing.
    for f, ln in ((side, side_len), (front, L), (ret, ret_len)):
        f.box(glazing_mesh, C, 0.035, ln - 0.035, -0.86, 0.0, 7.03, 7.20, 'JW soffit')
        f.box(
            glazing_mesh,
            C,
            0.035,
            ln - 0.035,
            -0.30,
            0.012,
            FLOOR - 0.02,
            0.842,
            'JW base stone',
        )
    mesh.add_part('三折幕墙、退进玻璃门及银色分格', glazing_mesh)
    columns = Mesh()
    for x, y in (C1, C2):
        # One shaft per position; a flared stone foot and a compact stepped capital.
        for lo, hi, r0, r1, mat in [
            (FLOOR, 0.95, 0.51, 0.51, 'JW base stone'),
            (0.95, 1.04, 0.51, 0.485, 'JW base stone'),
            (1.04, 1.085, 0.49, 0.475, 'JW portal'),
            (1.085, 1.15, 0.465, 0.428, 'JW column'),
            (1.15, 6.97, 0.428, 0.418, 'JW column'),
            (6.97, 7.04, 0.428, 0.46, 'JW column'),
            (7.04, 7.12, 0.46, 0.505, 'JW base stone'),
            (7.12, 7.19, 0.505, 0.505, 'JW column'),
        ]:
            columns.cylinder(
                x,
                y,
                z + (lo + hi) / 2,
                r0,
                hi - lo,
                Cmat(mat),
                36 if detail else 16,
                topr=r1,
            )
    mesh.add_part('两根独立圆柱及环形柱础柱头', columns)
    walk = Mesh()

    def block(poly, hi, mat):
        prism(walk, poly, -0.025, hi, z, Cmat(mat))

    # Deck behind both columns, wrapped around the glazing. The side approach and ramp
    # share only their boundary; the main stair descends perpendicular to the front door.
    end = L + 0.92
    block([inner, E, K, R, W], FLOOR, 'JW paving')
    # The east ramp rises approximately tangentially to the diagonal wall. Its width is
    # defined by the two visible lower corners in 259 degrees; the front stair meets its side.
    A = (-472.10, -624.43)
    T = (-475.65, -618.46)
    F = (-468.65, -622.05)
    H = (-472.85, -616.0)
    G = (-466.05, -619.15)
    edge0 = H
    edge1 = cross(front, end, 4.68)
    block([E, A, T, H, edge1, cross(front, end, 0.28), W, R, K], FLOOR, 'JW paving')
    block([F, T, H, G], [0.032, FLOOR, FLOOR, 0.032], 'JW paving')
    direction = (front.nx, front.ny)

    def outward(pt, d):
        return (pt[0] + direction[0] * d, pt[1] + direction[1] * d)

    for i in range(4):
        d = i * 0.43
        h = FLOOR * (4 - i) / 4
        block(
            [
                outward(edge0, d),
                outward(edge1, d),
                outward(edge1, d + 0.43),
                outward(edge0, d + 0.43),
            ],
            h,
            'JW tread',
        )
        block(
            [
                outward(edge0, d + 0.387),
                outward(edge1, d + 0.387),
                outward(edge1, d + 0.435),
                outward(edge0, d + 0.435),
            ],
            h + 0.009,
            'JW nosing',
        )
    # Five distinct side risers between the ramp kerb and the toe of the tiled return.
    P = (-470.93, -624.41)

    def lerp(a, b, t):
        return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))

    for i in range(5):
        t0 = i / 5
        t1 = (i + 1) / 5
        pts = [lerp(A, P, t0), lerp(T, F, t0), lerp(T, F, t1), lerp(A, P, t1)]
        block(pts, FLOOR * (5 - i) / 5, 'JW tread')
    perp = (-0.067, -0.13)
    off = lambda p: (p[0] + perp[0], p[1] + perp[1])
    block(
        [off(F), off(T), T, F], [0.16, FLOOR + 0.105, FLOOR + 0.105, 0.16], 'JW nosing'
    )
    mesh.add_part('包角台阶、平台与斜坡', walk)
    return mesh
