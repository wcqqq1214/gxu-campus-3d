"""Bounded, repeatable supplement for the formerly omitted north academic site.

The OSM snapshot and its campus polygon remain unchanged. Supplemental IDs and
source attribution explicitly distinguish traced geometry from mapped geometry.
"""
import json
import math
from pathlib import Path

from shapely.geometry import Point, Polygon, mapping, shape
from shapely.geometry.polygon import orient
from shapely.ops import transform, unary_union
from shapely.affinity import translate, scale

from building_forms import resolve_form
from building_overrides import pack_geometry, source_catalogue
from surroundings_data import tiled_triangles, surface_shape
from north_campus_forms import prepare_form

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'north-campus/'


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    if path.name == 'sources.json':
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    else:
        path.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n')


def elevation(terrain, x, y):
    cols, rows = terrain['cols'], terrain['rows']
    x0, y0, x1, y1 = terrain['bounds']
    u = max(0, min(cols-1.001, (x-x0)/(x1-x0)*(cols-1)))
    v = max(0, min(rows-1.001, (y-y0)/(y1-y0)*(rows-1)))
    i, j = int(u), int(v)
    a, b = u-i, v-j
    h = terrain['heights']
    return (h[j*cols+i]*(1-a)+h[j*cols+i+1]*a)*(1-b) + (h[(j+1)*cols+i]*(1-a)+h[(j+1)*cols+i+1]*a)*b


def prepare(root=ROOT):
    config = read(root/'data/north-campus-layout.json')
    out = root/'public/data'
    terrain = read(out/'terrain.json')
    region = read(root/'data/region.json')
    lon0, lat0 = region['center']
    mx = 111320*math.cos(math.radians(lat0))
    w, s, e, n = config['image']['extent']

    def point(pixel):
        px, py = pixel
        return [round((w+(e-w)*px/config['image']['width']-lon0)*mx, 3),
                round((n-(n-s)*py/config['image']['height']-lat0)*111320, 3)]

    def inverse(x, y, z=None):
        return x/mx+lon0, y/111320+lat0

    boundary = Polygon([point(p) for p in config['boundaryPixels']])
    public_road = Polygon([point(p) for p in config['publicRoadPixels']])
    assert boundary.is_valid
    records, footprints, features = [], [], []
    for item in config['buildings']:
        polygon = Polygon([point(p) for p in item['pixels']])
        alignment=config.get('roadAlignment',{})
        if item['id']=='north-campus/gym':
            polygon=translate(polygon,yoff=alignment.get('gymNorthMeters',0))
        elif alignment:
            polygon=scale(polygon,xfact=alignment['academicEastScale'],yfact=1,
                          origin=(alignment['academicAnchorX'],0))
        assert polygon.is_valid and polygon.area > 10 and boundary.covers(polygon), item['id']
        # Shared walls are drawn independently in the pixel trace. Partition
        # sub-pixel slivers once so adjoining blocks never double their walls.
        shared = unary_union(footprints)
        assert polygon.intersection(shared).area < polygon.area*.01
        polygon = polygon.difference(shared)
        assert polygon.geom_type == 'Polygon' and polygon.is_valid
        polygon = orient(polygon, sign=1)
        center = list(polygon.representative_point().coords)[0]
        rings, triangles = pack_geometry([polygon])
        ix, iy = (math.floor(v/360) for v in center)
        label = lambda v: ('p' if v >= 0 else 'n') + str(abs(v))
        # Conservative foundation: all footprint corners touch or penetrate
        # the unchanged coarse ground. Height is still only a massing estimate.
        samples = [elevation(terrain, *p) for p in polygon.exterior.coords]
        base = min(samples)-.25
        record = dict(id=item['id'], name=item['name'], category=item['category'],
                      center=list(center), bounds=list(polygon.bounds), polygons=rings,
                      roofTriangles=triangles, height=item['height'], levels=item['levels'],
                      elevation=round(base, 3), insideCampus=True, landmark=None,
                      zone='north', chunk=f'chunk-{label(ix)}-{label(iy)}',
                      customModel='north-campus', tags={'building':'yes'},
                      geometrySource='manual-imagery-trace', osmVersion=None, osmEditedAt=None,
                      sourceUrl=config['image']['service'], sourceRefs=config['sourceRefs'],
                      heightBasis=item.get('heightBasis','按类型估算'), facadeBasis=config['precision'],
                      constructionStatus=None)
        record['form'] = resolve_form(record)
        record['archetype'] = record['form']['archetype']
        record['roofBasis'] = record['form']['roof']['basis']
        if 'architecture' in item:
            record['northForm']=prepare_form(record,item['architecture'])
            record['facadeBasis']=item['architecture']['evidence']
            record['roofBasis']='照片及影像约束的屋顶形体；高度和构件尺寸估算'
            if item.get('levelsBasis'):record['levelsBasis']=item['levelsBasis']
        records.append(record)
        footprints.append(polygon)
        features.append({'type':'Feature', 'id':item['id'],
                         'properties':{**{k:record[k] for k in ('name','category','height','levels','heightBasis','facadeBasis','insideCampus','landmark','osmEditedAt','sourceUrl','sourceRefs','geometrySource')}, 'kind':'buildings'},
                         'geometry':mapping(transform(inverse, polygon))})
    for i, polygon in enumerate(footprints):
        for other in footprints[i+1:]:
            assert polygon.intersection(other).area < .02, 'Overlapping traced blocks'

    buildings = [b for b in read(out/'buildings.json') if not b['id'].startswith(PREFIX)]
    # Refuse overlap with existing assets rather than silently drawing duplicates.
    existing = unary_union([Polygon(p[0], p[1:]) for b in buildings for p in b['polygons']])
    assert existing.intersection(unary_union(footprints)).area < .02
    buildings.extend(records)
    occupied = unary_union(footprints)
    from north_underpass_data import prepare_underpass
    underpass,underpass_mask=prepare_underpass(root,lambda x,y:elevation(terrain,x,y))
    # The below-grade connector is not a campus island on the arterial deck.
    # Keep the illustrative boundary off the full carriageway/median corridor.
    crossing_corridor=unary_union([Polygon(r['outline']) for r in underpass['upperRoadRepairs']]).convex_hull
    public_road=public_road.union(crossing_corridor)
    existing_roads=unary_union([surface_shape(s) for s in read(out/'surfaces.json') if s['kind']=='roads'])
    grounds, ground_shapes = [], []
    for item in config['grounds']:
        area = Polygon([point(p) for p in item['pixels']]).difference(occupied.union(existing_roads).union(underpass_mask))
        assert area.is_valid
        ground_shapes.append(area)
        grounds.append({**{k:item[k] for k in ('id','name','kind','material')},
                        **tiled_triangles(area, step=10)})
    for b in records:
        if footprint:=b.get('northForm',{}).get('entryFootprint'):
            # Reserve stairs in the planting mask; actual stepped mesh is part
            # of the building rather than another horizontal ground overlay.
            ground_shapes.append(Polygon(footprint))
    track = config['track']
    px_scale = (e-w)/config['image']['width']*mx
    py_scale = (n-s)/config['image']['height']*111320
    prepared = {'version':1, 'precision':config['precision'], 'sourceRefs':config['sourceRefs'],
                'replacedSurfaceIds':['way/839763074'],
                'buildingIds':[b['id'] for b in records], 'grounds':grounds,
                'boundary':list(boundary.exterior.coords),
                'publicRoad':list(public_road.exterior.coords),
                'track':{**track, 'center':point(track['centerPixels']),
                         'width':track['widthPixels']*px_scale,
                         'depth':track['heightPixels']*py_scale},
                'connections':[{'id':underpass['id'],'name':underpass['name'],'north':underpass['axis'][-1],
                                'south':underpass['axis'][0],'mode':'underpass','note':underpass['topologyBasis']}]}
    prepared['buildingSiteFootprints']=[b['northForm']['entryFootprint'] for b in records if b.get('northForm',{}).get('entryFootprint')]
    prepared['underpass']=underpass
    ground_shapes.append(underpass_mask)
    geo = read(out/'geography.geojson')
    geo['features'] = [f for f in geo['features'] if not f['id'].startswith(PREFIX)] + features
    geo['features'].append({'type':'Feature', 'id':PREFIX+'area',
                            'properties':{'kind':'campus-supplement','name':'北校园北侧基础布局','sourceRefs':config['sourceRefs']},
                            'geometry':mapping(transform(inverse, boundary))})
    # Keep the public arterial between the two separate campus polygons. The
    # original OSM outline already includes some empty northern land, so union
    # before outlining rather than drawing two overlapping boundary rings.
    outline = read(out/'campus-boundary.json')
    outline.pop('northSupplementRing', None)
    base_display=shape(next(f['geometry'] for f in geo['features'] if f['id']=='campus-display-area'))
    display=transform(lambda x,y,z=None:((x-lon0)*mx,(y-lat0)*111320),base_display)
    display=display.union(boundary).difference(public_road).simplify(.35,preserve_topology=True)
    outline['rings']=[]
    for polygon in [display] if display.geom_type=='Polygon' else display.geoms:
        for edge in [polygon.exterior,*polygon.interiors]:
            ring=[]
            for a,b in zip(edge.coords,list(edge.coords)[1:]):
                count=max(1,math.ceil(math.dist(a,b)/10))
                for i in range(count):
                    x,y=[a[k]+(b[k]-a[k])*i/count for k in (0,1)]
                    ring.append([round(x,3),round(y,3),round(elevation(terrain,x,y)+2,3)])
            ring.append(ring[0]);outline['rings'].append(ring)
    outline['additionalSourceRefs'] = config['sourceRefs']
    outline['note'] = 'OSM主校园轮廓及北侧影像描绘补充范围；农院路和秀厢大道为公共道路。仅供辨认大致范围，不表示精确围墙或权属界线。'
    overview = read(out/'overview.json')
    overview.update(buildings=len(buildings),campusBuildings=sum(b['insideCampus'] for b in buildings))
    overview['estimatedHeights']=sum(b['heightBasis']=='按类型估算' for b in buildings)
    overview['layers']['buildings'] = len(buildings)
    overview['northCampusSupplement'] = {'blocks':len(records),'basis':config['precision'],
                                       'documentedLevels':sum(bool(b.get('levelsBasis')) for b in records),
                                       'estimatedDimensions':len(records)}
    for name, value in [('buildings.json',buildings),('geography.geojson',geo),
                        ('north-campus.json',prepared),('campus-boundary.json',outline),
                        ('overview.json',overview),('sources.json',{'version':1,'sources':source_catalogue(root)})]:
        write(out/name, value)
    # These derived contexts include building footprints and must stay honest.
    from shore_data import prepare_shores
    from vegetation_data import prepare_vegetation
    if root == ROOT:
        prepare_shores()
        trees=read(out/'vegetation.json')
        mask=unary_union([occupied,*ground_shapes])
        kept=[t for t in trees if mask.distance(Point(t[:2]))>4*t[2]/9+1]
        write(out/'vegetation.json',kept)
        prepare_vegetation(root)
        removed=[t for t in trees if t not in kept]
        report_path=root/'docs/model-checks/north-campus-trees.json'
        previous=read(report_path) if report_path.exists() else {'removed':[]}
        removed={tuple(t[:2]):t for t in previous['removed']+removed}
        write(report_path,{'removed':list(removed.values()),'remainingTrees':len(read(out/'vegetation.json')),
                           'basis':'仅移除新体块与新增硬地附近的示意树；保留其他树的位置、朝向、高度。'})
        from foundation_data import prepare_foundations
        prepare_foundations(root)
    print(f'North campus: {len(records)} traced blocks, {len(grounds)} ground areas')
    return prepared


if __name__ == '__main__':
    prepare()
