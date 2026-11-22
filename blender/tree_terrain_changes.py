"""Keep grounded trees on their local terrain throughout road and terrain edits."""

from mathutils.bvhtree import BVHTree

from site_geometry import mesh_triangles


def tree_surface_heights(rows, terrain):
    triangles = [indices for indices, _ in mesh_triangles(terrain)]
    surface = BVHTree.FromPolygons(terrain.v, triangles, all_triangles=True)
    heights = []
    for x, y, *_ in rows:
        hit = surface.ray_cast((x, y, 200), (0, 0, -1), 400)[0]
        heights.append(None if hit is None else hit.z)
    return heights


def apply_tree_heights(rows, previous_surface, final_surface):
    moved = []
    for i, (row, previous, current) in enumerate(
        zip(rows, previous_surface, final_surface, strict=True)
    ):
        if previous is None:
            continue
        if current is None:
            raise ValueError(f'Terrain edits removed tree support at {row[:2]}')
        if abs(current - previous) > 0.01:
            row[4] = round(current, 6)
            moved.append(i)
    return moved


def update_tree_contacts(rows, previous_surface, terrain):
    return apply_tree_heights(
        rows, previous_surface, tree_surface_heights(rows, terrain)
    )
