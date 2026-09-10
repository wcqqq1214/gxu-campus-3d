#!/usr/bin/env python3
"""Normalize OSM geometry, preserve courtyards, and assemble attributable scene data."""
import collections,datetime,json,math,random
from pathlib import Path
import numpy as np
from PIL import Image,ImageFilter
from shapely.geometry import Polygon,MultiPolygon,LineString,Point,mapping,shape,box
from shapely.ops import polygonize,unary_union,transform
from shapely import make_valid
from shapely.prepared import prep
import mapbox_earcut as earcut
from fetch_geodata import ROOT,CACHE,REGION,tile
from sports_data import prepare_sports
from architecture_data import architectural_envelope,clear_entrance_trees
OUT=ROOT/'public/data';OUT.mkdir(parents=True,exist_ok=True)
LON,LAT=REGION['center'];MX=111320*math.cos(math.radians(LAT));MY=111320

def project(lon,lat,z=None):return ((lon-LON)*MX,(lat-LAT)*MY)
def inverse(x,y,z=None):return (x/MX+LON,y/MY+LAT)
def polygons(g):return [g] if isinstance(g,Polygon) else list(g.geoms) if isinstance(g,MultiPolygon) else []
def geom(e):
    if e['type']=='node':return Point(project(e['lon'],e['lat']))
    if e['type']=='way':
        c=[project(p['lon'],p['lat']) for p in e.get('geometry',[]) if p]
        if len(c)<2:return None
        if len(c)>3 and c[0]==c[-1]:return make_valid(Polygon(c))
        return LineString(c)
    outer=[];inner=[]
    for m in e.get('members',[]):
        c=[project(p['lon'],p['lat']) for p in m.get('geometry',[]) if p]
        if len(c)<2:continue
        if m.get('role')=='inner':inner.append(LineString(c))
        elif m.get('role','') in ('outer','outline',''):outer.append(LineString(c))
    if not outer:return None
    g=unary_union(list(polygonize(unary_union(outer))))
    if inner:g=g.difference(unary_union(list(polygonize(unary_union(inner)))))
    return make_valid(g)
def feature_kind(t):
    if 'building' in t or t.get('amenity')=='library':return 'buildings'
    if t.get('natural')=='water' or t.get('waterway')=='riverbank':return 'water'
    if t.get('leisure') in ('pitch','track','swimming_pool'):return 'sports'
    if 'highway' in t:return 'roads'
    if t.get('landuse') in ('grass','forest','meadow','recreation_ground','village_green','orchard') or t.get('natural') in ('wood','scrub','grassland') or t.get('leisure') in ('park','garden'):return 'green'
    if t.get('natural')=='tree':return 'tree'
    return None
def category(t):
    name=t.get('name','');typ=t.get('building','')
    if typ in ('dormitory','apartments','residential','house') or any(s in name for s in ('宿舍','餐厅','公寓')):return 'living'
    if typ in ('stadium','sports_hall') or t.get('leisure')=='sports_hall' or any(s in name for s in ('体育','礼堂','活动')):return 'culture'
    if typ in ('school','university') or any(s in name for s in ('学院','教学','实验','图书')):return 'academic'
    return 'service'

def prepare():
    data=json.loads((CACHE/'osm.json').read_text()); elems=data['elements'];byid={(e['type'],e['id']):e for e in elems}
    campus=geom(byid[('way',398115378)]);clip=campus.buffer(300)
    # Only suppress member geometry after a usable parent has been assembled.
    skip=set()
    for e in elems:
        if e['type']=='relation' and feature_kind(e.get('tags',{})) and (g:=geom(e)) is not None and not g.is_empty:
            skip.update(m['ref'] for m in e.get('members',[]) if m['type']=='way' and m.get('role','') in ('outer','inner','outline','part',''))
    features=[];buildings=[]
    landmarks=json.loads((ROOT/'data/landmarks.json').read_text())
    lmids={l['osmId']:l for l in landmarks if l.get('osmId')}
    for e in elems:
        t=e.get('tags',{});kind=feature_kind(t)
        if not kind or (e['type']=='way' and e['id'] in skip):continue
        if e['type']=='node' and kind!='tree':continue
        g=geom(e)
        if g is None or g.is_empty or not g.intersects(clip):continue
        if kind=='roads' and (t.get('tunnel')=='yes' or t.get('highway') in ('proposed','construction','elevator','traffic_signals','crossing','bus_stop')):continue
        g=make_valid(g.intersection(clip)).simplify(.12,preserve_topology=True)
        if g.is_empty:continue
        if kind in ('buildings','green','water','sports') and not polygons(g):continue
        eid=f"{e['type']}/{e['id']}"; inside=campus.covers(g.representative_point());c=g.representative_point()
        props={'id':eid,'name':t.get('name',''),'kind':kind,'osmVersion':e.get('version'),'osmEditedAt':e.get('timestamp'),'sourceUrl':f'https://www.openstreetmap.org/{eid}','insideCampus':inside,'tags':t}
        if kind=='buildings':
            lm=lmids.get(eid);cat=category(t);estimated=not ('height' in t or 'building:levels' in t)
            defaults={'living':6,'academic':5,'culture':2,'service':3}
            try:levels=float(t.get('building:levels',defaults[cat]));height=float(t.get('height','').replace(' m','')) if t.get('height') else levels*3.3
            except ValueError:levels=defaults[cat];height=levels*3.3;estimated=True
            if lm:height=lm.get('height',height);cat=lm['category']
            coords=[]
            for p in polygons(g):coords.append([list(p.exterior.coords)]+[list(r.coords) for r in p.interiors])
            name=lm['name'] if lm else t.get('name') or f"{'校内' if inside else '周边'}建筑 {e['id']}"
            b={'id':eid,'name':name,'category':cat,'center':[round(c.x,2),round(c.y,2)],'height':height,'levels':levels,'insideCampus':inside,'landmark':lm['id'] if lm else None,'polygons':coords,'bounds':list(g.bounds),'heightBasis':'参考照片估算' if lm and 'height' in lm else '按类型估算' if estimated else 'OSM高度或层数','facadeBasis':'参考照片独立建模' if lm else '按建筑类型推定','osmVersion':e.get('version'),'osmEditedAt':e.get('timestamp'),'sourceUrl':props['sourceUrl'],'tags':t}
            b['constructionStatus']='OSM 标记施工中，完成状态待核对' if t.get('building')=='construction' or t.get('construction') else None
            if lm and lm['id']=='teaching-two':b['facadeBasis']='重点体量，立面按类型推定'
            if eid=='way/948683815':
                b['name']='西田径场主席台';b['category']='culture'
                b['facadeBasis']='2025 校方照片：开放主席台、白色挑檐、桁架及分色阶梯座席；尺寸估算'
                b['sourceRefs']=['osm','westTrack2025','westMeet2025']
            if lm and lm['id'] in ('library','international-residence','teaching-ten','teaching-six'):
                b['architecture']=architectural_envelope(b)
                b['facadeBasis']=lm['detail']
                if lm['id']=='teaching-six':b['sourceRefs']=['osm',lm['reference']]+lm.get('additionalReferences',[])
                if lm['id']=='teaching-ten':
                    b['heightBasis']=b['architecture']['heightBasis']
                    b['sourceRefs']=['osm',lm['reference']]+lm.get('additionalReferences',[])
            props.update({k:b[k] for k in ('name','category','height','heightBasis','facadeBasis','landmark')});buildings.append(b)
        features.append({'type':'Feature','id':eid,'properties':props,'geometry':mapping(transform(inverse,g))})
    # South gate uses the mapped road / campus boundary; its architectural extent is photo-estimated.
    for l in landmarks:
        b=next((b for b in buildings if b['id']==l.get('osmId')),None)
        if b:
            l['center']=b['center'];l['bounds']=b['bounds'];l['height']=b['height'];l['sourceUrl']=b['sourceUrl'];l['osmEditedAt']=b['osmEditedAt']
            if l['id']=='teaching-ten':l['osmVersion']=b['osmVersion']
        else:
            l['center']=list(project(*l['lonLat']));x,y=l['center']
            if l.get('placeKind')=='gate':
                # Gate nodes are POIs, not fabricated mapped building footprints.
                w,d=l['gateWidth'],l['gateDepth']
                if l['frontBearing'] in (90,270):w,d=d,w
                l['bounds']=[x-w/2,y-d/2,x+w/2,y+d/2]
                ref=l.get('osmId',l.get('positionRoad'));typ,num=ref.split('/')
                source=byid[(typ,int(num))]
                l['osmEditedAt']=source.get('timestamp');l['osmVersion']=source.get('version')
                props={'kind':'entrances','name':l['name'],'landmark':l['id'],'sourceUrl':l['sourceUrl'],
                       'osmEditedAt':l['osmEditedAt'],'osmVersion':l['osmVersion'],'positionBasis':l['positionBasis']}
                features.append({'type':'Feature','id':l['id'],'properties':props,
                                 'geometry':mapping(Point(l['lonLat']))})
            else:l['bounds']=[x-34,y-18,x+34,y+3]
        l['sourceRefs']=['osm',l['reference']]+l.get('additionalReferences',[])+(['sports2024'] if l['id']=='stadium' else [])
    surfaces=[]
    for f in features:
        kind=f['properties']['kind'];g=transform(project,shape(f['geometry']))
        if kind in ('buildings','tree'):continue
        if kind=='roads':
            t=f['properties']['tags'];width={'primary':18,'secondary':14,'tertiary':12,'residential':8,'service':5,'footway':2.2,'path':2,'steps':2}.get(t.get('highway'),5)
            if not polygons(g):g=g.buffer(width/2,cap_style=2,join_style=2)
        for p in polygons(g):
            rings=[list(p.exterior.coords)[:-1]]+[list(r.coords)[:-1] for r in p.interiors];v=[v for r in rings for v in r]
            tri=earcut.triangulate_float64(np.asarray(v,dtype=np.float64),np.cumsum([len(r) for r in rings],dtype=np.uint32)).tolist()
            surfaces.append({'id':f['id'],'kind':kind,'vertices':v,'triangles':tri,'insideCampus':f['properties']['insideCampus'],'tags':f['properties']['tags']})
    (OUT/'surfaces.json').write_text(json.dumps(surfaces,ensure_ascii=False,separators=(',',':')))
    geo={'type':'FeatureCollection','metadata':{'snapshotAt':data['osm3s']['timestamp_osm_base'],'retrievedAt':data.get('retrievedAt','2026-09-09'),'preparedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'license':'ODbL-1.0','attribution':'© OpenStreetMap contributors','region':REGION},'features':[{'type':'Feature','id':'campus','properties':{'kind':'campus','name':REGION['name']},'geometry':mapping(transform(inverse,campus))}]+features}
    (OUT/'geography.geojson').write_text(json.dumps(geo,ensure_ascii=False,separators=(',',':')))
    for b in buildings:
        b['roofTriangles']=[earcut.triangulate_float64(np.asarray([v for r in poly for v in r[:-1]],dtype=np.float64),np.cumsum([len(r)-1 for r in poly],dtype=np.uint32)).tolist() for poly in b['polygons']]
    (OUT/'buildings.json').write_text(json.dumps(buildings,ensure_ascii=False,separators=(',',':')))
    (OUT/'landmarks.json').write_text(json.dumps(landmarks,ensure_ascii=False,separators=(',',':')))
    # Sample and lightly filter coarse public DEM; spacing does not imply native survey resolution.
    w,s,e,n=REGION['bbox'];xmin,ymin=project(w,s);xmax,ymax=project(e,n);cols=125;rows=165;z=REGION['terrainZoom'];imgs={}
    raw=[]
    for j in range(rows):
        lat=s+(n-s)*j/(rows-1)
        for i in range(cols):
            lon=w+(e-w)*i/(cols-1);tx,ty=tile(lon,lat,z);key=(int(tx),int(ty))
            if key not in imgs:imgs[key]=Image.open(CACHE/f'terrain-{z}-{key[0]}-{key[1]}.png').convert('RGB')
            r,g,b=imgs[key].getpixel((min(255,int((tx%1)*256)),min(255,int((ty%1)*256))))
            raw.append(r*256+g+b/256-32768)
    a=np.array(raw).reshape(rows,cols)
    for _ in range(3):
        edge=np.pad(a,1,mode='edge')
        a=(a+edge[:-2,1:-1]+edge[2:,1:-1]+edge[1:-1,:-2]+edge[1:-1,2:])/5
    baseline=round(float(np.median(a)),2)
    # Local engineering corrections prevent coarse DEM from cutting through lakes or foundations.
    # Preserve the untouched raw DEM above; these are visual grading, not measured elevations.
    def sample(x,y):
        i=max(0,min(cols-1,round((x-xmin)/(xmax-xmin)*(cols-1))))
        j=max(0,min(rows-1,round((y-ymin)/(ymax-ymin)*(rows-1))))
        return float(a[j,i])
    grading=[]
    sports=prepare_sports(ROOT,features,project)
    for field in sports:
        ring=field['ground'][:-1]
        field['groundTriangles']=earcut.triangulate_float64(np.asarray(ring,dtype=np.float64),np.asarray([len(ring)],dtype=np.uint32)).tolist()
    for f in features:
        if f['properties']['kind']!='water':continue
        water=transform(project,shape(f['geometry']));c=water.representative_point();level=sample(c.x,c.y)
        grading.append((water.buffer(22),level-1.0,24))
        for surf in surfaces:
            if surf['id']==f['id']:surf['waterLevel']=round(level-baseline,2)
    for b in buildings:
        p=unary_union([Polygon(poly[0],poly[1:]) for poly in b['polygons']]);grading.append((p.buffer(4),sample(*b['center']),18))
    # Flatten all interpolation corners beneath each entire playing ground. A halo
    # at least one grid diagonal wide prevents coarse DEM cells piercing its edge.
    grid_diagonal=math.hypot((xmax-xmin)/(cols-1),(ymax-ymin)/(rows-1))
    for field in sports:
        level=round(sample(*field['center'])-baseline,2)
        field['elevation']=level
        grading.append((Polygon(field['ground']).buffer(grid_diagonal),level+baseline,24))
    (OUT/'sports.json').write_text(json.dumps(sports,ensure_ascii=False,indent=2))
    xx=np.linspace(xmin,xmax,cols);yy=np.linspace(ymin,ymax,rows)
    for region,height,fade in grading:
        x0,y0,x1,y1=region.buffer(fade).bounds
        for j in np.where((yy>=y0)&(yy<=y1))[0]:
            for i in np.where((xx>=x0)&(xx<=x1))[0]:
                weight=max(0,1-region.distance(Point(xx[i],yy[j]))/fade)
                a[j,i]=a[j,i]*(1-weight)+height*weight
    (OUT/'surfaces.json').write_text(json.dumps(surfaces,ensure_ascii=False,separators=(',',':')))
    terrain={'cols':cols,'rows':rows,'bounds':[xmin,ymin,xmax,ymax],'baseline':baseline,'rawHeights':raw,'heights':[round(float(h)-baseline,2) for h in a.flatten()],'source':json.loads((CACHE/'terrain-source.json').read_text())}
    (OUT/'terrain.json').write_text(json.dumps(terrain,separators=(',',':')))
    # Deterministic, schematic vegetation constrained to campus and mapped green spaces.
    bg=unary_union([shape(f['geometry']) for f in features if f['properties']['kind']=='buildings']);bg=transform(project,bg).buffer(5)
    waters=unary_union([transform(project,shape(f['geometry'])) for f in features if f['properties']['kind']=='water'])
    roads=[];greens=[]
    for f in features:
        p=f['properties'];g=transform(project,shape(f['geometry']))
        if p['kind']=='roads':roads.append(g.buffer(4 if p['tags'].get('highway') in ('footway','path','steps') else 8))
        if p['kind']=='green':greens.append(g)
    roadmask=unary_union(roads);greenmask=unary_union(greens)
    sportsmask=unary_union([transform(project,shape(f['geometry'])) for f in features if f['properties']['kind']=='sports'])
    valid=prep(campus.difference(unary_union([bg,waters.buffer(5),roadmask,sportsmask.buffer(3)])))
    greenmask=prep(greenmask)
    rng=random.Random(1928);trees=[]
    minx,miny,maxx,maxy=campus.bounds
    for y in np.arange(miny,maxy,13):
        for x in np.arange(minx,maxx,13):
            p=Point(x+rng.uniform(-4,4),y+rng.uniform(-4,4))
            if valid.contains(p) and rng.random()<(0.94 if greenmask.contains(p) else .55):trees.append([round(p.x,1),round(p.y,1),round(rng.uniform(9,17),1),rng.choices([0,1,2],[.66,.25,.09])[0]])
    # Filter AFTER generation to retain the random sequence and existing trees
    # elsewhere. Include canopy radius, not just trunks, at playing-area edges.
    grounds=unary_union([Polygon(field['ground']) for field in sports])
    west_stand=next(b for b in buildings if b['id']=='way/948683815')
    sx,sy=west_stand['center'];standmask=box(sx-11,sy-40,sx+11,sy+40)
    trees=[t for t in trees if grounds.distance(Point(t[0],t[1]))>4*t[2]/9+1
           and standmask.distance(Point(t[0],t[1]))>4*t[2]/9+1]
    trees=clear_entrance_trees(trees,buildings)
    gate_mask=unary_union([box(*l['bounds']).buffer(2) for l in landmarks if l.get('placeKind')=='gate'])
    trees=[t for t in trees if gate_mask.distance(Point(t[0],t[1]))>4*t[2]/9+1]
    (OUT/'vegetation.json').write_text(json.dumps(trees,separators=(',',':')))
    stats={'snapshotAt':geo['metadata']['snapshotAt'],'buildings':len(buildings),'campusBuildings':sum(b['insideCampus'] for b in buildings),'landmarks':len(landmarks),'trees':len(trees),'layers':dict(collections.Counter(f['properties']['kind'] for f in features)),'estimatedHeights':sum(b['heightBasis']=='按类型估算' for b in buildings),'editYears':dict(sorted(collections.Counter(b['osmEditedAt'][:4] for b in buildings if b['osmEditedAt']).items()))}
    (OUT/'overview.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2));print(json.dumps(stats,ensure_ascii=False))
if __name__=='__main__':
    prepare()
    from infrastructure_data import prepare_infrastructure
    prepare_infrastructure()
