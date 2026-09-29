"""Record a source-review conflict without inventing replacement geometry.

Photo interpretation is manual, not a fitted camera or a metric measurement.
This diagnostic compares that stated relationship with actual production edges.
"""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/model-checks/refinement/s2-platform-alignment-review'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = ROOT / 'public/data/buildings.json'
    building = next(b for b in json.loads(source.read_text()) if b['id'] == 'way/957404988')
    facades = building['form']['facades']
    corrected = any(p['id'] == 'north-low-wing' for p in building['form']['parts'])
    out = OUT.with_name('s2-platform-alignment-current') if corrected else OUT
    hall = next(f for f in facades if f['part'] == 'south-hall' and
                (f.get('adjacentPart') == 'north-low-wing' if corrected else f['edge'] == 15))
    low = next(f for f in facades if f['part'] == ('north-low-wing' if corrected else 'middle-labs')
               and f['edge'] == (15 if corrected else 14))

    def edge_record(face):
        a, b = face['start'], face['end']
        return {'part': face['part'], 'originalEdge': face['edge'],
                'start': a, 'end': b, 'lengthMeters': math.dist(a, b),
                'axisDegreesFromEastModulo180': math.degrees(math.atan2(b[1]-a[1], b[0]-a[0])) % 180}

    hall, low = edge_record(hall), edge_record(low)
    difference = abs(hall['axisDegreesFromEastModulo180'] - low['axisDegreesFromEastModulo180'])
    difference = min(difference, 180-difference)
    report = {
        'reviewedAt': '2026-09-29', 'buildingId': building['id'],
        'productionBuildingsSHA256': sha(source),
        'coordinateSystem': 'Campus local x east, y north; metres; not scene x/y/z',
        'hallNorthFace': hall, 'currentlyAssignedLowWingFace': low,
        'productionUndirectedAxisDifferenceDegrees': difference,
        'manualSourceObservation': 'The dense-window low wing follows the hall long front in the 2014 design rendering and the official aerial; the connected entrance canopy turns toward the office.',
        'relativeOrientationConsistentWithReviewedImages': difference < 1,
        'finding': ('The low-wing facade now follows the recessed hall long wall; depths and heights remain estimates.' if corrected else 'The previous assignment of those windows to original edge 14 is not supported; re-register the low wing and foyer before further detail work.'),
        'photoRegistrationAccepted': False,
        'replacementGeometryImplemented': corrected,
        'doNotInfer': ['Metric dimensions from perspective-image pixels',
                       'A new courtyard hole inside the mapped footprint',
                       'As-built dimensions or present condition from a 2014 design rendering'],
        'sourceRefs': ['gxuCivilPlatformDesign2014', 'gxuCivilDemolitionAerial2022', 'gx720CivilNorthPanorama'],
        'localEvidence': [],
    }
    # Optional research originals are not dependencies of production preparation.
    for name, scope in [
        ('work/refinement-s3-evidence/library-construction-2014.pdf', 'Platform text and embedded image xref 17; text about the library courtyard belongs to a different project'),
        ('work/refinement-s2-civil-labs/new-platform-detail.png', 'Hall roof, lower dense-window wing, connecting canopy and office relationship'),
        ('work/refinement-s2-civil-location/pano-tiles/b-6-7.jpg', 'Windowed low wing and columned canopy turn'),
        ('work/refinement-s2-civil-plan-evidence/temporary-utilities.pdf', 'PDF pages 4 and 39; platform crop incomplete, not a replacement surveyed footprint'),
    ]:
        path = ROOT / name
        if path.exists():
            report['localEvidence'].append({'file': name, 'sha256': sha(path), 'bytes': path.stat().st_size, 'reviewScope': scope})
    out.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')

    def xy(point):
        return (100+(point[0]+745)*6, 80+(-700-point[1])*6)

    def points(ring):
        return ' '.join(f'{x:.2f},{y:.2f}' for x, y in map(xy, ring))

    body = []
    colors = ['#c6e7f1', '#f1dcc2', '#e3dcec', '#e7e3c8', '#e4deed', '#d8e4db'] if corrected else ['#c6e7f1', '#f1dcc2', '#e3dcec', '#d8e4db']
    for part, color in zip(building['form']['parts'], colors):
        for polygon in part['polygons']:
            body.append(f'<polygon points="{points(polygon[0])}" fill="{color}" stroke="#66736f" stroke-width="1.5"/>')
    for face, color in [(hall, '#176ea0'), (low, '#b74032')]:
        body.append(f'<polyline points="{points([face["start"],face["end"]])}" fill="none" stroke="{color}" stroke-width="6"/>')
    if corrected:
        body.extend([
            '<text x="415" y="466" font-size="12">north-low-wing / 7.2 m</text>',
            '<path d="M 391 331 H 425" stroke="#66736f"/>',
            '<text x="430" y="335" font-size="12">link-portico / 7.2 m</text>',
        ])
    body.extend([
        f'<text x="32" y="28" font-size="20">结构平台：{"六分部方向修正（尺寸估算）" if corrected else "现有分部与低翼窗列配准冲突"}</text>',
        '<text x="32" y="53" font-size="13">仅画当前数据；不表示新的设计尺寸或替代建筑轮廓</text>',
        '<path d="M 610 145 V 90 l -5 12 m 5 -12 l 5 12" fill="none" stroke="#334b42" stroke-width="2"/>',
        '<text x="603" y="82">N</text>',
        '<text x="192" y="204">north-office / 29.7 m</text>',
        '<text x="53" y="327" font-size="12">west-foyer</text>',
        f'<text x="270" y="355" font-size="12">{"link-foyer" if corrected else "middle-labs"}</text>',
        '<text x="374" y="565">south-hall / 13.2 m</text>',
        f'<text x="410" y="510" fill="#176ea0" font-size="13">{"大厅后退高墙" if corrected else "大厅北长边 15"}</text>',
        f'<text x="414" y="424" fill="#b74032" font-size="13">低翼窗列：边 {15 if corrected else 14}</text>',
        f'<text x="32" y="652" font-size="15">两段实际模型轴线夹角 {difference:.2f}°；仅核对相对方向，非照片测绘尺寸。</text>',
        '<text x="32" y="682" font-size="13">进深、高度和柱列仍为估算；真实入口与屋面曲面仍需校准。</text>',
    ])
    out.with_suffix('.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="740" height="710" viewBox="0 0 740 710"><rect width="740" height="710" fill="#fafbf8"/><g font-family="sans-serif" fill="#283b34">'+''.join(body)+'</g></svg>')
    print(json.dumps({'axisDifferenceDegrees': difference, 'photoRegistrationAccepted': False, 'report': str(out.with_suffix('.json'))}))


if __name__ == '__main__':
    main()
