"""Check mathematical-center massing, open galleries and entrance in shipped meshes."""
import bpy,sys,json,math,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-math-center')
b=next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']=='way/759129515')
BASELINE=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--baseline-root=')),ROOT/'work/refinement-s2-math-center-before')
def root_name(o):
 while o.parent:o=o.parent
 return o.name
def trees(objects,materials=None):
 result=[]
 for o in objects:
  if o.type!='MESH':continue
  faces=[tuple(p.vertices) for p in o.data.polygons if materials is None or o.data.materials[p.material_index].name.split('.')[0] in materials]
  if faces:result.append(BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],faces))
 return result
def check(objects,tolerance,ground=None):
 objects=list(objects);all_mesh=trees(objects);stone=trees(objects,{'stone'});glass=trees(objects,{'glass','shadeGlass'});white=trees(objects,{'white'});samples=[]
 def ray(ts,p,d,limit=3):return min((hit[3] for t in ts if (hit:=t.ray_cast(Vector(p),Vector(d),limit))[0] is not None),default=None)
 def require(kind,ts,p,d,expected,limit=3):
  actual=ray(ts,p,d,limit);assert actual is not None and abs(actual-expected)<=tolerance,(kind,actual,expected,list(p));samples.append(dict(kind=kind,errorMeters=abs(actual-expected)))
 z=b['elevation']
 # Independent stations on the main west roof, flat stair and east wall.
 require('west-three-roof',all_mesh,(-268.623085875,-843.112242937,z+13),(0,0,-1),1.6,4)
 require('stair-flat-roof',all_mesh,(-250,-843,z+12),(0,0,-1),2.1,4)
 assert ray(all_mesh,(-222,-840,z+10),(0,0,1),3) is None,'east incorrectly raised to three floors'
 f=next(f for f in b['form']['facades'] if 'openCorridor' in f['rule']);a=Vector((*f['start'],z));edge=Vector((*f['end'],z))-a;u=edge.normalized();n=Vector((*f['normal'],0));length=edge.length
 for level in range(3):
  for bay in range(8):
   p=a+u*(.3+(length-.6)*(bay+.5)/8)+Vector((0,0,level*3.3+1.8))
   distance=ray(all_mesh,p+n*.3,-n)
   assert distance is not None and 1.75-tolerance<distance<2.1+tolerance,('gallery closed',level,bay,distance)
   samples.append(dict(kind='open-gallery',levelIndex=level,bay=bay,rearDistanceMeters=distance))
   require('gallery-floor',all_mesh,p-n*.9,(0,0,-1),1.8)
   require('gallery-soffit',all_mesh,p-n*.9,(0,0,1),1.32)
   if level==0 and ground is not None:
    for depth in (.2,.9,1.6):
     distance=ray(ground,p-n*depth,(0,0,-1),3)
     assert distance is not None and distance>=1.91-tolerance,('terrain inside ground gallery',bay,depth,distance)
     samples.append(dict(kind='gallery-ground-clearance',bay=bay,depth=depth,floorAboveGroundMeters=distance-1.8))
  for i in range(9):
   p=a+u*(.3+(length-.6)*i/8)+Vector((0,0,level*3.3+1.5))
   require('gallery-pier',stone,p+n*.3,-n,.3)
 count=math.ceil((length-.6)/.32)
 for level in (1,2):
  for i in (2,3,5):
   t=.3+(length-.6)*(i+.5)/count;p=a+u*t+Vector((0,0,level*3.3+.5))+n*.3
   require('baluster-bar',white,p,-n,.3)
   t=.3+(length-.6)*(i+1)/count;p=a+u*t+Vector((0,0,level*3.3+.5))+n*.3
   assert ray(all_mesh,p,-n,.7) is None,('filled baluster gap',level,i)
 p=a+u*(.3+(length-.6)*.5/8)+Vector((0,0,.5))+n*.3
 assert ray(all_mesh,p,-n,.7) is None,'ground gallery has blocking rail'
 e=b['form']['entrances'][0];n=Vector((math.sin(math.radians(e['bearing'])),math.cos(math.radians(e['bearing'])),0));a=Vector((*e['center'],z));tangent=Vector((n.y,-n.x,0))
 require('south-entrance',glass,a+n*.8+Vector((0,0,1.64)),-n,.625)
 for distance,top in [(.45,.34),(1.06,.19)]:
  for offset in (-2.8,0,2.8):
   p=a+n*distance+tangent*offset
   require('two-level-entry-step',stone,p+Vector((0,0,top+.4)),(0,0,-1),.4,1)
   if ground is not None:
    actual=ray(ground,p+Vector((0,0,3)),(0,0,-1),10);assert actual is not None
    ground_height=3-actual
    assert -.11-tolerance<=ground_height<=top-.015+tolerance,('entry floats or tread buried',distance,offset,ground_height,top)
    samples.append(dict(kind='entry-ground',distance=distance,offset=offset,topAboveGroundMeters=top-ground_height))
 f=next(f for f in b['form']['facades'] if f['edge']==7);a=Vector((*f['start'],z));edge=Vector((*f['end'],z))-a;n=Vector((*f['normal'],0))
 for center in (.35,.5,.65):
  for up in (4.5,5.55):require('three-upper-windows',glass,a+edge*center+Vector((0,0,up))+n*.8,-n,.76)
 # Old fallback entrance was halfway along the long north edge.
 old=Vector((-240.98028190468342,-837.2210220000644,z+3.5))+Vector((0,.8,0))
 assert ray(white,old,(0,0,-1),1) is None,'old north midpoint canopy retained'
 return dict(passed=True,samples=samples)

def check_apron(ground,apron,before,tolerance):
 e=b['form']['entrances'][0];n=Vector((math.sin(math.radians(e['bearing'])),math.cos(math.radians(e['bearing'])),0));u=Vector((n.y,-n.x,0));a=Vector((*e['center'],0));z=b['elevation'];samples=[]
 def point(x,y):return a+u*x+n*y
 def height(ts,p):
  hits=[hit[0].z for t in ts if (hit:=t.ray_cast(p+Vector((0,0,20)),Vector((0,0,-1)),40))[0] is not None]
  assert hits,('missing apron ground',list(p));return max(hits)
 for x in (-2.8,0,2.8):
  for y in (1.25,1.7,2.2,2.6):
   p=point(x,y);h=height(apron,p);g=height(ground,p)
   assert abs(h-z-.04)<=tolerance and h-g>=.12-tolerance,('apron level/clearance',x,y,h,g)
   samples.append(dict(kind='apron',x=x,y=y,clearanceMeters=h-g))
 for x in (-6,-5.3,-5.1,5.1,5.3,6):
  for y in (0,.5,1,2,3,4,5):
   p=point(x,y);delta=height(ground,p)-height(before,p)
   assert abs(delta)<=tolerance,('outside grading changed',x,y,delta)
   samples.append(dict(kind='preserved-ground',errorMeters=abs(delta)))
 for x in (-4,-2,0,2,4):
  for y in (-.3,4.62,4.9,5.3):
   p=point(x,y);delta=height(ground,p)-height(before,p)
   assert abs(delta)<=tolerance,('outside grading changed',x,y,delta)
 return dict(passed=True,samples=samples)

def check_gallery_apron(ground,apron,before,tolerance):
 f=next(f for f in b['form']['facades'] if 'openCorridor' in f['rule']);n=Vector((*f['normal'],0));u=Vector((n.y,-n.x,0));a=Vector((*[(x+y)/2 for x,y in zip(f['start'],f['end'])],0));half=math.dist(f['start'],f['end'])/2-.3;samples=[]
 def point(x,y):return a+u*x+n*y
 def height(ts,p):
  hits=[hit[0].z for t in ts if (hit:=t.ray_cast(p+Vector((0,0,20)),Vector((0,0,-1)),40))[0] is not None]
  assert hits,('missing gallery paving or ground',list(p));return max(hits)
 for x in (-14,-7,0,7,14):
  for y in (.1,.5,.9):
   p=point(x,y);h=height(apron,p);g=height(ground,p)
   assert abs(h-b['elevation'])<=tolerance and h-g>=.11-tolerance,('gallery apron level/clearance',x,y,h,g)
   samples.append(dict(kind='gallery-apron',clearanceMeters=h-g))
 for x in (-half-2.3,half+2.3):
  for y in (-1,0,1,2,3.3):
   p=point(x,y);delta=height(ground,p)-height(before,p)
   assert abs(delta)<=tolerance,('outside gallery grading changed',x,y,delta)
   samples.append(dict(kind='preserved-ground',errorMeters=abs(delta)))
 for x in (-14,-7,0,7,14):
  for y in (-2.1,3,3.3):
   p=point(x,y);delta=height(ground,p)-height(before,p)
   assert abs(delta)<=tolerance,('gallery grading outer plane changed',x,y,delta)
 return dict(passed=True,samples=samples)
report=dict(passed=False,buildingId=b['id'],checkedRoot=str(TARGET),wholeBuildingAccepted=False,scope='west three/east two massing; mixed roofs; three-level gallery, piers, open balusters; south entry steps and three upper windows; unobserved facades remain pending')
try:
 bpy.ops.wm.open_mainfile(filepath=str(BASELINE/'blender/gxu-campus.blend'))
 before_ground=trees([o for o in bpy.context.scene.objects if o.get('layer')=='terrain'])
 bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
 objects=[o for o in bpy.context.scene.objects if o.get('featureId')==b['id']];assert len(objects)==1
 ground=trees([o for o in bpy.context.scene.objects if o.get('layer')=='terrain'])
 report['source']=check(objects,.011,ground)
 report['sourceApron']=check_apron(ground,trees([o for o in bpy.context.scene.objects if o.get('siteId')=='math-center-south-apron']),before_ground,.011)
 report['sourceGalleryApron']=check_gallery_apron(ground,trees([o for o in bpy.context.scene.objects if o.get('siteId')=='math-center-gallery-apron']),before_ground,.011)
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update()
 ground=trees([o for o in bpy.context.scene.objects if o.get('layer')=='terrain'])
 report['base']=check([o for o in bpy.context.scene.objects if root_name(o)==b['chunk']],.05,ground)
 report['baseApron']=check_apron(ground,trees([o for o in bpy.context.scene.objects if o.get('siteId')=='math-center-south-apron']),before_ground,.025)
 report['baseGalleryApron']=check_gallery_apron(ground,trees([o for o in bpy.context.scene.objects if o.get('siteId')=='math-center-gallery-apron']),before_ground,.025)
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/f'{b["chunk"]}.glb'));bpy.context.view_layer.update()
 report['near']=check(bpy.context.scene.objects,.02)
 report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/data/buildings.json','public/data/models.json']}
 report['passed']=True
except Exception as error:report['failure']=str(error);raise
finally:
 (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,indent=2)+'\n');print('Math center actual geometry',report['passed'],flush=True)
