"""Street-view located sidewalks at Rongjiang Road and the Bocui Road parking island."""

import json
from functools import lru_cache
from pathlib import Path

from mathutils.bvhtree import BVHTree

from geometry import Mesh, tile_material
from site_geometry import mesh_triangles


def _sampler(source, bounds):
    local = Mesh()
    x0, y0, x1, y1 = bounds
    for face in source.f:
        points = [source.v[i] for i in face]
        if (
            all(p[0] < x0 for p in points)
            or all(p[0] > x1 for p in points)
            or all(p[1] < y0 for p in points)
            or all(p[1] > y1 for p in points)
        ):
            continue
        local.face(points, 0)
    tree = BVHTree.FromPolygons(
        local.v, [tri for tri, _ in mesh_triangles(local)], all_triangles=True
    )

    @lru_cache(maxsize=None)
    def height(x, y):
        hit = tree.ray_cast((x, y, 200), (0, 0, -1), 400)[0]
        if hit is None:
            raise ValueError(f'West sidewalk missing support at {(x, y)}')
        return hit.z

    return height


def _road_datum(sports, x, y, road):
    if sports:
        # West edge of the OSM Rongjiang carriageway. Sample five cm inside
        # the existing edge so edits to the connecting road grade propagate.
        edge = -144.96914 - (y + 390) * 0.00143939
        return road(edge + 0.05, y)
    # South edge of Bocui and north edge of the separate parking aisle.
    north = -593.57669 + (x + 45) * 0.00979
    south = -595.51587 + (x + 45) * 0.00184
    fraction = max(0, min(1, (y - south) / (north - south)))
    return road(x, south - 0.05) * (1 - fraction) + road(x, north + 0.05) * fraction


def apply_roads(base, C):
    """Add two disjoint road meshes after build_physics_street_grade(base, C)."""
    profiles = json.loads(
        Path(__file__).with_name('road_review_west_profiles.json').read_text()
    )
    tile_material(
        C, 'westWalkRedBond', 'road-review-west-red-bond.png', (0.36, 0.12, 0.09)
    )
    for profile in profiles:
        key = 'site-road-west-' + profile['id']
        if key in base:
            continue
        sports = profile['id'] == 'rongjiang-sports'
        bounds = (-151, -445, -139, -375) if sports else (-60, -600, -33, -588)
        road = _sampler(base['roads'], bounds)
        ground = _sampler(base['terrain'], bounds)
        deck = Mesh()
        vertices = []
        for x, y in profile['vertices']:
            z = max(_road_datum(sports, x, y, road) + 0.105, ground(x, y) + 0.035)
            vertices.append((x, y, z))
        soil_edges = {}
        for material, *indices in profile['faces']:
            points = [vertices[i] for i in indices]
            if material == 'brick':
                # Along-street running bond, local metric UV origin.
                uv = [
                    ((y + 440, x + 148) if sports else (x + 56, y + 596))
                    for x, y, _ in points
                ]
                deck.face(
                    points, C['westWalkRedBond'], [(u / 0.8, v / 0.8) for u, v in uv]
                )
            elif material == 'pit':
                deck.face([(x, y, z - 0.025) for x, y, z in points], C['gateRecess'])
                for i, j in zip(indices, indices[1:] + indices[:1]):
                    pair = (min(i, j), max(i, j))
                    if pair in soil_edges:
                        del soil_edges[pair]
                    else:
                        soil_edges[pair] = (i, j)
            else:
                deck.face(points, C[material])
        for i, j in soil_edges.values():
            a, b = vertices[i], vertices[j]
            deck.face(
                [a, b, (*b[:2], b[2] - 0.025), (*a[:2], a[2] - 0.025)], C['courtFrame']
            )
        for i, j in profile['perimeter']:
            a, b = vertices[i], vertices[j]
            foot = [(x, y, min(z - 0.12, ground(x, y) - 0.06)) for x, y, z in (a, b)]
            deck.face([a, b, foot[1], foot[0]], C['curb'])
            # The sports frontage photograph shows lawn meeting the back
            # of the kerb. Tie that edge into the DEM within two metres,
            # feathering away before either driveway.
            if sports and max(a[0], b[0]) < -147.5 and abs(a[1] - b[1]) > 0.01:
                right = sorted((a, b), key=lambda p: p[1])
                inner, outer = [], []
                for x, y, z in right:
                    weight = max(0, min(1, (-381 - y) / 2, (y + 439) / 2))
                    g = ground(x, y)
                    inner.append((x, y, g + (z - 0.035 - g) * weight))
                    edge_x = x - 2.0 * weight
                    outer.append((edge_x, y, ground(edge_x, y)))
                for tri in (
                    (inner[0], inner[1], outer[1]),
                    (inner[0], outer[1], outer[0]),
                ):
                    if len({p[:2] for p in tri}) == 3:
                        deck.face(tri, C['grass'])
        base[key] = deck
