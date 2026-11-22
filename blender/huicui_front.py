"""Photographed dining-floor windows and the north hotel lobby of Huicui."""

import math

from geometry import MATERIALS, Mesh, material
from south_gate import inscription


def finishes(colors):
    for name, rgb, rough, metal in (
        ('huiMirror', (0.105, 0.145, 0.14), 0.14, 0.51),
        ('huiBamboo', (0.20, 0.26, 0.065), 0.73, 0),
        ('huiLimestone', (0.66, 0.61, 0.50), 0.74, 0),
        ('huiJoint', (0.32, 0.30, 0.26), 0.77, 0),
        ('huiDiningGlass', (0.085, 0.14, 0.18), 0.18, 0.38),
        ('huiSash', (0.064, 0.078, 0.083), 0.40, 0.38),
        ('huiAluminium', (0.38, 0.41, 0.43), 0.37, 0.4),
        ('huiSoffit', (0.29, 0.30, 0.30), 0.54, 0.23),
        ('huiPortal', (0.055, 0.059, 0.06), 0.29, 0.31),
        ('huiColumn', (0.76, 0.67, 0.48), 0.60, 0),
        ('huiGranite', (0.54, 0.51, 0.46), 0.28, 0.08),
        ('huiRiser', (0.38, 0.35, 0.32), 0.54, 0.03),
        ('huiTimber', (0.37, 0.17, 0.09), 0.47, 0.05),
        ('huiLobbyLight', (0.95, 0.79, 0.55), 0.46, 0.03),
        ('huiEtch', (0.57, 0.60, 0.58), 0.44, 0.20),
    ):
        if name not in colors:
            colors[name] = material(name, rgb, rough, metal)
    light = MATERIALS[colors['huiLobbyLight']].node_tree.nodes['Principled BSDF']
    light.inputs['Emission Color'].default_value = (0.96, 0.65, 0.32, 1)
    light.inputs['Emission Strength'].default_value = 0.45
    if 'huiDoorGlass' not in colors:
        idx = material('huiDoorGlass', (0.34, 0.40, 0.37), 0.13, 0.25)
        colors['huiDoorGlass'] = idx
        mat = MATERIALS[idx]
        mat.diffuse_color = (0.34, 0.40, 0.37, 0.18)
        mat.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = 0.18


def dining_windows(north, yn, z, colors, detail):
    c = colors
    # Coordinates run from east to west as seen from the lawn. Between the end
    # lights the sixteen larger openings share a regular four-metre pitch.
    bays = [(34.03, 1.54)]
    bays.extend((30.02 - 3.969 * i, 2.35) for i in range(8))
    bays.extend((-1.76 - 4.018 * i, 2.41) for i in range(8))
    bays.extend([(-35.09, 0.75), (-36.69, 0.75)])
    north.box(0, yn + 0.012, z + 27.825, 83.63, 0.12, 6.55, c['huiLimestone'])
    for x, w in bays:
        lo, hi = 25.23, 28.78
        h = hi - lo
        for end in (-1, 1):
            north.box(
                x + end * (w / 2 + 0.020),
                yn + 0.105,
                z + (hi + lo) / 2,
                0.065,
                0.095,
                h + 0.10,
                c['huiSash'],
            )
        north.box(x, yn + 0.100, z + (hi + lo) / 2, w, 0.052, h, c['huiDiningGlass'])
        for v in (lo, hi, lo + h * 0.54, lo + h * 0.77):
            north.box(x, yn + 0.148, z + v, w + 0.05, 0.065, 0.052, c['huiSash'])
        if detail and w > 1.8:
            north.box(x, yn + 0.144, z + (hi + lo) / 2, 0.051, 0.068, h, c['huiSash'])
        if detail and x in (bays[0][0], bays[2][0], bays[7][0], bays[14][0]):
            # Bottom edge of the open awning sash tilts toward the lawn.
            a, b = x - w / 2 + 0.06, x - 0.03 if w > 1.8 else x + w / 2 - 0.06
            corners = [
                (a, yn + 0.34, z + 26.05),
                (b, yn + 0.34, z + 26.05),
                (b, yn + 0.16, z + 27.14),
                (a, yn + 0.16, z + 27.14),
            ]
            north.face(corners[::-1], c['huiDiningGlass'])
            for a0, b0 in zip(corners, corners[1:] + corners[:1]):
                north.line(a0, b0, 0.024, c['huiSash'])
    if detail:
        for j in range(1, 52):
            x = -41.815 + j * 1.61
            for lo, hi in ((24.55, 25.22), (28.84, 31.10)):
                north.box(
                    x,
                    yn + 0.077,
                    z + (lo + hi) / 2,
                    0.016,
                    0.018,
                    hi - lo,
                    c['huiJoint'],
                )
        for zz in (25.22, 28.83, 30.01):
            north.box(0, yn + 0.078, z + zz, 83.61, 0.018, 0.017, c['huiJoint'])


def hotel_lobby(yn, z, c, detail):
    g = Mesh()

    def box(x, out, level, width, depth, height, finish):
        g.box(x, yn + out, z + level, width, depth, height, c[finish])

    # The paired round supports are behind the front lip, partway back to the doors.
    width, front, back, soffit, fascia = 11.48, 2.61, -4.20, 5.57, 0.99
    middle = (front + back) / 2
    for y in (front, back):
        box(0, y, soffit + fascia / 2, width, 0.08, fascia, 'huiAluminium')
    for x in (-width / 2, width / 2):
        box(x, middle, soffit + fascia / 2, 0.08, front - back, fascia, 'huiAluminium')
    box(0, middle, soffit + 0.06, width, front - back, 0.12, 'huiSoffit')
    box(
        0,
        middle,
        soffit + fascia + 0.025,
        width + 0.13,
        front - back + 0.13,
        0.07,
        'huiAluminium',
    )
    for x in (-4.32, 4.32):
        g.cylinder(
            x,
            yn - 1.79,
            z + (soffit + 0.58) / 2,
            0.492,
            soffit - 0.58,
            c['huiColumn'],
            32 if detail else 16,
        )
        g.cylinder(
            x, yn - 1.79, z + 0.68, 0.59, 0.20, c['huiGranite'], 28 if detail else 12
        )
    if detail:
        for j in range(1, 9):
            x = -width / 2 + width * j / 9
            box(
                x, front + 0.045, soffit + fascia / 2, 0.016, 0.016, fascia, 'huiPortal'
            )
            box(x, middle, soffit - 0.006, 0.016, front - back, 0.014, 'huiPortal')
        for j in range(1, 5):
            box(
                0,
                back + (front - back) * j / 5,
                soffit - 0.006,
                width,
                0.016,
                0.014,
                'huiPortal',
            )
        for x in (-4.15, -2.1, 0, 2.1, 4.15):
            for y in (-3.05, -1.3, 0.45, 2.1):
                g.cylinder(
                    x, yn + y, z + soffit - 0.017, 0.053, 0.025, c['huiLobbyLight'], 12
                )
    box(0, -0.01, 7.34, 9.2, 0.18, 1.56, 'huiTimber')
    if detail:
        for j in range(80):
            box(-4.54 + j * 0.115, 0.115, 7.34, 0.043, 0.095, 1.55, 'huiTimber')
    # Four folded links form the white emblem centred above the canopy.
    for i in range(4):
        ang = i * math.pi / 2
        points = [(0, 0.79), (0.60, 0.49), (0.60, 0.05), (0.26, -0.14), (0.02, 0.04)]
        pts = [
            (
                x * math.cos(ang) - h * math.sin(ang),
                yn + 0.22,
                z + 7.34 + x * math.sin(ang) + h * math.cos(ang),
            )
            for x, h in points
        ]
        for a, b in zip(pts, pts[1:]):
            g.line(a, b, 0.057, c['white'], 6)
    for text, x, level, w, h in [
        ('荟萃楼', -3.07, 6.05, 1.80, 0.61),
        ('HUI', -4.22, 6.25, 0.45, 0.18),
        ('CUI', -4.22, 6.05, 0.45, 0.18),
        ('LOU', -4.22, 5.85, 0.45, 0.18),
    ]:
        letters = inscription(
            text, 0, 0, z + level, w, h, c['white'], False, flat=not detail
        )
        letters.rotate_z(0, 0, math.pi)
        letters.v = [(xx + x, yy + yn + front + 0.07, v) for xx, yy, v in letters.v]
        g.extend(letters)

    # Fixed sidelights and two partially open sliding leaves below a glazed transom.
    half, low, head, bar = 3.78, 0.58, 5.31, 3.73
    for x in (-half - 0.135, half + 0.135):
        box(x, -4.02, (head + low) / 2, 0.27, 0.29, head - low, 'huiPortal')
    box(0, -4.02, 5.46, 8.10, 0.32, 0.30, 'huiPortal')
    box(0, -4.02, bar, 2 * half, 0.25, 0.36, 'huiAluminium')
    for j in range(6):
        l = -half + j * (2 * half) / 6
        box(
            l + half / 6,
            -4.04,
            (head + bar) / 2,
            half / 3 - 0.042,
            0.055,
            head - bar - 0.16,
            'huiDoorGlass',
        )
        box(l, -3.97, (head + bar) / 2, 0.063, 0.085, head - bar, 'huiPortal')
    for sign in (-1, 1):
        for outer, inner, out in ((half, 2.16, -4.01), (2.78, 0.95, -3.88)):
            x = sign * (outer + inner) / 2
            box(
                x,
                out,
                (bar + low) / 2,
                outer - inner,
                0.052,
                bar - low - 0.16,
                'huiDoorGlass',
            )
            for edge in (inner, outer):
                box(
                    sign * edge,
                    out + 0.045,
                    (bar + low) / 2,
                    0.035,
                    0.063,
                    bar - low - 0.14,
                    'huiAluminium',
                )
            box(x, out + 0.05, 1.77, outer - inner, 0.02, 0.15, 'huiEtch')
    box(0, -6.1, 0.55, 8.10, 4.15, 0.055, 'huiGranite')
    box(0, -6.1, 5.29, 8.10, 4.15, 0.10, 'huiLobbyLight')
    box(0, -7.92, 2.62, 7.27, 0.075, 4.13, 'huiTimber')
    for x in (-2.9, -1.15, 1.15, 2.9):
        box(x, -7.82, 2.35, 1.10, 0.06, 2.93, 'huiLimestone')
    if detail:
        for x in (-2.84, 2.84):
            for h in (1.04, 2.02, 3.02, 4.05):
                box(x, -7.76, h, 1.15, 0.05, 0.035, 'huiLobbyLight')
        box(0, -7.75, 2.91, 1.83, 0.12, 1.24, 'huiLobbyLight')
        box(0, -7.66, 2.91, 1.62, 0.06, 1.06, 'huiTimber')
    # Shallow broad treads across the forecourt, with a sloping outer apron meeting the DEM.
    for out, top, finish in [(3.99, 0.39, 'huiRiser'), (3.80, 0.58, 'huiGranite')]:
        box(0, out / 2, (top - 1.22) / 2, 36.8, out, top + 1.22, finish)
        box(0, out - 0.02, top - 0.022, 36.83, 0.12, 0.045, 'huiGranite')
    g.face(
        [
            (-18.4, yn + 7.25, z - 0.45),
            (-18.4, yn + 3.99, z + 0.20),
            (18.4, yn + 3.99, z + 0.20),
            (18.4, yn + 7.25, z - 0.45),
        ],
        c['huiRiser'],
    )
    return g


def lobby_side_glazing(arcade, yn, z, c, detail):
    for side in (-1, 1):
        x = side * 8.17
        # The broad display windows extend to the sides of the portal beneath
        # one continuous metal transom. The planted troughs stand in front of them.
        arcade.box(x, yn - 3.90, z + 3.80, 8.48, 0.085, 6.40, c['huiMirror'])
        arcade.box(x, yn - 3.73, z + 5.68, 8.51, 0.25, 0.54, c['huiAluminium'])
        if not detail:
            continue
        for dx in (-4.21, -2.1, 0, 2.1, 4.21):
            arcade.box(x + dx, yn - 3.82, z + 3.75, 0.022, 0.045, 6.3, c['huiSash'])
        arcade.box(x, yn - 3.50, z + 0.78, 8.14, 0.48, 0.40, c['huiPortal'])
        for i in range(34):
            v = i * 2.39996
            stem = x - 3.85 + i * 0.233
            h = 0.86 + 0.52 * (1 + math.cos(v * 0.59))
            lean = 0.11 * math.sin(v)
            yy = yn - 3.48 + 0.105 * math.cos(v)
            arcade.line(
                (stem, yy, z + 0.98),
                (stem + lean, yy, z + 0.98 + h),
                0.012,
                c['huiBamboo'],
                5,
            )
            for j in range(4):
                t = 0.43 + j * 0.17
                a = stem + lean * t
                zz = z + 0.98 + h * t
                d = (-1 if (i + j) % 2 else 1) * (0.13 + 0.09 * math.cos(v + j))
                arcade.face(
                    [
                        (a, yy, zz),
                        (a + d * 0.55, yy + 0.026, zz + 0.12),
                        (a + d, yy + 0.045, zz + 0.13),
                        (a + d * 0.52, yy + 0.014, zz + 0.045),
                    ],
                    c['huiBamboo'],
                )
