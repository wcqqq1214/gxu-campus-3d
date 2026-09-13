"""Validate photo-constrained window groups on a bounded, solid facade strip."""
import math


def number(value, label):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('Window bands need a finite ' + label)
    return value


def validate_window_bands(config, length, height, levels):
    fields = {'from', 'to', 'firstLevel', 'heightRatio', 'depth', 'thickness', 'windows'}
    if not isinstance(config, dict) or set(config) != fields:
        raise ValueError('Window bands need a bounded strip, floors, ledges and window spans')
    for key in fields - {'firstLevel', 'windows'}:
        number(config[key], key)
    if not 0 <= config['from'] < config['to'] <= 1:
        raise ValueError('Window band bounds must lie on the original facade')
    if (type(config['firstLevel']) is not int or levels != int(levels)
            or not 1 <= config['firstLevel'] < levels):
        raise ValueError('Window bands require whole upper floors and preserve the ground floor')
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

