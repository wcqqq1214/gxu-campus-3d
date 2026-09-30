"""Local mesh repair masks; do not alter DEM samples or building datums."""
import math
import json
from pathlib import Path
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
from shore_data import effective_surfaces, geometry_rings
from surroundings_data import surface_shape, triangulate

ROOT = Path(__file__).resolve().parents[1]
from foundation_contract import foundation_context, revision


def convex_masks(shape):
    data = triangulate(shape)
    pieces = [Polygon([data['vertices'][k] for k in data['triangles'][i:i+3]])
              for i in range(0,len(data['triangles']),3)]
    # Shared triangulation diagonals are not grading boundaries. Merge convex
    # neighbors before clipping actual terrain to avoid needless sliver fans.
    changed = True
    while changed:
        changed = False
        for i,a in enumerate(pieces):
            for j in range(i+1,len(pieces)):
                b = pieces[j]
                if a.boundary.intersection(b.boundary).length < 1e-7: continue
                merged = a.union(b)
                if merged.geom_type == 'Polygon' and merged.convex_hull.area-merged.area < 1e-7:
                    pieces[i] = merged.convex_hull; pieces.pop(j); changed = True; break
            if changed: break
    return [list(p.exterior.coords)[:-1] for p in pieces]


def prepare_foundations(root=ROOT):
    context = foundation_context(root)
    config = context['config']
    if config.get('schemaVersion') != 1:
        raise ValueError('Unknown foundation repair schema')
    effective = effective_surfaces(context['surfaces'],
        [context[k]['surfaceOverrides'] for k in ('infrastructure', 'surroundings', 'campus-roads', 'sites')],
        set(context['infrastructure']['replaceSurfaceIds']))
    records = []
    if len({i['id'] for i in config['foundations']}) != len(config['foundations']):
        raise ValueError('Duplicate foundation repair ID')
    for item in config['foundations']:
        simplification=item.get('meshSimplification',{})
        if not isinstance(simplification,dict) or set(simplification)-{'normalTolerance','weldDistance'}:
            raise ValueError('Invalid foundation mesh simplification')
        for key,default,minimum in [('normalTolerance',1e-6,1e-8),('weldDistance',0,0)]:
            value=simplification.get(key,default)
            if type(value) not in (int,float) or not math.isfinite(value) or not minimum<=value<=1e-4:
                raise ValueError('Invalid foundation mesh simplification tolerance')
        for key in ('coreMargin','roadTrimMargin','haloMeters','groundOffset'):
            if type(item[key]) not in (int,float) or not math.isfinite(item[key]):
                raise ValueError('Invalid foundation dimension')
        if not -.1 <= item['groundOffset'] <= 0:
            raise ValueError('Invalid foundation floor offset')
        b = next(b for b in context['buildings'] if b['id'] == item['buildingId'])
        if not 0 < item['coreMargin'] < item['roadTrimMargin'] < item['haloMeters'] <= 8:
            raise ValueError('Invalid local foundation margins')
        closed = unary_union([Polygon(p[0], p[1:]) for part in b['form']['parts']
                              if not part.get('openBelow') for p in part['polygons']])
        core = closed.buffer(item['coreMargin'], join_style=2)
        trim = closed.buffer(item['roadTrimMargin'], join_style=2)
        halo = closed.buffer(item['haloMeters'], join_style=2)
        road_shapes = [surface_shape(s) for s in effective if s['kind'] == 'roads']
        for layer in context['campus-roads']['layers'] + context['surroundings']['layers']:
            vs, ts = layer['vertices'], layer['triangles']
            road_shapes.extend(Polygon([vs[k][:2] for k in ts[i:i+3]]) for i in range(0,len(ts),3))
        roads = unary_union(road_shapes)
        protection = [roads.difference(trim).buffer(.1, join_style=2)]
        protection.extend(Polygon(p[0],p[1:]).buffer(.5,join_style=2)
                          for other in context['buildings'] if other['id'] != b['id'] for p in other['polygons'])
        protection.extend(box(*s['gradingBounds']) for s in context['sites']['sites'] if 'gradingBounds' in s)
        protected = unary_union(protection)
        if core.intersection(protected).area > 1e-7:
            raise ValueError('Foundation core intersects protected road, site, or neighboring building')
        area = halo.difference(protected)
        ring = area.difference(core)
        if core.difference(area).area > 1e-7:
            raise ValueError('Foundation repair does not cover the closed building')
        t=context['terrain'];x,y=b.get('form',{}).get('stairTower',{}).get('hostCenter',b['center'])
        x0,y0,x1,y1=t['bounds'];cols,rows=t['cols'],t['rows'];hh=t['heights']
        u=max(0,min(cols-1.001,(x-x0)/(x1-x0)*(cols-1)));v=max(0,min(rows-1.001,(y-y0)/(y1-y0)*(rows-1)))
        i,j=int(u),int(v);a,c=u-int(u),v-int(v)
        datum=(hh[j*cols+i]*(1-a)+hh[j*cols+i+1]*a)*(1-c)+(hh[(j+1)*cols+i]*(1-a)+hh[(j+1)*cols+i+1]*a)*c
        record = {**item, 'datum': datum, 'bounds': list(area.bounds),
                  'corePolygons': geometry_rings(core), 'gradingPolygons': geometry_rings(area),
                  'coreMasks': convex_masks(core), 'transitionMasks': convex_masks(ring),
                  'roadTrimMasks': convex_masks(trim), 'roadTrimBounds': list(trim.bounds),
                  'closedArea': closed.area, 'gradingArea': area.area,
                  'trimmedRoadArea': roads.intersection(trim).area}
        # Every mask must cover exactly its intended region, including holes.
        for masks, shape in ((record['coreMasks'],core),(record['transitionMasks'],ring),(record['roadTrimMasks'],trim)):
            if unary_union([Polygon(t) for t in masks]).symmetric_difference(shape).area > 1e-6:
                raise ValueError('Incomplete foundation triangulation')
        if 'groundedServiceRoad' in item:
            export_with=item['groundedServiceRoad'].get('exportWith')
            if export_with is not None and not any(p['id']==export_with and 'groundedService' in p for p in context['pavings']['pavings']):
                raise ValueError('Missing grounded road export group')
            from service_road_data import derive_service_road
            record['groundedServiceRoad']=derive_service_road(item['groundedServiceRoad'],effective,context['campus-roads']['layers']+context['surroundings']['layers'],trim,convex_masks)
        records.append(record)
    digest = revision(context)
    result = {'schemaVersion':1, 'contextRevision':digest, 'foundations':records}
    (root/'public/data/foundations.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n')
    print('Foundation masks', [(r['id'],len(r['coreMasks']),len(r['transitionMasks']),r['trimmedRoadArea']) for r in records])


if __name__ == '__main__':
    prepare_foundations()
