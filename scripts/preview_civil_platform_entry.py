"""Build a separate, estimated D-area portico candidate; never update production data."""
import argparse,copy,hashlib,json,math
from pathlib import Path
from shapely.geometry import LineString, Point
from building_overrides import ROOT,load_catalogue,resolve_building,source_catalogue


def proposal(stone_surround=True, tall_surround=True, curved_roof=True):
    path=ROOT/'public/data/buildings.json'
    original=next(b for b in json.loads(path.read_text()) if b['id']=='way/957404988')
    record=copy.deepcopy(load_catalogue()[original['id']])
    porch=next(p for p in record['parts'] if p['id']=='link-portico')
    entry=next(e for e in original['form']['entrances'] if e.get('porticoId')==porch['id'])
    a=math.radians(entry['bearing']);n=[math.sin(a),math.cos(a)];t=[n[1],-n[0]];front=entry['outerCenter']
    def point(along,setback):return [front[k]+t[k]*along-n[k]*setback for k in (0,1)]
    curved_roof=stone_surround and tall_surround and curved_roof
    depth=6 if curved_roof else 3.6
    rear_setback=4.7 if curved_roof else 2.65
    if curved_roof:
        foyer=next(p for p in record['parts'] if p['id']=='link-foyer')
        ring=foyer['polygons'][0][0]
        replacements=[]
        # Move the shared wall along its existing north/south boundary lines,
        # preserving the total footprint rather than shifting it off those lines.
        for index,neighbor in [(0,4),(1,2)]:
            old=ring[index][:];toward=ring[neighbor]
            fraction=2.4/(old[0]-toward[0])
            new=[old[k]+fraction*(toward[k]-old[k]) for k in (0,1)]
            replacements.append((old,new))
        for old,new in replacements:
            for part in (foyer,porch):
                for vertex in part['polygons'][0][0]:
                    if vertex==old:vertex[:]=new
            for vertex in foyer['roof']['mesh']['vertices']:
                if vertex[:2]==old:vertex[:2]=new
        hit=LineString([front,point(0,10)]).intersection(LineString(foyer['polygons'][0][0][:2]))
        assert hit.geom_type=='Point', 'Deeper entry must meet the shared wall once'
        depth=Point(front).distance(hit)
        record['entrances'][0]['recess']=depth
    offsets=[sum((c['center'][k]-front[k])*t[k] for k in (0,1)) for c in porch['openBelow']['columns']]
    entrance_pair={max((i for i,v in enumerate(offsets) if v<0),key=lambda i:offsets[i]),min((i for i,v in enumerate(offsets) if v>0),key=lambda i:offsets[i])}
    for i,c in enumerate(porch['openBelow']['columns']):
        along=math.copysign(5.2,offsets[i]) if i in entrance_pair else offsets[i]
        setback=.6+.8*max(0,1-(along/9)**2) if curved_roof else .7
        c['center']=point(along,setback)
    template=porch['openBelow']['columns'][0]
    for along in (-2.8,2.8):
        c=copy.deepcopy(template);c['center']=point(along,rear_setback);porch['openBelow']['columns'].append(c)
    # Start on the short depth edge, so lattice beams run across the porch.
    ring=porch['polygons'][0][0][:-1];ring=ring[1:]+ring[:1]
    porch['polygons']=[[ring+[ring[0]]]]
    porch['roof'].pop('rim',None)
    porch['openBelow']['slattedRoof']=dict(edgeWidth=1.15,slatWidth=.2,slatCount=11,solidBays=[5,6,7,8,9])
    if curved_roof:
        edge=LineString(ring[1:3]);center=edge.project(Point(front))/edge.length
        porch['openBelow']['slattedRoof']['frontCurve']={
            'from':center-9/edge.length,'to':center+9/edge.length,'inset':.8,'segments':24}
    tall_surround = stone_surround and tall_surround
    if tall_surround:
        porch['height']=8.6
        porch['openBelow']['clearHeight']=8.25
    glass_top=7.45 if tall_surround else 6.1
    beam_top=8.0 if tall_surround else 6.65
    if stone_surround:
        # Bound stone and glass rectangles on the existing shared wall. Adjacent
        # intervals share exact endpoints; no full glass plane is hidden behind stone.
        facade=next(f for f in record['exposedFacadeRules'] if f.get('region')=='under-portico')
        foyer=next(p for p in record['parts'] if p['id']==facade['part'])
        ring=foyer['polygons'][0][0];edge=facade['edge']
        wall=LineString([ring[edge],ring[edge+1]])
        def fraction(along):return wall.project(Point(point(along,depth)))/wall.length
        panels=[]
        def panel(name,kind,bounds,bottom,top,columns=1,rows=1):
            lo,hi=sorted(bounds)
            panels.append(dict(id=name,type=kind,**{'from':lo,'to':hi},bottom=bottom,top=top,
                columns=columns,rows=rows,frameWidth=.04 if kind=='solid' else .07,
                depth=.21 if kind=='solid' else .1,
                **({'finish':'stone'} if kind=='solid' else {'frameFinish':'dark'})))
        def span(name,kind,lo,hi,bottom,top,columns=1,rows=1):
            panel(name,kind,[fraction(lo),fraction(hi)],bottom,top,columns,rows)
        span('central-upper-glass','glazing',-2.425,2.425,4.25,glass_top,4,3)
        span('upper-stone-beam','solid',-5.55,5.55,glass_top,beam_top)
        for sign,label in [(-1,'north'),(1,'south')]:
            span(label+'-inner-pier','solid',sign*2.425,sign*3.175,1.16,glass_top)
            span(label+'-outer-pier','solid',sign*4.9,sign*5.55,1.16,glass_top)
            span(label+'-side-glass','glazing',sign*3.175,sign*4.9,1.16,glass_top,2,3)
            span(label+'-door-cheek','solid',sign*1.9,sign*2.425,1.16,3.85)
            span(label+'-header-extension','solid',sign*1.9,sign*2.425,3.85,4.25)
            outer=fraction(sign*5.55)
            panel(label+'-wing-glass','glazing',[outer,.03 if outer<.5 else .97],1.16,beam_top,5,3)
        facade['rule']['panels']=panels
        record['entrances'][0]['recessDoor']['lintelHeight']=.4
        if tall_surround:
            # Raising the canopy invalidates the old automatic window row.
            # Preserve an estimated clerestory above it as a separate region.
            upper=copy.deepcopy(facade);upper['region']='above-portico'
            upper['rule']['panels']=[dict(id=f'clerestory-{i}',type='glazing',
                **{'from':(i+.5)/10-.55/wall.length,'to':(i+.5)/10+.55/wall.length},
                bottom=9.1,top=10.5,columns=1,rows=1,frameWidth=.07,depth=.1)
                for i in range(10)]
            record['exposedFacadeRules'].append(upper)
    candidate=resolve_building(original,record,{s['id'] for s in source_catalogue()})
    return dict(status='unregistered-composition-candidate',buildingId=original['id'],
                scope='Actual mapped D outline, existing estimated dimensions; not a photo fit or production replacement',
                original=original,candidate=candidate,override=record,
                assumptions=['D remains the OSM-supported location hypothesis.',
                             ('Front columns follow the estimated curved edge with 0.6m clearance; pair at +/-5.2m.' if curved_roof else 'Front pair at +/-5.2m around the entry; other four longitudinal positions retained; front setback 0.7m.'),
                             f'Two rear columns at +/-2.8m along entry and {rear_setback:g}m setback are estimates, not a surveyed count.',
                             f'{depth:g}m porch depth, central five solid bays and side lattice spacing are unverified estimates.',
                             (f'Stone-framed central glass bay is estimated: inner piers +/-2.8m, outer piers +/-5.225m; upper beam {glass_top:g}–{beam_top:g}m.' if stone_surround else 'Stone-framed glazing has not been reconstructed.'),
                             ('Front roof edge uses an estimated 18m-wide parabolic recess, 0.8m inset at its center, entirely inside the original footprint; not a recovered circular radius.' if curved_roof else 'Side glazing continuation remains estimated; curved named fascia has not been reconstructed.'),
                             ('8.6m roof and 8.25m clear height form a proportional alternative, not a measured height.' if tall_surround else 'Original 7.2m estimated roof height retained.')],
                productionReady=False,photoRegistrationAccepted=False,wholeBuildingAccepted=False,
                buildingSha256=hashlib.sha256(path.read_bytes()).hexdigest())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--without-surround',action='store_true',help='Reproduce the preceding full-glass candidate')
    parser.add_argument('--low-roof',action='store_true',help='Reproduce the preceding 7.2m roof and short central glazing')
    parser.add_argument('--straight-roof',action='store_true',help='Reproduce the preceding shallow straight-edged portico')
    args=parser.parse_args();r=proposal(not args.without_surround,not args.low_roof,not args.straight_roof)
    args.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    print(r['status'])
