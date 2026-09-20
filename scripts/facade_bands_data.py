"""Validate photo-constrained window groups on a bounded, solid facade strip."""
import math


def validate_horizontal_ledges(config, height):
    """Independent eaves, with explicit top heights above the building datum."""
    fields = {'from', 'to', 'tops', 'depth', 'thickness'}
    if not isinstance(config, dict) or set(config) != fields:
        raise ValueError('Horizontal ledges need bounds, top heights, depth and thickness')
    for key in fields - {'tops'}:
        number(config[key], key)
    if not 0 <= config['from'] < config['to'] <= 1:
        raise ValueError('Horizontal ledges must stay on their facade')
    if not .1 <= config['depth'] <= 1 or not .06 <= config['thickness'] <= .3:
        raise ValueError('Horizontal ledge dimensions are not usable')
    tops = config['tops']
    if not isinstance(tops, list) or not 1 <= len(tops) <= 50:
        raise ValueError('Horizontal ledges need explicit top heights')
    previous = 0
    for top in tops:
        number(top, 'top height')
        if not previous + config['thickness'] + .1 <= top <= height:
            raise ValueError('Horizontal ledges must be ordered, separate and within the wall height')
        previous = top


def number(value, label):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('Window bands need a finite ' + label)
    return value


def validate_window_bands(config, length, height, levels):
    fields = {'from', 'to', 'firstLevel', 'heightRatio', 'depth', 'thickness', 'windows'}
    if not isinstance(config, dict) or not fields <= set(config) or set(config) - fields - {'lastLevel'}:
        raise ValueError('Window bands need a bounded strip, floors, ledges and window spans')
    for key in fields - {'firstLevel', 'windows'}:
        number(config[key], key)
    if not 0 <= config['from'] < config['to'] <= 1:
        raise ValueError('Window band bounds must lie on the original facade')
    if (type(config['firstLevel']) is not int or levels != int(levels)
            or not 1 <= config['firstLevel'] < levels):
        raise ValueError('Window bands require whole upper floors and preserve the ground floor')
    if 'lastLevel' in config and (type(config['lastLevel']) is not int
            or not config['firstLevel'] <= config['lastLevel'] < levels):
        raise ValueError('Window band lastLevel must be a whole floor within the selected upper floors')
    if not .2 <= config['heightRatio'] <= .75 or not 0 < config['depth'] <= 1:
        raise ValueError('Window band height or ledge depth is not usable')
    fh = height / levels
    if not .06 <= config['thickness'] <= min(.5, fh * .1):
        raise ValueError('Window band ledge thickness is not usable')
    windows = config['windows']
    if not isinstance(windows, list) or not 1 <= len(windows) <= 32:
        raise ValueError('Window bands require explicit window spans')
    previous = config['from']
    for window in windows:
        if not isinstance(window, dict) or set(window) != {'from', 'to', 'panes'}:
            raise ValueError('Each window span needs from, to and panes')
        start, end = (number(window[k], k) for k in ('from', 'to'))
        if not previous <= start < end <= config['to']:
            raise ValueError('Window spans must be ordered, separate and inside the band')
        if (type(window['panes']) is not int or not 1 <= window['panes'] <= 12
                or (end-start)*length < window['panes']*.3):
            raise ValueError('Window panes do not fit their span')
        # Include the 6 cm frame on each side and a remaining wall gap.
        if (start-previous)*length < .16:
            raise ValueError('Window frames overlap each other or the band boundary')
        previous = end
    if (config['to']-previous)*length < .16:
        raise ValueError('Last window frame crosses the band boundary')
