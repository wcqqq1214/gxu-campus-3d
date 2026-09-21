"""Propose bounded parts for the existing civil-platform footprint, without edits.

The aerial supports different masses; partition lines follow existing OSM corners
and remain estimates. No photograph pixels are treated as metric measurements.
"""
import hashlib
import json
from pathlib import Path

from shapely.geometry import LineString, Polygon
from shapely.ops import split, unary_union

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'public/data/buildings.json'
OUT = ROOT / 'docs/model-checks/refinement/s2-civil-platform-parts-proposal'


def extended(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    return LineString([(a[0] - 100 * dx, a[1] - 100 * dy),
                       (b[0] + 100 * dx, b[1] + 100 * dy)])


def main():
    raw = SOURCE.read_bytes()
    building = next(b for b in json.loads(raw) if b['id'] == 'way/957404988')
    assert len(building['polygons']) == 1 and len(building['polygons'][0]) == 1
    ring = building['polygons'][0][0]
    original = Polygon(ring)
    # Retain the straight north and south wings. Derive cuts from their own
    # corners, not from an arbitrary axis-aligned search rectangle.
    north_cut = extended(ring[11], ring[12])
    south_cut = extended(ring[0], ring[15])
    west_cut = extended(ring[3], ring[10])
    first = sorted(split(original, north_cut).geoms, key=lambda p: p.centroid.y)
    assert len(first) == 2
    remaining, north = first
    second = sorted(split(remaining, south_cut).geoms, key=lambda p: p.centroid.y)
    assert len(second) >= 2
    south = second[0]
    # The curved west entrance projects south of the hall's north wall. Keep
    # that detached cut fragment with the entrance, not with the hall.
    middle = unary_union(second[1:])
    sides = sorted(split(middle, west_cut).geoms, key=lambda p: p.centroid.x)
    assert len(sides) == 2
    west, east = sides
    # Overlay roundoff can leave a zero-width tail on the hall's north edge.
    # Reconstruct the same partition from shared cut intersections and exact
    # mapped vertices so facade anchors retain a single continuous wall.
    q = list(LineString([ring[2], ring[3]]).intersection(south_cut).coords)[0]
    m = list(west_cut.intersection(south_cut).coords)[0]
    n = list(LineString([ring[14], ring[15]]).intersection(north_cut).coords)[0]
    clean = [Polygon([ring[0], ring[1], ring[2], q, ring[15]]),
             Polygon([ring[15], n, ring[11], ring[10], m]),
             Polygon([*ring[3:11], m, q]),
             Polygon([*ring[11:15], n])]
    assert all(a.symmetric_difference(b).area < 1e-7
               for a, b in zip([south, east, west, north], clean))
    south, east, west, north = clean
    parts = [('south-hall', south), ('middle-labs', east),
             ('west-foyer', west), ('north-office', north)]
    union = unary_union([p for _, p in parts])
    gaps = original.symmetric_difference(union).area
    overlaps = sum(a.intersection(b).area for i, (_, a) in enumerate(parts)
                   for _, b in parts[i + 1:])
    assert all(p.is_valid and p.area > 1 for _, p in parts)
    assert gaps < 1e-7 and overlaps < 1e-7
    report = {
        'status': 'estimated-partition-proposal-not-production-geometry',
        'buildingId': building['id'], 'sourceSha256': hashlib.sha256(raw).hexdigest(),
        'coordinateSystem': 'campus local east/north metres',
        'sourceAreaM2': original.area, 'symmetricDifferenceM2': gaps,
        'overlapM2': overlaps, 'topologyPassed': True,
        'productionReady': False,
        'cutsFromOriginalVertexPairs': {'north': [11, 12], 'south': [0, 15], 'west': [3, 10]},
        'sourceReview': 'docs/CIVIL_LAB_IDENTIFICATION.md',
        'parts': [{'id': name, 'areaM2': p.area,
                   'polygon': [list(point) for point in p.exterior.coords],
                   'heightM': None,
                   'levels': 9 if name == 'north-office' else None,
                   'basis': 'Nine-storey north office from 2014 school newspaper; part boundaries estimated from retained OSM corners.' if name == 'north-office' else 'Visible separate mass in school aerial; exact level count and height require part-specific interpretation.'}
                  for name, p in parts],
        'limitations': ['Topology check does not validate source-photo registration, dimensions or height.',
                       'No new building ID; hall, labs, foyer and office belong to the existing compound.',
                       'Old hall in the 2022 demolition inventory is a different historical building.',
                       'Do not apply the three-level map label as three complete floors through a high-bay experimental hall.'],
    }
    OUT.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    colors = ['#74a6bd', '#d9bc82', '#a4bea3', '#acabd0']
    labels = ['South experimental hall', 'Small laboratories (candidate)', 'Entrance/connection (candidate)', 'North office: 9 levels in 2014 design']
    def point(p):
        return 75 + (p[0] + 740) * 6, 105 + (-705 - p[1]) * 6
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="850" height="780" viewBox="0 0 850 780">',
           '<rect width="850" height="780" fill="#fafaf7"/>',
           '<g font-family="Arial,sans-serif" fill="#26323b">',
           '<text x="40" y="38" font-size="23">Civil platform: proposed massing parts</text>',
           '<text x="40" y="67" font-size="15">Estimated cuts within one existing footprint; heights not assigned.</text>']
    for i, ((name, poly), color) in enumerate(zip(parts, colors), 1):
        coords = [point(p) for p in poly.exterior.coords]
        d = 'M ' + ' L '.join(f'{x:.2f},{y:.2f}' for x, y in coords) + ' Z'
        x, y = point(poly.representative_point().coords[0])
        svg += [f'<path d="{d}" fill="{color}" stroke="#40535d" stroke-width="1.5"/>',
                f'<text x="{x:.2f}" y="{y:.2f}" font-size="21" text-anchor="middle">{i}</text>',
                f'<rect x="40" y="{645+(i-1)*26}" width="15" height="15" fill="{color}"/>',
                f'<text x="67" y="{658+(i-1)*26}" font-size="15">{i}. {labels[i-1]}</text>']
    svg += ['<path d="M 680,210 L 680,130 M 672,145 L 680,130 L 688,145" stroke="#26323b" fill="none"/>',
            '<text x="673" y="118" font-size="20">N</text>',
            '<path d="M 630,570 L 750,570 M 630,565 L 630,575 M 750,565 L 750,575" stroke="#26323b"/>',
            '<text x="668" y="596" font-size="15">20 m</text>',
            '</g></svg>']
    OUT.with_suffix('.svg').write_text('\n'.join(svg) + '\n')
    print(json.dumps({'parts': {name: round(p.area, 3) for name, p in parts},
                      'symmetricDifferenceM2': gaps, 'overlapM2': overlaps}))


if __name__ == '__main__':
    main()
