"""Check that a middle-storey recess never moves windows on solid storeys."""
import sys,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from geometry import Mesh
from generic_buildings import ordinary_building
from facade_corridors import add_corridor_openings
C={name:i for i,name in enumerate(['stone','pink','white','glass','dark','shadeGlass','paleRoof','red'])}
ring=[[0,0],[30,0],[30,20],[0,20],[0,0]]
config={'depth':1.4,'firstLevel':2,'lastLevel':2,'railHeight':.9,'endInset':.3}
f={'part':'body','polygon':0,'ring':0,'edge':0,'start':[0,0],'end':[30,0],
   'normal':[0,-1],'height':16.5,'levels':5,'rule':{'balconies':False,'openCorridor':config}}
b={'id':'way/test-bounded-corridor','name':'fixture','category':'academic','tags':{},
   'polygons':[[ring]],'roofTriangles':[[0,1,2,0,2,3]],
   'form':{'version':1,'height':16.5,'levels':5,'archetype':'generic','parts':[],
           'roof':{'type':'flat','rise':0},'entrances':[],'facades':[f]}}
for detail in (False,True):
    mesh=ordinary_building(b,0,C,detail)
    _,start,end=next(p for p in mesh.parts if p[0]=='04_立面窗格')
    visited=set()
    for face,material in zip(mesh.f,mesh.m):
        if material not in (C['glass'],C['shadeGlass']) or not all(start<=i<end for i in face):continue
        vertices=[mesh.v[i] for i in face];level=math.floor(sum(v[2] for v in vertices)/len(vertices)/3.3)
        visited.add(level)
        center_y=(1.4 if level==2 else 0)-(.2 if detail else .07)
        assert all(abs(v[1]-center_y)<(.051 if detail else 1e-6) for v in vertices),(detail,level,vertices)
    assert visited==set(range(5)),(detail,visited)
# Explicit openings use the same bounded range rather than firstLevel alone.
f['rule']['openCorridor']={**config,'openings':[{'kind':'window','t':.5,'width':1,'height':1,'sill':1,'levels':[1,2,3]}]}
mesh=Mesh();add_corridor_openings(mesh,f,0,C);visited=set()
for face,material in zip(mesh.f,mesh.m):
    if material!=C['glass']:continue
    vertices=[mesh.v[i] for i in face];level=math.floor(sum(v[2] for v in vertices)/len(vertices)/3.3);visited.add(level)
    assert all(abs(v[1]-((1.4 if level==2 else 0)-.1))<=.041 for v in vertices),(level,vertices)
assert visited=={1,2,3}
print('PASS bounded corridor: five storeys in both LODs and explicit openings below/inside/above the recess')

# Mixed facades retain ordinary/band rows while replacing only the explicitly
# opened recess row. This exercises the actual generator in both LODs.
f['rule']={'balconies':False,'openCorridor':{
    'depth':1.1,'firstLevel':4,'lastLevel':4,'railHeight':.9,'endInset':.5,
    'openings':[{'kind':'window','t':.5,'width':2,'height':1.9,'sill':.9,'levels':[4]}]},
    'windowBands':{'from':.1,'to':.9,'firstLevel':1,'lastLevel':2,
        'heightRatio':.55,'depth':.38,'thickness':.18,
        'windows':[{'from':.15,'to':.4,'panes':3},{'from':.6,'to':.85,'panes':3}]}}
for detail in (False,True):
    mesh=ordinary_building(b,0,C,detail)
    _,start,end=next(p for p in mesh.parts if p[0]=='04_立面窗格')
    rows=set();explicit=0
    for face,material in zip(mesh.f,mesh.m):
        if material not in (C['glass'],C['shadeGlass']):continue
        vertices=[mesh.v[i] for i in face]
        level=math.floor(sum(v[2] for v in vertices)/len(vertices)/3.3)
        if all(start<=i<end for i in face):
            rows.add(level)
            assert level!=4,'Generic window duplicates the explicit recessed row'
            assert all(abs(v[1])<.26 for v in vertices),'Lower windows incorrectly recessed'
        else:
            explicit+=1
            assert level==4 and all(abs(v[1]-1)<.041 for v in vertices),'Explicit rear window missing its depth'
    assert rows=={0,1,2,3} and explicit==6,(detail,rows,explicit)
print('PASS mixed facade: preserved lower bands/default rows and one explicit recessed row in both LODs')
