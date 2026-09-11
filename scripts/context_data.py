"""Keep only mapped external buildings immediately beside the campus boundary."""
import collections
import json
from pathlib import Path
from shapely.geometry import Polygon, shape
from shapely.ops import transform, unary_union

ROOT = Path(__file__).resolve().parents[1]
MAX_CONTEXT_DISTANCE_METERS = 20


def select_context(buildings, campus):
    kept, excluded = [], []
    for building in buildings:
        if building['insideCampus']:
            kept.append(building)
            continue
        footprint = unary_union([Polygon(p[0], p[1:]) for p in building['polygons']])
        distance = footprint.distance(campus)
        if distance <= MAX_CONTEXT_DISTANCE_METERS:
            kept.append(building)
        else:
            excluded.append({'id': building['id'], 'name': building['name'],
                             'distanceMeters': round(distance, 2)})
    return kept, excluded


def prepare_context():
    from prepare_geodata import project
    out = ROOT / 'public/data'
    geo = json.loads((out / 'geography.geojson').read_text())
    campus = transform(project, shape(next(f for f in geo['features'] if f['id'] == 'campus')['geometry']))
    buildings = json.loads((out / 'buildings.json').read_text())
    buildings, excluded = select_context(buildings, campus)
    removed = {b['id'] for b in excluded}
    geo['features'] = [f for f in geo['features'] if f['id'] not in removed]
    policy = {'maxDistanceMeters': MAX_CONTEXT_DISTANCE_METERS,
              'basis': '保留校内建筑；校外仅保留已有地图轮廓距 OSM 校界不超过 20 米的完整建筑，距离为展示筛选规则，不是权属认定。'}
    geo['metadata']['contextBuildings'] = policy
    stats = json.loads((out / 'overview.json').read_text())
    stats.update(buildings=len(buildings), campusBuildings=sum(b['insideCampus'] for b in buildings),
                 contextBuildings=sum(not b['insideCampus'] for b in buildings),
                 contextDistanceMeters=MAX_CONTEXT_DISTANCE_METERS,
                 estimatedHeights=sum(b['heightBasis'] == '按类型估算' for b in buildings),
                 editYears=dict(sorted(collections.Counter(b['osmEditedAt'][:4] for b in buildings if b['osmEditedAt']).items())))
    stats['layers']['buildings'] = len(buildings)
    for name, data in [('buildings.json', buildings), ('geography.geojson', geo), ('overview.json', stats)]:
        (out / name).write_text(json.dumps(data, ensure_ascii=False, indent=2 if name == 'overview.json' else None, separators=None if name == 'overview.json' else (',', ':')) + ('\n' if name == 'overview.json' else ''))
    report_path = ROOT / 'docs/model-checks/context-selection.json'
    # Re-running an already-filtered snapshot keeps its removal audit intact.
    previous = json.loads(report_path.read_text()) if report_path.exists() else {}
    exclusions = {} if excluded else {b['id']: b for b in previous.get('excluded', [])}
    exclusions.update({b['id']: b for b in excluded})
    report = {**policy, 'campusBuildings': stats['campusBuildings'], 'contextBuildings': stats['contextBuildings'],
              'retainedContextIds': [b['id'] for b in buildings if not b['insideCampus']],
              'excluded': [b for k,b in exclusions.items() if k not in {b['id'] for b in buildings}]}
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(f"Retained {stats['campusBuildings']} campus + {stats['contextBuildings']} adjacent buildings; removed {len(excluded)} distant buildings")


if __name__ == '__main__':
    prepare_context()
