"""Append the faculty housing footprints traced from the university site plan."""

import json
import math

from shapely.geometry import Polygon, mapping
from shapely.ops import transform

from building_overrides import pack_geometry, source_catalogue
from prepare_geodata import OUT, ROOT, inverse
from terrain_elevation import make_elevation


def prepare_housing():
    records = json.loads((ROOT / 'data/east-campus-housing.json').read_text())
    ids = {row['id'] for row in records}
    buildings = [
        b
        for b in json.loads((OUT / 'buildings.json').read_text())
        if b['id'] not in ids
    ]
    geo = json.loads((OUT / 'geography.geojson').read_text())
    geo['features'] = [f for f in geo['features'] if f['id'] not in ids]
    by_id = {b['id']: b for b in buildings}
    features = {f['id']: f for f in geo['features']}
    sources = {r['id'] for r in source_catalogue()}
    for fid, appearance in json.loads(
        (ROOT / 'data/building-appearance-sources.json').read_text()
    ).items():
        refs = appearance['sourceRefs']
        if set(refs) - sources:
            raise ValueError(f'Unknown appearance source for {fid}')
        b = by_id[fid]
        b['sourceRefs'] = list(dict.fromkeys([*b.get('sourceRefs', ['osm']), *refs]))
        props = features[fid]['properties']
        props['sourceRefs'] = b['sourceRefs']
        for key in ('levels', 'height', 'heightStatus', 'heightBasis'):
            if key in appearance:
                props[key] = b[key] = appearance[key]
                if key in ('levels', 'height') and 'form' in b:
                    b['form'][key] = b[key]
    elevation = make_elevation(json.loads((OUT / 'terrain.json').read_text()))
    for row in records:
        ring, *holes = row['polygons'][0]
        polygon = Polygon(ring, holes)
        if not polygon.is_valid or polygon.is_empty:
            raise ValueError(f'Invalid faculty housing footprint: {row["id"]}')
        x, y = polygon.centroid.coords[0]
        polys, triangles = pack_geometry([polygon])
        cell = [math.floor(v / 360) for v in (x, y)]
        chunk = 'chunk-' + '-'.join(
            ('p' if n >= 0 else 'n') + str(abs(n)) for n in cell
        )
        building = dict(
            row,
            category='living',
            center=[round(x, 2), round(y, 2)],
            bounds=list(polygon.bounds),
            elevation=round(elevation(x, y), 2),
            campusArea='east',
            zone='north' if y > 200 else 'west' if x < 0 else 'east',
            chunk=chunk,
            polygons=polys,
            roofTriangles=triangles,
            insideCampus=True,
            landmark=None,
            osmEditedAt=None,
            osmVersion=None,
            heightBasis='校方工程文件的设计高度，竣工实测未核；屋面小构筑物高度估算。',
            heightStatus='design',
            geometrySource='university-site-plan',
            archetype='generic',
            tags={},
            constructionStatus=None,
        )
        buildings.append(building)
        props = {
            k: building[k]
            for k in (
                'id',
                'name',
                'category',
                'height',
                'levels',
                'heightStatus',
                'sourceRefs',
                'sourceUrl',
                'insideCampus',
                'landmark',
                'osmEditedAt',
                'osmVersion',
                'geometrySource',
                'campusArea',
            )
        }
        geo['features'].append(
            dict(
                type='Feature',
                id=row['id'],
                properties=dict(props, kind='buildings'),
                geometry=mapping(transform(inverse, polygon)),
            )
        )
    for name, value in [('buildings.json', buildings), ('geography.geojson', geo)]:
        (OUT / name).write_text(
            json.dumps(value, ensure_ascii=False, separators=(',', ':'))
        )
