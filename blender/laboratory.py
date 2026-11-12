"""South elevation study: official campus gallery and BV18T411X7PP, 00:58–01:00.

Photo-derived proportions, not surveyed dimensions. Rear openings remain a
provisional repetition until a clear north-elevation reference is available.
"""

from geometry import Mesh


def laboratory(l, b, z, C, detail=True):
    m = Mesh()
    xmin, ymin, xmax, ymax = l['bounds']
    x, y = (xmin + xmax) / 2, (ymin + ymax) / 2
    w, d = xmax - xmin, ymax - ymin
    h = (l['height'] - 1.8) / 0.855
    stone, white, glass = C['stone'], C['white'], C['glass']
    floor = z + 1.8
    front = y - d * 0.35

    def windows(cx, cy, width, depth, bottom, height, rows, cols):
        for sy in (-1, 1):
            yy = cy + sy * (depth / 2 + 0.04)
            for row in range(rows):
                zz = bottom + (row + 0.52) * height / rows
                for col in range(cols):
                    xx = cx - width / 2 + (col + 0.5) * width / cols
                    bw, bh = width / cols * 0.52, height / rows * 0.63
                    m.box(xx, yy, zz, bw + 0.27, 0.16, bh + 0.24, white)
                    m.box(xx, yy + sy * 0.10, zz, bw, 0.10, bh, glass)
                    if detail:
                        m.box(xx, yy + sy * 0.17, zz, 0.07, 0.07, bh, white)
                        m.box(xx, yy + sy * 0.17, zz - bh * 0.15, bw, 0.07, 0.07, white)

    def block(cx, cy, width, depth, bottom, height, rows, cols):
        m.box(cx, cy, bottom + height / 2, width, depth, height, stone)
        windows(cx, cy, width, depth, bottom, height, rows, cols)
        m.box(cx, cy, bottom + height + 0.15, width + 1, depth + 1, 0.30, white)

    # Five lower window rows flank a genuine north/south passage. The mapped
    # end wings are shallower than the centre, not one bounding-box extrusion.
    for s in (-1, 1):
        block(x + s * w * 0.195, y, w * 0.21, d * 0.70, floor, h * 0.43, 5, 7)
        block(x + s * w * 0.355, y, w * 0.11, d * 0.66, floor, h * 0.43, 5, 3)
        m.box(
            x + s * w * 0.355, y, floor + h * 0.545, w * 0.11, d * 0.66, h * 0.23, stone
        )
        windows(
            x + s * w * 0.355, y, w * 0.064, d * 0.66, floor + h * 0.46, h * 0.18, 2, 2
        )
        block(x + s * w * 0.45, y, w * 0.08, d * 0.40, floor, h * 0.61, 7, 2)
        # Shoulder glazing and a shallow projecting flat cornice.
        m.box(
            x + s * w * 0.355, y, floor + h * 0.68, w * 0.11, d * 0.66, h * 0.035, glass
        )
        m.box(x + s * w * 0.355, y, floor + h * 0.71, w * 0.13, d * 0.71, 0.55, white)

    # Central upper block: three regular rows, a framed upper row, a recessed
    # glazed strip, then the broad flat overhang visible in both old/new photos.
    block(x, y, w * 0.58, d * 0.64, floor + h * 0.43, h * 0.25, 3, 20)
    block(x, y, w * 0.56, d * 0.62, floor + h * 0.69, h * 0.09, 1, 20)
    m.box(x, y, floor + h * 0.805, w * 0.55, d * 0.61, h * 0.045, glass)
    for sy in (-1, 1):
        for i in range(21):
            m.box(
                x - w * 0.275 + i * w * 0.55 / 20,
                y + sy * d * 0.306,
                floor + h * 0.805,
                0.15,
                0.16,
                h * 0.045,
                white,
            )
    m.box(x, y, floor + h * 0.84, w * 0.62, d * 0.72, 0.65, white)
    m.box(x, y, floor + h * 0.855, w * 0.62, d * 0.72, 0.35, stone)

    # Four circular columns each side, paired capital rings and low bases.
    # Keep their bays open; windows sit on the recessed wall behind them.
    column_y = front - 3.1
    shaft = h * 0.405
    for s in (-1, 1):
        for offset in (0.112, 0.169, 0.226, 0.283):
            xx = x + s * w * offset
            m.cylinder(
                xx, column_y, floor + 0.24, 0.74, 0.48, stone, 20 if detail else 12
            )
            m.cylinder(
                xx,
                column_y,
                floor + 0.48 + shaft / 2,
                0.56,
                shaft,
                white,
                20 if detail else 12,
                topr=0.49,
            )
            for dz, radius in ((0.0, 0.67), (0.24, 0.76)):
                m.cylinder(
                    xx,
                    column_y,
                    floor + 0.48 + shaft + dz,
                    radius,
                    0.22,
                    white,
                    20 if detail else 12,
                )
    m.box(x, column_y, floor + h * 0.435, w * 0.61, 3.0, 0.65, white)
    m.box(x, column_y, floor + h * 0.453, w * 0.61, 3.1, 0.28, stone)
    # Upper bridge hides no lower infill: the opening remains clear to north.
    m.box(x, y, z + 0.9, w * 0.19, d * 0.76, 1.8, stone)
    m.box(x, front - 1.5, z + 0.9, w * 0.61, 4.8, 1.8, stone)
    # Broad two-flight south stair, with a level intermediate landing.
    stair_back = column_y - 1.6
    for base, start, run, rise in (
        (z, stair_back - 9, 3.2, 0.6),
        (z + 0.6, stair_back - 4.8, 4.8, 1.2),
    ):
        count = 4 if rise < 1 else 8
        for i in range(count):
            tread = run / count
            top = base + rise * (i + 1) / count
            yy = start + (i + 0.5) * tread
            m.box(x, yy, (z + top) / 2, w * 0.29, tread, top - z, stone)
    m.box(x, stair_back - 5.6, z + 0.3, w * 0.29, 1.6, 0.6, stone)
    m.box(x, stair_back + 0.8, z + 0.9, w * 0.31, 1.6, 1.8, stone)
    return m
