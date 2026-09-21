"""Map unconfirmed entrance candidates without changing production data.

Edge indices refer to the original OSM ring, not the generated part rings.
Candidate edges and their lengths are diagnostic; they are not door anchors.
"""
import hashlib
import json
import math
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon

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
    report = {'buildingId': building['id'], 'sourceSha256': hashlib.sha256(raw).hexdigest(),
              'coordinateSystem': 'campus local east/north metres',
              'status': 'candidate-search-edges-only', 'productionReady': False,
              'sourceReview': 'docs/CIVIL_PLATFORM_ENTRY_EVIDENCE.md',
              'candidates': candidates, 'originalExteriorEdges': edges,
              'existingIllustrativeEntrances': building['form']['entrances'],
              'limitations': ['Boundary lengths are not measured entrance widths.',
                              'A/B are competing personnel-entry search areas, not confirmed doors.',
                              'C is the south delivery-entry search wall, not the personnel portal.',
                              'No road alignment, stairs, column count or door position is inferred.']}
    OUT.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    def point(p):
        return 100 + (p[0] + 740) * 6, 120 + (-705 - p[1]) * 6
    def path(points):
        return 'M ' + ' L '.join(f'{x:.2f},{y:.2f}' for x, y in map(point, points))
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="820" height="850" viewBox="0 0 820 850">',
           '<rect width="820" height="850" fill="#fafaf7"/>',
           '<g font-family="Arial,sans-serif" fill="#26323b">',
           '<text x="35" y="38" font-size="23">Platform: entrance search areas</text>',
           '<text x="35" y="67" font-size="15">Unregistered candidates; no production door anchors.</text>']
    for part in parts.values():
        svg.append(f'<path d="{path(part.exterior.coords)} Z" fill="#e2e6e8" stroke="#617581"/>')
    for c, color in zip(candidates, ['#b66827', '#4774a3', '#8b538b']):
        for index in c['originalEdges']:
            a, b = ring[index:index+2]
            x, y = point([(a[0]+b[0])/2, (a[1]+b[1])/2])
            nx, ny = edges[index]['outwardNormal']
            svg += [f'<path d="{path([a,b])}" fill="none" stroke="{color}" stroke-width="5"/>',
                    f'<text x="{x+nx*19:.2f}" y="{y-ny*19+5:.2f}" font-size="13" text-anchor="middle">{index}</text>']
    for entry in building['form']['entrances']:
        x, y = point(entry['center'])
        svg.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="6" fill="#26323b"/>')
    svg += ['<path d="M 695,205 L 695,125 M 687,140 L 695,125 L 703,140" fill="none" stroke="#26323b"/>',
            '<text x="687" y="112" font-size="20">N</text>',
            '<text x="35" y="675" font-size="16" fill="#b66827">A: West foyer perimeter, edges 3-9 (personnel candidate)</text>',
            '<text x="35" y="705" font-size="16" fill="#4774a3">B: North office wall, edge 13 (personnel candidate)</text>',
            '<text x="35" y="735" font-size="16" fill="#8b538b">C: South hall wall, edge 1 (delivery candidate)</text>',
            '<text x="35" y="770" font-size="15">Dot: existing illustrative entrance, still uncalibrated.</text>',
            '<text x="35" y="800" font-size="15">Numbers: original exterior edges; lengths are not door widths.</text>',
            '</g></svg>']
    OUT.with_suffix('.svg').write_text('\n'.join(svg) + '\n')
    print(json.dumps({'candidates': candidates, 'productionReady': False}))


if __name__ == '__main__':
    main()
