"""Public east stair of way/957404989, measured from GXHL project 887, photo 3.

Lower and upper tread sequences were independently counted in the 263° ground
panorama. The court, wall and road datums are model heights in campus metres.
"""

from math import dist

from entry_guardrails import glass_material
from geometry import Mesh, material
from physics_east_front import far_panel
from physics_street_grade import EAST, HALF_WIDTH, TOE

LOWER_RUN = 6.52
REST = 1.69
UPPER_RUN = 6.59
LOWER_STEPS, UPPER_STEPS = 18, 17
RISE = 5.135 / (LOWER_STEPS + UPPER_STEPS)
HEAD = TOE[2] + (LOWER_STEPS + UPPER_STEPS) * RISE
TURN_HEAD = HEAD + 1.515
TURN_FOOT_LINE = ((-643.25, -838.21), (-647.55, -837.75))
TURN_HEAD_LINE = ((-643.21, -842.14), (-647.51, -841.63))


def along_station(run):
    x, y, _ = TOE
    dx, dy = EAST
    return tuple(
        (x - run * dx - dy * v, y - run * dy + dx * v)
        for v in (-HALF_WIDTH, HALF_WIDTH)
    )


def east_stair_assembly(z, C, detail):
    mesh = Mesh()
    for key, rgb, rough, metal in (
        ('physicsGraniteTread', (0.138, 0.143, 0.144), 0.78, 0.03),
        ('physicsStoneRiser', (0.38, 0.38, 0.365), 0.83, 0.02),
        ('physicsStringer', (0.117, 0.108, 0.102), 0.83, 0.03),
        ('physicsEdgeStone', (0.40, 0.39, 0.367), 0.81, 0.02),
        ('physicsStairSteel', (0.215, 0.23, 0.228), 0.38, 0.58),
    ):
        if key not in C:
            C[key] = material(key, rgb, rough, metal)
    tread, riser, side, cap, steel = (
        C[k]
        for k in (
            'physicsGraniteTread',
            'physicsStoneRiser',
            'physicsStringer',
            'physicsEdgeStone',
            'physicsStairSteel',
        )
    )

    def mix(a, b, t):
        return tuple(x + (y - x) * t for x, y in zip(a, b))

    def top(points, mat, up=True):
        area = sum(
            a[0] * b[1] - a[1] * b[0] for a, b in zip(points, points[1:] + points[:1])
        )
        mesh.face(points if (area > 0) == up else points[::-1], mat)

    def slab(ring, h, thickness, mat, edge=side):
        pts = [(*p, h) for p in ring]
        if sum(a[0] * b[1] - a[1] * b[0] for a, b in zip(pts, pts[1:] + pts[:1])) < 0:
            pts.reverse()
        bottom = [(x, y, h - thickness) for x, y, h in pts]
        mesh.face(pts, mat)
        mesh.face(bottom[::-1], edge)
        for i, j in zip(range(len(pts)), list(range(1, len(pts))) + [0]):
            mesh.face([bottom[i], bottom[j], pts[j], pts[i]], edge)

    def guard(a, b, glazed=False):
        # At walking distance, the main flights have fine open horizontal steel
        # rails. Transparent glass belongs to the return and elevated terraces.
        h = 0.98
        spans = max(1, round(dist(a, b) / 1.83))
        if glazed:
            mesh.face(
                [
                    (*a[:2], a[2] + 0.15),
                    (*b[:2], b[2] + 0.15),
                    (*b[:2], b[2] + 0.89),
                    (*a[:2], a[2] + 0.89),
                ],
                glass_material(C),
            )
        if not detail:
            mesh.face(
                [a, b, (*b[:2], b[2] + h), (*a[:2], a[2] + h)],
                far_panel(C, 'physicsFarRail', 'physics-far-rail.png', True),
                [(0, 0), (spans, 0), (spans, 1), (0, 1)],
            )
            return
        for dh, radius in ((h, 0.036), (0.56, 0.022)) if not glazed else ((h, 0.036),):
            mesh.line((*a[:2], a[2] + dh), (*b[:2], b[2] + dh), radius, steel, 6)
        for i in range(spans + 1):
            x, y, h0 = mix(a, b, i / spans)
            mesh.box(x, y, h0 + h / 2, 0.055, 0.055, h, steel)

    def beam(lo, hi, out, up=0.165):
        # Narrow light coping on top of a deeper, dark tiled stringer.
        dx, dy = out
        ring = [
            lo,
            hi,
            (hi[0] + dx, hi[1] + dy, hi[2]),
            (lo[0] + dx, lo[1] + dy, lo[2]),
        ]
        a = [(x, y, h + up) for x, y, h in ring]
        b = [(x, y, h - 0.41) for x, y, h in ring]
        top(a, cap)
        top(b, side, False)
        if sum(i[0] * j[1] - i[1] * j[0] for i, j in zip(a, a[1:] + a[:1])) < 0:
            a.reverse()
            b.reverse()
        for k in range(4):
            n = (k + 1) % 4
            mesh.face([b[k], b[n], a[n], a[k]], side)

    def flight(lo, hi, lower, upper, n, glazed=False, rails=True):
        # Explicit treads, vertical risers and enclosed sides over one inclined
        # soffit. End faces follow the two measured lines even on the oblique return.
        depth = 0.31
        for i in range(n):
            t, u = i / n, (i + 1) / n
            a, b = [mix(p, q, t) for p, q in zip(lo, hi)]
            d, c = [mix(p, q, u) for p, q in zip(lo, hi)]
            h = lower + (upper - lower) * t
            h1 = lower + (upper - lower) * u
            # The granite nosing projects 22 mm in front of the lighter riser.
            # Its 34 mm exposed vertical edge remains visible from below.
            da = dist(a, d)
            db = dist(b, c)
            an = mix(a, d, -0.022 / da) if detail and i else a
            bn = mix(b, c, -0.022 / db) if detail and i else b
            top([(*an, h1), (*bn, h1), (*c, h1), (*d, h1)], tread)
            direction = (hi[0][0] - lo[0][0], hi[0][1] - lo[0][1])
            winding = (b[1] - a[1]) * direction[0] - (b[0] - a[0]) * direction[1]

            def front_band(front):
                return front if winding < 0 else front[::-1]

            if detail:
                mesh.face(
                    front_band([(*a, h), (*b, h), (*b, h1 - 0.034), (*a, h1 - 0.034)]),
                    riser,
                )
                mesh.face(
                    front_band(
                        [(*an, h1 - 0.034), (*bn, h1 - 0.034), (*bn, h1), (*an, h1)]
                    ),
                    tread,
                )
                if i:
                    top(
                        [
                            (*an, h1 - 0.034),
                            (*bn, h1 - 0.034),
                            (*b, h1 - 0.034),
                            (*a, h1 - 0.034),
                        ],
                        side,
                        False,
                    )
            else:
                mesh.face(
                    front_band([(*a, h), (*b, h), (*b, h1), (*a, h1)]),
                    far_panel(C, 'physicsFarRiser', 'physics-far-riser.png'),
                    [(0, 0), (1, 0), (1, 1), (0, 1)]
                    if winding < 0
                    else [(0, 1), (1, 1), (1, 0), (0, 0)],
                )
            # The closed continuous stringer completely conceals the sides of
            # the individual treads. Its outer face and the sloped soffit remain.
        top(
            [
                (*lo[0], lower - depth),
                (*lo[1], lower - depth),
                (*hi[1], upper - depth),
                (*hi[0], upper - depth),
            ],
            side,
            False,
        )
        for edge, level in ((lo, lower), (hi, upper)):
            a, b = edge
            mesh.face(
                [(*a, level - depth), (*b, level - depth), (*b, level), (*a, level)],
                side,
            )
        if rails:
            across = dist(lo[0], lo[1])
            for i, sgn in ((0, -1), (1, 1)):
                v = tuple((b - a) / across * sgn * 0.17 for a, b in zip(lo[0], lo[1]))
                a, b = (*lo[i], lower), (*hi[i], upper)
                beam(a, b, v)
                guard(
                    (a[0] + v[0] / 2, a[1] + v[1] / 2, lower + 0.135),
                    (b[0] + v[0] / 2, b[1] + v[1] / 2, upper + 0.135),
                    glazed,
                )

    def post(x, y, bottom, upper, width=0.40):
        mesh.box(x, y, (upper + bottom) / 2, width, width, upper - bottom, side)

    toe = along_station(0)
    low_end = along_station(LOWER_RUN)
    high_start = along_station(LOWER_RUN + REST)
    mouth = along_station(LOWER_RUN + REST + UPPER_RUN)
    rest = TOE[2] + LOWER_STEPS * RISE
    flight(toe, low_end, TOE[2], rest, LOWER_STEPS)
    slab([*low_end, high_start[1], high_start[0]], rest, 0.41, tread)
    for i, sgn in ((0, -1), (1, 1)):
        v = (-EAST[1] * sgn * 0.17, EAST[0] * sgn * 0.17)
        a, b = low_end[i], high_start[i]
        beam((*a, rest), (*b, rest), v)
        guard(
            (a[0] + v[0] / 2, a[1] + v[1] / 2, rest + 0.135),
            (b[0] + v[0] / 2, b[1] + v[1] / 2, rest + 0.135),
        )
        x, y = mix(a, b, 0.50)
        post(
            x + EAST[1] * sgn * 0.32, y - EAST[0] * sgn * 0.32, 5.75, rest - 0.41, 0.48
        )
    flight(high_start, mouth, rest, HEAD, UPPER_STEPS)
    # The top terrace turns south to the white frame. The planted edge limits
    # the observed deck westward; leave the photographed space beneath open.
    outer = (-649.32, -828.80)
    west = (-649.19, -835.31)
    slab(
        [mouth[0], mouth[1], outer, west, TURN_FOOT_LINE[1], TURN_FOOT_LINE[0]],
        HEAD,
        0.43,
        tread,
    )
    guard((*mouth[1], HEAD), (*outer, HEAD), True)
    guard((*mouth[0], HEAD), (*TURN_FOOT_LINE[0], HEAD), True)
    for x, y in (
        (-643.1, -829.6),
        (-648.55, -829.65),
        (-643.3, -835.7),
        (-646.85, -837.05),
    ):
        post(x, y, 6.16, HEAD - 0.43, 0.46)
    flight(TURN_FOOT_LINE, TURN_HEAD_LINE, HEAD, TURN_HEAD, 11, glazed=True)

    # The upper landing wraps the actual white frame columns. Its south end
    # meets the occupied wing, leaving the courtyard and the high bridge open.
    e, w = TURN_HEAD_LINE
    east_x = -636.50
    end_y = -850.11
    upper = [(east_x, end_y), (east_x, e[1]), e, w, (w[0], end_y)]
    slab(upper, TURN_HEAD, 0.44, C['gateStone'], C['libraryTrim'])
    guard((east_x, e[1], TURN_HEAD), (*e, TURN_HEAD), True)
    guard((east_x, end_y, TURN_HEAD), (east_x, e[1], TURN_HEAD), True)
    for x, y in ((-637.31, -849.35), (-643.20, -848.92), (-647.0, -846.3)):
        post(x, y, 6.50, TURN_HEAD - 0.44, 0.43)

    # The five visible risers behind the return belong to a separate small
    # landing. The upper landing's outline is resolved in GXHL photo 3;
    # the obscured route farther into the building is not established.
    rear_low = ((-651.35, -843.04), (-650.45, -840.43))
    rear_high = ((-652.45, -842.79), (-651.96, -840.64))
    rear_top = HEAD + 0.765
    flight(rear_low, rear_high, HEAD, rear_top, 5, glazed=True)
    small_s = (-654.14, -845.10)
    small_n = (-654.53, -841.03)
    slab([*rear_high, small_n, small_s], rear_top, 0.28, tread)
    guard((*rear_high[0], rear_top), (*small_s, rear_top), True)
    guard((*small_s, rear_top), (*small_n, rear_top), True)
    guard((*small_n, rear_top), (*rear_high[1], rear_top), True)
    # A short threshold under the shadow of the planter; its hidden
    # continuation is left unmodeled. Keep the playing surface at its datum.
    sill = [*rear_low, (-649.57, -839.78), (-650.31, -842.83)]
    slab(sill, HEAD, 0.30, tread)
    for x, y in ((-653.64, -842.5), (-652.53, -841.8)):
        post(x, y, 7.80, rear_top - 0.28, 0.26)
    guard((*west, HEAD), (*outer, HEAD), True)
    planter = [
        (-647.55, -837.75),
        (-649.19, -835.31),
        (-651.2, -835.88),
        (-651.72, -837.6),
    ]
    slab(planter, HEAD + 0.26, 0.52, C['gateStone'])
    center = tuple(sum(q[i] for q in planter) / len(planter) for i in (0, 1))
    ring = [mix(q, center, 0.12) for q in planter]
    top([(*q, HEAD + 0.28) for q in ring], C['grass'])
    return mesh
