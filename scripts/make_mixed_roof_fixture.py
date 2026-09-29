"""Generate a synthetic mixed-roof fixture; dimensions are not campus measurements."""
import argparse
import json
import math
from pathlib import Path
from building_overrides import resolve_parts


def fixture():
    cases=[]
    for angle in (0, math.radians(31)):
        def point(x,y):
            return [50+x*math.cos(angle)-y*math.sin(angle), -24+x*math.sin(angle)+y*math.cos(angle)]
        polygons=[[[point(x,y) for x,y in [(0,0),(9,0),(9,16),(0,16),(0,0)]]]]
        columns=[dict(center=point(x,y),width=.5,depth=.5,angle=angle,shape='cylinder')
                 for x,y in [(1,6),(8,6),(1,10),(8,10)]]
        roof=dict(type='flat',rise=0)
        part=dict(id='synthetic-portico',polygons=polygons,height=7.2,levels=1,
                  roof=roof,openBelow=dict(clearHeight=6.8,floorHeight=1.05,columns=columns,
                  slattedRoof=dict(edgeWidth=.8,slatWidth=.3,slatCount=7,solidBays=[2,3,4,5])))
        b=dict(id='synthetic-mixed-roof',height=7.2,polygons=polygons,tags={},category='academic')
        b['form']=dict(height=7.2,roof=roof,parts=resolve_parts(b,[part],roof),entrances=[],facades=[])
        cases.append(dict(angle=angle,building=b))
    return dict(scope='Synthetic component test only; not a platform position or size proposal',cases=cases)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.write_text(json.dumps(fixture(),indent=2)+'\n')
