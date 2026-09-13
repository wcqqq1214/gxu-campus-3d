"""North-portico columns and open bays in source and both shipped LODs."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
check_root=Path(next((a.split('=',1)[1] for a in sys.argv if a.startswith('--check-root=')),str(ROOT)))
building=next(b for b in json.loads((check_root/'public/data/buildings.json').read_text()) if b['landmark']=='library')
envelope=building['architecture'];angle=envelope['angle'];ox,oy=envelope['origin'];z=building['elevation']

def tree(obj):
    obj.data.calc_loop_triangles()
    return BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],
        [tuple(t.vertices) for t in obj.data.loop_triangles],all_triangles=True)

def check(objects,label):
    trees=[tree(o) for o in objects]
    def hit(offset):
        x=offset-.55;y=40.5
        start=Vector((ox+x*math.cos(angle)-y*math.sin(angle),
                      oy+x*math.sin(angle)+y*math.cos(angle),z+5.3))
        direction=Vector((math.sin(angle),-math.cos(angle),0))
        return any(t.ray_cast(start,direction,6.5)[0] is not None for t in trees)
    # Six columns, not six panes in the door behind them. Four-column source
    # fails at the two intermediate bays, which are visible in the event photo.
    columns=[-10.5,-7.3,-4.1,4.1,7.3,10.5]
    for x in columns:assert hit(x),(label,'missing north column',x)
    for a,b in zip(columns,columns[1:]):assert not hit((a+b)/2),(label,'blocked north bay',a,b)
    return {'columns':6,'openBays':5,'passed':True}

def root_name(o):
    while o.parent:o=o.parent
    return o.name

bpy.ops.wm.open_mainfile(filepath=str(check_root/'blender/gxu-campus.blend'))
report={'source':check([o for o in bpy.context.scene.objects if o.get('landmark')=='library'],'source')}
for label,file in [('base','base.glb'),('near','library.glb')]:
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(check_root/'public/models'/file))
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and root_name(o)=='landmark-library']
    assert objects,(label,'missing library export')
    report[label]=check(objects,label)
report['passed']=True
(ROOT/'docs/model-checks/refinement/s3-library-entry.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
