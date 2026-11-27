"""Stone entrance piers at the north edge of the West Campus tennis courts."""

from geometry import Mesh


def build(l, b, z, C, detail):
    x, y = l['center']
    mesh = Mesh()
    stone, cap = C['stone'], C['stoneCool']
    for side in (-1, 1):
        pier = Mesh()
        cx = x + side * 5.85
        pier.box(cx, y, z + 1.54, 0.99, 1.01, 3.48, cap)
        pier.box(cx, y, z + 3.40, 1.34, 1.30, 0.24, cap)
        for course in range(3):
            pier.box(
                cx, y, z - 0.20 + (course + 0.5) * 0.36, 1.005, 1.035, 0.355, stone
            )
        # Lower rough-faced shoulders flank the tall smooth central panel.
        for offset in (-0.73, 0.73):
            sx = cx + offset
            if detail:
                for course in range(8):
                    pier.box(
                        sx,
                        y,
                        z - 0.20 + (course + 0.5) * 0.376,
                        0.49,
                        1.09,
                        0.37,
                        stone,
                    )
            else:
                pier.box(sx, y, z + 1.30, 0.49, 1.09, 3.00, stone)
        mesh.add_part('西石柱' if side < 0 else '东石柱', pier)
        wall = Mesh()
        start = cx + side * 0.975
        wall.box(start + side * 2.7, y, z + 0.29, 5.4, 0.53, 0.98, stone)
        for offset in (2.7, 5.4):
            sx = start + side * offset
            wall.box(sx, y, z + 1.59, 0.44, 0.53, 1.75, stone)
            wall.box(sx, y, z + 2.53, 0.52, 0.6, 0.16, cap)
        for height in (1.0, 2.07):
            wall.box(start + side * 2.7, y, z + height, 5.4, 0.06, 0.06, C['dark'])
        for i in range(30):
            wall.box(
                start + side * (i + 0.5) * 0.18,
                y,
                z + 1.52,
                0.035,
                0.035,
                1.51,
                C['dark'],
            )
        mesh.add_part('西侧短墙' if side < 0 else '东侧短墙', wall)
    return mesh
