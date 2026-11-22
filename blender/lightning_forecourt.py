"""Industrial-door threshold, asphalt access and permeable parking, way/759079684."""

from functools import lru_cache

from mathutils.bvhtree import BVHTree

from civil_forecourt_grade import grade_mesh
from geometry import Mesh, tile_material
from site_geometry import mesh_triangles

DOOR_X = -140.22
WALL_Y = -981.49
LEFT = -148.0
RIGHT = -132.33


def lightning_forecourt(terrain, roads, datum, colors):
    # The north and north-west panoramas show a continuous vehicle approach.
    # The existing door pins its inner level, the actual road mesh pins the outer.
    tile_material(
        colors, 'lightningGrassBlock', 'lightning-grass-block.jpg', (0.35, 0.39, 0.35)
    )
    street = BVHTree.FromPolygons(
        roads.v, [ids for ids, _ in mesh_triangles(roads)], all_triangles=True
    )

    def road_z(x, y):
        hit = street.ray_cast((x, y, 80), (0, 0, -1))[0]
        return hit.z if hit is not None else None

    @lru_cache(maxsize=None)
    def join(x):
        lo, hi = -976.6, -972.0
        if road_z(x, lo) is not None or road_z(x, hi) is None:
            raise ValueError(f'Missing approach road boundary for way/759079684 at {x}')
        for _ in range(20):
            mid = (lo + hi) / 2
            if road_z(x, mid) is None:
                lo = mid
            else:
                hi = mid
        return hi, road_z(x, hi + 0.005)

    def finish(x, y):
        x = min(RIGHT, max(LEFT, x))
        edge, end_z = join(x)
        # Keep a low, level sill across the door. The parking wings pick up
        # part of the crossfall of their corresponding road edge.
        mid_z = join(DOOR_X)[1]
        side = min(1, max(0, (abs(x - DOOR_X) - 2.42) / 3.8))
        start_z = datum - 0.015 + side * (end_z - mid_z) * 0.4
        t = min(1, max(0, (y - WALL_Y) / (edge - WALL_Y)))
        return start_z + t * (end_z - start_z)

    # Only the short area between the north wall and road needs bedding.
    # Feather the sides and the strip below the wall back to the input mesh.
    footprint = dict(
        extent=[LEFT - 1.6, WALL_Y - 1.45, RIGHT + 1.6, -972.4],
        core=[LEFT, WALL_Y, RIGHT, -974.0],
        meshStep=0.9,
    )

    def bedding(x, y):
        z = finish(x, y)
        if y >= join(min(RIGHT, max(LEFT, x)))[0]:
            actual = road_z(x, y)
            if actual is not None:
                z = min(z, actual)
        return z - 0.04

    ground = grade_mesh(terrain, footprint, target_height=bedding)
    apron = Mesh()

    # Widen the central approach near the road, as in the flared corners in
    # both oblique views. Bands are adjoining faces, including the painted rows.
    boundaries = [
        LEFT,
        -145.65,
        -145.48,
        DOOR_X - 2.47,
        DOOR_X - 2.36,
        DOOR_X + 2.36,
        DOOR_X + 2.47,
        -135.04,
        -134.87,
        RIGHT,
    ]
    flares = [0, 0, 0, -1, -1, 1, 1, 0, 0, 0]
    materials = [
        'lightningGrassBlock',
        'roadYellow',
        'lightningGrassBlock',
        'roadYellow',
        'asphalt',
        'roadYellow',
        'lightningGrassBlock',
        'roadYellow',
        'lightningGrassBlock',
    ]
    rows = [(0, 0), (0.48, 0), (0.72, 0.08), (0.86, 0.25), (0.95, 0.50), (1, 0.87)]

    def point(x, v):
        end, _ = join(x)
        y = WALL_Y + v * (end - WALL_Y)
        return (x, y, finish(x, y))

    def surface(points, name):
        for q in (points[:3], [points[0], points[2], points[3]]):
            uv = (
                [(x / 0.24, y / 0.24) for x, y, _ in q]
                if name == 'lightningGrassBlock'
                else None
            )
            apron.face(q, colors[name], uv)

    def overlap(point, distance, lift):
        x, y, _ = point
        return (x, y + distance, road_z(x, y + distance) + lift)

    for i, material in enumerate(materials):

        def x_at(row, fraction):
            a = boundaries[i] + flares[i] * row
            b = boundaries[i + 1] + flares[i + 1] * row
            return a + (b - a) * fraction

        # Share edges across finish changes and subdivide sloping strips.
        for j in range(4):
            for (v, f), (w, g) in zip(rows, rows[1:]):
                q = [
                    point(x_at(f, j / 4), v),
                    point(x_at(f, (j + 1) / 4), v),
                    point(x_at(g, (j + 1) / 4), w),
                    point(x_at(g, j / 4), w),
                ]
                surface(q, material)
            # At the mouth carry the asphalt across the narrow curb top. The
            # far end of the overlap is below the existing carriageway.
            q = [point(x_at(0.87, t), 1) for t in (j / 4, (j + 1) / 4)]

            if material != 'asphalt':
                surface(
                    [*q, *(overlap(p, 0.04, -0.015) for p in reversed(q))], material
                )
                continue
            last = q
            for distance, lift in [(0.04, 0.007), (0.39, 0.007), (0.49, -0.012)]:
                next_row = [overlap(p, distance, lift) for p in q]
                surface([*last, *reversed(next_row)], material)
                last = next_row
    # Bed the outer edge of the pavers, with a short closed side return.
    for x in (LEFT, RIGHT):
        for (v, _), (w, _) in zip(rows, rows[1:]):
            a, b = point(x, v), point(x, w)
            quad = [a, b, (*b[:2], b[2] - 0.11), (*a[:2], a[2] - 0.11)]
            apron.face(quad if x == LEFT else quad[::-1], colors['road'])
    # The pale strip below the door is one low threshold. Both parking views
    # show the asphalt reaching it directly, without a flight of steps.
    apron.box(DOOR_X, WALL_Y + 0.25, datum - 0.012, 4.74, 0.52, 0.09, colors['stone'])
    return ground, apron
