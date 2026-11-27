"""Apply the published residence directory after resolving the underlying OSM building forms."""

import json

from shapely.geometry import Polygon, mapping
from shapely.ops import transform

from building_overrides import pack_geometry
from prepare_geodata import OUT, ROOT, inverse
from terrain_elevation import sample_elevation


def prepare_residences():
    directory = json.loads((ROOT / 'data/student-residences.json').read_text())
    buildings = json.loads((OUT / 'buildings.json').read_text())
    geo = json.loads((OUT / 'geography.geojson').read_text())
    terrain = json.loads((OUT / 'terrain.json').read_text())
    sources = json.loads((ROOT / 'data/building-sources.json').read_text())
    trace = directory['east12']
    fid = trace['id']
    ring = trace['roofRing']
    polygon = Polygon(ring)
    polygons, triangles = pack_geometry([polygon])
    center = [round(sum(axis) / len(ring), 2) for axis in zip(*ring)]
    east12 = {
        'id': fid,
        'name': directory['names'][fid],
        'category': 'living',
        'center': center,
        'bounds': list(polygon.bounds),
        'polygons': polygons,
        'roofTriangles': triangles,
        'height': trace['height'],
        'levels': trace['levels'],
        'heightBasis': '按类型估算',
        'heightStatus': 'estimated',
        'footprintStatus': 'approximate exterior roof projection',
        'form': {},
        'facadeBasis': trace['precision'],
        'insideCampus': True,
        'landmark': None,
        'constructionStatus': None,
        'tags': {},
        'geometrySource': 'manual-imagery-trace',
        'osmVersion': None,
        'osmEditedAt': None,
        'sourceUrl': next(s['url'] for s in sources if s['id'] == 'studentDormImagery'),
        'sourceRefs': trace['sourceRefs'],
    }
    by_id = {b['id']: b for b in buildings}
    by_id[fid] = east12
    features = {f['id']: f for f in geo['features']}
    features[fid] = {
        'type': 'Feature',
        'id': fid,
        'geometry': mapping(transform(inverse, polygon)),
        'properties': {
            'kind': 'buildings',
            **{
                k: east12[k]
                for k in (
                    'id',
                    'insideCampus',
                    'landmark',
                    'levels',
                    'height',
                    'geometrySource',
                    'osmVersion',
                    'osmEditedAt',
                    'sourceUrl',
                    'sourceRefs',
                    'tags',
                )
            },
        },
    }
    for key, name in directory['names'].items():
        b = by_id[key]
        b.update(
            name=name,
            category='living',
            elevation=round(sample_elevation(terrain, *b['center']), 2),
            zone='north'
            if b['center'][1] > 200
            else 'east'
            if b['center'][0] >= 0
            else 'west',
            chunk='chunk-dorm-' + key.replace('/', '-'),
        )
        features[key]['properties'].update(name=name, category='living')
    for group in directory['dimensions']:
        dimensions = {
            'levels': group['levels'],
            'height': group['height'],
            'heightStatus': 'estimated',
            'sourceRefs': group['sourceRefs'],
        }
        for key in group['ids']:
            by_id[key].update(dimensions, heightBasis='按类型估算')
            features[key]['properties'].update(dimensions)
    geo['features'] = list(features.values())
    for path, value in [
        ('buildings.json', list(by_id.values())),
        ('geography.geojson', geo),
    ]:
        (OUT / path).write_text(
            json.dumps(value, ensure_ascii=False, separators=(',', ':'))
        )
