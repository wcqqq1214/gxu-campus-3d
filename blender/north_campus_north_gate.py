"""秀厢北门。局部 X 沿门线向东，Y 指向北校园教学区。"""

from math import radians

from geometry import Mesh


def build(l, b, z, C, detail):
    x, y = l['center']
    gate = Mesh()
    stone, trim, metal = C['stoneCool'], C['stone'], C['metal']

    for side, label in [(-1, '西'), (1, '东')]:
        cx = x + side * 5.36
        pier = Mesh()
        pier.box(cx, y, z + 1.55, 0.98, 1.00, 3.30, stone)
        pier.box(cx, y, z + 3.24, 1.04, 1.06, 0.12, trim)
        pier.cylinder(cx, y, z + 3.45, 0.34, 0.30, metal, 12, topr=0.22)
        pier.ellipsoid(
            cx,
            y,
            z + 4.025,
            0.425,
            0.425,
            0.425,
            C['white'],
            n=16 if detail else 8,
            rings=8 if detail else 4,
        )
        if side == 1 and detail:
            pier.box(cx, y - 0.515, z + 1.73, 0.39, 0.035, 2.26, trim)
        gate.add_part(label + '门柱与球灯', pier)

    # 四段金属门扇以现场闭合状态呈现。两档均保持栏杆透空。
    span = 9.74
    for i in range(4):
        leaf = Mesh()
        width = span / 4
        cx = x + (i - 1.5) * width
        for u in [-width / 2 + 0.045, width / 2 - 0.045]:
            leaf.box(cx + u, y, z + 1.17, 0.09, 0.12, 2.12, metal)
        for height in (0.22, 1.97):
            leaf.box(cx, y, z + height, width, 0.09, 0.075, metal)
        bars = 14 if detail else 7
        for k in range(bars):
            bx = cx - width / 2 + width * (k + 0.5) / bars
            leaf.box(bx, y, z + 1.15, 0.038 if detail else 0.060, 0.05, 1.94, metal)
            if detail:
                leaf.cylinder(bx, y, z + 2.17, 0.039, 0.10, metal, 4, topr=0.008)
        gate.add_part(f'金属门扇{i + 1}', leaf)

    booth = Mesh()
    bx, by = x + 10.72, y + 1.76
    booth.box(bx, by, z + 1.51, 6.2, 3.52, 3.22, stone)
    booth.box(bx, by, z + 0.20, 6.22, 3.54, 0.46, trim)
    booth.box(bx, by, z + 3.21, 6.55, 3.83, 0.18, trim)
    gate.add_part('东侧值守房', booth)
    windows = Mesh()
    windows.box(bx - 1.43, y - 0.035, z + 1.88, 1.76, 0.08, 1.37, C['shadeGlass'])
    windows.box(bx - 3.12, by, z + 1.83, 0.08, 1.68, 1.46, C['shadeGlass'])
    if detail:
        for k in range(8):
            windows.box(
                bx - 2.32 + k * 0.253, y - 0.10, z + 1.88, 0.034, 0.05, 1.48, metal
            )
        for height in (1.17, 2.17, 2.58):
            windows.box(bx - 1.43, y - 0.10, z + height, 1.84, 0.06, 0.044, metal)
    gate.add_part('临街窗及侧窗', windows)
    gate.rotate_z(x, y, radians(-9))
    return gate
