"""Shared bounded northern base export: ~2 cm worst-case position grid."""
import bpy
from export_attributes import omit_unused_uvs


def export_north_base(obj,path):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    with omit_unused_uvs():
        bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_extras=True,
            export_draco_mesh_compression_enable=True,export_draco_mesh_compression_level=10,
            export_draco_position_quantization=14,export_draco_normal_quantization=6,
            export_materials='EXPORT',export_cameras=False,export_lights=False)


def repack_north_base(path,objects,keys):
    import tempfile
    from pathlib import Path
    from update_south_gate import replace_node_geometry,compact_static_accessors
    from preserve_glb_geometry import compact_buffer_views
    with tempfile.TemporaryDirectory(prefix='gxu-north-base-') as directory:
        temp=Path(directory)/'node.glb'
        for obj in objects:
            if obj.name in keys:
                export_north_base(obj,temp)
                replace_node_geometry(temp.read_bytes(),path,obj.name)
    compact_static_accessors(path);compact_buffer_views(path)
