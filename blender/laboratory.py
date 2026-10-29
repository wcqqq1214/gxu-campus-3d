"""South elevation study: official campus gallery and BV18T411X7PP, 00:58–01:00.

Photo-derived proportions, not surveyed dimensions. Rear openings remain a
provisional repetition until a clear north-elevation reference is available.
"""
from geometry import Mesh


def laboratory(l, b, z, C, detail=True):
    m = Mesh()
    xmin, ymin, xmax, ymax = l['bounds']
    x, y = (xmin+xmax)/2, (ymin+ymax)/2
    w, d = xmax-xmin, ymax-ymin
    h = (l['height']-1.8)/.855
    stone, white, glass = C['stone'], C['white'], C['glass']
    floor = z + 1.8
    front = y - d*.35

    def windows(cx, cy, width, depth, bottom, height, rows, cols):
        for sy in (-1, 1):
            yy = cy + sy*(depth/2+.04)
            for row in range(rows):
                zz = bottom+(row+.52)*height/rows
                for col in range(cols):
                    xx = cx-width/2+(col+.5)*width/cols
                    bw, bh = width/cols*.52, height/rows*.63
                    m.box(xx, yy, zz, bw+.27, .16, bh+.24, white)
                    m.box(xx, yy+sy*.10, zz, bw, .10, bh, glass)
                    if detail:
                        m.box(xx, yy+sy*.17, zz, .07, .07, bh, white)
                        m.box(xx, yy+sy*.17, zz-bh*.15, bw, .07, .07, white)

    def block(cx, cy, width, depth, bottom, height, rows, cols):
        m.box(cx, cy, bottom+height/2, width, depth, height, stone)
        windows(cx, cy, width, depth, bottom, height, rows, cols)
        m.box(cx, cy, bottom+height+.15, width+1, depth+1, .30, white)

    # Five lower window rows flank a genuine north/south passage. The mapped
    # end wings are shallower than the centre, not one bounding-box extrusion.
    for s in (-1, 1):
        block(x+s*w*.195, y, w*.21, d*.70, floor, h*.43, 5, 7)
        block(x+s*w*.355, y, w*.11, d*.66, floor, h*.43, 5, 3)
        m.box(x+s*w*.355, y, floor+h*.545, w*.11, d*.66, h*.23, stone)
        windows(x+s*w*.355, y, w*.064, d*.66,
                floor+h*.46, h*.18, 2, 2)
        block(x+s*w*.45, y, w*.08, d*.40, floor, h*.61, 7, 2)
        # Shoulder glazing and a shallow projecting flat cornice.
        m.box(x+s*w*.355, y, floor+h*.68, w*.11, d*.66, h*.035, glass)
        m.box(x+s*w*.355, y, floor+h*.71, w*.13, d*.71, .55, white)

    # Central upper block: three regular rows, a framed upper row, a recessed
    # glazed strip, then the broad flat overhang visible in both old/new photos.
    block(x, y, w*.58, d*.64, floor+h*.43, h*.25, 3, 20)
    block(x, y, w*.56, d*.62, floor+h*.69, h*.09, 1, 20)
    m.box(x, y, floor+h*.805, w*.55, d*.61, h*.045, glass)
    for sy in (-1, 1):
        for i in range(21):
            m.box(x-w*.275+i*w*.55/20, y+sy*d*.306,
                  floor+h*.805, .15, .16, h*.045, white)
    m.box(x, y, floor+h*.84, w*.62, d*.72, .65, white)
    m.box(x, y, floor+h*.855, w*.62, d*.72, .35, stone)

    # Four circular columns each side, paired capital rings and low bases.
    # Keep their bays open; windows sit on the recessed wall behind them.
    column_y = front-3.1
    shaft = h*.405
    for s in (-1, 1):
        for offset in (.112, .169, .226, .283):
            xx = x+s*w*offset
            m.cylinder(xx, column_y, floor+.24, .74, .48, stone, 20 if detail else 12)
            m.cylinder(xx, column_y, floor+.48+shaft/2, .56, shaft,
                       white, 20 if detail else 12, topr=.49)
            for dz, radius in ((.0,.67),(.24,.76)):
                m.cylinder(xx, column_y, floor+.48+shaft+dz, radius, .22,
                           white, 20 if detail else 12)
    m.box(x, column_y, floor+h*.435, w*.61, 3.0, .65, white)
    m.box(x, column_y, floor+h*.453, w*.61, 3.1, .28, stone)
    # Upper bridge hides no lower infill: the opening remains clear to north.
    m.box(x, y, z+.9, w*.19, d*.76, 1.8, stone)
    m.box(x, front-1.5, z+.9, w*.61, 4.8, 1.8, stone)
    # Broad two-flight south stair, with a level intermediate landing.
    stair_back = column_y-1.6
    for base, start, run, rise in ((z,stair_back-9,3.2,.6),
                                  (z+.6,stair_back-4.8,4.8,1.2)):
        count = 4 if rise < 1 else 8
        for i in range(count):
            tread = run/count
            top = base+rise*(i+1)/count
            yy = start+(i+.5)*tread
            m.box(x, yy, (z+top)/2, w*.29, tread, top-z, stone)
    m.box(x, stair_back-5.6, z+.3, w*.29, 1.6, .6, stone)
    m.box(x, stair_back+.8, z+.9, w*.31, 1.6, 1.8, stone)
    return m
