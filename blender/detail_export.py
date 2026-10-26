"""Shared export precision for the gate and its small facade details."""
import bpy
from export_attributes import omit_unused_uvs


def export_detail(obj, target):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    with omit_unused_uvs(deduplicate_vertices=True):
        bpy.ops.export_scene.gltf(
            filepath=str(target), export_format='GLB', use_selection=True,
            export_extras=True, export_cameras=False, export_lights=False,
            export_draco_mesh_compression_enable=True,
            export_draco_mesh_compression_level=7,
            export_draco_position_quantization=18,
            # Thin textured panel returns need more than the default 12-bit UVs.
            export_draco_texcoord_quantization=16,
            export_draco_normal_quantization=10,
            export_materials='EXPORT')
