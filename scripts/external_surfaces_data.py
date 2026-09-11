"""Remove selected external overlays while retaining stable surface indices."""
import gzip,json
from pathlib import Path
from shapely.geometry import shape
from shapely.ops import transform
ROOT=Path(__file__).resolve().parents[1]
COLLEGE_IDS=(398115381,398114009)


def prepare_external_surfaces():
    from prepare_geodata import geom,project,inverse
    from shapely.geometry import mapping
    from surroundings_data import surface_shape,triangulate
    from scene_cleanup import EXCLUSIONS,TRIMS,trim_corridor_chunk
    out=ROOT/'public/data'
    infrastructure=json.loads((out/'infrastructure.json').read_text())
    for chunk in infrastructure['chunks']:trim_corridor_chunk(chunk)
    (out/'infrastructure.json').write_text(json.dumps(infrastructure,ensure_ascii=False,separators=(',',':')))
    raw=json.loads(gzip.decompress((ROOT/'data/snapshots/osm-2026-09-09.json.gz').read_bytes()))
    schools=[e for e in raw['elements'] if e['type']=='way' and e['id'] in COLLEGE_IDS]
    masks=[(e['tags']['name'],geom(e)) for e in schools]
    geo=json.loads((out/'geography.geojson').read_text())
    report_path=ROOT/'docs/model-checks/external-surfaces.json'
    previous=json.loads(report_path.read_text()) if report_path.exists() else {}
    removed={e['id']:e for e in previous.get('excluded',[])}
    for f in geo['features']:
        p=f['properties']
        if f['id'] in EXCLUSIONS:
            removed[f['id']]={'id':f['id'],'kind':p['kind'],'tags':p.get('tags',{}),'reason':EXCLUSIONS[f['id']]}
            continue
        if p.get('insideCampus',True) or p['kind'] not in ('sports','green'):continue
        g=transform(project,shape(f['geometry']))
        for name,mask in masks:
            if mask.covers(g.representative_point()):
                removed[f['id']]={'id':f['id'],'kind':p['kind'],'tags':p.get('tags',{}),'college':name}
                break
    geo['features']=[f for f in geo['features'] if f['id'] not in removed]
    for f in geo['features']:
        if f['id'] in TRIMS:
            g=transform(project,shape(f['geometry'])).intersection(TRIMS[f['id']])
            f['geometry']=mapping(transform(inverse,g))
            f['properties']['displayTrim']='按 2026-09-12 用户圈选在路口收束校外断头段；原始轮廓见 OSM 快照。'
    geo['metadata']['excludedCollegeSurfaces']={'boundaryOsmIds':[f'way/{i}' for i in COLLEGE_IDS],'sourceSnapshot':'2026-09-09','featureIds':sorted(k for k,v in removed.items() if 'college' in v),'basis':'仅用于展示清理：移除财经学院与工业职业技术学院范围内、校外的运动及景观铺面，不改校内设施与周边公共道路。'}
    surfaces=json.loads((out/'surfaces.json').read_text())
    # Indices are referenced by road overrides: keep every slot in place.
    for s in surfaces:
        if s['id'] in removed:s.update(vertices=[],triangles=[],suppressed=True)
        elif s['id'] in TRIMS:s.update(triangulate(surface_shape(s).intersection(TRIMS[s['id']])))
    geo['metadata']['displayCleanup']={'date':'2026-09-12','excludedFeatureIds':sorted(EXCLUSIONS),'trimmedFeatureIds':sorted(TRIMS),'basis':'按用户圈选移除校外零散道路、公园、水面和球场；保留校园及周边主干道。原始 OSM 快照不变。'}
    overview=json.loads((out/'overview.json').read_text())
    for kind in ('sports','green','water','roads'):
        overview['layers'][kind]=sum(f['properties']['kind']==kind for f in geo['features'])
    for name,data in [('geography.geojson',geo),('surfaces.json',surfaces),('overview.json',overview)]:
        (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2 if name=='overview.json' else None,separators=None if name=='overview.json' else (',',':'))+ ('\n' if name=='overview.json' else ''))
    report={'boundaryOsmIds':[f'way/{i}' for i in COLLEGE_IDS],'excluded':list(removed.values()),'trimmedFeatureIds':sorted(TRIMS),'preservedSurfaceSlots':len(surfaces)}
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(f'Excluded {len(removed)} external features; trimmed {len(TRIMS)} road tails; surface indices preserved')


if __name__=='__main__':prepare_external_surfaces()
