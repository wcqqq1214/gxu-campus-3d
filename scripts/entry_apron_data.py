"""A sourced short entrance apron without inventing a mapped road connection."""
import copy,math
from shapely.geometry import Polygon,box
from shapely.ops import unary_union
from building_overrides import footprint_revision


def derive_entry_apron(config,buildings,source_ids):
    from site_data import world_shape
    keys={'id','type','buildingId','footprintRevision','entranceId','apronDepth',
          'gradingFeather','groundClearance','meshStep','sourceRefs','evidence'}
    if set(config)!=keys or config['type']!='entry-apron':raise ValueError('Invalid entry apron fields')
    b=next((b for b in buildings if b['id']==config['buildingId']),None)
    if not b or footprint_revision(b)!=config['footprintRevision']:raise ValueError('Stale apron building')
    entry=next((e for e in b.get('form',{}).get('entrances',[]) if e['id']==config['entranceId']),None)
    if not entry or 'stairFlight' not in entry:raise ValueError('Apron requires explicit stairs')
    if not config['sourceRefs'] or not set(config['sourceRefs'])<=source_ids:raise ValueError('Unknown apron source')
    if not isinstance(config['evidence'],dict) or not config['evidence'] or not all(isinstance(v,str) and v.strip() for v in config['evidence'].values()):raise ValueError('Missing apron evidence')
    for key,(lo,hi) in {'apronDepth':(.5,3),'gradingFeather':(1,4),'groundClearance':(.04,.2),'meshStep':(.25,1)}.items():
        if type(config[key]) not in (int,float) or not math.isfinite(config[key]) or not lo<=config[key]<=hi:raise ValueError('Invalid apron '+key)
    p=entry['stairFlight'];half=p['width']/2;front=p['front'];end=front+config['apronDepth'];feather=config['gradingFeather']
    frame={'origin':entry['center'],'angle':-math.radians(entry['bearing'])}
    area=world_shape(box(-half,front,half,end),frame)
    grading=world_shape(box(-half-feather,0,half+feather,end+feather),frame)
    for other in buildings:
        shape=unary_union([Polygon(poly[0],poly[1:]) for poly in other['polygons']])
        if grading.intersection(shape).area>1e-5:raise ValueError('Apron grading crosses a mapped building')
        for e in other.get('form',{}).get('entrances',[]):
            if other['id']==b['id'] and e['id']==entry['id']:continue
            for kind in ('attachedPortico','stairFlight'):
                if kind in e and grading.intersection(Polygon(e[kind]['footprint'])).area>1e-5:raise ValueError('Apron grading overlaps another entrance')
    return {**copy.deepcopy(config),**frame,'buildingCenter':b['center'],'entry':copy.deepcopy(entry),
            'halfWidth':half,'startY':front,'endY':end,'stairBaseHeight':p['baseHeight'],
            'pavingPolygon':list(area.exterior.coords),'gradingBounds':list(grading.bounds),
            'gradingPolygon':list(grading.exterior.coords),'layer':'roads','material':'path'},area,grading
