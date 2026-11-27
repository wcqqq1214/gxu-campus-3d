"""Donggao Gate pavilion, facing Xiuling Road. Local X follows the entrance road."""

import math

from geometry import Mesh


def build(l, b, z, C, detail):
    x, y = l['center']
    mesh = Mesh()
    mesh.box(x, y, z + 0.15, 3.65, 1.65, 0.30, C['stone'])
    mesh.box(x, y, z + 0.68, 3.15, 1.48, 0.76, C['paleRoof'])
    mesh.box(x, y, z + 1.94, 3.12, 1.46, 1.76, C['dark'])
    for side in (-1, 1):
        mesh.box(x, y + side * 0.74, z + 1.93, 3.01, 0.035, 1.59, C['wood'])
        mesh.box(x + side * 1.57, y, z + 1.93, 0.035, 1.31, 1.59, C['wood'])
        if detail:
            for station in (-1.49, -0.50, 0.50, 1.49):
                mesh.box(
                    x + station, y + side * 0.77, z + 1.93, 0.055, 0.04, 1.67, C['dark']
                )
            mesh.box(x, y + side * 0.77, z + 1.08, 3.15, 0.07, 0.07, C['metal'])
    mesh.box(x, y, z + 2.99, 3.55, 1.68, 0.34, C['metal'])
    mesh.box(x + 1.43, y, z + 3.67, 0.14, 1.38, 1.02, C['dark'])
    mesh.rotate_z(x, y, math.radians(15))
    return mesh
