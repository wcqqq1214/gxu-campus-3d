"""Native Draco regression: material cracks, T junctions and unused anchors."""
import bpy,json,sys,tempfile,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from geometry import Mesh,material
from shore_geometry import conform_edges
from export_attributes import omit_unused_uvs

bpy.ops.wm.read_factory_settings(use_empty=True)
material('left',(.3,.3,.3));material('right',(.8,.8,.8))
a=(.137,.291,.21);b=(12.734,18.419,.61)
m=tuple(a[k]+.37*(b[k]-a[k]) for k in range(3))
source=Mesh();source.face([a,m,(-110,4,.1)],0);source.face([m,b,(-110,4,.1)],0)
source.face([a,(130,5,.1),b],1)
with tempfile.TemporaryDirectory() as directory:
    paths={};expected={}
    for name,shared,conform in [('independent',False,False),('shared',True,False),('conformed',True,True)]:
        mesh=conform_edges(source,(-120,-1,140,20),preserve_vertical_faces=True) if conform else source
        obj=mesh.object(name,bpy.context.scene.collection)
        expected[name]=len(mesh.f)
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
        file=Path(directory)/(name+'.glb');paths[name]=file
        with omit_unused_uvs(deduplicate_vertices=True,share_position_bounds=shared):
            bpy.ops.export_scene.gltf(filepath=str(file),export_format='GLB',use_selection=True,
                export_draco_mesh_compression_enable=True,export_draco_mesh_compression_level=6,
                export_draco_position_quantization=14,export_draco_normal_quantization=6,
                export_materials='EXPORT',export_cameras=False,export_lights=False)
    results={}
    for name,file in paths.items():
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(file))
        obj=next(o for o in bpy.context.scene.objects if o.type=='MESH');mesh=obj.data
        assert len(mesh.polygons)==expected[name],(name,len(mesh.polygons),expected[name])
        used={i for p in mesh.polygons for i in p.vertices}
        assert len(used)==len(mesh.vertices),'Unused quantization anchors escaped into the GLB'
        points={mat.name:set() for mat in mesh.materials}
        for p in mesh.polygons:
            points[mesh.materials[p.material_index].name].update(tuple(mesh.vertices[i].co) for i in p.vertices)
        nearest=lambda key,p:min(points[key],key=lambda q:math.dist(p,q))
        rows={key:[nearest(key,p) for p in (a,m,b)] for key in ('left','right')}
        results[name]=rows
    assert any(results['independent']['left'][i]!=results['independent']['right'][i] for i in (0,2)),results
    assert all(results['shared']['left'][i]==results['shared']['right'][i] for i in (0,2)),results
    assert math.dist(results['shared']['left'][1],results['shared']['right'][1])>1
    assert results['conformed']['left']==results['conformed']['right'],results
    print('NATIVE_SHARED_QUANTIZATION passed',json.dumps(results),flush=True)
