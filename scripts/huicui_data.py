"""Photo-derived Huicui envelope within the existing journalism-building relation."""
import json, math
from pathlib import Path
from shapely.geometry import Polygon, box
from shapely.affinity import rotate, translate
from architecture_data import pack

ROOT = Path(__file__).resolve().parents[1]
FEATURE_ID = 'relation/11970574'

def prepare_huicui():
    path = ROOT/'public/data/buildings.json'
    buildings = json.loads(path.read_text())
    b = next(b for b in buildings if b['id'] == FEATURE_ID)
    p = Polygon(b['polygons'][0][0], b['polygons'][0][1:])
    edges = list(zip(p.exterior.coords, list(p.exterior.coords)[1:]))
    a, c = max(edges, key=lambda v: math.dist(*v))
    angle = math.atan2(c[1]-a[1], c[0]-a[0]) % math.pi
    if angle > math.pi/2: angle -= math.pi
    origin = [(p.bounds[i]+p.bounds[i+2])/2 for i in (0, 1)]
    local = translate(rotate(p, -angle, origin=origin, use_radians=True), -origin[0], -origin[1])
    # Ground-floor north colonnade is genuinely recessed; no opaque wall behind columns.
    north = local.bounds[3]
    arcade = local.intersection(box(-100, north-4.2, 100, north+1))
    parts = [pack(local.difference(arcade), '首层及夹层 · 北侧退进门厅', 6.8),
             pack(local, '三至七层 · 保留映射内院与西侧凹口', b['height']-6.8)]
    b.update(customModel='huicui', facadeBasis='荟萃楼北立面依据校方全景与入口照片独立建模；其余立面按轮廓及同楼风格估算',
             sourceRefs=['osm', 'huicuiExterior2020', 'huicuiEntrance2018', 'huicuiUse2024', 'huicuiMaintenance2026', 'huicuiLocation'],
             architecture={'origin':origin, 'angle':angle, 'bounds':list(local.bounds), 'parts':parts,
                           'arcadeCeiling':pack(arcade, '北侧柱廊顶板', .2),
                           'footprint':[list(local.exterior.coords)]+[list(r.coords) for r in local.interiors],
                           'hotelEntrance':[0, north], 'arcadeDepth':4.2, 'arcadeClearHeight':6.8,
                           'precision':'荟萃楼为新闻传播学院同一 OSM 建筑北翼；保留整栋关系 ID、轮廓和内院。7 层来自 OSM，总高按 3.3 米/层估算；楼层分段、门窗、雨棚尺寸及未拍到立面均非实测。',
                           'navigation':'仅精建，仍随普通建筑分区加载，不增加精选导航条目。'})
    path.write_text(json.dumps(buildings, ensure_ascii=False, separators=(',', ':')))
    path = ROOT/'public/data/sources.json'
    sources = json.loads(path.read_text())
    refs = json.loads((ROOT/'data/huicui-sources.json').read_text())
    ids = {r['id'] for r in refs}
    sources['sources'] = [r for r in sources['sources'] if r['id'] not in ids] + refs
    path.write_text(json.dumps(sources, ensure_ascii=False, indent=2)+'\n')
    print('Huicui: retained one OSM relation, one courtyard and existing navigation; north entrance', north)

if __name__ == '__main__': prepare_huicui()
