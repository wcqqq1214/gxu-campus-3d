"""Bounded exterior stair study; not registered as a production override yet."""
import copy
import math
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union


def resolve_switchback_stairs(building, config):
    from building_overrides import anchor
    fields = {'polygon','ring','edge','t','flightWidth','gap','landingDepth','tread',
              'risers','levels','slabThickness','railHeight','railThickness','firstLane'}
    if not isinstance(config,dict) or set(config) != fields:
        raise ValueError('Stair study needs complete anchor and dimensions')
    c = config
    if any(type(c[k]) is not int or c[k]<0 for k in ('polygon','ring','edge')) or c['ring'] != 0:
        raise ValueError('Stair study needs an exterior edge')
    if type(c['risers']) is not int or not 8 <= c['risers'] <= 16:
        raise ValueError('Stair study needs 8–16 risers per half flight')
    if type(c['firstLane']) is not int or c['firstLane'] not in (-1,1):
        raise ValueError('Stair study needs an explicit first lane')
    if (not isinstance(c['levels'],list) or not 2 <= len(c['levels']) <= 11
            or any(type(x) not in (int,float) or not math.isfinite(x) for x in c['levels'])):
        raise ValueError('Stair study needs finite landing levels')
    for key in fields-{'polygon','ring','edge','risers','levels','firstLane'}:
        if type(c[key]) not in (int,float) or not math.isfinite(c[key]):
            raise ValueError('Stair study dimensions must be finite numbers')
    if (not 0 < c['t'] < 1 or not 1.2 <= c['flightWidth'] <= 2.4
            or not .1 <= c['gap'] <= .6 or not .8 <= c['landingDepth'] <= 2
            or not .25 <= c['tread'] <= .4 or not .25 <= c['slabThickness'] <= .5
            or not .8 <= c['railHeight'] <= 1.3 or not .1 <= c['railThickness'] <= .25
            or c['flightWidth']-2*c['railThickness'] < .9):
        raise ValueError('Stair study dimensions outside supported bounds')
    rises = [(hi-lo)/(2*c['risers']) for lo,hi in zip(c['levels'],c['levels'][1:])]
    if (not 0 <= c['levels'][0] <= 1 or any(not .12 <= r <= .2 for r in rises)
            or c['slabThickness'] <= max(rises)+.05):
        raise ValueError('Stair study rise or waist thickness invalid')
    form = building['form']
    if (form['parts'] or 'stairTower' in form or form['roof']['type'] != 'flat'
            or c['levels'][-1] > form['height']+1e-7):
        raise ValueError('Stair study currently needs one solid full-height body')
    a,b,n,length = anchor(building,c,exterior=True)
    width = 2*c['flightWidth']+c['gap']
    if min(c['t'],1-c['t'])*length < width/2+.2:
        raise ValueError('Stair study does not fit its facade')
    u = [(b[k]-a[k])/length for k in (0,1)]
    center = [a[k]+(b[k]-a[k])*c['t'] for k in (0,1)]
    run = (c['risers']-1)*c['tread']; depth = run+2*c['landingDepth']
    point = lambda along,out:[center[k]+u[k]*along+n[k]*out for k in (0,1)]
    footprint = Polygon([point(-width/2,0),point(width/2,0),point(width/2,depth),point(-width/2,depth)])
    body = unary_union([Polygon(p[0],p[1:]) for p in building['polygons']])
    seam = LineString([point(-width/2,0),point(width/2,0)])
    if not body.boundary.buffer(1e-6).covers(seam) or footprint.intersection(body).area > 1e-5:
        raise ValueError('Stair study overlaps the building footprint')
    return {**copy.deepcopy(c),'center':center,'tangent':u,'normal':list(n),'width':width,
            'run':run,'depth':depth,'footprint':[list(p) for p in footprint.exterior.coords]}


def validate_stair_study_neighbors(owner_id, stairs, buildings):
    footprint = Polygon(stairs['footprint'])
    for b in buildings:
        if b['id'] != owner_id:
            body = unary_union([Polygon(p[0],p[1:]) for p in b['polygons']])
            if footprint.intersection(body).area > 1e-5:
                raise ValueError(f'Stair study intersects neighbor {b["id"]}')
