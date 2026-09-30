"""Keep graded ground and ordinary roads accurate after Draco quantization."""
import bpy,tempfile,re
from pathlib import Path
from preserve_glb_geometry import preserve_geometry,compact_buffer_views
from export_attributes import omit_unused_uvs,omit_zero_area_terrain_faces

TERRAIN_BITS=18
ROAD_BITS=18
ROAD_UV_BITS=10
LOCAL_ROAD_UV_BITS=11


def replace_precise_terrain(path,objects):
    terrain=[o for o in objects if o.get('layer')=='terrain']
    if not terrain:return
    if len(terrain)!=1:raise ValueError('Expected one aggregated terrain object')
    roads=[o for o in objects if re.sub(r'\.\d{3,}$','',o.name)=='roads']
    if len(roads)!=1:raise ValueError('Expected one aggregated ordinary road object')
    # Ordinary materials share a position domain so common vertices decode
    # identically. Keep the textured service-road material's previous UV budget.
    exports=[(terrain[0],TERRAIN_BITS,18,'terrain',None),
             (roads[0],ROAD_BITS,12,'roads',None),
             (roads[0],ROAD_BITS,ROAD_UV_BITS,'roads',{'road'})]
    # The joined civil service roads use a small position domain. Match the
    # granular-texture UV precision without lowering position precision.
    exports.extend((o,15,LOCAL_ROAD_UV_BITS,'paving-civil-platform-service-export',{'road'}) for o in objects
                   if re.sub(r'\.\d{3,}$','',o.name)=='paving-civil-platform-service-export')
    for obj,bits,uvbits,name,materials in exports:
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
        with tempfile.TemporaryDirectory(prefix='gxu-ground-export-') as directory:
            precise=Path(directory)/'ground.glb'
            with omit_zero_area_terrain_faces(obj),omit_unused_uvs(deduplicate_vertices=name in ('terrain','roads'),share_position_bounds=name=='roads'):
                bpy.ops.export_scene.gltf(filepath=str(precise),export_format='GLB',use_selection=True,export_extras=True,
                    export_draco_mesh_compression_enable=True,export_draco_mesh_compression_level=6,
                    export_draco_position_quantization=bits,export_draco_texcoord_quantization=uvbits,
                    export_draco_normal_quantization=6,export_materials='EXPORT',export_cameras=False,export_lights=False)
            preserve_geometry(precise.read_bytes(),path,[name],materials=materials)
    compact_buffer_views(path,optimize_jpegs=True)
