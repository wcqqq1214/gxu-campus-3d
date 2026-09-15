"""A bounded glazed entrance in the existing wall, without an invented canopy."""
import math


def validate_flush_entrance(config, width, height):
    fields = {'floorHeight', 'glazingHeight', 'splitHeight', 'bays', 'pierWidth',
              'pierDepth', 'doorWidth', 'doorHeight', 'frameWidth'}
    if not isinstance(config, dict) or set(config) != fields:
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
