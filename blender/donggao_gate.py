"""Donggao Gate pavilion facing Xiuling Road, based on the July 2023 street views."""

import math

from geometry import Mesh


def build(l, b, z, C, detail):
    x, y = l['center']
    mesh = Mesh()
    mesh.box(x, y, z + 0.15, 3.65, 1.65, 0.30, C['stone'])

    # The canopy overhangs the window enclosure. The street end has a
    # separate light transom below the shallow metal fascia.
    cx, cy = x + 0.22, y - 0.04
    mesh.box(cx, cy, z + 0.68, 2.56, 1.34, 0.76, C['paleRoof'])
    mesh.box(cx, cy, z + 2.005, 2.54, 1.32, 1.89, C['dark'])
    for side in (-1, 1):
        mesh.box(cx, cy + side * 0.665, z + 1.98, 2.46, 0.035, 1.72, C['wood'])
        mesh.box(cx + side * 1.275, cy, z + 1.92, 0.035, 1.25, 1.60, C['wood'])
        if detail:
            for station in (-1.22, -0.41, 0.41, 1.22):
                mesh.box(
                    cx + station,
                    cy + side * 0.69,
                    z + 1.98,
                    0.045,
                    0.035,
                    1.74,
                    C['dark'],
                )
            mesh.box(cx, cy + side * 0.69, z + 1.09, 2.55, 0.05, 0.06, C['metal'])
    mesh.box(cx + 1.29, cy, z + 2.79, 0.055, 1.27, 0.32, C['paleRoof'])
    mesh.box(cx, cy, z + 3.065, 2.84, 1.54, 0.23, C['metal'])

    # Keep the projecting top rim visible against the blank display face.
    mesh.box(x + 1.47, y + 0.01, z + 3.68, 0.14, 1.30, 1.00, C['dark'])
    if detail:
        mesh.box(x + 1.546, y + 0.01, z + 3.68, 0.016, 1.24, 0.89, C['wood'])
    mesh.box(x + 1.47, y + 0.01, z + 4.155, 0.16, 1.32, 0.05, C['metal'])
    mesh.rotate_z(x, y, math.radians(15))
    return mesh
