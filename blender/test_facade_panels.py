"""Ray-test shared facade panels and replacement windows under rotation."""
import copy
import json
import math
import sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'blender'))
from generic_buildings import ordinary_building

b=next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']=='way/759129516')
C={name:i for i,name in enumerate(['stone','pink','white','glass','dark','shadeGlass','paleRoof','red'])}

def tree(mesh, material):
    return BVHTree.FromPolygons(mesh.v,[face for face,mat in zip(mesh.f,mesh.m) if mat==C[material]])

def check(mesh, building):
    glass=tree(mesh,'glass');dark=tree(mesh,'dark');white=tree(mesh,'white')
    def hit(t,point,normal):
        return t.ray_cast(Vector(point),-normal,1)[3]
    for f in building['form']['facades']:
        a=Vector((*f['start'],0));edge=Vector((*f['end'],0))-a;n=Vector((*f['normal'],0))
        for p in f['rule'].get('panels',[]):
            # First clear cell center is independent of default window centers.
            w=edge.length*(p['to']-p['from']);h=p['top']-p['bottom'];fw=p['frameWidth']
            cw=(w-2*fw)/p['columns'];ch=(h-2*fw)/p['rows']
            center=a+edge*(p['from']+(fw+cw/2)/edge.length)+Vector((0,0,p['bottom']+fw+ch/2))+n*.8
            actual=hit(dark if p['type']=='lattice' else glass,center,n)
            assert actual is not None and abs(actual-.76)<1e-4,(p['id'],'backing',actual)
            assert hit(white,center,n) is None,(p['id'],'blocked clear cell')
            if p['type']=='lattice':
                assert hit(glass,center,n) is None,(p['id'],'default glass behind screen')
                bar=center-edge.normalized()*cw/2
                actual=hit(white,bar,n)
                assert actual is not None and abs(actual-(.75-p['depth']))<1e-4,(p['id'],'screen bar',actual)
            # Outer frame stays at the upper half's left edge.
            frame=a+edge*(p['from']+fw/2/edge.length)+Vector((0,0,(p['bottom']+p['top'])/2))+n*.8
            actual=hit(white,frame,n)
            assert actual is not None and abs(actual-(.75-p['depth']))<1e-4,(p['id'],'frame',actual)

for angle in (0,math.pi/2,math.pi*.173):
    current=copy.deepcopy(b);c=math.cos(angle);s=math.sin(angle)
    def rotate(p):return [p[0]*c-p[1]*s,p[0]*s+p[1]*c]
    current['polygons']=[[[rotate(p) for p in ring] for ring in poly] for poly in b['polygons']]
    form=current['form']
    for part in form['parts']:
        part['polygons']=[[[rotate(p) for p in ring] for ring in poly] for poly in part['polygons']]
        if 'parapetEdges' in part:
            part['parapetEdges']=[[rotate(p) for p in pair] for pair in part['parapetEdges']]
    form['entrances']=[]  # Separate entry checks cover portico/door rotations.
    for f in form['facades']:
        for key in ('start','end','normal'):f[key]=rotate(f[key])
    models=[ordinary_building(current,0,C,detail) for detail in (False,True)]
    for mesh in models:check(mesh,current)
    def shared(mesh):
        _,start,end=next(p for p in mesh.parts if p[0]=='05_立面专项')
        return mesh.v[start:end]
    assert shared(models[0])==shared(models[1]),'Major panels changed across LOD'
print('Passed shared panels in both LODs at 0, 90 and 31.14 degrees; clear holes, backing materials, frame depths and default-window replacement')
