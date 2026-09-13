"""A calibrated stair flight joined forward to one mapped at-grade surface."""
import copy,hashlib,json,math
from shapely.geometry import Polygon
from building_overrides import footprint_revision
from surroundings_data import surface_shape,triangulate

def derive_front_connection(config,buildings,surface,source_ids):
    from site_data import local_shape,world_shape,road_columns
    keys={'id','type','buildingId','footprintRevision','entranceId','surfaceId','surfaceRevision',
          'roadSearchDistance','meshStep','groundClearance','joinOverlap','roadContactDepth','roadContactSideMargin','sourceRefs','evidence'}
    if set(config)!=keys or config['type']!='front-connection':raise ValueError('Invalid front connection fields')
    b=next((b for b in buildings if b['id']==config['buildingId']),None)
    if not b or footprint_revision(b)!=config['footprintRevision']:raise ValueError('Stale front connection building')
    entry=next((e for e in b.get('form',{}).get('entrances',[]) if e['id']==config['entranceId']),None)
    if not entry or 'stairFlight' not in entry:raise ValueError('Front connection requires explicit stairs')
    if surface is None or surface['id']!=config['surfaceId'] or hashlib.sha256(json.dumps(surface,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=config['surfaceRevision']:
        raise ValueError('Stale front connection surface')
    tags=surface['tags']
    if surface['kind']!='roads' or tags.get('highway') not in ('footway','path','pedestrian','service') or tags.get('bridge') or tags.get('tunnel') or str(tags.get('layer','0'))!='0':
        raise ValueError('Front connection requires an at-grade pedestrian or service surface')
    if not config['sourceRefs'] or not set(config['sourceRefs'])<=source_ids:raise ValueError('Unknown connection source')
    if not isinstance(config['evidence'],dict) or not config['evidence'] or not all(isinstance(v,str) and v.strip() for v in config['evidence'].values()):raise ValueError('Missing connection evidence')
    for key,(lo,hi) in {'meshStep':(.5,2),'groundClearance':(.04,.2),'joinOverlap':(.05,.3),'roadContactDepth':(.5,2),'roadContactSideMargin':(.1,1)}.items():
        if type(config[key]) not in (int,float) or not math.isfinite(config[key]) or not lo<=config[key]<=hi:raise ValueError('Invalid connection '+key)
    search=config['roadSearchDistance']
    if not isinstance(search,list) or len(search)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in search) or not 0<search[0]<search[1]<=80:raise ValueError('Invalid front road search')
    p=entry['stairFlight'];frame={'origin':entry['center'],'angle':-math.radians(entry['bearing'])}
    start=p['front'];half=p['width']/2;target=local_shape(surface_shape(surface),frame)
    columns=road_columns(target,-half,half,start,search,config['meshStep'])
    shape=Polygon([(-half,start),(half,start),*reversed(columns)]);area=world_shape(shape,frame)
    if not shape.is_valid or not 5<shape.area<500 or shape.intersection(target).area>1e-5:raise ValueError('Invalid front connection footprint')
    for other in buildings:
        if any(area.intersection(Polygon(poly[0],poly[1:])).area>1e-5 for poly in other['polygons']):raise ValueError('Connection crosses a building')
        for e in other.get('form',{}).get('entrances',[]):
            for kind in ['attachedPortico','stairFlight']:
                if kind in e and area.intersection(Polygon(e[kind]['footprint'])).area>1e-5:raise ValueError('Connection overlaps an entrance platform')
    return {**copy.deepcopy(config),**frame,'buildingCenter':b['center'],'entry':copy.deepcopy(entry),
            'startY':start,'stairBaseHeight':p['baseHeight'],'columns':columns,'localPolygon':list(shape.exterior.coords),
            'pavingPolygon':list(area.exterior.coords),'gradingBounds':list(area.bounds),'localMesh':triangulate(shape),
            'layer':'roads','material':'asphalt'},area,area
