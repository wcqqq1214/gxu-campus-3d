"""Explicit external stair risers for an otherwise simple entrance."""
import math
from shapely.geometry import Polygon,LineString
from shapely.ops import unary_union

def resolve_stair_flight(building,entry,config,length):
    keys={'width','landingDepth','riserCount','tread','baseHeight'}
    if not isinstance(config,dict) or set(config)!=keys:raise ValueError('Stair flight needs all dimensions and a riser count')
    if type(config['riserCount']) is not int or not 2<=config['riserCount']<=10:raise ValueError('Invalid stair riser count')
    for k in keys-{'riserCount'}:
        if type(config[k]) not in (int,float) or not math.isfinite(config[k]):raise ValueError('Stair dimensions must be finite numbers')
    w,d,n,t,base=(config[k] for k in ['width','landingDepth','riserCount','tread','baseHeight'])
    if not .8<=d<=3 or not .25<=t<=.45 or base<0 or not .1<=(entry['landingHeight']-base)/n<=.2:
        raise ValueError('Unsupported stair depth, tread or riser height')
    if w<entry['width']+entry.get('doorFrame',{}).get('pierWidth',0) or w/2>min(entry['t'],1-entry['t'])*length:
        raise ValueError('Stair width must contain the doorway and fit its facade')
    if d<entry.get('doorFrame',{}).get('pierDepth',0)-.2:raise ValueError('Landing must support the entrance piers')
    a=math.radians(entry['bearing']);nx,ny=math.sin(a),math.cos(a);ox,oy=entry['center']
    point=lambda u,v:[ox+ny*u+nx*v,oy-nx*u+ny*v]
    front=d+(n-1)*t
    footprint=Polygon([point(-w/2,0),point(w/2,0),point(w/2,front),point(-w/2,front)])
    body=unary_union([Polygon(p[0],p[1:]) for p in building['polygons']])
    if not body.boundary.buffer(1e-5).covers(LineString([point(-w/2,0),point(w/2,0)])) or footprint.intersection(body).area>1e-5:
        raise ValueError('Stairs must attach to the facade without entering the building')
    return {**config,'front':front,'footprint':[list(p) for p in footprint.exterior.coords]}
