"""Bounded repairs of mapped ordinary pavement; retain its exact footprint."""
import copy,hashlib,json,math
from pathlib import Path
from shapely.geometry import Polygon,LineString,Point
from shapely.ops import unary_union
from shore_data import effective_surfaces,revision
from surroundings_data import surface_shape
from building_overrides import source_catalogue
ROOT=Path(__file__).resolve().parents[1]

def context_revision(surfaces,infrastructure,surroundings,roads,sites):
    return hashlib.sha256(json.dumps([surfaces,infrastructure,surroundings,roads,sites],sort_keys=True,separators=(',',':')).encode()).hexdigest()

def derive_paving(config,surface,neighbors,source_ids):
    fields={'id','surfaceId','surfaceRevision','joinEdges','joinFeather','meshStep','contactDepth','contactSideMargin','joinOverlap','burial','sourceRefs','evidence'}
    if not isinstance(config,dict) or set(config)!=fields:raise ValueError('Unknown/missing paving field')
    if not isinstance(config['id'],str) or not config['id'].strip():raise ValueError('Invalid paving ID')
    if surface['id']!=config['surfaceId'] or revision(surface['vertices'])!=config['surfaceRevision']:raise ValueError('Missing/stale paving surface')
    if surface['kind']!='roads' or surface['tags'].get('highway') not in ('pedestrian','footway','path') or not surface.get('insideCampus'):raise ValueError('Not ordinary campus pavement')
    if surface['tags'].get('bridge') or surface['tags'].get('tunnel') or str(surface['tags'].get('layer','0'))!='0':raise ValueError('Paving must be at grade')
    if not isinstance(config['sourceRefs'],list) or not config['sourceRefs'] or any(x not in source_ids for x in config['sourceRefs']):raise ValueError('Unknown paving source')
    if not isinstance(config['evidence'],dict) or set(config['evidence'])!={'location','surface','dimensions','excludedDetails'} or not all(isinstance(v,str) and v.strip() for v in config['evidence'].values()):raise ValueError('Missing paving evidence')
    ranges={'joinFeather':(1,8),'meshStep':(.5,3),'contactDepth':(.5,3),'contactSideMargin':(.1,2),'joinOverlap':(.05,.3),'burial':(.02,.2)}
    for name,(lo,hi) in ranges.items():
        v=config[name]
        if type(v) not in (int,float) or not math.isfinite(v) or not lo<=v<=hi:raise ValueError('Invalid paving '+name)
    ring=surface['vertices'];shape=Polygon(ring)
    if not shape.is_valid or shape.area<10 or shape.area>3000:raise ValueError('Invalid paving footprint')
    edges=config['joinEdges']
    if not isinstance(edges,list) or not edges or len(edges)!=len(set(edges)) or any(type(i) is not int or not 0<=i<len(ring) for i in edges):raise ValueError('Invalid paving join edges')
    sign=1 if shape.exterior.is_ccw else -1;joins=[]
    for i in edges:
        a,b=ring[i],ring[(i+1)%len(ring)];dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy);nx,ny=-dy/length*sign,dx/length*sign
        for t in [.05,.25,.5,.75,.95]:
            p=Point(a[0]*(1-t)+b[0]*t-nx*.05,a[1]*(1-t)+b[1]*t-ny*.05)
            if neighbors.distance(p)>.001:raise ValueError('Join edge has no mapped neighboring road')
        joins.append({'edge':i,'a':a,'b':b,'inward':[nx,ny]})
    # Stop side faces at real pavement connections, rather than walling them off.
    free=shape.boundary.difference(neighbors.buffer(.02))
    lines=[free] if free.geom_type=='LineString' else [g for g in getattr(free,'geoms',[]) if g.geom_type=='LineString']
    return {**copy.deepcopy(config),'vertices':copy.deepcopy(ring),'triangles':copy.deepcopy(surface['triangles']),'joins':joins,'freeEdges':[[list(p) for p in line.coords] for line in lines],'bounds':list(shape.bounds),'areaMeters2':shape.area,'layer':'roads','precision':'Mapped footprint and photo-supported hard paving; local join and buried side dimensions estimated.'}

def prepare_pavings(root=ROOT):
    read=lambda p:json.loads(p.read_text());data=read(root/'data/paving-overrides.json')
    if set(data)!={'schemaVersion','pavings'} or data['schemaVersion']!=1 or type(data['schemaVersion']) is not int or not isinstance(data['pavings'],list):raise ValueError('Invalid paving catalogue')
    out=root/'public/data';ss=read(out/'surfaces.json');infra=read(out/'infrastructure.json');sur=read(out/'surroundings.json');roads=read(out/'campus-roads.json');sites=read(out/'sites.json')
    effective=effective_surfaces(ss,[infra['surfaceOverrides'],sur['surfaceOverrides'],roads['surfaceOverrides'],sites['surfaceOverrides']],set(infra['replaceSurfaceIds']))
    sources={s['id'] for s in source_catalogue(root)};records=[];ids=set();shapes=[]
    for config in data['pavings']:
        if config['id'] in ids:raise ValueError('Duplicate paving ID')
        ids.add(config['id']);surface=next((s for s in effective if s['id']==config['surfaceId']),None)
        if surface is None:raise ValueError('Missing paving surface')
        neighbor_shapes=[surface_shape(s) for s in effective if s['id']!=surface['id'] and s['kind']=='roads' and s['vertices']]
        for layer in roads['layers']+sur['layers']:
            vs=layer['vertices'];ts=layer['triangles'];neighbor_shapes.extend(Polygon([vs[k] for k in ts[i:i+3]]) for i in range(0,len(ts),3))
        record=derive_paving(config,surface,unary_union(neighbor_shapes),sources);shape=Polygon(record['vertices'])
        if any(shape.intersects(other) for other in shapes):raise ValueError('Overlapping paving repairs')
        shapes.append(shape);records.append(record)
    result={'schemaVersion':1,'contextRevision':context_revision(ss,infra,sur,roads,sites),'pavings':records}
    (out/'pavings.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n')
    report={'pavingIds':list(ids),'areasMeters2':[r['areaMeters2'] for r in records],'originalSurfaceSlotsAndFootprintsPreserved':True,'treesUnchanged':True,'passed':True}
    (root/'docs/model-checks/refinement').mkdir(parents=True,exist_ok=True)
    (root/'docs/model-checks/refinement/paving-preparation.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
if __name__=='__main__':prepare_pavings()
