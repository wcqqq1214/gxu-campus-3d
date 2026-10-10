"""Resolve bounded road grading from existing entrance and mapped road anchors.

No prepared geometry cache: every build checks the pinned input revisions and
resolves the same source data. Blender can load this without Shapely.
"""
import hashlib
import json
import math


def revision(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def load_landings(root, configuration='data/road-landing-overrides.json'):
    read = lambda name: json.loads((root / name).read_text())
    buildings = read('public/data/buildings.json')
    surfaces = read('public/data/surfaces.json')
    overlays = [read('public/data/' + name + '.json') for name in
                ('infrastructure', 'surroundings', 'campus-roads', 'sites')]
    records = read(configuration)['landings']
    result = []
    for config in records:
        b = next(b for b in buildings if b['id'] == config['buildingId'])
        e = next(e for e in b['form']['entrances'] if e['id'] == config['entranceId'])
        index, surface = next((i, s) for i, s in enumerate(surfaces) if s['id'] == config['surfaceId'])
        if surface.get('suppressed') or surface['id'] in overlays[0]['replaceSurfaceIds']:
            raise ValueError('Road landing targets a replaced or suppressed road')
        for overlay in overlays:
            surface = {**surface, **overlay['surfaceOverrides'].get(str(index), {})}
        if surface['kind'] != 'roads' or surface['tags'].get('highway') != 'service':
            raise ValueError('Road landing requires an existing service road')
        if config['surfaceRevision'] != revision(surface) or config['anchorRevision'] != revision([b['elevation'], e]):
            raise ValueError('Road landing anchors changed; inspect and revise its bounded configuration')
        numeric = [config['sideFeather'], config['meshStep'], config['minimumTerrainClearance'], *config['depthStations']]
        if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in numeric):
            raise ValueError('Road landing dimensions must be finite and positive')
        stations = config['depthStations']
        if len(stations) != 4 or any(a >= b for a, b in zip(stations, stations[1:])):
            raise ValueError('Road landing needs four increasing depth stations')
        toe = e.get('steps', 3) * .3 + .01
        if not stations[1] <= toe <= toe + .025 <= stations[2]:
            raise ValueError('Road landing level band must contain the existing outer stair toe')
        if config['meshStep'] > 1 or config['sideFeather'] < 1:
            raise ValueError('Road landing needs a bounded mesh and a side transition')
        angle = math.radians(e['bearing'])
        normal = [math.sin(angle), math.cos(angle)]
        result.append({**config, 'origin': e['outerCenter'], 'normal': normal,
                       'tangent': [normal[1], -normal[0]],
                       'halfWidth': e.get('stepWidth', e['porticoWidth']) / 2,
                       'targetElevation': b['elevation'] + e.get('stepBaseHeight', 0),
                       'surface': surface})
    if len({r['id'] for r in result}) != len(result):
        raise ValueError('Duplicate road landing')
    return result
