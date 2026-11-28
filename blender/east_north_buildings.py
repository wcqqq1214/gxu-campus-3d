"""East campus faculty housing, from the university site plan and construction aerial."""

import math

from geometry import Mesh

IDS = frozenset(f'east-north/faculty-{n}' for n in ('1', '2', '3', '3a', '5', '6', '7'))


def build(b, z, C, detail):
    mesh = Mesh()
    ring = b['polygons'][0][0]
    h = b['height']
    # 3.9 m entrance storey and thirty 3 m storeys, per the construction contract.
    for low, high, wall in ((0, 12.9, 'red'), (12.9, 93.9, 'white'), (93.9, h, 'red')):
        mesh.extrude(
            b['polygons'],
            b['roofTriangles'] if high == h else [[]],
            z + low,
            high - low,
            C[wall],
            C['paleRoof'],
        )
    for a, end in zip(ring, ring[1:]):
        dx, dy = end[0] - a[0], end[1] - a[1]
        length = math.hypot(dx, dy)
        # A continuous terracotta parapet surrounds the pale roof terrace.
        mesh.box(
            (a[0] + end[0]) / 2,
            (a[1] + end[1]) / 2,
            z + h + 0.22,
            length,
            0.52,
            0.44,
            C['red'],
            math.atan2(dy, dx),
            bottom=False,
        )
        if length < 5:
            continue
        ux, uy = dx / length, dy / length

        def panel(t0, t1, bottom, top, finish, offset):
            def point(t, height):
                return (
                    a[0] + ux * t + uy * offset,
                    a[1] + uy * t - ux * offset,
                    z + height,
                )

            mesh.face(
                [point(t0, bottom), point(t1, bottom), point(t1, top), point(t0, top)],
                C[finish],
            )

        bays = max(1, round(length / 3.3))
        for bay in range(bays):
            start = length * (bay + 0.17) / bays
            stop = length * (bay + 0.83) / bays
            panel(start, stop, 0.65, 93.5, 'slate', 0.035)
            if detail and length > 8:
                # Narrow projected sill plates cast real shadows between the stacked bays.
                mid = (start + stop) * 0.5
                for floor in range(1, 31):
                    mesh.box(
                        a[0] + ux * mid + uy * 0.16,
                        a[1] + uy * mid - ux * 0.16,
                        z + 3.9 + (floor - 1) * 3,
                        stop - start + 0.18,
                        0.38,
                        0.17,
                        C['stone'],
                        math.atan2(dy, dx),
                        bottom=False,
                    )
            if detail:
                for floor in range(31):
                    sill = 0.95 if floor == 0 else 3.9 + (floor - 1) * 3 + 0.85
                    panel(start, stop, sill, sill + 1.65, 'glass', 0.075)
                    panel(start, stop, sill - 0.7, sill - 0.47, 'stone', 0.085)
    # Roof headhouse and terracotta cap seen above the pale terrace.
    x, y = b['center']
    a, end = max(zip(ring, ring[1:]), key=lambda pair: math.dist(*pair))
    rot = math.atan2(end[1] - a[1], end[0] - a[0])
    mesh.box(x, y, z + h + 1.5, 8.6, 5.5, 3, C['stone'], rot, bottom=False)
    mesh.box(x, y, z + h + 3.17, 9.4, 6.3, 0.34, C['red'], rot, bottom=False)
    return mesh
