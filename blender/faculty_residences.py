"""Street elevations and mapped roof finishes of the three east-campus residences west of Lürong Lake."""

import math

from geometry import Mesh, tile_material
from humanities_facades import finish as roof_finish

# West to east, in the roof's own axes. Rows run from the south eave north.
# The patches describe broad visible finish changes, without assigning roof uses.
_ROOFS = {
    'way/760144472': (
        (0, 0.26, 0.50, 0.95, 1),
        (
            ('facultyGreyRoof', 'stone', 'facultyGreyRoof', 'stone'),
            (
                'facultyRussetRoof',
                'facultyGreyRoof',
                'facultyRussetRoof',
                'facultyRussetRoof',
            ),
        ),
    ),
    'way/760144473': (
        (0, 0.31, 0.59, 0.94, 1),
        (
            ('facultyGreyRoof', 'facultyGreyRoof', 'wood', 'stone'),
            (
                'facultyRussetRoof',
                'facultyGreyRoof',
                'facultyRussetRoof',
                'facultyRussetRoof',
            ),
        ),
    ),
    'way/760144474': (
        (0, 0.24, 0.48, 1),
        (
            ('stone', 'paleRoof', 'facultyMutedRoof'),
            ('facultyMutedRoof', 'wood', 'facultyMutedRoof'),
        ),
    ),
}
# West-row evidence is indexed separately in faculty-west/parameters.json.
# Stair profiles on blocked elevations remain plain.
_STAIRS = {
    'way/760144465': 'recess',
    'way/760144466': 'unresolved',
    'way/760144467': 'open',
    'way/760144472': 'paired',
    'way/760144473': 'paired',
    'way/760144474': 'open',
}
IDS = frozenset(_STAIRS)
_SHORT_BAYS = ((0.078, 0.136), (0.264, 0.20), (0.736, 0.20), (0.922, 0.136))
_LONG_BAYS = (
    (0.049, 0.073),
    (0.165, 0.13),
    (0.33, 0.143),
    (0.67, 0.143),
    (0.835, 0.13),
    (0.951, 0.073),
)


def _exterior(b, z, colors, detail, height, style):
    """Build in the footprint axes. Positive v is the north stair elevation."""
    corners = sorted(b['polygons'][0][0][:-1])
    sw, nw = sorted(corners[:2], key=lambda p: p[1])
    se, _ = sorted(corners[2:], key=lambda p: p[1])
    angle = math.atan2(se[1] - sw[1], se[0] - sw[0])
    cs, sn = math.cos(angle), math.sin(angle)
    width, depth = math.dist(sw, se), math.dist(sw, nw)
    body, openings = Mesh(), Mesh()
    plaster = roof_finish(colors, 'facultySalmonTile', (0.62, 0.399, 0.326), 0.87)
    belt = roof_finish(colors, 'facultyRoseBand', (0.39, 0.174, 0.164), 0.86)
    glazing = roof_finish(colors, 'facultyRecessedGlass', (0.14, 0.166, 0.172), 0.63)
    service_green = roof_finish(colors, 'facultyDoorGreen', (0.105, 0.215, 0.15), 0.84)
    rail = colors['paleRoof']

    def box(mesh, u, v, low, w, d, h, mat):
        mesh.box(
            sw[0] + u * cs - v * sn,
            sw[1] + u * sn + v * cs,
            z + low + h / 2,
            w,
            d,
            h,
            mat,
            angle,
        )

    def window(u, v, low, w, h, side, split=True):
        box(openings, u, v, low, w, 0.055, h, glazing)
        if detail:
            divisions = max(2, round(w / 0.62)) if split else 1
            for j in range(divisions + 1):
                pos = (j / divisions - 0.5) * 0.97
                box(openings, u + pos * w, v + side * 0.044, low, 0.055, 0.042, h, rail)
            box(openings, u, v + side * 0.041, low + h * 0.76, w, 0.047, 0.055, rail)

    base = height * 0.126
    step = (height - base) / 6
    east_row = b['id'] in _ROOFS
    south_obscured = b['id'] == 'way/760144467'
    south_19b = b['id'] == 'way/760144474'
    # A recessed wall behind the balcony fronts keeps their returns visible.
    mid = width / 2
    north = depth - 0.71
    plan = [(0, 0.71), (width, 0.71), (width, north)]
    if style in ('open', 'recess'):
        half = width * 0.062
        plan.extend(
            [
                (mid + half, north),
                (mid + half, north - 1.05),
                (mid - half, north - 1.05),
                (mid - half, north),
            ]
        )
    plan.append((0, north))
    ring = [(sw[0] + u * cs - v * sn, sw[1] + u * sn + v * cs) for u, v in plan]
    tiled_gable = detail and b['id'] == 'way/760144473'
    if tiled_gable:
        # Replace the east shell edge with the stepped, street-visible finish.
        for i, (a, end_point) in enumerate(zip(ring, ring[1:] + ring[:1])):
            if i != 1:
                body.face(
                    [
                        (*a, z - 0.5),
                        (*end_point, z - 0.5),
                        (*end_point, z + height),
                        (*a, z + height),
                    ],
                    plaster,
                )

        tile_material(
            colors, 'faculty17bGable', 'faculty17b-gable.jpg', (0.52, 0.35, 0.24), 0.87
        )
        tile_material(
            colors,
            'faculty17bPlinth',
            'faculty17b-plinth.jpg',
            (0.17, 0.18, 0.18),
            0.91,
        )
        end = depth * 0.70
        front = width + 0.55

        def point(u, v, h):
            return (sw[0] + u * cs - v * sn, sw[1] + u * sn + v * cs, z + h)

        path = [(front, 0.71), (front, end), (width, end), (width, north)]
        run = 0.0
        for a, e in zip(path, path[1:]):
            length = math.dist(a, e)
            for bottom, top, mat in (
                (-0.5, 0, colors['slate']),
                (0, 0.72, colors['faculty17bPlinth']),
                (0.72, height, colors['faculty17bGable']),
            ):
                coords = [
                    point(*a, bottom),
                    point(*e, bottom),
                    point(*e, top),
                    point(*a, top),
                ]
                # Unwrap continuously along the stepped elevation. V starts at grade.
                uv = [
                    (u / 1.92, h / 0.96)
                    for u, h in (
                        (run, bottom),
                        (run + length, bottom),
                        (run + length, top),
                        (run, top),
                    )
                ]
                body.face(coords, mat, uv if bottom >= 0 else None)
            run += length
        for bottom, top, mat in (
            (-0.5, 0.42, colors['slate']),
            (0.42, height, plaster),
        ):
            body.face(
                [
                    point(width, 0.71, bottom),
                    point(front, 0.71, bottom),
                    point(front, 0.71, top),
                    point(width, 0.71, top),
                ],
                mat,
            )
        body.face(
            [
                point(width, 0.71, height),
                point(front, 0.71, height),
                point(front, end, height),
                point(width, end, height),
            ],
            plaster,
        )
    else:
        body.extrude([[ring + [ring[0]]]], [[]], z - 0.5, height + 0.5, plaster)

    # End the old base just inside the replacement east surface.
    inset = 0.03 if tiled_gable else 0
    box(
        body,
        (width - inset) / 2,
        depth / 2,
        -0.5,
        width + 0.04 - inset,
        depth - 1.38,
        0.92,
        colors['slate'],
    )
    for side in (-1, 1):
        v = 0.71 if side == -1 else depth - 0.71
        for i in range(1, 9):
            u = width * i / 9
            if side == 1 and abs(u - width / 2) < 2.4:
                continue
            box(
                openings,
                u,
                v + side * 0.035,
                0.18,
                (2.7 if side < 0 else 1.15),
                0.08,
                base * 0.77,
                (colors['wood'] if i % 3 else rail) if side == -1 else service_green,
            )
        for floor in range(6):
            low = base + floor * step
            # Both wings have short end bays and broader glazed balcony bays.
            bays = _SHORT_BAYS if east_row else _LONG_BAYS
            if side < 0 and south_obscured:
                bays = ((0.62, 0.20), (0.805, 0.089), (0.924, 0.09))
            elif side < 0 and south_19b:
                bays = (
                    (0.074, 0.12),
                    (0.18, 0.065),
                    (0.315, 0.19),
                    (0.685, 0.19),
                    (0.82, 0.065),
                    (0.926, 0.12),
                )
            elif side < 0 and b['id'] == 'way/760144465':
                bays = ((0.20, 0.16), (0.80, 0.16))
            for frac, span in bays:
                u = frac * width
                floating = south_19b and side < 0 and span < 0.14
                if floating or (south_obscured and side < 0 and frac > 0.78):
                    # 19B has splayed window boxes flanking both broad balconies.
                    half = span * width / 2
                    profile = [
                        (-half, v),
                        (-half * 0.70, v - 0.74),
                        (half * 0.70, v - 0.74),
                        (half, v),
                    ]
                    world = [
                        (sw[0] + (u + t) * cs - q * sn, sw[1] + (u + t) * sn + q * cs)
                        for t, q in profile
                    ]
                    bottom_edge, sill, head, top_edge = (
                        (0.21, 0.27, 0.84, 0.9) if floating else (0, 0.32, 0.88, 1)
                    )
                    for a, bp in zip(world, world[1:]):
                        for bottom, top, mat in (
                            (bottom_edge, sill, plaster),
                            (sill, head, glazing),
                            (head, top_edge, plaster),
                        ):
                            body.face(
                                [
                                    (a[0], a[1], z + low + step * bottom),
                                    (bp[0], bp[1], z + low + step * bottom),
                                    (bp[0], bp[1], z + low + step * top),
                                    (a[0], a[1], z + low + step * top),
                                ],
                                mat,
                            )
                    body.face([(*a, z + low + top_edge * step) for a in world], plaster)
                    if floating:
                        body.face(
                            [
                                (*a, z + low + bottom_edge * step)
                                for a in reversed(world)
                            ],
                            plaster,
                        )
                        if detail:
                            for t in (-0.68, 0, 0.68):
                                box(
                                    openings,
                                    u + t * half,
                                    v - 0.75,
                                    low + sill * step,
                                    0.045,
                                    0.046,
                                    (head - sill) * step,
                                    rail,
                                )
                    continue
                out = v + side * (0.90 if 0.15 < frac < 0.85 else 0.62)
                box(
                    body,
                    u,
                    (v + out) / 2,
                    low,
                    span * width,
                    abs(out - v) + 0.04,
                    step * 0.31,
                    plaster,
                )
                box(
                    body,
                    u,
                    (v + out) / 2,
                    low - 0.09,
                    span * width + 0.13,
                    0.85,
                    0.15,
                    rail,
                )
                window_width = span * width * (0.74 if side == 1 else 0.89)
                # Solid tiled cheeks support the projecting brows and set the glazing back.
                for edge in (-1, 1):
                    cheek = (span * width - window_width) / 2
                    box(
                        body,
                        u + edge * (window_width + cheek) / 2,
                        (out + v) / 2,
                        low + step * 0.31,
                        cheek,
                        abs(out - v) + 0.03,
                        step * 0.68,
                        plaster,
                    )
                window(
                    u,
                    out - side * 0.10,
                    low + 0.31 * step,
                    window_width,
                    step * 0.60,
                    side,
                )
                box(
                    body,
                    u,
                    (out + v) / 2,
                    low + 0.91 * step,
                    span * width,
                    abs(out - v) + 0.15,
                    0.09 * step,
                    plaster,
                )
                box(
                    body,
                    u,
                    out + side * 0.044,
                    low + 0.09,
                    span * width,
                    0.06,
                    0.105,
                    belt,
                )
                if detail and span > 0.14:
                    for j in range(1, 9):
                        box(
                            openings,
                            u + window_width * (j / 9 - 0.5),
                            out + side * 0.07,
                            low + 0.31 * step,
                            0.032,
                            0.035,
                            0.53 * step,
                            rail,
                        )
                    box(
                        openings,
                        u,
                        out + side * 0.065,
                        low + 0.60 * step,
                        window_width,
                        0.045,
                        0.035,
                        rail,
                    )
                if detail:
                    for sign in (-1, 1):
                        box(
                            openings,
                            u + sign * (span * width / 2 - 0.055),
                            (out + v) / 2,
                            low + step * 0.31,
                            0.095,
                            abs(out - v) + 0.04,
                            step * 0.62,
                            plaster,
                        )
            if side < 0:
                for frac in (0.12, 0.29, 0.44) if south_obscured else (0.425, 0.575):
                    window(
                        width * frac,
                        v - 0.04,
                        low + 0.34 * step,
                        width * 0.082,
                        0.56 * step,
                        -1,
                    )
            box(body, width / 2, v + side * 0.035, low - 0.14, width, 0.09, 0.14, belt)

    # Two narrow openings per storey on the visible gables.
    for sign in (-1, 1):
        u = 0 if sign == -1 else width
        if sign == 1 and b['id'] == 'way/760144473':
            # Both window columns share the advanced southern panel of the east gable.
            end = depth * 0.70
            center = (0.71 + end) / 2
            span = end - 0.71
            if not tiled_gable:
                box(body, u + 0.27, center, 0, 0.56, span, height, plaster)
                box(body, u + 0.28, center, -0.5, 0.57, span, 0.92, colors['slate'])
            for i in range(6):
                low = base + i * step
                box(body, u + 0.55, center, low - 0.14, 0.07, span, 0.14, belt)
                box(body, u + 0.28, end, low - 0.14, 0.56, 0.07, 0.14, belt)
                box(
                    body,
                    u + 0.02,
                    (end + north) / 2,
                    low - 0.14,
                    0.055,
                    north - end,
                    0.14,
                    belt,
                )
                # Short ledges mark the two outer gable corners at each storey.
                for edge_u, edge_v in ((u + 0.63, 0.91), (u + 0.12, north - 0.20)):
                    box(body, edge_u, edge_v, low - 0.08, 0.38, 0.62, 0.12, rail)
                for frac, w, h, sill in (
                    (0.36, 0.85, 0.60, 0.26),
                    (0.57, 0.72, 0.33, 0.43),
                ):
                    box(
                        openings,
                        u + 0.57,
                        frac * depth,
                        low + sill * step,
                        0.075,
                        w,
                        step * h,
                        glazing,
                    )
                    if detail:
                        pane_v = frac * depth
                        bottom = low + sill * step
                        pane_h = step * h
                        for edge in (-1, 1):
                            box(
                                openings,
                                u + 0.61,
                                pane_v + edge * (w - 0.035) / 2,
                                bottom,
                                0.036,
                                0.035,
                                pane_h,
                                rail,
                            )
                        box(openings, u + 0.61, pane_v, bottom, 0.04, w, 0.035, rail)
                        if h > 0.5:
                            # The tall gable window has a shallow upper light.
                            box(
                                openings,
                                u + 0.61,
                                pane_v,
                                bottom + 0.76 * pane_h,
                                0.036,
                                w,
                                0.04,
                                rail,
                            )
            continue
        for i in range(6):
            low = base + i * step
            box(
                body,
                u + sign * 0.02,
                depth / 2,
                low - 0.14,
                0.055,
                depth - 1.39,
                0.14,
                belt,
            )
            blanks = b['id'] == 'way/760144474' and sign == 1
            for frac, w, h in (
                () if blanks else ((0.43, 0.85, 0.61), (0.73, 0.68, 0.32))
            ):
                box(
                    openings,
                    u + sign * 0.035,
                    depth * frac,
                    low + 0.32 * step,
                    0.075,
                    w,
                    step * h,
                    glazing,
                )
            for v in () if blanks else (0.91, depth - 0.91):
                box(body, u + sign * 0.13, v, low - 0.08, 0.35, 0.62, 0.12, rail)

        # Shallow stepped gable return visible along the northern half.
        if b['id'] != 'way/760144474' or sign < 0:
            wall_u = u + sign * 0.28
            box(body, wall_u, depth * 0.70, 0, 0.58, depth * 0.34, height, plaster)
            for i in range(6):
                low = base + i * step
                box(
                    body,
                    wall_u + sign * 0.3,
                    depth * 0.70,
                    low - 0.14,
                    0.055,
                    depth * 0.34,
                    0.14,
                    belt,
                )
                box(
                    openings,
                    wall_u + sign * 0.32,
                    depth * 0.70,
                    low + 0.37 * step,
                    0.06,
                    0.74,
                    0.34 * step,
                    glazing,
                )
        if b['id'] == 'way/760144465' and sign == 1:
            for v in (0.32, 0.65):
                box(
                    openings,
                    u + 0.04,
                    depth * v,
                    base * 0.54,
                    0.08,
                    1.12,
                    0.38,
                    glazing,
                )
    mid = width / 2
    north = depth - 0.71
    if style == 'paired':
        for offset in (-0.084, 0.084):
            u = mid + width * offset
            box(body, u, north + 0.48, 0, width * 0.083, 1.04, height + 0.46, plaster)
            for half in range(12):
                window(
                    u,
                    north + 1.025,
                    base + half * step / 2 + 0.12,
                    width * 0.049,
                    step * 0.35,
                    1,
                )
        for floor in range(6):
            window(
                mid,
                north + 0.04,
                base + floor * step + 0.32 * step,
                width * 0.056,
                step * 0.58,
                1,
            )
    elif style == 'open':
        for floor in range(6):
            low = base + floor * step
            box(body, mid, north - 0.32, low, width * 0.123, 1.52, 0.16, rail)
            window(mid, north - 0.99, low + 0.20, width * 0.074, step * 0.57, 1, False)
            box(body, mid, north + 0.23, low, width * 0.115, 0.48, step * 0.34, plaster)
            for sign in (-1, 1):
                box(
                    body,
                    mid + sign * width * 0.061,
                    north + 0.24,
                    low,
                    0.22,
                    0.52,
                    step,
                    plaster,
                )
    elif style == 'recess':
        for i in range(6):
            window(
                mid,
                north - 0.99,
                base + step * (i + 0.31),
                width * 0.055,
                step * 0.55,
                1,
            )
    if b['id'] == 'way/760144474':
        for u in (0.18, 0.40, 0.62):
            box(body, width * u, 0.26, base - 0.26, width * 0.16, 1.18, 0.23, belt)

        def hood_point(u, v, h):
            return (sw[0] + u * cs - v * sn, sw[1] + u * sn + v * cs, z + base + h)

        # At the east end each of the last two doors has its own tiled hood.
        half = min(1.63, width / 18 - 0.07)
        for door in (7, 8):
            center = width * door / 9
            front = [hood_point(center + k * half, -0.30, -0.24) for k in (-1, 1)]
            back = [hood_point(center + k * (half - 0.22), 0.71, 0.10) for k in (-1, 1)]
            heels = [hood_point(center + k * half, 0.71, -0.24) for k in (-1, 1)]
            body.face([front[0], front[1], back[1], back[0]], belt)
            body.face([front[0], back[0], heels[0]], plaster)
            body.face([front[1], heels[1], back[1]], plaster)
            box(body, center, 0.205, base - 0.35, half * 2, 1.01, 0.11, plaster)
    box(body, mid, north + 0.57, base - 0.30, 2.75, 1.29, 0.21, belt)
    box(openings, mid, north + 0.046, 0.05, 1.58, 0.12, base - 0.40, colors['dark'])
    if style == 'paired':
        for frac in (0.206, 0.794):
            w = width * 0.33
            for pos in (-0.48, -0.23, 0, 0.23, 0.48):
                box(
                    body,
                    width * frac + w * pos,
                    north + 0.08,
                    height + 0.32,
                    0.12,
                    0.17,
                    0.70,
                    rail,
                )
            box(body, width * frac, north + 0.08, height + 0.99, w, 0.20, 0.10, rail)
    for v in (0.12, depth - 0.12):
        box(body, mid, v, height, width, 0.24, 0.38, plaster)
    for u in (0.12, width - 0.12):
        box(body, u, depth / 2, height, 0.24, depth, 0.38, plaster)
    result = Mesh()
    result.add_part('住宅基座、层带、阳台及楼梯', body)
    result.add_part('公共立面窗格', openings)
    return result


def build(b, z, C, detail):
    breaks, rows = _ROOFS.get(b['id'], ((0, 1), (('paleRoof',), ('paleRoof',))))
    roof_finish(C, 'facultyMutedRoof', (0.135, 0.137, 0.098), 0.88)
    roof_finish(C, 'facultyGreyRoof', (0.148, 0.144, 0.119), 0.88)
    roof_finish(C, 'facultyRussetRoof', (0.187, 0.110, 0.090), 0.88)
    style = _STAIRS[b['id']]
    mesh = _exterior(b, z, C, detail, b['form']['height'], style)
    ring = b['polygons'][0][0][:-1]
    sw, nw = sorted(sorted(ring)[:2], key=lambda p: p[1])
    se, ne = sorted(sorted(ring)[2:], key=lambda p: p[1])
    h = z + b['form']['height']

    def point(u, v):
        return (
            *(
                (1 - v) * ((1 - u) * sw[k] + u * se[k])
                + v * ((1 - u) * nw[k] + u * ne[k])
                for k in (0, 1)
            ),
            h,
        )

    roof = Mesh()
    for (v0, v1), finishes in zip(((0, 0.54), (0.54, 1)), rows):
        for u0, u1, finish in zip(breaks, breaks[1:], finishes):
            roof.face(
                [point(u0, v0), point(u1, v0), point(u1, v1), point(u0, v1)], C[finish]
            )
    mesh.add_part('航片可辨屋面分区', roof)
    return mesh
