"""Verify accepted materials-college entry geometry in source, base and near assets.

Run Blender with --check-root=/path/to/candidate and --report=/path/to/report.json.
Photo proportions are estimated; these checks do not validate real-world dimensions.
"""
import bpy,sys,json,math,re
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parents[1]
P=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),R)
REPORT=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--report=')),R/'work/materials-entry-geometry.json')
sys.path.insert(0,str(R/'blender'))
bs=json.loads((P/'public/data/buildings.json').read_text());b=next(b for b in bs if b['id']=='relation/11564999');e=b['form']['entrances'][0];p=e['recessedStairEntry'];z=b['elevation'];angle=math.radians(e['bearing']);n=Vector((math.sin(angle),math.cos(angle),0));u=Vector((n.y,-n.x,0));front=Vector((*e['center'],z));up=Vector((0,0,1));point=lambda w,d,h:front+u*w-n*d+up*h

def finish_name(name):
 return re.sub(r'\.\d+$','',name).replace('entryBorderStone','stone')

def trees(objects):
 result=[]
 for o in objects:
  if o.type!='MESH':continue
  result.append((BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(f.vertices) for f in o.data.polygons]),[finish_name(o.data.materials[f.material_index].name) for f in o.data.polygons]))
 return result

def ray(ts,start,direction,distance):
 hits=[]
 for tree,mats in ts:
  pos,normal,index,dist=tree.ray_cast(start,direction,distance)
  if pos is not None:hits.append((dist,pos,normal,mats[index]))
 return min(hits,key=lambda x:x[0],default=None)

def parking_joint_alignment(objects):
 # Inspect actual source/exported UVs after batching and quantization.
 # Hole centres must sit halfway between texture joints in both directions.
 triangles=[]
 for o in objects:
  if o.type!='MESH' or not o.data.uv_layers.active:continue
  mesh=o.data;uvs=mesh.uv_layers.active.data
  for f in mesh.polygons:
   if re.sub(r'\.\d+$','',mesh.materials[f.material_index].name)!='path':continue
   verts=[]
   for loop in f.loop_indices:
    q=o.matrix_world@mesh.vertices[mesh.loops[loop].vertex_index].co-front
    verts.append((q.dot(u),-q.dot(n),tuple(uvs[loop].uv)))
   for i in range(1,len(verts)-1):
    a,b,c=verts[0],verts[i],verts[i+1]
    den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
    if abs(den)>1e-9:triangles.append((a,b,c,den))
 errors=[]
 for w0 in (-20.7,16.5):
  for i in range(7):
   for j in range(28):
    w=w0+i*.6+.14;d=-19+j*.65+.14;sample=None
    for a,b,c,den in triangles:
     aa=((b[1]-c[1])*(w-c[0])+(c[0]-b[0])*(d-c[1]))/den
     bb=((c[1]-a[1])*(w-c[0])+(a[0]-c[0])*(d-c[1]))/den
     if min(aa,bb,1-aa-bb)<-1e-6:continue
     sample=[aa*a[2][k]+bb*b[2][k]+(1-aa-bb)*c[2][k] for k in (0,1)];break
    assert sample is not None,('missing parking UV probe',w,d)
    error=max(abs((sample[0]*2)%1-.5),abs((sample[1]*4)%1-.5))
    assert error<.012,('paving joint crosses grass-cell centre',w,d,sample,error)
    errors.append(error)
 return max(errors)


def border_course_alignment(objects):
 # Find the lowest horizontal stone finish below the projecting coping.
 # Test transverse joints on both legs of the border after export.
 tris=[];nose_corners=[]
 for o in objects:
  if o.type!='MESH' or not o.data.uv_layers.active:continue
  m=o.data;uv=m.uv_layers.active.data
  for f in m.polygons:
   if re.sub(r'\.\d+$','',m.materials[f.material_index].name)!='entryBorderStone':continue
   vs=[]
   for loop in f.loop_indices:
    q=o.matrix_world@m.vertices[m.loops[loop].vertex_index].co-front
    vs.append((q.dot(u),-q.dot(n),q.z,tuple(uv[loop].uv)))
   nose_corners.extend(v[3][1]*4 for v in vs if abs(v[1]+8.8)<.015 and 15.99<abs(v[0])<16.08)
   for i in range(1,len(vs)-1):
    a,b,c=vs[0],vs[i],vs[i+1];den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
    if abs(den)>1e-9:tris.append((a,b,c,den))
 assert nose_corners and min(nose_corners)>15.995 and max(nose_corners)<16.04,('nose short-cut stone',nose_corners)
 probes=[(side*16.12,-19+j*.65+.14,1,4) for side in (-1,1) for j in range(17,28)]
 nose_probes=[(side*16.03,d,1,4) for side in (-1,1) for d in (-8.79,-8.77,-8.74,-8.6,-8.4)]
 probes += [(w0+i*.6+.14,-.38,0,2) for w0 in (-20.7,16.5) for i in range(7)]
 errors=[]
 for w,d,axis,factor in probes+nose_probes:
  candidates=[]
  for a,b,c,den in tris:
   aa=((b[1]-c[1])*(w-c[0])+(c[0]-b[0])*(d-c[1]))/den;bb=((c[1]-a[1])*(w-c[0])+(a[0]-c[0])*(d-c[1]))/den
   if min(aa,bb,1-aa-bb)<-1e-6:continue
   candidates.append((aa*a[2]+bb*b[2]+(1-aa-bb)*c[2],aa*a[3][axis]+bb*b[3][axis]+(1-aa-bb)*c[3][axis]))
  assert candidates,('missing border UV',w,d)
  value=min(candidates)[1]
  if (w,d,axis,factor) in nose_probes:
   # The first 40 cm belong to one cut stone, with no interior seam/sliver.
   # Allow the measured UV quantization error at the starting boundary.
   assert 16.-.015 < value*factor < 16.75,('fragmented wall-foot nose',w,d,value*factor)
   continue
  error=abs((value*factor)%1-.5)
  assert error<.015,('border course joint alignment',w,d,error)
  errors.append(error)
 return max(errors)


def check(objects,ground,tol,roads):
 ts=trees(objects);rows=[]
 def top(kind,w,d,h):
  hit=ray(ts,point(w,d,h+.12),-up,.3)
  assert hit and abs(hit[1].z-z-h)<tol,(kind,w,d,h,hit)
  assert hit[2].z>.93,(kind,'top facing down',hit)
  rows.append(dict(kind=kind,w=w,d=d,expected=h,actual=hit[1].z-z))
 # Independently fixed accepted rise/run, not values inferred from mesh.
 for i in range(13):
  d=-5.4+(i+.5)*.3;h=4.0+2.6*(i+1)/14
  for w in (-5,0,5):top('outer-tread',w,d,h)
  assert ray(ts,point(0,d,h+.1),up,2) is None,('blocked outer flight',i)
 for i in range(21):
  d=p['innerStart']+(i+.5)*.3;h=6.6+3.3*(i+1)/22
  for w in (-3,0,3):top('inner-tread',w,d,h)
  assert ray(ts,point(0,d,h+.1),up,2) is None,('blocked inner flight',i)
 for w in (-3,0,3):top('intermediate',w,6.2,6.6);top('rear-landing',w,15.2,9.9)
 for w in (-4.5,4.5):
  for d in (1.3,7.1):
   hit=ray(ts,point(w,d,8)+n,-n,1.2)
   assert hit and hit[3]=='white' and abs(hit[0]-.675)<tol+.01,('round support',w,d,hit)
   hit=ray(ts,point(w,d,6.85)+n,-n,1.2)
   assert hit and hit[3]=='dark',('column foot sleeve missing',w,d)
 for side in (-1,1):
  hit=ray(ts,point(side*5.5,4,7.2),u*side,.6)
  assert hit and hit[3]=='entryGuardGlass',('landing guard panel missing',side)
  hit=ray(ts,point(side*5.88,4,7.8),-up,.3)
  assert hit and hit[3]=='dark' and abs(hit[1].z-z-7.68)<tol+.02,('guard top proportion',side)
 for d in (.8,7.6):top('canopy-crossbeam',0,d,14.4)
 if 'portalBeam' in p['canopy']:
  top('portal-beam',0,1.3,18.8)
  hit=ray(ts,point(0,1.3,17.4),up,.6)
  assert hit and abs(hit[1].z-z-17.7)<tol and hit[2].z<-.93,('portal beam soffit',hit)
  for w in (-4.5,4.5):
   hit=ray(ts,point(w,1.3,15)+n,-n,1.2)
   assert hit and hit[3]=='white',('upper column shaft missing',w,hit)
 # Mid-bay holes stay open below the existing high lattice.
 assert ray(ts,point(0,2,14.2),up,2) is None,'low lattice accidentally filled'
 top('canopy-rib',5/7,2,14.4)
 hall=p.get('hall');door_d=p['recess']+(hall['depth'] if hall else 0)-.08
 hit=ray(ts,point(1,door_d-.4,11.3),-n,.6)
 assert hit and hit[3]=='glass',('rear glass door',hit)
 if hall:
  # Independently probe the full walking volume, including the old facade
  # plane. A door painted over an intact wall must fail these rays.
  for w in (-4.8,-2,0,2,4.8):
   for h in (10.3,11.3,12.8,14):
    assert ray(ts,point(w,p['recess']-.3,h),-n,4.8) is None,('hall blocked',w,h)
   for d in (16.5,18,20):
    top('hall-floor',w,d,9.9)
    hit=ray(ts,point(w,d,14),up,.6)
    assert hit and abs(hit[1].z-z-14.3)<tol and hit[2].z<-.93,('hall ceiling',w,d,hit)
  for w in (-5.2,5.2):
   for d in (3,8,12):top('side-gallery',w,d,9.9)
  # No guard crosses the transition from stair landing into side aisles.
  for side in (-1,1):
   assert ray(ts,point(side*3.8,15,10.4),u*side,1.8) is None,'gallery access blocked'
 # Separate lower flight, raised cross-landing and genuinely open side courts.
 for i in range(7):
  for w in (-8,0,8):top('lower-tread',w,-10.5+(i+.5)*.3,2.8+.15*(i+1))
 for w in (-14,-6,0,6,14):top('raised-terrace',w,-7,4)
 for side in (-1,1):
  for d in (-4.5,-3,-1):
   top('sunken-floor',side*8.5,d,1.3)
   assert ray(ts,point(side*8.5,d,1.4),up,5) is None,('sunken court capped',side,d)
  for i in range(15):top('court-descending-tread',side*12.1,-5.4+(i+.5)*.25,4-.16875*(i+1))
  assert ray(ts,point(side*12.1,-5.7,4.5),-n,.5) is None,'descending stair entrance blocked'
  for d in (-1.5,-.5):top('court-bottom-landing',side*12.1,d,1.3)
  assert ray(ts,point(side*12.1,-1,1.8),-u*side,3) is None,'lower landing cannot turn into court'
  # Paired sloping handrails above the descending flight, below the
  # separate level retaining-wall guard.
  for w in (11.45,12.75):
   hit=ray(ts,point(side*w,-3.525,3.7),-up,.5)
   assert hit and hit[3]=='dark',('descending handrail missing',side,w)
  top('outer-walk' ,side*14.5,-3,4)
 # Ground and pavement samples span every external patch, plus the low approach.
 # The outer grade now continues all the way to the level stair approach;
 # no abrupt change of slope is left at the old two-metre perimeter strip.
 plaza=p['landscape']['groundPatches'][0]
 def plaza_height(w,d):
  vs=plaza['vertices'];ids=plaza['triangles']
  for i in range(0,len(ids),3):
   a,b,c=[vs[k] for k in ids[i:i+3]]
   den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
   u=((b[1]-c[1])*(w-c[0])+(c[0]-b[0])*(d-c[1]))/den
   v=((c[1]-a[1])*(w-c[0])+(a[0]-c[0])*(d-c[1]))/den
   if min(u,v,1-u-v)>=-1e-6:return u*a[2]+v*b[2]+(1-u-v)*c[2]
  raise AssertionError('Plaza sample outside paving')
 for w in (-15,-8,0,8,15):
  for d in (-23.5,-21,-18,-15,-12.1):top('graded-plaza',w,d,plaza_height(w,d))
 for w in (-8,0,8):
  for d in (-11.9,-11.2,-10.6):top('level-stair-approach',w,d,2.8)
 clearances=[]
 for patch in p['landscape']['groundPatches']:
  vs=patch['vertices'];indices=patch['triangles']
  for i in range(0,len(indices),3):
   tri=[vs[k] for k in indices[i:i+3]];w,d,h=[sum(v[k] for v in tri)/3 for k in (0,1,2)]
   hit=ray(ts,point(w,d,h+.15),-up,.3);g=ray(ground,point(w,d,h+1),-up,10)
   assert hit and g,('missing external paving',patch['id'],w,d)
   clearance=hit[1].z-g[1].z
   assert .002<clearance<.09,('paving bedding contact',patch['id'],w,d,clearance)
   clearances.append(clearance)
 for w in (-8,0,8):
  hit=ray(ts,point(w,-11.9,3.2),-up,1);g=ray(ground,point(w,-11.9,4),-up,5)
  assert hit and g and .002<hit[1].z-g[1].z<.09,'low approach bedding clearance'
 # Probe the visible lawn side, not just the hidden soil under a paving
 # centroid: a deep skirt used to hide an artificially lowered perimeter.
 edges=[(w,-24,0,-1) for w in (-15,-10,-5,0,5,10,15)]
 edges += [(side*16,d,side,0) for side in (-1,1) for d in (-23,-21)]
 edges += [(w,-20,0,-1) for w in (-21,-19,-17,17,19,23,26,29)]
 edges += [(w,-.3,0,1) for w in (-21,-19,-17,17,19,23,26,29)]
 edge_steps=[]
 for w,d,dw,dd in edges:
  paving=ray(ts,point(w-dw*.08,d-dd*.08,12),-up,15)
  lawn=ray(ground,point(w+dw*.08,d+dd*.08,12),-up,15)
  assert paving and lawn,('missing outer edge',w,d)
  step=paving[1].z-lawn[1].z
  assert -.04<step<.13,('outer paving looks like a raised plinth',w,d,step,paving,lawn)
  edge_steps.append(step)
 for w in (-10,-5,0,5,10):
  for d in (-1,-3,-4.5):
   assert ray(roads,point(w,d,10),-up,20) is None,('old road remains below entrance',w,d)
 # Parking / side access must meet the actual retained road mesh in height.
 joins=[]
 for patch in p['landscape']['groundPatches']:
  if patch['id'] not in ('north-parking','south-access'):continue
  side=-1 if patch['id']=='north-parking' else 1
  for d in (-18,-15,-12,-9,-6,-3,-1,-.5):
   edges=[];ring=patch['boundary']
   for a,b in zip(ring,ring[1:]):
    if min(a[1],b[1])<=d<=max(a[1],b[1]) and abs(b[1]-a[1])>1e-7:
     edges.append(a[0]+(b[0]-a[0])*(d-a[1])/(b[1]-a[1]))
   w=min(edges) if side<0 else max(edges)
   paving=ray(ts,point(w-side*.08,d,12),-up,15);road=ray(roads,point(w+side*.08,d,12),-up,15)
   assert paving and road,('missing parking/road contact',patch['id'],d)
   step=paving[1].z-road[1].z
   assert abs(step)<.12,('parking edge suspended above or below road',patch['id'],d,step)
   joins.append(step)
 # The lane also wraps behind both parking areas. These checks must not
 # silently skip asphalt when checking the rear edge against nearby soil.
 rear_joins=[]
 for w in (-21.5,-21,-20,-19,-18,-17,17,18,19,20,21,23,25,27,28,29):
  paving=ray(ts,point(w,-.38,12),-up,15);road=ray(roads,point(w,-.22,12),-up,15)
  assert paving and road,('missing rear parking/road join',w)
  step=paving[1].z-road[1].z
  assert -.04<step<.12,('rear parking/road step',w,step)
  rear_joins.append(step)
 # South parking and access share one grading field. A narrow trough or
 # ridge on their seam must not be hidden by matching the edge height only.
 seam_breaks=[]
 for d in (-6,-4,-2,-.5):
  # The two materials quantize separately; sample either side, then
  # extrapolate both planes to the seam instead of casting on its edge.
  hits=[ray(ts,point(w,d,12),-up,15) for w in (20.8,20.96,21.04,21.2)]
  assert all(hits),('missing parking/access seam',d)
  heights=[h[1].z for h in hits]
  left=(heights[1]-heights[0])/.16;right=(heights[3]-heights[2])/.16
  assert abs(heights[1]+left*.04-heights[2]+right*.04)<tol+.008,('parking/access height seam',d)
  bend=abs(right-left)
  assert bend<.06,('parking/access slope break',d,bend)
  seam_breaks.append(bend)
 # The adjusted parking plane must meet the outside retaining face below
 # its coping, without exposing a floating wall foot or filling the court.
 for side in (-1,1):
  for d in (-6,-4,-2,-.6):
   paving=ray(ts,point(side*16.25,d,12),-up,15)
   assert paving,('missing wall-side parking',side,d)
   h=paving[1].z-z+.15
   wall=ray(ts,point(side*16.25,d,h),-u*side,.4)
   assert wall and wall[3]=='stone' and abs(wall[0]-.25)<tol+.01,('parking/retaining wall gap',side,d,wall)
 # Sample below the projecting wall coping: the narrow margin must sit on
 # the parking grade, not on a new raised foundation or kerb.
 wall_slopes=[]
 for side in (-1,1):
  for d in (-6,-4,-2):
   a=ray(ts,point(side*16.3,d,3.8),-up,3)
   b=ray(ts,point(side*16.8,d,3.8),-up,3)
   assert a and b,('missing wall-foot paving',side,d)
   slope=(b[1].z-a[1].z)/.5
   assert 0<slope<(.14 if side<0 else .06),('steep or reversed wall-side crossfall',side,d,slope)
   wall_slopes.append(abs(slope))
   trim=ray(ts,point(side*16.12,d,3.8),-up,3)
   expected=a[1].z-slope*.18
   assert trim and trim[3]=='stone' and abs(trim[1].z-expected)<.02+tol,('wall-foot trim not flush',side,d,trim)
   assert ray(ts,trim[1]-up*.002,-up,.02) is None,('stacked paving below wall-foot inlay',side,d)
  corner=ray(ts,point(side*16.35,-.65,3.8),-up,3)
  assert corner and corner[3]=='stone',('missing bevel at rear wall-foot return',side)
  for w,d,material in ((16.03,-8.76,'stone'),(16.15,-8.65,'path'),(16.13,-8.4,'stone'),(16.22,-8.25,'path'),(16.22,-7.95,'stone')):
   end=ray(ts,point(side*w,d,3.8),-up,3)
   assert end and end[3]==material,('wall-foot inlay has a blunt start',side,d,end)
 # The north rear margin ends with a finite, flush mouth at the lane,
 # rather than a zero-width triangle that can collapse during quantization.
 for w,d,material in ((-21.84,-.33,'stone'),(-21.84,-.40,'path'),(-21.6,-.37,'stone')):
  hit=ray(ts,point(w,d,3.8),-up,3)
  assert hit and hit[3]==material,('rear inlay/lane junction',w,d,hit)
 # The stone rear course must continue down the road-facing shallow edge.
 for w in (-20,-18,18,20):
  top=ray(ts,point(w,-.33,3.8),-up,3)
  assert top and top[3]=='stone',('rear border top',w,top)
  edge=ray(ts,point(w,-.55,top[1].z-z-.04),-n,.35)
  assert edge and edge[3]=='stone' and abs(edge[0]-.25)<.02+tol,('rear stone edge material discontinuity',w,edge)
 # Closely probe rear grass-cell edges as well as their centres. A reduced
 # lift must remain clear of the paving after each LOD's quantization.
 grass_clearances=[]
 for w0 in (-20.7,16.5):
  for i in range(7):
   for j in range(14,28):
    for dw,dd in ((.14,.14),(.03,.03),(.25,.03),(.03,.25),(.25,.25)):
     w=w0+i*.6+dw;d=-19+j*.65+dd
     grass=ray(ts,point(w,d,6),-up,6)
     assert grass and grass[3]=='green',('missing or buried grass-cell edge',w,d,grass)
     paving=ray(ts,grass[1]-up*.0002,-up,.025)
     assert paving and paving[3]=='path',('grass-cell backing missing',w,d,paving)
     clearance=grass[1].z-paving[1].z
     assert .0004<clearance<.012,('grass-cell lift or intersection',w,d,clearance)
     grass_clearances.append(clearance)
 # Check the neighbouring grades as well as the last road-matching strip:
 # moving the whole slope break one station inward is not a smooth join.
 transition_bends=[]
 for w in (-20,-18,-16.3,16.3,18,20,20.9,21.1,23,25,27,29):
  stations=(-10,-8,-6,-4,-2,-.9,-.34);heights=[]
  for d in stations:
   hit=ray(ts,point(w,d,3.8),-up,3)
   # Grass-cell lifts vary between 4 and 8 mm above the paving grade.
   if hit and hit[3]=='green':hit=ray(ts,hit[1]-up*.0002,-up,.03)
   assert hit,('missing rear blending station',w,d)
   heights.append(hit[1].z)
  slopes=[(b-a)/(db-da) for a,b,da,db in zip(heights,heights[1:],stations,stations[1:])]
  bend=max(abs(b-a) for a,b in zip(slopes,slopes[1:]))
  inner_bend=max(abs(b-a) for a,b in zip(slopes[2:],slopes[3:]))
  assert inner_bend<.055,('concentrated parking grade change before rear edge',w,inner_bend)
  assert bend<.06,('upstream parking grade change',w,bend)
  transition_bends.append(bend)
 # The last paving strip meets the slope of the retained lane, rather than
 # only matching its edge height. Avoid the two existing south road planes'
 # junction and the narrow side-edge blend when probing this transition.
 rear_bends=[]
 for w in (-20,-18,-17,17,19,20,23,25,27):
  a=ray(ts,point(w,-.8,3.8),-up,3)
  b0=ray(ts,point(w,-.55,3.8),-up,3)
  assert a and b0,('missing rear transition',w)
  paving_slope=(b0[1].z-a[1].z)/.25
  # The lane is clipped to a narrow remnant behind this edge. Its decoded
  # sliver normals are unstable, so all LODs use the retained source road
  # plane as the slope reference; actual decoded edge heights are tested above.
  road_slope=road_reference_slopes[w]
  bend=abs(paving_slope-road_slope)
  assert bend<.03,('abrupt rear paving/road slope',w,bend,paving_slope,road_slope)
  rear_bends.append(bend)
 # Existing upper frame, side voids and courtyard opening remain.
 for w in (-6.6,6.6):assert ray(ts,point(w,15,20),-up,19) is None,('court side filled',w)
 assert ray(ts,point(0,15,20),-up,9.5) is None,'rear court capped'
 return dict(passed=True,borderJointPhaseError=border_course_alignment(objects),parkingJointPhaseError=parking_joint_alignment(objects),grassMinClearance=min(grass_clearances),grassMaxClearance=max(grass_clearances),probes=rows,apronMinClearance=min(clearances),apronMaxClearance=max(clearances),canopyGaps=True,rearDoor=True,passageClear=True,parkingRoadMaxStep=max(abs(v) for v in joins),outerEdgeMaxStep=max(edge_steps),rearParkingRoadMaxStep=max(abs(v) for v in rear_joins),parkingAccessMaxSlopeBreak=max(seam_breaks),wallSideMaxCrossfall=max(wall_slopes),wallFootTrim=True,rearRoadMaxSlopeBreak=max(rear_bends),rearTransitionMaxSlopeBreak=max(transition_bends))

def root_name(o):
 while o.parent:o=o.parent
 return re.sub(r'\.\d+$','',o.name)
report={}
bpy.ops.wm.open_mainfile(filepath=str(P/'blender/gxu-campus.blend'))
road_reference_slopes={}
source_roads=trees([bpy.data.objects['roads']])
for w in (-20,-18,-17,17,19,20,23,25,27):
 hit=ray(source_roads,point(w,-.22,12),-up,15)
 assert hit,('missing source rear road reference',w)
 road_reference_slopes[w]=hit[2].dot(n)/hit[2].z
report['source']=check([o for o in bpy.context.scene.objects if o.get('featureId')==b['id']],trees([o for o in bpy.context.scene.objects if o.get('layer') in ('terrain','roads')]),.008,trees([bpy.data.objects['roads']]))
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(P/'public/models/base.glb'));bpy.context.view_layer.update();ground=trees([o for o in bpy.context.scene.objects if root_name(o) in ('terrain','roads')])
roads=trees([o for o in bpy.context.scene.objects if root_name(o)=='roads'])
report['base']=check([o for o in bpy.context.scene.objects if root_name(o)==b['chunk']],ground,.05,roads)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(P/f"public/models/{b['chunk']}.glb"));bpy.context.view_layer.update()
report['near']=check(list(bpy.context.scene.objects),ground,.02,roads)
REPORT.parent.mkdir(parents=True,exist_ok=True);REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2));print('Source/base/near: stair treads, apron grounding, door, lattice gaps and courtyard probes passed')
