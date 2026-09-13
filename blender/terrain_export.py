"""Keep fine ground triangles and their meter-scaled UVs on matching grids."""
import bpy,tempfile
from pathlib import Path
from preserve_glb_geometry import preserve_geometry,compact_buffer_views

TERRAIN_BITS=18

def replace_precise_terrain(path,objects):
    terrain=[o for o in objects if o.get('layer')=='terrain']
    if not terrain:return
    if len(terrain)!=1:raise ValueError('Expected one aggregated terrain object')
    bpy.ops.object.select_all(action='DESELECT');terrain[0].select_set(True)
    with tempfile.TemporaryDirectory(prefix='gxu-terrain-export-') as directory:
        precise=Path(directory)/'terrain.glb'
        bpy.ops.export_scene.gltf(filepath=str(precise),export_format='GLB',use_selection=True,export_extras=True,
            export_draco_mesh_compression_enable=True,export_draco_mesh_compression_level=6,
            export_draco_position_quantization=TERRAIN_BITS,export_draco_texcoord_quantization=TERRAIN_BITS,
            export_draco_normal_quantization=6,export_materials='EXPORT',export_cameras=False,export_lights=False)
        preserve_geometry(precise.read_bytes(),path,['terrain'])
    compact_buffer_views(path)
