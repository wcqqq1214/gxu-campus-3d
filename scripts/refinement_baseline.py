"""Capture the immutable starting data for the campus refinement work.

Run before changing generated data/models. This does not refresh OSM or infer
real building dimensions; candidates remain explicitly awaiting evidence.
"""
import collections
import hashlib
import json
import math
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/model-checks/refinement'


def write(name, value):
    path = OUT / name
    if path.exists():
        raise FileExistsError(f'Refusing to overwrite baseline: {path}')
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def old_pitched_rule(b):
    ring = b['polygons'][0][0]
    return (b['height'] < 14 and len(b['polygons'][0]) == 1 and len(ring) == 5
            and all(abs(a[0]-c[0]) < .1 or abs(a[1]-c[1]) < .1
                    for a, c in zip(ring, ring[1:])))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / 'baseline.json').exists():
        raise FileExistsError('Baseline already recorded; use it for comparison.')
    load = lambda name: json.loads((ROOT / 'public/data' / name).read_text())
    bs = load('buildings.json')
    manifest = load('models.json')
    library = next(b for b in bs if b['landmark'] == 'library')
    ordinary = [b for b in bs if b['insideCampus'] and not b['landmark']
                and not b.get('customModel') and b['id'] != 'way/948683815'
                and b['tags'].get('memorial') != 'column']
    nearest = sorted(ordinary, key=lambda b: math.dist(b['center'], library['center']))
    # Local context first; add dining, courtyard and teaching samples without
    # mistaking name-based candidate selection for actual facade verification.
    chosen = nearest[:15]
    for predicate, count in [
        (lambda b: '餐厅' in b['name'], 3),
        (lambda b: any(len(p) > 1 for p in b['polygons']), 3),
        (lambda b: b['category'] == 'academic', 4),
    ]:
        extras = [b for b in nearest if predicate(b) and b not in chosen]
        chosen.extend(extras[:count])
    for b in nearest:
        if len(chosen) >= 25:
            break
        if b not in chosen:
            chosen.append(b)
    candidates = []
    for b in chosen[:25]:
        candidates.append({
            'id': b['id'], 'name': b['name'], 'chunk': b.get('chunk'),
            'distanceToLibraryMeters': round(math.dist(b['center'], library['center']), 1),
            'reason': '图书馆样板周边及食堂/教学/内院形制覆盖',
            'baseline': {k: b[k] for k in ('category', 'height', 'levels', 'heightBasis', 'tags')},
            'sourceUrl': b['sourceUrl'], 'osmVersion': b['osmVersion'],
            'status': 'awaiting-evidence',
            'toVerify': ['层数与主体/附楼高度', '屋顶', '主入口位置和朝向', '主要立面/阳台'],
        })
    files = sorted(set(list((ROOT/'public/data').glob('*'))
                       + list((ROOT/'public/models').glob('*.glb'))
                       + list((ROOT/'data/snapshots').glob('*'))
                       + [ROOT/'blender/gxu-campus.blend']))
    assets = {str(p.relative_to(ROOT)): {'bytes': p.stat().st_size,
              'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
              for p in files if p.is_file()}
    report = {
        'capturedAt': datetime.now(timezone.utc).isoformat(),
        'sourceCommit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'environment': {'os': platform.platform(), 'python': platform.python_version(),
                        'node': subprocess.check_output(['node', '--version'], text=True).strip(),
                        'blender': subprocess.check_output(['blender', '--version'], text=True).splitlines()[:8],
                        'draco': 'Blender bundled glTF exporter; compression level 6, base position 15 bits / normal 6 bits, near position 16 / normal 10'},
        'buildings': len(bs), 'campusBuildings': sum(b['insideCampus'] for b in bs),
        'heightBasis': dict(collections.Counter(b['heightBasis'] for b in bs)),
        'trees': len(load('vegetation.json')), 'landmarks': len(load('landmarks.json')),
        'initialModelBytes': manifest['base']['bytes'] + manifest['trees']['bytes'],
        'maxChunkBytes': max(a['bytes'] for a in manifest['zones']),
        'oldNearOnlyPitchedRoofIds': [b['id'] for b in ordinary if old_pitched_rule(b)],
        'assets': assets,
        'scope': 'Local data and asset baseline; browser measurements recorded separately.',
    }
    write('candidates.json', candidates)
    write('baseline.json', report)
    print(f'Baseline: {len(bs)} buildings, {len(candidates)} candidates; {OUT}')


if __name__ == '__main__':
    main()
