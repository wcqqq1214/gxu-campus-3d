"""Build a separate, estimated D-area portico candidate; never update production data."""
import argparse,copy,hashlib,json,math
from pathlib import Path
from building_overrides import ROOT,load_catalogue,resolve_building,source_catalogue


def proposal():
    path=ROOT/'public/data/buildings.json'
    original=next(b for b in json.loads(path.read_text()) if b['id']=='way/957404988')
    record=copy.deepcopy(load_catalogue()[original['id']])
    porch=next(p for p in record['parts'] if p['id']=='link-portico')
    entry=next(e for e in original['form']['entrances'] if e.get('porticoId')==porch['id'])
    a=math.radians(entry['bearing']);n=[math.sin(a),math.cos(a)];t=[n[1],-n[0]];front=entry['outerCenter']
    def point(along,setback):return [front[k]+t[k]*along-n[k]*setback for k in (0,1)]
    offsets=[sum((c['center'][k]-front[k])*t[k] for k in (0,1)) for c in porch['openBelow']['columns']]
    entrance_pair={max((i for i,v in enumerate(offsets) if v<0),key=lambda i:offsets[i]),min((i for i,v in enumerate(offsets) if v>0),key=lambda i:offsets[i])}
    for i,c in enumerate(porch['openBelow']['columns']):
        along=math.copysign(5.2,offsets[i]) if i in entrance_pair else offsets[i]
        c['center']=point(along,.7)
    template=porch['openBelow']['columns'][0]
    for along in (-2.8,2.8):
        c=copy.deepcopy(template);c['center']=point(along,2.65);porch['openBelow']['columns'].append(c)
    # Start on the short depth edge, so lattice beams run across the porch.
    ring=porch['polygons'][0][0][:-1];ring=ring[1:]+ring[:1]
    porch['polygons']=[[ring+[ring[0]]]]
    porch['roof'].pop('rim',None)
    porch['openBelow']['slattedRoof']=dict(edgeWidth=1.15,slatWidth=.2,slatCount=11,solidBays=[5,6,7,8,9])
    candidate=resolve_building(original,record,{s['id'] for s in source_catalogue()})
    return dict(status='unregistered-composition-candidate',buildingId=original['id'],
                scope='Actual mapped D outline, existing estimated dimensions; not a photo fit or production replacement',
                original=original,candidate=candidate,override=record,
                assumptions=['D remains the OSM-supported location hypothesis.',
                             'Front pair at +/-5.2m around the entry; other four longitudinal positions retained; front setback 0.7m.',
                             'Two rear columns at +/-2.8m along entry and 2.65m setback are estimates, not a surveyed count.',
                             '3.6m porch depth, central five solid bays and side lattice spacing are unverified estimates.',
                             'Curved named fascia and stone-framed glazing have not been reconstructed.'],
                productionReady=False,photoRegistrationAccepted=False,wholeBuildingAccepted=False,
                buildingSha256=hashlib.sha256(path.read_bytes()).hexdigest())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();r=proposal()
    args.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    print(r['status'])
