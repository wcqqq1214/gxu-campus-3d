"""Ray-test open ground galleries, baluster gaps and piers at three angles."""
import sys,json,copy,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from generic_buildings import ordinary_building
b=next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']=='way/759129515')
C={name:i for i,name in enumerate(['stone','pink','white','glass','dark','shadeGlass','paleRoof','red'])}
for angle in (0,math.pi/2,math.pi*.173):
 current=copy.deepcopy(b);c=math.cos(angle);s=math.sin(angle)
 def rotate(p):return [p[0]*c-p[1]*s,p[0]*s+p[1]*c]+list(p[2:])
 current['polygons']=[[[rotate(p) for p in ring] for ring in poly] for poly in current['polygons']]
 for part in current['form']['parts']:
  part['polygons']=[[[rotate(p) for p in ring] for ring in poly] for poly in part['polygons']]
  if 'parapetEdges' in part:part['parapetEdges']=[[rotate(p) for p in edge] for edge in part['parapetEdges']]
  if 'geometry' in part['roof']:part['roof']['geometry']['vertices']=[rotate(p) for p in part['roof']['geometry']['vertices']]
 current['form']['entrances']=[]
 for f in current['form']['facades']:
  for key in ('start','end','normal'):f[key]=rotate(f[key])
 meshes=[ordinary_building(current,0,C,detail) for detail in (False,True)]
 f=next(f for f in current['form']['facades'] if 'openCorridor' in f['rule']);a=Vector((*f['start'],0));edge=Vector((*f['end'],0))-a;u=edge.normalized();n=Vector((*f['normal'],0));length=edge.length
 for mesh in meshes:
  tree=BVHTree.FromPolygons(mesh.v,mesh.f)
  def hit(point,direction,distance=3):return tree.ray_cast(point,direction,distance)[3]
  for level in range(3):
   for bay in range(8):
    t=.3+(length-.6)*(bay+.5)/8
    p=a+u*t+Vector((0,0,level*3.3+1.8))
    rear=hit(p+n*.3,-n)
    assert rear is not None and 1.75<rear<2.101,('blocked gallery',angle,level,bay,rear)
    inside=p-n*.9
    assert abs(hit(inside,Vector((0,0,-1)))-1.8)<1e-4,'floor'
    assert abs(hit(inside,Vector((0,0,1)))-1.32)<1e-4,'ceiling'
   for i in range(9):
    t=.3+(length-.6)*i/8;p=a+u*t+Vector((0,0,level*3.3+1.5))
    assert abs(hit(p+n*.3,-n)-.3)<1e-4,'missing pier'
  count=math.ceil((length-.6)/.32)
  for level in (1,2):
   for i in (2,3,5):
    for t,blocked in [(.3+(length-.6)*(i+.5)/count,True),(.3+(length-.6)*(i+1)/count,False)]:
     p=a+u*t+Vector((0,0,level*3.3+.5))+n*.3
     assert (hit(p,-n,.7) is not None)==blocked,('baluster bar/gap',angle,level,i,blocked)
  p=a+u*(.3+(length-.6)*.5/8)+Vector((0,0,.5))+n*.3
  assert hit(p,-n,.7) is None,'ground floor railing blocks access'
 def body(m):
  _,start,end=next(part for part in m.parts if part[0]=='01_主体轮廓');return m.v[start:end]
 assert body(meshes[0])==body(meshes[1]),'gallery changes across LOD'
print('Passed ground/upper gallery voids, piers, slabs, baluster bars/gaps in both LODs at 0/90/31.14 degrees')
