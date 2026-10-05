"""Verify retained heights and open passage; full scene check: validate_north_roads."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'blender'))
b=json.loads((ROOT/'public/data/north-campus.json').read_text())['underpass']
def trees(names):
    return [BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons])
            for o in bpy.context.scene.objects if o.type=='MESH' and o.name.split('.')[0] in names]
def down(meshes,x,y,z=30):
    hits=[t.ray_cast(Vector((x,y,z)),Vector((0,0,-1)),100)[0] for t in meshes]
    return max((p.z for p in hits if p is not None),default=None)
def check(label):
    all_meshes=trees({'roads','terrain','north-campus-roads'})
    floor=b['floorElevation'];lo,hi=b['coveredRange']
    mid=[p for p in b['path'] if lo+1<p[4]<hi-1]
    a,d=Vector((*mid[0][:2],floor+1)),Vector((*mid[-1][:2],floor+1))
    for mesh in all_meshes:
        assert mesh.ray_cast(a,(d-a).normalized(),(d-a).length)[0] is None,(label,'sealed passage')
    maximum_step=0
    for p in b['path'][1:-1]:
        z=down(all_meshes,*p[:2],p[2]+.25)
        assert z is not None and abs(z-p[2])<.04,(label,'floor gap',p,z)
        maximum_step=max(maximum_step,abs(z-p[2]))
    for p in mid:
        origin=Vector((*p[:2],floor+.1))
        hits=[t.ray_cast(origin,Vector((0,0,1)),10)[0] for t in all_meshes]
        z=min(h.z for h in hits if h is not None)
        assert abs(z-b['soffit'])<.04,(label,'headroom',z)
    return {'representation':label,'roadsCheckedSeparately':'north-road-integrity.json','floorSamples':len(b['path'])-2,'maxFloorDeviation':maximum_step,'openPassage':True,'clearanceMeters':b['clearance']}
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'))
reports=[check('editable source')]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'public/models/base.glb'));bpy.context.view_layer.update()
reports.append(check('delivered base GLB'))
(ROOT/'docs/model-checks/north-underpass-geometry.json').write_text(json.dumps({'passed':True,'checks':reports},indent=2)+'\n')
print(reports,flush=True)
