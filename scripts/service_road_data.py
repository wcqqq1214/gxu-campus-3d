"""A mapped at-grade service road, excluding retained neighboring road surfaces."""
import math
from shapely.geometry import Polygon,LineString,box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from surroundings_data import surface_shape,polys,triangulate
from shore_data import geometry_rings


def derive_service_road(config,effective,other_layers,trim,convex_masks):
    surface=next(s for s in effective if s['id']==config['surfaceId'])
    tags=surface['tags']
    if surface['kind']!='roads' or tags.get('highway')!='service' or tags.get('bridge') or tags.get('tunnel') or str(tags.get('layer','0'))!='0':
        raise ValueError('Ground repair requires an at-grade mapped service road')
    for key,lo,hi in [('offset',.06,.15),('burial',.02,.1),('joinFeather',1,5),('joinMeshStep',.5,2)]:
        if type(config[key]) not in (int,float) or not math.isfinite(config[key]) or not lo<=config[key]<=hi:
            raise ValueError('Invalid service-road dimension: '+key)
    footprint=surface_shape(surface).difference(trim)
    shapes=[surface_shape(s) for s in effective if s['kind']=='roads' and s['id']!=surface['id']]
    for layer in other_layers:
        vs,ts=layer['vertices'],layer['triangles']
        shapes.extend(Polygon([vs[k][:2] for k in ts[i:i+3]]) for i in range(0,len(ts),3))
    neighbors=unary_union(shapes)
    area=unary_union([orient(p,sign=1) for p in polys(footprint.difference(neighbors))])
    contacts=area.boundary.intersection(neighbors.buffer(.00001))
    lines=[contacts] if contacts.geom_type=='LineString' else [g for g in getattr(contacts,'geoms',[]) if g.geom_type=='LineString']
    if not lines:raise ValueError('Service road has no mapped contact to retain')
    transition=area.intersection(contacts.buffer(config['joinFeather'],cap_style=3,join_style=2))
    core=area.difference(transition)
    masks=convex_masks(core);core_mask_count=len(masks)
    step=config['joinMeshStep'];x0,y0,x1,y1=transition.bounds
    for ix in range(math.floor(x0/step),math.ceil(x1/step)):
        for iy in range(math.floor(y0/step),math.ceil(y1/step)):
            tiled=triangulate(transition.intersection(box(ix*step,iy*step,(ix+1)*step,(iy+1)*step)))
            masks.extend([tiled['vertices'][k] for k in tiled['triangles'][i:i+3]] for i in range(0,len(tiled['triangles']),3))
    cover=unary_union([Polygon(m) for m in masks])
    if cover.symmetric_difference(area).area>1e-6:raise ValueError('Incomplete service road repair masks')
    free=[]
    for p in polys(area):
        p=orient(p,sign=1)
        for ring in [p.exterior,*p.interiors]:
            for a,b in zip(ring.coords,list(ring.coords)[1:]):
                segment=LineString([a,b]).difference(neighbors.buffer(.00002))
                pieces=[segment] if segment.geom_type=='LineString' else list(getattr(segment,'geoms',[]))
                free.extend([list(p.coords) for p in pieces if p.geom_type=='LineString' and p.length>1e-6])
    return {**config,'bounds':list(area.bounds),'polygons':geometry_rings(area),'masks':masks,'coreMaskCount':core_mask_count,'cutMasks':convex_masks(area),
            'contacts':[list(line.coords) for line in lines],'freeEdges':free,
            'mappedArea':footprint.area,'repairArea':area.area,'retainedOverlapArea':footprint.intersection(neighbors).area,
            'corePolygons':geometry_rings(core),'transitionPolygons':geometry_rings(transition)}
