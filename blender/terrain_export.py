"""Keep graded ground and ordinary roads accurate after Draco quantization."""
import bpy,tempfile,re,sys
from pathlib import Path
if __name__=='__main__':sys.path.insert(0,str(Path(__file__).resolve().parent))
from preserve_glb_geometry import preserve_geometry,compact_buffer_views
from export_attributes import omit_unused_uvs,omit_zero_area_terrain_faces

TERRAIN_BITS=18
ROAD_BITS=18
ROAD_UV_BITS=10
LOCAL_ROAD_UV_BITS=11


def replace_precise_terrain(path,objects,*,terrain_only=False):
    terrain=[o for o in objects if o.get('layer')=='terrain']
    if not terrain:return
    if len(terrain)!=1:raise ValueError('Expected one aggregated terrain object')
    roads=[o for o in objects if re.sub(r'\.\d{3,}$','',o.name)=='roads']
    if not terrain_only and len(roads)!=1:raise ValueError('Expected one aggregated ordinary road object')
    # Ordinary materials share a position domain so common vertices decode
    # identically. Keep the textured service-road material's previous UV budget.
    exports=[(terrain[0],TERRAIN_BITS,18,'terrain',None)]
    if not terrain_only:
        exports.extend([(roads[0],ROAD_BITS,12,'roads',None),
                        (roads[0],ROAD_BITS,ROAD_UV_BITS,'roads',{'road'})])
    # The joined civil service roads use a small position domain. Match the
    # granular-texture UV precision without lowering position precision.
    if not terrain_only:
        exports.extend((o,15,LOCAL_ROAD_UV_BITS,'paving-civil-platform-service-export',{'road'}) for o in objects
                       if re.sub(r'\.\d{3,}$','',o.name)=='paving-civil-platform-service-export')
    for obj,bits,uvbits,name,materials in exports:
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
        with tempfile.TemporaryDirectory(prefix='gxu-ground-export-') as directory:
            precise=Path(directory)/'ground.glb'
            with omit_zero_area_terrain_faces(obj,position_quantization_bits=bits),omit_unused_uvs(deduplicate_vertices=name in ('terrain','roads'),share_position_bounds=name=='roads'):
                bpy.ops.export_scene.gltf(filepath=str(precise),export_format='GLB',use_selection=True,export_extras=True,
                    export_draco_mesh_compression_enable=True,export_draco_mesh_compression_level=6,
                    export_draco_position_quantization=bits,export_draco_texcoord_quantization=uvbits,
                    export_draco_normal_quantization=6,export_materials='EXPORT',export_cameras=False,export_lights=False)
            preserve_geometry(precise.read_bytes(),path,[name],materials=materials)
    compact_buffer_views(path,optimize_jpegs=True)


if __name__=='__main__':
    import argparse,sys
    parser=argparse.ArgumentParser(description='Export only terrain into a candidate base copy; preserve the editable source and manifest.')
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--target',type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    if not args.target.is_file():raise ValueError('Target must be an existing candidate copy of base.glb')
    root=Path(__file__).resolve().parents[1]
    if args.target.resolve()==(root/'public/models/base.glb').resolve():
        raise ValueError('Validate a candidate copy before replacing the published base')
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    replace_precise_terrain(args.target,[bpy.data.objects['terrain']],terrain_only=True)
    print('Candidate terrain export:',args.target,args.target.stat().st_size,flush=True)
