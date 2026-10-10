"""Resolve two unapproved roof-location hypotheses without changing public data."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from building_overrides import footprint_revision, resolve_building, source_catalogue

ROOT = Path(__file__).resolve().parents[1]
ID = 'way/759170251'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    path = ROOT/'public/data/buildings.json'
    original = next(b for b in json.loads(path.read_text()) if b['id'] == ID)
    if original['levels'] != 8 or original.get('calibration'):
        raise ValueError('Production has changed; reassess this eight-storey baseline')
    record = {
        'name': original['name'], 'footprintRevision': footprint_revision(original),
        'levels': 7, 'roof': {'type': 'flat'},
        'roofVolumes': [{'id': 'historical-rooftop-pavilion', 'part': 'body',
                         'polygon': 0, 'edge': 3, 'from': .55, 'to': .71,
                         'inset': 1.1, 'depth': 7.0, 'rise': 3.0,
                         'cap': {'overhang': .5, 'height': .4}}],
        'evidence': {
            'levels': {'status': 'confirmed', 'sourceRefs': ['gxuDonationProjects'],
                       'note': '项目册PDF第40页第20项记载7层，具名照片可见七层主体；历史地图角点支持对象对应。OSM八层标签保留，计数原因未知。'},
            'roof.type': {'status': 'estimated', 'sourceRefs': ['gxuDonationProjects'],
                          'note': '照片支持平屋面及上部构架，当前候选尚未生成沿檐开敞构架。'},
            'roofVolumes': {'status': 'estimated', 'sourceRefs': ['gxuDonationProjects'],
                            'note': '只表达局部顶冠和外挑帽的简化包络；17.19米宽、7米深、3米高、外挑0.5米、帽厚0.4米均为待核对估算。柱窗构成未还原；沿边位置和南北朝向仅为假设，不能写入生产。'},
        },
        'review': {
            'height': {'status': 'partial', 'note': '3.3米层高估算；主体23.1米，局部顶冠26.5米，非实测。'},
            'roof': {'status': 'partial', 'note': '顶冠位置、构架、窗柱和真实尺寸待核对。'},
            'entrances': {'status': 'partial', 'note': '原示意入口保留，不代表实景门位。'},
            'facadeRules': {'status': 'partial', 'note': '窗列仍为通用规则，端部外梯尚未生成。'},
        },
    }
    refs = {s['id'] for s in source_catalogue()}
    north = resolve_building(original, record, refs)
    south_record = copy.deepcopy(record)
    south_record['roofVolumes'][0].update(edge=1, **{'from': .29, 'to': .45})
    south = resolve_building(original, south_record, refs)
    assert north['polygons'] == south['polygons'] == original['polygons']
    assert north['form']['entrances'] == south['form']['entrances'] == original['form']['entrances']
    report = dict(buildingId=ID, original=original,
                  variants={'north': north, 'south': south},
                  records={'north': record, 'south': south_record},
                  sourceSha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  productionReady=False, productionModified=False,
                  assumptions=['3.3 m estimated storey height',
                               'Pavilion is a coarse solid envelope, not an asserted opaque wall',
                               'Two opposite facade hypotheses remain; neither has a registered camera',
                               'Along-wall interval and dimensions also remain estimates; the variants are not exhaustive'],
                  nextGate='Locate the photographed facade, pavilion and end stairs with independent visual anchors; then refine the open roof frame and pavilion facade before integration.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print('Two isolated hypotheses resolved; public data unchanged')


if __name__ == '__main__':
    main()
