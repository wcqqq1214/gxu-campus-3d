"""Chemistry main building. Gallery 23 and panoramas on both sides of the court."""

from mathutils import Vector
from mathutils.geometry import tessellate_polygon

from college_details import flight, pane, sign
from geometry import Mesh

BUILDING_ID = 'way/759090371'


def main_shell(b, z, C):
    # On the 2004 extension plan the westernmost strip belongs to the
    # six-storey annex. End the earlier building at its shared wall.
    ring = b['polygons'][0][0]
    shoulder = ring[11]
    if abs(shoulder[0] + 601.27) > 0.6 or abs(shoulder[1] + 1020.14) > 0.6:
        raise ValueError('Recheck chemistry annex against the west courtyard return')
    outline = [*ring[:8], (shoulder[0], ring[8][1]), *ring[11:-1]]
    triangles = tessellate_polygon([[Vector((x, y, 0)) for x, y in outline]])
    body = Mesh()
    body.extrude(
        [[outline + [outline[0]]]],
        [[index for tri in triangles for index in tri]],
        z - 0.5,
        17.8,
        C['tenWall'],
        C['paleRoof'],
    )
    return body


def west_annex(z, C, detail):
    """Building 1 annex, sheets 建施01/02 plus the north and south street ends."""
    part = Mesh()
    west, east = -611.64, -601.27
    south, north = -1039.02, -1011.62
    corridor = west + 1.50
    cx, cy = (corridor + east) / 2, (north + south) / 2
    datum = z + 0.32
    # Section 1-1: six staggered floors, roof at +18.90, old building at +18.80.
    part.box(cx, cy, datum + 9.2, east - corridor, north - south, 19.4, C['tenWall'])
    part.box(
        (east + west) / 2,
        cy,
        datum + 18.97,
        east - west + 0.80,
        north - south + 0.80,
        0.22,
        C['gateTrim'],
    )
    for base, top in zip((0, 3, 6.1, 9.2, 12.4, 15.6), (3, 6.1, 9.2, 12.4, 15.6, 18.9)):
        h = datum + base
        storey = top - base
        part.box(west + 0.75, cy, h + 0.06, 1.50, north - south, 0.14, C['gateStone'])
        # Corridor openings are backed by the doors and small lights in 建施02.
        for y in (-1036.3, -1030.7, -1024.8, -1015.2):
            pane(
                part,
                corridor,
                y,
                h + 1.14,
                1.62,
                2.22,
                (-1, 0),
                C,
                detail,
                C['tenGlass'],
            )
        for y in (-1034.3, -1032.4, -1028.4, -1026.7, -1022.6, -1017.3):
            pane(part, corridor, y, h + 1.84, 0.84, 0.61, (-1, 0), C, detail)
        if base:
            part.box(west + 0.10, cy, h + 0.55, 0.20, north - south, 0.90, C['tenWall'])
        for y in (south + 0.16, north - 0.16):
            part.box(west + 0.80, y, h + storey / 2, 1.60, 0.32, storey, C['tenWall'])
        # Street views 169° and 355° resolve the two short ends including
        # the broad inset horizontal glazing and narrow lights at the jambs.
        for y, ny in ((north, 1), (south, -1)):
            part.box(
                (west + east) / 2,
                y,
                h + storey / 2,
                east - west,
                0.24,
                storey,
                C['tenWall'],
            )
            pane(
                part,
                cx,
                y + ny * 0.13,
                h + 1.62,
                4.8,
                1.52,
                (0, ny),
                C,
                detail,
                C['tenGlass'],
            )
            pane(
                part,
                west + 0.78,
                y + ny * 0.13,
                h + 2.02,
                0.67,
                0.82,
                (0, ny),
                C,
                detail,
            )
            if ny < 0:
                pane(
                    part,
                    east - 0.78,
                    y - 0.13,
                    h + 1.77,
                    0.76,
                    1.58,
                    (0, -1),
                    C,
                    detail,
                )
                # 建施02 splits only this second-storey opening on the south.
                if base == 3:
                    part.box(
                        cx + 0.59, y - 0.49, h + 1.62, 0.86, 0.22, 1.76, C['tenWall']
                    )
            if detail:
                for off in (-1.8, -1.2, -0.6, 0.6, 1.2, 1.8):
                    part.box(
                        cx + off, y + ny * 0.38, h + 1.63, 0.04, 0.05, 1.48, C['metal']
                    )
        # Exposed east return above the short low link to the north court.
        if base:
            pane(part, east, north - 3.75, h + 1.58, 5.10, 1.34, (1, 0), C, detail)
    # The L-shaped spur is single-storey in the north elevation and in the
    # 202° panorama. It is absent from the simplified OSM exterior.
    part.box(east + 4, north - 3.05, datum + 1.86, 8.0, 6.1, 4.25, C['huicuiWall'])
    part.box(east + 4, north - 3.05, datum + 4.05, 8.35, 6.42, 0.21, C['gateTrim'])
    for x in (east + 2.08, east + 5.9):
        pane(part, x, north + 0.06, datum + 2.7, 1.71, 0.82, (0, 1), C, detail)
    for y, normal in ((north, 1), (south, -1)):
        part.box(
            (west + east) / 2,
            y + normal * 0.12,
            z + 0.55,
            east - west,
            0.18,
            1.10,
            C['huicuiWall'],
        )
        if detail:
            for course in range(3):
                part.box(
                    (west + east) / 2,
                    y + normal * 0.22,
                    z + 0.22 + 0.32 * course,
                    east - west,
                    0.055,
                    0.033,
                    C['gateJoint'],
                )
                for joint in range(8):
                    part.box(
                        west + 0.62 + joint * 1.22 + (course % 2) * 0.52,
                        y + normal * 0.22,
                        z + 0.38 + 0.32 * course,
                        0.035,
                        0.055,
                        0.29,
                        C['gateJoint'],
                    )
    return part


def stair_cheeks(mesh, x, y, z, width, run, rise, mat):
    # The side walls rise with the upper flight in gallery 23.
    for side in (-1, 1):
        cx = x + side * (width / 2 + 0.18)
        outline = [(y - run, z), (y, z), (y, z + rise + 0.53), (y - run, z + 0.53)]
        left = [(cx - 0.18, py, pz) for py, pz in outline]
        right = [(cx + 0.18, py, pz) for py, pz in outline]
        mesh.face(left[::-1], mat)
        mesh.face(right, mat)
        for i, point in enumerate(left):
            j = (i + 1) % len(left)
            mesh.face([point, left[j], right[j], right[i]], mat)


def chemical_college(b, z, C, detail):
    body = main_shell(b, z, C)
    f = Mesh()
    # Section 1-1 places the older adjoining roof at +18.80, only 0.10 m
    # below the new wing. Carry that datum only across its attached block.
    old_roof = 0.32 + 18.80
    for east, south, north in (
        (-582.28, -1039.03, -1031.95),
        (-583.66, -1031.95, -1020.14),
    ):
        cx, cy = (-601.27 + east) / 2, (north + south) / 2
        body.box(
            cx,
            cy,
            z + (17.3 + old_roof) / 2,
            east + 601.27,
            north - south,
            old_roof - 17.3,
            C['tenWall'],
        )
        body.box(
            cx,
            cy,
            z + old_roof + 0.06,
            east + 601.27,
            north - south,
            0.12,
            C['paleRoof'],
        )
    # The raised basement and four full rows are visible on both court facades.
    for x0, x1, y, normal, count in [
        (-582.28, -525.22, -1032.02, -1, 15),
        (-583.66, -524.69, -1014.41, 1, 15),
        (-601.27, -582.28, -1039.05, -1, 5),
        (-601.27, -583.67, -1020.13, 1, 5),
    ]:
        w = (x1 - x0) / count
        adjacent = x0 == -601.27
        rows = (4.92, 9.22, 13.12, 17.02) if adjacent else (4.35, 7.87, 11.39, 14.91)
        body.box(
            (x0 + x1) / 2,
            y + normal * 0.11,
            z + 1.32,
            x1 - x0,
            0.27,
            2.64,
            C['huicuiWall'],
        )
        body.box(
            (x0 + x1) / 2,
            y + normal * 0.21,
            z + 2.65,
            x1 - x0,
            0.47,
            0.17,
            C['gateTrim'],
        )
        for j in range(count):
            x = x0 + (j + 0.5) * w
            pane(
                f,
                x,
                y + normal * 0.28,
                z + 1.36,
                w * 0.68,
                1.16,
                (0, normal),
                C,
                detail,
            )
            for level in rows:
                pane(
                    f,
                    x,
                    y + normal * 0.05,
                    z + level,
                    w * 0.64,
                    1.86,
                    (0, normal),
                    C,
                    detail,
                )
            if normal < 0:
                body.box(
                    x - w * 0.47, y - 0.31, z + 9.7, 0.27, 0.70, 14.3, C['gateStone']
                )
        body.box(
            (x0 + x1) / 2,
            y + normal * 0.26,
            z + (old_roof + 0.12 if adjacent else 17.42),
            x1 - x0 + 0.45,
            0.8,
            0.27,
            C['gateTrim'],
        )
    # On gallery 23 the high window bank meets the portico cornice. Three
    # framed rows above, then a nearly blind panel and three small vents.
    body.box(-512.15, -1022.31, z + 18.35, 25.25, 25.04, 2.1, C['tenWall'])
    body.box(-512.15, -1022.31, z + 19.53, 25.9, 25.65, 0.26, C['gateTrim'])
    for y in (-1034.86, -1009.72):
        normal = -1 if y < -1020 else 1
        body.box(-512.27, y + normal * 0.1, z + 1.12, 25.6, 0.24, 2.24, C['huicuiWall'])
    # The photographed plinth is coursed masonry. Keep joints below the
    # visible window sills and stop them at the raised portico platform.
    if detail:
        for y, normal in ((-1034.86, -1), (-1009.72, 1)):
            ranges = [(-508.1, -499.46)] if normal == -1 else [(-525.0, -499.46)]
            for lo, hi in ranges:
                for k in range(4):
                    body.box(
                        (lo + hi) / 2,
                        y + normal * 0.245,
                        z + 0.24 + k * 0.50,
                        hi - lo,
                        0.052,
                        0.037,
                        C['gateJoint'],
                    )
                    start = lo + 0.45 + (k % 2) * 0.56
                    for j in range(int((hi - start) / 1.18)):
                        body.box(
                            start + 1.18 * j,
                            y + normal * 0.245,
                            z + 0.49 + k * 0.50,
                            0.033,
                            0.052,
                            0.45,
                            C['gateJoint'],
                        )
    for k in range(3):
        h = z + 8.55 + 3.8 * k
        for x in (-522.62, -519.72, -516.82, -513.92, -511.02):
            pane(f, x, -1034.92, h, 1.89, 1.98, (0, -1), C, detail, C['tenGlass'])
            body.box(x - 1.45, -1035.29, h, 0.46, 0.96, 3.8, C['huicuiWall'])
            if k == 0:
                pane(
                    f, x, -1034.92, z + 7.04, 1.89, 0.46, (0, -1), C, detail, C['dark']
                )
        body.box(-509.57, -1035.29, h, 0.46, 0.96, 3.8, C['huicuiWall'])
        body.box(-516.97, -1035.32, h - 1.34, 14.8, 1.0, 0.55, C['huicuiWall'])
        pane(f, -502.6, -1034.9, z + 14.3 + k * 1.22, 0.65, 0.77, (0, -1), C, detail)
    x = -516.8
    # Near-2/3 show a separate lower flight and intermediate landing.
    body.box(x, -1036.90, z + 1.15, 17.4, 4.12, 2.3, C['huicuiWall'])
    body.box(x, -1037.04, z + 6.65, 18.4, 4.6, 0.42, C['gateStone'])
    for px in (-524.4, -519.3, -514.3, -509.2):
        body.box(px, -1038.62, z + 4.44, 1.0, 1.06, 4.3, C['huicuiWall'])
        body.box(px, -1038.62, z + 6.38, 1.20, 1.28, 0.31, C['gateStone'])
    # The front edge of the raised stone plinth turns back under the eave.
    # A light pierced guard on the east side is visible against the blank wall.
    for px in (-525.33, -508.27):
        body.box(px, -1036.94, z + 2.47, 0.33, 4.13, 0.33, C['gateStone'])
        for height in (2.66, 2.93, 3.28):
            body.box(px, -1036.94, z + height, 0.10, 4.09, 0.085, C['metal'])
        for j in range(12):
            body.box(px, -1038.89 + j * 0.35, z + 2.96, 0.085, 0.085, 0.61, C['metal'])
    f.box(x, -1034.99, z + 3.82, 7.0, 0.2, 3.0, C['dark'])
    for px in (x - 1.1, x + 1.1):
        pane(f, px, -1035.11, z + 3.72, 2.05, 2.60, (0, -1), C, detail)
    body.box(x, -1040.08, z + 0.525, 13.4, 2.24, 1.05, C['huicuiWall'])
    flight(body, x, -1038.96, z + 1.05, 13.4, 7, 0.32, 1.25 / 7, C['gateStone'])
    stair_cheeks(body, x, -1038.96, z + 1.05, 13.4, 2.24, 1.25, C['huicuiWall'])
    body.box(x, -1042.30, z + 0.525, 15.3, 2.20, 1.05, C['gateStone'])
    flight(body, x, -1043.4, z, 15.3, 6, 0.36, 1.05 / 6, C['gateStone'])
    for k in range(4):
        h = z + 5.34 + k * 3.46
        body.box(-498.75, -1019.3, h - 1.36, 1.36, 7.8, 0.21, C['gateTrim'])
        body.box(-498.13, -1019.3, h - 0.86, 0.16, 7.8, 0.85, C['tenWall'])
        for y in (-1030.8, -1027.8, -1020.8, -1017.8, -1012.6):
            pane(f, -499.31, y, h, 1.55, 1.85, (1, 0), C, detail)
    if detail:
        sign(
            f, '化学化工学院', -516.8, -1035.11, z + 20.52, 14.3, 1.60, C['gateRed'], 0
        )
    body.add_part('化工学院实景窗列与门厅', f)
    body.add_part('化工一号楼附楼与北侧低翼', west_annex(z, C, detail))
    return body
