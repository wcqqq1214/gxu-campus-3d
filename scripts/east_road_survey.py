"""Apply the surveyed East Campus street axes to ordinary geography and road surfaces."""

import json
from pathlib import Path

from shapely.geometry import LineString
from shapely.ops import unary_union

from surroundings_data import surface_shape, triangulate


def apply_east_road_survey(root):
    out = root / 'public/data'
    records = json.loads((root / 'data/east-road-survey.json').read_text())
    geo_file = out / 'geography.geojson'
    surface_file = out / 'surfaces.json'
    geo = json.loads(geo_file.read_text())
    surfaces = json.loads(surface_file.read_text())
    by_id = {f['id']: f for f in geo['features']}
    by_surface = {s['id']: s for s in surfaces}
    selected = {r['id'] for r in records}
    outlines = [
        LineString(r['displayXY']).buffer(r['width'] / 2, cap_style=2, join_style=2)
        for r in records
    ]
    neighborhood = unary_union(outlines)
    contacts = []
    for surface in surfaces:
        if (
            surface['kind'] != 'roads'
            or surface['id'] in selected
            or surface.get('suppressed')
        ):
            continue
        t = surface['tags']
        if (
            t.get('bridge', 'no') != 'no'
            or t.get('tunnel', 'no') != 'no'
            or str(t.get('layer', '0')) != '0'
        ):
            continue
        shape = surface_shape(surface)
        if neighborhood.intersects(shape):
            contacts.append(shape)
    occupied = unary_union(contacts)
    for record, outline in zip(records, outlines):
        fid = record['id']
        if fid not in by_id:
            by_id[fid] = {'type': 'Feature', 'id': fid, 'properties': {'name': ''}}
            geo['features'].append(by_id[fid])
        feature = by_id[fid]
        props = feature['properties']
        props.update(
            id=fid,
            kind='roads',
            osmVersion=record['version'],
            osmEditedAt=record['edited'],
            sourceUrl=record['source'],
            insideCampus=True,
        )
        props.setdefault('tags', {})['highway'] = record['kind']
        feature['geometry'] = dict(type='LineString', coordinates=record['coordinates'])
        if fid not in by_surface:
            by_surface[fid] = {'id': fid}
            surfaces.append(by_surface[fid])
        by_surface[fid].update(
            kind='roads',
            insideCampus=True,
            **triangulate(outline.difference(occupied)),
        )
        by_surface[fid].setdefault('tags', {})['highway'] = record['kind']
        occupied = occupied.union(outline)
    geo_file.write_text(json.dumps(geo, ensure_ascii=False, separators=(',', ':')))
    surface_file.write_text(
        json.dumps(surfaces, ensure_ascii=False, separators=(',', ':'))
    )


if __name__ == '__main__':
    import sys

    apply_east_road_survey(Path(sys.argv[1]).resolve())
