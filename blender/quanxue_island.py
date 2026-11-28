"""Zhixing Academy on the Yueya Lake peninsula. Local -Y faces the approach."""

import math

from geometry import Mesh, tile_material
from south_gate import inscription, prism


def entrance_gable(m, x, half_depth, eave, rise, C, detail=True):
    # Section along the visible front pitch. The sill follows the roof plane.
    # The returned cap dies into the unaltered rear pitch behind the ridge.
    profile = [
        (-half_depth, 0.56),
        (-3.95, 0.56),
        (-3.95, 0.43),
        (-1.02, 0.43),
        (-0.72, 0.50),
        (-0.66, 1.15),
    ]
    for i in range(1, 11):
        a = math.pi * (1 - i / 10)
        profile.append((-0.13 + 0.53 * math.cos(a), 1.15 + 0.53 * math.sin(a)))
    profile.extend([(0.48, 0.56), (0.68, 0.29), (1.15, 0.13)])
    # Solid masonry and slightly wider dark coping share a horizontal joint.
    for layer in ('wall', 'coping', 'course') if detail else ('wall', 'coping'):
        half_width = 0.13 if layer == 'wall' else 0.16
        section = []
        for y, height in profile:
            bed = (
                eave + rise * (1 - abs(y) / half_depth) + 0.34 * max(0, -y / half_depth)
            )
            bottom = bed - 0.42 if layer == 'wall' else bed + height - 0.09
            top = bed + height - (0.09 if layer == 'wall' else 0)
            if layer == 'course':
                bottom, top = bed + height - 0.30, bed + height - 0.24
            section.append(
                [
                    (x - half_width, y, bottom),
                    (x - half_width, y, top),
                    (x + half_width, y, top),
                    (x + half_width, y, bottom),
                ]
            )
        mat = C['bridgeConcrete'] if layer == 'wall' else C['stone']
        m.face(section[0][::-1], mat)
        for first, second in zip(section, section[1:]):
            if first[0][1] == second[0][1]:
                m.face([first[1], first[2], second[2], second[1]], mat)
                continue
            for k in range(4):
                j = (k + 1) % 4
                m.face([first[k], first[j], second[j], second[k]], mat)
        m.face(section[-1], mat)


def roof(m, x, y, w, d, eave, rise, C, detail, turn=False, entrance=False, wing=False):
    r = Mesh()
    h = d / 2
    front_lift = 0.34 if entrance else 0.26 if wing else 0.0
    front_fascia = 0.42 if entrance else 0.50 if wing else 0.18
    for side in (-1, 1):
        a, b = -w / 2, w / 2
        edge = side * h
        front = (entrance or wing) and side < 0
        lip = eave + (front_lift if front else 0)
        face = [
            (a, edge, lip),
            (b, edge, lip),
            (b, 0, eave + rise),
            (a, 0, eave + rise),
        ]
        r.face(face if side < 0 else face[::-1], C['slate'])
        fascia = front_fascia if front else 0.18
        r.box(0, edge, lip - fascia / 2, w, 0.16, fascia, C['white'])
        if entrance and front:
            # Visible soffit return from the eave fascia to the transom face.
            front_edge, beam_edge = edge + 0.08, -3.18
            r.face(
                [
                    (a, front_edge, lip - fascia),
                    (a, beam_edge, eave + 0.125),
                    (b, beam_edge, eave + 0.125),
                    (b, front_edge, lip - fascia),
                ],
                C['white'],
            )
        if detail:
            count = 12 if wing and front else round(w / 0.27)
            for i in range(count):
                u = w * ((i + 0.5) / count - 0.5)
                r.line(
                    (u, edge, lip), (u, 0, eave + rise), 0.045, C['residencePodium'], 5
                )
                if front:
                    pitch = w / count
                    radius = pitch * 0.23
                    # Exposed round ends and the scalloped pan between adjacent rolls.
                    ring = [
                        (
                            u + radius * math.cos(j * math.tau / 12),
                            edge - 0.12,
                            lip + radius * math.sin(j * math.tau / 12),
                        )
                        for j in range(12)
                    ]
                    back = [(px, py + 0.13, pz) for px, py, pz in ring]
                    r.face(ring, C['slate'])
                    for j in range(12):
                        k = (j + 1) % 12
                        r.face([ring[k], ring[j], back[j], back[k]], C['slate'])
                    if i < count - 1:
                        outline = [
                            (u + pitch * t, edge - 0.105, lip - radius * v)
                            for t, v in [
                                (0.12, 0.25),
                                (0.24, 0.84),
                                (0.5, 1.35),
                                (0.76, 0.84),
                                (0.88, 0.25),
                                (0.5, 0.52),
                            ]
                        ]
                        r.face(outline, C['slate'])
    for side in (-1, 1):
        u = side * w / 2
        if entrance:
            entrance_gable(r, u, h, eave, rise, C, detail)
        pts = [
            (u, -h, eave + front_lift - front_fascia),
            (u, h, eave - 0.18),
            (u, 0, eave + rise + 0.12),
        ]
        r.face(pts if side > 0 else pts[::-1], C['bridgeConcrete'])
        for v in (-h, h):
            if entrance and v < 0:
                continue
            r.line(
                (u, v, eave + (front_lift if v < 0 else 0) + 0.06),
                (u, 0, eave + rise + 0.2),
                0.105,
                C['stone'],
            )
    r.box(0, 0, eave + rise + 0.08, w + 0.12, 0.20, 0.2, C['slate'])
    if turn:
        r.rotate_z(0, 0, math.pi / 2)
    r.v = [(u + x, v + y, z) for u, v, z in r.v]
    m.extend(r)


def build(l, b, z, C, detail):
    m = Mesh()
    floor = z + 1.38
    # Both entrance views constrain the lift; a larger rise masks the plaque.
    transom_lift = 0.09
    band_bottom = 3.88
    band_top = 4.41
    stone, wood = C['bridgeConcrete'], C['wood']
    # A continuous plinth beds into the sloping baseline ground and pedestrian surface.
    m.box(0, 0.1, floor - 1.35, 28.6, 33.2, 2.7, stone)
    for side in (-1, 1):
        x = side * 10.45
        m.box(side * 12, 0, floor + 1.85, 4.3, 16.8, 3.7, stone)
        roof(m, x, 0, 17, 9.3, floor + 3.75, 1.55, C, detail, True)
        for y in (-6.9, 0, 6.9):
            m.cylinder(side * 6.5, y, floor + 1.84, 0.17, 3.68, wood)
    for x, w in [(-11.3, 7.3), (0, 15.3), (11.3, 7.3)]:
        roof(m, x, 12.8, w, 9.6, floor + (4.05 if x == 0 else 3.7), 1.85, C, detail)
    m.box(0, 14.25, floor + 2, 28.6, 5.8, 4, stone)
    for x in (-7, -3.5, 3.5, 7):
        m.cylinder(x, 9, floor + 2, 0.22, 4, stone)
    for side in (-1, 1):
        x = side * 7.5
        start = len(m.f)
        m.box(x, -12.9, floor + 1.95, 4.9, 7.7, 3.9, stone)
        if detail:
            tile_material(
                C,
                'zhixingGreyBrick',
                'zhixing-grey-brick.jpg',
                (0.235, 0.270, 0.301),
                roughness=0.86,
            )
            # The box has a single approach-facing quad. UVs stay aligned
            # with the brick courses when the completed academy rotates.
            for index in range(start, len(m.f)):
                corners = [m.v[i] for i in m.f[index]]
                if all(abs(y + 16.75) < 1e-6 for _, y, _ in corners):
                    m.m[index] = C['zhixingGreyBrick']
                    m.face_uvs[index] = [
                        (px / 1.92, (h - floor) / 0.96) for px, _, h in corners
                    ]
        roof(m, x, -12.9, 5.05, 8.8, floor + 4, 1.45, C, detail, wing=True)
        m.box(x, -16.79, floor + 2, 1.45, 0.13, 2.15, C['gateRed'])
        m.box(x, -16.88, floor + 2, 1.24, 0.07, 1.92, C['glass'])
        m.box(x, -16.93, floor + 2.49, 1.24, 0.055, 0.065, C['gateRed'])
        m.box(x, -16.93, floor + 1.72, 0.055, 0.055, 1.38, C['gateRed'])
        for y in (-16, -9.8):
            height = 4.9 + (transom_lift if y == -16 else 0)
            m.cylinder(side * 3.15, y, floor + height / 2, 0.245, height, wood, 16)
            m.cylinder(side * 3.15, y, floor + 0.14, 0.34, 0.28, stone, 16)
    roof(m, 0, -12.95, 10.2, 9.1, floor + 5, 1.8, C, detail, entrance=True)
    m.box(0, -16, floor + transom_lift + 4.48, 3.48, 0.29, 0.9, wood)
    m.box(0, -16, floor + transom_lift + 4.95, 10, 0.26, 0.17, wood)
    # Pale soffit and the solid fascia above each five-bar side screen.
    m.box(0, -12.21, floor + 5.04, 9.88, 7.24, 0.07, C['white'])
    if detail:
        # The news-school photograph shows three ribbed shades across the
        # near bay and another on the passage axis behind them.
        for x, y in ((-2.65, -13.8), (0, -13.8), (2.65, -13.8), (0, -9.9)):
            crown = floor + 4.91
            m.cylinder(x, y, floor + 4.96, 0.012, 0.10, wood, 8)
            for i in range(8):
                angle = math.tau * i / 8
                points = [
                    (
                        x + radius * math.cos(angle),
                        y + radius * math.sin(angle),
                        crown - drop,
                    )
                    for radius, drop in (
                        (0.065, 0),
                        (0.16, 0.08),
                        (0.18, 0.18),
                        (0.16, 0.28),
                        (0.07, 0.35),
                    )
                ]
                for a, end in zip(points, points[1:]):
                    m.line(a, end, 0.012, wood, 5)
            for drop in (0, 0.35):
                m.cylinder(x, y, crown - drop, 0.073, 0.02, wood, 10)
    for side in (-1, 1):
        post_edge = 3.36
        jamb = 4.97
        m.box(
            side * (post_edge + jamb) / 2,
            -16,
            floor + (band_bottom + band_top) / 2,
            jamb - post_edge,
            0.18,
            band_top - band_bottom,
            C['white'],
        )
        if not detail:
            continue
        for i in range(5):
            u = post_edge + (jamb - post_edge) * (i + 0.5) / 5
            m.box(
                side * u, -16, floor + band_bottom / 2, 0.085, 0.11, band_bottom, wood
            )

        # The outer panel stops on the white fascia. The taller inner panel
        # runs from the plaque to the post, with a continuous bottom rail.
        for start, end, bottom in [(1.74, 2.94, 4.12), (post_edge, jamb, band_top)]:
            top = 4.95 + transom_lift - 0.085
            width = end - start
            height = top - bottom
            cells = 3 if start < 2 else 4
            for i in range(cells):
                u = start + i * width / cells
                step = width / cells
                h = bottom + (0.38 if i % 2 else 0.64) * height
                m.box(side * (u + step / 2), -16, floor + h, step, 0.09, 0.047, wood)
                m.box(
                    side * (u + step / 2),
                    -16,
                    floor + (top + h) / 2,
                    0.047,
                    0.09,
                    top - h,
                    wood,
                )
                if i:
                    m.box(
                        side * u,
                        -16,
                        floor + (top + bottom) / 2,
                        0.047,
                        0.09,
                        height,
                        wood,
                    )
            m.box(
                side * (start + end) / 2, -16, floor + bottom, width, 0.10, 0.055, wood
            )

    for i in range(3):
        top = floor - 0.15 * (i + 1)
        base = floor - 1.4
        m.box(0, -16.7 - i * 0.37, (base + top) / 2, 7.1, 0.42, top - base, stone)
    # Axis stone has an asymmetric shoulder and a flat inscription face in the gallery.
    outline = [
        (-1.3, 0),
        (1.24, 0),
        (1.18, 1.62),
        (0.72, 2.18),
        (0.16, 2.31),
        (-0.58, 1.94),
        (-0.86, 1.28),
        (-1.27, 0.85),
    ]
    prism(m, [(x, floor + h) for x, h in outline], 2.6, 0.88, C['gateStone'])
    if detail:
        for label, x, y, h, w, ht, mat in [
            ('院书行知', 0, -16.16, 4.48 + transom_lift, 3.1, 0.64, 'timeLetter'),
            ('劝', 0, 2.14, 1.5, 0.56, 0.56, 'gateRed'),
            ('学', 0, 2.14, 0.82, 0.56, 0.56, 'gateRed'),
        ]:
            m.extend(
                inscription(
                    label,
                    x,
                    y,
                    floor + h,
                    w,
                    ht,
                    C[mat],
                    False,
                    flat=True,
                    curve_resolution=2,
                )
            )
    m.rotate_z(0, 0, math.radians(67))
    cx, cy = l['center']
    m.v = [(x + cx, y + cy, h) for x, y, h in m.v]
    return m
