"""Validate road grade, soil clearance and source/Draco agreement at civil entry."""
import bpy,json,math,sys,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from initial_model_budget import check_initial_model_budget
from civil_forecourt_grade import load_grade,height
from validation_inputs import baseline_root
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
REPORT=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--report=')),ROOT/'work/civil-grade-validation.json')

def owner(o):
 while o.parent:o=o.parent
 return o

def sampler(layer):
 trees=[]
 for o in bpy.context.scene.objects:
  if o.type!='MESH' or owner(o).get('layer')!=layer:continue
  o.data.calc_loop_triangles()
  trees.append(BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(t.vertices) for t in o.data.loop_triangles],all_triangles=True))
 def sample(x,y):
  hits=[t.ray_cast(Vector((x,y,100)),Vector((0,0,-1)),200) for t in trees]
  return max((h for h in hits if h[0] is not None),key=lambda h:h[0].z,default=None)
 return sample

# Fixed world-coordinate profiles span both the service road and the campus
# road junctions, rather than deriving acceptance points from mesh vertices.
profiles={
 'main-front': [(-492+i*.1,-843) for i in range(370)],
 'south-campus-road': [(-460+i*.1,-874) for i in range(50)],
 'materials-road-transition': [(-509+i*.1,-874) for i in range(490)],
 'east-campus-road': [(-460,-875+i*.1) for i in range(351)],
 'west-service-transition': [(-501,-867+i*.1) for i in range(211)],
}
report={'passed':False,'profiles':{}}
try:
 p=load_grade(ROOT)
 baseline=baseline_root(sys.argv)
 bpy.ops.wm.open_mainfile(filepath=str(baseline/'blender/gxu-campus.blend'))
 old_ground,old_road=sampler('terrain'),sampler('roads')
 bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
 ground,road=sampler('terrain'),sampler('roads');source={};clearances=[]
 for name,points in profiles.items():
  heights=[];slopes=[]
  for x,y in points:
   hit=road(x,y);soil=ground(x,y)
   assert hit and soil,('missing road/soil',name,x,y)
   z=hit[0].z;normal=hit[1];heights.append(z);source[x,y]=z
   if not name.endswith('transition'):
    assert abs(z-height(x,y,p)-.12)<.025,('ungraded road',name,x,y,z)
   slopes.append(math.hypot(normal.x,normal.y)/abs(normal.z))
   clearance=z-soil[0].z;clearances.append(clearance)
   limit=.18
   if name.endswith('transition'):
    old_r,old_g=old_road(x,y),old_ground(x,y)
    assert old_r and old_g,('missing baseline road',x,y)
    limit=max(limit,old_r[0].z-old_g[0].z+.03)
   assert .065<clearance<limit,('road/soil intersection or increased clearance',name,x,y,clearance,limit)
  steps=[abs(b-a) for a,b in zip(heights,heights[1:])]
  # The south junction also meets the adjoining lower building pad; allow a
  # shallow 5% crossfall there while retaining the stricter entrance limit.
  limit=.25 if name.endswith('transition') else .05 if name=='south-campus-road' else .04
  assert max(slopes)<limit,('excessive road gradient',name,max(slopes))
  assert max(steps)<(.025 if name.endswith('transition') else .006),('road seam/grade break',name,max(steps))
  report['profiles'][name]={'samples':len(points),'heightRange':[min(heights),max(heights)],'maximumSlope':max(slopes),'maximumStepPer10cm':max(steps)}
 report['groundClearanceRange']=[min(clearances),max(clearances)]
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update()
 road,ground=sampler('roads'),sampler('terrain');errors=[]
 for (x,y),expected in source.items():
  hit=road(x,y);soil=ground(x,y)
  assert hit and soil,('export hole',x,y)
  errors.append(abs(hit[0].z-expected))
  assert errors[-1]<.05,('export height error',x,y,errors[-1])
  assert hit[0].z-soil[0].z>.045,('export road/terrain intersection',x,y)
 report['exportMaximumError']=max(errors)
 files=['base.glb','trees.glb'];total=sum((TARGET/'public/models'/n).stat().st_size for n in files)
 report.update(check_initial_model_budget(total))
 manifest=json.loads((TARGET/'public/data/models.json').read_text())
 for name,key in [('base.glb','base'),('trees.glb','trees')]:
  data=(TARGET/'public/models'/name).read_bytes()
  assert manifest[key]['bytes']==len(data) and manifest[key]['sha256']==hashlib.sha256(data).hexdigest(),('stale manifest',name)
 report.update(passed=True)
except Exception as e:report['failure']=str(e);raise
finally:
 REPORT.parent.mkdir(parents=True,exist_ok=True);REPORT.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
