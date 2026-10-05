"""Mapped north-campus underpass, preserving the existing arterial alignment."""
import gzip,json,math
from shapely.geometry import LineString,Point
from shapely.ops import unary_union
from surroundings_data import surface_shape,tiled_triangles

def prepare_underpass(root,elevation):
    raw=json.loads(gzip.decompress((root/'data/snapshots/osm-2026-09-09.json.gz').read_bytes()))
    ways={e['id']:e for e in raw['elements'] if e['type']=='way'}
    lon,lat=json.loads((root/'data/region.json').read_text())['center']
    def points(ident):
        return [[(p['lon']-lon)*111320*math.cos(math.radians(lat)),(p['lat']-lat)*111320] for p in ways[ident]['geometry']]
    south=points(839763084);tunnel=points(839763085);north=points(839763086)
    axis=LineString([south[0],*tunnel,north[1]])
    surfaces=json.loads((root/'public/data/surfaces.json').read_text())
    public=[s for s in surfaces if s['kind']=='roads' and s['tags'].get('name')=='秀厢大道']
    public_shape=unary_union([surface_shape(s) for s in public])
    # The delivered arterial includes its previously modeled lane widening
    # and curbs, not just the narrower raw OSM service-surface buffers.
    surroundings=json.loads((root/'public/data/surroundings.json').read_text())
    modeled_upper=unary_union([surface_shape(s) for s in surroundings['layers']
                              if s.get('id') in ('surrounding-road','surrounding-curb')])
    public_shape=public_shape.union(modeled_upper)
    widths={s['id']:s['width'] for s in surroundings['sources']}
    repairs=[];repair_shapes=[]
    # The old perimeter-road builder subtracted the campus tunnel connector
    # polygon from the arterial. Reconnect the same four mapped carriageways.
    for s in public:
        way=LineString(points(int(s['id'].split('/')[1])))
        cross=axis.intersection(way)
        if cross.geom_type!='Point':continue
        t=way.project(cross);a=way.interpolate(t-18);d=way.interpolate(t+18)
        length=a.distance(d);ux,uy=(d.x-a.x)/length,(d.y-a.y)/length
        width=widths[s['id']]
        ring=[[p.x-uy*v,p.y+ux*v] for p,v in [(a,-width/2-.45),(d,-width/2-.45),(d,width/2+.45),(a,width/2+.45)]]
        from shapely.geometry import Polygon
        repair_shapes.append(Polygon(ring))
        repairs.append({'roadId':s['id'],'a':list(a.coords)[0],'b':list(d.coords)[0],
                        'width':width,'direction':[ux,uy],'outline':ring})
    repair_area=unary_union(repair_shapes)
    public_shape=public_shape.union(repair_area)
    crossing=axis.intersection(public_shape)
    samples=[axis.project(Point(p)) for part in crossing.geoms for p in part.coords]
    lo,hi=min(samples),max(samples)
    soffit=min(elevation(*axis.interpolate(t).coords[0]) for t in samples)-.45
    floor=soffit-3.2
    path=[]
    for i in range(math.ceil(axis.length/2)+1):
        t=axis.length*i/math.ceil(axis.length/2);x,y=axis.interpolate(t).coords[0]
        natural=elevation(x,y)+.4
        weight=max(0,(lo-t)/lo,(t-hi)/(axis.length-hi));weight=weight*weight*(3-2*weight)
        path.append([x,y,floor*(1-weight)+natural*weight,natural,t])
    mask=axis.buffer(2.95,cap_style=2,join_style=2)
    # Rebuild only the four bounded deck patches; preserve other arterial faces.
    road_cut=mask.difference(public_shape.buffer(.03)).union(repair_area)
    def pack(shape):
        mesh=tiled_triangles(shape,step=1000)
        return [[mesh['vertices'][j] for j in mesh['triangles'][i:i+3]] for i in range(0,len(mesh['triangles']),3)]
    return {'id':'north-campus-underpass','name':'北校园桥洞下穿','osmId':'way/839763085',
            'sourceUrl':'https://www.openstreetmap.org/way/839763085',
            'axis':list(axis.coords),'path':path,'coveredRange':[lo,hi],'soffit':soffit,
            'floorElevation':floor,'clearWidth':5,'clearance':3.2,'cutHalfWidth':2.95,
            'bounds':list(mask.union(repair_area).bounds),'terrainMasks':pack(mask),'roadMasks':pack(road_cut),
            'upperRoadRepairs':repairs,
            'upperRoadIds':[s['id'] for s in public if surface_shape(s).intersects(mask)],
            'topologyBasis':'原始OSM tunnel=yes、layer=-1；用户于2026-10-05确认桥洞下穿，保留上方原有道路。',
            'dimensionBasis':'沿原道路走向；净宽、净高、坡度及桥洞构件为建模估算。'},mask
