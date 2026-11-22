"""V6 terrain-only verge repairs for the east and north campus slices."""

import math
from copy import copy

from mathutils import Vector
from mathutils.bvhtree import BVHTree

from next_terrain_east import local_faces, smooth
from refine_roads_west import _bands, _split
from site_geometry import mesh_triangles

CASES = (
    {
        'name': 'graduate_bend',
        'bounds': (558, -522, 598, -482),
        'step': 0.25,
        'clearance': 0.12,
        'inner': 0.65,
        'shoulderSlope': 0.18,
        'border': 4.0,
    },
    {
        'name': 'north_farm_verges',
        'bounds': (-195, 770, -100, 845),
        'step': 1.0,
        'clearance': 0.16,
        'inner': 0.8,
        'shoulderSlope': 0.20,
        'border': 5.0,
    },
    {
        'name': 'west15_apron_verges',
        'bounds': (-158, 96, -145, 110),
        'step': 0.5,
        'clearance': 0.12,
        'inner': 0.45,
        'shoulderSlope': 0.15,
        'border': 2.0,
    },
)

WALL = ((556.356, -500.049), (584.875, -527.712))


def _pavement_tree(base, colors, bounds):
    road, ids = local_faces(base['roads'], bounds, False)
    triangles = mesh_triangles(road)
    materials = {colors[k] for k in ('asphalt', 'road', 'roadYellow', 'curb', 'path')}
    source = [
        [road.v[j] for j in face] for face, i in triangles if road.m[i] in materials
    ]
    planar_vertices, planar_faces = [], []
    for triangle in source:
        start = len(planar_vertices)
        planar_vertices.extend((x, y, 0.0) for x, y, z in triangle)
        planar_faces.append((start, start + 1, start + 2))
    return {
        'planar': BVHTree.FromPolygons(
            planar_vertices, planar_faces, all_triangles=True
        ),
        'vertical': BVHTree.FromPolygons(
            road.v,
            [face for face, i in triangles if road.m[i] in materials],
            all_triangles=True,
        ),
        'triangles': source,
    }


def _interpolate(triangle, x, y):
    a, b, c = triangle
    denominator = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
    if abs(denominator) < 1e-12:
        return min(p[2] for p in triangle)
    u = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / denominator
    v = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / denominator
    return u * a[2] + v * b[2] + (1.0 - u - v) * c[2]


def _border_weight(x, y, bounds, width):
    x0, y0, x1, y1 = bounds
    return (
        smooth((x - x0) / width)
        * smooth((x1 - x) / width)
        * smooth((y - y0) / width)
        * smooth((y1 - y) / width)
    )


def _graduate_guard(x, y):
    wx, wy = WALL[0]
    dx, dy = WALL[1][0] - wx, WALL[1][1] - wy
    wall_distance = (dx * (y - wy) - dy * (x - wx)) / math.hypot(dx, dy)
    square_distance = math.hypot(max(0.0, x - 564.625), max(0.0, -490.699 - y))
    return (
        smooth((wall_distance - 3.0) / 2.0)
        * smooth((square_distance - 1.45) / 1.5)
        * smooth((-484 - y) / 4)
    )


def _adjusted(point, pavement, soil, case):
    x, y, z = point[:3]
    bounds = case['bounds']
    weight = _border_weight(x, y, bounds, case['border'])
    if weight <= 0:
        return point[:3]
    underfoot = pavement['vertical'].ray_cast((x, y, 100), (0, 0, -1), 150)[0]
    if underfoot is not None:
        clearance = underfoot.z - z
        # V5 already beds these surfaces. Do not turn a sound 4--6 cm roadbed
        # into the wider verge clearance used at the three defective contacts.
        if 0.0 <= clearance <= 0.08:
            return point[:3]
        distance = 0.0
        road_z = underfoot.z
    else:
        nearest = pavement['planar'].find_nearest(Vector((x, y, 0)))
        if nearest[0] is None:
            return point[:3]
        contact, normal, index, planar_distance = nearest
        distance = math.hypot(x - contact.x, y - contact.y)
        # The planar tree chooses by XY only. Interpolate its source triangle;
        # if ribbons overlap, the vertical ray selects the actual upper face.
        overlap = pavement['vertical'].ray_cast(
            (contact.x, contact.y, 100), (0, 0, -1), 150
        )[0]
        if overlap is None:
            road_z = _interpolate(pavement['triangles'][index], contact.x, contact.y)
        else:
            road_z = overlap.z
    if case['name'] == 'graduate_bend':
        weight *= _graduate_guard(x, y)
    if weight <= 0:
        return point[:3]
    target = (
        road_z
        - case['clearance']
        - case['shoulderSlope'] * max(0.0, distance - case['inner'])
    )
    dz = weight * (target - z)
    if dz <= 0.0:
        return point[:3]
    # A target at one vertex must not lift a triangle through a lower adjoining
    # path. Cap it by the original clearance in the vertex's own support ring.
    radius = case['step'] * 0.75
    allowances = []
    protected = False
    for dx in (-radius, 0.0, radius):
        for dy in (-radius, 0.0, radius):
            px, py = x + dx, y + dy
            hard = pavement['vertical'].ray_cast((px, py, 100), (0, 0, -1), 150)[0]
            ground = soil.ray_cast((px, py, 100), (0, 0, -1), 150)[0]
            if hard is None or ground is None:
                continue
            clearance = hard.z - ground.z
            allowances.append(clearance - 0.035)
            protected |= 0.0 <= clearance <= 0.08
    if allowances:
        dz = min(dz, min(allowances))
    if protected:
        dz = 0.0
    else:
        dz = max(0.0, dz)
    # Ray heights are estimated verge levels, never new hard surfaces.
    return (x, y, z + dz)


def _cells(poly, bounds, step):
    x0, y0, x1, y1 = bounds
    for axis, cut, keep_high in (
        (0, x0, True),
        (0, x1, False),
        (1, y0, True),
        (1, y1, False),
    ):
        low, high = _split(poly, axis, cut)
        poly, rest = (high, low) if keep_high else (low, high)
        if len(rest) >= 3:
            yield rest, False
        if len(poly) < 3:
            return

    def stations(low, high):
        first = math.ceil((low + 1e-8) / step) * step
        count = max(0, math.floor((high - first + 1e-8) / step) + 1)
        return [first + i * step for i in range(count)]

    for row in _bands(poly, 1, stations(y0, y1)):
        for cell in _bands(row, 0, stations(x0, x1)):
            yield cell, True


def _has_area(points):
    if len(points) < 3:
        return False
    a, b, c = points[:3]
    return (
        max(
            abs((b[i] - a[i]) * (c[j] - a[j]) - (b[j] - a[j]) * (c[i] - a[i]))
            for i, j in ((0, 1), (1, 2), (2, 0))
        )
        > 1e-10
    )


def _repair(terrain, pavement, grass, case):
    bounds = case['bounds']
    local, ids = local_faces(terrain, bounds, True)
    ids = {i for i in ids if terrain.m[i] == grass}
    triangles = mesh_triangles(local)
    soil = BVHTree.FromPolygons(
        local.v,
        [face for face, i in triangles if local.m[i] == grass],
        all_triangles=True,
    )
    result = copy(terrain)
    result.v = list(terrain.v)
    result.f, result.m, result.face_uvs = [], [], {}
    for i, (face, mat) in enumerate(zip(terrain.f, terrain.m)):
        if i in ids:
            continue
        if i in terrain.face_uvs:
            result.face_uvs[len(result.f)] = terrain.face_uvs[i]
        result.f.append(face)
        result.m.append(mat)
    for face, i in triangles:
        if local.m[i] != grass:
            continue
        uv = dict(zip(local.f[i], local.face_uvs[i]))
        original = [(*local.v[j], *uv[j]) for j in face]
        for piece, active in _cells(original, bounds, case['step']):
            vertices = [
                _adjusted(p, pavement, soil, case) if active else p[:3] for p in piece
            ]
            for j in range(1, len(vertices) - 1):
                indices = (0, j, j + 1)
                corners = [vertices[k] for k in indices]
                if not _has_area(corners):
                    continue
                result.face(
                    corners,
                    local.m[i],
                    [piece[k][3:] for k in indices],
                )
    return result


def apply(base, colors):
    """Adjust only grass soil; preserve every road, shore and building mesh."""
    terrain = base['terrain']
    if getattr(terrain, 'verge_east_v6', False):
        return
    for case in CASES:
        pavement = _pavement_tree(base, colors, case['bounds'])
        terrain = _repair(terrain, pavement, colors['grass'], case)
    terrain.verge_east_v6 = True
    base['terrain'] = terrain
