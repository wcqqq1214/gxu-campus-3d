"""Local architectural envelopes clipped to mapped footprints, retaining inner rings."""
import math
import numpy as np
import mapbox_earcut as earcut
from shapely.geometry import Polygon, box
from shapely.affinity import rotate, translate


def pack(g, name, height):
    polygons = [g] if g.geom_type == 'Polygon' else [p for p in g.geoms if p.geom_type == 'Polygon']
    rings = [[list(p.exterior.coords)] + [list(r.coords) for r in p.interiors] for p in polygons if p.area > .01]
    triangles = [earcut.triangulate_float64(np.asarray([v for r in p for v in r[:-1]], dtype=np.float64), np.cumsum([len(r)-1 for r in p], dtype=np.uint32)).tolist() for p in rings]
    return {'name': name, 'height': height, 'polygons': rings, 'triangles': triangles}


def architectural_envelope(b):
    if b['landmark'] == 'teaching-ten':return teaching_ten_envelope(b)
    if b['landmark'] == 'teaching-six':return teaching_six_envelope(b)
    p = Polygon(b['polygons'][0][0], b['polygons'][0][1:])
    a, c = list(p.exterior.coords)[:2]
    angle = math.atan2(c[1]-a[1], c[0]-a[0]) % math.pi
    center = list(p.centroid.coords)[0]
    local = translate(rotate(p, -angle, origin=center, use_radians=True), -center[0], -center[1])
    if b['landmark'] == 'library':
        regions = [('南楼中央阅览区', box(-32,-100,35.5,-12.1),23.5),
                   ('南楼西翼',box(-100,-100,-32,.5),27),('南楼东翼',box(35.5,-100,100,.5),27),
                   ('内院两侧连廊',box(-32,-12.1,35.5,.5),27),
                   ('北楼主体',box(-100,.5,100,100),36)]
    else:
        # Whole mapped irregular footprint is the four-storey academic podium.
        # Two perpendicular residential wings leave the southeast recess open above it.
        regions = [('国际学院裙楼',box(-100,-100,100,100),13.2),
                   ('公寓西翼',box(-31.8,-24.7,-14.0,24.6),79.2),
                   ('公寓北翼',box(-14.0,6.8,15.7,24.6),79.2)]
    return {'origin': center, 'angle': angle, 'parts': [pack(local.intersection(region),name,height) for name,region,height in regions]}


def clear_entrance_trees(trees, buildings):
    """Clear crowns from modelled stairs / colonnades, without reseeding other trees."""
    from shapely.geometry import Point
    from shapely.ops import unary_union
    masks=[]
    for b in buildings:
        if b['landmark'] not in ('library','international-residence','teaching-ten','teaching-six'):continue
        e=b['architecture']
        if b['landmark']=='teaching-six':
            for ent in e['entrances']:
                x,y=ent['center'];w=ent['width']+3
                reach=22 if ent['id'] in ('south','north') else 6
                local=translate(rotate(box(-w/2,-reach,w/2,0),ent['angle'],origin=(0,0),use_radians=True),x,y)
                masks.append(translate(rotate(local,e['angle'],origin=(0,0),use_radians=True),*e['origin']))
            continue
        if b['landmark']=='teaching-ten':
            masks.append(translate(rotate(box(-6,-23,6,-17.5),e['angle'],origin=(0,0),use_radians=True),*e['origin']))
            continue
        entrances=[(-23,-45.5,27,-35),(-13.3,26.9,12.2,39.2)] if b['landmark']=='library' else [(-3,-32,18,-24)]
        for bounds in entrances:
            masks.append(translate(rotate(box(*bounds),e['angle'],origin=(0,0),use_radians=True),*e['origin']))
    mask=unary_union(masks)
    return [t for t in trees if mask.distance(Point(t[0],t[1]))>4*t[2]/9+1]


def teaching_ten_envelope(b):
    """Estimated height zones partition the real footprint without filling recesses."""
    p=Polygon(b['polygons'][0][0],b['polygons'][0][1:])
    edges=list(zip(p.exterior.coords,list(p.exterior.coords)[1:]))
    a,c=max(edges,key=lambda ab:math.dist(*ab))
    angle=math.atan2(c[1]-a[1],c[0]-a[0])%math.pi
    origin=(166,-190)
    local=translate(rotate(p,-angle,origin=origin,use_radians=True),-origin[0],-origin[1])
    north=local.intersection(box(-100,26,100,100))
    link=local.intersection(box(-5,13,8,26))
    central=local.intersection(box(-12,-11,12,13))
    low=local.difference(north.union(link).union(central))
    return {'origin':list(origin),'angle':angle,'parts':[
        pack(low,'南侧弧形教学区',9.9),pack(central,'中央高起采光体量',13.2),
        pack(link,'南北连接空间',6.6),pack(north,'北侧八层教学翼',26.4)],
        'footprint':list(local.exterior.coords),'entrance':[0,-19.35],
        'heightBasis':'北翼按 OSM 8 层乘 3.3 米估算，南部和连接区按照片分区估算'}


def teaching_six_envelope(b):
    """2025 official entrance diagram: central N/S passage and two side portals."""
    p=Polygon(b['polygons'][0][0],b['polygons'][0][1:])
    a,c=list(p.exterior.coords)[:2];angle=math.atan2(c[1]-a[1],c[0]-a[0])%math.pi
    origin=[(p.bounds[i]+p.bounds[i+2])/2 for i in (0,1)]
    local=translate(rotate(p,-angle,origin=origin,use_radians=True),-origin[0],-origin[1])
    # Openings follow the diagram; widths and clear heights are visual estimates.
    passages=box(-4,-31,4,31).union(box(-7,-31,7,-13)).union(box(-7,13,7,31))
    passages=passages.union(box(-59,-3.5,-34,3.5)).union(box(34,-3.5,59,3.5))
    return {'origin':origin,'angle':angle,'parts':[
        pack(local.difference(passages),'首层教室与门厅实墙',5.2),
        pack(local,'二至六层及三个内院',b['height']-5.2)],
        'footprint':list(local.exterior.coords),
        'entrances':[{'id':n,'center':c,'angle':a,'width':w} for n,c,a,w in [
            ('south',[0,-29.966],0,14),('north',[0,29.966],math.pi,14),
            ('west',[-57.116,0],-math.pi/2,7),('east',[57.116,0],math.pi/2,7)]],
        'passageCeilings':pack(local.intersection(passages),'架空通道顶板',.2),
        'entranceBasis':'2025-12-17 校方六教入口示意图；宽度、净高与台阶尺寸估算'}
