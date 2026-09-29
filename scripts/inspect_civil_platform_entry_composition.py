"""Read-only composition audit; photo interpretation is explicit, not a camera fit."""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ID = 'way/957404988'


def inspect(root=ROOT):
    path = root / 'public/data/buildings.json'
    building = next(b for b in json.loads(path.read_text()) if b['id'] == ID)
    parts = {p['id']: p for p in building['form']['parts']}
    portico = parts['link-portico']
    entry = next(e for e in building['form']['entrances'] if e.get('porticoId') == 'link-portico')
    angle = math.radians(entry['bearing'])
    normal = (math.sin(angle), math.cos(angle))
    tangent = (normal[1], -normal[0])
    front = entry['outerCenter']
    columns = portico['openBelow']['columns']
    coordinates = []
    for c in columns:
        delta = [c['center'][i] - front[i] for i in (0, 1)]
        coordinates.append({'center': c['center'],
                            'alongMeters': sum(delta[i] * tangent[i] for i in (0, 1)),
                            'setbackMeters': -sum(delta[i] * normal[i] for i in (0, 1))})
    rows = []
    for c in sorted(coordinates, key=lambda c: c['setbackMeters']):
        if not rows or abs(c['setbackMeters'] - rows[-1]) > .02:
            rows.append(c['setbackMeters'])
    roof_rings = portico['polygons']
    report = {
        'status': 'needs-photo-composition-review',
        'buildingId': ID,
        'calculationPassed': True,
        'scope': 'Current D portico composition versus manually reviewed wide photograph; no automatic image measurement or registration.',
        'model': {'columns': coordinates, 'columnCount': len(columns),
                  'depthRowsAtTwoCentimeterTolerance': len(rows), 'rowSetbacksMeters': rows,
                  'porticoRoofType': portico['roof']['type'],
                  'slattedRoofConfigured': 'slattedRoof' in portico['openBelow'],
                  'porticoRoofRingCount': sum(len(p) for p in roof_rings),
                  'doorCenter': entry['center'], 'outerCenter': front,
                  'entryRecessMeters': entry['recess']},
        'photoObservation': {
            'source': 'https://tmjz.gxu.edu.cn/info/1452/6575.htm',
            'image': 'https://tmjz.gxu.edu.cn/__local/B/11/E5/A12DDA85D1E7598DA582B485BE1_12A98A97_61751.png',
            'method': 'Direct human visual interpretation of the full 855 by 570 image, not a surveyed count.',
            'visibleRoundColumnsAtLeast': 4,
            'visibleDepthRowsAtLeast': 2,
            'sideSlattedRoofVisible': True,
            'namedFrontFasciaAppearsCurved': True,
            'centralUpperGlazingFramedByStoneBeamAndPiers': True,
            'exactTotalColumns': None, 'metricDimensions': None,
        },
        'mismatches': [],
        'photoRegistrationAccepted': False,
        'productionChangeReady': False,
        'wholeBuildingAccepted': False,
        'limitations': [
            'The OSM entrance node supports the D area but does not resolve column rows, canopy shape or doorway dimensions.',
            'A curved fascia in perspective alone does not establish the A west outline as the photographed location.',
            'Visible front/rear columns do not establish the total count or depth without a geometric photo fit.',
            'Indoor hall openings have not been registered to the C south wall or proven to be separate doors.',
        ],
        'buildingSha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    if len(rows) < 2:
        report['mismatches'].append('The modeled columns form one depth row; the photograph shows front and rear columns.')
    if not report['model']['slattedRoofConfigured']:
        report['mismatches'].append('The modeled solid portico roof has no side grille openings visible in the photograph.')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'docs/model-checks/refinement/s2-platform-wide-entry-composition.json')
    args = parser.parse_args()
    report = inspect()
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['status', 'mismatches', 'photoRegistrationAccepted']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
