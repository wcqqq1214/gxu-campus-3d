"""Glazed portal return and a connected L-shaped canopy at a mapped corner."""
import copy
import math
from shapely.geometry import Polygon, LineString
from shapely.geometry.polygon import orient
from shapely.ops import unary_union


def resolve_flush_return(building, form, entry, config):
    from building_overrides import anchor, pack_geometry
    fields={'side','depth','bays','pierWidth','pierDepth','beamHeight','canopyProjection'}
    if not isinstance(config,dict) or set(config)!=fields or config['side'] not in ('start','end'):
        raise ValueError('Portal return needs side, glazing and canopy dimensions')
    if type(config['bays']) is not int or not 1<=config['bays']<=4:
        raise ValueError('Portal return needs 1–4 glazing bays')
    for key in fields-{'side','bays'}:
        if type(config[key]) not in (int,float) or not math.isfinite(config[key]):
            raise ValueError('Portal return dimensions must be finite numbers')
    p=entry['flushEntrance'];c=config
    if 'canopy' not in p:
        raise ValueError('Portal return requires the existing front canopy')
    if not 2<=c['depth']<=8 or not .25<=c['pierWidth']<=.65 or not .1<=c['pierDepth']<=.5 or not .25<=c['beamHeight']<=.8 or not .3<=c['canopyProjection']<=3:
        raise ValueError('Portal return dimensions outside supported ranges')
    if (c['depth']-.2)/c['bays']-c['pierWidth']<.7:
        raise ValueError('Portal return glazing bays too narrow')
    a,b,n,length=anchor(building,entry,exterior=True)
    ring=building['polygons'][entry['polygon']][0][:-1]
    start=c['side']=='start';corner=a if start else b
    neighbor=ring[(entry['edge']-1)%len(ring)] if start else ring[(entry['edge']+2)%len(ring)]
    return_edge=(entry['edge']-1)%len(ring) if start else (entry['edge']+1)%len(ring)
    side_length=math.dist(corner,neighbor);v=[(neighbor[k]-corner[k])/side_length for k in (0,1)]
    other=b if start else a;u=[(other[k]-corner[k])/length for k in (0,1)]
    if abs(sum(u[k]*v[k] for k in (0,1)))>.02 or c['depth']>side_length-.1:
        raise ValueError('Portal return needs a sufficiently long near-rectangular corner')
    normal=[v[1],-v[0]]
    if sum(normal[k]*u[k] for k in (0,1))>0:normal=[-x for x in normal]
    point=lambda s,t:[corner[k]+u[k]*s+v[k]*t for k in (0,1)]
    backing=Polygon([point(0,0),point(.5,0),point(.5,c['depth']),point(0,c['depth'])])
    wall_line=LineString([point(0,0),point(0,c['depth'])])
    parts=form['parts'] or [dict(id='body',polygons=building['polygons'],height=form['height'])]
    matches=[part for part in parts if unary_union([Polygon(r[0],r[1:]) for r in part['polygons']]).boundary.buffer(1e-7).covers(wall_line)]
    head=p['glazingHeight']+p['canopy']['thickness']
    if len(matches)!=1 or 'openBelow' in matches[0] or matches[0]['height']<head+.2:
        raise ValueError('Portal return needs one solid supporting wall above its canopy')
    support=unary_union([Polygon(r[0],r[1:]) for r in matches[0]['polygons']])
    if not support.buffer(1e-7).covers(backing):
        raise ValueError('Portal return corner is concave or lacks backing')
    # Join exactly to the near end of the existing front slab, including the small corner gap.
    gap=math.dist(corner,entry['center'])-p['canopy']['width']/2
    if not -1e-7<=gap<=2:
        raise ValueError('Portal return cannot reach the front canopy at this corner')
    gap=max(0,gap);front=p['canopy']['depth'];projection=c['canopyProjection']
    join=point(gap,0);join_front=[join[k]+n[k]*front for k in (0,1)]
    outer_front=[corner[k]+normal[k]*projection+n[k]*front for k in (0,1)]
    outer_rear=[corner[k]+normal[k]*projection+v[k]*c['depth'] for k in (0,1)]
    shape=orient(Polygon([join,join_front,outer_front,outer_rear,point(0,c['depth']),corner]),sign=1)
    body=unary_union([Polygon(r[0],r[1:]) for r in building['polygons']])
    if not shape.is_valid or shape.intersection(body).area>1e-5:
        raise ValueError('Portal return canopy overlaps another wing or has invalid geometry')
    polys,triangles=pack_geometry([shape])
    return {**copy.deepcopy(c),'corner':list(corner),'tangent':v,'normal':normal,'edge':return_edge,
            'part':matches[0]['id'],'canopyGeometry':dict(polygons=polys,triangles=triangles),'frontJoint':[join,join_front]}


def validate_return_facades(form,entry):
    p=entry['flushEntrance'];r=p.get('returnGlazing')
    if not r:return
    for facade in form.get('facades',[]):
        if facade['part']!=r['part'] or facade['polygon']!=entry['polygon'] or facade['ring']!=0 or facade['edge']!=r['edge']:continue
        rule=facade['rule']
        if any(k in rule for k in ('openCorridor','windowGrid','windowBands','attachedGallery')):
            raise ValueError('Portal return conflicts with another facade system')
        # Compare actual panel endpoints to the corner, for either mapped edge direction.
        length=math.dist(facade['start'],facade['end']);direction=[(facade['end'][k]-facade['start'][k])/length for k in (0,1)]
        for panel in rule.get('panels',[]):
            distances=[sum((facade['start'][k]+direction[k]*length*f-r['corner'][k])*r['tangent'][k] for k in (0,1)) for f in (panel['from'],panel['to'])]
            if min(distances)<r['depth'] and max(distances)>0 and panel['bottom']<p['glazingHeight']+p['canopy']['thickness']:
                raise ValueError('Facade panels overlap the portal return')
