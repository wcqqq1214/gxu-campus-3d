"""The market's five mapped roofs share a street-level datum and one editable asset."""

from pathlib import Path

import bpy

from civil_forecourt_grade import grade_mesh
from geometry import MATERIALS, Mesh

DATUM = 4.27


def market_building(building_id, detail):
    suffix = '-near' if detail else '-base'
    name = 'west-market-' + building_id.split('/')[1] + suffix
    if name not in bpy.data.meshes:
        asset = Path(__file__).parent / 'assets' / 'west-market.blend'
        with bpy.data.libraries.load(str(asset)) as (source, target):
            target.meshes = [key for key in source.meshes if key.endswith(suffix)]

    data = bpy.data.meshes[name]
    slots = []
    for mat in data.materials:
        if mat not in MATERIALS:
            MATERIALS.append(mat)
        slots.append(MATERIALS.index(mat))
    mesh = Mesh()
    mesh.v = [tuple(v.co) for v in data.vertices]
    uv = data.uv_layers.active.data
    for face in data.polygons:
        mesh.f.append(tuple(face.vertices))
        mesh.m.append(slots[face.material_index])
        mesh.face_uvs[face.index] = [tuple(uv[k].uv) for k in face.loop_indices]
    return mesh


def market_ground(mesh, clearance=0):
    # The photographed curb is 14 cm high. Blend the coarse DEM into the
    # entrance plane so the published road cannot cover the curb or the ramp.
    return grade_mesh(
        mesh,
        {
            'core': (-599, -280, -528, -233),
            'extent': (-603, -284, -524, -228),
            'origin': (-531.5, -238.5),
            'gradient': (0, 0),
            'groundHeight': DATUM - 0.025,
            'meshStep': 7,
        },
        clearance,
    )
