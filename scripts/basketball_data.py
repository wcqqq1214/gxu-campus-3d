"""Derive basketball courts from mapped single-court footprints; no new POIs."""
import json,math
from pathlib import Path
import numpy as np
from shapely.geometry import shape,Polygon,Point,box
from shapely.ops import transform,unary_union
from prepare_geodata import project
from surroundings_data import triangulate,tiled_triangles
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'public/data'
def prepare_basketball():
    geo=json.loads((OUT/'geography.geojson').read_text());terrain=json.loads((OUT/'terrain.json').read_text());infra=json.loads((OUT/'infrastructure.json').read_text())
    courts=[];areas=[]
    for f in geo['features']:
        p=f['properties']
        if p['kind']!='sports' or p['tags'].get('sport')!='basketball':continue
        g=transform(project,shape(f['geometry']));rect=g.minimum_rotated_rectangle;corners=list(rect.exterior.coords)
        if g.area>700:
            areas.append({'osmId':f['id'],'sourceUrl':p['sourceUrl'],'note':'仅映射整体活动区，缺少独立场地布局；保留铺地，不绘制超大篮球场标线。'});continue
        a,b=max(zip(corners,corners[1:]),key=lambda v:math.dist(*v));dx,dy=b[0]-a[0],b[1]-a[1]
        if dy<0 or (abs(dy)<1e-8 and dx<0):dx,dy=-dx,-dy
        angle=math.atan2(-dx,dy);cx,cy=rect.centroid.coords[0]
        # Normalize only the playing rectangle, retaining OSM centers and axes.
        c,s=math.cos(angle),math.sin(angle)
        footprint=[[cx+x*c-y*s,cy+x*s+y*c] for x,y in [(-7.5,-14),(7.5,-14),(7.5,14),(-7.5,14),(-7.5,-14)]]
        courts.append({'id':'basketball-'+f['id'].split('/')[1],'osmId':f['id'],'center':[cx,cy],'rotation':angle,'footprint':footprint,'mappedFootprint':list(g.exterior.coords),'length':28,'width':15,'rimHeight':3.05,'insideCampus':p['insideCampus'],'sourceUrl':p['sourceUrl'],'osmVersion':p['osmVersion'],'osmEditedAt':p['osmEditedAt'],'precision':'OSM 中心与长轴；按 28×15 米标准比例归整，篮架、配色和缓冲铺装为视觉估算，非实测或赛事认证。'})
    pending=list(courts);groups=[]
    while pending:
        group=[pending.pop(0)]
        while True:
            added=[c for c in pending if any(Polygon(c['footprint']).distance(Polygon(a['footprint']))<10 for a in group)]
            if not added:break
            group+=added;pending=[c for c in pending if c not in added]
        groups.append(group)
    x0,y0,x1,y1=terrain['bounds'];cols,rows=terrain['cols'],terrain['rows'];hh=terrain['heights'];sx=(x1-x0)/(cols-1);sy=(y1-y0)/(rows-1)
    def elevation(x,y):
        u=max(0,min(cols-1.001,(x-x0)/sx));v=max(0,min(rows-1.001,(y-y0)/sy));i,j=int(u),int(v);a,b=u-i,v-j
        return (hh[j*cols+i]*(1-a)+hh[j*cols+i+1]*a)*(1-b)+(hh[(j+1)*cols+i]*(1-a)+hh[(j+1)*cols+i+1]*a)*b
    banks=[];cells=set();patches=[]
    for group in groups:
        key='basketball-bank-'+group[0]['osmId'].split('/')[1];ground=unary_union([Polygon(c['footprint']) for c in group]).convex_hull.buffer(.9,join_style=2)
        level=round(float(np.median([elevation(*c['center']) for c in group])),3)
        for court in group:court.update(bank=key,elevation=level+.22)
        halo=ground.buffer(1.5,join_style=2);ring=halo.difference(ground)
        banks.append({'id':key,'courtIds':[c['id'] for c in group],'elevation':level+.22,'ground':list(ground.exterior.coords),'paving':triangulate(ground),'terrainLevel':level,'bounds':list(halo.bounds)})
        def patch(g,height):
            t=tiled_triangles(g,step=4);t['vertices']=[[x,y,height(x,y)] for x,y in t['vertices']];patches.append(t)
        patch(ground,lambda x,y:level)
        patch(ring,lambda x,y:level+(elevation(x,y)-level)*min(1,ground.distance(Point(x,y))/1.5))
        for j in range(max(0,math.floor((halo.bounds[1]-y0)/sy)),min(rows-1,math.ceil((halo.bounds[3]-y0)/sy))):
            for i in range(max(0,math.floor((halo.bounds[0]-x0)/sx)),min(cols-1,math.ceil((halo.bounds[2]-x0)/sx))):
                cell=box(x0+i*sx,y0+j*sy,x0+(i+1)*sx,y0+(j+1)*sy)
                if not cell.intersects(halo):continue
                cell_id=j*(cols-1)+i
                assert cell_id not in infra['terrainCells'],'Basketball grading intersects bridge earthworks'
                assert cell_id not in cells,'Basketball grading halos share a DEM cell'
                cells.add(cell_id);patch(cell.difference(halo),elevation)
    data={'version':1,'snapshotAt':geo['metadata']['snapshotAt'],'basis':'既有 OSM 单场轮廓与 2024 FIBA 尺度参考；近期校方照片辅助通用配色，不声称逐场实测。','courts':courts,'banks':banks,'areas':areas,'terrainCells':sorted(cells),'terrainPatch':patches,'sourceRefs':['osm','sports2024','basketballEast2026','basketballRules2024']}
    trees=json.loads((OUT/'vegetation.json').read_text());mask=unary_union([Polygon(b['ground']) for b in banks])
    trees=[t for t in trees if mask.distance(Point(t[:2]))>4*t[2]/9+1]
    (OUT/'vegetation.json').write_text(json.dumps(trees,separators=(',',':')))
    overview=json.loads((OUT/'overview.json').read_text());overview['trees']=len(trees)
    (OUT/'overview.json').write_text(json.dumps(overview,ensure_ascii=False,indent=2)+'\n')
    (OUT/'basketball.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')))
    sources=json.loads((OUT/'sources.json').read_text());refs=json.loads((ROOT/'data/basketball-sources.json').read_text());ids={r['id'] for r in refs}
    sources['sources']=[r for r in sources['sources'] if r['id'] not in ids]+refs
    (OUT/'sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n')
    print(f'{len(courts)} courts, {len(banks)} banks, {len(cells)} local terrain cells; {len(areas)} aggregate areas retained')
if __name__=='__main__':prepare_basketball()
