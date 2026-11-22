"""West 23 north-west arcade. X points west along the street-facing wall."""

from pathlib import Path

import bpy
from mathutils import Vector

from geometry import MATERIALS, Mesh, material

TEX = Path(__file__).parent / 'textures'
FACADE_TEXTURES = TEX / 'west23'
WEST23 = 'way/759140894'
BAY = 6.5


def west23(building, elevation, colors, detail):
    shell, roof, front, windows = Mesh(), Mesh(), Mesh(), Mesh()
    m = shell

    def paint(n, c, r=0.7, metal=0, texture=None):
        key = 'w23-' + n + ('' if detail else '-base')
        if key in colors:
            return colors[key]
        i = colors[key] = material(key, c, r, metal)
        if texture and detail:
            mat = MATERIALS[i]
            nt = mat.node_tree
            node = nt.nodes.new('ShaderNodeTexImage')
            node.image = bpy.data.images.load(str(texture), check_existing=True)
            node.image.pack()
            nt.links.new(
                node.outputs['Color'], nt.nodes['Principled BSDF'].inputs['Base Color']
            )
        return i

    brick = paint(
        'face-brick', (0.40, 0.18, 0.12), texture=FACADE_TEXTURES / 'masonry.jpg'
    )
    base = paint('dark-red-skirting', (0.14, 0.059, 0.04))
    cream = paint('tile', (0.68, 0.62, 0.5))
    trim = paint('coping', (0.055, 0.043, 0.033))
    glass = paint(
        'store-glass',
        (0.045, 0.052, 0.045),
        0.22,
        0.19,
        texture=FACADE_TEXTURES / 'glazing.jpg',
    )
    lower = paint('lower-glass', (0.063, 0.062, 0.050), 0.30, 0.24)
    steel = paint('aluminium', (0.36, 0.35, 0.32), 0.28, 0.65)
    frame = paint('jamb', (0.048, 0.04, 0.034), 0.47, 0.35)
    plaster = paint('soffit', (0.63, 0.55, 0.44))
    black = paint('recess', (0.041, 0.029, 0.022))
    blue = paint('blue', (0.018, 0.050, 0.17))
    red = paint('red', (0.30, 0.027, 0.020))
    white = paint('film', (0.67, 0.64, 0.61))
    rubber = paint('mat', (0.103, 0.035, 0.024), texture=FACADE_TEXTURES / 'mat.jpg')
    door = paint('service-door', (0.081, 0.035, 0.026))
    grille = paint('bars', (0.08, 0.095, 0.09), texture=TEX / 'west22' / 'grille.png')
    fan = paint('fan', (0.20, 0.20, 0.17), texture=FACADE_TEXTURES / 'condenser.png')
    dualfan = paint(
        'twin-condenser-cover',
        (0.36, 0.32, 0.24),
        texture=FACADE_TEXTURES / 'double-fan.png',
    )
    cement = paint('court', (0.50, 0.43, 0.365), texture=FACADE_TEXTURES / 'apron.jpg')
    wsign = paint('address', (0.61, 0.55, 0.52), texture=FACADE_TEXTURES / 'wall.png')
    board = paint('stand', (0.47, 0.05, 0.034), texture=FACADE_TEXTURES / 'board.png')
    wifi = paint('wlan', (0.65, 0.63, 0.58), texture=FACADE_TEXTURES / 'wifi.png')
    cornice = paint(
        'fluted-edge', (0.5, 0.45, 0.4), texture=FACADE_TEXTURES / 'cornice.jpg'
    )
    paintline = paint('pavement-marking', (0.48, 0.444, 0.35))
    poster = paint('printed-notice', (0.39, 0.35, 0.31))
    leaf = paint('glass-leaf', (0.17, 0.16, 0.14), 0.11, 0.19)
    MATERIALS[leaf].node_tree.nodes['Principled BSDF'].inputs[
        'Alpha'
    ].default_value = 0.21

    def panel(x0, x1, y, z0, z1, mat):
        m.face(
            [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)],
            mat,
            [(0, 0), (1, 0), (1, 1), (0, 1)],
        )

    def rect(x0, x1, y0, y1, z0, z1, mat):
        m.box(
            (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2, x1 - x0, y1 - y0, z1 - z0, mat
        )

    def badge(cx, at, z, w, h, mat):
        panel(cx - w / 2, cx + w / 2, at, z - h / 2, z + h / 2, mat)

    # Wing ends are recessed behind the long brick arcade.
    xmin, _, xmax, ymax = building['bounds']
    right = 6.3
    left = right - (xmax - xmin)
    depth = 15.82
    h = building['height']
    rect(left, right, 1.65, depth - 0.5, 3.53, h, brick)
    rect(left + 3, 3, -0.16, depth - 0.70, 3.53, h - 0.03, brick)
    rect(left, 0, 1.65, depth - 0.50, -0.08, 3.53, brick)
    rect(3, right, 1.65, depth - 0.50, -0.08, 3.53, brick)
    rect(0, 3, 5.25, depth - 0.50, -0.08, 3.53, brick)
    rect(0.00, 0.12, 0.68, 5.25, 0, 2.54, base)
    rect(2.88, 3, 1.65, 5.25, 0, 2.54, base)
    rect(-5 * BAY, 0, 1.51, 1.53, 0, 2.61, black)
    rect(0, 3, 5.21, 5.25, 0, 2.70, black)
    rect(0, 3, 1.60, 1.68, 2.54, 3.55, brick)
    rect(left, 0, 1.61, 1.65, 0, 0.48, base)
    rect(3, right, 1.61, 1.65, 0, 0.62, base)
    m = roof
    rect(left + 0.06, right - 0.06, 1.63, depth - 0.50, h, h + 0.12, cream)
    m = windows
    for level in range(1, 8):
        z = 3.53 + (level - 1) * (h - 3.53) / 7
        rect(left + 3, 3.10, -0.27, 0.02, z - 0.13, z + 0.08, cream)
        rect(left + 3, 3.10, -0.28, -0.21, z + 0.06, z + 0.11, trim)
        rect(3, right + 0.10, 1.47, 1.73, z - 0.13, z + 0.08, cream)
        rect(3, right + 0.10, 1.46, 1.57, z + 0.06, z + 0.11, trim)
        rect(2.97, 3.13, -0.25, 1.58, z - 0.13, z + 0.08, cream)
        rect(left + 3, 3.10, -0.29, 0.0, z - 0.23, z + 0.02, cornice)
        rect(3, right + 0.1, 1.45, 1.73, z - 0.23, z + 0.02, cornice)
        rect(2.98, 3.13, -0.28, 1.58, z - 0.23, z + 0.02, cornice)
        rect(left + 3, 3.10, -0.245, 0.02, z - 0.40, z - 0.23, cornice)
        rect(3, right + 0.1, 1.495, 1.73, z - 0.40, z - 0.23, cornice)
        rect(2.98, 3.09, -0.25, 1.58, z - 0.40, z - 0.23, cornice)
        rect(left + 3, 3.10, -0.25, -0.20, z - 0.41, z - 0.387, trim)
        for j in range(20):
            x = -(j + 0.5) * BAY - 0.31
            if x < left + 3.6:
                continue
            for s in (-1, 1):
                xx = x + 0.88 * s
                badge(xx, -0.172, z + 1.72, 1.49, 1.70, grille)
                badge(x + s * 2.43, -0.174, z + 2.13, 0.88, 0.70, glass)
                if not detail:
                    continue
                ac = x + s * 0.84
                m.box(ac, -0.38, z + 1.03, 1.09, 0.54, 0.86, cream)
                badge(ac, -0.66, z + 1.03, 1.04, 0.82, fan)
                for dx in (-0.34, 0.34):
                    m.box(ac + dx, -0.40, z + 0.56, 0.055, 0.67, 0.055, frame)
            m.box(x, -0.18, z + 1.59, 0.28, 0.09, 3.03, cream)
    # Window and condenser above the passage on the west return.
    for lev in range(1, 8):
        sill = 3.53 + (lev - 1) * (h - 3.53) / 7
        badge(1.5, -0.173, sill + 2.08, 2.05, 1.67, grille)
        badge(-0.42, -0.174, sill + 1.92, 0.88, 0.75, glass)
        m.box(1.84, -0.48, sill + 1.10, 1.11, 0.6, 0.78, cream)
        badge(1.84, -0.79, sill + 1.10, 1.05, 0.74, fan)
        for u in (1.47, 2.25):
            m.box(u, -0.48, sill + 0.48, 0.04, 0.68, 0.05, steel)
    m = front
    # Silver strip below the tiled brick lintel recedes over each bay.
    rect(left + 3, 3.03, -0.22, 0.92, 2.48, 3.43, brick)
    rect(left + 3, 3.04, -0.22, 0.92, 2.47, 2.52, plaster)
    for j in range(5):
        center = -(j + 0.5) * BAY - 0.14
        rect(center - 2.20, center + 2.20, -0.32, 0.86, 2.46, 2.66, steel)
        rect(center - 2.20, center + 2.20, -0.34, -0.30, 2.45, 2.47, frame)
    for j in range(20):
        x = -j * BAY
        if x < left + 3.5:
            continue
        rect(x - 0.35, x + 0.35, 0, 0.64, 0, 2.54, brick)
        if j < 6:
            rect(x - 0.36, x + 0.36, -0.012, 0.65, 0, 0.55, base if j == 0 else brick)
    for x in (3.14, 3.34):
        m.cylinder(x, 1.49, 1.76, 0.055, 3.52, cream, n=12)
        m.box(x, 0.65, 3.48, 0.10, 1.71, 0.10, cream)
    # Drainpipes and the return elbow beside the second doorway are visible from the yard.
    for j in (2, 6, 10, 14):
        u = -j * BAY + 1.22
        m.cylinder(u, -0.28, (h + 2.5) / 2, 0.092, h - 2.5, cream, n=16)
        m.box(u, -0.01, 2.50, 0.19, 0.57, 0.18, cream)
    # Floor and threshold form a single street-level approach, with a thin door mat.
    rect(left - 1, right + 1.2, -7.4, depth - 0.50, -0.075, 0, cement)
    for j in range(5):
        l0 = -(j + 1) * BAY
        rect(l0 + 0.05, l0 + BAY - 0.11, -0.87, -0.84, 0.001, 0.004, paintline)
        a = -(j + 1) * BAY + 0.35
        b = -j * BAY - 0.35
        # The pair of mat-marked entrances flank a brick pier.
        spans = [(a, b, False)]
        if j == 2:
            spans = [(a, -15.21, False), (-15.21, -13.21, True)]
        if j == 1:
            spans = [(-12.53, a + 1.98, True), (a + 1.98, b, False)]
        if j == 4:
            spans = [(a, a + 2.04, True), (a + 2.04, b, False)]
        for l, r, isdoor in spans:
            cx = (l + r) / 2
            if not isdoor:
                panel(l, r, 0.82, 0.24, 2.36, glass)
            for x in (l, r):
                m.box(x, 0.787, 1.19, 0.034, 0.048, 2.32, frame)
            if isdoor:
                rect(l - 0.02, r + 0.02, 0.285, 1.50, 2.365, 2.47, frame)
                for x in (l, r):
                    rect(x - 0.018, x + 0.018, 0.285, 0.82, 0.02, 2.365, frame)
                rect(l, r, 0.29, 1.52, 0.001, 0.016, black)
                # Shallow exterior reveal and a pair of glass leaves with silver pull handles.
                for xx, dx in ((l, 1), (r, -1)):
                    edge = xx + dx * 0.16
                    end = xx + dx * 0.03
                    m.face(
                        [
                            (end, 0.05, 0.032),
                            (edge, 0.80, 0.032),
                            (edge, 0.80, 2.34),
                            (end, 0.05, 2.34),
                        ],
                        leaf,
                    )
                    m.box(end, 0.08, 1.17, 0.014, 0.022, 2.27, steel)
                    m.box(xx + dx * 0.07, 0.35, 0.95, 0.026, 0.030, 0.63, steel)
                    for hh in (0.67, 1.23):
                        m.box(xx + dx * 0.055, 0.38, hh, 0.047, 0.10, 0.024, steel)
                rect(l, r, 0.79, 0.85, 0.002, 0.017, steel)
                if j == 2:
                    matpts = [
                        (-15.15, -1.058),
                        (-13.475, -0.986),
                        (-13.217, 0.36),
                        (-15.177, 0.282),
                    ]
                elif j == 1:
                    matpts = [
                        (-12.55, -0.766),
                        (-10.61, -0.78),
                        (-10.61, 0.46),
                        (-12.55, 0.18),
                    ]
                else:
                    matpts = [
                        (l - 0.09, -0.84),
                        (r + 0.08, -0.84),
                        (r + 0.08, 0.74),
                        (l - 0.09, 0.74),
                    ]
                m.face(
                    [(x, y, 0.021) for x, y in matpts],
                    rubber,
                    [(0, 0), (1, 0), (1, 1), (0, 1)],
                )
            else:
                rect(l, r, 0.80, 0.94, 0, 0.24, brick)
                panel(l + 0.017, r - 0.017, 0.814, 0.248, 0.89, lower)
                for z, ht, mat in [
                    (1.28, 0.087, blue),
                    (1.17, 0.092, red),
                    (1.025, 0.145, white),
                ]:
                    panel(l + 0.015, r - 0.015, 0.802, z - ht / 2, z + ht / 2, mat)
                # Whole printed band outline, across the unobscured part of the pane.
                if j == 0:
                    panel(-0.91, -0.45, 0.777, 0.06, 0.90, red)
                if j == 2:
                    badge(r - 0.62, 0.78, 1.54, 0.48, 0.36, poster)
                # Repeated divisions on the narrow printed safety strip.
                n = max(1, round((r - l) / 1.12))
                for k in range(n):
                    u = l + (k + 0.5) * (r - l) / n
                    for n0 in range(8):
                        xx = u - 0.43 + n0 * 0.105
                        if l + 0.03 < xx < r - 0.03:
                            badge(xx, 0.797, 1.025, 0.058, 0.026, red)
        x = a + 0.64 if j in (0, 2) else b - 0.62
        if j == 1:
            x = b - 0.63
        rect(x - 0.51, x + 0.51, 0.24, 0.82, 0.065, 1.55, cream)
        for zfan in (0.466, 1.145):
            badge(x, -0.001 + 0.24, zfan, 0.92, 0.67, dualfan)
        for s in (-1, 1):
            m.box(x + s * 0.37, 0.52, 0.045, 0.10, 0.64, 0.09, steel)
    # West passage and the two signs are separate exterior elements.

    badge(5.145, 1.616, 2.24, 0.641, 0.453, wsign)
    badge(5.864, 1.612, 2.225, 0.418, 0.342, wifi)

    # Measured orientation of the portable notice; the hinge and both feet follow
    # the panel normal rather than an axis of the building.
    corners = [
        Vector(v)
        for v in [
            (-0.656, -0.587, 0.576),
            (-0.032, -0.550, 0.566),
            (-0.031, -0.344, 1.362),
            (-0.655, -0.380, 1.372),
        ]
    ]
    m.face([tuple(v) for v in corners], board, [(0, 0), (1, 0), (1, 1), (0, 1)])
    for foot, hinge in ((corners[0], corners[3]), (corners[1], corners[2])):
        bottom = hinge + (foot - hinge) * (hinge.z / (hinge.z - foot.z))
        back = bottom.copy()
        back.y = hinge.y + 0.14
        for tip in (bottom, back):
            axis = hinge - tip
            rotation = axis.to_track_quat('Z', 'Y')
            legs = Mesh()
            legs.box(0, 0, 0, 0.028, 0.032, axis.length, steel)
            legs.v = [tuple((hinge + tip) / 2 + rotation @ Vector(pt)) for pt in legs.v]
            m.extend(legs)
        m.box(
            bottom.x,
            (bottom.y + back.y) / 2,
            0.024,
            0.033,
            abs(bottom.y - back.y) + 0.05,
            0.048,
            steel,
        )
    # Other north bays show barred windows and solid access doors.
    for j in range(6, 19):
        cx = -(j - 0.5) * BAY
        if j % 3 == 0:
            rect(cx - 0.68, cx + 0.68, 1.57, 1.68, 0, 2.15, door)
        else:
            badge(cx, 1.57, 1.65, 2.6, 1.12, grille)
    result = Mesh()
    for name, part in [
        ('01_主体轮廓', shell),
        ('02_屋顶轮廓', roof),
        ('03_入口与平台', front),
        ('04_立面窗格', windows),
    ]:
        result.add_part(name, part)
    # Retain the accepted facade's local metre-based texture projection.
    for i, face in enumerate(result.f):
        if i in result.face_uvs or not detail:
            continue
        vs = [Vector(result.v[k]) for k in face]
        normal = (vs[1] - vs[0]).cross(vs[2] - vs[0])
        axis = max(range(3), key=lambda j: abs(normal[j]))
        u, v = [j for j in range(3) if j != axis]
        result.face_uvs[i] = [(q[u] / 4, q[v] / 4) for q in vs]
    result.v = [(xmin + right - u, ymax - v, elevation + z) for u, v, z in result.v]
    return result
