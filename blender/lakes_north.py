"""Fit northern lake beds and pond dividers to the reviewed terrain mesh."""

import hashlib
import json
import struct
from pathlib import Path


def _face_key(points):
    # Face indices change when another district subdivides its own terrain.
    coordinates = sorted(tuple(round(v * 100000) for v in p) for p in points)
    packed = b''.join(struct.pack('<3i', *xyz) for xyz in coordinates)
    return hashlib.sha256(packed).hexdigest()[:24]


def _water_key(surface):
    source = [surface['vertices'], surface['triangles'], surface['waterLevel']]
    return hashlib.sha256(
        json.dumps(source, separators=(',', ':')).encode()
    ).hexdigest()


def apply_lakes(base, surfaces, C):
    """Replace only matched ground faces and add the unmapped pond to existing water."""
    terrain, water = base['terrain'], base['water']
    if getattr(terrain, '_lakes_north_applied', False):
        return
    patch = json.loads(Path(__file__).with_name('lakes_north_ground.json').read_text())
    target = patch['surfaces']
    found = {
        s['id']: _water_key(s)
        for s in surfaces
        if s['id'] in target and not s.get('suppressed')
    }
    if found != target:
        raise ValueError(
            'Northern water geometry has changed. Recheck the shoreline fit.'
        )

    pending = patch['ground']
    matched = {}
    x0, y0, x1, y1 = patch['bounds']
    for index, face in enumerate(terrain.f):
        x, y, _ = terrain.v[face[0]]
        if x0 <= x <= x1 and y0 <= y <= y1:
            key = _face_key(terrain.v[i] for i in face)
            if key in pending:
                if key in matched or index in terrain.face_uvs:
                    raise ValueError(
                        'Unexpected duplicate or UV-mapped northern ground face.'
                    )
                matched[key] = index
    if len(matched) != len(pending):
        raise ValueError('Northern ground no longer matches the reviewed mesh.')

    # Reuse every original face corner. Mesh.face allocates private vertices
    # per face. Shared patch vertices on neighboring faces have identical XYZ.
    points = patch['vertices']
    caps = []
    for key, index in matched.items():
        original = terrain.f[index]
        triangles = pending[key]
        used = dict.fromkeys(i for *vertex_ids, _ in triangles for i in vertex_ids)
        replacements = iter(original)
        for i in used:
            v = next(replacements, None)
            if v is None:
                v = len(terrain.v)
                terrain.v.append(points[i])
            else:
                terrain.v[v] = points[i]
            used[i] = v
        ground = terrain.m[index]
        for j, (a, b, c, hard_bank) in enumerate(triangles):
            face = (used[a], used[b], used[c])
            if hard_bank:
                caps.append((a, b, c))
            if j:
                terrain.f.append(face)
                terrain.m.append(ground)
            else:
                terrain.f[index] = face
                terrain.m[index] = ground

    # The precise terrain exporter requires one ground material. Keep a
    # continuous earth embankment below each narrow, embedded masonry crown.
    # Boundary sides stop below the terrain, including at both ends.
    stone = C['stone']
    boundary = {}

    def offset(i, dz):
        x, y, z = points[i]
        return x, y, z + dz

    for a, b, c in caps:
        water.face([offset(i, 0.13) for i in (a, b, c)], stone)
        for i, j in ((a, b), (b, c), (c, a)):
            if (j, i) in boundary:
                del boundary[j, i]
            else:
                boundary[i, j] = True
    for i, j in boundary:
        water.face(
            [offset(i, -0.12), offset(j, -0.12), offset(j, 0.13), offset(i, 0.13)],
            stone,
        )

    pond = patch['pond']
    for face in pond['triangles']:
        water.face([pond['vertices'][i] for i in face], C['water'])
    terrain._lakes_north_applied = True
