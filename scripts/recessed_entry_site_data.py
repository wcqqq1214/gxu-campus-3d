"""Ground contact for a photo-calibrated projecting recessed stair entry."""
import copy, math
from shapely.geometry import Polygon
from site_data import world_shape
from building_overrides import footprint_revision


def derive_recessed_entry_site(config, buildings, source_ids):
    keys={'id','type','buildingId','footprintRevision','entranceId','groundClearance','sourceRefs','evidence'}
    if set(config)!=keys or config['type']!='recessed-entry-ground':
        raise ValueError('Invalid recessed entry ground fields')
    b=next((b for b in buildings if b['id']==config['buildingId']),None)
    if not b or footprint_revision(b)!=config['footprintRevision']:
        raise ValueError('Stale recessed entry ground footprint')
    e=next((e for e in b.get('form',{}).get('entrances',[]) if e['id']==config['entranceId']),None)
    if not e or 'forecourt' not in e.get('recessedStairEntry',{}):
        raise ValueError('Ground repair needs a projecting recessed entry')
    if not config['sourceRefs'] or not set(config['sourceRefs'])<=source_ids:
        raise ValueError('Unknown recessed entry ground sources')
    if not config['evidence'] or not all(isinstance(v,str) and v.strip() for v in config['evidence'].values()):
        raise ValueError('Missing recessed entry ground evidence')
    c=config['groundClearance']
    if type(c) not in (int,float) or not math.isfinite(c) or not .04<=c<=.15:
        raise ValueError('Invalid recessed entry ground clearance')
    p=e['recessedStairEntry'];fw=p['apronFrontWidth']/2;pw=p['platformWidth']/2
    # Standard site axes use positive Y outward; entry stair D is inward.
    area=world_shape(Polygon([(-fw,-p['apronStart']),(fw,-p['apronStart']),
                             (pw,-p['toe']),(pw,0),(-pw,0),(-pw,-p['toe'])]),
                     {'origin':e['center'],'angle':-math.radians(e['bearing'])})
    if 'landscape' in p:
        from entry_forecourt_data import resolve_landscape
        from shapely.affinity import scale
        _,extra=resolve_landscape({k:v for k,v in p['landscape'].items() if k!='lowerEnd'},p)
        from shapely.geometry import box
        from shapely.ops import unary_union
        local=unary_union([extra,box(-fw,p['apronStart'],fw,p['landscape']['lowerEnd']),
                           box(-pw,p['toe'],pw,0)])
        area=world_shape(scale(local,xfact=1,yfact=-1,origin=(0,0)),
                         {'origin':e['center'],'angle':-math.radians(e['bearing'])})
    if area.geom_type!='Polygon' or area.interiors:
        raise ValueError('Entrance landscape must have a connected boundary')
    for other in buildings:
        if any(area.intersection(Polygon(poly[0],poly[1:])).area>1e-6 for poly in other['polygons']):
            raise ValueError('Projecting forecourt overlaps a mapped building')
    # Elevation is resolved against the build's terrain, as for other aprons.
    # A fresh data preparation has no model-build elevation cache.
    return {**copy.deepcopy(config),'entry':copy.deepcopy(e),'buildingCenter':b['center'],
            'pavingPolygon':list(area.exterior.coords),
            'gradingBounds':list(area.bounds),'layer':'roads','material':'stone'},area,area
