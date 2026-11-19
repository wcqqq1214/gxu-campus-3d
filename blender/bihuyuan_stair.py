"""East-projecting stair at the south end of Bihuyuan, in local metres."""

import math

from geometry import material, tile_material
from south_gate import inscription


def finishes(colors):
    for key, file in [('biIvoryTile', 'ivory'), ('biRoseTile', 'rose')]:
        tile_material(colors, key, f'bihuyuan-{file}.png', (0.7, 0.62, 0.51))
    if 'biStairConcrete' not in colors:
        colors['biStairConcrete'] = material('biStairConcrete', (0.34, 0.32, 0.29), 0.9)
    if 'biLetterBronze' not in colors:
        colors['biLetterBronze'] = material(
            'biLetterBronze', (0.39, 0.26, 0.095), 0.24, 0.86
        )


def slab(e, x0, x1, back, front, z0, z1, depth, *, end_depth=None):
    """A solid slab with a continuous soffit; endpoints give the top elevations."""
    a = [
        (x0, -back, z0),
        (x0, -front, z0),
        (x0, -front, z0 - depth),
        (x0, -back, z0 - depth),
    ]
    far_depth = depth if end_depth is None else end_depth
    b = [
        (x1, -back, z1),
        (x1, -front, z1),
        (x1, -front, z1 - far_depth),
        (x1, -back, z1 - far_depth),
    ]
    mat = e.colors['biStairConcrete']
    e.structure.face(a[::-1], mat)
    e.structure.face(b, mat)
    for i in range(4):
        j = (i + 1) % 4
        e.structure.face([a[i], a[j], b[j], b[i]], mat)


def parapet(e, path, band_heights, thickness=0.16):
    """Sweep the tiled face, coping and inner face together along straights and arcs.

    Each path station gives outer XY, outward unit normal, bottom and top.
    Band heights are measured down from the coping. UVs accumulate arc length.
    """
    stations = []
    distance = 0
    for i, (x, y, nx, ny, bottom, top) in enumerate(path):
        if i:
            distance += math.dist((x, y), path[i - 1][:2])
        heights = [top]
        for offset in band_heights:
            heights.extend([top - offset, top - offset - 0.16])
        heights.append(bottom)
        outer = [(x, y, z) for z in heights]
        inner = [(x - thickness * nx, y - thickness * ny, z) for z in (top, bottom)]
        stations.append((outer, inner, distance))
    ivory, rose = e.colors['biIvoryTile'], e.colors['biRoseTile']
    for (a, ai, u), (b, bi, v) in zip(stations, stations[1:]):
        # Eight 10 cm tiles per repeat. Follow the diagonal courses on the cheeks.
        for j in range(len(a) - 1):
            coords = [a[j + 1], b[j + 1], b[j], a[j]]
            uv = [
                (s / 0.80, (pt[2] - t) / 0.80)
                for s, pt, t in [
                    (u, coords[0], a[0][2]),
                    (v, coords[1], b[0][2]),
                    (v, coords[2], b[0][2]),
                    (u, coords[3], a[0][2]),
                ]
            ]
            e.structure.face(coords, rose if j % 2 else ivory, uv)
        e.structure.face(
            [a[0], b[0], bi[0], ai[0]],
            ivory,
            [
                (u / 0.8, 0),
                (v / 0.8, 0),
                (v / 0.8, thickness / 0.8),
                (u / 0.8, thickness / 0.8),
            ],
        )
        e.structure.face(
            [ai[0], bi[0], bi[1], ai[1]],
            ivory,
            [
                (u / 0.8, 0),
                (v / 0.8, 0),
                (v / 0.8, (b[-1][2] - b[0][2]) / 0.8),
                (u / 0.8, (a[-1][2] - a[0][2]) / 0.8),
            ],
        )
        e.structure.face([ai[1], bi[1], b[-1], a[-1]], e.colors['biStairConcrete'])
    for index in (0, -1):
        a, ai, _ = stations[index]
        cap = [a[0], ai[0], ai[1], a[-1]]
        e.structure.face(cap if index == 0 else cap[::-1], ivory)


def flight(e, start, finish, back, front, z0, z1):
    # A sloping concrete waist carries solid sawtooth treads with level nosings.
    count = 12
    going = (finish - start) / count
    rise = (z1 - z0) / count
    ascending_right = going > 0
    left, right = (
        ((start, z0), (finish, z1)) if ascending_right else ((finish, z1), (start, z0))
    )
    slab(e, left[0], right[0], back, front, left[1], right[1], 0.19)

    def surface(points):
        e.structure.face(
            points if ascending_right else points[::-1], e.colors['biStairConcrete']
        )

    for i in range(count):
        x, h = start + i * going, z0 + i * rise
        tread = [
            (x, -front, h + rise),
            (x + going, -front, h + rise),
            (x + going, -back, h + rise),
            (x, -back, h + rise),
        ]
        surface(tread)
        surface([(x, -back, h), (x, -front, h), tread[0], tread[3]])
        for y in (-front, -back):
            pts = [(x, y, h), (x + going, y, h + rise), (x, y, h + rise)]
            surface(pts if y == -front else pts[::-1])
        if e.detail:
            e.glazing.box(
                x + math.copysign(0.012, going),
                -(back + front) / 2,
                h + rise - 0.014,
                0.045,
                front - back,
                0.028,
                e.colors['paleRoof'],
            )


# Both street views show the tiled end tapering above the half-landing.
TURN_X = 4.55
TURN_BOTTOM = 1.30
TURN_CROWN = 5.55
BAND_TOP = 2.13
OUTER = 3.92
INNER = 2.76
REAR = 1.81
RETURN_START = 1.05


def turn_point(theta, z, inset=0.0):
    t = (z - TURN_BOTTOM) / (TURN_CROWN - TURN_BOTTOM)
    rx = 2.07 - 0.13 * t
    ry = (OUTER - REAR) / 2
    x = TURN_X + rx * math.sin(theta)
    # A shallow, oblique oval: the crown's east tip sits south of its chord.
    skew = 0.36
    y = -OUTER + ry * (1 - math.cos(theta)) - skew * math.sin(theta) ** 2 + 0.12 * t
    nx, ny = (
        ry * math.sin(theta) - 2 * skew * math.sin(theta) * math.cos(theta),
        -rx * math.cos(theta),
    )
    norm = math.hypot(nx, ny)
    # Both photographs show a slight fall across the crown towards the outer jamb.
    fall = 0.20 * math.sin(theta) ** 4 * min(1.0, max(0.0, (z - 4.75) / 0.40))
    return x - inset * nx / norm, y - inset * ny / norm, z - fall


def curved_landing(e, mid):
    ivory, rose = e.colors['biIvoryTile'], e.colors['biRoseTile']
    concrete = e.colors['biStairConcrete']
    # The outer jamb of the tall side opening curves back at the foot.
    rows = [
        (TURN_BOTTOM, None),
        (BAND_TOP - 0.16, None),
        (BAND_TOP, None),
        (2.80, (1.48, 1.73)),
        (3.00, (1.33, 1.73)),
        (3.23, (1.29, 1.73)),
        (3.47, (1.31, 1.73)),
        (3.71, (1.37, 1.73)),
        (3.79, (1.43, 1.73)),
        (4.76, (1.43, 1.73)),
        (TURN_CROWN - 0.39, None),
        (TURN_CROWN - 0.23, None),
        (TURN_CROWN, None),
    ]
    for (lo, a), (hi, b) in zip(rows, rows[1:]):
        cutout = a is not None and b is not None
        l0, r0 = a or (1.43, 1.73)
        l1, r1 = b or (1.43, 1.73)
        sections = [(0, l0, 0, l1, 22), (r0, math.pi, r1, math.pi, 22)]
        if not cutout:
            sections.append((l0, r0, l1, r1, 8))
        band = hi == BAND_TOP or hi == TURN_CROWN - 0.23
        for u0, u1, v0, v1, count in sections:
            for j in range(count):
                f, g = j / count, (j + 1) / count
                face = [
                    (u0 + (u1 - u0) * f, lo),
                    (u0 + (u1 - u0) * g, lo),
                    (v0 + (v1 - v0) * g, hi),
                    (v0 + (v1 - v0) * f, hi),
                ]
                uv = [(angle * 1.63 / 0.8, h / 0.8) for angle, h in face]
                e.structure.face(
                    [turn_point(angle, h) for angle, h in face],
                    rose if band else ivory,
                    uv,
                )
                e.structure.face(
                    [turn_point(angle, h, 0.16) for angle, h in reversed(face)],
                    concrete,
                )
        if cutout:
            for t0, t1 in [(l0, l1), (r0, r1)]:
                e.structure.face(
                    [
                        turn_point(t0, lo),
                        turn_point(t1, hi),
                        turn_point(t1, hi, 0.16),
                        turn_point(t0, lo, 0.16),
                    ],
                    rose,
                    [(0, lo / 0.8), (0, hi / 0.8), (0.2, hi / 0.8), (0.2, lo / 0.8)],
                )
        if (a is None) != (b is None):
            z = hi if b else lo
            left, right = b or a
            for j in range(8):
                u, v = (
                    left + (right - left) * j / 8,
                    left + (right - left) * (j + 1) / 8,
                )
                e.structure.face(
                    [
                        turn_point(u, z),
                        turn_point(v, z),
                        turn_point(v, z, 0.16),
                        turn_point(u, z, 0.16),
                    ],
                    rose,
                )
    angles = [0.0]
    for start, stop, count in ((0, 1.43, 22), (1.43, 1.73, 8), (1.73, math.pi, 22)):
        angles.extend(start + (stop - start) * i / count for i in range(1, count + 1))
    for theta in (0, math.pi):
        edge = [
            turn_point(theta, h, inset)
            for h, inset in (
                (TURN_BOTTOM, 0),
                (TURN_CROWN, 0),
                (TURN_CROWN, 0.16),
                (TURN_BOTTOM, 0.16),
            )
        ]
        e.structure.face(edge, ivory)
    for z, down in [
        (mid, False),
        (TURN_BOTTOM, True),
        (TURN_CROWN, False),
        (TURN_CROWN - 0.62, True),
    ]:
        center = (TURN_X, turn_point(math.pi / 2, z)[1], z)
        for u, v in zip(angles, angles[1:]):
            face = [center, turn_point(u, z), turn_point(v, z)]
            e.structure.face(face[::-1] if down else face, concrete)


def exterior_stair(e):
    finishes(e.colors)
    x0, x1 = 1.45, TURN_X
    outer, rear = OUTER, REAR
    # The entry lands on the rising pavement beside the east wall.
    sill, mid, upper, crown = 0.17, 1.725, 3.28, TURN_CROWN
    slab(e, x0 - 1.38, x0, INNER, outer, sill, sill, 0.21)
    flight(e, x0, x1, INNER + 0.02, outer - 0.12, sill, mid)
    flight(e, x1, RETURN_START, rear, INNER - 0.14, mid, upper)

    # Open under the landing. The support piers sit behind the rounded tiled screen.
    slab(e, 0, RETURN_START, 0.01, INNER - 0.14, upper, upper, 0.23)
    # Open along the north edge; the upper landing meets the east-wall door.
    for px, out in ((4.83, 3.66), (4.90, 2.77), (6.06, 2.85)):
        e.box(
            px,
            out,
            TURN_BOTTOM / 2,
            0.33,
            0.35,
            TURN_BOTTOM,
            'biStairConcrete',
        )
        # Flared head of each support beneath the round half-landing.
        for side in (-1, 1):
            foot = px + side * 0.15
            lip = foot + side * 0.40
            profile = [(foot, mid - 0.77), (lip, TURN_BOTTOM), (foot, TURN_BOTTOM)]
            faces = [[(x, -out + d, z) for x, z in profile] for d in (-0.17, 0.17)]
            e.structure.face(faces[0], e.colors['biStairConcrete'])
            e.structure.face(faces[1][::-1], e.colors['biStairConcrete'])
            e.structure.face(
                [faces[0][0], faces[1][0], faces[1][1], faces[0][1]],
                e.colors['biStairConcrete'],
            )
    # A single tiled pier ties the inner flight, landing and sloping cover together.
    post_x, post_out = 1.31, 2.42
    roof_knee, roof_high, roof_skin = 0.87, 7.10, 0.28
    post_height = (
        roof_high
        + (crown - roof_high) * (post_x - roof_knee) / (x1 - roof_knee)
        - roof_skin
    )
    e.box(post_x, post_out, post_height / 2, 0.25, 0.27, post_height, 'biStairConcrete')
    e.cladding(
        post_x - 0.125,
        post_x + 0.125,
        0.0,
        post_height,
        post_out + 0.136,
        'biIvoryTile',
    )
    # Turn the same two brick bands back towards the main façade.
    for front, bottom, top in [(outer - 0.12, 6.5, 7.10), (INNER, upper - 0.23, 4.31)]:
        x = x0 - 1.45
        parapet(
            e,
            [(x, -0.30, -1, 0, bottom, top), (x, -front, -1, 0, bottom, top)],
            (0.23 if top > 6 else 0.25,),
        )
    curved_landing(e, mid)

    # Exterior cheek follows the lower flight into the band on the curved landing.
    parapet(
        e,
        [
            (x0, -outer, 0, -1, sill - 0.16, 0.92),
            (x1, -outer, 0, -1, TURN_BOTTOM, BAND_TOP + 0.32),
        ],
        (0.32,),
    )
    # Inner return cheek is visible across the well. Its fascia continues on the balcony.
    parapet(
        e,
        [
            (0, -INNER, 0, -1, upper - 0.23, 4.31),
            (RETURN_START, -INNER, 0, -1, upper - 0.23, 4.31),
            (x1, -INNER, 0, -1, mid - 0.29, 2.53),
        ],
        (0.25,),
    )
    # Sloping cover and its deep, banded fascia meet both ends at full thickness.
    roof_front = outer - 0.12
    slab(e, 0, roof_knee, 0, roof_front, roof_high, roof_high, roof_skin)
    slab(e, roof_knee, x1, rear - 0.12, roof_front, roof_high, crown, roof_skin)
    # The deeper back edge is visible across the stairwell in the street view.
    slab(
        e,
        roof_knee,
        x1,
        rear - 0.12,
        rear + 0.05,
        roof_high - roof_skin,
        crown - roof_skin,
        0.22,
        end_depth=0.64,
    )
    parapet(
        e,
        [
            (0, -roof_front, 0, -1, 6.5, 7.10),
            (roof_knee, -roof_front, 0, -1, 6.5, 7.10),
            (x1, -roof_front, 0, -1, crown - 0.60, crown),
        ],
        (0.23,),
    )
    if e.detail:
        # Fix the handrail inside the tiled outer cheek, below the coping.
        rail_out = outer - 0.21
        rail_low, rail_high = 0.92 - 0.10, BAND_TOP + 0.32 - 0.10
        for i in (0, 3, 6, 9, 12):
            t = i / 12
            x = x0 + (x1 - x0) * t
            z = rail_low + (rail_high - rail_low) * t
            e.glazing.line(
                (x, -outer + 0.14, z - 0.06),
                (x, -rail_out, z),
                0.018,
                e.colors['metal'],
            )
        e.glazing.line(
            (x0, -rail_out, rail_low),
            (x1, -rail_out, rail_high),
            0.028,
            e.colors['metal'],
            n=10,
        )
    # Raised bronze letters face the street along the rounded front of the turn.
    for i, char in enumerate('碧湖苑'):
        glyph = inscription(
            char,
            0,
            0,
            0,
            0.88,
            0.70,
            e.colors['biLetterBronze'],
            False,
            flat=not e.detail,
            stroke_offset=0.005,
        )
        mapped = []
        for u, v, h in glyph.v:
            z = 4.77 - i * 1.00 + h
            theta = 0.245 + 1.28 * u / 2.02
            mapped.append(turn_point(theta, z, v - 0.035))
        glyph.v = mapped
        e.glazing.extend(glyph)
