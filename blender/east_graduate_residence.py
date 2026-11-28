"""Exposed structural frame of the graduate residence seen during topping out."""

import math

from geometry import Mesh
from humanities_facades import finish

IDS = {'east-campus/graduate-residence-1'}


def build(b, z, colors, detail):
    frame = b['graduateFrame']
    concrete = finish(colors, 'graduateFrameConcrete', (0.49, 0.42, 0.36), 0.91)
    interior = finish(colors, 'graduateFrameInterior', (0.13, 0.12, 0.11), 0.94)
    screen = finish(colors, 'graduateFrameScreen', (0.075, 0.21, 0.30), 0.85)
    mesh = Mesh()
    pitch = b['height'] / b['levels']
    for left, bottom, right, top, floors in frame['volumes']:
        x, y = (left + right) / 2, (bottom + top) / 2
        width, depth = right - left, top - bottom
        height = floors * pitch
        mesh.box(x, y, height / 2, width - 2.4, depth - 2.4, height, interior)
        # Open bays continue between the floor plates. Narrow end walls reveal
        # a smaller opening than the repeated bays along the long faces.
        for x_side in (left + 0.22, right - 0.22):
            if depth > width:
                bays = round(depth / 3.65)
                for i in range(bays + 1):
                    v = bottom + 0.22 + i * (depth - 0.44) / bays
                    mesh.box(x_side, v, height / 2, 0.44, 0.48, height, concrete)
                continue
            for side in (-1, 1):
                jamb = depth * 0.32
                mesh.box(
                    x_side,
                    y + side * (depth - jamb) / 2,
                    height / 2,
                    0.44,
                    jamb,
                    height,
                    concrete,
                )
        bays = max(2, round(width / 3.65))
        for y_side in (bottom + 0.22, top - 0.22):
            for i in range(bays + 1):
                u = left + 0.22 + i * (width - 0.44) / bays
                mesh.box(u, y_side, height / 2, 0.48, 0.44, height, concrete)
        for n in range(1, floors + 1):
            mesh.box(x, y, n * pitch - 0.28, width, depth, 0.56, concrete)
        # Temporary perimeter screens visible at the heads of both wings
        # and the lower link in the two 2026 construction photographs.
        band = 3 * pitch
        mesh.box(x, y, height - band / 2, width + 0.14, depth + 0.14, band, screen)
        if detail:
            for side in (-1, 1):
                for bay in range(1, bays):
                    u = left + bay * width / bays
                    mesh.box(
                        u,
                        y + side * (depth / 2 + 0.085),
                        height - band / 2,
                        0.06,
                        0.05,
                        band,
                        colors['metal'],
                    )
    ox, oy = frame['origin']
    angle = math.radians(frame['rotationDegrees'])
    c, s = math.cos(angle), math.sin(angle)
    mesh.v = [(ox + c * x - s * y, oy + s * x + c * y, z + h) for x, y, h in mesh.v]
    result = Mesh()
    result.add_part('01_主体轮廓', mesh)
    return result
