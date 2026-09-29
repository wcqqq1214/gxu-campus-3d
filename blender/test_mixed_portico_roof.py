"""Check real shared-form mesh surfaces and voids using a generated synthetic fixture."""
import argparse,json,math,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from generic_buildings import shared_form
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--fixture',type=Path,required=True)
parser.add_argument('--report',type=Path,required=True)
a=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
fixture=json.loads(a.fixture.read_text());checks=[]
for case in fixture['cases']:
    angle=case['angle'];mesh=shared_form(case['building'],0,{'white':0,'stone':1,'paleRoof':2})
    tree=BVHTree.FromPolygons(mesh.v,mesh.f)
    def probe(x,y,z,direction,distance):
        p=Vector((50+x*math.cos(angle)-y*math.sin(angle),-24+x*math.sin(angle)+y*math.cos(angle),z))
        return tree.ray_cast(p,Vector(direction),distance)
    gap=(16-1.6-7*.3)/8
    for i in range(8):
        y=.8+i*(gap+.3)+gap/2
        for x in (2,4.5,7):
            top=probe(x,y,8,(0,0,-1),2)
            bottom=probe(x,y,6,(0,0,1),2)
            if i in (2,3,4,5):
                assert top[0] is not None and abs(top[0].z-7.2)<1e-5 and top[1].z>.999
                assert bottom[0] is not None and abs(bottom[0].z-6.8)<1e-5 and bottom[1].z<-.999
            else:
                assert top[0] is None and bottom[0] is None,(angle,i,x,top,bottom)
            checks.append(dict(angle=angle,bay=i,x=x,solid=i in (2,3,4,5),topAndUnderside=True))
    for x,y in ((.4,8),(8.6,8),(4.5,.4),(4.5,15.6)):
        p=probe(x,y,8,(0,0,-1),2)[0];assert p is not None and abs(p.z-7.2)<1e-5
        checks.append(dict(angle=angle,perimeter=[x,y],passed=True))
    for x,y in ((2,1.2),(4.5,8),(7,14.8)):
        p=probe(x,y,3,(0,0,-1),3)[0];assert p is not None and abs(p.z-1.05)<1e-5
        checks.append(dict(angle=angle,floor=[x,y],passed=True))
report=dict(passed=True,scope=fixture['scope'],cases=len(fixture['cases']),checks=checks,
            method='BVH rays on shared_form mesh, including both roof faces, real open bays and continuous floor',
            campusGeometryChanged=False,wholeBuildingAccepted=False)
a.report.write_text(json.dumps(report,indent=2)+'\n')
print('PASS mixed portico roof:',len(checks),'records, two rotations')
