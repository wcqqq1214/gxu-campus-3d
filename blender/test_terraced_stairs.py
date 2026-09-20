"""Both detail levels retain upper/other windows but not terrace-cut fragments."""
import sys,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from generic_buildings import ordinary_building
from terraced_stairs import blocks_window
C={n:i for i,n in enumerate(['stone','pink','white','glass','dark','shadeGlass','paleRoof','red'])}
s=dict(center=[15,0],tangent=[1,0],normal=[0,-1],width=12,upperWidth=4.8,upperOffset=-3.2,
 baseHeight=0,intermediateHeight=1.62,landingHeight=2.52,lowerRisers=9,upperRisers=5,tread=.32,
 landingDepth=1.2,intermediateDepth=1.6,upperFront=2.48,terraceFront=4.08,front=6.64)
assert blocks_window(s,15,-.07,0,-1,2.4,1,3)
assert not blocks_window(s,15,-.07,0,-1,2.4,4,6)
assert not blocks_window(s,2,-.07,0,-1,2.4,1,3)
assert not blocks_window(s,15,20.07,0,1,2.4,1,3)
ring=[[0,0],[30,0],[30,20],[0,20],[0,0]]
b=dict(id='way/terraced-test',name='fixture',category='academic',tags={},polygons=[[ring]],roofTriangles=[[0,1,2,0,2,3]],
 form=dict(version=1,height=10.8,levels=3,archetype='generic',parts=[],roof=dict(type='flat',rise=0),entrances=[],terracedStairs=s,
 facades=[dict(part='body',polygon=0,ring=0,edge=0,start=[0,0],end=[30,0],normal=[0,-1],height=10.8,levels=3,rule={})]))
for detail in (False,True):
 m=ordinary_building(b,0,C,detail);_,start,end=next(p for p in m.parts if p[0]=='04_立面窗格');rows=set();lower=[]
 for f,mat in zip(m.f,m.m):
  if mat not in (C['glass'],C['shadeGlass']) or not all(start<=i<end for i in f):continue
  points=[m.v[i] for i in f];level=math.floor(sum(p[2] for p in points)/len(points)/3.6);rows.add(level)
  if level==0:
   center=sum(p[0] for p in points)/len(points);lower.append(center)
   assert center<9 or center>21,(detail,center,'window fragment intersects terrace')
 assert rows=={0,1,2} and lower,(detail,rows,'unaffected window rows lost')
print('PASS terraced stairs window exclusion in both LODs; upper and outside rows preserved')
