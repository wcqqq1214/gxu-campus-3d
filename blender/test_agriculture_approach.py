import sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'blender'))
from inspect_agriculture_approach import inspect
b={'elevation':0,'form':{'entrances':[{'id':'south-portico-door','porticoWidth':18,'outerCenter':[0,0],'bearing':180,'platformHeight':.45}]}}
def stairs(x,y,top,bottom):
 return .45 if -y<.3 else .3 if -y<.6 else .15 if -y<=.91 else None
flat=lambda x,y,top,bottom:0
terrain=lambda x,y,top,bottom:-.2
result=inspect(b,stairs,flat,terrain,'source');assert result['passed']
assert abs(result['outerRiserRange'][0]-.15)<1e-10
for name,road,ground in [('high-riser',lambda *a:-.18,terrain),('crossfall',lambda x,*a:x*.02,terrain),('missing-road',lambda *a:None,terrain),('buried-tread',flat,lambda *a:.4)]:
 r=inspect(b,stairs,road,ground,'source');assert not r['passed'],name
 assert r['failures'],name
 print(name,'rejected')
print('Five analytic interface cases passed: level approach accepted; tall riser, crossfall, missing road and burial rejected.')
