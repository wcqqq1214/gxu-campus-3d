"""Validate photo-located openings and palette choices on a corridor facade."""
import math


def validate_corridor_details(rule, length, height, levels):
    corridor = rule['openCorridor']
    finish = corridor.get('finish', {})
    if not isinstance(finish, dict) or set(finish) - {'wall', 'rail'}:
        raise ValueError('Invalid corridor finish fields')
    if any(value not in ('white', 'pink', 'stone') for value in finish.values()):
        raise ValueError('Corridor finish must use the shared wall palette')
    if 'openings' not in corridor:
        return
    openings = corridor['openings']
    if rule.get('windows') is not False or not isinstance(openings, list) or not 1 <= len(openings) <= 12:
        raise ValueError('Explicit corridor openings require disabled default windows')
    occupied = []
    for opening in openings:
        if not isinstance(opening, dict) or set(opening) != {'kind', 't', 'width', 'height', 'sill', 'levels'}:
            raise ValueError('Invalid corridor opening fields')
        if opening['kind'] not in ('door', 'window'):
            raise ValueError('Invalid corridor opening kind')
        for key in ('t', 'width', 'height', 'sill'):
            value = opening[key]
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError('Non-finite corridor opening dimension')
        if not 0 < opening['t'] < 1 or not .4 <= opening['width'] <= 3 or not .4 <= opening['height'] <= 3 or opening['sill'] < 0:
            raise ValueError('Invalid corridor opening dimensions')
        if opening['kind'] == 'door' and opening['sill'] != 0:
            raise ValueError('Corridor doorway must meet its floor')
        floors = opening['levels']
        if not isinstance(floors, list) or not floors or any(type(i) is not int or not 0 <= i < levels for i in floors) or len(set(floors)) != len(floors):
            raise ValueError('Invalid corridor opening levels')
        half = opening['width'] / 2 + .06
        left, right = opening['t'] * length - half, opening['t'] * length + half
        bottom, top = opening['sill'], opening['sill'] + opening['height'] + .06
        if left < corridor['endInset'] + .1 or right > length - corridor['endInset'] - .1 or top > height / levels - .23:
            raise ValueError('Corridor opening crosses a return or slab')
        for level in floors:
            if any(level == l and min(right, r) > max(left, a) and min(top, t) > max(bottom, b) for l, a, r, b, t in occupied):
                raise ValueError('Corridor openings overlap')
            occupied.append((level, left, right, bottom, top))
