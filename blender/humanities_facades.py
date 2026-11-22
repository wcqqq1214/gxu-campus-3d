"""Visible architectural details from GXU's college gallery and matched street views."""

import math
from pathlib import Path

from facade_bands import frame
from geometry import Mesh, material
from shaw_entrance import shaw_transoms
from south_gate import inscription

YULIN = 'relation/11970573'
SHAW = 'relation/12875607'
MANAGEMENT = 'relation/11564915'
GATE = 'way/1501460937'


def finish(colors, name, linear_rgb, roughness, metallic=0):
    if name not in colors:
        colors[name] = material(name, linear_rgb, roughness, metallic)
    return colors[name]


def yulin_front(building, z, colors, detail):
    mesh = Mesh()
    front = next(f for f in building['form']['facades'] if f['edge'] == 4)
    length, _, _, angle, point = frame(front)
    top = front['height']
    # Curved relief over the oculus. The outer roof line is straight in gallery 10.
    # The straight crown rises above both flanks. Its front face is in
    # front of the inset rooftop block, so the relief reads against pink plaster.
    x, y = point(0.5, -0.392)
    mesh.box(x, y, z + top + 0.96, length * 0.875, 0.78, 1.92, colors['pink'], angle)
    samples = 32 if detail else 16
    for i in range(samples):

        def vertex(j, radius, depth):
            a = math.pi * (0.14 + 0.72 * j / samples)
            x, y = point(0.5 + math.cos(a) * radius / length, depth)
            return (x, y, z + top - 1.08 + math.sin(a) * radius * 0.63)

        mesh.face(
            [
                vertex(i, 3.45, 0.21),
                vertex(i + 1, 3.45, 0.21),
                vertex(i + 1, 3.64, 0.21),
                vertex(i, 3.64, 0.21),
            ],
            colors['white'],
        )
        mesh.face(
            [
                vertex(i, 3.64, 0.21),
                vertex(i + 1, 3.64, 0.21),
                vertex(i + 1, 3.64, 0.10),
                vertex(i, 3.64, 0.10),
            ],
            colors['white'],
        )
    for t in (0.11, 0.89):
        x, y = point(t, 0.15)
        mesh.box(x, y, z + top - 0.65, length * 0.22, 0.34, 1.3, colors['white'], angle)
    for up, depth in ((1.40, 0.34), (1.94, 0.54)):
        x, y = point(0.5, depth / 2)
        mesh.box(x, y, z + top + up, length * 0.90, depth, 0.17, colors['white'], angle)
    x, y = point(0.5, 0.22)
    mesh.extend(
        inscription(
            '育林楼',
            x,
            y,
            z + 16.64,
            5.15,
            0.83,
            colors['wood'],
            False,
            flat=True,
            curve_resolution=2,
        )
    )
    return mesh


def shaw_front(building, z, colors, entry):
    mesh = Mesh()
    granite = colors['shawPinkGranite']
    joint = finish(colors, 'shawStoneJoint', (0.090, 0.064, 0.058), 0.88)
    soffit = finish(colors, 'shawSoffit', (0.52, 0.49, 0.42), 0.80)
    for f in building['form']['facades']:
        if f['part'] != 'front-podium' or f['ring'] or f['edge'] not in (7, 8, 9):
            continue
        if f['edge'] == 8:
            silver = finish(colors, 'shawRaisedSilver', (0.88, 0.94, 1.00), 0.27, 0.34)
            dark_edge = finish(
                colors, 'shawLetterEdges', (0.16, 0.17, 0.18), 0.42, 0.48
            )
            mesh.extend(entry.build(z, colors, joint, soffit, silver, dark_edge))
            continue
        length, _, _, angle, point = frame(f)
        # The joint bed continues around both folds. Individual granite slabs
        # sit on its outer face, with a narrow recessed joint between neighbours.
        x, y = point(0.5, 0.054)
        mesh.box(x, y, z + 3.434, length, 0.08, 0.56, joint, angle)
        count = max(1, round(length / 0.64))
        pitch = length / count
        for j in range(count):
            x, y = point((j + 0.5) / count, 0.108)
            mesh.box(x, y, z + 3.434, pitch - 0.012, 0.028, 0.56, granite, angle)
        pane = f['rule']['panels'][0]
        # The glazing continues right up to both folds above the stone fascia.
        for lo, hi in ((0, pane['from']), (pane['to'], 1)):
            x, y = point((lo + hi) / 2, 0.025)
            mesh.box(
                x,
                y,
                z + (pane['top'] + pane['bottom']) / 2,
                (hi - lo) * length,
                0.03,
                pane['top'] - pane['bottom'],
                colors['shawCurtainGlass'],
                angle,
            )
            if (f['edge'] == 7 and hi == 1) or (f['edge'] == 9 and lo == 0):
                # Span the glass return up to the fold. The generic panel stops at
                # its configured inset, leaving its end lights without transoms.
                rx, ry = point((lo + hi) / 2, 0.11)
                for up, thickness in shaw_transoms(pane):
                    mesh.box(
                        rx,
                        ry,
                        z + up,
                        (hi - lo) * length,
                        0.12,
                        thickness,
                        colors['shawGlazingFrame'],
                        angle,
                    )
        # Thin mullions divide each wider structural bay seen in the official
        # head-on photograph; the structural bars remain at the panel joints.
        bay = (pane['to'] - pane['from']) / pane['columns']
        for j in range(pane['columns']):
            x, y = point(pane['from'] + (j + 0.5) * bay, 0.102)
            mesh.box(
                x,
                y,
                z + (pane['top'] + pane['bottom']) / 2,
                0.048,
                0.102,
                pane['top'] - pane['bottom'],
                colors['shawGlazingFrame'],
                angle,
            )
    core = next(p for p in building['form']['parts'] if p['id'] == 'stair-core')
    ring = core['polygons'][0][0]
    cy = min(y for x, y in ring)
    x0, x1 = min(x for x, y in ring), max(x for x, y in ring)
    middle = (x0 + x1) / 2
    top = core['height']
    # Tower rises from the podium. Narrow ribbon left of the four upright characters.
    low = 9.97
    mesh.box(
        x0 + 0.98,
        cy - 0.07,
        z + (low + top - 3.6) / 2,
        1.6,
        0.14,
        top - 3.6 - low,
        colors['glass'],
    )
    for x in (x0 + 0.19, x0 + 0.99, x0 + 1.77):
        mesh.box(
            x,
            cy - 0.16,
            z + (low + top - 3.6) / 2,
            0.075,
            0.07,
            top - 3.6 - low,
            colors['dark'],
        )
    mesh.box(
        x1 - 0.42,
        cy - 0.09,
        z + (low + top - 3.6) / 2,
        0.72,
        0.15,
        top - 3.6 - low,
        colors['glass'],
    )
    for i in range(6):
        mesh.box(
            x1 - 0.42,
            cy - 0.19,
            z + low + (top - 3.6 - low) * i / 5,
            0.72,
            0.07,
            0.065,
            colors['dark'],
        )
        mesh.box(
            x0 + 0.98,
            cy - 0.16,
            z + low + (top - 3.6 - low) * i / 5,
            1.6,
            0.07,
            0.075,
            colors['dark'],
        )
    mesh.ellipsoid(
        middle, cy - 0.09, z + top - 1.52, 0.56, 0.085, 0.56, colors['dark'], 24, 8
    )
    for i, c in enumerate('邵逸夫楼'):
        mesh.extend(
            inscription(
                c,
                middle + 0.42,
                cy - 0.12,
                z + top - 4.7 - i * 2.1,
                1.0,
                1.0,
                colors['wood'],
                False,
                flat=True,
                curve_resolution=2,
            )
        )
    return mesh


def rotunda_faces(building):
    return [
        f
        for f in building['form']['facades']
        if f['part'] == 'main'
        and not f['ring']
        and f['edge'] in {*range(40, 47), *range(6)}
    ]


def rotunda_shell(shell, building, z, colors):
    """Open the lower two storeys under the curved stone fascia."""
    for f in rotunda_faces(building):
        a, b = f['start'], f['end']

        def at(p, h):
            return (p[0], p[1], z + h)

        for i, face in enumerate(shell.f):
            if len(face) != 4:
                continue
            verts = [shell.v[j] for j in face]
            if not all(
                min(math.dist(v[:2], a), math.dist(v[:2], b)) < 0.001 for v in verts
            ):
                continue
            if min(v[2] for v in verts) < z - 0.2 and max(v[2] for v in verts) > z + 19:
                # Other walls still share the original base vertices.
                modified = []
                cap = []
                for j in face:
                    vx, vy, vz = shell.v[j]
                    modified.append(len(shell.v))
                    shell.v.append((vx, vy, z + (6.65 if vz < z else 16.75)))
                    cap.append((vx, vy, z + 19.00) if vz < z else (vx, vy, vz))
                shell.f[i] = modified
                shell.face(cap, colors['stone'])
                break
        else:
            raise ValueError('Missing curved lobby wall on edge ' + str(f['edge']))
        inner_a, inner_b = [rotunda_inner(p) for p in (a, b)]
        shell.face(
            [at(a, 6.65), at(b, 6.65), at(inner_b, 6.65), at(inner_a, 6.65)],
            colors['white'],
        )
        if f['edge'] in (40, 5):
            outer, inner = (a, inner_a) if f['edge'] == 40 else (b, inner_b)
            shell.face(
                [at(outer, 0), at(inner, 0), at(inner, 6.65), at(outer, 6.65)],
                colors['stone'],
            )


def rotunda_inner(p):
    # Best-fit centre of the circular northeast perimeter in the mapped footprint.
    return [-486.3 + (p[0] + 486.3) * 0.77, -1146.3 + (p[1] + 1146.3) * 0.77]


def rotunda_cornice(mesh, faces, z, stone, soffit):
    """Sweep the gallery 22 fascia and two coping lips over the recessed balcony."""
    # Radial offset from the mapped footprint, elevation above the building datum.
    # The section returns to the balcony glazing below and to the flat roof above.
    profile = [
        (-1.22, 18.76),
        (0.62, 18.76),
        (0.62, 20.15),
        (0.72, 20.18),
        (0.72, 20.27),
        (0.60, 20.27),
        (0.60, 20.38),
        (0.78, 20.41),
        (0.78, 20.57),
        (0.0, 20.57),
        (0.0, 19.80),
        (-1.22, 19.80),
    ]

    def section(p):
        dx, dy = p[0] + 486.3, p[1] + 1146.3
        radius = math.hypot(dx, dy)
        return [
            (p[0] + dx * d / radius, p[1] + dy * d / radius, z + h) for d, h in profile
        ]

    for f in faces:
        a, b = section(f['start']), section(f['end'])
        for i in range(len(profile)):
            j = (i + 1) % len(profile)
            if profile[i][1] == profile[j][1] == 19.80:
                continue  # The existing roof already closes this strip.
            mesh.face([a[i], a[j], b[j], b[i]], soffit if i == 0 else stone)
        if f['edge'] == 40:
            mesh.face(a[::-1], stone)
        if f['edge'] == 5:
            mesh.face(b, stone)


def rotunda(building, z, colors):
    mesh = Mesh()
    door_edge = next(
        e['edge'] for e in building['form']['entrances'] if e['id'] == 'rotunda-lobby'
    )
    lobby_stone = finish(colors, 'rotundaWindowApron', (0.43, 0.41, 0.36), 0.71)
    mullion = finish(colors, 'rotundaAluminium', (0.36, 0.39, 0.39), 0.37, 0.44)
    faces = rotunda_faces(building)
    soffit = finish(colors, 'rotundaSoffit', (0.285, 0.24, 0.18), 0.81)
    deep_glass = finish(
        colors, 'rotundaGalleryGlazing', (0.048, 0.052, 0.050), 0.25, 0.34
    )
    rotunda_cornice(mesh, faces, z, colors['stone'], soffit)
    for f in faces:
        length, _, _, angle, point = frame(f)
        a, b = [rotunda_inner(p) for p in (f['start'], f['end'])]
        cx, cy = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        width = math.dist(a, b)
        mesh.box(cx, cy, z + 3.34, width, 0.12, 6.60, colors['glass'], angle)
        for h in (2.65, 4.05, 6.48):
            mesh.box(cx, cy, z + h, width, 0.23, 0.09, colors['dark'], angle)
        mesh.box(*a, z + 3.34, 0.095, 0.22, 6.60, colors['dark'], angle)
        mesh.box(cx, cy, z + 3.22, width, 0.23, 0.58, lobby_stone, angle)
        if f['edge'] == door_edge:
            mesh.box(cx, cy, z + 1.36, 0.065, 0.22, 2.65, colors['dark'], angle)
            normal = f['normal']
            for sign in (-1, 1):
                dx, dy = (b[0] - a[0]) / width, (b[1] - a[1]) / width
                mesh.box(
                    cx + dx * sign * 0.14 + normal[0] * 0.16,
                    cy + dy * sign * 0.14 + normal[1] * 0.16,
                    z + 1.18,
                    0.045,
                    0.06,
                    0.54,
                    mullion,
                    angle,
                )
            x, y = point(0.5, -1.5)
            mesh.box(x, y, z + 0.11, 2.85, 1.38, 0.22, colors['stone'], angle)
        if f['edge'] in (0, 2, 4, 40, 42, 44, 46):
            x, y = point(0.50, -0.30)
            mesh.box(x, y, z + 3.325, 0.80, 0.76, 6.65, colors['stone'], angle)
            mesh.box(x, y, z + 0.15, 0.95, 0.90, 0.30, colors['stone'], angle)
        # Three ribbons of office windows stand above the two-storey lobby.
        # Gallery 22 shows a deep opaque sill and small transom lights on each.
        x, y = point(0.5, 0.19)
        for sill in (6.88, 10.16, 13.46):
            mesh.box(x, y, z + sill + 0.19, length, 0.18, 0.38, lobby_stone, angle)
            mesh.box(x, y, z + sill + 2.47, length, 0.115, 0.09, mullion, angle)
        for t in (0.25, 0.75):
            x, y = point(t, 0.134)
            for sill in (6.88, 10.16, 13.46):
                mesh.box(x, y, z + sill + 2.76, 0.055, 0.075, 0.48, mullion, angle)
        # The top floor is a recessed balcony between solid piers.
        x, y = point(0.5, -1.18)
        mesh.box(x, y, z + 17.76, length * 0.89, 0.12, 2.00, deep_glass, angle)
        x, y = point(0.5, -0.55)
        mesh.box(x, y, z + 16.78, length, 1.26, 0.12, colors['stone'], angle)
        x, y = point(0.5, 0.02)
        mesh.box(x, y, z + 16.99, length, 0.15, 0.41, colors['stone'], angle)
        for t in (0.25, 0.75):
            sx, sy = point(t, -0.055)
            mesh.box(sx, sy, z + 17.40, 0.048, 0.055, 0.45, mullion, angle)
        for h in (17.39, 17.62):
            mesh.box(x, y, z + h, length, 0.06, 0.044, mullion, angle)
        if f['edge'] % 2 == 0:
            mesh.box(x, y, z + 17.98, 0.43, 0.36, 1.57, colors['stone'], angle)
        for h, depth in [
            (6.7, 0.55),
            (10.0, 0.34),
            (13.3, 0.34),
            (16.65, 0.46),
        ]:
            x, y = point(0.5, depth / 2)
            mesh.box(x, y, z + h, length + 0.05, depth, 0.22, colors['stone'], angle)
    return mesh


def new_east_gatehouse(building, z, colors, detail):
    """Low western annex. The neighbouring tower and lintel belong to new-east-gate."""
    mesh = Mesh()
    metal = finish(colors, 'gatehouseAluminium', (0.42, 0.45, 0.48), 0.40, 0.54)
    height = building['height']
    mesh.extrude(
        building['polygons'],
        building['roofTriangles'],
        z - 0.25,
        height + 0.25,
        metal,
        colors['metal'],
    )
    face = next(f for f in building['form']['facades'] if f['edge'] == 0)
    length, _, _, angle, point = frame(face)

    def box(t, offset, up, w, d, h, mat):
        x, y = point(t, offset)
        mesh.box(x, y, z + up, w, d, h, mat, angle)

    # The street view shows a low glazed opening in the continuous metal facing.
    # The sill and grille are scaled from the 11-degree view.
    t = 0.53
    box(t, 0.075, 1.62, 1.92, 0.14, 0.89, colors['dark'])
    for j in range(3):
        box(t + (j - 1) * 0.48 / length, 0.16, 1.62, 0.045, 0.045, 0.86, metal)
    box(t, 0.19, 1.19, 2.00, 0.28, 0.09, metal)
    count = round(length / 0.16) if detail else round(length / 0.33)
    for i in range(count):
        u = (i + 0.5) / count
        if abs(u - t) * length < 1.02:
            for low, high in [(0.27, 1.12), (2.12, height - 0.09)]:
                box(u, 0.055, (low + high) / 2, 0.045, 0.09, high - low, metal)
        else:
            box(u, 0.055, (height + 0.18) / 2, 0.045, 0.09, height - 0.18, metal)
    box(0.50, 0.06, 0.14, length, 0.16, 0.25, colors['stone'])
    return mesh


RED_HOUSE = 'way/759096564'
HISTORIC_PAIR = {'way/759090364', 'way/842784665'}


def historic_windows(building, z, colors):
    """North-facing vertical bays have opaque spandrels between the three storeys."""
    mesh = Mesh()
    door = building['form']['entrances'][0]
    grey = finish(colors, 'historicSpandrel', (0.19, 0.205, 0.21), 0.76)
    for f in building['form']['facades']:
        bays = f['rule'].get('panels', [])
        if not bays:
            continue
        length, _, _, angle, point = frame(f)
        for p in bays:
            t = (p['from'] + p['to']) / 2
            w = (p['to'] - p['from']) * length
            x, y = point(t, 0.07)
            above_door = f['edge'] == door['edge'] and abs(t - door['t']) < 0.01
            if not above_door:
                mesh.box(x, y, z + 1.75, w, 0.09, 2.10, colors['shadeGlass'], angle)
                xx, yy = point(t, 0.135)
                mesh.box(xx, yy, z + 1.75, 0.055, 0.05, 2.10, colors['dark'], angle)
            for bottom, top in [(3.30 if above_door else 2.80, 3.73), (5.75, 6.85)]:
                xx, yy = point(t, 0.205)
                mesh.box(
                    xx, yy, z + (top + bottom) / 2, w, 0.09, top - bottom, grey, angle
                )
                for h in (bottom + 0.12, bottom + 0.25, top - 0.15):
                    xx, yy = point(t, 0.26)
                    mesh.box(xx, yy, z + h, w, 0.035, 0.033, colors['dark'], angle)
    return mesh


def red_house_ends(building, z, colors):
    mesh = Mesh()
    plaster = finish(colors, 'redHouseCream', (0.68, 0.45, 0.25), 0.87)
    for f in building['form']['facades']:
        length, u, n, angle, point = frame(f)
        # Wide horizontal plaster band interrupts the pink brickwork on all sides.
        x, y = point(0.5, 0.034)
        mesh.box(x, y, z + 3.56, length, 0.065, 1.32, plaster, angle)
        mesh.box(x, y, z + 0.38, length, 0.07, 0.76, colors['stone'], angle)
        if f['edge'] not in (0, 2):
            continue
        for t, bottom in [(0.14, 0.98), (0.14, 4.48), (0.5, 4.57)]:
            x, y = point(t, 0.095)
            mesh.box(x, y, z + bottom + 0.70, 0.94, 0.12, 1.4, colors['dark'], angle)
            x, y = point(t, 0.18)
            mesh.box(x, y, z + bottom + 0.7, 0.84, 0.08, 0.06, colors['white'], angle)
        for i in range(3):
            height = (3 - i) * 0.14
            x, y = point(0.5, 0.24 + i * 0.33)
            mesh.box(x, y, z + height / 2, 2.45, 0.34, height, colors['stone'], angle)
        # Short-end roof vent, as seen above the tiled eave in the college photo.
        h = building['form']['height']

        def v(t, depth, up):
            px, py = point(0.5 + t / length, depth)
            return px, py, z + h + up

        front = -1.95
        peak = 1.78
        verts = [v(-1.65, front, 0.62), v(1.65, front, 0.62), v(0, front, peak)]
        mesh.face(verts, plaster)
        for s in (-1, 1):
            mesh.face(
                [
                    v(s * 1.82, front + 0.18, 0.56),
                    v(0, front + 0.18, peak + 0.13),
                    v(0, -4.3, peak + 0.13),
                    v(s * 1.82, -4.3, 0.56),
                ],
                colors['red'],
            )
        mesh.face(
            [
                v(-0.93, front + 0.025, 0.71),
                v(0.93, front + 0.025, 0.71),
                v(0, front + 0.025, 1.38),
            ],
            colors['dark'],
        )
    return mesh


def arts_entry_sign(building, z, colors):
    mesh = Mesh()
    entry = next(e for e in building['form']['entrances'] if e.get('shelter'))
    front = next(f for f in building['form']['facades'] if f['edge'] == entry['edge'])
    length, u, n, angle, point = frame(front)
    roof = entry['shelter']
    # Passage endpoints are on the outer edge of the separately mapped canopy.
    cx, cy = roof['passages'][1][-1]
    tx, ty = -n[1], n[0]
    # In both west views the inscription stands against a continuous light fascia.
    # Set the masonry behind the lettering and keep the roof edge at its front.
    for depth, up, width, thickness, height in (
        (0.35, 4.47, 11.54, 0.32, 1.34),
        (0.31, 5.16, 11.68, 0.43, 0.09),
    ):
        mesh.box(
            cx - n[0] * depth,
            cy - n[1] * depth,
            z + up,
            width,
            thickness,
            height,
            colors['white'],
            angle,
        )
    for text, width, height, up in [
        ('艺术学院', 7.6, 1.25, 4.98),
        ('SCHOOL OF ARTS', 6.0, 0.30, 4.15),
    ]:
        glyph = inscription(
            text,
            0,
            0,
            0,
            width,
            height,
            colors['dark'],
            False,
            flat=True,
            curve_resolution=3,
            font_path=Path(__file__).parent / 'fonts/GXUArtsSign.ttf',
        )
        glyph.v = [
            (cx + tx * x - n[0] * y, cy + ty * x - n[1] * y, z + up + h)
            for x, y, h in glyph.v
        ]
        mesh.extend(glyph)
    # The original approach pavement meets the mapped canopy at its foot.
    # Three risers occupy the first metre inside its front edge. The raised
    # landing continues to the doors, below their transoms and between the columns.
    floor = roof['floorHeight']
    run = 0.32
    rise = 0.12
    full_depth = math.dist(roof['passages'][1][0], roof['passages'][1][-1])
    width = entry['width'] + 0.28
    for j in range(3):
        d = (j + 0.5) * run
        mesh.box(
            cx - n[0] * d,
            cy - n[1] * d,
            z + floor + (j + 1) * rise / 2,
            width,
            run,
            (j + 1) * rise,
            colors['stone'],
            angle,
            bottom=False,
        )
    remaining = full_depth - 3 * run
    d = 3 * run + remaining / 2
    mesh.box(
        cx - n[0] * d,
        cy - n[1] * d,
        z + floor + 0.18,
        width,
        remaining,
        0.36,
        colors['stone'],
        angle,
        bottom=False,
    )
    for side in (-1, 1):
        dx = side * (width / 2 + 0.32)
        mesh.box(
            cx + tx * dx - n[0] * 0.60,
            cy + ty * dx - n[1] * 0.60,
            z + floor + 0.33,
            0.62,
            1.20,
            0.66,
            colors['stone'],
            angle,
            bottom=False,
        )
    for dx in [-2.9, -1.5, 0, 1.5, 2.9]:
        mesh.box(
            cx + tx * dx - n[0] * 0.12,
            cy + ty * dx - n[1] * 0.12,
            z + 4.34,
            0.052,
            0.10,
            1.08,
            colors['dark'],
            angle,
        )
    # The official head-on view shows a shallow transom over the nine top windows.
    band = front['rule']['windowBands']
    fh = front['height'] / front['levels']
    for opening in band['windows']:
        center = (opening['from'] + opening['to']) / 2
        x, y = point(center, 0.273)
        mesh.box(
            x,
            y,
            z + (2.56 + band['heightRatio'] * 0.22) * fh,
            (opening['to'] - opening['from']) * length,
            0.035,
            0.045,
            colors['dark'],
            angle,
        )
    for j in range(1, 9):
        x, y = point(j / 9, 0.12)
        mesh.box(x, y, z + 8.25, 0.16, 0.27, 2.83, colors['pink'], angle)
    return mesh


def continuing_canopy(mesh, entry, z, colors):
    """Rounded metal fascia over the north courtyard entrance, seen at 122°."""
    angle = math.radians(entry['bearing'])
    n = (math.sin(angle), math.cos(angle))
    t = (n[1], -n[0])
    x, y = entry['center']
    width = entry['stairFlight']['width']
    top = entry['landingHeight'] + 3.45
    finish_index = finish(
        colors, 'continuingCanopyMetal', (0.59, 0.55, 0.46), 0.46, 0.31
    )

    def vertex(along, depth, height):
        return (
            x + t[0] * along + n[0] * depth,
            y + t[1] * along + n[1] * depth,
            z + height,
        )

    # Closed half-round nose joined to the level soffit and roof in one profile.
    section = [(0, top), (0.86, top)]
    for i in range(1, 13):
        a = math.pi * i / 12
        section.append((0.86 + 0.36 * math.sin(a), top - 0.36 + 0.36 * math.cos(a)))
    section.append((0, top - 0.72))
    ends = [[vertex(s * width / 2, d, h) for d, h in section] for s in (-1, 1)]
    mesh.face(ends[0], finish_index)
    mesh.face(ends[1][::-1], finish_index)
    for i in range(len(section)):
        j = (i + 1) % len(section)
        mesh.face([ends[0][i], ends[1][i], ends[1][j], ends[0][j]], finish_index)
    for along in (-width * 0.36, width * 0.36):
        px, py, pz = vertex(along, 0.38, (top - 0.72 + entry['landingHeight']) / 2)
        mesh.box(
            px,
            py,
            pz,
            0.37,
            0.55,
            top - 0.72 - entry['landingHeight'],
            colors['stone'],
            -angle,
        )


def physics_lobby(mesh, entry, z, colors, form):
    """Glazed vestibule, rectangular stone surround and transom seen from due south."""
    p = entry['attachedPortico']
    floor = p['platformHeight']
    width = entry['width']
    n = math.radians(entry['bearing'])
    nx, ny = math.sin(n), math.cos(n)
    x, y = entry['center']
    dark = finish(colors, 'physicsVestibuleGlass', (0.085, 0.107, 0.105), 0.30, 0.25)

    def box(dx, offset, up, w, depth, h, material):
        mesh.box(
            x + ny * dx + nx * offset,
            y - nx * dx + ny * offset,
            z + up,
            w,
            depth,
            h,
            material,
            -n,
        )

    # Standard attached-portico door panels remain behind these flush frames.
    for side in (-1, 1):
        box(
            side * (width / 2 + 0.16),
            0.20,
            floor + 1.36,
            0.32,
            0.28,
            2.72,
            colors['stone'],
        )
        box(side * (width / 2 + 0.89), 0.10, floor + 1.30, 1.05, 0.12, 2.60, dark)
    box(0, 0.23, floor + 2.68, width + 0.64, 0.31, 0.30, colors['stone'])
    for dx in (-width / 4, 0, width / 4):
        box(dx, 0.134, floor + 1.26, 0.065, 0.065, 2.52, colors['dark'])
    low = floor + 2.88
    high = p['clearHeight'] - 0.06
    box(0, 0.09, (low + high) / 2, width + 2.85, 0.12, high - low, dark)
    for j in range(7):
        dx = (j - 3) * (width + 2.8) / 6
        box(dx, 0.18, (low + high) / 2, 0.06, 0.055, high - low, colors['white'])

    # The due-south frame shows narrower panes and paired transoms within
    # the broad structural grid of the southwest curtain wall.
    wall = next(
        f
        for f in form.get('facades', [])
        if f['edge'] == entry['edge'] and f['ring'] == 0
    )
    pane = next(p for p in wall['rule']['panels'] if p['id'] == 'south-glazing')
    length, _, _, angle, point = frame(wall)
    width = (pane['to'] - pane['from']) * length
    height = pane['top'] - pane['bottom']
    for i in range(pane['columns']):
        t = pane['from'] + (i + 0.5) / pane['columns'] * (pane['to'] - pane['from'])
        xx, yy = point(t, 0.098)
        mesh.box(
            xx,
            yy,
            z + (pane['top'] + pane['bottom']) / 2,
            0.047,
            0.05,
            height,
            colors['metal'],
            angle,
        )
    xx, yy = point((pane['from'] + pane['to']) / 2, 0.115)
    for i in range(pane['rows']):
        mesh.box(
            xx,
            yy,
            z + pane['bottom'] + (i + 0.58) * height / pane['rows'],
            width,
            0.055,
            0.062,
            colors['metal'],
            angle,
        )


def continuing_roof_edge(mesh, a, b, height, colors):
    """Open the slatted parapet at the street end seen above the gate in the 292° panorama."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    angle = math.atan2(dy, dx)
    if min(a[0], b[0]) > 518:
        span = length
    elif a[1] < -658 and b[1] < -658 and a[0] > b[0]:
        # Two southern end bays are visible before the tall solid rear cornice.
        span = min(length, 11.0)
    else:
        return False

    def box(start, end, up, depth, tall, material):
        t = (start + end) / (2 * length)
        mesh.box(
            a[0] + dx * t,
            a[1] + dy * t,
            height + up,
            end - start,
            depth,
            tall,
            material,
            angle,
        )

    if span < length:
        box(span, length, 0.40, 0.25, 0.80, colors['white'])
    box(0, span, 0.15, 0.25, 0.30, colors['white'])
    for up in (0.45, 0.62, 0.79, 0.96):
        box(0, span, up, 0.11, 0.065, colors['dark'])
    bays = max(1, round(span / 3.10))
    for i in range(bays):
        midpoint = span * (i + 0.5) / bays
        box(midpoint - 0.12, midpoint + 0.12, 0.64, 0.25, 0.68, colors['white'])
    return True


def continuing_street_front(building, z, colors):
    """Warm sill panels and narrow white pilasters on the photographed shop frontage."""
    mesh = Mesh()
    face = next(
        f for f in building['form']['facades'] if f['edge'] == 2 and f['ring'] == 0
    )
    band = face['rule']['windowBands']
    length, _, _, angle, point = frame(face)
    fh = face['height'] / face['levels']
    finish_index = finish(colors, 'continuingStreetOchre', (0.63, 0.48, 0.31), 0.82)
    for bay in band['windows']:
        lo, hi = bay['from'], bay['to']
        x, y = point((lo + hi) / 2, 0.09)
        for level in range(1, int(face['levels'])):
            mesh.box(
                x,
                y,
                z + (level + 0.12) * fh,
                (hi - lo) * length,
                0.12,
                0.55,
                finish_index,
                angle,
            )
        x, y = point(lo - 0.006, 0.19)
        mesh.box(
            x,
            y,
            z + (fh + face['height']) / 2,
            0.21,
            0.34,
            face['height'] - fh,
            colors['white'],
            angle,
        )
    return mesh
