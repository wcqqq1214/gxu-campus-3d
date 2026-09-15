"""Check all corridor types in both edge directions and three rotations."""
import copy,json,math,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from geometry import Mesh
from facade_corridors import add_corridor
checks=0
for b in json.loads((ROOT/'public/data/buildings.json').read_text()):
    for original in b.get('form',{}).get('facades',[]):
        if 'openCorridor' not in original['rule']:continue
        for reverse in (False,True):
            for angle in (0,.63,math.pi/2):
                f=copy.deepcopy(original);cs,sn=math.cos(angle),math.sin(angle)
                for key in ('start','end','normal'):
                    x,y=f[key];f[key]=[x*cs-y*sn,x*sn+y*cs]
                if reverse:f['start'],f['end']=f['end'],f['start']
                a=Vector((*f['start'],0));d=Vector((*f['end'],0))-a;length=d.length;u=d.normalized();n=Vector((*f['normal'],0));h=f['height'];rule=f['rule']['openCorridor'];fh=h/f['levels']
                mesh=Mesh();mesh.face([(*f['start'],-.5),(*f['end'],-.5),(*f['end'],h),(*f['start'],h)],0)
                add_corridor(mesh,f,0,0,1,2,pitched_roof=b['form']['roof']['type']!='flat')
                tree=BVHTree.FromPolygons(mesh.v,mesh.f)
                t=rule['endInset']+(length-2*rule['endInset'])*.5/rule.get('piers',{}).get('bays',1)
                for level in range(rule['firstLevel'],int(f['levels'])):
                    p=a+u*t+Vector((0,0,level*fh+1.8))
                    hit,normal,_,distance=tree.ray_cast(p+n*.3,-n,rule['depth']+.5)
                    assert hit is not None and abs(distance-rule['depth']-.3)<1e-4 and normal.dot(n)>.99,('rear normal',b['id'],reverse,angle)
                    for direction in (-1,1):
                        hit,normal,_,distance=tree.ray_cast(p-n*(rule['depth']/2),Vector((0,0,direction)),2)
                        assert hit is not None and normal.z*direction<-.99,('slab normal',b['id'],reverse,angle,direction)
                checks+=1
print('PASS corridor face directions:',checks,'facade/direction/rotation combinations')
