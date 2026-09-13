"""Sourced avenue arrangements with estimated dimensions and stable stations."""
import hashlib,json,math
from pathlib import Path
from shapely.geometry import Point,shape
from shapely.ops import transform,substring,unary_union
from building_overrides import read_json,source_catalogue


def revision(coordinates):
    return hashlib.sha256(json.dumps(coordinates,separators=(',',':')).encode()).hexdigest()


def derive_avenues(root):
    from prepare_geodata import project
    config=read_json(root/'data/vegetation-avenues.json')
    if set(config)!={'schemaVersion','avenues'} or type(config['schemaVersion']) is not int or config['schemaVersion']!=1 or not isinstance(config['avenues'],list):
        raise ValueError('Invalid avenue catalogue')
    geo=read_json(root/'public/data/geography.geojson');features={f['id']:f for f in geo['features']}
    sources={s['id'] for s in source_catalogue(root)}
    campus=transform(project,shape(features['campus']['geometry']))
    roads=[(f['id'],transform(project,shape(f['geometry']))) for f in geo['features']
           if f['properties'].get('kind')=='roads' and f['geometry']['type']=='LineString']
    result=[];ids=set()
    fields={'id','roadId','roadRevision','startMeters','endMeters','spacingMeters','offsetMeters',
            'heightMeters','template','junctionClearanceMeters','replacementHalfWidthMeters','sourceRefs','evidence'}
    for item in config['avenues']:
        if set(item)!=fields or not isinstance(item['id'],str) or not item['id'] or item['id'] in ids:
            raise ValueError('Unknown avenue field or duplicate/missing ID')
        ids.add(item['id']);feature=features.get(item['roadId'])
        if not feature or feature['properties'].get('kind')!='roads' or feature['geometry']['type']!='LineString':
            raise ValueError('Avenue requires a mapped road axis')
        if revision(feature['geometry']['coordinates'])!=item['roadRevision']:
            raise ValueError('Stale avenue road revision')
        tags=feature['properties'].get('tags',{})
        if tags.get('bridge') not in (None,'no') or tags.get('tunnel') not in (None,'no') or str(tags.get('layer','0'))!='0':
            raise ValueError('Avenue axis must be at grade')
        if not isinstance(item['sourceRefs'],list) or not item['sourceRefs'] or not all(isinstance(s,str) and s in sources for s in item['sourceRefs']):
            raise ValueError('Unknown avenue source')
        if not isinstance(item['evidence'],dict) or set(item['evidence'])!={'location','layout','dimensions','species'} or not all(isinstance(s,str) and s.strip() for s in item['evidence'].values()):
            raise ValueError('Avenue requires field-specific evidence')
        limits={'spacingMeters':(6,30),'offsetMeters':(2,20),'heightMeters':(4,25),
                'junctionClearanceMeters':(3,20),'replacementHalfWidthMeters':(3,30)}
        for name,(low,high) in limits.items():
            value=item[name]
            if type(value) not in (int,float) or not math.isfinite(value) or not low<=value<=high:
                raise ValueError('Invalid avenue '+name)
        if type(item['template']) is not int or item['template'] not in (0,1,2):raise ValueError('Invalid avenue template')
        line=transform(project,shape(feature['geometry']))
        a,b=item['startMeters'],item['endMeters']
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in [a,b]) or not 0<=a<b<=line.length:
            raise ValueError('Invalid avenue station interval')
        if item['replacementHalfWidthMeters']<=item['offsetMeters']+.2:raise ValueError('Avenue replacement must include its rows')
        segment=substring(line,a,b)
        replacement=segment.buffer(item['replacementHalfWidthMeters'],cap_style=2,join_style=2).intersection(campus)
        if any(replacement.intersection(other['replacement']).area>1e-6 for other in result):
            raise ValueError('Overlapping avenue replacement areas require an explicit layout decision')
        junctions=[]
        for ident,other in roads:
            if ident==item['roadId']:continue
            hit=line.intersection(other)
            if hit.geom_type=='Point':junctions.append(hit)
            elif hit.geom_type=='MultiPoint':junctions.extend(hit.geoms)
            elif not hit.is_empty:raise ValueError('Overlapping road axes require avenue review')
            for endpoint in [Point(other.coords[0]),Point(other.coords[-1])]:
                if line.distance(endpoint)<.5:junctions.append(line.interpolate(line.project(endpoint)))
        quiet=unary_union(junctions).buffer(item['junctionClearanceMeters'])
        candidates=[];rejected=[]
        for station_index in range(math.ceil(a/item['spacingMeters']),math.floor(b/item['spacingMeters'])+1):
            station=station_index*item['spacingMeters'];p=line.interpolate(station)
            before=line.interpolate(max(0,station-.25));after=line.interpolate(min(line.length,station+.25))
            dx,dy=after.x-before.x,after.y-before.y;length=math.hypot(dx,dy)
            for side in [-1,1]:
                row=[round(p.x-side*dy/length*item['offsetMeters'],1),round(p.y+side*dx/length*item['offsetMeters'],1),item['heightMeters'],item['template']]
                point=Point(row[:2]);record={'stationIndex':station_index,'side':side,'tree':row}
                # Junction openings are measured at the centreline station; offset
                # rows must not evade them by sitting laterally outside the disk.
                if quiet.covers(p) or not replacement.covers(point):rejected.append(record)
                else:candidates.append(record)
        result.append({'config':item,'replacement':replacement,'candidates':candidates,'junctionRejected':rejected})
    return result


def apply_avenues(trees,derived):
    """Replace only selected road bands; exact surviving rows keep grounded Z."""
    existing={tuple(t[:4]):t for t in trees}
    if len(existing)!=len(trees):raise ValueError('Duplicate tree rows before avenue preparation')
    masks=[a['replacement'] for a in derived]
    kept=[t for t in trees if not any(g.covers(Point(t[:2])) for g in masks)]
    records=[]
    for avenue in derived:
        candidates=[]
        for item in avenue['candidates']:
            row=item['tree'];value=existing.get(tuple(row),row)
            kept.append(value);candidates.append(value)
        records.append({'id':avenue['config']['id'],'parameters':avenue['config'],
                        'candidates':candidates,'junctionRejected':avenue['junctionRejected'],
                        'replacedPriorRows':sum(avenue['replacement'].covers(Point(t[:2])) for t in trees)})
    if len({tuple(t[:2]) for t in kept})!=len(kept):raise ValueError('Avenue creates duplicate positions')
    return kept,records
