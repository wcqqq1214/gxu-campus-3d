"""Exterior study of the West 22 residence, based on March 2019 street panoramas."""

from pathlib import Path

import bpy

from geometry import MATERIALS, Mesh, material
from west22_court import east_steps
from west22_storefront import cloth, shopfront

WEST22 = 'way/759140893'


def west22(b, z, colors, detail):
    ring = b['polygons'][0][0]
    length = max(x for x, y in ring) - min(x for x, y in ring)
    depth = max(y for x, y in ring) - min(y for x, y in ring)
    height = b['height']
    level = height / b['levels']
    bay = length / 18
    shell, roof, frontage, windows = Mesh(), Mesh(), Mesh(), Mesh()

    def finish(name, rgb, roughness=0.75, metal=0):
        key = 'west22' + name + ('' if detail else 'Base')
        if key not in colors:
            colors[key] = material(key, rgb, roughness, metal)
        return colors[key]

    tile = finish('Brick', (0.40, 0.177, 0.114))
    shadow = finish('Reveal', (0.171, 0.068, 0.043))
    ivory = finish('Ceramic', (0.73, 0.68, 0.60))
    pane = finish('StoreGlass', (0.055, 0.062, 0.052), 0.095, 0.77)
    pane_hi = finish('WindowGlass', (0.105, 0.132, 0.134), 0.27, 0.30)
    steel = finish('Steel', (0.235, 0.245, 0.237), 0.34, 0.47)
    concrete = finish('Concrete', (0.52, 0.47, 0.40))
    awning = finish('FabricRed', (0.49, 0.050, 0.054))
    blue = finish('GlassBlue', (0.045, 0.113, 0.21))
    frosted = finish('LowerGlass', (0.064, 0.060, 0.047), 0.33, 0.27)
    fan = finish('Fan', (0.19, 0.187, 0.172))

    def textured(key, image, roughness):
        mat = MATERIALS[key]
        if any(node.type == 'TEX_IMAGE' for node in mat.node_tree.nodes):
            return
        node = mat.node_tree.nodes.new('ShaderNodeTexImage')
        node.image = bpy.data.images.load(
            str(Path(__file__).parent / 'textures' / 'west22' / image),
            check_existing=True,
        )
        node.image.pack()
        shader = mat.node_tree.nodes.get('Principled BSDF')
        mat.node_tree.links.new(node.outputs['Color'], shader.inputs['Base Color'])
        shader.inputs['Roughness'].default_value = roughness

    grille = finish('Grille', (0.09, 0.11, 0.10), 0.40)
    linen = finish('CanopyLinen', (0.66, 0.63, 0.57), 0.91)
    frame = finish('DoorFrame', (0.050, 0.046, 0.040), 0.34, 0.55)
    rail = finish('AwningRail', (0.12, 0.11, 0.095), 0.42, 0.56)
    rubber = finish('EntryMat', (0.058, 0.032, 0.025))
    sticker = finish('SafetyRed', (0.25, 0.027, 0.019), 0.56)
    wall = finish('RetainingConcrete', (0.38, 0.29, 0.22))
    riser = finish('Riser', (0.33, 0.26, 0.19))
    if detail:
        textured(tile, 'brick.png', 0.78)
        textured(grille, 'grille.png', 0.42)
        textured(fan, 'ac.png', 0.71)
        textured(linen, 'canopy-cloth.jpg', 0.91)
        textured(awning, 'canopy-red.jpg', 0.9)
        textured(concrete, 'court-concrete.jpg', 0.88)
        textured(wall, 'retaining-concrete.jpg', 0.92)
        textured(riser, 'retaining-concrete.jpg', 0.90)

    def panel(mesh, x, y, z, w, h, mat, side):
        hw, hh = w / 2, h / 2
        corners = [
            (x - hw, y, z - hh),
            (x + hw, y, z - hh),
            (x + hw, y, z + hh),
            (x - hw, y, z + hh),
        ]
        uv = [(0, 0), (1, 0), (1, 1), (0, 1)]
        if side > 0:
            corners.reverse()
            uv.reverse()
        mesh.face(corners, mat, uv)

    pitch = level
    roof.box(
        length / 2, depth / 2, height + 0.07, length + 0.20, depth + 0.20, 0.14, ivory
    )
    shell.box(
        length / 2, depth / 2, (height + level) / 2, length, depth, height - level, tile
    )
    # Ground-floor glazing is behind the piers; the projecting floor has a real soffit.
    inset = 1.12
    for left, right, recess in (
        (2.9, 0.55 * length, inset),
        (0.55 * length, length - 2.9, 4.25),
    ):
        shell.box(
            (left + right) / 2,
            depth / 2,
            level / 2,
            right - left,
            depth - 2 * recess,
            level,
            tile,
        )
    for x in (1.45, length - 1.45):
        shell.box(x, depth / 2, level / 2, 2.90, depth, level, tile)

    for side, y in ((-1, 0), (1, depth)):
        fascia = y + side * 0.08
        frontage.box(
            length / 2, y - side * 0.48, level - 0.32, length - 5.8, 1.58, 0.45, tile
        )
        frontage.box(
            length / 2, y - side * 0.50, level - 0.08, length, 1.78, 0.16, ivory
        )
        for j in range(18):
            x = (j + 0.5) * bay
            frontage.box(
                x, y - side * 0.20, (level - 0.47) / 2, 0.70, 0.80, level - 0.47, tile
            )
        for row in range(1, round(b['levels'])):
            base = row * pitch
            windows.box(length / 2, fascia, base, length, 0.26, 0.17, ivory)
            for j in range(1, 18):
                cx = j * bay
                # Stair cores interrupt the banks of paired large and small windows.
                if j in (7, 12):
                    windows.box(
                        cx,
                        y + side * 0.035,
                        base + pitch / 2,
                        2.6,
                        0.09,
                        pitch - 0.18,
                        ivory,
                    )
                    windows.box(
                        cx, y + side * 0.10, base + 0.65, 2.52, 0.08, 1.0, pane_hi
                    )
                    continue
                windows.box(
                    cx,
                    y + side * 0.095,
                    base + pitch / 2,
                    0.30,
                    0.24,
                    pitch - 0.13,
                    ivory,
                )
                for sign in (-1, 1):
                    xx = cx + sign * 1.04
                    windows.box(
                        xx, y + side * 0.05, base + 1.92, 1.74, 0.13, 1.57, shadow
                    )
                    windows.box(
                        xx, y + side * 0.12, base + 1.93, 1.60, 0.055, 1.44, pane_hi
                    )
                    windows.box(
                        cx + sign * 2.78,
                        y + side * 0.045,
                        base + 2.29,
                        0.94,
                        0.105,
                        0.75,
                        pane_hi,
                    )
                    if detail:
                        panel(
                            windows,
                            xx,
                            y + side * 0.16,
                            base + 1.93,
                            1.60,
                            1.44,
                            grille,
                            side,
                        )
                        acx = cx + sign * 0.77
                        windows.box(
                            acx, y + side * 0.28, base + 0.72, 0.89, 0.52, 0.66, ivory
                        )
                        panel(
                            windows,
                            acx,
                            y + side * 0.549,
                            base + 0.72,
                            0.84,
                            0.62,
                            fan,
                            side,
                        )
                        if row <= 2 and side < 0:
                            for dx in (-0.32, 0.32):
                                windows.box(
                                    acx + dx,
                                    y - 0.27,
                                    base + 0.35,
                                    0.043,
                                    0.63,
                                    0.047,
                                    steel,
                                )
        if detail:
            for j in range(0, 18, 2):
                x = (j + 0.48) * bay
                windows.cylinder(
                    x,
                    y + side * 0.14,
                    (height + level) / 2,
                    0.056,
                    height - level,
                    ivory,
                    n=8,
                )
        if side < 0:
            shopfront(
                frontage,
                bay,
                y,
                (pane, frosted, frame, steel, tile, blue, sticker, rubber, shadow),
                True,
            )
            for center in (1.1 * bay, 3.5 * bay + 1.08):
                cloth(frontage, center, 0.86 * bay, awning, linen, rail)
            # Two stacked condenser fans to the east of the striped canopy, visible in both street views.
            acx = 4.23 * bay
            frontage.box(acx, 0.65, 0.77, 1.04, 0.59, 1.46, ivory)
            for zfan in (0.41, 1.09):
                panel(frontage, acx, 0.348, zfan, 0.92, 0.65, fan, -1)
            for x in (acx - 0.36, acx + 0.36):
                frontage.box(x, 0.66, 0.048, 0.12, 0.68, 0.096, steel)
            # Slender dark flashing caps the white fascia above the ground-floor windows.
            frontage.box(
                length / 2, -0.39, level + 0.05, length - 0.16, 0.095, 0.068, rail
            )
    for end, outward in ((0, -1), (length, 1)):
        for row in range(round(b['levels'])):
            for yy in (depth * 0.41, depth * 0.62):
                windows.box(
                    end + outward * 0.055,
                    yy,
                    row * pitch + 1.75,
                    0.12,
                    1.62,
                    1.51,
                    pane_hi,
                )
                if detail:
                    for k in range(-3, 4):
                        windows.box(
                            end + outward * 0.13,
                            yy + k * 0.21,
                            row * pitch + 1.75,
                            0.045,
                            0.028,
                            1.50,
                            steel,
                        )
            if row:
                windows.box(
                    end + outward * 0.03,
                    depth / 2,
                    row * pitch,
                    0.23,
                    depth + 0.1,
                    0.15,
                    ivory,
                )
        for x in [end - outward * 1.4]:
            panel(frontage, x, -0.075, 1.73, 1.7, 1.58, grille, -1)
    # The steps connect the raised courtyard to the lower east path.
    # This is a site stair, with no evidence of steps directly below the dining sign.
    east_steps(frontage, length, depth, concrete, wall, riser)
    m = Mesh()
    for name, part in [
        ('01_主体轮廓', shell),
        ('02_屋顶轮廓', roof),
        ('03_入口与平台', frontage),
        ('04_立面窗格', windows),
    ]:
        m.add_part(name, part)
    xmin, ymin = b['bounds'][:2]
    m.v = [(xmin + x, ymin + y, z + h) for x, y, h in m.v]
    return m
