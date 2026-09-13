"""Independent bounds/support checks on flat, sloping and absent terrain."""
import math
import sys
import tempfile
from pathlib import Path
import bpy
import bmesh
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from geometry import material
from low_planting import hedge_mesh
from tree_mesh_audit import snapshot
from mesh_volumes import MeshVolumes

colors = {'leaf':material('test-leaf',(.1,.3,.1)), 'leaf2':material('test-leaf2',(.2,.4,.1))}
item = {'line':[[0,0],[12,5]], 'widthMeters':1.4, 'heightMeters':.75}
for slope in (0, .12):
    terrain = [(x,y,slope*x + .04*y) for x,y in [(-20,-20),(20,-20),(20,20),(-20,20)]]
    mesh = hedge_mesh(item, terrain, [(0,1,2),(0,2,3)], colors)
    length = 13
    residuals = []
    for x,y,z in mesh.v:
        along = (12*x+5*y)/length
        lateral = (-5*x+12*y)/length
        assert -1e-6 <= along <= length+1e-6
        assert abs(lateral) <= .7+1e-6
        residual = z - slope*x - .04*y
        # BVH ray casting uses float32 at a 200 m origin; allow 0.05 mm.
        assert -.03005 <= residual <= .75005, residual
        residuals.append(residual)
    assert min(residuals) < -.029 and max(residuals) > .70
    assert len(mesh.f) < 200
    obj = mesh.object('low-planting-test', bpy.context.scene.collection, {'layer':'vegetation'})
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-5)
    assert all(e.is_manifold for e in bm.edges)
    assert all(e.is_contiguous for e in bm.edges)
    bm.free()
    # Exercise the shipping compression settings: independent material
    # primitives can break a closed source mesh at their quantized seams.
    with tempfile.TemporaryDirectory(prefix='low-planting-') as directory:
        path=Path(directory)/'hedge.glb'
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
        bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,
            export_draco_mesh_compression_enable=True,export_draco_mesh_compression_level=6,
            export_draco_position_quantization=15,export_draco_normal_quantization=6)
        before=set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(path))
        imported=list(set(bpy.data.objects)-before)
        decoded=next(o for o in imported if o.type=='MESH')
        vertices,faces,_=snapshot(decoded)
        volumes=MeshVolumes(vertices,faces)
        assert len(volumes.shells)==1 and volumes.open_components==0
        for other in imported:bpy.data.objects.remove(other,do_unlink=True)
    data=obj.data;bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(data)
try:
    hedge_mesh(item, [(100,100,0),(110,100,0),(100,110,0)], [(0,1,2)], colors)
except ValueError:
    pass
else:
    raise AssertionError('Missing terrain support must fail')
print('Low planting: flat, sloping, Draco round trips and missing terrain scenarios passed',flush=True)
