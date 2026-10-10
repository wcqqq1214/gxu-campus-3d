"""Probe actual study meshes: treads, landings, headroom, guards and normals."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'blender'))
from geometry import Mesh
from switchback_stairs import add_switchback_stairs


def inspect(stairs):
    s=stairs;mesh=Mesh();add_switchback_stairs(mesh,s,0,0)
    tree=BVHTree.FromPolygons(mesh.v,mesh.f)
    n=Vector((*s['normal'],0));u=Vector((*s['tangent'],0));origin=Vector((*s['center'],0))
    point=lambda along,out,height:origin+u*along+n*out+Vector((0,0,height))
    up=Vector((0,0,1)); samples=[];clearances=[]
    def probe(along,out,height,kind):
        p=point(along,out,height)
        hit=tree.ray_cast(p+up*.04,-up,.1)
        assert hit[0] is not None and abs(hit[0].z-height)<1e-4,(kind,height,hit)
        assert hit[1].z>.99,(kind,'inverted top normal')
        samples.append(dict(kind=kind,expected=height,actual=hit[0].z))
        return p
    for level in s['levels']:probe(0,s['landingDepth']/2,level,'building-landing')
    for index,(bottom,top) in enumerate(zip(s['levels'],s['levels'][1:])):
        middle=(bottom+top)/2
        probe(0,s['depth']-s['landingDepth']/2,middle,'outer-landing')
        for lane,direction,base in ((s['firstLane'],1,bottom),(-s['firstLane'],-1,middle)):
            along=lane*(s['gap']+s['flightWidth'])/2
            start=s['landingDepth'] if direction>0 else s['landingDepth']+s['run']
            for i in range(1,s['risers']):
                out=start+direction*(i-.5)*s['tread'];height=base+i*(top-bottom)/(2*s['risers'])
                p=probe(along,out,height,'tread')
                if index<len(s['levels'])-2:
                    # A direct 2.75 m upward sweep must stay clear at the lane center.
                    hit=tree.ray_cast(p+up*.01,up,2.75)
                    assert hit[0] is None,('insufficient candidate headroom',height,hit)
                    clearances.append(2.75)
            # The waist has an outward (downward) underside, not an open ramp.
            out=s['landingDepth']+s['run']/2
            p=point(along,out,(bottom+middle)/2 if direction>0 else (middle+top)/2)
            hit=tree.ray_cast(p-up*.6,up,1)
            assert hit[0] is not None and hit[1].z<-.7,'Missing or inverted waist underside'
        p=point(0,s['depth']-s['landingDepth']/2,middle+.5)
        for side in (-1,1):
            hit=tree.ray_cast(p,u*side,s['width'])
            assert hit[0] is not None and abs(hit[3]-(s['width']/2-s['railThickness']))<1e-4
            assert hit[1].dot(u*side)<-.99,'Inner guard face normal wrong'
        hit=tree.ray_cast(p,n,s['depth'])
        assert hit[0] is not None and hit[1].dot(n)<-.99,'Outer landing guard missing'
    # Do not allow degenerate caps to disappear silently during export.
    for face in mesh.f:
        a,b,c=[Vector(mesh.v[i]) for i in face[:3]]
        assert (b-a).cross(c-a).length>1e-8,'Degenerate stair face'
    return dict(samples=samples,treadAndLandingSamples=len(samples),headroomSamples=len(clearances),
                headroomProbeLength=2.75,waistUndersides=2*(len(s['levels'])-1),
                guardChecks=3*(len(s['levels'])-1),triangles=sum(len(f)-2 for f in mesh.f),passed=True)


parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--proposal',type=Path,required=True)
parser.add_argument('--report',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
proposal=json.loads(args.proposal.read_text())
if hashlib.sha256((ROOT/'public/data/buildings.json').read_bytes()).hexdigest()!=proposal['sourceSha256']:
    raise ValueError('Stair proposal is stale')
checks={name:inspect(stairs) for name,stairs in proposal['stairCandidates'].items()}
# Reversing the tangent changes handedness without changing the physical envelope.
# Inspect again to expose face-winding assumptions in the mesh builder.
for name,stairs in proposal['stairCandidates'].items():
    inspect({**stairs,'tangent':[-x for x in stairs['tangent']],'firstLane':-stairs['firstLane']})
report=dict(proposalSha256=hashlib.sha256(args.proposal.read_bytes()).hexdigest(),checks=checks,
            reversedTangentCasesPassed=2,productionReady=False,productionModified=False,
            scope='Actual isolated mesh geometry only; no wall openings, structural design, current site/ground or safe-use certification.')
args.report.parent.mkdir(parents=True,exist_ok=True)
args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('Both stair studies and reversed tangents passed tread, landing, clearance and guard probes')
