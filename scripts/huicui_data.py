"""Photo-derived Huicui envelope within the existing journalism-building relation."""

import json
import math
from pathlib import Path

from shapely.affinity import rotate, translate
from shapely.geometry import Polygon, box

from architecture_data import pack

ROOT = Path(__file__).resolve().parents[1]
FEATURE_ID = 'relation/11970574'


def prepare_huicui():
    path = ROOT / 'public/data/buildings.json'
    buildings = json.loads(path.read_text())
    b = next(b for b in buildings if b['id'] == FEATURE_ID)
    p = Polygon(b['polygons'][0][0], b['polygons'][0][1:])
    edges = list(zip(p.exterior.coords, list(p.exterior.coords)[1:]))
    a, c = max(edges, key=lambda v: math.dist(*v))
    angle = math.atan2(c[1] - a[1], c[0] - a[0]) % math.pi
    if angle > math.pi / 2:
        angle -= math.pi
    origin = [(p.bounds[i] + p.bounds[i + 2]) / 2 for i in (0, 1)]
    local = translate(
        rotate(p, -angle, origin=origin, use_radians=True), -origin[0], -origin[1]
    )
    # Ground-floor north colonnade is genuinely recessed; no opaque wall behind columns.
    north = local.bounds[3]
    arcade = local.intersection(box(-100, north - 4.2, 100, north + 1))
    # The lobby doors sit behind the column line. The two-storey notch below
    # the west end of the dining floor is open in the May 2026 lawn view.
    vestibule = box(-4.07, north - 8.0, 4.07, north)
    west_loggia = box(local.bounds[0] - 1, north - 4.5, -36.1, north + 1)
    # Views from the two southern approaches show an open two-storey edge.
    south = local.bounds[1]
    south_arcade = local.intersection(box(-100, south - 1, 100, south + 3.1))
    # Two east-road panoramas show a glazed doorway and an adjacent flight
    # ascending into the recessed southeast bay. Only the visible run is known.
    east = local.bounds[2]
    entry = dict(east=east, south=south + 3.1, north=south + 14.7, depth=7.0)
    stair_pocket = box(east - entry['depth'], entry['south'], east + 1, entry['north'])
    storeys = [
        (
            local.difference(arcade)
            .difference(vestibule)
            .difference(south_arcade)
            .difference(stair_pocket),
            '首层及夹层 · 北侧退进门厅',
            0,
            8.15,
        ),
        (local, '三至四层 · 保留内院', 8.15, 16.70),
        (local.difference(west_loggia), '五至六层 · 西端开敞柱廊', 16.70, 24.55),
        (local, '七层 · 荟萃餐厅', 24.55, 30.32),
    ]
    parts = [
        dict(pack(shape, name, top - base), base=base)
        for shape, name, base, top in storeys
    ]
    catalogue = json.loads((ROOT / 'data/landmarks.json').read_text())
    l = next(l for l in catalogue if l['id'] == 'huicui').copy()
    b.update(
        height=l['height'],
        heightBasis='北立面跨度与七层窗带照片比例估算',
        customModel='huicui',
        facadeBasis='荟萃楼北立面依据2026年5月住客入口与草坪斜拍、校方全景独立建模；南侧架空柱列及上部窗肋依据双向街景，柱距和退深估算',
        sourceRefs=[
            'osm',
            l['reference'],
            *l['additionalReferences'],
            'gxuNewsStreet27',
            'gxuNewsStreet307',
            'gxuNewsEast299',
            'gxuNewsEast268',
            'gxuWelcome2026',
        ],
        architecture={
            'origin': origin,
            'angle': angle,
            'bounds': list(local.bounds),
            'parts': parts,
            'arcadeCeiling': pack(arcade, '北侧柱廊顶板', 0.2),
            'eastStairEntry': entry,
            'southArcade': pack(south_arcade, '新闻学院南侧柱廊', 0.2),
            'footprint': [list(local.exterior.coords)]
            + [list(r.coords) for r in local.interiors],
            'hotelEntrance': [0, north],
            'arcadeDepth': 4.2,
            'arcadeClearHeight': 8.15,
            'precision': '荟萃楼为新闻传播学院同一 OSM 建筑北翼；保留整栋关系 ID、轮廓和内院。7 层来自 OSM，北翼檐顶高度按照片比例估算；楼层分段、门窗、雨棚尺寸及未拍到立面均非实测。',
            'navigation': '第 20 处精选地标；支持名称搜索、定位、详情与巡游。',
        },
    )
    b['landmark'] = 'huicui'
    b.pop('chunk', None)
    l.update(
        center=b['center'],
        bounds=b['bounds'],
        height=b['height'],
        elevation=b.get('elevation', 0),
        zone='west',
        sourceUrl=b['sourceUrl'],
        osmEditedAt=b['osmEditedAt'],
        sourceRefs=b['sourceRefs'],
    )
    lp = ROOT / 'public/data/landmarks.json'
    landmarks = [a for a in json.loads(lp.read_text()) if a['id'] != 'huicui'] + [l]
    landmarks.sort(key=lambda a: a.get('navigationOrder', 0))
    lp.write_text(json.dumps(landmarks, ensure_ascii=False, separators=(',', ':')))
    op = ROOT / 'public/data/overview.json'
    overview = json.loads(op.read_text())
    overview['landmarks'] = len(landmarks)
    op.write_text(json.dumps(overview, ensure_ascii=False, indent=2) + '\n')
    gp = ROOT / 'public/data/geography.geojson'
    geo = json.loads(gp.read_text())
    # Keep the GeoJSON catalogue aligned with the final shared building record,
    # including its photo-derived facade provenance. Navigation owns its alias.
    next(f for f in geo['features'] if f['id'] == FEATURE_ID)['properties'].update(
        {
            key: b[key]
            for key in (
                'name',
                'category',
                'height',
                'heightBasis',
                'facadeBasis',
                'landmark',
                'sourceRefs',
            )
        }
    )
    gp.write_text(json.dumps(geo, ensure_ascii=False, separators=(',', ':')))
    path.write_text(json.dumps(buildings, ensure_ascii=False, separators=(',', ':')))
    path = ROOT / 'public/data/sources.json'
    sources = json.loads(path.read_text())
    refs = json.loads((ROOT / 'data/huicui-sources.json').read_text())
    ids = {r['id'] for r in refs}
    sources['sources'] = [r for r in sources['sources'] if r['id'] not in ids] + refs
    path.write_text(json.dumps(sources, ensure_ascii=False, indent=2) + '\n')
    print('Huicui: retained one OSM relation and courtyard; curated landmark 20')


if __name__ == '__main__':
    prepare_huicui()
