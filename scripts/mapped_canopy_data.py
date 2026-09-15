"""Attach a sourced doorway to a separately mapped, already modelled canopy."""
import copy,hashlib,json,math


def validate_mapped_canopy(config):
    keys={'buildingId','footprintRevision','partId','bays','pierWidth','doorHeight','transomHeight'}
    if not isinstance(config,dict) or set(config)!=keys:raise ValueError('Invalid mapped canopy fields')
    if not all(isinstance(config[k],str) and config[k] for k in ('buildingId','footprintRevision','partId')):
        raise ValueError('Mapped canopy needs stable building/part identifiers and footprint revision')
    if type(config['bays']) is not int or not 1<=config['bays']<=5:raise ValueError('Invalid sheltered door bay count')
    for k,lo,hi in [('pierWidth',.25,1.2),('doorHeight',2,3.2),('transomHeight',.2,1)]:
        v=config[k]
        if type(v) not in (int,float) or not math.isfinite(v) or not lo<=v<=hi:raise ValueError('Invalid sheltered door '+k)


def resolve_mapped_canopy_context(buildings,check_only=False):
    from shapely.geometry import Polygon,LineString,box
    from shapely.affinity import rotate,translate
    from shapely.ops import unary_union
    from building_overrides import footprint_revision
    by_id={b['id']:b for b in buildings}
    for b in buildings:
        for e in b.get('form',{}).get('entrances',[]):
            if 'mappedCanopy' not in e:continue
            c=e['mappedCanopy'];validate_mapped_canopy(c);roof=by_id.get(c['buildingId'])
            if not roof or roof['id']==b['id'] or roof['tags'].get('building')!='roof' or footprint_revision(roof)!=c['footprintRevision']:
                raise ValueError('Missing or stale mapped canopy building')
            part=next((p for p in roof['form']['parts'] if p['id']==c['partId']),None)
            if not part or 'openBelow' not in part:raise ValueError('Mapped canopy requires an explicit open part')
            opening=part['openBelow'];floor=opening['floorHeight']
            if floor+c['doorHeight']+c['transomHeight']+.12>opening['clearHeight']:
                raise ValueError('Door/transom exceeds canopy soffit')
            if e['width']/c['bays']-c['pierWidth']<1.2:raise ValueError('Sheltered doorway bays are too narrow')
            shape=unary_union([Polygon(p[0],p[1:]) for p in part['polygons']])
            angle=math.radians(e['bearing']);n=[math.sin(angle),math.cos(angle)];t=[n[1],-n[0]]
            width=e['width']+c['pierWidth'];center=e['center']
            wall=LineString([[center[i]+t[i]*v for i in (0,1)] for v in [-width/2,width/2]])
            if not shape.buffer(.01).covers(wall):raise ValueError('Doorway is not behind the mapped canopy')
            columns=[translate(rotate(box(-p['width']/2,-p['depth']/2,p['width']/2,p['depth']/2),p['angle'],use_radians=True),*p['center']) for p in opening['columns']]
            passages=[]
            for k in range(c['bays']):
                offset=-e['width']/2+(k+.5)*e['width']/c['bays']
                start=[center[i]+t[i]*offset+n[i]*.01 for i in (0,1)]
                line=LineString([start,[start[i]+n[i]*40 for i in (0,1)]])
                path=line.intersection(shape)
                if path.geom_type!='LineString' or path.length<1 or any(path.buffer(.45).intersection(col).area>1e-5 for col in columns):
                    raise ValueError('Mapped canopy columns obstruct a doorway passage')
                passages.append([list(path.coords[0]),list(path.coords[-1])])
            shelter={**copy.deepcopy(c),'floorHeight':floor,'clearHeight':opening['clearHeight'],
                     'canopyCenter':roof['center'],'canopyPolygons':part['polygons'],'passages':passages,
                     'contextRevision':context_revision(e,roof,part),
                     'partRevision':hashlib.sha256(json.dumps(part,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
            if check_only:
                if e.get('shelter')!=shelter:raise ValueError('Resolved mapped canopy is stale; prepare the data')
            else:e['shelter']=shelter


def context_revision(entry,roof,part):
    payload=[{k:v for k,v in entry.items() if k!='shelter'},roof['center'],roof['polygons'],part]
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def check_prepared_mapped_canopies(buildings):
    """Dependency-free source guard for Blender; spatial checks run in preparation."""
    by_id={b['id']:b for b in buildings}
    for b in buildings:
        for e in b.get('form',{}).get('entrances',[]):
            if 'mappedCanopy' not in e:continue
            c=e['mappedCanopy'];validate_mapped_canopy(c)
            roof=by_id.get(c['buildingId']);s=e.get('shelter',{})
            part=next((p for p in (roof or {}).get('form',{}).get('parts',[]) if p['id']==c['partId']),None)
            if not roof or not part or s.get('contextRevision')!=context_revision(e,roof,part):
                raise ValueError('Mapped canopy context is stale; prepare the data')
            if any(s.get(k)!=v for k,v in c.items()) or s.get('canopyCenter')!=roof['center'] or s.get('canopyPolygons')!=part['polygons'] or any(s.get(k)!=part['openBelow'][k] for k in ['floorHeight','clearHeight']):
                raise ValueError('Mapped canopy derived geometry is stale; prepare the data')
