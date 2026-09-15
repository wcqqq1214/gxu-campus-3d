"""A photo-supported open portico roof, clipped to its existing quadrilateral.

This is a flat beam lattice, not an occupied storey or a solid roof slab.
The first polygon edge determines the slat direction.
"""
import math
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union


def resolve_slatted_roof(polygons, config, columns):
    if not isinstance(config, dict) or set(config) != {'edgeWidth', 'slatWidth', 'slatCount'}:
        raise ValueError('Slatted roof requires edgeWidth, slatWidth and slatCount')
    for key in ('edgeWidth', 'slatWidth'):
        v = config[key]
        if type(v) not in (float, int) or not math.isfinite(v) or v <= 0:
            raise ValueError('Slatted roof widths must be positive finite numbers')
    count = config['slatCount']
    if type(count) is not int or not 1 <= count <= 24:
        raise ValueError('Slatted roof needs 1–24 interior slats')
    if len(polygons) != 1 or len(polygons[0]) != 1 or len(polygons[0][0]) != 5:
        raise ValueError('Slatted roof requires one quadrilateral without holes')
    pts = polygons[0][0][:-1]
    shape = Polygon(pts)
    if not shape.is_valid or shape.area <= 0 or shape.symmetric_difference(shape.convex_hull).area > 1e-7:
        raise ValueError('Slatted roof requires a convex quadrilateral')
    lengths = [math.dist(pts[i], pts[(i+1)%4]) for i in range(4)]
    if min(lengths) <= 0:
        raise ValueError('Slatted roof has a collapsed edge')
    for i in range(4):
        a,b,c=pts[i-1],pts[i],pts[(i+1)%4]
        cosine=sum((a[k]-b[k])*(c[k]-b[k]) for k in range(2))/(lengths[i-1]*lengths[i])
        if abs(cosine) > math.sin(math.radians(5)):
            raise ValueError('Slatted roof corners must be within five degrees of square')
    u_length=min(lengths[0],lengths[2]);v_length=min(lengths[1],lengths[3])
    edge=config['edgeWidth'];slat=config['slatWidth']
    gap=(v_length-2*edge-count*slat)/(count+1)
    if u_length-2*edge < .5 or gap < .25:
        raise ValueError('Slatted roof must retain at least 0.25m open gaps')
    def point(u,v):
        return [(1-u)*(1-v)*pts[0][k]+u*(1-v)*pts[1][k]+u*v*pts[2][k]+(1-u)*v*pts[3][k] for k in range(2)]
    def strip(u0,u1,v0,v1):
        return Polygon([point(u0,v0),point(u1,v0),point(u1,v1),point(u0,v1)])
    eu=edge/u_length;ev=edge/v_length
    beams=[strip(0,eu,0,1),strip(1-eu,1,0,1),strip(eu,1-eu,0,ev),strip(eu,1-eu,1-ev,1)]
    for i in range(count):
        start=(edge+(i+1)*gap+i*slat)/v_length
        beams.append(strip(eu,1-eu,start,start+slat/v_length))
    roof=unary_union(beams)
    if roof.difference(shape).area > 1e-7 or roof.geom_type != 'Polygon' or len(roof.interiors) != count+1:
        raise ValueError('Slatted roof geometry must preserve every opening')
    for column in columns:
        if not roof.buffer(1e-7).covers(Point(column['center'])):
            raise ValueError('Slatted roof column center must meet a supporting beam')
    return roof
