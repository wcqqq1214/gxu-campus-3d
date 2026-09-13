"""Sourced, estimated low planting anchored to an existing building frame."""
import json
import math
from pathlib import Path

from shapely.geometry import LineString, Polygon, shape
from shapely.ops import transform
from building_overrides import footprint_revision, read_json, source_catalogue
from site_data import world_shape
from vegetation_exclusions import INPUT_NAMES, ground_masks
from vegetation_reservations import INPUT_NAMES as RESERVATION_INPUTS, crown_reservations
from low_planting_contract import digest, context_value

ROOT = Path(__file__).resolve().parents[1]


def derive_plantings(config, buildings, source_ids, campus, exclusions, open_zones):
    if not isinstance(config, dict) or set(config) != {'schemaVersion', 'plantings'} or type(config['schemaVersion']) is not int or config['schemaVersion'] != 1 or not isinstance(config['plantings'], list):
        raise ValueError('Invalid low-planting catalogue')
    fields = {'id', 'type', 'buildingId', 'footprintRevision', 'localLine',
              'widthMeters', 'heightMeters', 'sourceRefs', 'evidence'}
    result, ids, shapes = [], set(), []
    by_id = {b['id']:b for b in buildings}
    for item in config['plantings']:
        if not isinstance(item, dict) or set(item) != fields:
            raise ValueError('Unknown or missing low-planting field')
        if not isinstance(item['id'], str) or not item['id'].strip() or item['id'] in ids or item['type'] != 'hedge':
            raise ValueError('Invalid low-planting identity or type')
        ids.add(item['id'])
        building = by_id.get(item['buildingId'])
        if not building or item['footprintRevision'] != footprint_revision(building):
            raise ValueError('Unknown building or stale low-planting footprint')
        frame = building.get('architecture', {})
        if 'origin' not in frame or 'angle' not in frame:
            raise ValueError('Low planting requires a calibrated building frame')
        refs = item['sourceRefs']
        if not isinstance(refs, list) or not refs or not all(isinstance(s, str) and s in source_ids for s in refs):
            raise ValueError('Unknown low-planting source')
        evidence = item['evidence']
        if not isinstance(evidence, dict) or set(evidence) != {'placement', 'dimensions', 'species', 'openSpace'} or not all(isinstance(v, str) and v.strip() for v in evidence.values()):
            raise ValueError('Low planting requires field-specific evidence')
        number = lambda v: type(v) in (int, float) and math.isfinite(v)
        line = item['localLine']
        if not isinstance(line, list) or len(line) != 2 or not all(isinstance(p, list) and len(p) == 2 and all(number(v) for v in p) for p in line):
            raise ValueError('Low-planting line requires two finite local points')
        if not 1 <= LineString(line).length <= 50:
            raise ValueError('Invalid low-planting length')
        width, height = item['widthMeters'], item['heightMeters']
        if not number(width) or not .3 <= width <= 4 or not number(height) or not .2 <= height <= 1.5:
            raise ValueError('Invalid low-planting dimensions')
        world = world_shape(LineString(line), frame)
        area = world.buffer(width / 2, cap_style=2)
        if not campus.covers(area):
            raise ValueError('Low planting is outside the campus')
        # Reject occupied placement rather than silently moving a sourced hedge.
        for ident, geometry in exclusions + open_zones:
            if area.intersects(geometry):
                raise ValueError(f'Low planting intersects reserved space: {ident}')
        if any(area.intersects(other) for other in shapes):
            raise ValueError('Overlapping low planting')
        shapes.append(area)
        result.append({**item, 'line': [list(p) for p in world.coords],
                       'polygon': [list(p) for p in area.exterior.coords],
                       'areaMeters2': area.area, 'origin': frame['origin'], 'angle': frame['angle']})
    return result


def prepare_low_planting(root=ROOT):
    from prepare_geodata import project
    out = root / 'public/data'
    config = read_json(root / 'data/low-planting.json')
    data = {name:read_json(out / (name + '.json')) for name in dict.fromkeys(INPUT_NAMES + RESERVATION_INPUTS)}
    masks, _ = ground_masks(data)
    exclusions = [(m.id, m.geometry) for m in masks]
    exclusions += [(m.id, m.geometry.buffer(m.radius) if m.radius else m.geometry)
                   for m in crown_reservations(data)]
    from vegetation_data import load_zones
    zone_shapes = {('campus-roads', data['campus-roads']['lawn']['osmId']):Polygon(data['campus-roads']['lawn']['polygon'])}
    zone_shapes.update({('sites', s['id']):Polygon(s['pavingPolygon']) for s in data['sites']['sites']})
    open_zones = [(z['id'], zone_shapes[(z['stage'], z['maskRef'])]) for z in load_zones(root)]
    geo = read_json(out / 'geography.geojson')
    campus = transform(project, shape(next(f['geometry'] for f in geo['features'] if f['id'] == 'campus')))
    plantings = derive_plantings(config, data['buildings'], {s['id'] for s in source_catalogue(root)}, campus, exclusions, open_zones)
    report = {'schemaVersion': 1, 'plantings': plantings,
              'contextRevision': digest(context_value(root, config, data)),
              'configRevision': digest(config), 'placementPassed': True,
              'scope': 'Entire low-planting footprints avoid final ground masks, existing structural reservations and explicit open zones. Actual terrain support and mesh checks run after modeling.'}
    (out / 'low-planting.json').write_text(json.dumps(report, ensure_ascii=False, separators=(',', ':')) + '\n')
    return report


if __name__ == '__main__':
    print('Prepared low plantings:', len(prepare_low_planting()['plantings']))
