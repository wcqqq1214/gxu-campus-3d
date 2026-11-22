"""Support the grounded east arm at the west entrance to the civil platform."""

from copy import copy
from functools import lru_cache

from mathutils.bvhtree import BVHTree

from geometry import Mesh
from next_terrain_north import has_area, replace_local
from refine_roads_west import _bands, _source_uv, _split
from shore_geometry import bounds, overlaps
from site_geometry import mesh_triangles

# Frame follows the 5 m wide service road from its western OSM end.
WEST, EAST = -725.5, -696.0
REACH = 9.0
BOUNDS = (WEST, -810.7, EAST, -792.2)


def _axis(x):
    return -801.604188 + (x + 722.474078) * 0.014078


def _road_surface(mesh, material):
    tile = Mesh()
    for face, mat in zip(mesh.f, mesh.m):
        if mat == material:
            pts = [mesh.v[j] for j in face]
            if overlaps(bounds(pts), BOUNDS):
                tile.face(pts, mat)
    tris = [ids for ids, _ in mesh_triangles(tile)]
    tree = BVHTree.FromPolygons(tile.v, tris, all_triangles=True)

    # Upright road-edge triangles collapse to lines in XY. They can win a
    # nearest query outside the tread without defining any height function.
    treads = []
    for ids in tris:
        a, b, c = (tile.v[i] for i in ids)
        normal = tuple(
            (b[j] - a[j]) * (c[k] - a[k]) - (b[k] - a[k]) * (c[j] - a[j])
            for j, k in ((1, 2), (2, 0), (0, 1))
        )
        if abs(normal[2]) > 0.6 * max(abs(normal[0]), abs(normal[1]), 1e-8):
            treads.append(ids)
    flat = BVHTree.FromPolygons(
        [(x, y, 0.0) for x, y, z in tile.v], treads, all_triangles=True
    )

    @lru_cache(maxsize=12000)
    def height(x, y):
        hit = tree.ray_cast((x, y, 50), (0, 0, -1), 100)[0]
        if hit is not None:
            return hit.z, 0.0
        # The fork has two intersecting alignments. Extend the closest real rim
        # (including the sloping north-south road) onto its own shoulder.
        pt, _, idx, distance = flat.find_nearest((x, y, 0.0), 4.0)
        if pt is None:
            return None, 0.0
        a, b, c = (tile.v[j] for j in treads[idx])
        u, v = b[0] - a[0], b[1] - a[1]
        s, t = c[0] - a[0], c[1] - a[1]
        det = u * t - v * s
        if abs(det) < 1e-9:
            return None, 0.0
        dx, dy = pt.x - a[0], pt.y - a[1]
        z = (
            a[2]
            + (dx * t - dy * s) / det * (b[2] - a[2])
            + (u * dy - v * dx) / det * (c[2] - a[2])
        )
        return z, distance

    return height


def _smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3.0 - 2.0 * t)


def _cells(poly):
    # The second coordinate measures northing from the service-road axis.
    for axis, limit, keep_high in (
        (0, WEST, True),
        (0, EAST, False),
        (1, -REACH, True),
        (1, REACH, False),
    ):
        low, high = _split(poly, axis, limit)
        poly, outside = (high, low) if keep_high else (low, high)
        if has_area(outside):
            yield outside, False
        if not has_area(poly):
            return
    for strip in _bands(
        poly,
        1,
        (
            -8.0,
            -7.0,
            -6.0,
            -5.5,
            -4.5,
            -3.5,
            -2.65,
            -2.5,
            -1.25,
            0.0,
            1.25,
            2.5,
            2.65,
            3.5,
            4.5,
            5.5,
            6.0,
            7.0,
            8.0,
        ),
    ):
        for cell in _bands(
            strip,
            0,
            sorted(set(range(-725, -696)) | {j / 4 for j in range(-2900, -2872)}),
        ):
            if has_area(cell):
                yield cell, True


def apply(base, colors):
    terrain = base['terrain']
    if getattr(terrain, '_west_platform_bed', False):
        return
    height = _road_surface(base['roads'], colors['road'])

    def support(pts):
        frame = [(x, y - _axis(x), z, *uv) for x, y, z, *uv in pts]
        for piece, inside in _cells(frame):
            ring = []
            for x, side, z, *uv in piece:
                y = side + _axis(x)
                if inside:
                    # Sample the road at this station. Carry the rim briefly past
                    # the edge, then taper into the sloping original soil.
                    ref, distance = height(x, y)
                    if ref is not None:
                        w = _smooth((x - WEST) / 3.0) * _smooth((EAST - x) / 6.0)
                        w *= _smooth((REACH - abs(side)) / 2.5)
                        w *= _smooth((4.0 - distance) / 3.85)
                        z += w * max(0.0, ref - 0.055 - z)
                ring.append((x, y, z, *uv))
            yield ring

    # Capture the source UV basis before locally changing the slope.
    source = copy(terrain)
    source.face_uvs = dict(terrain.face_uvs)
    for i, (face, mat) in enumerate(zip(terrain.f, terrain.m)):
        if mat == colors['grass'] and i not in source.face_uvs:
            pts = [terrain.v[j] for j in face]
            if overlaps(bounds(pts), BOUNDS):
                source.face_uvs[i] = _source_uv(terrain, i, pts, True)
    result = replace_local(source, BOUNDS, colors['grass'], support)
    result._west_platform_bed = True
    base['terrain'] = result
