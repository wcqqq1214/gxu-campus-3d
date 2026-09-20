"""Validate photo-located openings and palette choices on a corridor facade."""
import math


def validate_corridor_details(rule, length, height, levels):
    corridor = rule['openCorridor']
    if 'frontProfile' in corridor:
        profile = corridor['frontProfile']
        if (not isinstance(profile, list) or not 3 <= len(profile) <= 64 or
                any(not isinstance(p, list) or len(p) != 2 or
                    any(type(v) not in (int, float) or not math.isfinite(v) for v in p) for p in profile)):
            raise ValueError('Corridor front profile needs 3–64 finite fraction/depth pairs')
        if profile[0] != [0, 0] or profile[-1] != [1, 0]:
            raise ValueError('Corridor front profile must meet both original end returns')
        if (corridor['firstLevel'] < 1 or corridor.get('lastLevel', levels-1) != levels-1
                or 'piers' in corridor or 'balusters' in corridor):
            raise ValueError('Profiled corridor needs a retained ground floor, full upper stack and solid rails without piers')
        span = length-2*corridor['endInset']
        if (any(not 0 <= t <= 1 or not 0 <= d <= min(.8, corridor['depth']-.6) for t, d in profile) or
                any((b[0]-a[0])*span < .15 for a, b in zip(profile, profile[1:]))):
            raise ValueError('Corridor front profile must progress along the facade and leave rear clearance')
    thickness = corridor.get('firstSlabThickness', .18)
    if type(thickness) not in (int, float) or not math.isfinite(thickness) or not .08 <= thickness <= .3:
        raise ValueError('Corridor first slab thickness must be between 0.08 and 0.30 metres')
    if 'piers' in corridor:
        first = corridor['piers'].get('firstLevel', corridor['firstLevel'])
        if (type(first) is not int or not corridor['firstLevel'] <= first <= corridor.get('lastLevel', levels-1)
                or (corridor['firstLevel'] == 0 and first != 0)):
            raise ValueError('Corridor pier firstLevel must lie within its recess and retain ground piers')
    finish = corridor.get('finish', {})
    if not isinstance(finish, dict) or set(finish) - {'wall', 'rail'}:
        raise ValueError('Invalid corridor finish fields')
    if any(value not in ('white', 'pink', 'stone') for value in finish.values()):
        raise ValueError('Corridor finish must use the shared wall palette')
    if 'openings' not in corridor:
        return
    openings = corridor['openings']
    if not isinstance(openings, list) or not 1 <= len(openings) <= 32:
        raise ValueError('Explicit corridor openings require 1–32 opening definitions')
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
        if rule.get('windows') is not False and any(
                not corridor['firstLevel'] <= level <= corridor.get('lastLevel', levels-1)
                for level in floors):
            raise ValueError('Mixed explicit openings must stay within recessed floors')
        half = opening['width'] / 2 + .06
        left, right = opening['t'] * length - half, opening['t'] * length + half
        bottom, top = opening['sill'], opening['sill'] + opening['height'] + .06
        if left < corridor['endInset'] + .1 or right > length - corridor['endInset'] - .1 or top > height / levels - .23:
            raise ValueError('Corridor opening crosses a return or slab')
        for level in floors:
            if any(level == l and min(right, r) > max(left, a) and min(top, t) > max(bottom, b) for l, a, r, b, t in occupied):
                raise ValueError('Corridor openings overlap')
            occupied.append((level, left, right, bottom, top))


def validate_corridor_facade_layers(rule, height, levels):
    """Allow solid-wall bands/panels only outside the recessed slab stack."""
    corridor = rule['openCorridor']; fh = height/levels
    low = corridor['firstLevel']*fh-corridor.get('firstSlabThickness', .18)
    high = (corridor.get('lastLevel', levels-1)+1)*fh
    for panel in rule.get('panels', []):
        if panel['bottom'] < high and panel['top'] > low:
            raise ValueError('Facade panel overlaps the recessed corridor or slab')
    band = rule.get('windowBands')
    if band:
        for level in range(band['firstLevel'], band.get('lastLevel', int(levels)-1)+1):
            bottom = (level+.56-band['heightRatio']/2)*fh-.06
            top = (level+.56+band['heightRatio']/2)*fh+.12+band['thickness']
            if bottom < high and top > low:
                raise ValueError('Window band or ledge overlaps the recessed corridor or slab')
