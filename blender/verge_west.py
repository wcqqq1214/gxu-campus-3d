"""Repair the V5 west-side verge transitions without moving retained surfaces."""

from copy import copy

from mathutils.bvhtree import BVHTree

from geometry import Mesh
from materials_north_road import split
from refine_roads_west import _source_uv
from refine_terrain_west import hit_z, sample, submesh
from site_geometry import mesh_triangles
from v5_terrain_west import axis_x, smooth

AVENUE_BOX = (-475.0, -678.0, -444.0, -609.0)
WALK_BOX = (-405.0, -606.5, -392.0, -596.0)
CROSS_BOX = (-417.0, -604.0, -409.3, -585.0)
# Conservative bounds of the complete OSM wall outlines in buildings.json.
BUILDING_FOOTPRINTS = (
    (-535.95171869, -651.823128, -474.48202459, -606.449096),
    (-396.04456113, -667.207552, -365.57643839, -608.797948),
)


def building_weight(x, y):
    weight = 1.0
    for x0, y0, x1, y1 in BUILDING_FOOTPRINTS:
        dx = max(x0 - x, 0.0, x - x1)
        dy = max(y0 - y, 0.0, y - y1)
        distance = max(dx, dy)
        weight = min(weight, smooth((distance - 1.0) / 2.0))
    return weight


def water_projection(mesh, box):
    local = submesh(mesh, box)
    if not local.f:
        return None
    triangles = [tri for tri, _ in mesh_triangles(local)]
    flat = []
    for ids in triangles:
        a, b, c = (local.v[i] for i in ids)
        area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if abs(area) > 1e-9:
            flat.append(ids)
    return sample(local), BVHTree.FromPolygons(
        [(x, y, 0.0) for x, y, z in local.v], flat, all_triangles=True
    )


def water_weight(projection, x, y):
    if projection is None:
        return 1.0
    top, flat = projection
    if hit_z(top, x, y, 20) is not None:
        return 0.0
    point, normal, index, distance = flat.find_nearest((x, y, 0.0), 2.0)
    return 1.0 if point is None else smooth(distance / 2.0)


def cut_pieces(triangle, box, cuts):
    x0, y0, x1, y1 = box
    inside = [triangle]
    for axis, limit, sign in ((0, x0, 1), (0, x1, -1), (1, y0, 1), (1, y1, -1)):
        keep = []
        for part in inside:
            for q in split(part, lambda p: sign * (p[axis] - limit)):
                if sign * (sum(p[axis] for p in q) / len(q) - limit) < 0:
                    yield q, False
                else:
                    keep.append(q)
        inside = keep
    for cut in cuts:
        inside = [q for part in inside for q in split(part, cut)]
    for q in inside:
        yield q, True


def rebuild(mesh, colors, box, cuts, grade):
    local = Mesh()
    selected = []
    for fi, face in enumerate(mesh.f):
        pts = [mesh.v[j] for j in face]
        xs, ys, _ = zip(*pts)
        x0, y0, x1, y1 = box
        if min(xs) >= x1 or max(xs) <= x0 or min(ys) >= y1 or max(ys) <= y0:
            continue
        if mesh.m[fi] != colors['grass']:
            continue
        local.face(pts, mesh.m[fi], _source_uv(mesh, fi, pts, True))
        selected.append(fi)
    omit = set(selected)
    result = copy(mesh)
    result.v = mesh.v.copy()
    result.f, result.m, result.face_uvs = [], [], {}
    for fi, (face, mat) in enumerate(zip(mesh.f, mesh.m)):
        if fi not in omit:
            if fi in mesh.face_uvs:
                result.face_uvs[len(result.f)] = mesh.face_uvs[fi]
            result.f.append(face)
            result.m.append(mat)
    for ids, fi in mesh_triangles(local):
        uv = dict(zip(local.f[fi], local.face_uvs.get(fi, [])))
        poly = [(*local.v[j], *uv.get(j, ())) for j in ids]
        for ring, inside in cut_pieces(poly, box, cuts):
            pts = [(x, y, grade(x, y, z) if inside else z) for x, y, z, u, v in ring]
            for j in range(1, len(pts) - 1):
                indices = (0, j, j + 1)
                a, b, c = [pts[k] for k in indices]
                ab = [b[k] - a[k] for k in range(3)]
                ac = [c[k] - a[k] for k in range(3)]
                if any(
                    abs(ab[k] * ac[(k + 1) % 3] - ac[k] * ab[(k + 1) % 3]) > 1e-10
                    for k in range(3)
                ):
                    result.face(
                        [pts[k] for k in indices],
                        local.m[fi],
                        [ring[k][3:] for k in indices]
                        if fi in local.face_uvs
                        else None,
                    )
    return result


def transition_grade(
    tree, i, box, inner, outer_east, outer_west=None, roads=None, water=None
):
    y0, y1 = box[1], box[3]

    def grade(x, y, z):
        dx = x - axis_x(i, y)
        side = 1 if dx > 0 else -1
        distance = abs(dx)
        if side < 0 and outer_west is None:
            return z
        outer = outer_east if side > 0 else outer_west
        if distance <= inner or distance >= outer:
            return z
        cx = axis_x(i, y)
        a = hit_z(tree, cx + side * inner, y, 20)
        b = hit_z(tree, cx + side * outer, y, 20)
        if a is None or b is None:
            return z
        target = a + (b - a) * (distance - inner) / (outer - inner)
        if roads is None:
            longitudinal = smooth((y - y0) / 12) * smooth((y1 - y) / 12)
        else:
            edge = south_edge(x)
            if y > edge + 0.8:
                return z
            longitudinal = smooth((edge + 0.8 - y) / 0.8)
            pavement = hit_z(roads, x, y, 20)
            if pavement is not None:
                target = min(target, pavement - 0.045)
        longitudinal *= building_weight(x, y) * water_weight(water, x, y)
        if longitudinal == 0:
            return z
        change = longitudinal * (target - z)
        if roads is not None:
            limit = 0.09 * max(0.0, y - y0)
            change = max(-limit, min(limit, change))
        return z + change

    return grade


def south_edge(x):
    return -598.6264944 + 0.01346 * (x + 409.36)


def cross_grade(roads):
    def grade(x, y, z):
        south = south_edge(x)
        north = south + 7.78
        if not south - 5 <= y <= north + 5:
            return z
        lateral = smooth((x - CROSS_BOX[0]) / 2.0) * smooth((CROSS_BOX[2] - x) / 1.0)
        if lateral == 0:
            return z
        road_z = hit_z(roads, x, y, 20)
        if south <= y <= north and road_z is not None:
            target = road_z - 0.045
            return z + lateral * max(0.0, target - z)
        if y < south:
            edge_z = hit_z(roads, x, south + 0.025, 20)
            distance = south - y
        else:
            edge_z = hit_z(roads, x, north - 0.025, 20)
            distance = y - north
        if edge_z is None or distance >= 5:
            return z
        target = edge_z - 0.045
        return z + lateral * (1 - distance / 5.0) * max(0.0, target - z)

    return grade


def building_cuts():
    return [
        lambda p, axis=axis, value=value: p[axis] - value
        for x0, y0, x1, y1 in BUILDING_FOOTPRINTS
        for axis, value in (
            (0, x0 - 3),
            (0, x0 - 1),
            (0, x0),
            (0, x1),
            (0, x1 + 1),
            (0, x1 + 3),
            (1, y0 - 3),
            (1, y0 - 1),
            (1, y0),
            (1, y1),
            (1, y1 + 1),
            (1, y1 + 3),
        )
    ]


def offset_cuts(i, offsets):
    return [lambda p, d=d: p[0] - axis_x(i, p[1]) - d for d in offsets]


def apply(base, colors):
    terrain = base['terrain']
    if getattr(terrain, 'verge_west_v6', False):
        return
    original_tree = sample(terrain)
    roads = sample(submesh(base['roads'], (-478, -684, -385, -580)))
    water = water_projection(base['water'], (-478, -684, -360, -580))

    avenue_y = tuple(range(-676, -608, 2))
    avenue_offsets = (
        -14,
        -12,
        -10,
        -9,
        -8,
        -7,
        -6,
        -5,
        -4.6,
        4.6,
        5.5,
        6.5,
        7.5,
        8.5,
        9.5,
        10.5,
    )
    avenue_cuts = [lambda p, y=y: p[1] - y for y in avenue_y]
    avenue_cuts += offset_cuts(0, avenue_offsets)
    avenue_cuts += building_cuts()
    terrain = rebuild(
        terrain,
        colors,
        AVENUE_BOX,
        avenue_cuts,
        transition_grade(original_tree, 0, AVENUE_BOX, 4.6, 10.5, 14.0, water=water),
    )

    walk_y = tuple(-606.5 + i * 0.5 for i in range(22))
    walk_offsets = (
        2.75,
        3.5,
        4.5,
        5.5,
        6.5,
        7.5,
        8.5,
        9.5,
        10.5,
        11.5,
        12.5,
        13.5,
        14.0,
    )
    walk_cuts = [lambda p, y=y: p[1] - y for y in walk_y]
    walk_cuts += [lambda p, d=d: p[1] - south_edge(p[0]) - d for d in (0.0, 0.8)]
    walk_cuts += offset_cuts(1, walk_offsets)
    walk_cuts += building_cuts()
    terrain = rebuild(
        terrain,
        colors,
        WALK_BOX,
        walk_cuts,
        transition_grade(
            original_tree, 1, WALK_BOX, 2.75, 14.0, roads=roads, water=water
        ),
    )

    cross_cuts = [
        lambda p, x=x: p[0] - x
        for x in (-416, -415, -414, -413, -412, -411, -410, -409.3)
    ]
    cross_cuts += [
        lambda p, d=d: p[1] - south_edge(p[0]) - d
        for d in (
            -5,
            -4,
            -3,
            -2,
            -1,
            0,
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            7.78,
            8.78,
            9.78,
            10.78,
            11.78,
            12.78,
        )
    ]
    terrain = rebuild(
        terrain,
        colors,
        CROSS_BOX,
        cross_cuts,
        cross_grade(roads),
    )
    terrain.verge_west_v6 = True
    base.update(terrain=terrain)
