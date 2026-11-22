"""Measured east name wall, its court-facing galleries and north street access.

Only way/957404989 calls this, after its upper-storey calibration. Site and
photographic control points are in campus XYZ, in metres.
"""

from math import ceil, dist, hypot

from entry_guardrails import glass_material
from geometry import Mesh, material
from physics_right_wall import (
    BOTTOM,
    FRAME_WEST,
    FRONT,
    LID,
    NORTH,
    SOUTH,
    TOP,
    right_wall,
)


def subtract(mesh, bounds):
    """Clip facade polygons against a local box, carrying per-corner UVs."""
    faces, materials, uvs = mesh.f, mesh.m, mesh.face_uvs
    mesh.f, mesh.m, mesh.face_uvs = [], [], {}
    for i, indices in enumerate(faces):
        points = [mesh.v[k] for k in indices]
        if any(
            max((p[axis] - edge) * sign for p in points) <= 0.00001
            for axis, edge, sign in bounds
        ):
            if i in uvs:
                mesh.face_uvs[len(mesh.f)] = uvs[i]
            mesh.f.append(indices)
            mesh.m.append(materials[i])
            continue
        if i in uvs:
            points = [(*p, *uv) for p, uv in zip(points, uvs[i])]
        for axis, edge, sign in bounds:
            if min((p[axis] - edge) * sign for p in points) >= -1.0e-8:
                continue
            inside, outside = [], []
            for a, b in zip(points, points[1:] + points[:1]):
                da, db = (a[axis] - edge) * sign, (b[axis] - edge) * sign
                if da >= 0:
                    inside.append(a)
                if da <= 0:
                    outside.append(a)
                if da * db < 0:
                    t = da / (da - db)
                    q = tuple(x + t * (y - x) for x, y in zip(a, b))
                    outside.append(q)
                    inside.append(q)
            if len(outside) >= 3:
                mesh.face(
                    [p[:3] for p in outside],
                    materials[i],
                    [p[3:] for p in outside] if i in uvs else None,
                )
            points = inside
            if len(points) < 3:
                break


def finish_corner(body, z, C, detail):
    base, head, lid = (z + h for h in (BOTTOM, TOP, LID))
    west = FRONT - 14.47
    # Remove the previous solid cheek and lower part of the cantilever only
    # within the north end bay. The street-facing upper roof and dome stay put.
    subtract(
        body,
        [
            (0, west - 0.01, 1),
            (1, SOUTH - 7.74, 1),
            (1, NORTH + 0.08, -1),
            (2, base - 0.02, 1),
            (2, lid + 0.01, -1),
        ],
    )
    subtract(
        body,
        [
            (0, FRAME_WEST, 1),
            (1, NORTH - 3.43, 1),
            (2, base - 0.02, 1),
            (2, lid + 0.01, -1),
        ],
    )
    subtract(
        body,
        [
            (0, FRONT - 14.47, 1),
            (1, -845.22, 1),
            (1, SOUTH - 7.73, -1),
            (2, z + 15.46, 1),
            (2, lid + 0.01, -1),
        ],
    )
    # Remove the original shopfront and masonry behind the separate small
    # stair and its upper screen. Leave a solid room behind the threshold.
    subtract(
        body,
        [
            (0, FRONT - 5.98, 1),
            (1, SOUTH - 2.10, 1),
            (1, SOUTH + 0.01, -1),
            (2, z - 1.65, 1),
            (2, base + 0.02, -1),
        ],
    )
    subtract(
        body,
        [
            (0, west, 1),
            (1, SOUTH - 7.74, 1),
            (1, SOUTH - 0.04, -1),
            (2, z - 1.8, 1),
            (2, base + 0.03, -1),
        ],
    )
    # Remove only the previous east transverse bridge and its fixed guards.
    # The stair landing and the stair footbridge below this cut stay intact.
    subtract(
        body,
        [
            (0, west, 1),
            (1, -845.23, 1),
            (1, SOUTH - 7.70, -1),
            (2, 20.08, 1),
            (2, 21.72, -1),
        ],
    )
    # Oblique 15244: the old north opening post was directly in front of
    # the three gallery openings. Remove its front and rear members together.
    subtract(
        body,
        [
            (0, west - 0.02, 1),
            (1, -830.94, 1),
            (1, -828.65, -1),
            (2, 6.25, 1),
            (2, lid + 0.04, -1),
        ],
    )
    bx = FRONT - 7.76
    subtract(
        body,
        [
            (0, bx - 1.32, 1),
            (0, bx + 1.32, -1),
            (1, -848.10, 1),
            (1, -845.19, -1),
            (2, head - 0.36, 1),
            (2, lid + 0.01, -1),
        ],
    )
    # The old north wall at grade would occlude the recessed entrance glazing.
    subtract(
        body,
        [
            (0, FRAME_WEST + 0.4, 1),
            (0, FRONT - 0.5, -1),
            (1, NORTH - 1.64, 1),
            (2, z - 1.80, 1),
            (2, base + 0.01, -1),
        ],
    )
    part = Mesh()
    right_wall(part, z, C, detail)

    def box(x0, x1, y0, y1, h0, h1, mat):
        assert x1 > x0 and y1 > y0 and h1 > h0
        part.box(
            (x0 + x1) / 2,
            (y0 + y1) / 2,
            (h0 + h1) / 2,
            x1 - x0,
            y1 - y0,
            h1 - h0,
            C[mat],
        )

    def face(points, mat):
        part.face(points, C[mat])

    def south(x0, x1, y, h0, h1, mat):
        face([(x0, y, h0), (x1, y, h0), (x1, y, h1), (x0, y, h1)], mat)

    def rail(a, b, mat='lampMetal', radius=0.035):
        part.line(a, b, radius, C[mat], 4)

    def guard(a, b, height=0.99):
        ax, ay, az = a
        bx, by, bz = b
        if not detail:
            from physics_east_front import far_panel

            repeats = max(1, round(hypot(bx - ax, by - ay) / 1.65))
            mat = far_panel(C, 'physicsFarRail', 'physics-far-rail.png', True)
            part.face(
                [a, b, (bx, by, bz + height), (ax, ay, az + height)],
                mat,
                [(0, 0), (repeats, 0), (repeats, 1), (0, 1)],
            )
            return
        rail((ax, ay, az + height), (bx, by, bz + height))
        if detail:
            rail((ax, ay, az + 0.45), (bx, by, bz + 0.45), radius=0.019)
        spans = max(1, ceil(dist(a, b) / (1.65 if detail else 3.3)))
        for i in range(spans + 1):
            t = i / spans
            x, y, h = ax + (bx - ax) * t, ay + (by - ay) * t, az + (bz - az) * t
            box(x - 0.025, x + 0.025, y - 0.025, y + 0.025, h, h + height, 'lampMetal')

    def slab(points, thickness, mat):
        # Convex planar deck, in counterclockwise order as seen from above.
        if (
            sum(
                a[0] * b[1] - a[1] * b[0]
                for a, b in zip(points, points[1:] + points[:1])
            )
            < 0
        ):
            points = points[::-1]
        bottom = [(x, y, h - thickness) for x, y, h in points]
        face(bottom[::-1], mat)
        face(points, mat)
        for i, j in zip(range(len(points)), list(range(1, len(points))) + [0]):
            face([bottom[i], bottom[j], points[j], points[i]], mat)

    # The terminal side is separate from the narrow east slit. Three open
    # decks share its two division elevations. Photo 15244 fixes their length
    # and the rear window line independently of the street station.
    left, right = FRONT - 9.88, FRONT - 1.61
    rear = SOUTH + 2.83
    box(west, left, SOUTH, rear, base, head, 'libraryTrim')
    box(right, FRONT, SOUTH, SOUTH + 0.37, base, head, 'libraryTrim')
    levels = [base, base + 4.327, base + 8.865, base + 13.355]
    glass = glass_material(C)
    for lo, hi in zip(levels, levels[1:]):
        box(left, right, SOUTH, rear, lo, lo + 0.34, 'physicsPier')
        box(left, right, SOUTH - 0.04, SOUTH + 0.09, lo, lo + 0.085, 'gateStone')
        south(left, right, rear, lo + 0.34, hi, 'libraryTrim')
        south(
            left + 0.23,
            right - 0.23,
            rear - 0.025,
            lo + 0.48,
            hi - 0.46,
            'physicsWindow',
        )
        for j in range(1, 5):
            x = left + j * (right - left) / 5
            south(x - 0.035, x + 0.035, rear - 0.049, lo + 0.48, hi - 0.46, 'fenceIron')
        y = SOUTH + 0.13
        part.face(
            [
                (left, y, lo + 0.34),
                (right, y, lo + 0.34),
                (right, y, lo + 1.30),
                (left, y, lo + 1.30),
            ],
            glass,
        )
        guard((left + 0.03, y, lo + 0.34), (right - 0.03, y, lo + 0.34))
    box(left, right, SOUTH, rear, levels[-1], head, 'libraryTrim')
    box(right, FRONT, SOUTH + 0.37, rear, head - 0.44, head, 'libraryTrim')
    box(FRONT - 0.31, FRONT, SOUTH + 0.37, SOUTH + 0.92, base, head, 'libraryTrim')

    # Close the raised bay with a real underside and a return into the
    # retained upper mass at the preceding beam line (the rest of the roof is fixed).
    south_end = -845.22
    box(west, FRONT + 0.58, south_end, NORTH + 0.46, lid, lid + 0.28, 'libraryTrim')
    box(FRAME_WEST, west, NORTH - 3.43, NORTH + 0.46, lid, lid + 0.28, 'libraryTrim')
    box(FRAME_WEST, west, NORTH - 3.46, NORTH - 3.43, head, lid, 'physicsWindow')
    box(west - 0.10, west, south_end, SOUTH, 23.57, lid, 'huicuiFrame')
    for a, b in ((west, bx - 1.33), (bx + 1.33, FRONT + 0.58)):
        box(a, b, south_end - 0.12, south_end, 23.57, lid, 'libraryTrim')
    # Two independent supports. The stair turn is south of this column line.
    for x in (FRONT - 0.43, FRONT - 0.43 - 10.27):
        box(x - 0.43, x + 0.43, SOUTH - 20.79, SOUTH - 19.93, 5.80, lid, 'gateStone')
    box(bx - 1.32, bx + 1.32, -848.1, south_end, head - 0.35, head, 'bridgeConcrete')
    box(bx - 1.34, bx + 1.34, -848.14, -848.10, head, lid, 'physicsWindow')
    for i in range(6):
        y = SOUTH - i * (19.93 / 5)
        box(west, FRONT + 0.58, y - 0.15, y + 0.15, lid - 0.43, lid, 'gateStone')
    for x in (west + 3.10, west + 6.90, west + 10.70, FRONT + 0.30):
        box(x - 0.14, x + 0.14, south_end, SOUTH, lid - 0.45, lid - 0.02, 'gateStone')
    # 15244 puts the transverse bridge above the third loggia. Its north
    # landing is continuous with the roof of that loggia, clear of its rails.
    bridge = head
    bx = FRONT - 7.76
    sy = -845.20
    box(bx - 1.20, bx + 1.20, sy, SOUTH, bridge - 0.35, bridge, 'physicsPier')
    for x in (bx - 1.20, bx + 1.20):
        box(x - 0.075, x + 0.075, sy, SOUTH, base + 13.75, bridge - 0.35, 'huicuiFrame')
        part.face(
            [
                (x, sy, bridge),
                (x, SOUTH, bridge),
                (x, SOUTH, bridge + 1.0),
                (x, sy, bridge + 1.0),
            ],
            glass,
        )
        guard((x, sy, bridge), (x, SOUTH, bridge))
    box(bx - 1.23, bx + 1.23, sy - 1.48, sy, bridge - 0.35, bridge, 'bridgeConcrete')
    # A framed glazed bay recedes behind the bend beside the court.
    for k in range(3):
        lo = levels[k]
        hi = levels[k + 1]
        box(west - 0.12, west, SOUTH - 7.69, SOUTH, lo, hi, 'physicsPier')
        box(
            west,
            west + 0.04,
            SOUTH - 7.40,
            SOUTH - 0.31,
            lo + 0.44,
            hi - 0.32,
            'physicsWindow',
        )
        for yy in (SOUTH - 5.5, SOUTH - 3.75, SOUTH - 2):
            box(
                west + 0.04,
                west + 0.10,
                yy - 0.045,
                yy + 0.045,
                lo + 0.44,
                hi - 0.32,
                'libraryMullion',
            )

    def run(a, b, width, steps):
        # From lower approach to upper landing; slab sides follow the soffit.
        ax, ay, az = a
        bx, by, bz = b
        length = hypot(bx - ax, by - ay)
        vx, vy = -(by - ay) * width / (2 * length), (bx - ax) * width / (2 * length)

        def pt(t, side, h):
            return (ax + (bx - ax) * t + side * vx, ay + (by - ay) * t + side * vy, h)

        for i in range(steps):
            t, u = i / steps, (i + 1) / steps
            lo = az + (bz - az) * t
            hi = az + (bz - az) * u
            # A folded flight over a single sloped soffit, not buried boxes.
            face(
                [pt(t, -1, hi), pt(u, -1, hi), pt(u, 1, hi), pt(t, 1, hi)],
                'bridgeConcrete',
            )
            face(
                [pt(t, 1, lo), pt(t, -1, lo), pt(t, -1, hi), pt(t, 1, hi)],
                'physicsPier',
            )
            for side in (-1, 1):
                v = [
                    pt(t, side, lo - 0.19),
                    pt(u, side, hi - 0.19),
                    pt(u, side, hi),
                    pt(t, side, hi),
                ]
                face(v if side == -1 else v[::-1], 'bridgeConcrete')
        face(
            [
                pt(0, 1, az - 0.19),
                pt(1, 1, bz - 0.19),
                pt(1, -1, bz - 0.19),
                pt(0, -1, az - 0.19),
            ],
            'physicsPier',
        )
        for side in (-1, 1):
            guard(pt(0, side, az + 0.10), pt(1, side, bz))

    run((-635.59, -822.50, 6.63), (-639.79, -822.46, 9.04), 1.82, 15)
    box(-642.15, -639.78, -823.37, -821.55, 8.82, 9.04, 'bridgeConcrete')
    box(-642.21, -642.16, -823.72, -821.64, 6.40, base, 'physicsPier')
    # Set-back dark slotted podium instead of the isolated street-facing
    # shop pane: the low platform terminates alongside the narrow stair.
    box(-644.65, -642.18, SOUTH - 7.72, SOUTH, 6.06, 10.12, 'physicsPier')
    box(-644.68, -641.99, SOUTH - 7.72, SOUTH, 10.12, 10.38, 'huicuiFrame')
    for j in range(26 if detail else 13):
        y = SOUTH - 7.57 + j * (7.40 / (25 if detail else 12))
        if detail:
            box(-642.18, -642.09, y, y + 0.058, 7.29, 9.70, 'fenceIron')
        else:
            face(
                [
                    (-642.09, y, 7.29),
                    (-642.09, y + 0.058, 7.29),
                    (-642.09, y + 0.058, 9.70),
                    (-642.09, y, 9.70),
                ],
                'fenceIron',
            )
    box(-641.45, -637.30, -823.15, -821.60, base + 0.03, base + 0.16, 'huicuiFrame')
    # Actual street/terrain intersection. Each edge elevation is taken on the
    # exported terrain; the east end meets the existing street-side paving.
    stations = [
        (-635.59, 6.63, 6.63),
        (-633.6, 6.535, 6.495),
        (-631.6, 6.365, 6.315),
        (-629.6, 6.125, 6.065),
        (-628.15, 5.965, 5.972),
        (-627.65, 5.922, 5.921),
    ]
    for a, b in zip(stations, stations[1:]):
        slab(
            [
                (a[0], -823.41, a[1]),
                (b[0], -823.41, b[1]),
                (b[0], -821.59, b[2]),
                (a[0], -821.59, a[2]),
            ],
            0.12,
            'bridgeConcrete',
        )
    # Unconnected narrow stone margin at the foot of the plinth.
    for i in range(4):
        y = SOUTH + i * 3.02
        h = 6.59 - 0.093 * i
        slab(
            [
                (FRONT - 0.85, y, h),
                (FRONT + 0.12, y, h - 0.025),
                (FRONT + 0.12, y + 3.02, h - 0.118),
                (FRONT - 0.85, y + 3.02, h - 0.093),
            ],
            0.12,
            'bridgeConcrete',
        )

    # North street: glazing and rectangular masonry bearings sit behind the
    # platform, and remain visible through its open undercroft.
    west_base = FRAME_WEST + 0.46
    glass_y = NORTH - 1.52
    if not detail:
        # These rooms share a single recessed glazing plane and continuous
        # stone base. Bearings mask the joins; keep just the visible faces.
        for ya, lo, hi, mat in (
            (glass_y, 7.32, base, 'physicsWindow'),
            (glass_y + 0.08, 5.65, 7.32, 'bridgeConcrete'),
            (glass_y + 0.055, 10.93, 11.01, 'fenceIron'),
        ):
            face(
                [
                    (FRONT - 11.06, ya, lo),
                    (west_base, ya, lo),
                    (west_base, ya, hi),
                    (FRONT - 11.06, ya, hi),
                ],
                mat,
            )
    for i in range(8):
        a = west_base + i * (FRONT - 11.06 - west_base) / 8
        b = west_base + (i + 1) * (FRONT - 11.06 - west_base) / 8
        box(a, a + 0.65, glass_y - 0.26, glass_y + 0.34, 5.6, base, 'physicsPier')
        if detail:
            box(a + 0.65, b, glass_y - 0.14, glass_y, 7.32, base, 'physicsWindow')
            box(
                a + 0.65,
                b,
                glass_y - 0.15,
                glass_y + 0.08,
                5.65,
                7.32,
                'bridgeConcrete',
            )
        for j in (1, 2, 3) if detail else (2,):
            x = a + 0.65 + (b - a - 0.65) * j / 4
            if detail:
                box(
                    x - 0.04,
                    x + 0.04,
                    glass_y,
                    glass_y + 0.055,
                    7.32,
                    base,
                    'fenceIron',
                )
            else:
                face(
                    [
                        (x + 0.045, glass_y + 0.055, 7.32),
                        (x - 0.045, glass_y + 0.055, 7.32),
                        (x - 0.045, glass_y + 0.055, base),
                        (x + 0.045, glass_y + 0.055, base),
                    ],
                    'fenceIron',
                )
        if detail:
            box(a + 0.65, b, glass_y, glass_y + 0.055, 10.93, 11.01, 'fenceIron')

    # The north deck is deliberately split around the descending flight.
    # Upper route against the wall, lower approach and ramp at its street edge.
    deck = 8.48
    box(-674.7, -644.12, glass_y, -806.56, deck - 0.38, deck, 'bridgeConcrete')
    box(-646.75, -644.12, -806.56, -804.06, deck - 0.38, deck, 'bridgeConcrete')
    for x in (-672.6, -663.0, -654.0, -645.1):
        for y in (-808.25, -807.04):
            box(
                x - 0.24, x + 0.24, y - 0.24, y + 0.24, 5.35, deck - 0.38, 'physicsPier'
            )
    box(-645.10, -644.62, -805.04, -804.58, 5.40, deck - 0.38, 'physicsPier')
    guard((-644.15, -809.80, deck), (-644.15, -804.10, deck))
    guard((-644.15, -804.10, deck), (-646.72, -804.10, deck))
    guard((-672.12, -806.58, deck), (-648.20, -806.58, deck))
    # Follow the measured axis and preserve a solid grade connection despite
    # the difference between photographed grade and the published site mesh.
    run((-651.53, -804.76, 6.96), (-646.72, -805.30, deck), 2.18, 10)
    slab(
        [
            (-646.84, -806.39, deck),
            (-646.60, -804.21, deck),
            (-645.98, -804.21, deck),
            (-645.98, -806.39, deck),
        ],
        0.38,
        'bridgeConcrete',
    )
    # Crossfall at the street edge is strong. Split the toe pad along the seam
    # with the ramp; the road-side half falls to the existing paving.
    slab(
        [
            (-651.65, -805.84, 6.96),
            (-651.41, -803.68, 6.96),
            (-653.35, -803.49, 6.95),
            (-653.35, -805.66, 6.95),
        ],
        0.33,
        'bridgeConcrete',
    )
    slab(
        [
            (-651.41, -803.68, 6.96),
            (-651.25, -802.73, 6.55),
            (-653.09, -802.54, 6.56),
            (-653.35, -803.49, 6.95),
        ],
        0.30,
        'bridgeConcrete',
    )
    x0, x1 = -653.35, -672.1
    y0, y1 = -804.80, -804.35
    h0, h1 = 6.95, deck
    slab(
        [
            (x0, y0 - 0.79, h0),
            (x1, y1 - 0.79, h1),
            (x1, y1 + 0.79, h1),
            (x0, y0 + 0.79, h0),
        ],
        0.27,
        'bridgeConcrete',
    )
    for side in (-0.76, 0.76):
        guard((x0, y0 + side, h0), (x1, y1 + side, h1))
    box(-674.72, x1, y1 - 0.83, -803.11, deck - 0.36, deck, 'bridgeConcrete')
    box(-674.72, x1, -806.58, y1 - 0.83, deck - 0.36, deck, 'bridgeConcrete')
    for x in (-671.15, -662.6, -655.7):
        hi = h0 + (h1 - h0) * (x - x0) / (x1 - x0)
        box(x - 0.22, x + 0.22, -804.73, -804.27, 5.42, hi - 0.27, 'physicsPier')
    guard((-674.66, -806.1, deck), (-674.66, -803.17, deck))
    # Low planter flanking the slab, clear of the street-facing windows.
    box(-642.0, -639.15, -807.91, -806.85, 6.13, 6.75, 'bridgeConcrete')
    box(-641.88, -639.27, -807.80, -806.98, 6.75, 6.79, 'grass')
    for a, b, y in ((-655.46, -644.12, -808.07), (-695.65, -692.05, -808.10)):
        box(a, b, y - 0.10, y + 0.07, base + 0.13, base + 0.25, 'lampMetal')
        part.face(
            [
                (a, glass_y, base + 0.49),
                (b, glass_y, base + 0.49),
                (b, y, base + 0.23),
                (a, y, base + 0.23),
            ],
            glass,
        )
        for j in range(max(3, round((b - a) / 1.55)) + 1):
            x = a + j * (b - a) / max(3, round((b - a) / 1.55))
            rail((x, glass_y, base + 0.47), (x, y, base + 0.21), radius=0.083)
            rail((x, glass_y, base - 0.15), (x, y - 0.14, base + 0.20), radius=0.055)
    if 'physicsGalvanized' not in C:
        C['physicsGalvanized'] = material(
            'physicsGalvanized', (0.205, 0.224, 0.232), 0.38, 0.50
        )
    part.m = [
        C['physicsGalvanized'] if mat == C['lampMetal'] else mat for mat in part.m
    ]
    body.add_part('物理学院院名墙、南向三层外廊与北平台', part)
