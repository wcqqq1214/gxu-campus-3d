"""A photo-supported entrance landing connected sideways to a mapped footway."""
import copy,hashlib,json,math
from shapely.geometry import Polygon,LineString,box
from shapely.ops import unary_union
from building_overrides import footprint_revision
from surroundings_data import surface_shape,triangulate

def derive_side_connection(config,buildings,surface,source_ids):
    from site_data import local_shape,world_shape
    required={'id','type','buildingId','footprintRevision','entranceId','surfaceId','surfaceRevision',
        'leadDistance','pathWidth','roadSearchDistance','meshStep','groundClearance',
        'joinOverlap','roadContactDepth','roadContactSideMargin','sourceRefs','evidence'}
    if set(config)!=required or config['type']!='side-connection':raise ValueError('Invalid side connection fields')
    b=next((b for b in buildings if b['id']==config['buildingId']),None)
    if not b or footprint_revision(b)!=config['footprintRevision']:raise ValueError('Stale connection building')
    entry=next((e for e in b.get('form',{}).get('entrances',[]) if e['id']==config['entranceId']),None)
    if not entry or 'attachedPortico' not in entry:raise ValueError('Connection needs an attached-portico entrance')
    if surface is None or surface['id']!=config['surfaceId'] or hashlib.sha256(json.dumps(surface,separators=(',',':'),sort_keys=True).encode()).hexdigest()!=config['surfaceRevision']:
        raise ValueError('Stale connection footway')
    if surface['kind']!='roads' or surface['tags'].get('highway') not in ('footway','path','pedestrian') or surface['tags'].get('bridge') or surface['tags'].get('tunnel') or str(surface['tags'].get('layer','0'))!='0':
        raise ValueError('Connection target must be an at-grade footway')
    if not config['sourceRefs'] or not set(config['sourceRefs'])<=source_ids:raise ValueError('Unknown connection source')
    if not isinstance(config['evidence'],dict) or not config['evidence'] or not all(isinstance(v,str) and v.strip() for v in config['evidence'].values()):raise ValueError('Missing connection evidence')
    for k,(lo,hi) in {'leadDistance':(.5,8),'pathWidth':(1.5,8),'meshStep':(.5,2),'groundClearance':(.04,.2),'joinOverlap':(.05,.3),'roadContactDepth':(.5,2),'roadContactSideMargin':(.1,1)}.items():
        if type(config[k]) not in (int,float) or not math.isfinite(config[k]) or not lo<=config[k]<=hi:raise ValueError('Invalid connection '+k)
    search=config['roadSearchDistance']
    if not isinstance(search,list) or len(search)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in search) or not 0<search[0]<search[1]<=80:raise ValueError('Invalid side road search')
    p=entry['attachedPortico'];frame={'origin':entry['center'],'angle':-math.radians(entry['bearing'])}
    start=p['depth']+p['steps']*p['tread'];half=p['width']/2
    y0=start+config['leadDistance']-config['pathWidth']/2;y1=y0+config['pathWidth']
    if y0<=start:raise ValueError('Side connection must leave room in front of the stairs')
    target=local_shape(surface_shape(surface),frame);stations={y0,y1}
    for poly in ([target] if target.geom_type=='Polygon' else target.geoms):
        for ring in [poly.exterior,*poly.interiors]:stations.update(y for x,y in ring.coords if y0<y<y1)
    breaks=sorted(stations);ys=[]
    for a,c in zip(breaks,breaks[1:]):
        n=max(1,math.ceil((c-a)/config['meshStep']));ys.extend(a+(c-a)*i/n for i in range(n))
    ys.append(y1);columns=[]
    for y in ys:
        hit=target.intersection(LineString([(-half,y),(-search[1],y)]))
        if hit.is_empty or not search[0]<=-hit.bounds[2]<=search[1]:raise ValueError('Missing footway across connection width')
        columns.append([hit.bounds[2],y])
    outline=[(-half,start),(half,start),(half,y1),*reversed(columns),(-half,y0)]
    shape=Polygon(outline);area=world_shape(shape,frame)
    if not shape.is_valid or not 5<shape.area<500 or shape.intersection(target).area>1e-5:raise ValueError('Invalid connection paving footprint')
    for other in buildings:
        for poly in other['polygons']:
            if area.intersection(Polygon(poly[0],poly[1:])).area>1e-5:raise ValueError('Connection crosses a building')
        for e in other.get('form',{}).get('entrances',[]):
            for kind in ('attachedPortico','stairFlight'):
                if kind in e and area.intersection(Polygon(e[kind]['footprint'])).area>1e-5:raise ValueError('Connection overlaps an entrance platform')
    return {**copy.deepcopy(config),**frame,'buildingCenter':b['center'],'entry':copy.deepcopy(entry),
        'startY':start,'stairBaseHeight':p['stepBaseHeight'],'columns':columns,'localPolygon':list(shape.exterior.coords),
        'pavingPolygon':list(area.exterior.coords),'gradingBounds':list(area.bounds),'localMesh':triangulate(shape),
        'layer':'roads','material':'asphalt'},area,area
