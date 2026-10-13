"""Export bounded terrain separately, welding its seam to decoded global vertices."""
import json,tempfile
from pathlib import Path
import bpy
from mathutils import Vector,Matrix
from mathutils.kdtree import KDTree
from terrain_planar import planar_terrain_candidate
from export_attributes import omit_unused_uvs,omit_zero_area_terrain_faces
from preserve_glb_geometry import replace_compressed_node_parts,compact_buffer_views

def subset(source,ids,name):
    m=source.data;vertices=[];faces=[];uvs=[]
    for i in ids:
        p=m.polygons[i];start=len(vertices)
        vertices.extend(tuple(m.vertices[k].co) for k in p.vertices)
        faces.append(tuple(range(start,len(vertices))))
        uvs.append([tuple(m.uv_layers.active.data[k].uv) for k in p.loop_indices])
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces)
    for material in m.materials:mesh.materials.append(material)
    uv=mesh.uv_layers.new(name=m.uv_layers.active.name)
    for face,i,values in zip(mesh.polygons,ids,uvs):
        face.material_index=m.polygons[i].material_index;face.use_smooth=m.polygons[i].use_smooth
        for k,v in zip(face.loop_indices,values):uv.data[k].uv=v
    obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj);obj['layer']='terrain'
    return obj

def export(obj,path,bits):
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    with omit_zero_area_terrain_faces(obj,position_quantization_bits=bits),planar_terrain_candidate(obj),omit_unused_uvs(deduplicate_vertices=True):
        bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_extras=True,
            export_draco_mesh_compression_enable=True,export_draco_mesh_compression_level=6,
            export_draco_position_quantization=bits,export_draco_texcoord_quantization=18,
            export_draco_normal_quantization=6,export_materials='EXPORT',export_cameras=False,export_lights=False)

def decoded_positions(path):
    old=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(path));bpy.context.view_layer.update()
    added=set(bpy.data.objects)-old
    values={tuple(o.matrix_world@v.co) for o in added if o.type=='MESH' for v in o.data.vertices}
    for o in added:bpy.data.objects.remove(o,do_unlink=True)
    tree=KDTree(len(values))
    for i,v in enumerate(values):tree.insert(Vector(v),i)
    tree.balance();return tree

def replace_with_local_precision(target,source,regions,*,report_directory=None):
    m=source.data
    if (source.get('layer')!='terrain' or source.matrix_world!=Matrix.Identity(4)
            or source.modifiers or m.shape_keys or m.has_custom_normals
            or any(p.use_smooth for p in m.polygons) or len(m.uv_layers)!=1
            or m.color_attributes or len(set(p.material_index for p in m.polygons))!=1):
        raise ValueError('Local precision requires plain flat terrain with one UV layer and material')
    supported={'position','.edge_verts','.corner_vert','.corner_edge','material_index','sharp_face','sharp_edge',m.uv_layers.active.name}
    if any(a.name not in supported and not a.name.startswith('.') for a in m.attributes):
        raise ValueError('Unsupported terrain attribute')
    local=[];outer=[]
    for p in m.polygons:
        vs=[m.vertices[k].co for k in p.vertices]
        hit=any(max(v.x for v in vs)>=x0 and min(v.x for v in vs)<=x1
                and max(v.y for v in vs)>=y0 and min(v.y for v in vs)<=y1
                for x0,y0,x1,y1 in regions)
        (local if hit else outer).append(p.index)
    if not local or not outer:raise ValueError('Precision regions must select a bounded subset of terrain')
    main=subset(source,outer,'terrain-main');patch=subset(source,local,'terrain-local')
    try:
        coordinates=lambda o:{tuple(v.co) for v in o.data.vertices}
        seam=coordinates(main)&coordinates(patch)
        if not seam:raise ValueError('Missing local terrain seam')
        bounds=lambda o:[min(v.co[k] for v in o.data.vertices) for k in range(3)]+[max(v.co[k] for v in o.data.vertices) for k in range(3)]
        if bounds(main)!=bounds(source):raise ValueError('Global position bounds changed')
        with tempfile.TemporaryDirectory(prefix='gxu-terrain-local-') as directory:
            directory=Path(directory);a=directory/'main.glb';b=directory/'local.glb'
            export(main,a,18);tree=decoded_positions(a);snapped={}
            for p in seam:
                q,_,distance=tree.find(Vector(p))
                if distance>=.025:raise ValueError('Terrain seam exceeds global position precision')
                snapped[p]=tuple(q)
            for v in patch.data.vertices:
                if tuple(v.co) in snapped:v.co=snapped[tuple(v.co)]
            export(patch,b,26);decoded=decoded_positions(b)
            seam_error=max(decoded.find(Vector(p))[2] for p in snapped.values())
            if seam_error>=.0001:raise ValueError('Decoded terrain seam is discontinuous')
            replace_compressed_node_parts(target,'terrain',[a.read_bytes(),b.read_bytes()])
            compact_buffer_views(target,optimize_jpegs=True)
        record=dict(passed=True,mainPolygons=len(outer),localPolygons=len(local),seamVertices=len(seam),maximumDecodedSeamError=seam_error,mainPositionBits=18,localPositionBits=26,regions=regions)
        if report_directory is not None:
            report_directory.mkdir(parents=True,exist_ok=True)
            (report_directory/'local-precision.json').write_text(json.dumps(record,indent=2)+'\n')
        return record
    finally:
        for obj in [main,patch]:
            mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(mesh)
