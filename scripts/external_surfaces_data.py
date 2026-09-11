"""Remove non-campus sports/landscape overlays inside the two adjacent colleges."""
import gzip,json
from pathlib import Path
from shapely.geometry import shape
from shapely.ops import transform
ROOT=Path(__file__).resolve().parents[1]
COLLEGE_IDS=(398115381,398114009)


def prepare_external_surfaces():
    from prepare_geodata import geom,project
    out=ROOT/'public/data'
    raw=json.loads(gzip.decompress((ROOT/'data/snapshots/osm-2026-09-09.json.gz').read_bytes()))
    schools=[e for e in raw['elements'] if e['type']=='way' and e['id'] in COLLEGE_IDS]
    masks=[(e['tags']['name'],geom(e)) for e in schools]
    geo=json.loads((out/'geography.geojson').read_text())
    report_path=ROOT/'docs/model-checks/external-surfaces.json'
    previous=json.loads(report_path.read_text()) if report_path.exists() else {}
    removed={e['id']:e for e in previous.get('excluded',[])}
    for f in geo['features']:
        p=f['properties']
        if p.get('insideCampus',True) or p['kind'] not in ('sports','green'):continue
        g=transform(project,shape(f['geometry']))
        for name,mask in masks:
            if mask.covers(g.representative_point()):
                removed[f['id']]={'id':f['id'],'kind':p['kind'],'tags':p.get('tags',{}),'college':name}
                break
    geo['features']=[f for f in geo['features'] if f['id'] not in removed]
    geo['metadata']['excludedCollegeSurfaces']={'boundaryOsmIds':[f'way/{i}' for i in COLLEGE_IDS],'sourceSnapshot':'2026-09-09','featureIds':sorted(removed),'basis':'仅用于展示清理：移除财经学院与工业职业技术学院范围内、校外的运动及景观铺面，不改校内设施与周边公共道路。'}
    surfaces=json.loads((out/'surfaces.json').read_text())
    # Indices are referenced by road overrides: keep every slot in place.
    for s in surfaces:
        if s['id'] in removed:s.update(vertices=[],triangles=[],suppressed=True)
    overview=json.loads((out/'overview.json').read_text())
    for kind in ('sports','green'):
        overview['layers'][kind]=sum(f['properties']['kind']==kind for f in geo['features'])
    for name,data in [('geography.geojson',geo),('surfaces.json',surfaces),('overview.json',overview)]:
        (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2 if name=='overview.json' else None,separators=None if name=='overview.json' else (',',':'))+ ('\n' if name=='overview.json' else ''))
    report={'boundaryOsmIds':[f'way/{i}' for i in COLLEGE_IDS],'excluded':list(removed.values()),'preservedSurfaceSlots':len(surfaces)}
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(f'Removed {len(removed)} external sports/landscape features, preserving road override indices')


if __name__=='__main__':prepare_external_surfaces()
