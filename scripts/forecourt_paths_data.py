"""Source-attributed garden paths that meet an existing grounded service road."""
import copy
import hashlib
import json
import math
from shapely.affinity import scale
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import unary_union
from building_overrides import footprint_revision
from surroundings_data import surface_shape, triangulate
from shore_data import revision, geometry_rings


def surface_revision(surface):
    return hashlib.sha256(json.dumps(surface, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def derive_forecourt_paths(config, buildings, surface, paving, source_ids):
    keys = {'id', 'type', 'buildingId', 'footprintRevision', 'surfaceId',
            'surfaceRevision', 'boundary', 'center', 'radii', 'pathWidth',
            'branches', 'surfaceOffset', 'batchWith', 'sourceRefs', 'evidence'}
    if set(config) != keys or config['type'] != 'forecourt-paths':
        raise ValueError('Invalid forecourt path fields')
    if not isinstance(config['batchWith'], str) or not config['batchWith'] or config['batchWith']==config['id']:
        raise ValueError('Forecourt paths need a separate existing paving batch')
    building = next((b for b in buildings if b['id'] == config['buildingId']), None)
    if not building or footprint_revision(building) != config['footprintRevision']:
        raise ValueError('Stale forecourt building')
    if not surface or surface['id'] != config['surfaceId'] or surface_revision(surface) != config['surfaceRevision']:
        raise ValueError('Stale forecourt road')
    tags=surface.get('tags',{})
    if (surface.get('kind')!='roads' or not surface.get('insideCampus') or tags.get('highway')!='service'
            or tags.get('bridge') or tags.get('tunnel') or str(tags.get('layer','0'))!='0'):
        raise ValueError('Forecourt contact must be a campus road at grade')
    if not paving or paving['surfaceId'] != config['surfaceId'] or paving['surfaceRevision'] != revision(surface['vertices']) or paving.get('groundedService', {}).get('offset') != config['surfaceOffset']:
        raise ValueError('Forecourt paths require the same grounded road plane')
    if not config['sourceRefs'] or not set(config['sourceRefs']) <= source_ids:
        raise ValueError('Unknown forecourt source')
    if set(config['evidence']) != {'location', 'layout', 'dimensions', 'ground'} or not all(isinstance(s, str) and s.strip() for s in config['evidence'].values()):
        raise ValueError('Missing forecourt evidence')

    def point(p):
        if not isinstance(p, list) or len(p) != 2 or any(type(v) not in (int, float) or not math.isfinite(v) for v in p):
            raise ValueError('Invalid forecourt point')
        return p

    width = config['pathWidth']; offset = config['surfaceOffset']
    if type(width) not in (int, float) or not math.isfinite(width) or not .8 <= width <= 2.5:
        raise ValueError('Invalid forecourt path width')
    if type(offset) not in (int, float) or not math.isfinite(offset) or not .08 <= offset <= .2:
        raise ValueError('Invalid forecourt offset')
    center = point(config['center']); rx, ry = point(config['radii'])
    if not 3 <= min(rx, ry) <= max(rx, ry) <= 15 or min(rx, ry) <= width:
        raise ValueError('Invalid forecourt ring radii')
    boundary = Polygon([point(p) for p in config['boundary']])
    host = unary_union([Polygon(p[0], p[1:]) for p in building['polygons']])
    if not boundary.is_valid or not 50 <= boundary.area <= 1500 or not host.buffer(40).covers(boundary):
        raise ValueError('Invalid or remote forecourt boundary')
    ellipse = scale(Point(center).buffer(1, quad_segs=16), rx, ry, origin=tuple(center))
    loop = ellipse.boundary.buffer(width/2, quad_segs=4)
    branches = config['branches']
    if not isinstance(branches, list) or not 1 <= len(branches) <= 4:
        raise ValueError('Invalid forecourt branch count')
    road = surface_shape(surface)
    pieces = [loop]
    for points in branches:
        if not isinstance(points, list) or not 2 <= len(points) <= 4:
            raise ValueError('Invalid forecourt branch')
        line = LineString([point(p) for p in points])
        branch = line.buffer(width/2, cap_style=2, join_style=2)
        if not line.is_simple or not 1 <= line.length <= 30 or not branch.intersects(loop) or branch.intersection(road).area < .2:
            raise ValueError('Forecourt branch must connect ring to road')
        pieces.append(branch)
    paths = unary_union(pieces).difference(road)
    if paths.geom_type != 'Polygon' or not paths.is_valid or len(paths.interiors) != 1 or not boundary.covers(paths):
        raise ValueError('Forecourt paths must be bounded and retain one lawn island')
    for b in buildings:
        shape = unary_union([Polygon(p[0], p[1:]) for p in b['polygons']])
        if paths.distance(shape) < .2:
            raise ValueError('Forecourt paths intersect a building clearance')
    contact = paths.boundary.intersection(road.boundary.buffer(1e-7))
    if contact.length < len(branches)*width*.95:
        raise ValueError('Forecourt paths lack full-width road contacts')
    ring = list(road.exterior.coords)
    for edge in paving['joinEdges']:
        if contact.distance(LineString([ring[edge], ring[edge+1]])) <= paving['joinFeather']+.1:
            raise ValueError('Forecourt contact enters the road height transition')
    # Straight contact strips preserve vertices at the zero-burial edge.
    # Buffering the entire path can remove those collinear vertices and make
    # a triangulated overlap sink by the full burial depth at the seam.
    overlap = contact.simplify(1e-6).buffer(.12, cap_style=2, join_style=2).intersection(road)
    result = {**copy.deepcopy(config), 'pavingPolygon': list(paths.exterior.coords),
              'pavingHoles': [list(r.coords) for r in paths.interiors],
              'pavingMesh': triangulate(paths), 'gradingBounds': list(paths.buffer(.12).bounds),
              'joinOverlap': .12, 'joinBurial': .02,
              'seamPolygons': geometry_rings(overlap), 'seamMesh': triangulate(overlap),
              'contactLengthMeters': contact.length, 'areaMeters2': paths.area,
              'layer': 'roads', 'material': 'path'}
    return result, paths, paths
