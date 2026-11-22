"""North-campus pedestrian paving fitted to the stage3 pre-export road mesh."""

import json
from copy import copy
from pathlib import Path

from geometry import Mesh, tile_material
from road_review_north_bed import fit_farm_bed


def _replace_faces(source, replacements, expected_material, bounds):
    """Keep every unaltered face and the uncovered fragments of each cut face."""
    result = copy(source)
    result.v = source.v.copy()
    result.f = []
    result.m = []
    result.face_uvs = {}
    matched = set()
    x0, y0, x1, y1 = bounds
    for i, indices in enumerate(source.f):
        x, y, _ = source.v[indices[0]]
        key = None
        if x0 <= x <= x1 and y0 <= y <= y1:
            coordinates = [source.v[j] for j in indices]
            key = '|'.join(','.join(f'{n:.6f}' for n in pt) for pt in coordinates)
        if key in replacements:
            if source.m[i] != expected_material or i in source.face_uvs:
                raise ValueError('North paving source material or UV changed')
            matched.add(key)
            for triangle in replacements[key]:
                result.face(triangle, source.m[i])
        else:
            if i in source.face_uvs:
                result.face_uvs[len(result.f)] = source.face_uvs[i]
            result.f.append(indices)
            result.m.append(source.m[i])
    if matched != replacements.keys():
        raise ValueError('North paving source triangulation changed')
    return result


def apply_roads(base, C):
    """Fit the reviewed pedestrian surfaces after build_physics_street_grade."""
    path = Path(__file__).with_name('road_review_north_mesh.json')
    patch = json.loads(path.read_text())
    nodes = patch['nodes']
    existing = set(nodes).intersection(base)
    if existing == set(nodes):
        base['terrain'] = fit_farm_bed(base['terrain'], base['roads'], C['road'])
        return
    if existing:
        raise ValueError('Incomplete north-campus pedestrian mesh set')
    for layer, samples in patch['anchors'].items():
        missing = {tuple(pt) for pt in samples}
        missing.difference_update(map(tuple, base[layer].v))
        if missing:
            raise ValueError(
                f'North-campus road review requires updated {layer} anchors'
            )

    result = {}
    for layer, material in [('north-campus-roads', 'path'), ('roads', 'road')]:
        replacements = patch['remesh'][layer]
        # The bounds constrain only the first-vertex signature lookup. This also
        # preserves unrelated edits made by other review regions on the same mesh.
        first = [key.split('|', 1)[0].split(',') for key in replacements]
        xs = [float(pt[0]) for pt in first]
        ys = [float(pt[1]) for pt in first]
        bounds = min(xs) - 0.001, min(ys) - 0.001, max(xs) + 0.001, max(ys) + 0.001
        result[layer] = _replace_faces(base[layer], replacements, C[material], bounds)
    tile_material(
        C, 'northRoadRunningBrick', 'road_review_north_brick.png', (0.38, 0.22, 0.18)
    )
    tile_material(
        C, 'northRoadSquareSlab', 'road_review_north_slab.png', (0.46, 0.44, 0.40)
    )
    for name, data in nodes.items():
        mesh = Mesh()
        for material, indices, uv in data['faces']:
            mesh.face([data['vertices'][i] for i in indices], C[material], uv)
        result[name] = mesh
    result['terrain'] = fit_farm_bed(base['terrain'], base['roads'], C['road'])
    base.update(result)
