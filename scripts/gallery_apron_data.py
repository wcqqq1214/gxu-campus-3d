"""Ground-floor galleries need a clear floor and a sourced exterior apron."""
import copy,math
from shapely.geometry import Polygon,box
from building_overrides import footprint_revision


def derive_gallery_apron(config,buildings,source_ids):
    from site_data import world_shape
    keys={'id','type','buildingId','footprintRevision','facade','apronDepth',
          'gradingFeather','groundClearance','meshStep','sourceRefs','evidence'}
    if set(config)!=keys or config['type']!='gallery-apron':raise ValueError('Invalid gallery apron fields')
    b=next((b for b in buildings if b['id']==config['buildingId']),None)
    if not b or footprint_revision(b)!=config['footprintRevision']:raise ValueError('Stale gallery building')
    anchor=config['facade']
    if not isinstance(anchor,dict) or set(anchor)!={'polygon','ring','edge','part'}:raise ValueError('Gallery apron needs a complete facade anchor')
    if any(type(anchor[k]) is not int or anchor[k]<0 for k in ('polygon','ring','edge')) or not isinstance(anchor['part'],str) or not anchor['part']:raise ValueError('Invalid gallery facade anchor')
    facades=[f for f in b.get('form',{}).get('facades',[]) if all(f.get(k)==v for k,v in anchor.items())]
    if len(facades)!=1:raise ValueError('Missing gallery facade')
    f=facades[0];corridor=f['rule'].get('openCorridor',{})
    if corridor.get('firstLevel')!=0 or 'piers' not in corridor:raise ValueError('Gallery apron requires an open ground floor with piers')
    if not config['sourceRefs'] or not set(config['sourceRefs'])<=source_ids:raise ValueError('Unknown gallery apron source')
    if not isinstance(config['evidence'],dict) or not config['evidence'] or not all(isinstance(v,str) and v.strip() for v in config['evidence'].values()):raise ValueError('Missing gallery apron evidence')
    for key,(lo,hi) in {'apronDepth':(.5,2),'gradingFeather':(1,4),'groundClearance':(.04,.2),'meshStep':(.25,1)}.items():
        if type(config[key]) not in (int,float) or not math.isfinite(config[key]) or not lo<=config[key]<=hi:raise ValueError('Invalid gallery apron '+key)
    half=math.dist(f['start'],f['end'])/2-corridor['endInset'];end=config['apronDepth'];feather=config['gradingFeather'];depth=corridor['depth']
    frame={'origin':[(a+b)/2 for a,b in zip(f['start'],f['end'])],'angle':-math.atan2(*f['normal'])}
    area=world_shape(box(-half,0,half,end),frame)
    grading=world_shape(box(-half-feather,-depth,half+feather,end+feather),frame)
    for other in buildings:
        for poly in other['polygons']:
            if area.intersection(Polygon(poly[0],poly[1:])).area>1e-5:raise ValueError('Gallery apron crosses a building')
            if other['id']!=b['id'] and grading.intersection(Polygon(poly[0],poly[1:])).area>1e-5:raise ValueError('Gallery grading crosses another building')
        for e in other.get('form',{}).get('entrances',[]):
            for kind in ('attachedPortico','stairFlight'):
                if kind in e and grading.intersection(Polygon(e[kind]['footprint'])).area>1e-5:raise ValueError('Gallery grading overlaps an entrance')
    return {**copy.deepcopy(config),**frame,'buildingCenter':b['center'],'resolvedFacade':copy.deepcopy(f),
            'halfWidth':half,'startY':0,'endY':end,'gradingStartY':-depth,'stairBaseHeight':0,
            'pavingPolygon':list(area.exterior.coords),'gradingBounds':list(grading.bounds),
            'gradingPolygon':list(grading.exterior.coords),'layer':'roads','material':'path'},area,grading
