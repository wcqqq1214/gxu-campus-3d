"""Read actual saved tree instances and compare their prepared attributes."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
report_prefix=next((a.split('=',1)[1] for a in args if a.startswith('--report-prefix=')),'s4-background')
if not report_prefix or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in report_prefix):
    raise ValueError('Invalid vegetation report prefix')
sys.path.insert(0,str(ROOT/'scripts'))
from vegetation_layout import tree_rotation
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'))
rows=json.loads((ROOT/'public/data/vegetation.json').read_text())
expected={(row[0],row[1]):row[2:] for row in rows}
objects=[o for o in bpy.context.scene.objects if o.name.startswith('树木示意-')]
templates={o.get('template'):o.data for o in bpy.context.scene.objects if o.get('template') is not None}
assert len(objects)==len(expected)==len(rows)
terrain=bpy.data.objects['terrain']
terrain.data.calc_loop_triangles()
bvh=BVHTree.FromPolygons([terrain.matrix_world@v.co for v in terrain.data.vertices],
                        [tuple(p.vertices) for p in terrain.data.loop_triangles], all_triangles=True)
measurements=[];ground_errors=[]
for o in objects:
    x,y=round(o.location.x,1),round(o.location.y,1)
    h,typ,z=expected[(x,y)]
    assert o.data==templates[typ]
    assert max(abs(s-h/9) for s in o.scale)<1e-5
    assert abs(math.remainder(o.rotation_euler.z-tree_rotation(x,y),math.tau))<1e-6
    hit=bvh.ray_cast(Vector((x,y,200)),Vector((0,0,-1)),400)[0]
    assert hit is not None,('Tree outside terrain',x,y)
    ground_errors.append(o.location.z-hit.z)
    assert abs(o.location.z-z)<1e-5
    measurements.append([x,y,float(o.location.z),float(o.rotation_euler.z)])
report={'trees':len(rows),'typesScalesAndRotationsMatch':True,'savedTransforms':measurements,
        'sourceAnchorMinusActualTerrain':{'minimumMeters':min(ground_errors),'maximumMeters':max(ground_errors),
            'over25cmAbsolute':sum(abs(e)>.25 for e in ground_errors)},'passed':max(abs(e) for e in ground_errors)<1e-4,
        'scope':'Saved tree attributes and fifth-column elevations against final source terrain triangles.'}
assert report['passed'],report['sourceAnchorMinusActualTerrain']
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'public/models/base.glb'))
terrain_objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.split('.')[0]=='terrain']
assert len(terrain_objects)==1,('Expected one exported terrain mesh',len(terrain_objects))
terrain=terrain_objects[0]
terrain.data.calc_loop_triangles()
bvh=BVHTree.FromPolygons([terrain.matrix_world@v.co for v in terrain.data.vertices],
                        [tuple(t.vertices) for t in terrain.data.loop_triangles],all_triangles=True)
errors=[]
for x,y,h,typ,z in rows:
    hit=bvh.ray_cast(Vector((x,y,200)),Vector((0,0,-1)),400)[0]
    assert hit is not None,('GLB terrain missing under tree',x,y)
    errors.append(z-hit.z)
report['shippingGLBTerrain']={'sampledTrees':len(errors),'minAnchorOffsetMeters':min(errors),'maxAnchorOffsetMeters':max(errors),'toleranceMeters':.15}
assert max(abs(v) for v in errors)<.15,report['shippingGLBTerrain']
(ROOT/f'docs/model-checks/refinement/{report_prefix}-tree-source.json').write_text(json.dumps(report,indent=2)+'\n')
print({k:v for k,v in report.items() if k!='savedTransforms'},flush=True)
