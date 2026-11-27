"""Public exterior of the South Area blocks, in campus metres (east, north, up)."""

from math import atan2, hypot

from geometry import material

from .panels import Plate

# Fractions measured/estimated along the mapped wall, from west to east.
# Each pair is a balcony centre and width. Only the indicated faces are replaced.
SPECS = {
    'way/759147055': (
        1,
        'N',
        [(0.08, 0.14), (0.31, 0.15), (0.48, 0.115), (0.68, 0.15), (0.90, 0.145)],
    ),
    'way/759147054': (2, 'N', [(0.051, 0.102)]),  # Only the western return is visible.
    'way/759147056': (
        3,
        'S',
        [(0.062, 0.124), (0.338, 0.19), (0.615, 0.18), (0.929, 0.142)],
    ),
    'way/759147053': (4, 'S', [(0.051, 0.102), (0.48, 0.18), (0.945, 0.11)]),
    'way/759147057': (
        5,
        'S',
        [
            (0.064, 0.128),
            (0.225, 0.142),
            (0.415, 0.128),
            (0.674, 0.14),
            (0.823, 0.105),
            (0.95, 0.10),
        ],
    ),
    'way/759147062': (7, '', []),
    'way/759147059': (9, 'N', []),  # Set out separately against both stepped wings.
    'way/759147058': (10, 'S', [(0.156, 0.312), (0.85, 0.30)]),
}


def finishes(C):
    colors = {
        'buff': (0.51, 0.395, 0.285),
        'sand': (0.63, 0.495, 0.345),
        'concrete': (0.41, 0.36, 0.30),
        'cream': (0.69, 0.625, 0.515),
        'trim': (0.44, 0.46, 0.405),
        'glass': (0.145, 0.182, 0.186),
        'slate': (0.185, 0.167, 0.145),
        'clay': (0.32, 0.121, 0.073),
        'gravel': (0.37, 0.35, 0.30),
    }
    palette = {}
    for key, rgb in colors.items():
        name = 'southDorm_' + key
        if name not in C:
            C[name] = material(name, rgb, 0.37 if key == 'glass' else 0.86)
        palette[key] = C[name]
    return palette


def window(m, x, y, h, w, height, n, p, detail, end=False):
    # Return wall has either east or west normal, as opposed to a long facade.
    def piece(u, offset, width, thick, high, mat):
        a, b = (x + n * offset, y + u) if end else (x + u, y + n * offset)
        m.box(a, b, h, thick if end else width, width if end else thick, high, p[mat])

    piece(0, 0.037, w, 0.075, height, 'glass')
    if detail:
        piece(0, 0.09, 0.055, 0.047, height, 'cream')


def balcony(m, x, y, n, bottom, width, depth, style, p, detail):
    # The floor, side returns and front are separate solids with an open cavity.
    front = y + n * (depth - 0.08)
    m.box(x, y + n * depth / 2, bottom + 0.08, width, depth, 0.16, p['concrete'])
    if style == 'west_corner':
        _west_corner_parapet(m, x, y, bottom, width, depth, p)
        return
    for edge in (-1, 1):
        m.box(
            x + edge * (width / 2 - 0.07),
            y + n * (depth + 0.04) / 2,
            bottom + 0.55,
            0.14,
            depth - 0.04,
            0.78,
            p['cream'],
        )
    if style in ('open', 'divided'):
        m.box(x, front, bottom + 0.24, width - 0.28, 0.16, 0.16, p['concrete'])
        m.box(x, front, bottom + 1.0, width, 0.19, 0.12, p['concrete'])
        if style == 'divided':
            return
        count = max(3, round((width - 0.32) / (0.48 if detail else 0.92)))
        for i in range(count):
            bx = x - width / 2 + 0.16 + (i + 0.5) * (width - 0.32) / count
            if detail:
                # V-shaped precast balusters visible on 1 and 3's upper balconies.
                s = min(0.13, (width - 0.32) / count * 0.31)
                for dx in [-s, s]:
                    m.line(
                        (bx, front, bottom + 0.32),
                        (bx + dx, front, bottom + 0.94),
                        0.053,
                        p['cream'],
                        4,
                    )
            else:
                m.box(bx, front, bottom + 0.63, 0.10, 0.12, 0.62, p['cream'])
    else:
        if style == 'pierced':
            _pierced_front(m, x, y, bottom, width, depth, p)
        else:
            m.box(x, front, bottom + 0.57, width - 0.28, 0.16, 0.82, p['buff'])
        m.box(
            x,
            front,
            bottom + 1.02,
            width,
            0.22,
            0.09,
            p['trim'] if style == 'rim' else p['concrete'],
        )


def roof(m, b, top, p, num):
    x0, y0, x1, y1 = b['bounds']
    if num == 7:
        # Ridge and triangular end walls, confirmed by the east street elevation.
        a, bx = x0 - 0.34, x1 + 0.34
        lo, hi = y0 - 0.46, y1 + 0.46
        cy = (hi + lo) / 2
        e = top + 0.13
        peak = e + 1.24
        # Sloped slab with a real soffit and matching rake fascias at its two ends.
        profile = [(lo, e), (cy, peak), (hi, e)]
        for (ya, za), (yb, zb) in zip(profile, profile[1:]):
            surf = [(a, ya, za), (bx, ya, za), (bx, yb, zb), (a, yb, zb)]
            m.face(surf, p['clay'])
            m.face([(x, y, h - 0.14) for x, y, h in reversed(surf)], p['concrete'])
            for x, normal in [(a, -1), (bx, 1)]:
                rake = [
                    (x, ya, za - 0.14),
                    (x, yb, zb - 0.14),
                    (x, yb, zb),
                    (x, ya, za),
                ]
                m.face(rake if normal == 1 else rake[::-1], p['concrete'])
        for y, n in [(lo, -1), (hi, 1)]:
            face = [(a, y, e - 0.14), (bx, y, e - 0.14), (bx, y, e), (a, y, e)]
            m.face(face if n == -1 else face[::-1], p['concrete'])
        wall_eave = e - 0.14 + 1.24 * (y0 - lo) / (cy - lo)
        for x, n in [(x0, -1), (x1, 1)]:
            points = [
                (x, y0, top),
                (x, y1, top),
                (x, y1, wall_eave),
                (x, cy, peak - 0.14),
                (x, y0, wall_eave),
            ]
            m.face(points if n == 1 else points[::-1], p['sand'])
        for y, n in [(y0, -1), (y1, 1)]:
            pts = [(x0, y, top), (x1, y, top), (x1, y, wall_eave), (x0, y, wall_eave)]
            m.face(pts if n == -1 else pts[::-1], p['sand'])
        return
    # A low rim follows the real ring, including the slot in the small ninth block.
    for poly in b['polygons']:
        for ring in poly:
            for a, c in zip(ring, ring[1:]):
                dx, dy = c[0] - a[0], c[1] - a[1]
                m.box(
                    (a[0] + c[0]) / 2,
                    (a[1] + c[1]) / 2,
                    top + 0.075,
                    hypot(dx, dy),
                    0.31,
                    0.15,
                    p['concrete'],
                    atan2(dy, dx),
                )


def _divided_bay(b, k, fh, floor, x, width, d, y, p, detail, new):
    h = floor - 0.03 + 0.56 * fh
    edge = sorted(b['polygons'][0][0][:-1], key=lambda v: v[1])[:2]
    a, c = edge

    def wall(u):
        return a[1] + (u - a[0]) * (c[1] - a[1]) / (c[0] - a[0])

    # The partition bears on the floor and terminates at the next slab/roof hood.
    l = x - 0.11
    r = x + 0.11
    bottom = floor + 0.16
    top = floor + fh if k < int(b['levels']) - 1 else floor + fh - 0.20
    front = y - d + 0.20
    new.face(
        [(l, front, bottom), (r, front, bottom), (r, front, top), (l, front, top)],
        p['cream'],
    )
    new.face(
        [(l, wall(l), bottom), (l, front, bottom), (l, front, top), (l, wall(l), top)],
        p['cream'],
    )
    new.face(
        [(r, front, bottom), (r, wall(r), bottom), (r, wall(r), top), (r, front, top)],
        p['cream'],
    )
    # Two shallow sashes touch the slightly skew mapped wall at their perimeter.
    # Their frame and glass partition the plane; neither lies on the plaster mesh.
    for side in (-1, 1):
        center = x + side * width * 0.245
        l = center - 0.68
        r = center + 0.68
        lo = h - 0.82
        hi = h + 0.82
        t = 0.052

        def face(u, v, z0, z1, offset, mat):
            new.face(
                [
                    (u, wall(u) - offset, z0),
                    (v, wall(v) - offset, z0),
                    (v, wall(v) - offset, z1),
                    (u, wall(u) - offset, z1),
                ],
                mat,
            )

        loop = [(l, lo), (r, lo), (r, hi), (l, hi)]
        for j, (u, z0) in enumerate(loop):
            v, z1 = loop[(j + 1) % 4]
            new.face(
                [
                    (v, wall(v), z1),
                    (v, wall(v) - 0.046, z1),
                    (u, wall(u) - 0.046, z0),
                    (u, wall(u), z0),
                ],
                p['concrete'],
            )
        face(l, r, lo, lo + t, 0.046, p['cream'])
        face(l, r, hi - t, hi, 0.046, p['cream'])
        face(l, l + t, lo + t, hi - t, 0.046, p['cream'])
        face(r - t, r, lo + t, hi - t, 0.046, p['cream'])
        # Reveal between frame face and glazing.
        inner = [(l + t, lo + t), (r - t, lo + t), (r - t, hi - t), (l + t, hi - t)]
        for j, (u, z0) in enumerate(inner):
            v, z1 = inner[(j + 1) % 4]
            new.face(
                [
                    (u, wall(u) - 0.046, z0),
                    (v, wall(v) - 0.046, z1),
                    (v, wall(v) - 0.012, z1),
                    (u, wall(u) - 0.012, z0),
                ],
                p['concrete'],
            )
        if detail:
            face(l + t, center - 0.022, lo + t, hi - t, 0.012, p['glass'])
            face(center - 0.022, center + 0.022, lo + t, hi - t, 0.012, p['cream'])
            face(center + 0.022, r - t, lo + t, hi - t, 0.012, p['glass'])
        else:
            face(l + t, r - t, lo + t, hi - t, 0.012, p['glass'])

    # The center is solid. South 3 has diamond castings and South 4 has a vertical grille.
    number = SPECS[b['id']][0]
    l = x - width / 2 + 0.14
    r = x + width / 2 - 0.14
    half = (0.33 if number == 3 else 0.49) * width / 2
    plate = Plate(
        new,
        lambda u, offset, h: (u, y - offset, h),
        d - 0.136,
        d - 0.024,
        p['buff'],
        p['concrete'],
    )
    lo = floor + 0.32
    hi = floor + 0.94
    plate.rectangle(x - half, x + half, lo, hi)
    for a, c in [(l, x - half), (x + half, r)]:
        pitch = (
            (0.38 if detail else 0.50) if number == 3 else (0.26 if detail else 0.36)
        )
        plate.perforated(a, c, lo, hi, max(3, round((c - a) / pitch)), number == 3)


def _pierced_front(m, x, y, floor, width, d, p):
    # Cast parapet with five diagonal openings on South 10.
    w = width - 0.28
    l = x - w / 2
    r = x + w / 2
    lo = floor + 0.16
    hi = floor + 0.98
    front = y - d
    back = front + 0.16
    for face in [
        [(l, back, lo), (r, back, lo), (r, front, lo), (l, front, lo)],
        [(r, front, lo), (r, back, lo), (r, back, hi), (r, front, hi)],
        [(l, back, lo), (l, front, lo), (l, front, hi), (l, back, hi)],
        [(l, front, hi), (r, front, hi), (r, back, hi), (l, back, hi)],
    ]:
        m.face(face, p['buff'])
    plate = Plate(
        m,
        lambda u, offset, h: (u, y - offset, h),
        d - 0.16,
        d,
        p['buff'],
        p['concrete'],
    )
    al = x - w * 0.245
    ar = x + w * 0.245
    plate.rectangle(l, r, lo, floor + 0.665)
    plate.rectangle(l, r, floor + 0.91, hi)
    plate.rectangle(l, al, floor + 0.665, floor + 0.91)
    plate.rectangle(ar, r, floor + 0.665, floor + 0.91)
    plate.diagonal_modules(al, ar, floor + 0.665, floor + 0.91, 5)


def _hood(new, x, y, underside, hood, p):
    lower = underside - 0.035
    l = x - hood / 2
    r = x + hood / 2
    d = 0.46
    th = 0.105
    A = (l, y, underside)
    B = (r, y, underside)
    F = (r, y - d, lower)
    E = (l, y - d, lower)

    def up(v):
        return (v[0], v[1], v[2] + th)

    for face, mat in [
        ([A, B, F, E], p['concrete']),
        ([up(E), up(F), up(B), up(A)], p['concrete']),
        ([E, F, up(F), up(E)], p['concrete']),
        ([A, E, up(E), up(A)], p['cream']),
        ([F, B, up(B), up(F)], p['cream']),
    ]:
        new.face(face, mat)


def primary_wall(facade, b, z, p, detail):
    num, side, bays = SPECS[b['id']]
    x0, y0, x1, y1 = b['bounds']
    w = x1 - x0
    top = z + b['height']
    n = 1 if side == 'N' else -1
    y = y1 if n == 1 else y0
    # Absolute X centres on the two five-metre tips of the notched ninth block.
    stacks = [(x0 + w * t, y, w * s) for t, s in bays]
    if num == 9:
        ring = b['polygons'][0][0]
        stacks = [
            ((ring[0][0] + ring[7][0]) / 2, ring[0][1], 3.45),
            ((ring[3][0] + ring[4][0]) / 2, ring[3][1], 3.55),
        ]
    standard = {
        1: 'open',
        2: 'solid',
        3: 'open',
        4: 'open',
        5: 'rim',
        9: 'solid',
        10: 'pierced',
    }[num]
    nlev = int(b['levels'])
    fh = b['height'] / nlev
    depth = {1: 1.05, 2: 1.18, 3: 1.14, 4: 1.08, 5: 1.30, 9: 1.02, 10: 1.15}[num]

    def place_window(level, x, wall_y, width, height):
        # The retained ground-floor glazing is 0.35 m deep on these long walls.
        # Use its actual span so an adjacent clear window keeps its original size.
        if level == 0 and any(
            abs(wall_y - entry['center'][1]) < 0.175
            and abs(x - entry['center'][0]) < (width + entry['width']) / 2
            for entry in b['form']['entrances']
        ):
            return
        window(facade, x, wall_y, z + (level + 0.56) * fh, width, height, n, p, detail)

    for index, (x, wy, width) in enumerate(stacks):
        style = standard
        if num in (3, 4) and width > w * 0.17:
            style = 'divided'
        elif num == 5 and index == 0:
            style = 'west_corner'
        for level in range(nlev):
            base = z + level * fh
            if level and style == 'divided':
                _divided_bay(
                    b, level, fh, base + 0.03, x, width, depth, wy, p, detail, facade
                )
            else:
                place_window(level, x, wy, width * 0.47, 1.62)
            if level:
                balcony(
                    facade,
                    x,
                    wy,
                    n,
                    base + 0.03,
                    width,
                    depth,
                    style,
                    p,
                    detail,
                )
        facade.box(
            x,
            wy + n * depth * 0.51,
            top - 0.085,
            width + 0.10,
            depth * 1.08,
            0.17,
            p['cream'],
        )
    if num in (1, 3, 4, 5, 10):
        # Standalone windows occupy the observed solid piers between balcony stacks.
        for left, right in zip(stacks, stacks[1:]):
            a = left[0] + left[2] / 2
            c = right[0] - right[2] / 2
            if c - a < 1.45:
                continue
            count = max(1, round((c - a) / 3.15))
            for j in range(count):
                for k in range(nlev):
                    x = a + (j + 0.5) * (c - a) / count
                    win = min(1.4, (c - a) / count * 0.56)
                    place_window(k, x, y, win, 1.52)
                    if num == 4 and k in (2, 3, 4):
                        head = z + (k + 0.56) * fh + 0.76 + 0.09
                        _hood(facade, x, y, head, win * 1.34, p)
    if num == 1:
        for k in range(nlev):
            for offset in (-0.57, 0.57):
                window(
                    facade,
                    x0,
                    (y0 + y1) / 2 + offset,
                    z + (k + 0.55) * fh,
                    0.55,
                    1.1,
                    -1,
                    p,
                    detail,
                    True,
                )


def _west_corner_parapet(m, x, wall, floor, width, depth, p):
    """South 5, west-facing return of the first stack on the south elevation."""
    left, right = x - width / 2, x + width / 2
    west, east = left + 0.14, right - 0.14
    rear, inner = 0.04, depth - 0.16
    cap_back, cap_front = depth - 0.19, depth + 0.03
    foot, side_top, bearing, crown = 0.16, 0.94, 0.98, 1.065

    def vertical(a, b, lo, hi, material):
        m.face(
            [
                (u, wall - d, floor + h)
                for (u, d), h in [(a, lo), (b, lo), (b, hi), (a, hi)]
            ],
            p[material],
        )

    def horizontal(a, b, back, front, h, material, bottom=False):
        ring = [(a, back), (a, front), (b, front), (b, back)]
        m.face(
            [(u, wall - d, floor + h) for u, d in (reversed(ring) if bottom else ring)],
            p[material],
        )

    # West cheek bears directly on the slab and meets the coping. The east
    # cheek terminates at its existing lower height.
    for outer, inside, top in [(left, west, bearing), (right, east, side_top)]:
        edges = [
            ((outer, rear), (outer, depth)),
            ((outer, depth), (inside, depth)),
            ((inside, inner), (inside, rear)),
            ((inside, rear), (outer, rear)),
        ]
        for a, b in edges:
            if outer == right:
                a, b = b, a
            vertical(a, b, foot, top, 'cream')
    horizontal(east, right, rear, depth, side_top, 'cream')
    vertical((west, depth), (east, depth), foot, bearing, 'buff')
    vertical((east, inner), (west, inner), foot, bearing, 'buff')
    vertical((east, depth), (east, inner), side_top, bearing, 'buff')

    # One L-shaped coping. Only the overhangs and the gap above the east
    # cheek expose an underside. Omit contact faces against slab and masonry.
    outline = [
        (left, rear),
        (left, cap_front),
        (right, cap_front),
        (right, cap_back),
        (west, cap_back),
        (west, rear),
    ]
    for a, b in zip(outline, outline[1:] + outline[:1]):
        vertical(a, b, bearing, crown, 'trim')
    horizontal(left, west, rear, cap_back, crown, 'trim')
    horizontal(left, right, cap_back, cap_front, crown, 'trim')
    for a, b, back, front in [
        (left, right, depth, cap_front),
        (west, right, cap_back, inner),
        (east, right, inner, depth),
    ]:
        horizontal(a, b, back, front, bearing, 'trim', bottom=True)
