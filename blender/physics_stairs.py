"""East-facing stair slabs and railings of the physics building.

The two runs and cross-landing are visible at
https://physics.gxu.edu.cn/images/banner55555.jpg. Baidu street-view station
09007200121903051340120769B (heading 283°) shows the separate glazed entry.
The two toe elevations fit the terrain at the outside edge of each flight;
individual step dimensions and rail heights are model estimates.
"""

SHORT_WIDTH = 9.20


def stair_run(mesh, x, y, width, upper, lower, count, going, stone, metal, detail):
    """One flight descending east, with a continuous inclined soffit."""
    south, north = y - width / 2, y + width / 2
    rise = (upper - lower) / count
    depth = 0.36
    end = x + count * going
    for i in range(count):
        a, b = x + i * going, x + (i + 1) * going
        top = upper - i * rise
        next_top = top - rise
        inside, outside = top - depth, next_top - depth
        mesh.face(
            [(a, south, top), (b, south, top), (b, north, top), (a, north, top)], stone
        )
        mesh.face(
            [
                (b, south, next_top),
                (b, north, next_top),
                (b, north, top),
                (b, south, top),
            ],
            stone,
        )
        edge = [(a, inside), (b, outside), (b, top), (a, top)]
        mesh.face([(px, south, pz) for px, pz in edge], stone)
        mesh.face([(px, north, pz) for px, pz in reversed(edge)], stone)
    mesh.face(
        [
            (x, south, upper - depth),
            (x, north, upper - depth),
            (end, north, lower - depth),
            (end, south, lower - depth),
        ],
        stone,
    )
    mesh.face(
        [
            (end, south, lower - depth),
            (end, north, lower - depth),
            (end, north, lower),
            (end, south, lower),
        ],
        stone,
    )
    mesh.face(
        [
            (x, south, upper),
            (x, north, upper),
            (x, north, upper - depth),
            (x, south, upper - depth),
        ],
        stone,
    )
    for side in (south + 0.10, north - 0.10):
        rail_heights = (0.48, 0.94) if detail else (0.94,)
        for h in rail_heights:
            mesh.line((x, side, upper + h), (end, side, lower + h), 0.035, metal)
        for i in range(0, count + 1, 3):
            t = i / count
            h = upper + t * (lower - upper)
            mesh.box(x + t * (end - x), side, h + 0.46, 0.055, 0.055, 0.96, metal)
        if count % 3:
            mesh.box(end, side, lower + 0.46, 0.055, 0.055, 0.96, metal)
