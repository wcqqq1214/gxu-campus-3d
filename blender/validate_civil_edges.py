"""Check actual exterior profiles and source/export contacts, not only the plateau."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from civil_forecourt_grade import load_grade
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
REPORT=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--report=')),ROOT/'work/civil-edge-validation.json')

def sampler(layer):
 trees=[]
 for o in bpy.context.scene.objects:
  root=o
  while root.parent:root=root.parent
  if o.type!='MESH' or root.get('layer')!=layer:continue
  o.data.calc_loop_triangles()
  trees.append(BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(t.vertices) for t in o.data.loop_triangles],all_triangles=True))
 def sample(x,y):
  hits=[t.ray_cast(Vector((x,y,100)),Vector((0,0,-1)),200)[0] for t in trees]
  return max((h.z for h in hits if h is not None),default=None)
 return sample

profiles={f'east-grass-{y}':('terrain',[(-456+i*.25,y) for i in range(425)],.18)
          for y in (-874,-860,-850,-842,-812,-797,-770)}
profiles['north-road']=('roads',[(-460,-840+i*.25) for i in range(521)],.10)
# Fixed fine probes catch the short pad seam that 25 cm profiles can skip.
seam_profiles={
 'north-road-cross':('roads',[(-462+i*.02,-722) for i in range(201)],.003),
 'east-pad-grass':('terrain',[(-390+i*.02,-812) for i in range(151)],.003),
}
def check_seams(samples):
 result={}
 for name,(layer,points,limit) in seam_profiles.items():
  heights=[samples[layer](*q) for q in points]
  assert all(z is not None for z in heights),('missing seam surface',name)
  step=max(abs(b-a) for a,b in zip(heights,heights[1:]))
  assert step<limit,('local seam/fold',name,step,limit)
  result[name]={'samples':len(points),'maximumStepPer2cm':step}
 return result
report={'passed':False,'profiles':{}}
try:
 p=load_grade(ROOT)
 bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
 samples={n:sampler(n) for n in ('terrain','roads')};reference={}
 for name,(layer,points,limit) in profiles.items():
  heights=[samples[layer](*q) for q in points]
  assert all(z is not None for z in heights),('missing surface',name)
  # Travel and cross-slope profiles measure visible grade; a thin clipping
  # triangle's normal alone does not measure the road's longitudinal slope.
  slope=max(abs(b-a)/.25 for a,b in zip(heights,heights[1:]))
  assert slope<limit,('edge cliff/road fold',name,slope,limit)
  report['profiles'][name]={'samples':len(points),'maxProfileSlope':slope,'heightRange':[min(heights),max(heights)]}
  reference[name]=heights
 report['sourceSeams']=check_seams(samples)
 # Explicit near-edge road cross-sections prevent a good centerline from
 # masking a new transverse lip. Curbs are outside these interior samples.
 for y in (-780,-760,-740,-722):
  points=[(-462+i*.1,y) for i in range(41)];heights=[samples['roads'](*q) for q in points]
  assert all(z is not None for z in heights),('missing road cross section',y)
  step=max(abs(b-a) for a,b in zip(heights,heights[1:]))
  assert step<.006,('transverse road lip',y,step)
  report.setdefault('roadCrossSectionSteps',{})[y]=step
 # Pad footprints must actually carry their new floor, not leave floating
 # context buildings after removing the DEM hump.
 for pad in p['contextPads']:
  a,b,c,d=pad['bounds'];z=samples['terrain']((a+c)/2,(b+d)/2)
  assert z is not None and abs(z-(pad['datum']-.02))<.025,('context floor detached',pad['buildingId'],z)
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update()
 samples={n:sampler(n) for n in ('terrain','roads')};errors=[]
 report['exportSeams']=check_seams(samples)
 for name,(layer,points,limit) in profiles.items():
  for q,z in zip(points,reference[name]):
   actual=samples[layer](*q)
   assert actual is not None,('export edge hole',name,q)
   errors.append(abs(actual-z))
 assert max(errors)<.025,('export edge drift',max(errors))
 report.update(exportMaximumError=max(errors),passed=True)
except Exception as e:report['failure']=str(e);raise
finally:
 REPORT.parent.mkdir(parents=True,exist_ok=True);REPORT.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
