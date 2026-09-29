"""Build an isolated estimated west-wing roof candidate; never edit production data."""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
from shapely.geometry import Polygon
from shapely.ops import unary_union
from building_overrides import resolve_building, source_catalogue

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
original = next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']=='way/759185166')
record = copy.deepcopy(json.loads((ROOT/'data/building-overrides.json').read_text())['buildings'][original['id']])
p = original['polygons'][0][0]
# Stable original vertices: detach only the west wing. Keep the start order of
# the main part so its central roof-eave edge remains the same physical edge.
main = [p[i] for i in [1,2,3,4,5,6,7,8,11,12,17,18,19,0,1]]
west = Polygon([p[i] for i in [12,13,14,15,16,17,12]])
u = [(p[15][i]-p[14][i])/math.dist(p[15],p[14]) for i in [0,1]]
t = [u[1],-u[0]]
def point(along,across):return [p[14][i]+u[i]*along+t[i]*across for i in [0,1]]
# Eight metres is a deliberately provisional depth, not a roof break measured
# from the image. Record six/ten-metre partition sensitivity below.
front = Polygon([point(-10,-50),point(-10,50),point(8,50),point(8,-50)])
terrace = west.intersection(front)
rear = west.difference(front)
assert all(g.geom_type=='Polygon' and g.is_valid for g in [terrace,rear])
pack=lambda g:[[list(map(list,g.exterior.coords))]]
record['parts'][0]['polygons']=[[main]]
record['parts'] += [dict(id='west-four-storeys-candidate',polygons=pack(rear),height=13.2,levels=4),dict(id='west-front-terrace-candidate',polygons=pack(terrace),height=9.9,levels=3)]
record['evidence']['parts']['sourceRefs'] += ['gxuAgricultureAnniversaryCandidate']
record['evidence']['parts']['note']='独立候选：院庆片约255秒显示西翼屋顶较主体低、南端露台再低。西翼4层/13.2米、露台下3层/9.9米、退台深8米为待验证假设，不是照片已确认层数或测绘分界；东翼、中央后翼和南门廊保持。'
record['review']['parts']['note']=record['evidence']['parts']['note']
candidate=resolve_building(original,record,{s['id'] for s in source_catalogue()}|{'gxuAgricultureAnniversaryCandidate'})
parts=[Polygon(q['polygons'][0][0]) for q in candidate['form']['parts']]
footprint=Polygon(original['polygons'][0][0]);combined=unary_union(parts)
assert combined.symmetric_difference(footprint).area<1e-7
assert sum(g.area for g in parts)-combined.area<1e-7
assert candidate['polygons']==original['polygons']
for key in ['entrances','roofEave']:
 assert candidate['form'][key]==original['form'][key],key
assert record['facadeRules']==json.loads((ROOT/'data/building-overrides.json').read_text())['buildings'][original['id']]['facadeRules']
# Bounds for later field/photo reconciliation, not confidence intervals.
sensitivity=[]
for depth in [6,8,10]:
 clip=Polygon([point(-10,-50),point(-10,50),point(depth,50),point(depth,-50)])
 sensitivity.append(dict(depthMeters=depth,terraceArea=west.intersection(clip).area))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
photos=['work/refinement-s3-agriculture-roof/anniversary-255s.png','work/refinement-s3-agriculture-roof/admission-25s.png']
result=dict(buildingId=original['id'],scope='Isolated provisional west-roof massing. No production replacement, photograph registration, measured dimensions or whole-building acceptance.',productionReady=False,original=original,candidate=candidate,candidateOverride=record,assumptions=dict(westLevels=4,westHeight=13.2,terraceSupportingLevels=3,terraceHeight=9.9,terraceDepth=8),sensitivity=sensitivity,partitionChecks=dict(footprintArea=footprint.area,symmetricDifferenceArea=combined.symmetric_difference(footprint).area,overlapArea=sum(g.area for g in parts)-combined.area,entranceAndCentralEavePreserved=True),source=dict(id='gxuAgricultureAnniversaryCandidate',url='https://nxy.gxu.edu.cn/xyzc/a90znyqxcsp.htm',frameSeconds=255,captureDate=None,observation='Lower western roof and a further lower front terrace are visible; storey counts and break location are unresolved.'),referenceImages={p:sha(ROOT/p) for p in photos},productionFingerprints={p:sha(ROOT/p) for p in ['data/building-overrides.json','public/data/buildings.json','public/data/models.json','blender/gxu-campus.blend']})
args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result['partitionChecks']));print(json.dumps(sensitivity))
