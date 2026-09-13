"""Stable background candidates and sourced open-space exclusions.

The zone list supports no-tree masks; background parameters are configured
separately. Infrastructure, sports, sculpture and entrance filters precede the
final derived-ground and no-tree passes. Every upstream tree source reaches
these final placement constraints before grounding and 3D building checks.
"""
import hashlib
import json
import math
import random
from pathlib import Path
from shapely.geometry import Point, Polygon
from building_overrides import read_json, source_catalogue

ROOT = Path(__file__).resolve().parents[1]


def load_zones(root=ROOT):
    data = read_json(root / 'data/vegetation-zones.json')
    if not isinstance(data, dict) or not {'schemaVersion', 'zones'} <= set(data) or set(data) - {'schemaVersion', 'zones', 'background'} or type(data['schemaVersion']) is not int or data['schemaVersion'] != 1 or not isinstance(data['zones'], list):
        raise ValueError('Vegetation zones require schemaVersion 1 and a zone list')
    sources = {s['id'] for s in source_catalogue(root)}
    ids = set()
    for zone in data['zones']:
        if set(zone) != {'id', 'type', 'stage', 'maskRef', 'sourceRefs', 'evidence'}:
            raise ValueError('Unknown or missing vegetation zone field')
        if not isinstance(zone['id'], str) or not zone['id'].strip() or zone['id'] in ids:
            raise ValueError('Missing or duplicate vegetation zone ID')
        ids.add(zone['id'])
        if zone['type'] != 'no-tree' or zone['stage'] not in {'campus-roads', 'sites'}:
            raise ValueError('Unsupported vegetation zone rule or preparation stage')
        if not isinstance(zone['maskRef'], str) or not zone['maskRef'].strip():
            raise ValueError('Vegetation zone requires a mask reference')
        refs = zone['sourceRefs']
        if not isinstance(refs, list) or not refs or not all(isinstance(x, str) for x in refs) or not set(refs) <= sources:
            raise ValueError('Unknown or missing vegetation source')
        if not isinstance(zone['evidence'], str) or not zone['evidence'].strip():
            raise ValueError('Vegetation zone requires an evidence note')
    return data['zones']


def load_background(root=ROOT):
    # Validate the shared catalogue as well, even when only generating candidates.
    load_zones(root)
    config = read_json(root / 'data/vegetation-zones.json').get('background')
    fields = {'id', 'seed', 'spacingMeters', 'jitterMeters', 'heightRangeMeters',
              'greenDensity', 'otherDensity', 'typeWeights', 'sourceRefs', 'evidence'}
    if not isinstance(config, dict) or set(config) != fields:
        raise ValueError('Background vegetation requires explicit parameters')
    if not isinstance(config['id'], str) or not config['id'].strip():
        raise ValueError('Background vegetation requires a stable ID')
    if type(config['seed']) is not int or not 0 <= config['seed'] < 2**32:
        raise ValueError('Invalid background seed')
    def number(value):
        return type(value) in (int, float) and math.isfinite(value)
    spacing, jitter = config['spacingMeters'], config['jitterMeters']
    if not number(spacing) or not 5 <= spacing <= 50 or not number(jitter) or not 0 <= jitter < spacing/2:
        raise ValueError('Invalid background grid spacing or jitter')
    heights, weights = config['heightRangeMeters'], config['typeWeights']
    if not isinstance(heights, list) or len(heights) != 2 or not all(number(x) for x in heights) or not 0 < heights[0] <= heights[1] <= 50:
        raise ValueError('Invalid background height range')
    if not isinstance(weights, list) or len(weights) != 3 or not all(number(x) and x >= 0 for x in weights) or sum(weights) <= 0:
        raise ValueError('Invalid background template weights')
    if not all(number(config[k]) and 0 <= config[k] <= 1 for k in ['greenDensity', 'otherDensity']):
        raise ValueError('Invalid background density')
    refs = config['sourceRefs']; sources = {s['id'] for s in source_catalogue(root)}
    if not isinstance(refs, list) or not refs or not all(isinstance(x, str) for x in refs) or not set(refs) <= sources:
        raise ValueError('Unknown or missing background source')
    if not isinstance(config['evidence'], str) or not config['evidence'].strip():
        raise ValueError('Background vegetation requires an evidence note')
    return config


def generate_background(bounds, valid, green, config):
    """One independent candidate per world-anchored cell, then local acceptance.

    Acceptance, greenness and traversal bounds cannot consume another cell's
    random sequence. Quantize before mask checks so the exported point is tested.
    """
    spacing = config['spacingMeters']; jitter = config['jitterMeters']
    x0,y0,x1,y1 = bounds
    trees = []
    for iy in range(math.floor(y0/spacing), math.ceil(y1/spacing)):
        for ix in range(math.floor(x0/spacing), math.ceil(x1/spacing)):
            key = f"background-v1:{config['id']}:{config['seed']}:{ix}:{iy}"
            seed = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], 'big')
            rng = random.Random(seed)
            x = round((ix+.5)*spacing+rng.uniform(-jitter,jitter),1)
            y = round((iy+.5)*spacing+rng.uniform(-jitter,jitter),1)
            chance = rng.random()
            height = round(rng.uniform(*config['heightRangeMeters']),1)
            typ = rng.choices([0,1,2],config['typeWeights'])[0]
            p = Point(x,y)
            density = config['greenDensity'] if green.contains(p) else config['otherDensity']
            if x0 <= x <= x1 and y0 <= y <= y1 and valid.contains(p) and chance < density:
                trees.append([x,y,height,typ])
    return trees


def filter_zones(trees, zones, masks):
    resolved = []
    for zone in zones:
        key = (zone['stage'], zone['maskRef'])
        if key not in masks:
            raise ValueError(f'Unresolved vegetation mask: {key}')
        mask = masks[key]
        if mask.is_empty or not mask.is_valid or mask.geom_type not in {'Polygon', 'MultiPolygon'}:
            raise ValueError(f'Invalid vegetation mask: {key}')
        resolved.append(mask)
    return [t for t in trees if all(mask.distance(Point(t[:2])) > 4 * t[2] / 9 + 1 for mask in resolved)]


def apply_stage(trees, stage, masks, root=ROOT):
    zones = [z for z in load_zones(root) if z['stage'] == stage]
    return filter_zones(trees, zones, {(stage, key): value for key, value in masks.items()})


def prepare_vegetation(root=ROOT):
    from vegetation_exclusions import INPUT_NAMES, final_ground_exclusions
    from vegetation_reservations import INPUT_NAMES as RESERVATION_INPUTS, final_crown_reservations
    from vegetation_avenues import derive_avenues, apply_avenues
    out = root / 'public/data'
    read = lambda name: json.loads((out / name).read_text())
    zones = load_zones(root)
    background = load_background(root)
    roads = read('campus-roads.json')
    sites = read('sites.json')['sites']
    masks = {('campus-roads', roads['lawn']['osmId']): Polygon(roads['lawn']['polygon'])}
    masks.update({('sites', s['id']): Polygon(s['pavingPolygon']) for s in sites})
    trees = read('vegetation.json')
    candidates, avenue_records = apply_avenues(trees, derive_avenues(root))
    context = {name: read(name+'.json') for name in dict.fromkeys(INPUT_NAMES+RESERVATION_INPUTS)}
    ground_kept, ground_report = final_ground_exclusions(candidates, context)
    reserved_kept, reservation_report = final_crown_reservations(ground_kept, context)
    kept = filter_zones(reserved_kept, zones, masks)
    kept_positions = {tuple(t[:2]) for t in kept}
    for avenue in avenue_records:
        avenue['retainedCandidates'] = [t for t in avenue['candidates'] if tuple(t[:2]) in kept_positions]
    records = [{**z, 'polygon': list(masks[(z['stage'], z['maskRef'])].exterior.coords),
                'remainingCrownConflicts': sum(masks[(z['stage'], z['maskRef'])].distance(Point(t[:2])) <= 4*t[2]/9+1 for t in kept)} for z in zones]
    overview = read('overview.json'); overview['trees'] = len(kept)
    report = {'schemaVersion': 1, 'zones': records, 'trees': len(kept),
              'removedInFinalPass': len(candidates)-len(kept),
              'avenues': avenue_records,
              'finalGroundExclusion': ground_report,
              'finalCrownReservations': reservation_report,
              'rotationBasis': 'Position-keyed FNV-1a, decimetres; schematic, not surveyed.',
              'background': background,
              'backgroundBasis': 'Independent SHA-256-seeded candidates in world-anchored cells; local masks and green density cannot shift other cells.',
              'passed': all(z['remainingCrownConflicts'] == 0 for z in records)}
    for name, value in [('vegetation.json', kept), ('vegetation-zones.json', report), ('overview.json', overview)]:
        (out / name).write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':'))+'\n')
    from low_planting_data import prepare_low_planting
    prepare_low_planting(root)
    print('Vegetation zones prepared', len(zones), 'trees', len(kept), flush=True)


if __name__ == '__main__':
    prepare_vegetation()
