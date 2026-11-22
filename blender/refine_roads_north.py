"""Tie three photographed northern teaching entrances to their existing road edges."""

import json
from copy import copy
from pathlib import Path


def _signature(points):
    return '|'.join(','.join(f'{v:.7f}' for v in pt) for pt in points)


def apply(base, colors):
    """Replace only the affected path triangles on the existing road-ground node."""
    path = base['north-campus-roads']
    if getattr(path, 'north_teaching_entrances_fitted', False):
        return
    config = json.loads(
        Path(__file__).with_name('refine_roads_north_mesh.json').read_text()
    )
    anchors = {tuple(pt) for pt in config['roadAnchors']}
    anchors.difference_update(map(tuple, base['roads'].v))
    if anchors:
        raise ValueError('Northern teaching entrance road elevations have changed')
    expected = config['sourceFaces']
    found = set()
    result = copy(path)
    result.v = path.v.copy()
    result.f = []
    result.m = []
    result.face_uvs = {}
    paving = colors['path']
    for i, (face, material) in enumerate(zip(path.f, path.m)):
        key = _signature([path.v[j] for j in face]) if material == paving else None
        if key in expected:
            if i in path.face_uvs:
                raise ValueError('Northern entrance paving UV projection has changed')
            found.add(key)
            for retained in expected[key]:
                result.face(retained, paving)
        else:
            if i in path.face_uvs:
                result.face_uvs[len(result.f)] = path.face_uvs[i]
            result.f.append(face)
            result.m.append(material)
    if found != expected.keys():
        raise ValueError('Northern teaching entrance source triangulation has changed')
    for triangle in config['paving']:
        result.face(triangle, paving)
    result.north_teaching_entrances_fitted = True
    base['north-campus-roads'] = result
