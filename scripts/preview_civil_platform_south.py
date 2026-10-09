"""Resolve a complete upper-south-window and west-wall candidate, read-only."""
import argparse
import copy
import json
import math
from pathlib import Path

from building_overrides import ROOT, load_catalogue, resolve_building, source_catalogue

ID = 'way/957404988'
SOURCE = 'gx720CivilSouthwestPanorama'


def proposal(building, override):
    r = copy.deepcopy(override)
    office = next(p for p in r['parts'] if p['id'] == 'north-office')
    foyer = next(p for p in r['parts'] if p['id'] == 'link-foyer')
    # Split the collinear south edge at the actual foyer/portico junction.
    # No vertex moves and the union of all parts stays the mapped footprint.
    junction = foyer['polygons'][0][0][1]
    ring = office['polygons'][0][0]
    if junction not in ring:
        ring.insert(1, copy.deepcopy(junction))
    west = next(f for f in r['facadeRules'] if f['edge'] == 12)
    west['skipWindowLevels'] = [5, 6, 7, 8]

    def panels(label, length, columns):
        return [dict(id=f'office-south-{label}-{i}', type='glazing',
                     **{'from':.5/length, 'to':1-.5/length},
                     bottom=14+3.3*i, top=16.25+3.3*i, columns=columns,
                     rows=1, frameWidth=.12, depth=.1) for i in range(5)]

    outer = building['polygons'][0][0]
    west_south = next(f for f in r['facadeRules'] if f['edge'] == 11)
    west_south['panels'] = panels('west', math.dist(outer[11], outer[12]), 8)
    for edge, adjacent, columns, label in [(0, 'link-foyer', 11, 'middle'),
                                           (1, 'link-portico', 3, 'east')]:
        config = dict(part='north-office', adjacentPart=adjacent, polygon=0, ring=0,
                      edge=edge, region='above-roof', rule=dict(windows=False, balconies=False,
                      panels=panels(label, math.dist(ring[edge], ring[edge+1]), columns)))
        r['exposedFacadeRules'] = [f for f in r['exposedFacadeRules']
                                   if not (f['part'] == 'north-office' and f.get('region') == 'above-roof') or f['edge'] != edge]
        r['exposedFacadeRules'].append(config)
    note = ('鲁班路全景659定性对应北楼南面和西端墙。西墙仅停用零起算5–8层通用窗；'
            '南面14.0米以上分五行、三段8+11+3列浅色窗框，列数、尺寸、标高均估算，未逐窗测绘。'
            '北楼南边只在既有门厅/门廊接缝插入共线点，不移轮廓；门厅最高屋面与檐口净空保留。'
            '南面下部和西墙下五层仍为示意，照片遮挡不作为删除依据。尺寸级照片配准未通过。')
    for field in ('parts', 'facadeRules', 'exposedFacadeRules'):
        e = r['evidence'][field]
        if SOURCE not in e['sourceRefs']:
            e['sourceRefs'].append(SOURCE)
            e['note'] += ' ' + note
    candidate = resolve_building(building, r, {s['id'] for s in source_catalogue()} | {SOURCE})
    return dict(original=building, candidate=candidate, override=r, candidateOnly=True,
                photoMetricRegistrationAccepted=False, note=note)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--buildings', type=Path, default=ROOT/'public/data/buildings.json')
    parser.add_argument('--catalogue', type=Path, default=ROOT/'data/building-overrides.json')
    parser.add_argument('--output', type=Path, required=True)
    a = parser.parse_args()
    b = next(b for b in json.loads(a.buildings.read_text()) if b['id'] == ID)
    result = proposal(b, load_catalogue(a.catalogue)[ID])
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print('Resolved upper south / west candidate; no production data written.')
