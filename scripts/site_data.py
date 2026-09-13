"""Small sourced forecourts; keep mapped footprints and existing surface slots."""
import copy,hashlib,json,math
from pathlib import Path
from shapely.geometry import Polygon,Point,LineString,box
from shapely.affinity import rotate,translate
from shapely.ops import unary_union
from building_overrides import read_json,footprint_revision
from building_forms import positive
from surroundings_data import surface_shape,triangulate,polys

ROOT=Path(__file__).resolve().parents[1]

def local_shape(shape,envelope):
    return translate(rotate(shape,-envelope['angle'],origin=envelope['origin'],use_radians=True),
                     -envelope['origin'][0],-envelope['origin'][1])

def world_shape(shape,envelope):
    return translate(rotate(shape,envelope['angle'],origin=(0,0),use_radians=True),*envelope['origin'])

def rings(shape):
    return [[list(p.exterior.coords)]+[list(r.coords) for r in p.interiors] for p in polys(shape)]

def road_columns(paving,x0,x1,start,search,step):
    """Cross-sections include every road edge bend, then subdivide laterally."""
    lo,hi=search
    window=box(x0,start+lo,x1,start+hi)
    nearby=paving.intersection(window)
    xs={x0,x1}
    for p in polys(nearby):
        for ring in [p.exterior,*p.interiors]:
            xs.update(x for x,y in ring.coords if x0<x<x1)
    breaks=[]
    for x in sorted(xs):
        if not breaks or x-breaks[-1]>1e-6:breaks.append(x)
    if x1-breaks[-1]<=1e-6:breaks[-1]=x1
    else:breaks.append(x1)
    xs=[]
    for a,b in zip(breaks,breaks[1:]):
        n=max(1,math.ceil((b-a)/step));xs.extend(a+(b-a)*i/n for i in range(n))
    xs.append(x1);columns=[]
    for x in xs:
        hit=paving.intersection(LineString([(x,start),(x,start+hi)]))
        if hit.is_empty or not lo<=hit.bounds[1]-start<=hi:
            raise ValueError('Road is missing or outside the expected entrance search range')
        columns.append([x,hit.bounds[1]])
    return columns

def derive_site(config,buildings,roads,source_ids):
    b=next((b for b in buildings if b['id']==config['buildingId']),None)
    if not b or config['footprintRevision']!=footprint_revision(b):
        raise ValueError('Unknown building or stale site footprint')
    e=b.get('architecture',{});entry=e.get('northEntry')
    if b.get('landmark')!='library' or not entry or config['entranceId']!=entry['id']:
        raise ValueError('Unsupported or missing site entrance')
    if not config['sourceRefs'] or not set(config['sourceRefs'])<=source_ids:
        raise ValueError('Unknown or missing site source')
    if not any(r['id']==config['roadId'] for r in roads['sources']):
        raise ValueError('Site road ID is not a prepared at-grade campus road')
    for key in ('gradingFeather','groundClearance','meshStep','joinOverlap','roadContactDepth','roadContactSideMargin'):
        positive(config[key],key)
    if not .25<=config['meshStep']<=2 or not .03<=config['groundClearance']<=.2:
        raise ValueError('Site mesh resolution or clearance outside supported range')
    if type(config['terrainSubdivisions']) is not int or not 4<=config['terrainSubdivisions']<=32:
        raise ValueError('Invalid terrain subdivision count')
    lo,hi=config['roadSearchDistance']
    if not 0<lo<hi<=100:raise ValueError('Invalid road search interval')
    if not all(isinstance(v,str) and v.strip() for v in config['evidence'].values()):
        raise ValueError('Site evidence notes must be present')
    # Union only nearby triangles; the rest of the campus road network is not
    # rewritten or retriangulated by a small entrance correction.
    cx=entry['centerX'];x0=cx-entry['width']/2;x1=cx+entry['width']/2
    start=entry['platformFrontY']+entry['stepCount']*entry['stepRun']
    nearby=world_shape(box(x0-1,start,x1+1,start+hi+1),e)
    pieces=[]
    for layer in roads['layers']:
        vs=layer['vertices'];ts=layer['triangles']
        for i in range(0,len(ts),3):
            p=Polygon([vs[k] for k in ts[i:i+3]])
            if p.intersects(nearby):pieces.append(p)
    paving=local_shape(unary_union(pieces),e)
    columns=road_columns(paving,x0,x1,start,[lo,hi],config['meshStep'])
    footprint=Polygon([(x0,start),(x1,start)]+list(reversed(columns)))
    if not footprint.is_valid or footprint.intersection(paving).area>1e-5:
        raise ValueError('Forecourt crosses prepared road paving')
    core=footprint.union(box(x0,entry['platformFrontY'],x1,start))
    area=world_shape(footprint,e);grading=world_shape(core.buffer(config['gradingFeather']),e)
    exclusions=[]
    for other in buildings:
        shape=unary_union([Polygon(p[0],p[1:]) for p in other['polygons']])
        if area.intersection(shape).area>1e-5:raise ValueError('Forecourt intersects a mapped building')
        if shape.intersects(grading):exclusions.extend(rings(local_shape(shape,e)))
    return {**copy.deepcopy(config),'origin':e['origin'],'angle':e['angle'],
            'buildingCenter':b['center'],'entry':entry,'startY':start,'columns':columns,
            'pavingPolygon':list(area.exterior.coords),'gradingCore':list(core.exterior.coords),
            'gradingBounds':list(grading.bounds),'gradingExclusions':exclusions,
            'layer':'roads','material':'path'},area,grading

def prepare_sites(root=ROOT):
    out=root/'public/data';catalogue=read_json(root/'data/site-overrides.json')
    if catalogue.get('schemaVersion')!=1 or set(catalogue)!={'schemaVersion','sites'}:
        raise ValueError('Site overrides require schemaVersion 1 and sites')
    ids=[s['id'] for s in catalogue['sites']]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate site ID')
    read=lambda name:json.loads((out/name).read_text())
    buildings=read('buildings.json');roads=read('campus-roads.json');ss=read('surfaces.json')
    infra=read('infrastructure.json');surround=read('surroundings.json')
    source_ids={s['id'] for s in read('sources.json')['sources']}
    sites=[];areas=[];gradings=[]
    for config in catalogue['sites']:
        if config.get('type')=='gallery-apron':
            from gallery_apron_data import derive_gallery_apron
            site,area,grading=derive_gallery_apron(config,buildings,source_ids)
        elif config.get('type')=='entry-apron':
            from entry_apron_data import derive_entry_apron
            site,area,grading=derive_entry_apron(config,buildings,source_ids)
        elif config.get('type') in ('side-connection','front-connection'):
            from side_connection_data import derive_side_connection
            from front_connection_data import derive_front_connection
            from shore_data import effective_surfaces
            effective=effective_surfaces(ss,[infra['surfaceOverrides'],surround['surfaceOverrides'],roads['surfaceOverrides']],set(infra['replaceSurfaceIds']))
            target=next((s for s in effective if s['id']==config['surfaceId']),None)
            derive=derive_front_connection if config['type']=='front-connection' else derive_side_connection
            site,area,grading=derive(config,buildings,target,source_ids)
        else:site,area,grading=derive_site(config,buildings,roads,source_ids)
        if any(grading.intersects(previous) for previous in gradings):raise ValueError('Overlapping site grading areas')
        sites.append(site);areas.append(area);gradings.append(grading)
    area=unary_union(areas);grading=unary_union(gradings);overrides={}
    for i,s in enumerate(ss):
        if s.get('suppressed') or s['id'] in infra['replaceSurfaceIds']:continue
        current={**s,**infra['surfaceOverrides'].get(str(i),{}),
                 **surround['surfaceOverrides'].get(str(i),{}),**roads['surfaceOverrides'].get(str(i),{})}
        shape=surface_shape(current)
        if s['kind'] in ('water','sports') and shape.intersection(area).area>1e-5:
            raise ValueError('Site conflicts with water or sports')
        cut=grading if s['kind']=='green' else area
        if shape.intersection(cut).area>1e-5:overrides[str(i)]=triangulate(shape.difference(cut))
    # Always filter the final pre-site tree list; never reseed or move survivors.
    from vegetation_data import apply_stage
    trees=read('vegetation.json');kept=apply_stage(trees,'sites',{s['id']:area for s,area in zip(sites,areas)},root)
    overview=read('overview.json');overview['trees']=len(kept)
    result={'schemaVersion':1,'sites':sites,'surfaceOverrides':overrides,
            'roadRevision':hashlib.sha256(json.dumps(roads['layers'],separators=(',',':')).encode()).hexdigest()}
    for name,value in [('sites.json',result),('vegetation.json',kept),('overview.json',overview)]:
        (out/name).write_text(json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n')
    report={'siteIds':ids,'surfaceSlotsPreserved':True,'overriddenSurfaceSlots':sorted(overrides),
            'removedTrees':[t for t in trees if t not in kept],'remainingTrees':len(kept),
            'pavingAreasMeters2':[round(a.area,3) for a in areas],'passed':True}
    report_path=root/'docs/model-checks/refinement/site-preparation.json'
    report_path.parent.mkdir(parents=True,exist_ok=True)
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Entrance sites prepared',report,flush=True)

if __name__=='__main__':prepare_sites()
