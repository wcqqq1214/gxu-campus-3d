"""Style existing at-grade campus main roads; keep map axes, widths and side roads."""
import json
from pathlib import Path
from shapely.geometry import shape,Point
from shapely.ops import transform,unary_union,substring
from surroundings_data import surface_shape,triangulate,tiled_triangles
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'public/data'
MAIN_CLASSES={'residential','living_street','unclassified','tertiary','secondary','primary'}

def prepare_campus_roads():
    from prepare_geodata import project
    geo=json.loads((OUT/'geography.geojson').read_text());ss=json.loads((OUT/'surfaces.json').read_text())
    infra=json.loads((OUT/'infrastructure.json').read_text());surround=json.loads((OUT/'surroundings.json').read_text())
    byid={f['id']:f for f in geo['features']};campus=transform(project,shape(byid['campus']['geometry']))
    records=[];selected=[];roads=[];original={}
    for i,s in enumerate(ss):
        if s['kind']!='roads' or s.get('suppressed') or s['id'] in infra['replaceSurfaceIds']:continue
        f=byid.get(s['id']);t=s['tags']
        if not f or t.get('bridge') or t.get('tunnel') or str(t.get('layer','0'))!='0':continue
        current={**s,**infra['surfaceOverrides'].get(str(i),{}),**surround['surfaceOverrides'].get(str(i),{})}
        g=surface_shape(current);original[i]=g
        axis=transform(project,shape(f['geometry']))
        if axis.geom_type=='Polygon':axis=axis.boundary
        if axis.geom_type!='LineString':continue
        roads.append((s['id'],axis,t.get('highway')))
        if not f['properties'].get('insideCampus') or t.get('highway') not in MAIN_CLASSES or t.get('area')=='yes':continue
        part=g.intersection(campus)
        if part.is_empty:continue
        selected.append(part);records.append({'id':s['id'],'name':t.get('name','未命名主路'),'highway':t['highway'],'lengthMeters':round(axis.intersection(campus).length,2),'sourceUrl':f['properties']['sourceUrl'],'osmVersion':f['properties'].get('osmVersion'),'osmEditedAt':f['properties'].get('osmEditedAt')})
    area=unary_union(selected)
    # Reuse existing footprint; remove only intersections under the new finish.
    overrides={str(i):triangulate(g.difference(area)) for i,g in original.items() if g.intersects(area)}
    ids={r['id'] for r in records};other=unary_union([g for i,g in original.items() if ss[i]['id'] not in ids])
    curb=area.difference(area.buffer(-.28,join_style=2)).difference(other.buffer(.35))
    asphalt=area.difference(curb)
    junctions=[]
    main=[r for r in roads if r[0] in ids]
    for ident,line,typ in main:
        for otherid,otherline,othertype in roads:
            if ident==otherid or othertype in ('path','footway','steps','pedestrian') or not line.intersects(otherline):continue
            cross=line.intersection(otherline)
            junctions.extend([p for p in ([cross] if cross.geom_type=='Point' else getattr(cross,'geoms',[])) if p.geom_type=='Point'])
    quiet=unary_union(junctions).buffer(6)
    stripes=[]
    for ident,line,typ in main:
        if line.length<22:continue
        for start in range(8,int(line.length)-8,9):
            stripes.append(substring(line,start,min(start+3,line.length-8)).buffer(.09,cap_style=2))
    paint=unary_union(stripes).intersection(asphalt.buffer(-.75)).difference(quiet)
    asphalt=asphalt.difference(paint)
    layers=[dict(id='校园主路-'+label,material=mat,**tiled_triangles(g,step=8)) for label,mat,g in [('沥青','asphalt',asphalt),('浅色路缘','curb',curb),('中心虚线','roadYellow',paint)]]
    # User correction: the mapped lawn opposite Huixue's east facade is treeless.
    lawn=transform(project,shape(byid['way/822812174']['geometry']))
    trees=json.loads((OUT/'vegetation.json').read_text())
    kept=[t for t in trees if lawn.distance(Point(t[:2]))>4*t[2]/9+1]
    (OUT/'vegetation.json').write_text(json.dumps(kept,separators=(',',':')))
    overview=json.loads((OUT/'overview.json').read_text());overview['trees']=len(kept)
    (OUT/'overview.json').write_text(json.dumps(overview,ensure_ascii=False,indent=2)+'\n')
    data={'version':1,'scope':'校内同层主路；道路轴线和原路幅保留，小路及支路不作扩建。','basis':'借用崇左桥等下穿路面已有的 asphalt、curb、roadYellow 材质；中心虚线与路缘分带为展示估算，不声称逐条道路实测。','sources':records,'surfaceOverrides':overrides,'layers':layers,'lawn':{'osmId':'way/822812174','polygon':list(lawn.exterior.coords),'basis':'用户现场指正：汇学堂正对的东侧为无树草地；以 OSM 草地轮廓及树冠余量清除示意树。'}}
    (OUT/'campus-roads.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')))
    report={'roadFeatures':len(records),'roadMeters':round(sum(r['lengthMeters'] for r in records),2),'mainRoadArea':round(area.area,2),'pavingOverlap':round(asphalt.intersection(curb).area+asphalt.intersection(paint).area+curb.intersection(paint).area,8),'uncoveredArea':round(area.difference(unary_union([asphalt,curb,paint])).area,8),'trees':len(kept),'lawnRemainingTrees':sum(lawn.distance(Point(t[:2]))<=4*t[2]/9+1 for t in kept),'basis':data['basis']}
    assert report['pavingOverlap']<1e-5 and report['uncoveredArea']<1e-5 and report['lawnRemainingTrees']==0
    (ROOT/'docs/model-checks/campus-roads.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(report)

if __name__=='__main__':prepare_campus_roads()
