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
        if b['landmark'] not in ('library','international-residence'):continue
        e=b['architecture']
        bounds=(-23,-45.5,27,-35) if b['landmark']=='library' else (-3,-32,18,-24)
        masks.append(translate(rotate(box(*bounds),e['angle'],origin=(0,0),use_radians=True),*e['origin']))
    mask=unary_union(masks)
    return [t for t in trees if mask.distance(Point(t[0],t[1]))>4*t[2]/9+1]
