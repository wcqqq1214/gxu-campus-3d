"""A bounded glazed entrance with an optional explicitly dimensioned canopy."""
import math


def validate_flush_entrance(config, width, height):
    fields = {'floorHeight', 'glazingHeight', 'splitHeight', 'bays', 'pierWidth',
              'pierDepth', 'doorWidth', 'doorHeight', 'frameWidth'}
    if not isinstance(config, dict) or not fields <= set(config) or set(config)-fields-{'canopy','returnGlazing'}:
        raise ValueError('Flush entrance needs explicit glazing, door and frame dimensions')
    if type(config['bays']) is not int or config['bays'] not in (1, 3, 5):
        raise ValueError('Flush entrance needs an odd number of bays with a central door')
    for k in fields - {'bays'}:
        if type(config[k]) not in (int, float) or not math.isfinite(config[k]):
            raise ValueError('Flush entrance dimensions must be finite numbers')
    floor, top, split = (config[k] for k in ('floorHeight', 'glazingHeight', 'splitHeight'))
    pw, pd, fw = (config[k] for k in ('pierWidth', 'pierDepth', 'frameWidth'))
    if not 0 <= floor <= .5 or not floor + 3 <= top <= min(height-.2, 8):
        raise ValueError('Flush entrance glazing exceeds its wall')
    if not .25 <= pw <= .9 or not .1 <= pd <= .5 or not .04 <= fw <= .12:
        raise ValueError('Flush entrance frame dimensions are outside supported bounds')
    if not 2 <= config['doorHeight'] <= 3 or not 1.2 <= config['doorWidth'] <= width/config['bays']-pw-2*fw:
        raise ValueError('Flush entrance door does not fit its central bay')
    if not floor+config['doorHeight']+.2 <= split <= top-.5:
        raise ValueError('Flush entrance transom crosses the door or glazing head')
    if 'canopy' in config:
        canopy=config['canopy']
        if not isinstance(canopy,dict) or set(canopy)!={'width','depth','thickness'}:
            raise ValueError('Flush canopy requires width, depth and thickness')
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in canopy.values()):
            raise ValueError('Flush canopy dimensions must be finite numbers')
        if not width <= canopy['width'] <= width+4 or not .3 <= canopy['depth'] <= 4 or not .2 <= canopy['thickness'] <= 1.2:
            raise ValueError('Flush canopy dimensions exceed supported bounds')
        if top+canopy['thickness'] >= height-.2:
            raise ValueError('Flush canopy exceeds its wall height')


def validate_flush_canopy_footprint(building, entry, edge_length):
    """A canopy shares the entrance head, fits its edge and projects outside it."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    canopy=entry['flushEntrance'].get('canopy')
    if canopy is None:return
    width,depth=canopy['width'],canopy['depth']
    if width/2 > min(entry['t'],1-entry['t'])*edge_length:
        raise ValueError('Flush canopy extends beyond its facade')
    a=math.radians(entry['bearing']);nx,ny=math.sin(a),math.cos(a);x,y=entry['center']
    points=[[x+ny*u+nx*v,y-nx*u+ny*v] for u,v in [(-width/2,0),(width/2,0),(width/2,depth),(-width/2,depth)]]
    body=unary_union([Polygon(p[0],p[1:]) for p in building['polygons']])
    if Polygon(points).intersection(body).area>1e-5:
        raise ValueError('Flush canopy overlaps another building wing')
