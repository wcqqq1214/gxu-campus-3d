"""Check agriculture road grading against the saved pre-repair road and actual terrain.

Use the same 1.2 cm profile, 2.5 cm export, 0.5 mm boundary and 12 cm
terrain-clearance gates for source and shipped candidate verification.
"""
import argparse,bpy,json,sys,math,re
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root',type=Path,default=ROOT)
parser.add_argument('--baseline',type=Path,required=True)
parser.add_argument('--report',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'blender')]
from road_landing_contract import load_landings
from road_landing_geometry import world,weight
from inspect_agriculture_approach import layer
r=next(r for r in load_landings(ROOT) if r['id']=='agriculture-south-stair-road')
def read(path):
 if path.suffix=='.blend':bpy.ops.wm.open_mainfile(filepath=str(path))
 else:
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(path))
 bpy.context.view_layer.update()
 roads=[o for o in bpy.context.scene.objects if o.type=='MESH' and re.sub(r'\.\d{3,}$','',o.name)=='roads']
 terrain=[o for o in bpy.context.scene.objects if o.type=='MESH' and layer(o)=='terrain']
 def sample(objects):
  trees=[]
  for o in objects:
   o.data.calc_loop_triangles();trees.append(BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(t.vertices) for t in o.data.loop_triangles],all_triangles=True))
  def fn(x,y,top,bottom):
   hits=[t.ray_cast(Vector((x,y,top)),Vector((0,0,-1)),top-bottom)[0] for t in trees]
   return max((p.z for p in hits if p is not None),default=None)
  return fn
 return sample(roads),sample(terrain)
def height(fn,p):return fn(*p,50,-50)
before,_=read(args.baseline/'blender/gxu-campus.blend');source,ground=read(args.root/'blender/gxu-campus.blend');base,baseground=read(args.root/'public/models/base.glb')
h=r['halfWidth']+r['sideFeather'];rows=[];fails=[];boundary=[]
for i in range(math.ceil((2*h+1)/.1)+1):
 x=-h-.5+(2*h+1)*i/math.ceil((2*h+1)/.1)
 for j in range(50):
  y=.19+j*.1;p=world(r,x,y);old,a,b=[height(f,p) for f in [before,source,base]]
  if old is None:continue
  if a is None or b is None:fails.append(['missing',x,y]);continue
  exact=old+(r['targetElevation']-old)*weight(r,p)
  ga,gb=[height(f,p) for f in [ground,baseground]]
  row=dict(x=x,y=y,expected=exact,source=a,base=b,sourceError=abs(a-exact),exportError=abs(b-a),sourceTerrainClearance=a-ga,baseTerrainClearance=b-gb)
  rows.append(row)
  if row['sourceError']>.012 or row['exportError']>.025 or min(row['sourceTerrainClearance'],row['baseTerrainClearance'])<.12:fails.append(row)
# Exact clipping boundary and adjacent samples, including both horizontal edges.
for axis,fixed,low,high in [('x',-h,.2,4.5),('x',h,.2,4.5),('y',.2,-h,h),('y',4.5,-h,h)]:
 for i in range(101):
  v=low+(high-low)*i/100;x,y=(fixed,v) if axis=='x' else (v,fixed);p=world(r,x,y)
  old,a,b=[height(f,p) for f in [before,source,base]]
  delta=abs(a-old);err=abs(b-a);boundary.append(dict(x=x,y=y,sourceChange=delta,exportError=err))
  if delta>.0005 or err>.025:fails.append(boundary[-1])
report=dict(passed=not fails,samples=len(rows),boundarySamples=len(boundary),maximumSourceProfileError=max(s['sourceError'] for s in rows),maximumExportError=max(s['exportError'] for s in rows),minimumSourceTerrainClearance=min(s['sourceTerrainClearance'] for s in rows),minimumBaseTerrainClearance=min(s['baseTerrainClearance'] for s in rows),maximumBoundarySourceChange=max(s['sourceChange'] for s in boundary),maximumBoundaryExportError=max(s['exportError'] for s in boundary),failures=fails)
args.report.parent.mkdir(parents=True,exist_ok=True)
args.report.write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True);assert report['passed']
