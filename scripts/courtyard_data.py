"""A bounded courtyard layout anchored to existing building vertices."""
import copy
import math
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from building_overrides import footprint_revision
from surroundings_data import triangulate


def derive_courtyard(config, buildings, source_ids):
    keys = {'id', 'type', 'buildingId', 'footprintRevision', 'boundaryVertices',
            'frameVertices', 'contextRevisions', 'buildingClearance', 'surfaceOffset',
            'openAreaLocal', 'trees', 'sourceRefs', 'evidence'}
    if set(config) != keys or config['type'] != 'courtyard-paving':
        raise ValueError('Invalid courtyard fields')
    by_id = {b['id']: b for b in buildings}
    b = by_id.get(config['buildingId'])
    if not b or footprint_revision(b) != config['footprintRevision']:
        raise ValueError('Stale courtyard building')
    if not config['sourceRefs'] or not set(config['sourceRefs']) <= source_ids:
        raise ValueError('Unknown courtyard source')
    if not isinstance(config['evidence'], dict) or set(config['evidence']) != {'location', 'layout', 'dimensions', 'ground'} or not all(isinstance(s, str) and s.strip() for s in config['evidence'].values()):
        raise ValueError('Missing courtyard evidence')
    for key, limits in [('buildingClearance', (.05, .5)), ('surfaceOffset', (.03, .08))]:
        value = config[key]
        if type(value) not in (int, float) or not math.isfinite(value) or not limits[0] <= value <= limits[1]:
            raise ValueError('Invalid courtyard ' + key)
    ring = b['polygons'][0][0]
    def vertices(indices, count):
        if not isinstance(indices, list) or len(indices) != count or len(set(indices)) != count or any(type(i) is not int or not 0 <= i < len(ring)-1 for i in indices):
            raise ValueError('Invalid courtyard vertex anchors')
        return [ring[i] for i in indices]
    boundary = Polygon(vertices(config['boundaryVertices'], 4))
    if not boundary.is_valid or not 50 <= boundary.area <= 2000:
        raise ValueError('Invalid courtyard boundary')
    a, z = vertices(config['frameVertices'], 2)
    angle = math.atan2(z[1]-a[1], z[0]-a[0]); cs, sn = math.cos(angle), math.sin(angle)
    def world(p):
        if not isinstance(p, list) or len(p) != 2 or any(type(v) not in (int, float) or not math.isfinite(v) for v in p):
            raise ValueError('Invalid courtyard local point')
        return [a[0]+p[0]*cs-p[1]*sn, a[1]+p[0]*sn+p[1]*cs]
    obstacles = []
    neighbours = set()
    for other in buildings:
        shape = unary_union([Polygon(p[0], p[1:]) for p in other['polygons']])
        if shape.intersects(boundary.buffer(config['buildingClearance'])):
            if other['id'] != b['id']:
                neighbours.add(other['id'])
                if config['contextRevisions'].get(other['id']) != footprint_revision(other):
                    raise ValueError('Stale or unrecorded courtyard neighbour')
            obstacles.append(shape.buffer(config['buildingClearance'], join_style=2))
    if neighbours != set(config['contextRevisions']):
        raise ValueError('Courtyard neighbour set changed')
    available = boundary.difference(unary_union(obstacles))
    open_area = Polygon([world(p) for p in config['openAreaLocal']])
    if not open_area.is_valid or open_area.area < 25 or not available.covers(open_area):
        raise ValueError('Open activity area leaves courtyard')
    pits, trees, ids = [], [], set()
    if not isinstance(config['trees'], list) or not 1 <= len(config['trees']) <= 8:
        raise ValueError('Courtyard requires a small explicit tree layout')
    for item in config['trees']:
        if set(item) != {'id', 'local', 'height', 'template', 'pitRadius'} or not isinstance(item['id'], str) or not item['id'] or item['id'] in ids:
            raise ValueError('Invalid or duplicate courtyard tree')
        ids.add(item['id'])
        for key, limits in [('height', (4, 20)), ('pitRadius', (.8, 2))]:
            if type(item[key]) not in (int, float) or not math.isfinite(item[key]) or not limits[0] <= item[key] <= limits[1]:
                raise ValueError('Invalid courtyard tree ' + key)
        if type(item['template']) is not int or item['template'] not in (0, 1, 2):
            raise ValueError('Invalid courtyard tree template')
        xy = [round(v, 1) for v in world(item['local'])]
        point = Point(xy); pit = point.buffer(item['pitRadius'], quad_segs=6)
        if not available.covers(pit) or any(pit.intersects(p) for p in pits):
            raise ValueError('Courtyard tree pit leaves available ground or overlaps')
        if open_area.distance(point) <= 4*item['height']/9+1:
            raise ValueError('Tree crown intrudes into courtyard activity area')
        pits.append(pit); trees.append([*xy, item['height'], item['template']])
    paving = available.difference(unary_union(pits))
    if paving.geom_type != 'Polygon' or not paving.is_valid:
        raise ValueError('Courtyard paving must remain connected')
    result = {**copy.deepcopy(config), 'origin': a, 'angle': angle,
              'pavingPolygon': list(paving.exterior.coords),
              'pavingHoles': [list(r.coords) for r in paving.interiors],
              'replacementPolygon': list(boundary.exterior.coords),
              'openAreaPolygon': list(open_area.exterior.coords),
              'treeCandidates': trees, 'pavingMesh': triangulate(paving),
              'gradingBounds': list(boundary.bounds), 'layer': 'roads', 'material': 'path'}
    return result, paving, paving


def apply_courtyards(trees, sites):
    """Replace only the named courtyard background; final exclusion passes follow."""
    courts = [s for s in sites if s.get('type') == 'courtyard-paving']
    masks = [Polygon(s['replacementPolygon']) for s in courts]
    if any(a.intersects(b) for i, a in enumerate(masks) for b in masks[i+1:]):
        raise ValueError('Overlapping courtyard layouts')
    kept = [t for t in trees if not any(m.covers(Point(t[:2])) for m in masks)]
    existing = {tuple(t[:4]): t for t in trees}
    records = []
    for site, mask in zip(courts, masks):
        candidates = [existing.get(tuple(t), t) for t in site['treeCandidates']]
        kept.extend(candidates)
        records.append({'id': site['id'], 'candidates': candidates,
                        'replacedPriorRows': sum(mask.covers(Point(t[:2])) for t in trees),
                        'openAreaPolygon': site['openAreaPolygon'], 'sourceRefs': site['sourceRefs']})
    if len({tuple(t[:2]) for t in kept}) != len(kept):
        raise ValueError('Courtyard creates duplicate tree positions')
    return kept, records
