"""West-campus competition hall and north pool, OSM way/699156920.

World metres, X east and Y north. Dimensions are scaled to the mapped outline,
the 2021 GXU exterior film and north-up imagery. The entrance module supplies
the south stair, gallery and door assemblies against the closed south wall.
"""

from geometry import Mesh, material


def _ring(x, y, half_x, half_y, z):
    return [
        (x + i * half_x, y + j * half_y, z)
        for i, j in ((-1, -1), (1, -1), (1, 1), (-1, 1))
    ]


def _join(mesh, lower, upper, finish):
    for i in range(4):
        j = (i + 1) % 4
        mesh.face([lower[i], lower[j], upper[j], upper[i]], finish)


def _roof_panel(
    mesh,
    x,
    y,
    z,
    radial,
    offset,
    sign,
    transverse,
    inner,
    outer,
    width,
    lift,
    finish,
    colors,
):
    points = []
    for scale, delta in (
        (inner, -width),
        (outer, -width),
        (outer, width),
        (inner, width),
    ):
        v = sign * radial * scale
        u = offset + delta
        h = 21.38 + (0.84 - scale) * (22.66 - 21.38) / 0.24
        dx, dy = (v, u) if transverse else (u, v)
        points.append((x + dx, y + dy, z + h))
    if (sign == 1) != transverse:
        points.reverse()
    base = [(a, b, c - 0.09) for a, b, c in points]
    top = [(a, b, c + lift) for a, b, c in points]
    mesh.face(base[::-1], finish)
    _join(mesh, base, top, colors['metal'])
    mesh.face(top, finish)


def _roof(mesh, x, y, z, colors, detail):
    # Rolled eave, broad border, and low hipped field. Matching rectangular
    # sections preserve the diagonal seams visible in the orthophoto.
    sections = [
        (1, 19.85),
        (1, 20.5),
        (0.85, 21.43),
        (0.84, 21.38),
        (0.60, 22.66),
        (0.33, 23.55),
        (0.08, 24),
    ]
    lower = _ring(x, y, 46.54, 50, z + sections[0][1])
    mesh.face(lower[::-1], colors['metal'])
    for scale, height in sections[1:]:
        upper = _ring(x, y, 46.54 * scale, 50 * scale, z + height)
        finish = 'metal' if scale in (1, 0.84) else 'paleRoof'
        _join(mesh, lower, upper, colors[finish])
        lower = upper
    mesh.face(lower, colors['paleRoof'])

    # Four banks of short radial strips end at a row of raised pale caps.
    # Their footprints line up with the pitched surface throughout the slope.
    for transverse in (False, True):
        radial = 46.54 if transverse else 50
        across = 50 if transverse else 46.54
        for sign in (-1, 1):
            for i in range(-6, 7):
                offset = i * across * 0.075
                if detail:
                    _roof_panel(
                        mesh,
                        x,
                        y,
                        z,
                        radial,
                        offset,
                        sign,
                        transverse,
                        0.618,
                        0.833,
                        0.33,
                        0.085,
                        colors['metal'],
                        colors,
                    )
                _roof_panel(
                    mesh,
                    x,
                    y,
                    z,
                    radial,
                    offset,
                    sign,
                    transverse,
                    0.59,
                    0.622,
                    0.77,
                    0.29,
                    colors['white'],
                    colors,
                )
            if detail:
                for i in range(-3, 4):
                    u, v = i * 6.6, sign * radial * 0.485
                    dx, dy = (v, u) if transverse else (u, v)
                    height = 22.66 + (0.60 - 0.485) * (0.89 / 0.27)
                    mesh.cylinder(
                        x + dx,
                        y + dy,
                        z + height + 0.11,
                        0.64,
                        0.42,
                        colors['paleRoof'],
                        10,
                    )


def _facade(mesh, x, y, z, side, sign, colors, detail):
    # The two monumental openings in the film face south and east.
    radius, width = (39.54, 86) if side else (43, 79.08)

    def band(u, out, height, length, depth, thick, finish):
        v = sign * (radius + out)
        dx, dy = (v, u) if side else (u, v)
        w, d = (depth, length) if side else (length, depth)
        mesh.box(x + dx, y + dy, z + height, w, d, thick, colors[finish])

    opening = 57 if not side else 61
    public_face = (side and sign == 1) or (not side and sign == -1)
    if public_face:
        band(0, 0.10, 12.7, opening + 2, 0.26, 10.4, 'gymCurtain')
        for i in range(-3, 4):
            band(i * opening / 6, 0.45, 12.65, 1.25, 0.96, 10.30, 'stone')
        band(0, 0.63, 18.05, opening + 3.4, 1.48, 0.82, 'stone')
        for i in range(5):
            band(0, 1.02, 14.5 + i * 0.64, opening + 2, 1.26, 0.17, 'metal')
        if detail:
            for i in range(-17, 18):
                band(i * opening / 36, 0.25, 12.69, 0.075, 0.09, 10.38, 'slate')
            for h in (9.2, 11.1, 13.0):
                band(0, 0.26, h, opening + 1, 0.09, 0.075, 'slate')
        for end in (-1, 1):
            u = end * (width / 2 - 3)
            band(u, 0.32, 9.39, 5.55, 0.8, 19.5, 'stone')
            band(u, 0.76, 12.85, 1.47, 0.14, 10.6, 'gymCurtain')
            for i in range(3):
                band(u, 0.75, 18.55 + i * 0.52, 6.4, 1.65, 0.19, 'metal')
    else:
        # Secondary walls are obscured in the street-level reference.
        for i in range(-3, 4):
            band(i * width / 8, 0.08, 12, width / 8 - 1.6, 0.23, 5.6, 'glass')
        band(0, 0.32, 15, width - 2.8, 0.8, 0.44, 'metal')


def _pool_east_openings(mesh, wall, y, z, colors, detail):
    """Photo-scaled east wall openings, visible in GXU's 00:07 aerial."""
    # Thin stone cladding forms actual reveals against the closed pool wall.
    # Y increases northwards (screen right). The last pane meets the edge
    # of the observed section; the obscured bays retain their v4 geometry.
    sill, head = 0.85, 11.35
    spans = (
        (-18.9, -18.30, 6.00, 'dark'),
        (-15.0, -14.40, 6.00, 'dark'),
        (-11.1, -10.50, 1.65, 'dark'),
        (-9.65, -1.30, 1.15, 'glass'),
        (-0.55, 3.40, 1.15, 'glass'),
    )

    def panel(start, end, bottom, top, depth, finish):
        mesh.box(
            wall + depth / 2 - 0.015,
            y + (start + end) / 2,
            z + (bottom + top) / 2,
            depth,
            end - start,
            top - bottom,
            colors[finish],
        )

    edge = -20.40
    for start, end, bottom, finish in spans:
        # The continuous substrate also closes the wall below every sill.
        panel(edge, start, sill, head, 0.24, 'stone')
        panel(start, end, sill, bottom, 0.24, 'stone')
        panel(start, end, 10.75, head, 0.24, 'stone')
        panel(start, end, bottom, 10.75, 0.065, finish)
        if finish == 'dark':
            panel(start, end, 8.37, 8.98, 0.24, 'stone')
        elif detail:
            panel(start, end, 6.00, 6.09, 0.11, 'slate')
        edge = end
    panel(edge, 3.60, sill, head, 0.24, 'stone')


def _pool(mesh, z, colors, detail):
    # Low north wing offset towards the west; continuous roof rises in tiers.
    x, y = -104.5, -277
    mesh.box(x, y, z + 5.84, 41.3, 62.5, 12.68, colors['stone'])
    lower = _ring(x, y, 22.5, 32, z + 11.96)
    mesh.face(lower[::-1], colors['metal'])
    for rx, ry, h in (
        (22.5, 32, 12.3),
        (18, 28, 12.8),
        (16, 26, 13.65),
        (14.8, 25, 13.75),
        (10, 25, 14.43),
        (2, 25, 14.85),
    ):
        upper = _ring(x, y, rx, ry, z + h)
        _join(mesh, lower, upper, colors['paleRoof'])
        lower = upper
    mesh.face(lower, colors['paleRoof'])
    for side in (-1, 1):
        for i in range(-3, 4):
            if side == 1 and -2 <= i <= 0:
                continue
            mesh.box(
                x + side * 20.7, y + i * 8, z + 6.8, 0.21, 6.8, 5.3, colors['glass']
            )
            if detail:
                for t in (-1, 0, 1):
                    mesh.box(
                        x + side * 20.84,
                        y + i * 8 + t * 1.64,
                        z + 6.8,
                        0.12,
                        0.1,
                        5.3,
                        colors['metal'],
                    )
    _pool_east_openings(mesh, x + 20.65, y, z, colors, detail)
    mesh.box(x, y + 31.28, z + 6.8, 32, 0.17, 4.95, colors['glass'])


def _main_walls(mesh, x, y, z, colors):
    # Subdivide the backing wall itself so the entrance doors sit flush on
    # glazing at landing level. The reserved mounting plane stays continuous.
    low, high = z - 0.50, z + 19.96
    floor = _ring(x, y, 39.54, 43, low)
    boundary = []
    for a, b in zip(floor, floor[1:] + floor[:1]):
        for t in (0, 0.13, 0.87):
            boundary.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]), low))
    mesh.face(boundary[::-1], colors['stone'])
    mesh.face([(a, b, high) for a, b, _ in boundary], colors['stone'])
    for i, (a, b) in enumerate(zip(floor, floor[1:] + floor[:1])):
        for u, v in ((0, 0.13), (0.13, 0.87), (0.87, 1)):

            def at(t, h):
                return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]), h)

            for h0, h1, finish in (
                (low, z + 4.26, 'stone'),
                (z + 4.26, z + 7.6, 'glass'),
                (z + 7.6, z + 18.5, 'stone'),
                (z + 18.5, high, 'dark'),
            ):
                color = finish if u == 0.13 and i < 2 else 'stone'
                mesh.face([at(u, h0), at(v, h0), at(v, h1), at(u, h1)], colors[color])


def stadium_shell(l, b, z, C, detail):
    """Generate the enclosed shell at the shared south-entry datum."""
    if 'gymCurtain' not in C:
        C['gymCurtain'] = material('gymCurtain', (0.061, 0.28, 0.41), 0.29, 0.24)
    mesh = Mesh()
    x, y = l['center']
    # The plinth extends below the lowest adjacent terrain sample.
    _main_walls(mesh, x, y, z, C)
    _roof(mesh, x, y, z, C, detail)
    _pool(mesh, z, C, detail)
    for side in (False, True):
        for sign in (-1, 1):
            _facade(mesh, x, y, z, side, sign, C, detail)
    return mesh
