"""Editable west-gate components and the accepted distant mesh in gate-local metres."""

from pathlib import Path

import bpy

from geometry import MATERIALS, Mesh


def west_gate(_colors, detail):
    near_prefix = 'west-gate-near-'
    if 'west-gate-far' not in bpy.data.meshes:
        asset = Path(__file__).parent / 'assets' / 'west-gate.blend'
        with bpy.data.libraries.load(str(asset)) as (source, target):
            target.meshes = source.meshes

    names = (
        sorted(name for name in bpy.data.meshes.keys() if name.startswith(near_prefix))
        if detail
        else ['west-gate-far']
    )
    gate = Mesh()
    for name in names:
        data = bpy.data.meshes[name]
        indices = []
        for mat in data.materials:
            if mat not in MATERIALS:
                MATERIALS.append(mat)
            indices.append(MATERIALS.index(mat))
        part = Mesh()
        part.v = [tuple(vertex.co) for vertex in data.vertices]
        uv = data.uv_layers.active.data
        for face in data.polygons:
            part.f.append(tuple(face.vertices))
            part.m.append(indices[face.material_index])
            part.face_uvs[face.index] = [tuple(uv[k].uv) for k in face.loop_indices]
        gate.add_part(name.removeprefix(near_prefix), part)
    return gate
