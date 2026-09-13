"""Sourced, bounded shoreline grading masks; original water and roads stay fixed."""
import copy, hashlib, json, math
from pathlib import Path
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import unary_union
from building_overrides import read_json, source_catalogue
from surroundings_data import surface_shape, polys, triangulate

ROOT = Path(__file__).resolve().parents[1]

def revision(vertices):
    return hashlib.sha256(json.dumps(vertices,separators=(',',':')).encode()).hexdigest()

def geometry_rings(shape):
    return [[list(p.exterior.coords)]+[list(r.coords) for r in p.interiors] for p in polys(shape)]

def effective_surfaces(surfaces, overlays, replace_ids):
    result=[]
    for i,s in enumerate(surfaces):
        if s.get('suppressed') or s['id'] in replace_ids:continue
        current=copy.deepcopy(s)
        for overlay in overlays:current.update(overlay.get(str(i),{}))
        result.append(current)
    return result

def derive_shore(config,surfaces,buildings,roads,source_ids):
    fields={'id','waterId','shorelineRevision','edgeIndices','freeboard','capWidth','landWidth','endFeather','meshStep','safetyMargin','safetyFeather','sourceRefs','evidence'}
    if not isinstance(config,dict) or set(config)!=fields:raise ValueError('Unknown or missing shore field')
    if not isinstance(config['id'],str) or not config['id'].strip():raise ValueError('Invalid shore ID')
    s=next((s for s in surfaces if s['id']==config['waterId'] and s['kind']=='water'),None)
    if not s or revision(s['vertices'])!=config['shorelineRevision']:raise ValueError('Missing water or stale shoreline')
    refs=config['sourceRefs']
    if not isinstance(refs,list) or not refs or any(not isinstance(x,str) or x not in source_ids for x in refs):raise ValueError('Unknown shore source')
    evidence=config['evidence']
    if not isinstance(evidence,dict) or set(evidence)!={'location','form','dimensions','details'} or not all(isinstance(x,str) and x.strip() for x in evidence.values()):raise ValueError('Missing shore evidence')
    ranges={'freeboard':(.1,1.5),'capWidth':(.15,1),'landWidth':(2,15),'endFeather':(1,15),'meshStep':(.25,1.5),'safetyMargin':(.3,2),'safetyFeather':(.25,2)}
    for name,(lo,hi) in ranges.items():
        value=config[name]
        if type(value) not in (int,float) or not math.isfinite(value) or not lo<=value<=hi:raise ValueError('Invalid shore '+name)
    if config['capWidth']>=config['landWidth']:raise ValueError('Shore land width must exceed cap')
    vertices=s['vertices'];water=Polygon(vertices)
    if not water.is_valid or not s.get('insideCampus') or not math.isfinite(s.get('waterLevel',math.nan)):raise ValueError('Invalid shore water')
    indices=config['edgeIndices'];n=len(vertices)
    if not isinstance(indices,list) or not indices or len(indices)>=n-2 or any(type(i) is not int or not 0<=i<n for i in indices):raise ValueError('Invalid shore edge indices')
    if any(b!=(a+1)%n for a,b in zip(indices,indices[1:])):raise ValueError('Shore edges must be consecutive')
    core=[vertices[i] for i in indices]+[vertices[(indices[-1]+1)%n]]
    prev=vertices[(indices[0]-1)%n];after=vertices[(indices[-1]+2)%n]
    feather=config['endFeather']
    if min(math.dist(prev,core[0]),math.dist(core[-1],after))<=feather:raise ValueError('End feather exceeds adjacent shoreline edge')
    def toward(a,b,d):
        length=math.dist(a,b);return [a[0]+(b[0]-a[0])*d/length,a[1]+(b[1]-a[1])*d/length]
    path=[toward(core[0],prev,feather)]+core+[toward(core[-1],after,feather)]
    # A clockwise ring has land on its left; reverse for the opposite orientation.
    sign=-1 if water.exterior.is_ccw else 1
    line=LineString(path);core_line=LineString(core)
    band=line.buffer(sign*config['landWidth'],single_sided=True,join_style=2).difference(water)
    cap=core_line.buffer(sign*config['capWidth'],single_sided=True,join_style=2).difference(water)
    building_shapes=[Polygon(p[0],p[1:]) for b in buildings for p in b['polygons']]
    other_water=[surface_shape(x) for x in surfaces if x['kind']=='water' and x['id']!=s['id']]
    obstacles=unary_union([roads,*building_shapes,*other_water])
    safety=obstacles.buffer(config['safetyMargin'])
    if cap.intersection(safety).area>1e-7:raise ValueError('Shore cap conflicts with road/building/water safety margin')
    area=band.difference(safety)
    if area.is_empty or not area.is_valid or area.area<cap.area:raise ValueError('No usable shore land band')
    local_safety=safety.intersection(band.buffer(config['safetyFeather']+1))
    # Cross-sections and lateral splits constrain interpolation of the grade.
    direction=[]
    for a,b in zip(path,path[1:]):
        dx,dy=b[0]-a[0],b[1]-a[1];l=math.hypot(dx,dy);direction.append((-dy/l*sign,dx/l*sign))
    miters=[direction[0]]
    for a,b in zip(direction,direction[1:]):
        den=1+a[0]*b[0]+a[1]*b[1]
        if den<.25:raise ValueError('Shore corner too sharp for bounded offset')
        miters.append(((a[0]+b[0])/den,(a[1]+b[1])/den))
    miters.append(direction[-1]);stations=[];along=0
    for i,(a,b) in enumerate(zip(path,path[1:])):
        length=math.dist(a,b);steps=max(1,math.ceil(length/config['meshStep']))
        for j in range(steps):
            t=j/steps
            stations.append({'xy':[a[k]*(1-t)+b[k]*t for k in range(2)],'normal':[miters[i][k]*(1-t)+miters[i+1][k]*t for k in range(2)],'along':along+length*t})
        along+=length
    stations.append({'xy':path[-1],'normal':miters[-1],'along':along})
    offsets=sorted(set([0,config['capWidth'],config['landWidth']/3,config['landWidth']*2/3,config['landWidth']]))
    masks=[]
    def point(station,d):return [station['xy'][k]+station['normal'][k]*d for k in range(2)]
    for a,b in zip(stations,stations[1:]):
        for lo,hi in zip(offsets,offsets[1:]):
            piece=Polygon([point(a,lo),point(b,lo),point(b,hi),point(a,hi)]).intersection(area)
            data=triangulate(piece)
            for i in range(0,len(data['triangles']),3):masks.append([data['vertices'][k] for k in data['triangles'][i:i+3]])
    cover=unary_union([Polygon(t) for t in masks])
    if cover.symmetric_difference(area).area>1e-5:raise ValueError('Shore grading mesh does not cover its land band')
    result={**copy.deepcopy(config),'waterLevel':s['waterLevel'],'waterPolygon':vertices,'core':core,'path':path,'coreLength':core_line.length,'pathLength':line.length,'stations':stations,'outwardSign':sign,'gradingMasks':masks,'gradingPolygons':geometry_rings(area),'gradingBounds':list(area.bounds),'capPolygons':geometry_rings(cap),'safetyPolygons':geometry_rings(local_safety),'layer':'water','precision':'Photo-supported form and mapped boundary; dimensions and exact photo coverage estimated.'}
    return result,area,cap

def prepare_shores(root=ROOT):
    data=read_json(root/'data/shore-overrides.json')
    if set(data)!={'schemaVersion','shores'} or type(data['schemaVersion']) is not int or data['schemaVersion']!=1 or not isinstance(data['shores'],list):raise ValueError('Invalid shore catalogue')
    ids=[x['id'] for x in data['shores']]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate shore ID')
    out=root/'public/data';read=lambda name:json.loads((out/name).read_text())
    ss=read('surfaces.json');infra=read('infrastructure.json');campus=read('campus-roads.json');sites=read('sites.json');surround=read('surroundings.json')
    effective=effective_surfaces(ss,[infra['surfaceOverrides'],surround['surfaceOverrides'],campus['surfaceOverrides'],sites['surfaceOverrides']],set(infra['replaceSurfaceIds']))
    road_shapes=[surface_shape(s) for s in effective if s['kind']=='roads']
    for layer in campus['layers']+surround['layers']:
        vs=layer['vertices'];ts=layer['triangles'];road_shapes.extend(Polygon([vs[k] for k in ts[i:i+3]]) for i in range(0,len(ts),3))
    roads=unary_union(road_shapes);buildings=read('buildings.json');source_ids={s['id'] for s in source_catalogue(root)}
    records=[];areas=[];caps=[]
    for config in data['shores']:
        record,area,cap=derive_shore(config,effective,buildings,roads,source_ids)
        if any(area.intersects(other) for other in areas):raise ValueError('Overlapping shore grading bands')
        records.append(record);areas.append(area);caps.append(cap)
    trees=read('vegetation.json');mask=unary_union(caps)
    kept=[t for t in trees if mask.distance(Point(t[:2]))>4*t[2]/9+1]
    context={'surfaces':ss,'roads':campus,'surroundings':surround,'sites':sites,'infrastructure':infra,'buildings':[[b['id'],b['polygons']] for b in buildings]}
    context_revision=hashlib.sha256(json.dumps(context,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    result={'schemaVersion':1,'contextRevision':context_revision,'shores':records,'basis':'Only the sourced sampled shore is modeled; water and existing roads remain fixed.'}
    (out/'shores.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n')
    (out/'vegetation.json').write_text(json.dumps(kept,separators=(',',':'))+'\n')
    overview=read('overview.json');overview['trees']=len(kept);(out/'overview.json').write_text(json.dumps(overview,ensure_ascii=False,separators=(',',':'))+'\n')
    report={'shoreIds':ids,'areasMeters2':[a.area for a in areas],'capAreasMeters2':[a.area for a in caps],'removedTrees':[t for t in trees if t not in kept],'remainingTrees':len(kept),'surfaceSlotsAndWaterGeometryPreserved':True,'passed':True}
    folder=root/'docs/model-checks/refinement';folder.mkdir(parents=True,exist_ok=True);(folder/'shore-preparation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Shore preparation',report,flush=True)

if __name__=='__main__':prepare_shores()
