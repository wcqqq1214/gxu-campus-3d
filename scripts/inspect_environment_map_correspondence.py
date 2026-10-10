"""Check a historical building identity against neighboring map corners.

This is an image-space correspondence check, not a survey or a model writer.
Four agriculture corners fit one reflected similarity transform; all four
environment-building corners are held out. Original map pixels are top-left
based. Manual readings refer to the orange roof outlines, not their shadows.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MAP_HASH = 'f79d029e4eb3e36f829cc44331880e10b73dfe29e80c19142ddee728deabf63f'
AGRICULTURE = 'way/759185166'
ENVIRONMENT = 'way/759170251'
# Read on a 4x inspection crop whose original top-left pixel is (1320, 1490).
CONTROL_INDICES = [14, 15, 4, 5]
CONTROL_PIXELS = np.array([[1356.75, 1582.5], [1347.75, 1535.25],
                           [1454.5, 1512.0], [1465.75, 1559.0]])
CHECK_PIXELS = np.array([[1469.75, 1612.75], [1472.5, 1624.25],
                         [1380.5, 1645.0], [1377.75, 1633.0]])


def fit(points, pixels):
    rows, values = [], []
    for (x, y), (u, v) in zip(points, pixels):
        rows.extend([[x, y, 1, 0], [-y, x, 0, 1]])
        values.extend([u, v])
    return np.linalg.lstsq(rows, values, rcond=None)[0]


def project(points, coefficients):
    a, b, tx, ty = coefficients
    return np.asarray(points) @ np.array([[a, b], [b, -a]]) + [tx, ty]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--map', type=Path, default=ROOT/'work/refinement-s3-neighbor-current/map2019-official.jpg')
    parser.add_argument('--buildings', type=Path, default=ROOT/'public/data/buildings.json')
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--diagram', type=Path, required=True)
    args = parser.parse_args()
    if hashlib.sha256(args.map.read_bytes()).hexdigest() != MAP_HASH:
        raise ValueError('Map hash differs: re-read the manual corner observations')
    buildings = {b['id']: b for b in json.loads(args.buildings.read_text())}
    agriculture = np.asarray(buildings[AGRICULTURE]['polygons'][0][0][:-1])
    environment = np.asarray(buildings[ENVIRONMENT]['polygons'][0][0][:-1])
    if len(agriculture) != 20 or len(environment) != 4:
        raise ValueError('Footprint topology changed: re-identify corner indices')
    coefficients = fit(agriculture[CONTROL_INDICES], CONTROL_PIXELS)
    predicted = project(environment, coefficients)
    control_errors = np.linalg.norm(project(agriculture[CONTROL_INDICES], coefficients)-CONTROL_PIXELS, axis=1)
    check_errors = np.linalg.norm(predicted-CHECK_PIXELS, axis=1)
    # 5 original image pixels is a coarse identity gate, not metric accuracy.
    limit = 5.0
    wrong_corner_errors = np.linalg.norm(predicted-np.roll(CHECK_PIXELS, 1, axis=0), axis=1)
    passed = bool(max(control_errors) <= limit and max(check_errors) <= limit)
    report = {
        'baselineCommit': 'c3a10aa', 'mapSha256': MAP_HASH,
        'mapUrl': 'https://www.gxu.edu.cn/images/18/2019ght.jpg',
        'imageSize': [2048, 2552], 'method': 'four-parameter-reflected-similarity',
        'coefficientsABTxTy': coefficients.tolist(),
        'formula': 'u=a*x+b*y+tx; v=b*x-a*y+ty',
        'controlBuildingId': AGRICULTURE, 'targetBuildingId': ENVIRONMENT,
        'controlVertexIndices': CONTROL_INDICES,
        'controlModelXY': agriculture[CONTROL_INDICES].tolist(),
        'controlImagePixels': CONTROL_PIXELS.tolist(),
        'controlResidualPixels': control_errors.tolist(),
        'heldOutModelXY': environment.tolist(),
        'heldOutObservedPixels': CHECK_PIXELS.tolist(),
        'heldOutPredictedPixels': predicted.tolist(),
        'heldOutResidualPixels': check_errors.tolist(),
        'coarseIdentityLimitPixels': limit, 'passed': passed,
        'wrongCyclicCornerOrder': {'maximumResidualPixels': float(max(wrong_corner_errors)),
                                  'rejected': bool(max(wrong_corner_errors) > limit)},
        'productionReady': False,
        'limitations': [
            'Manual orange-roof readings; shadows excluded. Picking uncertainty approximately 2 original pixels, not independently measured.',
            'Only one adjacent building supplies fitting controls; target is nearby extrapolation. Target corners are not used in fitting.',
            'Historical illustrative roof outlines are compared with OSM footprints. Residuals do not establish survey accuracy or a current cadastral boundary.',
            'Location correspondence does not locate the photograph camera, entrance, rooftop pavilion or external stairs.',
        ],
    }
    if not passed or not report['wrongCyclicCornerOrder']['rejected']:
        raise ValueError(f'Correspondence checks failed: {report}')
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')

    def coordinates(points):
        # Explicit closing point also renders correctly in PDF/SVG converters.
        closed = list(points) + [points[0]]
        return ' '.join(f'{(x-1320)*4:.2f},{(y-1490)*4:.2f}' for x, y in closed)

    svg = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 770">',
           '<rect width="760" height="770" fill="#fff"/>',
           '<g font-family="sans-serif" font-size="16">',
           '<text x="20" y="30">Historical map correspondence (4x image pixels)</text>',
           f'<polygon points="{coordinates(project(agriculture, coefficients))}" fill="#eee" stroke="#777"/>',
           f'<polygon points="{coordinates(CHECK_PIXELS)}" fill="none" stroke="#da780a" stroke-width="3"/>',
           f'<polygon points="{coordinates(predicted)}" fill="none" stroke="#1670b6" stroke-width="2"/>']
    for label, points in [('A', CONTROL_PIXELS), ('E', CHECK_PIXELS)]:
        for i, (x, y) in enumerate(points):
            x, y = (x-1320)*4, (y-1490)*4
            svg += [f'<circle cx="{x}" cy="{y}" r="4" fill="#333"/>',
                    f'<text x="{x+8}" y="{y-8}">{label}{i+1}</text>']
    svg += ['<text x="20" y="685">A: fit controls on agriculture; E: held-out environment corners</text>',
            '<text x="20" y="712" fill="#da780a">Orange: map observations</text>',
            '<text x="20" y="738" fill="#1670b6">Blue: predicted OSM outline; not a surveyed boundary</text>',
            '</g></svg>']
    args.diagram.parent.mkdir(parents=True, exist_ok=True)
    args.diagram.write_text('\n'.join(svg)+'\n')
    print(json.dumps({'passed': passed, 'controlMaxPixels': float(max(control_errors)),
                      'heldOutMaxPixels': float(max(check_errors))}))


if __name__ == '__main__':
    main()
