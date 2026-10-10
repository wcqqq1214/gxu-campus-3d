"""Independent bidirectional projected coverage and attributes for an export candidate.

Consumes the NPZ pair emitted by --planar-candidate-directory. Requires NumPy
and Shapely; does not import the simplifier or use its patch classifications.
This checks source geometry, not Draco output or browser performance.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree


def read(path):
    with np.load(path) as data:
        result = {key: data[key] for key in data.files}
    result['points'] = result['vertices'][result['triangles']]
    result['keys'] = []
    result['polygons'] = []
    for triangle, uv, normals, material in zip(result['points'], result['uvs'], result['normals'], result['materials']):
        corners = [(tuple(p), tuple(u), tuple(n)) for p, u, n in zip(triangle, uv, normals)]
        result['keys'].append((int(material), min(tuple(corners[k:]+corners[:k]) for k in range(3))))
        result['polygons'].append(Polygon(triangle[:, :2]))
    return result


def interpolate(points, values, query):
    ab, ac = points[1, :2]-points[0, :2], points[2, :2]-points[0, :2]
    d = query-points[0, :2]
    det = ab[0]*ac[1]-ab[1]*ac[0]
    u = (d[:, 0]*ac[1]-d[:, 1]*ac[0])/det
    v = (ab[0]*d[:, 1]-ab[1]*d[:, 0])/det
    return values[0]+u[:, None]*(values[1]-values[0])+v[:, None]*(values[2]-values[0])


def read_decoded(path):
    raw = json.loads(path.read_text())
    data = {k: np.array(raw[k]) for k in ('vertices', 'triangles', 'uvs', 'normals')}
    data['points'] = data['vertices'][data['triangles']]
    for key in ('uvs', 'normals'):
        data[key] = data[key][data['triangles']]
    data['materials'] = np.zeros(len(data['triangles']), dtype=int)
    data['polygons'] = [Polygon(p[:, :2]) for p in data['points']]
    data['keys'] = [min(tuple(map(tuple, np.roll(p, k, axis=0))) for k in range(3)) for p in data['points']]
    data['modelSHA256'], data['material'] = raw['modelSHA256'], raw['material']
    return data


def check(source, target, *, height_tolerance=.0002, uv_tolerance=1e-9, normal_tolerance=.001):
    tree = STRtree(target['polygons'])
    unchanged = Counter(target['keys'])
    failures, changed = [], 0
    maximum_height = maximum_uv = maximum_normal = uncovered = 0.
    for i, (points, key, poly) in enumerate(zip(source['points'], source['keys'], source['polygons'])):
        if unchanged[key]:
            unchanged[key] -= 1
            continue
        changed += 1
        if np.cross(points[1]-points[0], points[2]-points[0])[2] <= 0:
            failures.append({'face': i, 'reason': 'changed vertical, reversed or zero-area face'})
            continue
        covered = []
        for j in tree.query(poly, predicate='intersects'):
            if source['materials'][i] != target['materials'][j] or target['polygons'][j].area == 0:
                continue
            cut = poly.intersection(target['polygons'][j])
            parts = [cut] if cut.geom_type == 'Polygon' else [g for g in getattr(cut, 'geoms', []) if g.geom_type == 'Polygon']
            for part in parts:
                if part.area == 0:
                    continue
                q = np.array(part.exterior.coords)
                a = np.column_stack((points[:, 2], source['uvs'][i], source['normals'][i]))
                b = np.column_stack((target['points'][j, :, 2], target['uvs'][j], target['normals'][j]))
                error = np.abs(interpolate(points, a, q)-interpolate(target['points'][j], b, q))
                h, uv, normal = error[:, 0].max(), error[:, 1:3].max(), np.linalg.norm(error[:, 3:], axis=1).max()
                if h <= height_tolerance and uv <= uv_tolerance and normal <= normal_tolerance:
                    covered.append(part)
                    maximum_height = max(maximum_height, float(h))
                    maximum_uv = max(maximum_uv, float(uv))
                    maximum_normal = max(maximum_normal, float(normal))
        loss = poly.difference(unary_union(covered)).area if covered else poly.area
        uncovered += loss
        # GEOS clipping round-off, independent of height/attribute thresholds.
        if loss > max(1e-9, poly.area*1e-8):
            failures.append({'face': i, 'area': poly.area, 'uncovered': loss})
    return {'changedFaces': changed, 'failedFaces': len(failures), 'failures': failures,
            'uncoveredAreaMetres2': uncovered, 'maximumHeightErrorMetres': maximum_height,
            'maximumUVError': maximum_uv, 'maximumNormalError': maximum_normal,
            'passed': not failures}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path)
    parser.add_argument('--decoded-before', type=Path)
    parser.add_argument('--decoded-after', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    decoded = args.decoded_before is not None or args.decoded_after is not None
    if decoded:
        if args.directory or not (args.decoded_before and args.decoded_after):
            parser.error('Use either --directory or both --decoded-before and --decoded-after')
        paths = [args.decoded_before, args.decoded_after]
    else:
        if not args.directory:
            parser.error('--directory is required for source validation')
        paths = [args.directory / name for name in ('original.npz', 'candidate.npz')]
    fingerprints = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    old, new = map(read_decoded if decoded else read, paths)
    tolerance = .0002
    uv_tolerance, normal_tolerance = 1e-9, .001
    if decoded:
        if old['material'] != new['material']:
            raise ValueError('Terrain material changed')
        # One existing 18-bit position grid step plus the independent source
        # plane bound. This does not relax source, paving or foundation checks.
        position_step = np.ptp(old['vertices'], axis=0).max()/((1 << 18)-1)
        tolerance += position_step
        uv_step = np.ptp(old['uvs'].reshape(-1, 2), axis=0).max()/((1 << 18)-1)
        uv_tolerance = position_step/4+uv_step
        # Octahedral normal decoding has Lipschitz bound 3 on each folded
        # region; allow two independent 6-bit roundings plus the source bound.
        normal_tolerance += 6*np.sqrt(2)/((1 << 6)-2)
    options = dict(height_tolerance=tolerance, uv_tolerance=uv_tolerance, normal_tolerance=normal_tolerance)
    results = {'originalToCandidate': check(old, new, **options),
               'candidateToOriginal': check(new, old, **options)}
    if fingerprints != {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}:
        raise RuntimeError('Inputs changed during validation; discard this run')
    report = {'scope': ('Decoded coverage, height, UV and normals under existing quantization bounds; visual checks remain separate.'
                        if decoded else 'Source geometry, UV and normals; Draco and browser acceptance remain separate.'),
              'heightToleranceMetres': tolerance,
              'uvTolerance': uv_tolerance, 'normalTolerance': normal_tolerance,
              'sha256': fingerprints,
              'originalFaces': len(old['triangles']), 'candidateFaces': len(new['triangles']),
              'results': results, 'passed': all(r['passed'] for r in results.values())}
    if decoded:
        report['modelSHA256'] = {'before': old['modelSHA256'], 'after': new['modelSHA256']}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False))
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
