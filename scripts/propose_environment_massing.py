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
    parser.add_argument('--roof-details', action='store_true', help='Add unapproved open roof frame and pavilion windows')
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
    if args.roof_details:
        record['roofVolumes'][0].update(rise=6.0, glazing={
            'faces': {'outer':8, 'start':3}, 'sill':3.6, 'height':2.0,
            'margin':.35, 'frameWidth':.25, 'projection':.12})
        record['roofEdgeFrames'] = [dict(
            id='front-open-roof-frame', part='body', polygon=0, edge=3,
            **{'from':.01, 'to':.99}, inset=.8, rise=3.3, beamHeight=.4,
            beamDepth=.5, postCount=18, postWidth=.45, postDepth=.4)]
        record['evidence']['roof.type']['note'] = '历史照片可见平屋面、沿檐开敞梁柱与局部高顶冠；仅为候选。'
        record['evidence']['roofVolumes']['note'] = '按历史照片分出顶冠上部窗柱；6米上升、3.6米窗台、2米窗带及8/3列均为试配估算，不是测量。仅配置假设正面及起点端面，其余面未知。'
        record['evidence']['roofEdgeFrames'] = dict(status='estimated', sourceRefs=['gxuDonationProjects'],
            note='照片支持沿檐开敞构架；18柱、3.3米总高与截面为试配估算，不代表逐柱确认；朝向仍有南北假设。')
        record['review']['height']['note'] = '主体23.1米、构架26.4米、局部顶冠29.5米均基于估算，非摄影测量。'
        record['review']['roof']['note'] = '新增开敞梁柱和顶冠两面窗柱，朝向、相对尺度与柱数待验收。'
    refs = {s['id'] for s in source_catalogue()}
    north = resolve_building(original, record, refs)
    south_record = copy.deepcopy(record)
    south_record['roofVolumes'][0].update(edge=1, **{'from': .55 if args.roof_details else .29,
                                                  'to': .71 if args.roof_details else .45})
    if args.roof_details:
        south_record['roofEdgeFrames'][0]['edge'] = 1
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
    if args.roof_details:
        report.update(roofDetails=True,
                      assumptions=['3.3 m estimated storey height; roof frame rise 3.3 m; pavilion rise 6 m plus 0.4 m cap',
                                   '18 frame posts and 8/3 pavilion window panes are visual trial parameters, not measured counts',
                                   'Surface glazing does not model a room interior or a through-opening',
                                   'Only the hypothesized outer and start pavilion faces are detailed; other faces remain unknown',
                                   'South hypothesis now rotates longitudinal asymmetry too; prior south proposal did not',
                                   'Neither facade has an accepted camera registration; end stairs remain unmodeled'],
                      nextGate='Review roof composition, locate facade and end stairs using independent anchors; integrate only after source/base/near/site/budget checks.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print('Two isolated hypotheses resolved; public data unchanged')


if __name__ == '__main__':
    main()
