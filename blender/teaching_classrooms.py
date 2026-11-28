"""Classroom wings reconstructed on the surveyed outlines of Teaching 1 and 11."""

import math

from mathutils import Vector

from geometry import Mesh, tile_material
from humanities_facades import finish

FIRST = 'way/759079681'
ELEVENTH = 'way/759170266'
IDS = {FIRST, ELEVENTH}


def build(b, z, colors, detail):
    first = b['id'] == FIRST
    ivory, pink = (0.70, 0.65, 0.52), (0.65, 0.39, 0.32)
    if detail:
        tile_material(colors, 'classroomIvoryCeramic', 'bihuyuan-ivory.png', ivory)
        tile_material(colors, 'classroomPinkCeramic', 'bihuyuan-rose.png', pink)
        tile, rose = colors['classroomIvoryCeramic'], colors['classroomPinkCeramic']
    else:
        tile = finish(colors, 'classroomIvoryTile', ivory, 0.84)
        rose = finish(colors, 'classroomRoseTile', pink, 0.82)
    rim = finish(colors, 'classroomCreamCoping', (0.83, 0.80, 0.69), 0.78)
    glass = finish(colors, 'classroomWindowGlass', (0.16, 0.22, 0.23), 0.35)
    recessed = finish(colors, 'classroomRecess', (0.082, 0.067, 0.054), 0.86)
    stone = finish(colors, 'classroomStonePlinth', (0.35, 0.33, 0.28), 0.91)
    ring = b['polygons'][0][0]
    height, levels = b['height'], int(b['levels'])
    stories = height / levels
    body, roof, openings, galleries = Mesh(), Mesh(), Mesh(), Mesh()
    for i in range(0, len(b['roofTriangles'][0]), 3):
        ids = b['roofTriangles'][0][i : i + 3]
        a, c, d = [ring[j] for j in ids]
        if (c[0] - a[0]) * (d[1] - a[1]) < (c[1] - a[1]) * (d[0] - a[0]):
            c, d = d, c
        roof.face([(x, y, z + height) for x, y in (a, c, d)], colors['paleRoof'])

    for edge, (a, b_end) in enumerate(zip(ring, ring[1:])):
        dx, dy = b_end[0] - a[0], b_end[1] - a[1]
        length = math.hypot(dx, dy)
        tx, ty = dx / length, dy / length
        # Both OSM exterior rings are clockwise. Depth increases out of the wall.
        nx, ny = -ty, tx
        angle = math.atan2(ty, tx)

        def point(along, out, up):
            return a[0] + tx * along + nx * out, a[1] + ty * along + ny * out, z + up

        def box(mesh, along, out, up, width, depth, thickness, material):
            mesh.box(*point(along, out, up), width, depth, thickness, material, angle)

        def wall(start, end, offset, mat):
            body.face(
                [
                    point(end, offset, 0),
                    point(start, offset, 0),
                    point(start, offset, height),
                    point(end, offset, height),
                ],
                mat,
            )

        # Teaching 1 has a recessed south gallery and a shorter west gallery
        # beside the solid end bay. Teaching 11 has flush classroom glazing.
        gallery_edge = first and edge in (9, 14)
        start = length * 0.34 if first and edge == 14 else 0
        offset = -1.42 if gallery_edge else 0
        mat = tile if first or edge == 6 else rose
        if start:
            wall(0, start, 0, mat)
        wall(start, length, offset, mat)
        if gallery_edge:
            for t, reverse in [(start, False), (length, True)]:
                corners = [
                    point(t, offset, 0),
                    point(t, 0, 0),
                    point(t, 0, height),
                    point(t, offset, height),
                ]
                body.face(corners[::-1] if reverse else corners, mat)
        box(roof, length / 2, -0.04, height + 0.10, length, 0.20, 0.20, rim)
        box(
            body,
            (start + length) / 2,
            offset + 0.016,
            0.30,
            length - start,
            0.042,
            0.60,
            stone,
        )
        if start:
            box(body, start / 2, 0.016, 0.30, start, 0.042, 0.60, stone)

        if first:
            count = {
                1: 15,
                3: 3,
                4: 2,
                5: 3,
                7: 2,
                9: 11,
                11: 2,
                13: 3,
                14: 2,
                15: 3,
            }.get(edge, 0)
        else:
            count = {0: 4, 2: 2, 3: 3, 4: 2, 5: 1, 6: 10, 7: 1}.get(edge, 0)
        for level in range(levels):
            if gallery_edge and level:
                span = length - start
                middle = (start + length) / 2
                floor = stories * level
                if edge == 14 and level <= 2:
                    # The two exposed west landings return to the wall behind the front rail.
                    outer, inner = 1.11, offset - 0.06
                    soffit = len(galleries.f)
                    box(
                        galleries,
                        middle,
                        (inner + outer) / 2,
                        floor + 0.055,
                        span,
                        outer - inner,
                        0.29,
                        tile,
                    )
                    # Mesh.box emits the soffit first and the walking surface last.
                    galleries.m[soffit] = galleries.m[-1] = rim
                    for center_z, h, front, depth, mat in (
                        (0.505, 0.61, 1.05, 0.12, rose),
                        (0.895, 0.17, 1.055, 0.16, rim),
                    ):
                        box(
                            galleries,
                            middle,
                            front,
                            floor + center_z,
                            span,
                            depth,
                            h,
                            mat,
                        )
                        back = front - depth / 2
                        for t, direction in ((start, 1), (length, -1)):
                            box(
                                galleries,
                                t + direction * depth / 2,
                                back / 2,
                                floor + center_z,
                                depth,
                                back,
                                h,
                                mat,
                            )
                else:
                    box(
                        galleries,
                        middle,
                        offset / 2,
                        floor,
                        span,
                        -offset + 0.12,
                        0.18,
                        rim,
                    )
                    box(galleries, middle, 0.01, floor + 0.47, span, 0.12, 0.82, rose)
                    box(galleries, middle, 0.015, floor + 0.91, span, 0.16, 0.07, rim)
            if not first and level and edge in (6, 7):
                width = 0.34 if edge == 6 else 0.045
                box(
                    galleries,
                    length / 2,
                    width * 0.40,
                    stories * level,
                    length,
                    width,
                    0.18,
                    rose,
                )
            for bay in range(count):
                t = start + (bay + 0.5) * (length - start) / count
                if not first and edge == 7:
                    # Stacked narrow stair lights on the east gable.
                    t = length * 0.31
                door = (first and edge == 14 and bay == 0) or (
                    not first and edge == 7 and level == 0
                )
                w = (
                    (1.20 if door else 0.98)
                    if not first and edge == 7
                    else min(2.02, 0.64 * (length - start) / count)
                )
                if first and door:
                    w = 1.32
                h = 2.20 if door else 1.56
                threshold = (0.48 if not first else 0.14) if door else 0.88
                mid_z = stories * level + h / 2 + threshold
                box(
                    openings,
                    t,
                    offset + 0.035,
                    mid_z,
                    w,
                    0.09,
                    h,
                    recessed if door else glass,
                )
                if detail and not door:
                    box(openings, t, offset + 0.091, mid_z + 0.24, w, 0.035, 0.05, rim)
                    for split in (
                        (-0.33, -0.16, 0, 0.16, 0.33)
                        if not first and edge == 7
                        else (-0.23, 0, 0.23)
                    ):
                        box(
                            openings,
                            t + split * w,
                            offset + 0.091,
                            mid_z,
                            0.04,
                            0.035,
                            h,
                            rim,
                        )
                if door and not first:
                    box(galleries, t, 0.83, 2.82, 3.72, 1.80, 0.25, rose)
                    for step in range(4):
                        rise = 0.12 * (4 - step)
                        box(
                            galleries,
                            t,
                            0.31 + 0.34 * step,
                            rise / 2,
                            2.55,
                            0.36,
                            rise,
                            stone,
                        )

    model = Mesh()
    for label, mesh in [
        ('外墙与石基', body),
        ('屋面与压顶', roof),
        ('教室窗列和山墙采光', openings),
        ('走廊与楼层饰带', galleries),
    ]:
        model.add_part(label, mesh)
    if detail:
        # Both tile swatches contain eight squares per repeat.
        for i, (face, material) in enumerate(zip(model.f, model.m)):
            if material in (tile, rose):
                points = [model.v[j] for j in face]
                a, b, c = map(Vector, points[:3])
                normal = (b - a).cross(c - a)
                axis = max(range(3), key=lambda j: abs(normal[j]))
                u, v = [j for j in range(3) if j != axis]
                model.face_uvs[i] = [(p[u] / 0.72, p[v] / 0.72) for p in points]
    return model
