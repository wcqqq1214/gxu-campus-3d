"""Add two unapproved stair positions to the resolved environment roof study."""
import argparse
import hashlib
import json
from pathlib import Path
from switchback_stairs_data import resolve_switchback_stairs, validate_stair_study_neighbors

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--roof-proposal',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    proposal=json.loads(args.roof_proposal.read_text())
    path=ROOT/'public/data/buildings.json'
    if proposal['sourceSha256'] != hashlib.sha256(path.read_bytes()).hexdigest():
        raise ValueError('Roof proposal is stale')
    if not proposal.get('roofDetails') or proposal['buildingId'] != 'way/759170251':
        raise ValueError('Stair study needs the seven-storey environment roof proposal')
    buildings=json.loads(path.read_text()); proposal['stairCandidates']={}
    for name,b in proposal['variants'].items():
        config=dict(polygon=0,ring=0,edge=2 if name=='north' else 0,t=.80,
                    flightWidth=1.4,gap=.2,landingDepth=.95,tread=.28,risers=10,
                    levels=[round(i*3.3,2) for i in range(8)],slabThickness=.3,
                    railHeight=1.1,railThickness=.15,firstLane=1)
        stairs=resolve_switchback_stairs(b,config)
        validate_stair_study_neighbors(b['id'],stairs,buildings)
        proposal['stairCandidates'][name]=stairs
    proposal['roofProposalSha256']=hashlib.sha256(args.roof_proposal.read_bytes()).hexdigest()
    proposal['assumptions'] += [
        'Photo-right end stairs: west end in north hypothesis; east end in south hypothesis',
        '0.80 short-edge anchor, 1.4 m flight, 0.95 m landings, 10 risers per half-flight and 0.28 m treads are estimates',
        'Seven storey intervals reach the estimated roof; ground level and final roof access remain unverified',
        'Solid parapets follow the photo; doors, window conflicts, ground and site connections are not resolved',
        'Background building in library scenery is unidentified and is not accepted as orientation evidence']
    proposal['nextGate']='Locate the photographed end and long facade; then resolve wall openings, roof access and ground interfaces before production integration.'
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(proposal,ensure_ascii=False,indent=2)+'\n')
    print('Both isolated end-stair hypotheses resolved; no neighbor footprint overlap')


if __name__=='__main__':main()
