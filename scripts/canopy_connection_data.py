"""A bounded connection from a mapped canopy's front edge to prepared campus road."""
import copy,math
from shapely.geometry import Polygon,LineString,box
from shapely.ops import unary_union
from building_overrides import footprint_revision
from surroundings_data import triangulate


def derive_canopy_connection(config,buildings,roads,source_ids):
    from site_data import local_shape,world_shape,road_columns
    keys={'id','type','buildingId','footprintRevision','entranceId','canopyEdge','roadId','roadSearchDistance','meshStep','groundClearance','joinOverlap','roadContactDepth','roadContactSideMargin','sourceRefs','evidence'}
    if set(config)!=keys or config['type']!='canopy-connection':raise ValueError('Invalid canopy connection fields')
    b=next((b for b in buildings if b['id']==config['buildingId']),None)
    if not b or footprint_revision(b)!=config['footprintRevision']:raise ValueError('Stale canopy connection building')
    entry=next((e for e in b['form']['entrances'] if e['id']==config['entranceId']),None)
    if not entry or 'shelter' not in entry:raise ValueError('Canopy connection requires resolved sheltered entry')
    if not config['sourceRefs'] or not set(config['sourceRefs'])<=source_ids:raise ValueError('Unknown canopy connection source')
    if not isinstance(config['evidence'],dict) or not config['evidence'] or not all(isinstance(v,str) and v.strip() for v in config['evidence'].values()):raise ValueError('Missing canopy connection evidence')
    if not any(r['id']==config['roadId'] for r in roads['sources']):raise ValueError('Unknown prepared campus road')
    for k,lo,hi in [('meshStep',.5,2),('groundClearance',.04,.2),('joinOverlap',.05,.3),('roadContactDepth',.5,2),('roadContactSideMargin',.1,1)]:
        v=config[k]
        if type(v) not in (int,float) or not math.isfinite(v) or not lo<=v<=hi:raise ValueError('Invalid canopy connection '+k)
    search=config['roadSearchDistance']
    if not isinstance(search,list) or len(search)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in search) or not 0<search[0]<search[1]<=30:raise ValueError('Invalid canopy road search')
    p=entry['shelter'];polys=p['canopyPolygons']
    if len(polys)!=1 or len(polys[0])!=1:raise ValueError('Canopy connection needs one simple mapped canopy')
    ring=polys[0][0];edge=config['canopyEdge']
    if type(edge) is not int or not 0<=edge<len(ring)-1:raise ValueError('Invalid canopy edge')
    frame={'origin':entry['center'],'angle':-math.radians(entry['bearing'])}
    a,c=sorted(list(local_shape(LineString(ring[edge:edge+2]),frame).coords))
    if min(a[1],c[1])<=1 or abs(c[1]-a[1])>.05 or c[0]-a[0]<entry['width'] or abs(a[0]+c[0])>.02:
        raise ValueError('Canopy edge is not centered in front of the entry')
    region=world_shape(box(a[0]-1,min(a[1],c[1]),c[0]+1,max(a[1],c[1])+search[1]+1),frame)
    triangles=[]
    for layer in roads['layers']:
        vs,ts=layer['vertices'],layer['triangles']
        for i in range(0,len(ts),3):
            tri=Polygon([vs[k] for k in ts[i:i+3]])
            if tri.intersects(region):triangles.append(tri)
    paving=local_shape(unary_union(triangles),frame)
    columns=road_columns(paving,a[0],c[0],max(a[1],c[1]),search,config['meshStep'])
    shape=Polygon([a,c,*reversed(columns)]);area=world_shape(shape,frame)
    if not shape.is_valid or not 5<shape.area<300 or shape.intersection(paving).area>1e-5:raise ValueError('Invalid canopy connection footprint')
    for other in buildings:
        if any(area.intersection(Polygon(poly[0],poly[1:])).area>1e-5 for poly in other['polygons']):raise ValueError('Canopy connection crosses a mapped building')
        for e in other.get('form',{}).get('entrances',[]):
            for kind in ('attachedPortico','stairFlight'):
                if kind in e and area.intersection(Polygon(e[kind]['footprint'])).area>1e-5:raise ValueError('Canopy connection crosses another entry')
    return {**copy.deepcopy(config),**frame,'entry':copy.deepcopy(entry),'buildingCenter':p['canopyCenter'],
            'stairBaseHeight':p['floorHeight'],'startY':min(a[1],c[1]),'startColumns':[a,c],'halfWidth':(c[0]-a[0])/2,
            'columns':columns,'localPolygon':list(shape.exterior.coords),'pavingPolygon':list(area.exterior.coords),
            'gradingBounds':list(area.bounds),'localMesh':triangulate(shape),'layer':'roads','material':'asphalt'},area,area
