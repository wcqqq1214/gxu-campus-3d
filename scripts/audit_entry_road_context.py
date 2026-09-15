#!/usr/bin/env python3
"""Screen explicit entrance footprints against mapped motor-vehicle roads.

This read-only 2D preflight complements the infrastructure-mesh validator.
An overlap needs a level/placement review; it does not prove a 3D collision.
"""
import argparse
import hashlib
import json
from pathlib import Path
from shapely.geometry import Polygon
from shapely.ops import unary_union

ROOT=Path(__file__).resolve().parents[1]
VEHICLE_ROADS={'motorway','trunk','primary','secondary','tertiary','unclassified','residential','living_street','service','track'}
FOOTPRINT_CONFIGS=('attachedPortico','stairFlight','recessedStairEntry')


def conflicts_for_entry(building_id,entry,surfaces):
    shapes=[Polygon(entry[k]['footprint']) for k in FOOTPRINT_CONFIGS if k in entry and 'footprint' in entry[k]]
    if not shapes:return []
    if any(not p.is_valid or p.area<=0 for p in shapes):raise ValueError('Invalid entrance footprint')
    footprint=unary_union(shapes);result=[]
    for s in surfaces:
        if s.get('kind')!='roads' or s.get('tags',{}).get('highway') not in VEHICLE_ROADS:continue
        vs=s['vertices'];indices=s['triangles']
        if len(indices)%3:raise ValueError('Incomplete road triangle')
        road=unary_union([Polygon([vs[k][:2] for k in indices[i:i+3]]) for i in range(0,len(indices),3)])
        overlap=footprint.intersection(road)
        if overlap.area<=1e-5:continue
        result.append(dict(buildingId=building_id,entranceId=entry['id'],roadId=s['id'],roadTags=s.get('tags',{}),overlapAreaSquareMeters=overlap.area,overlapBounds=list(overlap.bounds),status='needs-placement-and-level-review'))
    return sorted(result,key=lambda r:r['roadId'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proposal',type=Path,help='JSON with buildingId and proposalEntry; entry must include a resolved footprint')
    parser.add_argument('--building-id',help='Limit current snapshot audit to one stable building ID')
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    read=lambda p:json.loads(p.read_text())
    surfaces=read(ROOT/'public/data/surfaces.json');bs=read(ROOT/'public/data/buildings.json')
    if args.proposal:
        proposal=read(args.proposal)
        if proposal['buildingId'] not in {b['id'] for b in bs}:raise ValueError('Unknown proposal building')
        entries=[(proposal['buildingId'],proposal['proposalEntry'])]
        if not any('footprint' in entries[0][1].get(k,{}) for k in FOOTPRINT_CONFIGS):raise ValueError('Proposal requires an explicit resolved footprint')
    else:
        if args.building_id and args.building_id not in {b['id'] for b in bs}:raise ValueError('Unknown building ID')
        entries=[(b['id'],e) for b in bs if not args.building_id or b['id']==args.building_id for e in b.get('form',{}).get('entrances',[]) if any('footprint' in e.get(k,{}) for k in FOOTPRINT_CONFIGS)]
    conflicts=[r for ident,e in entries for r in conflicts_for_entry(ident,e,surfaces)]
    files=[ROOT/'public/data/buildings.json',ROOT/'public/data/surfaces.json']+([args.proposal] if args.proposal else [])
    report=dict(status='needs-review' if conflicts else 'no-plan-overlap-in-tested-footprints',mode='proposal' if args.proposal else 'current-snapshot',testedEntries=len(entries),testedEntryIds=[{'buildingId':ident,'entranceId':e['id']} for ident,e in entries],conflicts=conflicts,limitations=['Only explicit attached-portico/stair footprints and mapped motor-vehicle surface roads are tested.','No overlap is not whole-entrance acceptance; terrain, pedestrian paths, level separation, crown clearance and actual geometry require separate checks.','A bridge/tunnel/layer tag is retained for review, never silently excluded.'],fingerprints={str(p.relative_to(ROOT) if p.is_absolute() and p.is_relative_to(ROOT) else p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 1 if conflicts else 0

if __name__=='__main__':raise SystemExit(main())
