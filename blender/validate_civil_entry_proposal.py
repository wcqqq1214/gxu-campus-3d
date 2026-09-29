"""Check the isolated portico candidate in both mesh detail modes, not photo fidelity."""
import argparse,json,math,sys,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from generic_buildings import ordinary_building
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--proposal',type=Path,required=True);parser.add_argument('--report',type=Path,required=True)
a=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);data=json.loads(a.proposal.read_text())
C={k:i for i,k in enumerate(['white','stone','pink','paleRoof','dark','glass','shadeGlass','blueRoof','red'])}
b=data['candidate'];entry=next(e for e in b['form']['entrances'] if e.get('porticoId')=='link-portico')
angle=math.radians(entry['bearing']);n=Vector((math.sin(angle),math.cos(angle),0));t=Vector((n.y,-n.x,0));front=Vector((*entry['outerCenter'],0))
porch=next(p for p in b['form']['parts'] if p['id']=='link-portico');corners=porch['polygons'][0][0][:-1]
length=min(math.dist(corners[1],corners[2]),math.dist(corners[3],corners[0]));gap=(length-2*1.15-11*.2)/12
checks=[];negative=[]
for detail in (False,True):
    m=ordinary_building(b,0,C,detail);tree=BVHTree.FromPolygons(m.v,m.f)
    previous=ordinary_building(data['original'],0,C,detail);old=BVHTree.FromPolygons(previous.v,previous.f)
    for i in range(12):
        v=(1.15+i*(gap+.2)+gap/2)/length
        p=Vector(tuple(sum(w*c[k] for w,c in zip([.5*(1-v),.5*(1-v),.5*v,.5*v],corners)) for k in (0,1))+(8,))
        hit=tree.ray_cast(p,Vector((0,0,-1)),2)[0]
        solid=i in (5,6,7,8,9)
        assert (hit is not None and abs(hit.z-7.2)<1e-4) if solid else hit is None,(detail,i,hit)
        checks.append(dict(detail=detail,bay=i,solid=solid,passed=True))
        if not solid:assert old.ray_cast(p,Vector((0,0,-1)),2)[0] is not None
    negative.append(dict(detail=detail,baselineBlocksAllSevenIntendedOpenings=True))
    for along in (-2.8,2.8):
        center=front+t*along-n*2.65+Vector((0,0,3.2))
        hit=tree.ray_cast(center-t,t,2)
        assert hit[0] is not None and .65<hit[3]<.7,(detail,along,hit)
        assert old.ray_cast(center-t,t,2)[0] is None
        checks.append(dict(detail=detail,rearColumnAlong=along,passed=True))
    for along in (-1.75,0,1.75):
        start=front+t*along+n+Vector((0,0,2.25))
        hit=tree.ray_cast(start,-n,5)
        assert hit[0] is not None and 4.3<hit[3]<4.7,(detail,along,hit)
        checks.append(dict(detail=detail,doorRouteAlong=along,hitDistance=hit[3],passed=True))
    # Every full column top fits the roof; center-only data validation is weaker.
    for i,c in enumerate(porch['openBelow']['columns']):
        for theta in [math.tau*j/16 for j in range(16)]:
            p=Vector((c['center'][0]+.32*math.cos(theta),c['center'][1]+.32*math.sin(theta),7.8))
            hit=tree.ray_cast(p,Vector((0,0,-1)),.7)[0]
            assert hit is not None and abs(hit.z-7.2)<1e-4,(detail,i,theta,hit)
        checks.append(dict(detail=detail,column=i,shaftTopRingSamples=16,passed=True))
report=dict(passed=True,scope='Candidate shared geometry and actual base/detail mesh functions; not exported campus GLB or photo fit',
 checks=checks,negative=negative,proposalSHA256=hashlib.sha256(a.proposal.read_bytes()).hexdigest(),
 photoRegistrationAccepted=False,productionReady=False,wholeBuildingAccepted=False)
a.report.write_text(json.dumps(report,indent=2)+'\n');print('PASS proposal:',len(checks),'records; two detail modes; baseline negative checks')
