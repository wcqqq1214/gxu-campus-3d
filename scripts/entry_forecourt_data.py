"""Bounded, photo-derived lower stair / side courts and grounded exterior paving."""
import math
from shapely.geometry import Polygon, box
from shapely.ops import unary_union


def resolve_landscape(c, entry):
    if not isinstance(c,dict) or set(c)!={'lowerFlight','terraceWidth','court','groundPatches'}:
        raise ValueError('Entrance landscape requires flights, courts and ground patches')
    lower=c['lowerFlight'];court=c['court']
    for obj,keys in [(lower,{'toe','risers','tread','baseHeight','width'}),
                     (court,{'outerWidth','back','floorHeight','stairWidth','risers','tread'})]:
        if not isinstance(obj,dict) or set(obj)!=keys or any(type(v) not in (int,float) or not math.isfinite(v) for v in obj.values()):
            raise ValueError('Invalid lower flight or sunken court dimensions')
    base=entry['baseHeight'];pw=entry['platformWidth'];tw=c['terraceWidth']
    if type(tw) not in (int,float) or not math.isfinite(tw) or not lower['width']<=tw<=34:
        raise ValueError('Invalid raised terrace width')
    for flight,rise in [(lower,base-lower['baseHeight']),(court,base-court['floorHeight'])]:
        if type(flight['risers']) is not int or not 2<=flight['risers']<=24 or not .1<=rise/flight['risers']<=.2 or not .25<=flight['tread']<=.4:
            raise ValueError('Invalid landscape stair rise/run')
    end=lower['toe']+(lower['risers']-1)*lower['tread']
    if not entry['apronStart']<lower['toe']<end<=entry['toe']-1.5 or not pw<=lower['width']<=entry['apronFrontWidth']:
        raise ValueError('Lower flight must leave an approach and a raised landing')
    if not pw+4<=court['outerWidth']<=tw-2 or not entry['toe']+3<court['back']<=-.2 or not 1<=court['stairWidth']<=2:
        raise ValueError('Invalid side court bounds')
    if court['back']-entry['toe']-(court['risers']-1)*court['tread']<court['stairWidth']:
        raise ValueError('Sunken court needs a lower landing at least as deep as its stair width')
    areas=[box(-tw/2,end,tw/2,court['back']),
           box(-entry['apronFrontWidth']/2,entry['apronStart'],entry['apronFrontWidth']/2,end)]
    used=[]
    for patch in c['groundPatches']:
        if not isinstance(patch,dict) or set(patch)!={'id','material','vertices','triangles','boundary'} or patch['material'] not in ('stone','path'):
            raise ValueError('Invalid ground patch')
        if patch['id'] in used:raise ValueError('Duplicate ground patch')
        used.append(patch['id']);v=patch['vertices'];tris=patch['triangles']
        if len(v)<3 or any(len(p)!=3 or any(type(a) not in (int,float) or not math.isfinite(a) for a in p) or not -32<=p[0]<=32 or not -28<=p[1]<=-.2 or not -1<=p[2]<=9 for p in v):
            raise ValueError('Ground patch exceeds bounded entrance context')
        if not tris or len(tris)%3 or any(type(i) is not int or not 0<=i<len(v) for i in tris):raise ValueError('Invalid ground patch topology')
        shape=Polygon(patch['boundary'])
        faces=[Polygon([v[i][:2] for i in tris[k:k+3]]) for k in range(0,len(tris),3)]
        if not shape.is_valid or shape.area<.01 or unary_union(faces).symmetric_difference(shape).area>1e-6:
            raise ValueError('Ground patch coverage differs from its boundary')
        if any(shape.intersection(s).area>1e-6 for s in areas):raise ValueError('Ground patches overlap the raised court')
        areas.append(shape)
    return {**c,'lowerEnd':end},unary_union(areas)
