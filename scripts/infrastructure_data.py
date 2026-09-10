"""Reproducible public-road / bridge geometry; dimensions are visual estimates.

OSM remains the positional source. A separate derived corridor mask is NOT a
cadastral boundary. Exact terrain cuts keep the campus underpasses open even
though the historic DEM is much coarser than a bridge.
"""
import gzip,json,math
from pathlib import Path
import numpy as np
import mapbox_earcut as earcut
from shapely.geometry import Point,LineString,Polygon,box,mapping,shape
from shapely.geometry.polygon import orient
from shapely.ops import transform,unary_union,linemerge,substring
from prepare_geodata import ROOT,OUT,geom,project,inverse,polygons

SNAPSHOT=ROOT/'data/snapshots/infrastructure-2026-09-11.json.gz'
MAIN_BRIDGES=[
    ('chongzuo-bridge','崇左桥',699157425,[699156914],'chongzuo2023'),
    ('bocui-bridge','博萃桥',822812177,[699156911,759150546],'bridgeFlowers2023'),
    ('huixian-bridge','荟贤桥',822812179,[759332839],'huixian2025'),
]

def write(name,data):
    (OUT/name).write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')))

def triangulate(g):
    vertices=[];triangles=[]
    for p in polygons(g):
        rings=[list(p.exterior.coords)[:-1]]+[list(r.coords)[:-1] for r in p.interiors]
        v=[list(v) for r in rings for v in r]
        if len(v)<3:continue
        tri=earcut.triangulate_float64(np.asarray(v,dtype=np.float64),np.cumsum([len(r) for r in rings],dtype=np.uint32))
        triangles.extend(int(i)+len(vertices) for i in tri);vertices.extend(v)
    return {'vertices':vertices,'triangles':triangles}

def samples(line,step=3):
    return [list(line.interpolate(s).coords[0]) for s in np.linspace(0,line.length,max(2,math.ceil(line.length/step)+1))]

def path_frames(path):
    result=[]
    for i in range(len(path)):
        a=path[max(0,i-1)];b=path[min(len(path)-1,i+1)]
        dx=b[0]-a[0];dy=b[1]-a[1];length=math.hypot(dx,dy)
        result.append([dx/length,dy/length])
    return result

def strip_shape(path,axes,sections,left=2,right=3,extra=0):
    edges=[]
    for p,(ux,uy),section in zip(path,axes,sections):
        edges.append([(p[0]-uy*off,p[1]+ux*off) for off in [section[left]-extra,section[right]+extra]])
    return unary_union([Polygon([a[0],b[0],b[1],a[1]]) for a,b in zip(edges,edges[1:])])

def fit_road_sections(path,axes,buildings):
    # Keep mapped building footprints and road axes. Only the unsurveyed road
    # width changes; 2.2 m also reserves the generated entrances / balconies.
    obstacles=unary_union(buildings).buffer(2.2)
    def limits_at(p,axis):
        ux,uy=axis
        row=[]
        for sign in [-1,1]:
            ray=LineString([p[:2],(p[0]-uy*sign*7,p[1]+ux*sign*7)])
            hit=ray.intersection(obstacles)
            row.append(7.0 if hit.is_empty else Point(p[:2]).distance(hit)/math.hypot(ux,uy))
        return row
    # Check between road vertices too. Sampling only the stations misses a
    # building corner between two rays, even when the endpoints are clear.
    segment_limits=[]
    for i,(a,b) in enumerate(zip(path,path[1:])):
        values=[]
        for t in np.linspace(0,1,math.ceil(math.dist(a[:2],b[:2])/.35)+1):
            p=[a[k]*(1-t)+b[k]*t for k in [0,1]]
            axis=[axes[i][k]*(1-t)+axes[i+1][k]*t for k in [0,1]]
            values.append(limits_at(p,axis))
        segment_limits.append([min(v[k] for v in values) for k in [0,1]])
    limits=[[min(segment_limits[j][k] for j in {max(0,i-1),min(len(path)-2,i)}) for k in [0,1]] for i in range(len(path))]
    # A lower envelope starts each taper BEFORE the obstruction, and is shared
    # by neighbouring chunks. Avoid per-face clipping / abrupt notches in roads.
    for side in [0,1]:
        for order in [range(1,len(path)),range(len(path)-2,-1,-1)]:
            for i in order:
                j=i-1 if order.step>0 else i+1
                limits[i][side]=min(limits[i][side],limits[j][side]+.12*math.dist(path[i][:2],path[j][:2]))
    sections=[]
    for negative,positive in limits:
        walks=[min(2,max(1,width*2/7)) for width in [negative,positive]]
        section=[-negative+walks[0],positive-walks[1],-negative,positive]
        assert section[1]-section[0]>=5, 'Mapped clearance requires manual review; do not cut buildings or disconnect road'
        sections.append(section)
    return sections

def prepare_infrastructure():
    raw=json.loads(gzip.decompress(SNAPSHOT.read_bytes()));byid={e['id']:e for e in raw['elements']}
    geo=json.loads((OUT/'geography.geojson').read_text())
    campus=transform(project,shape(next(f for f in geo['features'] if f['id']=='campus')['geometry']))
    clip=campus.buffer(300)
    terrain=json.loads((OUT/'terrain.json').read_text());cols=terrain['cols'];rows=terrain['rows'];xmin,ymin,xmax,ymax=terrain['bounds'];hh=terrain['heights']
    def elevation(x,y):
        u=max(0,min(cols-1.001,(x-xmin)/(xmax-xmin)*(cols-1)));v=max(0,min(rows-1.001,(y-ymin)/(ymax-ymin)*(rows-1)))
        i=int(u);j=int(v);a=u-i;b=v-j
        return (hh[j*cols+i]*(1-a)+hh[j*cols+i+1]*a)*(1-b)+(hh[(j+1)*cols+i]*(1-a)+hh[(j+1)*cols+i+1]*a)*b
    def provenance(e):
        return {'osmId':f"way/{e['id']}",'osmVersion':e['version'],'osmEditedAt':e['timestamp'],
                'sourceUrl':f"https://www.openstreetmap.org/way/{e['id']}"}
    roadways=[e for e in raw['elements'] if e.get('tags',{}).get('name')=='农院路']
    road=linemerge([geom(e).intersection(clip) for e in roadways])
    assert isinstance(road,LineString),'The Nongyuan corridor must be connected'
    # Orient the chain from University East Road towards Luban Road.
    if road.coords[0][1]>road.coords[-1][1]:road=LineString(list(road.coords)[::-1])
    carriage=10.0;sidewalk=2.0;corridor=road.buffer(carriage/2+sidewalk+1,cap_style=2,join_style=2)
    bridges=[];cuts=[]
    for ident,name,upperid,lowerids,reference in MAIN_BRIDGES:
        upper=geom(byid[upperid]);lower=linemerge([geom(byid[i]) for i in lowerids])
        crossing=upper.intersection(lower)
        assert isinstance(crossing,Point),f'{name}: missing mapped crossing'
        distance=lower.project(crossing)
        approach=substring(lower,max(0,distance-85),min(lower.length,distance+85))
        # Estimated 4.5 m headroom includes the lowest exposed beam, not just the slab.
        deck=round(elevation(crossing.x,crossing.y)+.55,3)
        slab=.85;beam_depth=.245;clearance=4.5;floor=deck-slab-beam_depth-clearance
        under=lower.intersection(upper.buffer(carriage/2+sidewalk+1,cap_style=2))
        covered=under.length/2+1.5
        path=[];pedestrian_path=[]
        pedestrian_clearance=2.45
        pedestrian_floor=deck-slab-beam_depth-pedestrian_clearance
        pedestrian_inner=6.3;pedestrian_width=2.2;cut_half_width=8.65
        for x,y in samples(approach,2):
            signed=lower.project(Point(x,y))-distance;s=abs(signed)
            # Short approaches must meet the mapped T junction at ground level.
            available=min(80,distance if signed<0 else lower.length-distance)
            weight=min(1,max(0,(s-covered)/max(1,available-covered)))
            weight=weight*weight*(3-2*weight)
            natural=elevation(x,y)+.40
            vehicle_height=floor*(1-weight)+natural*weight
            path.append([x,y,round(vehicle_height,3),round(natural,3)])
            # Raised side walks have their own vertical alignment. The old rail
            # followed the untouched DEM and consequently cut through the deck.
            # Extend the flat section for the full side-walk width on skew crossings.
            walk_covered=covered+cut_half_width
            walk_weight=min(1,max(0,(s-walk_covered)/max(1,available-walk_covered)))
            walk_weight=walk_weight*walk_weight*(3-2*walk_weight)
            walk_height=max(vehicle_height+.15,pedestrian_floor*(1-walk_weight)+(natural+.15)*walk_weight)
            pedestrian_path.append([x,y,round(walk_height,3)])
        # Portal ends follow the actual crossing angle, rather than assumed E-W axes.
        p0=lower.interpolate(max(0,distance-.5));p1=lower.interpolate(min(lower.length,distance+.5))
        direction=np.array([p1.x-p0.x,p1.y-p0.y]);direction/=np.linalg.norm(direction)
        if direction[0]>0:direction=-direction
        bearing=math.degrees(math.atan2(direction[0],direction[1]))%360
        pick=upper.buffer(carriage/2+sidewalk+.4,cap_style=2)
        # A skew crossing can put one full-width rectangular abutment across a
        # side walk (Huixian). Reserve the complete pedestrian opening first.
        ends=list(upper.coords);cx=(ends[0][0]+ends[-1][0])/2;cy=(ends[0][1]+ends[-1][1])/2
        ux=(ends[-1][0]-ends[0][0])/upper.length;uy=(ends[-1][1]-ends[0][1])/upper.length
        def bridge_local(x,y,z=None):return ((x-cx)*ux+(y-cy)*uy,-(x-cx)*uy+(y-cy)*ux)
        opening=transform(bridge_local,approach.buffer(cut_half_width+.2,cap_style=2,join_style=2))
        abutments=[]
        for side in [-1,1]:
            x=side*(upper.length/2-.55)
            for p in polygons(box(x-.45,-7,x+.45,7).difference(opening)):
                p=orient(p,sign=1)
                rings=[list(map(list,p.exterior.coords))]+[list(map(list,r.coords)) for r in p.interiors]
                abutments.append({'rings':rings,'triangles':triangulate(p)['triangles']})
        item={'id':ident,'name':name,**provenance(byid[upperid]),'center':[crossing.x,crossing.y],
              'upper':list(map(list,upper.coords)),'underpass':path,'underpassWidth':10.0,
              'deckWidth':carriage+sidewalk*2,'deckElevation':deck,'slabThickness':slab,'beamDepth':beam_depth,'clearance':clearance,
              'floorElevation':floor,'lowerRoadIds':[f'way/{i}' for i in lowerids],
              'abutments':abutments,
              'pedestrian':{'path':pedestrian_path,'innerOffset':pedestrian_inner,'width':pedestrian_width,
                  'clearance':pedestrian_clearance,'cutHalfWidth':cut_half_width,
                  'basis':('崇左桥两侧抬高步道依据用户现场指正，2023 年校方坡道照片辅助核对内侧护栏与挡墙。' if ident=='chongzuo-bridge' else '两侧步道采用通用连通构造估算，尚无近期完整桥洞照片核实。')+'步道宽度、高程、坡度与净空为视觉估算。'},
              'lowerSources':[provenance(byid[i]) for i in lowerids],
              'frontBearing':bearing,'bounds':list(pick.bounds),'pickPolygon':list(map(list,pick.exterior.coords)),
              'portalCenter':[crossing.x+direction[0]*covered,crossing.y+direction[1]*covered],
              'reference':reference,'topologyBasis':'OSM bridge=yes、layer=1 标记农院路上跨；校内道路下穿。',
              'nameBasis':'桥名由校方资料与相交校道位置匹配；农院路 OSM 桥段未直接标注 bridge:name。',
              'dimensionBasis':'车道宽、桥面宽、净高、坡度、桥墩数量及跨径分配为视觉估算，非工程测量。'}
        bridges.append(item)
        # Remove ground below the full deck as well as the lower passage. Coarse
        # DEM / Draco rounding can otherwise expose grass through the bridge road.
        deck_cut=upper.buffer(carriage/2+sidewalk-.1,cap_style=2,join_style=2)
        cuts.append(unary_union([approach.buffer(cut_half_width,cap_style=2,join_style=2),deck_cut]))
    # Smooth the public road into each estimated deck, independently of the lower road.
    bridge_ranges=[];deck_stations=[]
    for b in bridges:
        # The crossing is not necessarily at the midpoint of the upper span.
        # Align the flat wearing surface to BOTH mapped bridge endpoints.
        start,end=sorted(road.project(Point(p)) for p in [b['upper'][0],b['upper'][-1]])
        bridge_ranges.append(((start+end)/2,(end-start)/2,b['deckElevation']))
        deck_stations.extend([start,end])
    # Round unsurveyed sharp polyline corners within the estimated road width.
    # Shared smooth stations keep wide sidewalks from folding inside a bend.
    regular_stations=np.linspace(0,road.length,math.ceil(road.length/3)+1).tolist()
    # Replace nearby regular stations instead of creating centimetre-long
    # segments whose offset sidewalk / paint edges can fold at a corner.
    stations=sorted(set([s for s in regular_stations if s in (0,road.length) or
                        all(abs(s-end)>=1.5 for end in deck_stations)]+deck_stations))
    rawpoints=[list(road.interpolate(s).coords[0]) for s in stations];renderpoints=[];sigma=7.0
    for i,p in enumerate(rawpoints):
        station=stations[i]
        weights=[(j,math.exp(-.5*((stations[j]-station)/sigma)**2)) for j in range(max(0,i-9),min(len(rawpoints),i+10)) if abs(stations[j]-station)<=21.01]
        total=sum(w for _,w in weights)
        smooth=[sum(rawpoints[j][k]*w for j,w in weights)/total for k in [0,1]]
        blend=min(1,station/21,(road.length-station)/21)
        for center,half,_ in bridge_ranges:blend=min(blend,max(0,min(1,(abs(station-center)-half-6)/21)))
        renderpoints.append([p[k]*(1-blend)+smooth[k]*blend for k in [0,1]])
    # Preserve the original source line and mask while including rounded display edges.
    corridor=unary_union([corridor,LineString(renderpoints).buffer(carriage/2+sidewalk+1,cap_style=2,join_style=2)])
    roadpoints=[]
    for x,y in renderpoints:
        s=road.project(Point(x,y));z=elevation(x,y)+.40
        for center,half,height in bridge_ranges:
            gap=abs(s-center)-half
            w=max(0,min(1,1-gap/22));w=w*w*(3-2*w)
            z=z*(1-w)+height*w
        roadpoints.append([x,y,round(z,3)])
    roadframes=path_frames(roadpoints)
    # At exact bridge ends, use the bridge normal rather than averaging in the
    # curved approach. Otherwise one road edge extends beyond the slab end.
    for bridge in bridges:
        start,end=sorted(road.project(Point(p)) for p in bridge['upper'])
        a=road.interpolate(start);c=road.interpolate(end);length=a.distance(c)
        for i,p in enumerate(roadpoints):
            if start-1e-6<=road.project(Point(p[:2]))<=end+1e-6:
                roadframes[i]=[(c.x-a.x)/length,(c.y-a.y)/length]
    building_data=json.loads((OUT/'buildings.json').read_text())
    building_shapes=[unary_union([Polygon(p[0],p[1:]) for p in b['polygons']]) for b in building_data]
    sections=fit_road_sections(roadpoints,roadframes,building_shapes)
    pavement=strip_shape(roadpoints,roadframes,sections)
    minimum_footprint_clearance=pavement.distance(unary_union(building_shapes))
    assert minimum_footprint_clearance>2.15, 'Road taper cuts a building corner between stations'
    # This display mask follows the fitted roadway, not the old uniform strip
    # that excluded parts of buildings from the campus display area.
    corridor=strip_shape(roadpoints,roadframes,sections,extra=1)
    assert not corridor.intersects(unary_union(building_shapes)), 'Road display mask overlaps a mapped building'
    clearance_records=[]
    old_strip=LineString(roadpoints).buffer(8,cap_style=2)
    for b,g in zip(building_data,building_shapes):
        overlap=g.intersection(old_strip).area
        if overlap>.01:
            clearance_records.append({'id':b['id'],'name':b['name'],'previousOverlapSquareMeters':round(overlap,3)})
    for index,b in enumerate(bridges):
        start,end=sorted(road.project(Point(p)) for p in [b['upper'][0],b['upper'][-1]])
        indices=[i for i,p in enumerate(roadpoints) if start-1e-6<=road.project(Point(p[:2]))<=end+1e-6]
        profile={'path':[roadpoints[i] for i in indices],'frames':[roadframes[i] for i in indices],
                 'sections':[sections[i] for i in indices]}
        b['roadProfile']=profile
        if all(abs(s[2]+7)<1e-6 and abs(s[3]-7)<1e-6 for s in profile['sections']):continue
        deck_shape=strip_shape(profile['path'],profile['frames'],profile['sections'])
        a,c=b['upper'][0],b['upper'][-1];cx=(a[0]+c[0])/2;cy=(a[1]+c[1])/2
        length=math.dist(a,c);ux=(c[0]-a[0])/length;uy=(c[1]-a[1])/length
        def local(x,y,z=None):return ((x-cx)*ux+(y-cy)*uy,-(x-cx)*uy+(y-cy)*ux)
        local_deck=orient(transform(local,deck_shape),sign=1)
        b['deckGeometry']={'rings':[list(map(list,local_deck.exterior.coords))],
                           'triangles':triangulate(local_deck)['triangles']}
        abutments=[]
        for abutment in b['abutments']:
            for piece in polygons(Polygon(abutment['rings'][0],abutment['rings'][1:]).intersection(local_deck)):
                piece=orient(piece,sign=1)
                abutments.append({'rings':[list(map(list,piece.exterior.coords))], 'triangles':triangulate(piece)['triangles']})
        b['abutments']=abutments
        pick=deck_shape.buffer(.4)
        b['bounds']=list(pick.bounds);b['pickPolygon']=list(map(list,pick.exterior.coords))
        cuts[index]=unary_union([LineString([p[:2] for p in b['underpass']]).buffer(b['pedestrian']['cutHalfWidth'],cap_style=2,join_style=2),deck_shape.buffer(-.1)])
    # Open railings at mapped at-grade junctions; an underpass is not a street entrance.
    roadnodes={n for e in roadways for n in e.get('nodes',[])};junctions=[]
    for e in raw['elements']:
        if e in roadways or 'highway' not in e.get('tags',{}):continue
        for n,p in zip(e.get('nodes',[]),e.get('geometry',[])):
            if n in roadnodes and p:junctions.append(list(project(p['lon'],p['lat'])))
    waterfeatures=[f for f in geo['features'] if f['properties']['kind']=='water']
    waters=unary_union([transform(project,shape(f['geometry'])) for f in waterfeatures])
    waterlevels={s['id']:s.get('waterLevel') for s in json.loads((OUT/'surfaces.json').read_text()) if s['kind']=='water'}
    lakebridges=[]
    for e in raw['elements']:
        tags=e.get('tags',{})
        if tags.get('bridge')!='yes' or tags.get('highway') not in ('residential','service','footway') or tags.get('indoor')=='yes' or e in roadways:continue
        line=geom(e)
        if not line.within(clip) or not line.intersects(waters):continue
        width=8 if tags['highway']=='residential' else 3 if tags['highway']=='footway' else 4.5
        relevant=[waterlevels.get(f['id']) for f in waterfeatures if line.intersects(transform(project,shape(f['geometry'])))]
        level=max([z for z in relevant if z is not None],default=-2)
        length=line.length;ends=list(line.coords);h0=max(elevation(*ends[0])+.45,level+1);h1=max(elevation(*ends[-1])+.45,level+1)
        path=[]
        for x,y in samples(line,2):
            t=line.project(Point(x,y))/length
            path.append([x,y,round(h0*(1-t)+h1*t+math.sin(math.pi*t)*.35,3)])
        lakebridges.append({'id':f"lake-bridge-{e['id']}",'name':tags.get('name','湖上桥梁')+'（OSM '+str(e['id'])+'）',
            **provenance(e),'width':width,'path':path,'waterLevel':level,'bounds':list(line.buffer(width/2).bounds),
            'precision':'位置及跨水关系来自 OSM；桥面、栏杆、桥墩和高度为通用估算，不据此认定桥名或实测形制。'})
    cut=unary_union(cuts)
    # Exact polygon clipping of every intersecting coarse terrain cell preserves voids.
    terrain_cells=[];terrain_patch=[]
    for j in range(rows-1):
        for i in range(cols-1):
            x0=xmin+(xmax-xmin)*i/(cols-1);x1=xmin+(xmax-xmin)*(i+1)/(cols-1)
            y0=ymin+(ymax-ymin)*j/(rows-1);y1=ymin+(ymax-ymin)*(j+1)/(rows-1)
            cell=box(x0,y0,x1,y1)
            if not cell.intersects(cut):continue
            terrain_cells.append(j*(cols-1)+i)
            t=triangulate(cell.difference(cut));t['vertices']=[[x,y,elevation(x,y)] for x,y in t['vertices']]
            terrain_patch.append(t)
    replace_ids={f"way/{e['id']}" for e in roadways}|{b['osmId'] for b in lakebridges}
    overrides={}
    surfaces=json.loads((OUT/'surfaces.json').read_text())
    for i,surface in enumerate(surfaces):
        if surface['id'] in replace_ids or surface['kind']=='water':continue
        verts=surface['vertices'];indices=surface['triangles']
        x0,y0,x1,y1=LineString(verts).bounds
        if not cut.intersects(box(x0,y0,x1,y1)):continue
        parts=[]
        for j in range(0,len(indices),3):
            p=Polygon([verts[k] for k in indices[j:j+3]])
            if p.area>0:parts.append(p.difference(cut))
        overrides[str(i)]=triangulate(unary_union(parts))
    result={'version':1,'snapshotAt':raw['osm3s']['timestamp_osm_base'],'retrievedAt':raw['retrievedAt'],
        'attribution':'© OpenStreetMap contributors','license':'ODbL-1.0','units':'meters','axes':['east','north','up'],
        'corridor':{'id':'nongyuan-road','name':'农院路','publicRoad':True,'insideCampus':False,
          'path':roadpoints,'carriageWidth':carriage,'sidewalkWidth':sidewalk,'lengthMeters':round(road.length,1),
          'sections':sections,'frames':roadframes,
          'clearance':{'buildingBufferMeters':2.2,'affectedBuildings':clearance_records,
                       'minimumFootprintClearanceMeters':round(minimum_footprint_clearance,3),
                       'minimumCarriageWidthMeters':round(min(s[1]-s[0] for s in sections),3),
                       'basis':'保留 OSM 建筑轮廓与道路轴线，按建筑及生成式入口、阳台避让收窄估算路幅并渐变衔接；桥面边缘同步调整。宽度及余量为展示参数，非实测或交通设计。'},
          'curveBasis':'原 OSM 中心线保存在 GeoJSON；展示路径对尖角做约 7 米尺度的平滑过渡，桥段及道路端点保持对齐。',
          'maximumCenterlineAdjustmentMeters':round(max(math.dist(a,b) for a,b in zip(rawpoints,renderpoints)),3),
          'bounds':list(corridor.bounds),'junctions':junctions,'sourceWays':[provenance(e) for e in roadways],
          'boundaryBasis':'公共道路关系依据用户现场指正；校方记录提及农院路围墙周边绿化养护。带状掩膜按估算路幅生成，仅供展示，非权属或通行权限边界。',
          'detailBasis':'围墙配色与黑色栅栏、三角梅参考 2023 校方局部照片；红色铺装、盲道、灯杆参考 2025 荟贤桥路段照片。该照片不能确认农院路全线外观；延伸到公共道路的铺装、围栏及灯杆分布为示意配置。'},
        'bridges':bridges,'lakeBridges':lakebridges,'replaceSurfaceIds':sorted(replace_ids),
        'terrainCells':terrain_cells,'terrainPatch':terrain_patch,'surfaceOverrides':overrides}
    # Partition small near models without adding the entire road to initial downloads.
    chunks=[];all_buildings=unary_union(building_shapes)
    for start in range(0,len(roadpoints)-1,90):
        pts=roadpoints[start:min(start+91,len(roadpoints))]
        fence=[]
        for i,p in enumerate(pts):
            a=pts[max(0,i-1)];b=pts[min(len(pts)-1,i+1)];dx=b[0]-a[0];dy=b[1]-a[1];length=math.hypot(dx,dy)
            on_bridge=any(LineString(bridge['upper']).distance(Point(p[:2]))<1 and Point(p[:2]).distance(Point(bridge['center']))<LineString(bridge['upper']).length/2+1 for bridge in bridges)
            row=[]
            for k,side in enumerate([-1,1]):
                off=sections[start+i][k+2]+side*.7;ux,uy=roadframes[start+i]
                position=Point(p[0]-uy*off,p[1]+ux*off)
                row.append(not on_bridge and campus.contains(position) and all_buildings.distance(position)>3.2 and all(math.dist(p[:2],q)>9 for q in junctions))
            fence.append(row)
        chunks.append({'id':f'infra-road-{start//90:02d}','kind':'corridor','path':pts,'frames':roadframes[start:start+len(pts)],
                       'sections':sections[start:start+len(pts)],'fence':fence,'bounds':list(LineString([p[:2] for p in pts]).buffer(10).bounds)})
    for bridge in lakebridges:
        chunks.append({'id':'infra-'+bridge['id'],'kind':'lake','bridgeId':bridge['id'],'bounds':bridge['bounds']})
    result['chunks']=chunks
    write('infrastructure.json',result)
    # Retain the original polygon and original insideCampus tag explicitly.
    geo['features']=[f for f in geo['features'] if f['id'] not in replace_ids and f['properties']['kind'] not in ('public-corridor','campus-display-area','bridge-poi')]
    for e in roadways+[byid[int(b['osmId'].split('/')[1])] for b in lakebridges]:
        g=geom(e).intersection(clip);public=e in roadways
        geo['features'].append({'type':'Feature','id':f"way/{e['id']}",'geometry':mapping(transform(inverse,g)),
            'properties':{'id':f"way/{e['id']}",'kind':'roads','name':e['tags'].get('name',''),
              'tags':e['tags'],**provenance(e),'snapshotAt':result['snapshotAt'],
              'insideCampus':False if public else campus.covers(g.representative_point()),
              'withinOsmCampusOutline':campus.covers(g.representative_point()),'publicRoad':public}})
    for ident,kind,g,name in [('nongyuan-public-corridor','public-corridor',corridor,'农院路公共道路走廊（估算路幅）'),
                             ('campus-display-area','campus-display-area',campus.difference(corridor),'校园展示范围（扣除农院路估算路幅）')]:
        geo['features'].append({'type':'Feature','id':ident,'properties':{'kind':kind,'name':name,'derived':True,'basis':result['corridor']['boundaryBasis']},'geometry':mapping(transform(inverse,g))})
    landmarks=[l for l in json.loads((OUT/'landmarks.json').read_text()) if l.get('placeKind')!='bridge']
    for b in bridges:
        recent='2023 年校方照片核对下穿坡道、排水沟与圆形护栏；桥洞总体结构仅有 2013 年历史照片辅助。' if b['id']=='chongzuo-bridge' else '近期校方资料核对桥名、路段或围栏；尚缺近期完整桥体照片，结构依据 OSM 层级与通用构造估算。'
        landmarks.append({'id':b['id'],'name':b['name'],'placeKind':'bridge','category':'infrastructure',
            **{k:b[k] for k in ('osmId','osmEditedAt','osmVersion','center','bounds','sourceUrl','frontBearing','reference','pickPolygon','portalCenter')},
            'height':b['deckElevation']-b['floorElevation']+1.3,'elevation':b['floorElevation'],
            'approachPath':[p[:3] for p in b['underpass']],
            'distance':90,'zone':'roads','cameraOffset':[-1,.75,1],
            'description':f"{b['name']}连接农院路两侧校园。农院路是公共道路，校内通道从桥下穿行，两者在这里分层交叉。",
            'detail':recent+' '+b['pedestrian']['basis']+' 净高、路幅、跨径分配、桥墩及未见于照片的构件为视觉估算。',
            'sourceRefs':['infrastructureOsm',b['reference'],'bridgeMaintenance2024']+(['chongzuoReport2013','chongzuoHistoric2013','chongzuoRoute2025'] if b['id']=='chongzuo-bridge' else ['bocuiNotice2023'] if b['id']=='bocui-bridge' else ['bridgeNamingGuide']),
            'additionalReferences':['bridgeMaintenance2024']+(['chongzuoReport2013','chongzuoHistoric2013','chongzuoRoute2025'] if b['id']=='chongzuo-bridge' else ['bocuiNotice2023'] if b['id']=='bocui-bridge' else ['bridgeNamingGuide'])})
        geo['features'].append({'type':'Feature','id':b['id'],'properties':{'kind':'bridge-poi','name':b['name'],'landmark':b['id'],'osmId':b['osmId'],'sourceUrl':b['sourceUrl']},'geometry':mapping(Point(inverse(*b['center'])))})
    geo['metadata']['infrastructureSnapshotAt']=result['snapshotAt']
    geo['metadata']['campusDisplayBoundaryNote']=result['corridor']['boundaryBasis']
    write('geography.geojson',geo);write('landmarks.json',landmarks)
    trees=json.loads((OUT/'vegetation.json').read_text());mask=unary_union([corridor,cut]+[LineString([p[:2] for p in b['path']]).buffer(b['width']/2) for b in lakebridges])
    trees=[t for t in trees if mask.distance(Point(t[:2]))>4*t[2]/9+1]
    write('vegetation.json',trees)
    overview=json.loads((OUT/'overview.json').read_text());overview.update(landmarks=len(landmarks),trees=len(trees),
        infrastructureSnapshotAt=result['snapshotAt'],publicRoadMeters=result['corridor']['lengthMeters'],bridges=len(bridges)+len(lakebridges))
    write('overview.json',overview)
    write('infrastructure-map.json',{'path':[[round(p[0],1),round(p[1],1)] for p in roadpoints[::6]]+[roadpoints[-1][:2]],'note':'农院路为公共道路；带状宽度仅供识别。'})
    print(f"农院路 {road.length:.0f} m；3 座校道立交、{len(lakebridges)} 座跨水桥；{len(terrain_cells)} 个地形单元精确开口")

if __name__=='__main__':prepare_infrastructure()
