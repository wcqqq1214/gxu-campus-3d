"""Full builds suffix export names because editable source objects coexist."""
import bpy,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from terrain_export import replace_precise_terrain
from preserve_glb_geometry import unpack,mesh_nodes_by_name
bpy.ops.wm.read_factory_settings(use_empty=True)
road=bpy.data.materials.new('road');white=bpy.data.materials.new('white')

def mesh(name,layer,z):
    data=bpy.data.meshes.new(name)
    data.from_pydata([(0,0,z),(1,0,z),(1,1,z),(0,1,z)],[],[(0,1,2),(0,2,3)])
    data.materials.append(road);data.materials.append(white);data.polygons[1].material_index=1
    obj=bpy.data.objects.new(name,data);bpy.context.scene.collection.objects.link(obj);obj['layer']=layer
    return obj

# The actual export objects acquire .001, just as in a full campus build.
mesh('terrain','terrain',-1);mesh('roads','roads',-1);mesh('paving-civil-platform-service-export','roads',-1)
objects=[mesh('terrain','terrain',0),mesh('roads','roads',.2),mesh('paving-civil-platform-service-export','roads',.3)]
assert all(o.name.endswith('.001') for o in objects)
bpy.ops.object.select_all(action='DESELECT')
for obj in objects:obj.select_set(True)
with tempfile.TemporaryDirectory() as directory:
    path=Path(directory)/'base.glb'
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_extras=True,
        export_draco_mesh_compression_enable=True,export_draco_position_quantization=15)
    before,blob=unpack(path.read_bytes())
    def payload(doc,binary,name,material):
        node=mesh_nodes_by_name(doc)[name]
        p=next(p for p in doc['meshes'][node['mesh']]['primitives'] if doc['materials'][p['material']]['name']==material)
        view=doc['bufferViews'][p['extensions']['KHR_draco_mesh_compression']['bufferView']]
        start=view.get('byteOffset',0);return binary[start:start+view['byteLength']]
    old_white={n:payload(before,blob,n,'white') for n in ['roads','paving-civil-platform-service-export']}
    replace_precise_terrain(path,objects)
    after,binary=unpack(path.read_bytes())
    assert set(mesh_nodes_by_name(after))=={'roads','terrain','paving-civil-platform-service-export'}
    assert payload(after,binary,'paving-civil-platform-service-export','white')==old_white['paving-civil-platform-service-export']
    assert payload(after,binary,'roads','white')!=old_white['roads']
    assert payload(after,binary,'roads','road')
    assert all(len(after['meshes'][n['mesh']]['primitives'])==2 for n in mesh_nodes_by_name(after).values())
print('GROUND_EXPORT_SUFFIX_AND_MATERIAL_FILTER passed',flush=True)
