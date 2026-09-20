"""Check the repaired mapped service road against original terrain and joins."""
import bpy,json,math,sys,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from site_geometry import inside,ring_distance
PREFIX=next((s.split('=',1)[1] for s in sys.argv if s.startswith('--report-prefix=')),'s2-civil-front-connection-road-grade')
TARGET=next((Path(s.split('=',1)[1]).resolve() for s in sys.argv if s.startswith('--check-root=')),ROOT)
BASELINE=ROOT/'work/refinement-s2-civil-front-connection-before'
r=next(p for p in json.load(open(ROOT/'public/data/pavings.json'))['pavings'] if p['id']=='civil-forecourt-service')
def root(o):
 while o.parent:o=o.parent
 return o
def sample(objects):
 trees=[]
 for o in objects:
  if o.type!='MESH':continue
  o.data.calc_loop_triangles();trees.append(BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(t.vertices) for t in o.data.loop_triangles],all_triangles=True))
 def height(x,y):
  hits=[t.ray_cast(Vector((x,y,100)),Vector((0,0,-1)),200)[0] for t in trees]
  return max((p.z for p in hits if p is not None),default=None)
 return height
bpy.ops.wm.open_mainfile(filepath=str(BASELINE/'blender/gxu-campus.blend'))
oldground=sample([o for o in bpy.context.scene.objects if root(o).get('layer')=='terrain'])
oldroad=sample([o for o in bpy.context.scene.objects if root(o).get('layer')=='roads'])
def check(label):
 road=sample([o for o in bpy.context.scene.objects if root(o).get('layer')=='roads'])
 ground=sample([o for o in bpy.context.scene.objects if root(o).get('layer')=='terrain'])
 tolerance=.008 if label=='source' else .045
 ring=r['vertices'];errors=[];clearances=[]
 x0,y0,x1,y1=r['bounds']
 for ix in range(math.floor(x0*2),math.ceil(x1*2)):
  for iy in range(math.floor(y0*2),math.ceil(y1*2)):
   x,y=ix/2+.17,iy/2+.13
   if not inside((x,y),ring) or ring_distance((x,y),ring)<.2:continue
   if min(ring_distance((x,y),[j['a'],j['b'],j['a']]) for j in r['joins'])<=3.1:continue
   h,g,old=road(x,y),ground(x,y),oldground(x,y)
   assert h is not None and g is not None and old is not None,('road/terrain hole',x,y)
   errors.append(abs(h-old-.12));clearances.append(h-g)
   assert errors[-1]<tolerance,('grounded road height',x,y,h,old,errors[-1])
   assert h-g>.055,('terrain through road',x,y,h-g)
 # Independently fixed former failure location, a two-centimetre scan.
 angle=math.radians(-180.07647434826438);cs,sn=math.cos(angle),math.sin(angle)
 ox,oy=-485.10996235425523,-838.0392239999364
 def world(x,y):return ox+x*cs-y*sn,oy+x*sn+y*cs
 profiles=[]
 for x in (-1.125,0,1.125):
  heights=[road(*world(x,3.3+i*.02)) for i in range(61)]
  assert all(h is not None for h in heights),('internal road hole',x)
  delta=max(abs(b-a) for a,b in zip(heights,heights[1:]))
  assert delta<.03,('internal road jump',x,delta)
  profiles.append(dict(x=x,maximumStepPer2cm=delta))
 joins=[]
 for j in r['joins']:
  a,b,n=j['a'],j['b'],j['inward']
  for t in (.2,.5,.8):
   x,y=[a[k]*(1-t)+b[k]*t for k in (0,1)]
   xx,yy=x-n[0]*.05,y-n[1]*.05
   expected,h=oldroad(xx,yy),road(xx,yy)
   assert expected is not None and h is not None and abs(h-expected)<tolerance,('campus road join changed',j['edge'],t,h,expected)
   hs=[];gaps=[]
   for d in [-.2+i*.02 for i in range(41)]:
    xx,yy=x+n[0]*d,y+n[1]*d;h=road(xx,yy)
    if h is None:
     # Bound a float32/material boundary miss on both sides, using the same
     # precision limits as the existing connection validator.
     spacing=.00005 if label=='source' else .0005;found=[]
     for sign in (-1,1):
      for k in range(1,7):
       nearby=road(xx+n[0]*sign*k*spacing,yy+n[1]*sign*k*spacing)
       if nearby is not None:found.append((k*spacing,nearby));break
     assert len(found)==2,('join gap exceeds precision bound',j['edge'],t,d)
     gaps.append(sum(v[0] for v in found));h=max(v[1] for v in found)
    hs.append(h)
   jump=max(abs(b-a) for a,b in zip(hs,hs[1:]))
   assert jump<.06,('join step',j['edge'],t,jump)
   joins.append(dict(edge=j['edge'],t=t,maximumStepPer2cm=jump,measuredGapUpperBounds=gaps))
 export_seams=[]
 if label=='base':
  # The local export cut must also remain covered where it meets the
  # campus-wide compressed road node, not only at the repaired road ends.
  x0,y0,x1,y1=r['bounds'];box=[(x0-5,y0-5),(x1+5,y0-5),(x1+5,y1+5),(x0-5,y1+5)]
  for a,b in zip(box,box[1:]+box[:1]):
   length=math.dist(a,b);nx,ny=-(b[1]-a[1])/length,(b[0]-a[0])/length
   for i in range(1,math.ceil(length*2)):
    t=i/math.ceil(length*2);x,y=a[0]*(1-t)+b[0]*t,a[1]*(1-t)+b[1]*t
    for d in (-.1,-.04,0,.04,.1):
     xx,yy=x+nx*d,y+ny*d;expected=source_road(xx,yy)
     if expected is None:continue
     h=road(xx,yy)
     assert h is not None,('export partition hole',xx,yy)
     error=abs(h-expected);assert error<.07,('export partition step',xx,yy,error)
     export_seams.append(error)
  assert export_seams,'No road samples at export partition boundary'
 return dict(passed=True,interiorSamples=len(errors),maximumGroundedHeightError=max(errors),minimumGroundClearance=min(clearances),formerFailureProfiles=profiles,joins=joins,tolerance=tolerance,exportSeamSamples=len(export_seams),maximumExportSeamError=max(export_seams,default=0))
report=dict(passed=False,scope='Mapped 309.606 square metre service road repaired to original rendered terrain plus estimated 0.12 m offset; both campus road contacts preserved through 3 m blends. Fixed old discontinuity scan included.')
try:
 bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'));report['source']=check('source');source_road=sample([o for o in bpy.context.scene.objects if root(o).get('layer')=='roads'])
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update();report['base']=check('base')
 report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/models/base.glb','public/data/pavings.json']};report['passed']=True
except Exception as e:report['failure']=str(e);raise
finally:
 (ROOT/f'docs/model-checks/refinement/{PREFIX}-geometry.json').write_text(json.dumps(report,indent=2)+'\n');print('Civil forecourt road:',report['passed'],flush=True)
