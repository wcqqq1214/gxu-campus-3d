"""A calibrated threshold or stair toe joined to one mapped at-grade surface."""
import copy,hashlib,json,math
from shapely.geometry import Polygon
from building_overrides import footprint_revision
from surroundings_data import surface_shape,triangulate

def derive_front_connection(config,buildings,surface,source_ids):
    from site_data import local_shape,world_shape,road_columns
    terrace=config.get('type')=='terraced-stair-connection'
    keys={'id','type','buildingId','footprintRevision','surfaceId','surfaceRevision',
          'roadSearchDistance','meshStep','groundClearance','joinOverlap','roadContactDepth','roadContactSideMargin','sourceRefs','evidence'}
    if not terrace:keys.add('entranceId')
    optional=set() if terrace else {'pathWidth'}
    if not keys <= set(config) or set(config)-keys-optional or config['type'] not in ('front-connection','terraced-stair-connection'):raise ValueError('Invalid front connection fields')
    b=next((b for b in buildings if b['id']==config['buildingId']),None)
    if not b or footprint_revision(b)!=config['footprintRevision']:raise ValueError('Stale front connection building')
    if terrace:
        p=b.get('form',{}).get('terracedStairs')
        if not p:raise ValueError('Terraced stair connection requires resolved terraced stairs')
        # A stair toe is an exterior circulation anchor, not a new entrance.
        entry={'terracedStairs':copy.deepcopy(p)}
        frame={'origin':p['center'],'angle':math.atan2(p['tangent'][1],p['tangent'][0])}
    else:
        entry=next((e for e in b.get('form',{}).get('entrances',[]) if e['id']==config['entranceId']),None)
        if not entry or not any(k in entry for k in ('stairFlight','flushEntrance')):raise ValueError('Front connection requires explicit stairs or a flush entrance')
        frame={'origin':entry['center'],'angle':-math.radians(entry['bearing'])}
    if 'flushEntrance' in entry:
        width=config.get('pathWidth')
        portal=entry['flushEntrance'];clear=entry['width']/portal['bays']-portal['pierWidth']
        if type(width) not in (int,float) or not math.isfinite(width) or not portal['doorWidth']+.2 <= width <= clear-.1:
            raise ValueError('Flush entrance path width must contain its door and clear its piers')
        p={'width':width,'front':0,'baseHeight':entry['flushEntrance']['floorHeight']}
    elif not terrace:
        if 'pathWidth' in config:raise ValueError('Stair connection width must match its stairs')
        p=entry['stairFlight']
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
    start=p['front'];half=p['width']/2;target=local_shape(surface_shape(surface),frame)
    columns=road_columns(target,-half,half,start,search,config['meshStep'])
    shape=Polygon([(-half,start),(half,start),*reversed(columns)]);area=world_shape(shape,frame)
    if not shape.is_valid or not 5<shape.area<500 or shape.intersection(target).area>1e-5:raise ValueError('Invalid front connection footprint')
    for other in buildings:
        if any(area.intersection(Polygon(poly[0],poly[1:])).area>1e-5 for poly in other['polygons']):raise ValueError('Connection crosses a building')
        stairs=other.get('form',{}).get('terracedStairs')
        if stairs and area.intersection(Polygon(stairs['footprint'])).area>1e-5:raise ValueError('Connection overlaps terraced stairs')
        for facade in other.get('form',{}).get('facades',[]):
            if 'attachedGallery' in facade and area.intersection(Polygon(facade['attachedGallery']['footprint'])).area>1e-5:raise ValueError('Connection overlaps an attached gallery')
        for e in other.get('form',{}).get('entrances',[]):
            for kind in ['attachedPortico','stairFlight']:
                if kind in e and area.intersection(Polygon(e[kind]['footprint'])).area>1e-5:raise ValueError('Connection overlaps an entrance platform')
    return {**copy.deepcopy(config),**frame,'buildingCenter':b['center'],'entry':copy.deepcopy(entry),
            **({'halfWidth':half} if terrace or 'flushEntrance' in entry else {}),
            'startY':start,'stairBaseHeight':p['baseHeight'],'columns':columns,'localPolygon':list(shape.exterior.coords),
            'pavingPolygon':list(area.exterior.coords),'gradingBounds':list(area.bounds),'localMesh':triangulate(shape),
            'layer':'roads','material':'path' if terrace or 'flushEntrance' in entry else 'asphalt'},area,area
