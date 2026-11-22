"""Keep the existing five-metre farm lane visible through the sloping terrain west of Daoxiang Lake."""

from math import hypot

from geometry import Mesh
from shore_geometry import bounds, overlaps
from site_geometry import mesh_triangles
from west22_ground import split


def lower_farm_road_bed(terrain, roads, colors):
    from mathutils.bvhtree import BVHTree

    # Straight part of way/760167447, at least 35 m from the lake.
    start = (-771.4, 814.0)
    end = (-773.8, 831.4)
    box = (-782.0, 806.0, -762.5, 839.5)
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = hypot(dx, dy)
    ux, uy = dx / length, dy / length
    local_road = Mesh()
    for face, material in zip(roads.f, roads.m):
        if material == colors['road']:
            coords = [roads.v[i] for i in face]
            if overlaps(bounds(coords), box):
                local_road.face(coords, 0)
    tree = BVHTree.FromPolygons(
        local_road.v, [t for t, _ in mesh_triangles(local_road)], all_triangles=True
    )

    def road_z(x, y):
        point = tree.ray_cast((x, y, 80), (0, 0, -1), 160)[0]
        if point is None:
            raise ValueError(f'Farm lane missing at {(x, y)}')
        return point.z

    # Recover the plane from the built carriageway, including its crossfall.
    low = road_z(*start)
    grade = (road_z(*end) - low) / length
    crossfall = road_z(start[0] - uy, start[1] + ux) - low

    def frame(p):
        x, y = p[0] - start[0], p[1] - start[1]
        return x * ux + y * uy, -x * uy + y * ux

    # The central bed sits just below the road. Side slopes end at the uncut ground.
    half_width, shoulder = 2.53, 0.52
    planes = [
        (0, 0, 0),
        (0, shoulder, -shoulder * half_width),
        (0, -shoulder, -shoulder * half_width),
        (-shoulder, 0, 0),
        (shoulder, 0, -shoulder * length),
    ]

    def elevation(plane, point):
        s, t = frame(point)
        return (
            low - 0.075 + (grade + plane[0]) * s + (crossfall + plane[1]) * t + plane[2]
        )

    local = Mesh()
    source_ids = []
    for i, face in enumerate(terrain.f):
        coords = [terrain.v[j] for j in face]
        if overlaps(bounds(coords), box):
            local.face(coords, 0)
            source_ids.append(i)
    patches = {}
    for tri, local_index in mesh_triangles(local):
        polygon = [tuple(local.v[i]) for i in tri]
        original = source_ids[local_index]
        changed, pieces = polygon, []
        for plane in planes:
            changed, outside = split(changed, lambda q: q[2] - elevation(plane, q))
            if len(outside) >= 3:
                pieces.append(outside)
            if len(changed) < 3:
                break
        if len(changed) < 3:
            patches.setdefault(original, []).append((False, polygon))
            continue
        for plane in planes:
            patch = changed
            for other in planes:
                if plane != other:
                    patch, _ = split(
                        patch, lambda q: elevation(plane, q) - elevation(other, q)
                    )
                    if len(patch) < 3:
                        break
            if len(patch) >= 3:
                pieces.append([(q[0], q[1], elevation(plane, q)) for q in patch])
        patches.setdefault(original, []).extend((True, piece) for piece in pieces)
    result = Mesh()
    result.v = list(terrain.v)
    result.ground_uv_bounds = list(terrain.ground_uv_bounds)
    result.xy_uv_materials = set(terrain.xy_uv_materials)
    for i, (face, material) in enumerate(zip(terrain.f, terrain.m)):
        parts = patches.get(i, ())
        if not any(changed for changed, _ in parts):
            if i in terrain.face_uvs:
                result.face_uvs[len(result.f)] = terrain.face_uvs[i]
            result.f.append(face)
            result.m.append(material)
            continue
        if i in terrain.face_uvs:
            raise ValueError('Farm road bed overlaps separately mapped ground UVs')
        for _, polygon in parts:
            result.face(polygon, material)
    return result
