"""Check the isolated portico candidate in both mesh detail modes, not photo fidelity."""
import argparse,copy,json,math,sys,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from generic_buildings import ordinary_building
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--proposal',type=Path,required=True);parser.add_argument('--report',type=Path,required=True)
parser.add_argument('--surround',action='store_true',help='Check estimated stone surround and bounded glazing')
parser.add_argument('--tall-surround',action='store_true',help='Check 8.6m proportional roof alternative')
parser.add_argument('--curved-roof',action='store_true',help='Check curved front and approximately 6m recess')
parser.add_argument('--refined-columns',action='store_true',help='Check camera-guided column layout and six-pane glazing')
parser.add_argument('--finished-portico',action='store_true',help='Check stone exterior, white soffit, capitals and subdivided side lattice')
a=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);data=json.loads(a.proposal.read_text())
C={k:i for i,k in enumerate(['white','stone','pink','paleRoof','dark','glass','shadeGlass','blueRoof','red'])}
b=data['candidate'];entry=next(e for e in b['form']['entrances'] if e.get('porticoId')=='link-portico')
angle=math.radians(entry['bearing']);n=Vector((math.sin(angle),math.cos(angle),0));t=Vector((n.y,-n.x,0));front=Vector((*entry['outerCenter'],0))
porch=next(p for p in b['form']['parts'] if p['id']=='link-portico');corners=porch['polygons'][0][0][:-1]
edge_width=1.55 if a.refined_columns else 1.15
if a.finished_portico:edge_width=1.65
length=min(math.dist(corners[1],corners[2]),math.dist(corners[3],corners[0]));gap=(length-2*edge_width-11*.2)/12
roof_height=8.6 if a.tall_surround else 7.2
assert not a.tall_surround or a.surround, 'Tall alternative requires surround checks'
assert not a.curved_roof or a.tall_surround, 'Curved alternative requires tall surround checks'
assert not a.refined_columns or a.curved_roof, 'Refined columns require the curved candidate'
assert not a.finished_portico or a.refined_columns, 'Finished portico requires refined columns'
checks=[];negative=[]
for detail in (False,True):
    m=ordinary_building(b,0,C,detail);tree=BVHTree.FromPolygons(m.v,m.f)
    previous=ordinary_building(data['original'],0,C,detail);old=BVHTree.FromPolygons(previous.v,previous.f)
    if a.finished_portico:
        plain=copy.deepcopy(b)
        for c in next(p for p in plain['form']['parts'] if p['id']=='link-portico')['openBelow']['columns']:c.pop('capital',None)
        plain_mesh=ordinary_building(plain,0,C,detail);plain_tree=BVHTree.FromPolygons(plain_mesh.v,plain_mesh.f)
        # Capitals are wider only at the top; every outer top vertex has support.
        for i,c in enumerate(porch['openBelow']['columns']):
            center=Vector((*c['center'],8.1));hit=tree.ray_cast(center+t,-t,1)
            assert hit[0] is not None and .58<hit[3]<.61 and m.m[hit[2]]==C['stone'],(i,hit)
            bare=plain_tree.ray_cast(center+t,-t,1)
            assert bare[0] is not None and bare[3]>.66,(i,bare)
            for theta in [math.tau*j/16 for j in range(16)]:
                top=Vector((c['center'][0]+.405*math.cos(theta),c['center'][1]+.405*math.sin(theta),8.24))
                roof_hit=tree.ray_cast(top,Vector((0,0,1)),.03)
                assert roof_hit[0] is not None and abs(roof_hit[0].z-8.25)<1e-4,(i,theta,roof_hit)
            checks.append(dict(detail=detail,capital=i,outerTopSupportSamples=16,passed=True))
        negative.append(dict(detail=detail,absentCapitalsFailWidthProbes=True))
        for along in (-8,-4,0,4,8):
            setback=.8*(1-(along/9)**2)
            hit=tree.ray_cast(front+t*along+n*.5+Vector((0,0,8.42)),-n,2)
            assert hit[0] is not None and m.m[hit[2]]==C['stone'],(along,hit)
            hit=tree.ray_cast(front+t*along-n*(setback+.2)+Vector((0,0,8)),Vector((0,0,1)),.3)
            assert hit[0] is not None and m.m[hit[2]]==C['white'],(along,hit)
            checks.append(dict(detail=detail,fasciaAlong=along,stoneExteriorWhiteSoffit=True,passed=True))
        # Three clear slots and two white dividers per original open bay.
        assert len(porch['openBelow']['roofGeometry']['polygons'][0])-1==21
        clear=(gap-2*.12)/3
        for i in (0,1,2,3,4,10,11):
            start=edge_width+i*(gap+.2)
            probes=[(start+j*(clear+.12)+clear/2,False) for j in range(3)]
            probes += [(start+j*clear+(j-.5)*.12,True) for j in (1,2)]
            for pos,solid in probes:
                v=pos/length
                p=Vector(tuple(sum(w*c[k] for w,c in zip([.5*(1-v),.5*(1-v),.5*v,.5*v],corners)) for k in (0,1))+(9.4,))
                hit=tree.ray_cast(p,Vector((0,0,-1)),1.5)
                assert (hit[0] is not None)==solid,(i,pos,solid,hit)
                if solid:assert abs(hit[0].z-8.6)<1e-4 and m.m[hit[2]]==C['white']
                checks.append(dict(detail=detail,subdividedBay=i,solid=solid,passed=True))
    if a.refined_columns:
        for along in (-4,4):
            depth=1+.8*(1-(along/9)**2)
            center=front+t*along-n*depth+Vector((0,0,3.2))
            hit=tree.ray_cast(center-t,t,2)
            assert hit[0] is not None and .65<hit[3]<.7,(detail,along,hit)
            checks.append(dict(detail=detail,frontColumnAlong=along,passed=True))
        # Interior divider locations are fixed independently of panel config.
        for along,height in [(2.425-.07-i*.785,5.8) for i in range(1,6)]+[(2.0,5.4675),(2.0,6.2325)]:
            start=front+t*along-n*5.4+Vector((0,0,height));hit=tree.ray_cast(start,-n,1)
            assert hit[0] is not None and m.m[hit[2]]==C['dark'],(detail,along,height,hit)
            checks.append(dict(detail=detail,glazingDividerAlong=along,height=height,passed=True))
    if a.curved_roof:
        for along in (-12,-9,-8,-6,-4,-2,0,2,4,6,8,9,12):
            setback=.8*max(0,1-(along/9)**2)
            for delta,inside in [(-.06,False),(.06,True)]:
                p=front+t*along-n*(setback+delta)+Vector((0,0,9.2))
                hit=tree.ray_cast(p,Vector((0,0,-1)),.8)[0]
                assert (hit is not None)==inside,(detail,along,delta,hit)
                checks.append(dict(detail=detail,curveAlong=along,inside=inside,passed=True))
                if not inside and abs(along)<=8:
                    assert old.ray_cast(p,Vector((0,0,-1)),2.5)[0] is not None
        negative.append(dict(detail=detail,oldStraightRoofOccupiesCurvedSetback=True))
    if a.tall_surround:
        absent=copy.deepcopy(b)
        absent['form']['facades']=[f for f in absent['form']['facades'] if f.get('region')!='above-portico']
        missing_mesh=ordinary_building(absent,0,C,detail)
        missing=BVHTree.FromPolygons(missing_mesh.v,missing_mesh.f)
        wall_start=Vector((-698.6939074704767,-760.4773988305454,0))
        wall_end=Vector((-698.8909494339341,-729.4075449670695,0))
        if a.curved_roof:
            wall_start=Vector((-701.0939074704767,-760.4739448185203,0))
            wall_end=Vector((-701.2909494339341,-729.4056767281803,0))
        for i in range(10):
            center=wall_start+(wall_end-wall_start)*((i+.5)/10)+Vector((0,0,9.8))
            for offset,expected in [(0,'glass'),(.515,'white')]:
                start=center+t*offset+n*.8;hit=tree.ray_cast(start,-n,1)
                assert hit[0] is not None and m.m[hit[2]]==C[expected],(detail,i,expected,hit)
                if expected=='glass':
                    hit_missing=missing.ray_cast(start,-n,1)
                    assert hit_missing[0] is not None and missing_mesh.m[hit_missing[2]]!=C['glass']
                checks.append(dict(detail=detail,clerestory=i,material=expected,passed=True))
        negative.append(dict(detail=detail,omittedClerestoryFailsAllTenGlazingProbes=True))
    if a.surround:
        # Start behind the column rows, using fixed design points independent
        # of panel rectangles. Stone must replace, not cover, a glass plane.
        glass=BVHTree.FromPolygons(m.v,[face for face,mat in zip(m.f,m.m) if mat==C['glass']])
        for along,height,material in [(0,7.7 if a.tall_surround else 6.35,'stone'),(-2.8,5.4,'stone'),(2.8,5.4,'stone'),
                (-5.225,3.2,'stone'),(5.225,3.2,'stone'),(-2.15,4.05,'stone'),(2.15,4.05,'stone'),
                (-2.15,2.4,'stone'),(2.15,2.4,'stone'),(.4,6.7 if a.tall_surround else 5.5,'glass'),(-3.5,4.2,'glass'),(3.5,4.2,'glass')]:
            start=front+t*along-n*(5.4 if a.curved_roof else 3)+Vector((0,0,height))
            hit=tree.ray_cast(start,-n,1)
            assert hit[0] is not None and m.m[hit[2]]==C[material],(detail,along,height,material,hit)
            if material=='stone':assert glass.ray_cast(start,-n,1)[0] is None,(detail,along,height,'hidden glass')
            checks.append(dict(detail=detail,surroundAlong=along,height=height,material=material,passed=True))
        start=front-n*3+Vector((0,0,6.35));hit=old.ray_cast(start,-n,1)
        assert hit[0] is not None and previous.m[hit[2]]!=C['stone']
        negative.append(dict(detail=detail,baselineLacksStoneSurround=True))
    for i in range(12):
        v=(edge_width+i*(gap+.2)+gap/2)/length
        p=Vector(tuple(sum(w*c[k] for w,c in zip([.5*(1-v),.5*(1-v),.5*v,.5*v],corners)) for k in (0,1))+(roof_height+.8,))
        hit=tree.ray_cast(p,Vector((0,0,-1)),3)[0]
        solid=i in (5,6,7,8,9)
        assert (hit is not None and abs(hit.z-roof_height)<1e-4) if solid else hit is None,(detail,i,hit)
        checks.append(dict(detail=detail,bay=i,solid=solid,passed=True))
        if not solid:assert old.ray_cast(p,Vector((0,0,-1)),3)[0] is not None
    negative.append(dict(detail=detail,baselineBlocksAllSevenIntendedOpenings=True))
    rear_half=2.35 if a.refined_columns else 2.8
    for along in (-rear_half,rear_half):
        rear_depth=3.8 if a.refined_columns else (4.7 if a.curved_roof else 2.65)
        center=front+t*along-n*rear_depth+Vector((0,0,3.2))
        hit=tree.ray_cast(center-t,t,2)
        assert hit[0] is not None and .65<hit[3]<.7,(detail,along,hit)
        assert old.ray_cast(center-t,t,2)[0] is None
        checks.append(dict(detail=detail,rearColumnAlong=along,passed=True))
    for along in (-1.75,0,1.75):
        start=front+t*along+n+Vector((0,0,2.25))
        hit=tree.ray_cast(start,-n,8 if a.curved_roof else 5)
        low,high=(6.7,7.1) if a.curved_roof else (4.3,4.7)
        assert hit[0] is not None and low<hit[3]<high,(detail,along,hit)
        checks.append(dict(detail=detail,doorRouteAlong=along,hitDistance=hit[3],passed=True))
    # Every full column top fits the roof; center-only data validation is weaker.
    for i,c in enumerate(porch['openBelow']['columns']):
        for theta in [math.tau*j/16 for j in range(16)]:
            p=Vector((c['center'][0]+.32*math.cos(theta),c['center'][1]+.32*math.sin(theta),roof_height+.6))
            hit=tree.ray_cast(p,Vector((0,0,-1)),.7)[0]
            assert hit is not None and abs(hit.z-roof_height)<1e-4,(detail,i,theta,hit)
        checks.append(dict(detail=detail,column=i,shaftTopRingSamples=16,passed=True))
report=dict(passed=True,scope='Candidate shared geometry and actual base/detail mesh functions; not exported campus GLB or photo fit',
 checks=checks,negative=negative,proposalSHA256=hashlib.sha256(a.proposal.read_bytes()).hexdigest(),
 photoRegistrationAccepted=False,productionReady=False,wholeBuildingAccepted=False)
a.report.write_text(json.dumps(report,indent=2)+'\n');print('PASS proposal:',len(checks),'records; two detail modes; baseline negative checks')
