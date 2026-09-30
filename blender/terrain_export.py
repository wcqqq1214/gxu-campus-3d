"""Keep graded ground and ordinary roads accurate after Draco quantization."""
import bpy,tempfile,re
from pathlib import Path
from preserve_glb_geometry import preserve_geometry,compact_buffer_views
from export_attributes import omit_unused_uvs

TERRAIN_BITS=18
ROAD_BITS=17


def replace_precise_terrain(path,objects):
    terrain=[o for o in objects if o.get('layer')=='terrain']
    if not terrain:return
    if len(terrain)!=1:raise ValueError('Expected one aggregated terrain object')
    roads=[o for o in objects if re.sub(r'\.\d{3,}$','',o.name)=='roads']
    if len(roads)!=1:raise ValueError('Expected one aggregated ordinary road object')
    # The campus-wide road bounding box makes 15-bit Z steps about 6 cm.
    # Clipping a footprint can shift that grid even for retained road planes.
    # A finer grid for the ordinary service-road material keeps the exported
    # height within contact tolerance without raising every road material cost.
    for obj,bits,name in [(terrain[0],TERRAIN_BITS,'terrain'),(roads[0],ROAD_BITS,'roads')]:
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
        with tempfile.TemporaryDirectory(prefix='gxu-ground-export-') as directory:
            precise=Path(directory)/'ground.glb'
            with omit_unused_uvs():
                bpy.ops.export_scene.gltf(filepath=str(precise),export_format='GLB',use_selection=True,export_extras=True,
                    export_draco_mesh_compression_enable=True,export_draco_mesh_compression_level=6,
                    export_draco_position_quantization=bits,export_draco_texcoord_quantization=TERRAIN_BITS if obj==terrain[0] else 11,
                    export_draco_normal_quantization=6,export_materials='EXPORT',export_cameras=False,export_lights=False)
            preserve_geometry(precise.read_bytes(),path,[name],materials={'road'} if obj==roads[0] else None)
    compact_buffer_views(path)
