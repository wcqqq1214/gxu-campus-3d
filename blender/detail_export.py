"""Export facade detail and report its decoded geometry allocation."""

import bpy

from export_attributes import omit_unused_uvs
from preserve_glb_geometry import unpack


def export_detail(obj, target, *, base_chunk=False):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    with omit_unused_uvs(deduplicate_vertices=True):
        bpy.ops.export_scene.gltf(
            filepath=str(target),
            export_format='GLB',
            use_selection=True,
            export_extras=True,
            export_cameras=False,
            export_lights=False,
            export_draco_mesh_compression_enable=True,
            export_draco_mesh_compression_level=7,
            export_draco_position_quantization=15 if base_chunk else 18,
            # Base chunks use the main campus budget. Close textured returns need finer UVs.
            export_draco_texcoord_quantization=12 if base_chunk else 16,
            export_draco_normal_quantization=6 if base_chunk else 10,
            export_materials='EXPORT',
        )


def geometry_bytes(raw):
    """Four bytes per decoded attribute component and index in the streaming budget."""
    doc, _ = unpack(raw)
    widths = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}
    total = 0
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            for index in (*primitive['attributes'].values(), primitive['indices']):
                accessor = doc['accessors'][index]
                total += 4 * accessor['count'] * widths[accessor['type']]
    return total
