"""Check saved and Draco-decoded perimeter road surfaces against delivery data."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parents[1]
name='campus-roads' if '--campus' in sys.argv else 'surroundings'
d=json.loads((R/f'public/data/{name}.json').read_text());terrain=json.loads((R/'public/data/terrain.json').read_text())
def elevation(x,y):
 c,r=terrain['cols'],terrain['rows'];x0,y0,x1,y1=terrain['bounds'];hh=terrain['heights'];u=(x-x0)/(x1-x0)*(c-1);v=(y-y0)/(y1-y0)*(r-1);i,j=int(u),int(v);a,t=u-i,v-j
 return (hh[j*c+i]*(1-a)+hh[j*c+i+1]*a)*(1-t)+(hh[(j+1)*c+i]*(1-a)+hh[(j+1)*c+i+1]*a)*t
samples=[]
for layer in d['layers']:
 vs,ts=layer['vertices'],layer['triangles'];tris=[ts[i:i+3] for i in range(0,len(ts),3)]
 for tri in tris[::max(1,len(tris)//75)]:
  a,b,c=[vs[i] for i in tri];area=abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))/2
  if area<.1:continue
  samples.append(((a[0]+b[0]+c[0])/3,(a[1]+b[1]+c[1])/3,[a,b,c]))
def check(objects,ground_objects,label):
 vs=[];fs=[]
 for o in objects:
  if o.type!='MESH':continue
  off=len(vs);vs.extend([tuple(o.matrix_world@v.co) for v in o.data.vertices]);fs.extend([tuple(off+i for i in p.vertices) for p in o.data.polygons])
 bv=BVHTree.FromPolygons(vs,fs);errors=[]
 gvs=[];gfs=[]
 for o in ground_objects:
  if o.type!='MESH':continue
  o.data.calc_loop_triangles()
  off=len(gvs);gvs.extend([tuple(o.matrix_world@v.co) for v in o.data.vertices]);gfs.extend([tuple(off+i for i in p.vertices) for p in o.data.loop_triangles])
 ground=BVHTree.FromPolygons(gvs,gfs);margins=[]
 for x,y,triangle in samples:
  zs=[]
  for px,py in triangle:
   z=elevation(px,py);g=ground.ray_cast(Vector((px,py,z+100)),Vector((0,0,-1)),200)[0]
   zs.append(max(z,g.z if g is not None else z)+.4)
  expected=sum(zs)/3
  hit=bv.ray_cast(Vector((x,y,expected+2)),Vector((0,0,-1)),4)
  assert hit[0] is not None,(label,'missing road',x,y)
  error=abs(hit[0].z-expected);assert error<.14,(label,'road height mismatch',x,y,error);errors.append(error)
  terrain_hit=ground.ray_cast(Vector((x,y,expected+2)),Vector((0,0,-1)),6)
  assert terrain_hit[0] is not None,(label,'missing terrain')
  margin=hit[0].z-terrain_hit[0].z;assert margin>.02,(label,'road buried in terrain',x,y,margin);margins.append(margin)
 return {'representation':label,'surfaceSamples':len(errors),'maximumExportHeightError':round(max(errors),4),'minimumRoadAboveTerrain':round(min(margins),4)}
bpy.ops.wm.open_mainfile(filepath=str(R/'blender/gxu-campus.blend'));report=[check([bpy.data.objects['roads']],[bpy.data.objects['terrain']],'editable source')]
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(R/'public/models/base.glb'))
objects=[];ground_objects=[]
for o in bpy.context.scene.objects:
 root=o
 while root.parent:root=root.parent
 if root.name=='roads':objects.append(o)
 if root.name=='terrain':ground_objects.append(o)
report.append(check(objects,ground_objects,'base GLB'))
(R/f'docs/model-checks/{name}-geometry.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
