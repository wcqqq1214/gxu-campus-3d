"""Bound the glazed rear wall of an already resolved open portico."""
import math
from shapely.geometry import LineString


def validate_recess_glazing(config, entry, opening, body_boundary, porch_shape, tangent):
    fields={'width','glazingHeight','transomHeight','sideColumns','doorWidth','doorHeight','frameWidth','bayGap'}
    if not isinstance(config,dict) or set(config)!=fields:
        raise ValueError('Recess glazing requires explicit banks, door and frame dimensions')
    if type(config['sideColumns']) is not int or not 2<=config['sideColumns']<=6:
        raise ValueError('Recess glazing side columns must be an integer from 2 to 6')
    for key in fields-{'sideColumns'}:
        if type(config[key]) not in (int,float) or not math.isfinite(config[key]):
            raise ValueError('Recess glazing dimensions must be finite numbers')
    width=config['width'];central=entry['width'];gap=config['bayGap'];fw=config['frameWidth']
    height=config['glazingHeight'];transom=config['transomHeight']
    if not .15<=gap<=1.2 or not .04<=fw<=.12:
        raise ValueError('Recess glazing gap and frame dimensions are outside supported bounds')
    side=(width-central-2*gap)/2
    if width>entry['porticoWidth']-.3 or side<=0 or (side-2*fw)/config['sideColumns']<.6:
        raise ValueError('Recess glazing banks do not fit the portico')
    if not 2.5<=height<=min(opening['clearHeight']-opening['floorHeight']-.15,4.5):
        raise ValueError('Recess glazing exceeds the portico clear height')
    if not 2<=config['doorHeight']<=3 or not 1.2<=config['doorWidth']<=min(central-4*fw,4.5):
        raise ValueError('Recess glazing door does not fit its central bank')
    if not config['doorHeight']+.15<=transom<=height-.25:
        raise ValueError('Recess glazing transom crosses the door or glazing head')
    rear=LineString([[entry['center'][i]+tangent[i]*offset for i in (0,1)] for offset in (-width/2,width/2)])
    if not body_boundary.buffer(.01).covers(rear) or not porch_shape.buffer(.01).covers(rear):
        raise ValueError('Recess glazing must lie on the main-body rear wall')
