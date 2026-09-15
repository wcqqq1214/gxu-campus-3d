"""Check corridor wall, floor and soffit directions in all affected exports."""
import bpy,json,sys,math,re,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-arts-corridor-normals')
bs=[b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if any('openCorridor' in f['rule'] for f in b.get('form',{}).get('facades',[]))]
def root(o):
 while o.parent:o=o.parent
 return re.sub(r'\.\d+$','',o.name)
def tree(objects):
 return [BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons]) for o in objects if o.type=='MESH']
def check(b,meshes,tol):
 samples=[]
 for f in b['form']['facades']:
  if 'openCorridor' not in f['rule']:continue
  a=Vector((*f['start'],b['elevation']));edge=Vector((*f['end'],0))-Vector((*f['start'],0));u=edge.normalized();n=Vector((*f['normal'],0));length=edge.length;r=f['rule']['openCorridor'];fh=f['height']/f['levels']
  t=r['endInset']+(length-2*r['endInset'])*.5/r.get('piers',{}).get('bays',1)
  def ray(p,d):
   hits=[h for m in meshes if (h:=m.ray_cast(p,d,fh+1))[0] is not None]
   assert hits,'no surface';return min(hits,key=lambda h:h[3])
  for level in range(r['firstLevel'],int(f['levels'])):
   p=a+u*t+Vector((0,0,level*fh+fh-.35));inside=p-n*(r['depth']/2)
   rear=ray(p+n*.3,-n)
   assert abs(rear[3]-(r['depth']+.3))<tol and rear[1].dot(n)>.98,('rear direction',b['id'],f['edge'],level,rear[1],rear[3])
   for direction,expected in [(-1,level*fh),(1,(level+1)*fh-.18)]:
    hit=ray(inside,Vector((0,0,direction)))
    assert hit[1].z*direction<-.98 and abs(hit[0].z-b['elevation']-expected)<tol,('slab direction',b['id'],f['edge'],level,direction,hit[1])
   samples.append(dict(edge=f['edge'],level=level,rearOutwardDot=rear[1].dot(n),floorAndSoffitDirectionsPassed=True))
 return samples
report={'passed':False,'checkedRoot':str(TARGET),'scope':'Every existing openCorridor: three buildings, four facades; direction plus position of rear walls, floors and soffits in source/base/near.'}
try:
 bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
 report['source']={b['id']:check(b,tree(o for o in bpy.context.scene.objects if o.get('featureId')==b['id']),.01) for b in bs}
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update()
 report['base']={b['id']:check(b,tree(o for o in bpy.context.scene.objects if root(o)==b['chunk']),.05) for b in bs}
 report['near']={}
 for b in bs:
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/f"{b['chunk']}.glb"));bpy.context.view_layer.update()
  report['near'][b['id']]=check(b,tree(bpy.context.scene.objects),.02)
 report['sourceSha256']=hashlib.sha256((TARGET/'blender/gxu-campus.blend').read_bytes()).hexdigest();report['manifestSha256']=hashlib.sha256((TARGET/'public/data/models.json').read_bytes()).hexdigest();report['passed']=True
except Exception as error:report['failure']=str(error);raise
finally:
 (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,indent=2)+'\n');print('Corridor normals:',report['passed'],flush=True)
