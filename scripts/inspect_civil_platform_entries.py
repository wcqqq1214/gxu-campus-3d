"""Map unconfirmed entrance candidates without changing production data.

Original edge indices and part-local edge indices are kept separate.
Candidate edges and their lengths are diagnostic; they are not door anchors.
"""
import copy
import gzip
import hashlib
import json
import math
from pathlib import Path

from shapely.affinity import rotate, translate
from shapely.geometry import LineString, Point, Polygon, box

from building_overrides import resolve_building, source_catalogue

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'public/data/buildings.json'
OUT = ROOT / 'docs/model-checks/refinement/s2-platform-entry-candidates'


def main():
    raw = SOURCE.read_bytes()
    building = next(b for b in json.loads(raw) if b['id'] == 'way/957404988')
    ring = building['polygons'][0][0]
    assert len(building['polygons']) == 1 and len(building['polygons'][0]) == 1
    assert len(ring) == 17 and ring[0] == ring[-1], 'Recheck candidates after footprint changes'
    footprint = Polygon(ring)
    assert footprint.is_valid
    parts = {p['id']: Polygon(p['polygons'][0][0]) for p in building['form']['parts']}
    groups = [('A', 'west-foyer', list(range(3, 10))),
              ('B', 'north-office', [13]), ('C', 'south-hall', [1])]
    signed_area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:]))
    edges = []
    for index, (a, b) in enumerate(zip(ring, ring[1:])):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        sign = 1 if signed_area < 0 else -1
        normal = [-dy / length * sign, dx / length * sign]
        center = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]
        assert not footprint.covers(Point(center[0] + normal[0] * .01,
                                          center[1] + normal[1] * .01))
        edges.append({'originalEdge': index, 'start': a, 'end': b,
                      'lengthM': length, 'outwardNormal': normal})
    candidates = []
    for label, part, indices in groups:
        for index in indices:
            line = LineString([ring[index], ring[index + 1]])
            assert line.difference(parts[part].boundary.buffer(1e-7)).length < 1e-6
        candidates.append({'label': label, 'part': part, 'originalEdges': indices,
                           'boundaryLengthM': sum(edges[i]['lengthM'] for i in indices),
                           'photoRegistered': False, 'doorAnchor': None})
    # The six-part model has an open portico. Its outer roof edge is not the
    # recessed wall on which a personnel door would need to be registered.
    assert len(parts) == 6, 'Recheck candidates after part repartition'
    foyer_ring = list(parts['link-foyer'].exterior.coords)
    portico_ring = list(parts['link-portico'].exterior.coords)
    wall = LineString(foyer_ring[:2])
    outer = LineString(portico_ring[2:4])
    assert wall.difference(parts['link-portico'].boundary.buffer(1e-7)).length < 1e-6
    assert outer.difference(footprint.boundary.buffer(1e-7)).length < 1e-6
    assert outer.difference(LineString([ring[14], ring[15]]).buffer(1e-7)).length < 1e-6
    a, b = foyer_ring[:2]
    dx, dy = b[0] - a[0], b[1] - a[1]
    normal = [dy / wall.length, -dx / wall.length]
    midpoint = wall.interpolate(.5, normalized=True)
    assert parts['link-foyer'].exterior.is_ccw
    assert parts['link-portico'].contains(Point(midpoint.x + normal[0] * .01,
                                               midpoint.y + normal[1] * .01))
    candidates.append({
        'label': 'D', 'part': 'link-foyer', 'originalEdges': [],
        'partLocalWallEdge': {'polygon': 0, 'ring': 0, 'edge': 0,
                             'start': a, 'end': b, 'outwardNormal': normal},
        'boundaryLengthM': wall.length,
        'porticoOuterEdge': {'part': 'link-portico', 'polygon': 0, 'ring': 0, 'edge': 2,
                            'originalEdge': 14, 'start': portico_ring[2],
                            'end': portico_ring[3], 'lengthM': outer.length},
        'wallToOuterEdgeAtMidpointM': midpoint.distance(outer),
        'photoRegistered': False, 'doorAnchor': None,
        'note': 'Search wall behind the open portico; roof edge is not a door anchor.'})
    snapshot = ROOT / 'data/snapshots/osm-2026-09-09.json.gz'
    with gzip.open(snapshot) as source:
        elements = json.load(source)['elements']
    node = next(e for e in elements if e['type'] == 'node' and e['id'] == 7096023516)
    way = next(e for e in elements if e['type'] == 'way' and e['id'] == 957404988)
    assert node['tags']['entrance'] == 'yes' and node['id'] in way['nodes']
    lon, lat = json.loads((ROOT / 'data/region.json').read_text())['center']
    mapped = Point((node['lon'] - lon) * 111320 * math.cos(math.radians(lat)),
                   (node['lat'] - lat) * 111320)
    original_edge = LineString([ring[14], ring[15]])
    # Normalization removed this nearly collinear tagged node. Retain its raw
    # coordinates and report the tiny projection offset, rather than hiding it.
    assert original_edge.distance(mapped) < .01
    front = original_edge.interpolate(original_edge.project(mapped))
    rear = wall.interpolate(wall.project(front))
    route = LineString([front, rear])
    assert outer.distance(front) < 1e-6
    portico = next(p for p in building['form']['parts'] if p['id'] == 'link-portico')
    supports = []
    for index, column in enumerate(portico['openBelow']['columns']):
        support = translate(rotate(box(-column['width']/2, -column['depth']/2,
                                       column['width']/2, column['depth']/2),
                                   column['angle'], use_radians=True), *column['center'])
        supports.append({'columnIndex': index, 'center': column['center'],
                         'distanceToRouteM': route.distance(support),
                         'blocksCentralRoute': route.buffer(.6).intersects(support)})
    record = copy.deepcopy(json.loads((ROOT / 'data/building-overrides.json').read_text())
                           ['buildings'][building['id']])
    record['entrances'] = [{'id': 'osm-entry-probe', 'polygon': 0, 'ring': 0, 'edge': 14,
                            't': original_edge.project(front, normalized=True),
                            'width': 2.2, 'primary': True, 'recess': 3.6}]
    record['evidence']['entrances'] = {
        'status': 'estimated', 'sourceRefs': ['osm'],
        'note': 'Diagnostic only: mapped point with existing 3.6 m recess and arbitrary 2.2 m probe width.'}
    try:
        resolve_building(building, record, {s['id'] for s in source_catalogue()})
        rejection = None
    except ValueError as error:
        rejection = str(error)
    blocked = any(s['blocksCentralRoute'] for s in supports)
    mapped_entry = {
        'nodeId': node['id'], 'sourceUrl': 'https://www.openstreetmap.org/node/7096023516',
        'snapshot': str(snapshot.relative_to(ROOT)),
        'snapshotSha256': hashlib.sha256(snapshot.read_bytes()).hexdigest(),
        'nodeVersion': node['version'], 'nodeTimestamp': node['timestamp'],
        'tags': node['tags'], 'longitude': node['lon'], 'latitude': node['lat'],
        'rawLocalPosition': list(mapped.coords[0]), 'originalEdge': 14,
        'edgeFraction': original_edge.project(front, normalized=True),
        'distanceToNormalizedEdgeM': original_edge.distance(mapped),
        'projectedOuterPosition': list(front.coords[0]),
        'projectedRearWallPosition': list(rear.coords[0]),
        'modelRecessM': route.length, 'preferredSearchArea': 'D',
        'columnClearance': supports, 'probeWidthM': 2.2,
        'probePurpose': 'Exercise existing parser only; not a proposed or measured doorway width.',
        'candidateParserRejection': rejection,
        'centralApproachClear': not blocked,
        'locationAccuracy': 'Unspecified OSM mapping accuracy; no surveyed or photo-registered door anchor.'}
    report = {'buildingId': building['id'], 'sourceSha256': hashlib.sha256(raw).hexdigest(),
              'coordinateSystem': 'campus local east/north metres',
              'status': 'mapped-entrance-and-portico-constraint-review', 'productionReady': False,
              'sourceReview': 'docs/CIVIL_PLATFORM_ENTRY_EVIDENCE.md',
              'candidates': candidates, 'originalExteriorEdges': edges,
              'mappedEntranceEvidence': mapped_entry,
              'existingIllustrativeEntrances': building['form']['entrances'],
              'limitations': ['Boundary lengths are not measured entrance widths.',
                              'D is prioritized by an OSM entrance node; A/B remain unregistered alternatives or other doors.',
                              'C is the south delivery-entry search wall, not the personnel portal.',
                              'D is a part-local recessed wall; its normal enters the open portico.',
                              ('OSM node supports D; existing estimated columns conflict with its straight approach.'
                               if blocked else 'Mapped central approach is clear; doorway and stairs are still uncalibrated.'),
                              'No road alignment, stairs, column count or door position is inferred.']}
    OUT.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    def point(p):
        return 100 + (p[0] + 740) * 6, 120 + (-705 - p[1]) * 6
    def path(points):
        return 'M ' + ' L '.join(f'{x:.2f},{y:.2f}' for x, y in map(point, points))
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="820" height="910" viewBox="0 0 820 910">',
           '<rect width="820" height="910" fill="#fafaf7"/>',
           '<g font-family="Arial,sans-serif" fill="#26323b">',
           '<text x="35" y="38" font-size="23">Platform: entrance search areas</text>',
           '<text x="35" y="67" font-size="15">OSM entry supports D; production door placement remains unresolved.</text>']
    for part in parts.values():
        svg.append(f'<path d="{path(part.exterior.coords)} Z" fill="#e2e6e8" stroke="#617581"/>')
    for c, color in zip(candidates, ['#b66827', '#4774a3', '#8b538b']):
        for index in c['originalEdges']:
            a, b = ring[index:index+2]
            x, y = point([(a[0]+b[0])/2, (a[1]+b[1])/2])
            nx, ny = edges[index]['outwardNormal']
            svg += [f'<path d="{path([a,b])}" fill="none" stroke="{color}" stroke-width="5"/>',
                    f'<text x="{x+nx*19:.2f}" y="{y-ny*19+5:.2f}" font-size="13" text-anchor="middle">{index}</text>']
    svg += [f'<path d="{path(wall.coords)}" fill="none" stroke="#167a67" stroke-width="5"/>',
            f'<path d="{path(outer.coords)}" fill="none" stroke="#167a67" stroke-width="2" stroke-dasharray="6 5"/>']
    x, y = point(midpoint.coords[0])
    svg.append(f'<text x="{x-18:.2f}" y="{y:.2f}" font-size="15" fill="#167a67">D</text>')
    route_color = '#a22c3c' if blocked else '#167a67'
    svg.append(f'<path d="{path(route.coords)}" fill="none" stroke="{route_color}" stroke-width="3"/>')
    for support in supports:
        x, y = point(support['center'])
        color = '#a22c3c' if support['blocksCentralRoute'] else '#617581'
        svg.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="{color}"/>')
    x, y = point(mapped.coords[0])
    svg += [f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" fill="{route_color}"/>',
            f'<text x="{x+12:.2f}" y="{y+5:.2f}" font-size="13" fill="{route_color}">OSM entry 7096023516</text>']
    for entry in building['form']['entrances']:
        x, y = point(entry['center'])
        svg.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="6" fill="#26323b"/>')
    svg += ['<path d="M 695,205 L 695,125 M 687,140 L 695,125 L 703,140" fill="none" stroke="#26323b"/>',
            '<text x="687" y="112" font-size="20">N</text>',
            '<text x="35" y="675" font-size="16" fill="#b66827">A: West foyer perimeter, edges 3-9 (personnel candidate)</text>',
            '<text x="35" y="705" font-size="16" fill="#4774a3">B: North office wall, edge 13 (personnel candidate)</text>',
            '<text x="35" y="735" font-size="16" fill="#8b538b">C: South hall wall, edge 1 (delivery candidate)</text>',
            '<text x="35" y="765" font-size="16" fill="#167a67">D: Recessed link-foyer east wall (personnel candidate)</text>',
            '<text x="35" y="795" font-size="15" fill="#167a67">Dashed: portico outer roof edge; no wall or door inferred.</text>',
            '<text x="35" y="815" font-size="15">Entry route: red if blocked, green if clear; neither confirms a door.</text>',
            '<text x="35" y="840" font-size="15">Black dot: existing illustrative entrance, still uncalibrated.</text>',
            '<text x="35" y="865" font-size="15">Numbers: original exterior edges; D uses a part-local wall.</text>',
            '<text x="35" y="890" font-size="15">All lengths are model search boundaries, not measured door widths.</text>',
            '</g></svg>']
    OUT.with_suffix('.svg').write_text('\n'.join(svg) + '\n')
    print(json.dumps({'candidates': candidates, 'productionReady': False}))


if __name__ == '__main__':
    main()
