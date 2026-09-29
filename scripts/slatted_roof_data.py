"""A photo-supported open portico roof, clipped to its existing quadrilateral.

The first polygon edge determines the slat direction. Optional solidBays
close selected spaces between beams, for a solid canopy with open side bays.
"""
import math
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union


def resolve_slatted_roof(polygons, config, columns):
    required = {'edgeWidth', 'slatWidth', 'slatCount'}
    if not isinstance(config, dict) or not required <= set(config) or set(config)-required-{'solidBays'}:
        raise ValueError('Slatted roof requires edgeWidth, slatWidth and slatCount')
    for key in ('edgeWidth', 'slatWidth'):
        v = config[key]
        if type(v) not in (float, int) or not math.isfinite(v) or v <= 0:
            raise ValueError('Slatted roof widths must be positive finite numbers')
    count = config['slatCount']
    if type(count) is not int or not 1 <= count <= 24:
        raise ValueError('Slatted roof needs 1–24 interior slats')
    solid = config.get('solidBays', [])
    if (not isinstance(solid, list) or any(type(i) is not int or not 0 <= i <= count for i in solid)
            or len(set(solid)) != len(solid) or len(solid) == count+1):
        raise ValueError('solidBays must be unique gap indices and retain at least one opening')
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
        uv=[(u0,v0),(u1,v0),(u1,v1),(u0,v1)]
        # Union mixed bays in the unit square: independently transformed beam
        # edges can otherwise produce microscopic gaps on oblique buildings.
        return Polygon(uv if solid else [point(u,v) for u,v in uv])
    eu=edge/u_length;ev=edge/v_length
    beams=[strip(0,eu,0,1),strip(1-eu,1,0,1),strip(eu,1-eu,0,ev),strip(eu,1-eu,1-ev,1)]
    for i in range(count):
        start=(edge+(i+1)*gap+i*slat)/v_length
        beams.append(strip(eu,1-eu,start,start+slat/v_length))
    for i in solid:
        # Overlap adjacent beams rather than relying on floating-point shared
        # edges. The union removes internal faces before triangulation.
        start=0 if i==0 else (edge+i*gap+(i-1)*slat)/v_length
        end=1 if i==count else (edge+(i+1)*gap+(i+1)*slat)/v_length
        beams.append(strip(0,1,start,end))
    roof=unary_union(beams)
    if solid and roof.geom_type == 'Polygon':
        roof=Polygon([point(*p) for p in roof.exterior.coords],
                     [[point(*p) for p in ring.coords] for ring in roof.interiors])
    if roof.difference(shape).area > 1e-7 or roof.geom_type != 'Polygon' or len(roof.interiors) != count+1-len(solid):
        raise ValueError('Slatted roof geometry must preserve every opening')
    for column in columns:
        if not roof.buffer(1e-7).covers(Point(column['center'])):
            raise ValueError('Slatted roof column center must meet a supporting beam')
    return roof
