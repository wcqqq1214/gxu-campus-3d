"""Field-attributed ordinary-building calibration on stable mapped footprints.

The catalogue is input, never a second set of building footprints. Missing
evidence leaves defaults visible; malformed or stale overrides fail preparation.
"""
import copy
import hashlib
import json
import math
from pathlib import Path

import mapbox_earcut as earcut
import numpy as np
from shapely.geometry import Polygon, Point, LineString, box
from shapely.affinity import rotate, translate
from shapely.ops import unary_union

from building_forms import positive, infer_archetype, resolve_form, roof_geometry
from attached_portico_data import resolve_attached_portico

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEVELS = {'living': 6, 'academic': 5, 'culture': 2, 'service': 3}
ARCHETYPE_LEVELS = {'dormitory':6,'residential-block':6,'teaching-block':5,
                    'courtyard-lab':5,'low-rise-service':2}
ARCHETYPES = {'generic', 'dormitory', 'residential-block', 'canteen', 'teaching-block',
              'courtyard-lab', 'low-rise-service'}
FIELDS = {'archetype', 'levels', 'floorHeight', 'height', 'roof', 'parts', 'entrances', 'facadeRules'}


def ordinary(b):
    return not (b.get('landmark') or b.get('customModel') or b['id'] == 'way/948683815'
                or b.get('tags', {}).get('memorial') == 'column')


def footprint_revision(b):
    return hashlib.sha256(json.dumps(b['polygons'], separators=(',', ':')).encode()).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def read_json(path):
    return json.loads(Path(path).read_text(), object_pairs_hook=unique_object)


def load_catalogue(path=None):
    data = read_json(path or ROOT/'data/building-overrides.json')
    if set(data) != {'schemaVersion', 'buildings'} or type(data['schemaVersion']) is not int or data['schemaVersion'] != 1:
        raise ValueError('Building overrides require schemaVersion 1 and buildings')
    if not isinstance(data['buildings'], dict):
        raise ValueError('buildings must be keyed by stable OSM ID')
    return data['buildings']


def source_catalogue(root=None):
    # Public data is output, not an input dependency of a clean preparation.
    root = Path(root or ROOT)
    sources = []
    for name in ('sources.json', 'huicui-sources.json',
                 'basketball-sources.json', 'building-sources.json'):
        sources.extend(read_json(root/'data'/name))
    if len({s['id'] for s in sources}) != len(sources):
        raise ValueError('Duplicate source ID across source catalogues')
    return sources


def validate_ids(catalogue, buildings):
    available = {b['id'] for b in buildings if ordinary(b)}
    unknown = set(catalogue) - available
    if unknown:
        raise ValueError(f'Unknown or dedicated building override IDs: {sorted(unknown)}')


def evidence(record, field, source_ids):
    item = record.get('evidence', {}).get(field)
    if not isinstance(item, dict) or item.get('status') not in ('confirmed', 'estimated'):
        raise ValueError(f'{field}: explicit confirmed/estimated evidence is required')
    if not isinstance(item.get('note'), str) or not item['note'].strip():
        raise ValueError(f'{field}: evidence rationale is required')
    refs = item.get('sourceRefs')
    if not isinstance(refs, list) or any(not isinstance(ref,str) or ref not in source_ids for ref in refs):
        raise ValueError(f'{field}: unknown source reference')
    if item['status'] == 'confirmed' and not refs:
        raise ValueError(f'{field}: confirmed information needs a source')
    return copy.deepcopy(item)


def osm_number(tags, key):
    value = tags.get(key)
    if isinstance(value, str) and key == 'height':
        value = value.strip().removesuffix('m').strip()
    try:
        return positive(value, key), None
    except ValueError:
        return None, f'invalid OSM {key}: {tags[key]!r}' if key in tags else None


def anchor(b, value, exterior=False):
    for key in ('polygon', 'ring', 'edge'):
        if isinstance(value.get(key), bool) or not isinstance(value.get(key), int) or value[key] < 0:
            raise ValueError(f'{b["id"]}: invalid {key} anchor')
    try:
        ring = b['polygons'][value['polygon']][value['ring']]
        a, c = ring[value['edge']], ring[value['edge']+1]
    except IndexError as error:
        raise ValueError(f'{b["id"]}: stale facade anchor') from error
    if exterior and value['ring'] != 0:
        raise ValueError('Ordinary entrances must anchor the exterior ring')
    dx, dy = c[0]-a[0], c[1]-a[1]; length = math.hypot(dx, dy)
    if length < .01:
        raise ValueError('Degenerate facade anchor')
    sign = 1 if sum(p[0]*q[1]-q[0]*p[1] for p,q in zip(ring,ring[1:])) > 0 else -1
    # Interior rings face the courtyard regardless of the source winding.
    if value['ring'] > 0:
        sign *= -1
    return a, c, (dy/length*sign, -dx/length*sign), length


def pack_geometry(polys):
    coords, triangles = [], []
    for poly in polys:
        rings = [[list(p) for p in poly.exterior.coords]] + [[list(p) for p in r.coords] for r in poly.interiors]
        coords.append(rings)
        xy = [p for r in rings for p in r[:-1]]
        triangles.append(earcut.triangulate_float64(np.asarray(xy),
            np.cumsum([len(r)-1 for r in rings], dtype=np.uint32)).tolist())
    return coords, triangles


def resolve_parts(b, raw, roof):
    footprint = unary_union([Polygon(p[0], p[1:]) for p in b['polygons']])
    parts, covered, ids = [], [], set()
    if not isinstance(raw, list) or not raw:
        raise ValueError('parts must be a nonempty explicit partition')
    for part in raw:
        required = {'id', 'polygons', 'height', 'levels'}
        if not required <= set(part) or set(part) - required - {'openBelow','roof'} or not isinstance(part['id'],str) or not part['id'] or part['id'] in ids:
            raise ValueError('Each part needs a unique ID, polygons, height and levels')
        ids.add(part['id'])
        polys = [Polygon(p[0], p[1:]) for p in part['polygons']]
        if not polys or any(not p.is_valid or p.area < .01 for p in polys):
            raise ValueError('Invalid part polygon')
        shape = unary_union(polys)
        if shape.difference(footprint).area > 1e-5:
            raise ValueError('Part leaves the original footprint or fills its courtyard')
        if any(shape.intersection(other).area > 1e-5 for other in covered):
            raise ValueError('Building parts overlap')
        covered.append(shape)
        height = positive(part['height'], 'part height'); levels = positive(part['levels'], 'part levels')
        coords, triangles = pack_geometry(polys)
        part_roof = copy.deepcopy(roof)
        if 'roof' in part:
            own = part['roof']
            if not isinstance(own,dict) or set(own) != {'type','rise'} or own['type'] not in ('flat','hipped','gabled'):
                raise ValueError('Part roof needs an explicit type and rise')
            if type(own['rise']) not in (float,int) or not math.isfinite(own['rise']):
                raise ValueError('Part roof rise must be finite and numeric')
            if (own['type']=='flat' and own['rise']!=0) or (own['type']!='flat' and own['rise']<=0):
                raise ValueError('Part roof rise conflicts with its type')
            part_roof={**own,'basis':'Explicit part roof; see attributed parts evidence','status':'estimated'}
        if part_roof['type'] != 'flat':
            part_roof['geometry'] = roof_geometry(coords, part_roof['type'], part_roof['rise'])
        resolved = {'id':part['id'], 'polygons':coords, 'triangles':triangles,
                    'height':height, 'levels':levels, 'roof':part_roof}
        if 'openBelow' in part:
            opening = part['openBelow']
            if not isinstance(opening, dict) or set(opening) != {'clearHeight','floorHeight','columns'}:
                raise ValueError('Open portico needs floor, soffit and explicit columns')
            clear = positive(opening['clearHeight'], 'portico soffit height')
            floor = positive(opening['floorHeight'], 'portico floor height')
            if part_roof['type'] != 'flat' or not .1 <= floor < clear-2 or clear > height-.15:
                raise ValueError('Portico floor/soffit/roof heights are inconsistent')
            columns = opening['columns']; supports = []
            if not isinstance(columns,list) or not 2 <= len(columns) <= 12:
                raise ValueError('Portico requires 2–12 explicit columns')
            for column in columns:
                if not isinstance(column,dict) or set(column) != {'center','width','depth','angle'}:
                    raise ValueError('Unknown portico column fields')
                if not isinstance(column['center'],list) or len(column['center']) != 2:
                    raise ValueError('Invalid portico column center')
                values = [*column['center'], column['angle']]
                if len(column['center']) != 2 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in values):
                    raise ValueError('Invalid portico column coordinates')
                w = positive(column['width'],'column width'); d = positive(column['depth'],'column depth')
                support = translate(rotate(box(-w/2,-d/2,w/2,d/2),column['angle'],use_radians=True),*column['center'])
                if support.difference(shape).area > 1e-5 or any(support.intersection(s).area > 1e-5 for s in supports):
                    raise ValueError('Portico columns leave their footprint or overlap')
                supports.append(support)
            resolved['openBelow'] = copy.deepcopy(opening)
        parts.append(resolved)
    if footprint.symmetric_difference(unary_union(covered)).area > 1e-5:
        raise ValueError('Building parts do not cover the complete mapped footprint')
    if abs(max(p['height'] for p in parts)-b['height']) > 1e-5:
        raise ValueError('Maximum part height must equal the building body height')
    # A recessed ground floor can split a single roof into two volume parts.
    # Do not turn the shared, equal-height seam into a rooftop parapet.
    for part in parts:
        adjacent = [Polygon(poly[0],poly[1:]) for other in parts
                    if other['id'] != part['id'] and abs(other['height']-part['height']) < 1e-6
                    for poly in other['polygons']]
        if adjacent:
            # Polygon subtraction can leave the same rotated edge a few ULPs
            # apart. A 0.1 micrometre overlay tolerance removes that seam;
            # it is not a design setback or a change to any body polygon.
            covered = unary_union(adjacent).buffer(1e-7)
            edges = []
            for poly in part['polygons']:
                for ring in poly:
                    for a,c in zip(ring,ring[1:]):
                        line = LineString([a,c]).difference(covered)
                        segments = [line] if line.geom_type == 'LineString' else list(getattr(line,'geoms',[]))
                        edges.extend([list(s.coords[0]),list(s.coords[-1])] for s in segments
                                     if s.geom_type == 'LineString' and s.length > .01)
            part['parapetEdges'] = edges
    return parts


def resolve_facades(b, form, rules):
    from facade_bands_data import validate_window_bands
    from facade_panels_data import validate_panels
    indexed = {}
    part_ids = {p['id'] for p in form['parts']} or {'body'}
    for rule in rules:
        if set(rule) - {'polygon','ring','edge','part','windows','balconies','spacing','openCorridor','windowGrid','windowBands','panels','attachedGallery'}:
            raise ValueError('Unknown facade rule field')
        anchor(b, rule)
        if 'part' in rule and (not isinstance(rule['part'],str) or rule['part'] not in part_ids):
            raise ValueError('Facade rule references an unknown building part')
        edge_key = tuple(rule[k] for k in ('polygon','ring','edge'))
        key = (*edge_key, rule.get('part'))
        if key in indexed:
            raise ValueError('Duplicate facade rule')
        if any(k[:3] == edge_key and (k[3] is None or key[3] is None) for k in indexed):
            raise ValueError('Do not mix whole-edge and part-specific facade rules')
        for key_bool in ('windows','balconies'):
            if key_bool in rule and not isinstance(rule[key_bool], bool):
                raise ValueError('Facade window/balcony switches must be boolean')
        if 'spacing' in rule:
            positive(rule['spacing'], 'window spacing')
        if 'attachedGallery' in rule:
            if (rule['ring'] != 0 or rule.get('windows') is False or rule.get('balconies') is not False
                    or any(k in rule for k in ('openCorridor', 'windowGrid', 'windowBands', 'panels', 'spacing'))):
                raise ValueError('Attached gallery requires an exterior facade without conflicting window rules')
        if 'panels' in rule:
            if (rule['ring'] != 0 or rule.get('windows') is False or rule.get('balconies') is not False
                    or any(k in rule for k in ('windowGrid', 'openCorridor', 'spacing'))):
                raise ValueError('Panels need an exterior solid facade with balconies explicitly disabled')
        if 'windowBands' in rule:
            if (rule['ring'] != 0 or rule.get('windows') is False or rule.get('balconies') is True
                    or any(k in rule for k in ('windowGrid', 'openCorridor', 'spacing'))):
                raise ValueError('Window bands require an exterior solid facade without conflicting rules')
        if 'windowGrid' in rule:
            grid=rule['windowGrid']
            if not isinstance(grid,dict) or set(grid)!={'columns','firstLevel','edgeInset','widthRatio','heightRatio','pilasterWidth','pilasterDepth','paneRows'}:
                raise ValueError('Window grid needs explicit bay, floor, pier and pane dimensions')
            for parameter in ['edgeInset','widthRatio','heightRatio','pilasterWidth','pilasterDepth']:
                positive(grid[parameter],'window grid '+parameter)
            for parameter,lower,upper in [('columns',1,32),('paneRows',1,8),('firstLevel',0,49)]:
                if type(grid[parameter]) is not int or not lower<=grid[parameter]<=upper:
                    raise ValueError('Invalid window grid '+parameter)
            if grid['widthRatio']>=1 or grid['heightRatio']>.85:
                raise ValueError('Window grid glazing must leave wall bands')
            if rule['ring']!=0 or rule.get('windows') is False or rule.get('balconies') is True or 'openCorridor' in rule or 'spacing' in rule:
                raise ValueError('Window grid requires an exterior windowed facade without conflicting rules')
        if 'openCorridor' in rule:
            corridor = rule['openCorridor']
            required={'depth','firstLevel','railHeight','endInset'}
            if not isinstance(corridor,dict) or not required <= set(corridor) or set(corridor)-required-{'piers','balusters'}:
                raise ValueError('Open corridor needs depth, firstLevel, railHeight and endInset')
            for parameter in ['depth','railHeight','endInset']:
                positive(corridor[parameter], 'corridor '+parameter)
            if type(corridor['firstLevel']) is not int or corridor['firstLevel'] < 0:
                raise ValueError('Corridor firstLevel must be a nonnegative floor index')
            if corridor['firstLevel']==0 and 'piers' not in corridor:
                raise ValueError('Ground-level open corridor requires explicit piers')
            if 'piers' in corridor:
                piers=corridor['piers']
                if not isinstance(piers,dict) or set(piers)!={'bays','width','depth'} or type(piers['bays']) is not int or not 1<=piers['bays']<=24:
                    raise ValueError('Corridor piers need bounded bays, width and depth')
                for parameter in ('width','depth'):positive(piers[parameter],'corridor pier '+parameter)
            if 'balusters' in corridor:
                rail=corridor['balusters']
                if not isinstance(rail,dict) or set(rail)!={'spacing','width'}:
                    raise ValueError('Balusters need spacing and width')
                for parameter in ('spacing','width'):positive(rail[parameter],'baluster '+parameter)
                if not .08<=rail['width']<=.18 or not rail['width']+.12<=rail['spacing']<=.6 or corridor['railHeight']<.5:
                    raise ValueError('Balusters need usable clear gaps and railing height')
            if rule['ring'] != 0 or rule.get('balconies') is True:
                raise ValueError('Open corridor requires an exterior facade without added balconies')
        indexed[key] = rule
    parts = form['parts'] or [{'id':'body', 'polygons':b['polygons'],
                              'height':form['height'], 'levels':form['levels'], 'roof':form['roof']}]
    result = []
    corridor_strips = []
    matched = {key: 0 for key in indexed}
    for pi, poly in enumerate(b['polygons']):
        for ri, ring in enumerate(poly):
            for ei in range(len(ring)-1):
                a,c,normal,_ = anchor(b, {'polygon':pi,'ring':ri,'edge':ei})
                line = LineString([a,c])
                for part in parts:
                    shape = unary_union([Polygon(p[0],p[1:]) for p in part['polygons']])
                    segment = line.intersection(shape)
                    segments = [segment] if segment.geom_type == 'LineString' else [s for s in getattr(segment,'geoms',[]) if s.geom_type == 'LineString']
                    # Clipping a slightly oblique mapped edge can place a new
                    # endpoint a few ULPs outside the original line. Recover
                    # only coincident boundary intervals, not buffered shapes
                    # that would overlap the neighbouring part at its seam.
                    boundary_segments = []
                    for rings in part['polygons']:
                        for boundary in rings:
                            for v,w in zip(boundary,boundary[1:]):
                                if max(line.distance(Point(v)),line.distance(Point(w))) > 1e-7:
                                    continue
                                lo,hi=sorted((line.project(Point(v)),line.project(Point(w))))
                                if hi-lo>.01:
                                    boundary_segments.append(LineString([line.interpolate(lo),line.interpolate(hi)]))
                    if not any(s.length > .01 for s in segments):
                        segments=boundary_segments
                    for s in segments:
                        if s.length < .01: continue
                        rule_key = (pi,ri,ei,part['id'])
                        if rule_key not in indexed:
                            rule_key = (pi,ri,ei,None)
                        rule = indexed.get(rule_key,{})
                        if rule_key in matched:
                            matched[rule_key] += 1
                        start,end = list(s.coords)[0],list(s.coords)[-1]
                        if line.project(Point(start)) > line.project(Point(end)): start,end=end,start
                        facade = {'polygon':pi,'ring':ri,'edge':ei,'part':part['id'],
                            'start':list(start),'end':list(end),'normal':list(normal),'height':part['height'],
                            'levels':part['levels'],'rule':rule}
                        if 'attachedGallery' in rule:
                            from attached_gallery_data import resolve_attached_gallery
                            if abs(s.length-line.length)>1e-5:
                                raise ValueError('Attached gallery needs an undivided mapped facade')
                            facade['attachedGallery'] = resolve_attached_gallery(b, facade, part, rule['attachedGallery'])
                        if 'windowBands' in facade['rule']:
                            if 'openBelow' in part or ('part' not in rule and abs(s.length-line.length)>1e-5):
                                raise ValueError('Window bands need one undivided solid facade edge')
                            validate_window_bands(facade['rule']['windowBands'], s.length,
                                                  part['height'], part['levels'])
                        if 'panels' in rule:
                            if 'openBelow' in part or ('part' not in rule and abs(s.length-line.length)>1e-5):
                                raise ValueError('Panels need one undivided solid facade edge')
                            validate_panels(rule['panels'], s.length, part['height'], part['levels'], rule.get('windowBands'))
                        if 'openBelow' in part:
                            if 'openCorridor' in facade['rule']:
                                raise ValueError('Corridor requires a solid flat-roofed part with whole floors')
                            if part['levels'] == 1:
                                if 'windowGrid' in facade['rule']:
                                    raise ValueError('Window grid cannot occupy a one-level open portico')
                                facade['rule'] = {'windows':False}
                            else:
                                facade['minimumHeight'] = part['openBelow']['clearHeight']
                        if 'windowGrid' in facade['rule']:
                            grid=facade['rule']['windowGrid'];length=math.dist(start,end)
                            if 'part' not in rule and abs(length-line.length)>1e-5:
                                raise ValueError('Window grid needs one undivided original facade edge')
                            if part['levels']!=int(part['levels']) or grid['firstLevel']>=part['levels']:
                                raise ValueError('Window grid requires whole floors above firstLevel')
                            bay=(length-2*grid['edgeInset'])/grid['columns'];fh=part['height']/part['levels']
                            if grid['edgeInset']<grid['pilasterWidth']/2 or bay*(1-grid['widthRatio'])<=grid['pilasterWidth']+.12:
                                raise ValueError('Window grid frames and piers do not fit within the facade')
                            if grid['pilasterDepth']>bay/2 or fh*grid['heightRatio']<=grid['paneRows']*.06:
                                raise ValueError('Window grid pier depth or pane spacing is not usable')
                            if (grid['firstLevel']+.56-grid['heightRatio']/2)*fh<facade.get('minimumHeight',0):
                                raise ValueError('Window grid glazing intrudes into the open portico')
                        if 'openCorridor' in facade['rule']:
                            corridor=facade['rule']['openCorridor'];fh=part['height']/part['levels']
                            if part['levels']!=int(part['levels']):
                                raise ValueError('Corridor requires a solid part with whole floors')
                            if corridor['firstLevel']>=part['levels'] or corridor['railHeight']>=fh-.5:
                                raise ValueError('Corridor floors or railing leave no upper opening')
                            length=math.dist(start,end);inset=corridor['endInset']
                            if length-2*inset<2:
                                raise ValueError('Corridor end returns leave no usable facade')
                            if 'piers' in corridor:
                                piers=corridor['piers'];bay=(length-2*inset)/piers['bays']
                                if piers['width']>=bay-.8 or piers['width']/2>inset or not .15<=piers['depth']<=corridor['depth']:
                                    raise ValueError('Corridor piers must fit inside the facade and leave usable bays')
                            tangent=[(end[k]-start[k])/length for k in (0,1)]
                            a0=[start[k]+tangent[k]*inset for k in (0,1)]
                            c0=[end[k]-tangent[k]*inset for k in (0,1)]
                            strip=Polygon([a0,c0,[c0[k]-normal[k]*corridor['depth'] for k in (0,1)],
                                           [a0[k]-normal[k]*corridor['depth'] for k in (0,1)]])
                            if strip.difference(shape).area>1e-5:
                                raise ValueError('Corridor leaves its part or reaches a courtyard')
                            if any(strip.intersection(other).area>1e-5 for other in corridor_strips):
                                raise ValueError('Corridor recesses overlap at a corner')
                            corridor_strips.append(strip)
                        result.append(facade)
                covered=sum(math.dist(f['start'],f['end']) for f in result
                            if (f['polygon'],f['ring'],f['edge'])==(pi,ri,ei))
                if abs(covered-line.length)>1e-5:
                    raise ValueError(f'{b["id"]}: missing/duplicate facade at {(pi,ri,ei)}')
    for key,count in matched.items():
        if key[3] is not None and count != 1:
            raise ValueError('Part-specific facade must resolve to one continuous exterior segment')
    # A low portico exposes the main wall above its roof. This boundary is
    # inside the mapped outline, so the ordinary exterior-ring pass misses it.
    for porch in (p for p in parts if 'openBelow' in p):
        porch_shape = unary_union([Polygon(p[0],p[1:]) for p in porch['polygons']])
        for part in parts:
            if part['height'] <= porch['height']: continue
            for pi,poly in enumerate(part['polygons']):
                for ri,ring in enumerate(poly):
                    for ei in range(len(ring)-1):
                        a,c,n,_ = anchor({'id':b['id'],'polygons':part['polygons']},{'polygon':pi,'ring':ri,'edge':ei})
                        segment = LineString([a,c]).intersection(porch_shape.boundary)
                        segments = [segment] if segment.geom_type == 'LineString' else [s for s in getattr(segment,'geoms',[]) if s.geom_type == 'LineString']
                        for line in segments:
                            if line.length < .01: continue
                            result.append({'polygon':None,'ring':None,'edge':None,'part':part['id'],
                                'start':list(line.coords[0]),'end':list(line.coords[-1]),'normal':list(n),
                                'height':part['height'],'levels':part['levels'],'minimumHeight':porch['height'],'rule':{}})
    return result


def resolve_building(building, record=None, source_ids=None):
    if not ordinary(building):
        if record is not None: raise ValueError('Dedicated models do not use ordinary overrides')
        return copy.deepcopy(building)
    b = copy.deepcopy(building); record = record or {}; source_ids = set(source_ids or {'osm'})
    if set(record) - FIELDS - {'footprintRevision','evidence','review','name'}:
        raise ValueError(f'{b["id"]}: unknown building override field')
    if record and record.get('footprintRevision') != footprint_revision(b):
        raise ValueError(f'{b["id"]}: footprint revision changed; recheck anchors and parts')
    expected_evidence=(FIELDS & set(record) - {'roof'}) | {'roof.'+key for key in record.get('roof',{})}
    if set(record.get('evidence',{})) != expected_evidence:
        raise ValueError(f'{b["id"]}: evidence fields must exactly match applied override fields')
    provenance = {}; warnings = []
    for field in FIELDS & set(record) - {'roof'}:
        provenance[field] = evidence(record, field, source_ids)
    tags = b['tags']; levels, warning = osm_number(tags, 'building:levels')
    if warning: warnings.append(warning)
    height, warning = osm_number(tags, 'height')
    if warning: warnings.append(warning)
    archetype=record.get('archetype',infer_archetype(b))
    default_levels=ARCHETYPE_LEVELS.get(archetype,DEFAULT_LEVELS[b['category']])
    b['levels'] = positive(record.get('levels', levels or default_levels), 'levels')
    floor_height = positive(record.get('floorHeight', 3.3), 'floorHeight')
    b['height'] = positive(record.get('height', height or b['levels']*floor_height), 'height')
    if not 2.2 <= b['height']/b['levels'] <= 6:
        warnings.append('body height / floor count is outside 2.2–6.0 m; review this conflict')
    provenance.setdefault('levels', {'status':'osm' if levels else 'estimated',
        'sourceRefs':['osm'] if levels else [], 'note':'OSM building:levels' if levels else '用途类型默认层数'})
    provenance.setdefault('height', {'status':'osm' if height else 'estimated',
        'sourceRefs':['osm'] if height else provenance['levels']['sourceRefs'],
        'note':'OSM height' if height else f'采用层数 × {floor_height:g} 米估算层高，非测量高度'})
    # A multipart pitched roof is resolved on each part, never on a bounding
    # roof over the complete (possibly concave) building.
    form_input = b if 'parts' not in record else {**b,'tags':{**tags,'roof:shape':'flat'}}
    form = resolve_form(form_input)
    form['archetype'] = archetype
    if form['archetype'] not in ARCHETYPES:
        raise ValueError('Unknown building archetype')
    roof = record.get('roof', {})
    if set(roof) - {'type','rise'}:
        raise ValueError('Unsupported roof parameter; ridge follows the mapped local axis')
    for field in roof:
        provenance['roof.'+field] = evidence(record, 'roof.'+field, source_ids)
    if roof:
        kind = roof.get('type', form['roof']['type'])
        if kind not in ('flat','hipped','gabled'): raise ValueError('Unknown roof type')
        rise = 0 if kind == 'flat' else positive(roof.get('rise',form['roof']['rise'] or 2.3),'roof rise')
        if kind == 'flat' and roof.get('rise',0) != 0: raise ValueError('A flat roof cannot have a pitched rise')
        basis = provenance.get('roof.type', {'note':form['roof']['basis']})
        form['roof'] = {'type':kind,'rise':rise,'basis':basis['note'],
                        'status':basis.get('status',form['roof']['status'])}
        if kind != 'flat' and 'parts' not in record:
            form['roof']['geometry'] = roof_geometry(b['polygons'],kind,rise)
    if 'parts' in record:
        form['parts'] = resolve_parts(b, record['parts'], form['roof'])
    if 'entrances' in record:
        entrances = []; ids = set()
        for e in record['entrances']:
            required = {'id','polygon','ring','edge','t','width','primary'}
            if not required <= set(e) or set(e) - required - {'recess','steps','stepBaseHeight','attachedPortico','landingHeight','doorFrame','stairFlight'} or not e['id'] or e['id'] in ids:
                raise ValueError('Invalid or duplicate entrance')
            if 'landingHeight' in e:
                if type(e['landingHeight']) not in (int,float):
                    raise ValueError('Entrance landing height must be numeric')
                landing=positive(e['landingHeight'],'entrance landing height')
                if not .2 <= landing <= 1.2 or any(k in e for k in ('recess','steps','stepBaseHeight','attachedPortico')):
                    raise ValueError('Simple raised landing needs 0.2–1.2 m height and no other portico configuration')
            if 'steps' in e and ('recess' not in e or type(e['steps']) is not int or not 1 <= e['steps'] <= 12):
                raise ValueError('Explicit steps require a recessed entrance and an integer count from 1 to 12')
            ids.add(e['id']);a,c,n,length=anchor(b,e,exterior=True)
            t=e['t'];width=positive(e['width'],'entrance width')
            if isinstance(t,bool) or not isinstance(t,(float,int)) or not math.isfinite(t) or not 0<=t<=1:
                raise ValueError('Entrance fraction must lie on its facade')
            if width/2 > min(t,1-t)*length or not isinstance(e['primary'],bool):
                raise ValueError('Entrance width exceeds its facade or primary is not boolean')
            if 'doorFrame' in e:
                frame=e['doorFrame']
                if ('landingHeight' not in e or not isinstance(frame,dict)
                        or set(frame)!={'bays','pierWidth','pierDepth'}):
                    raise ValueError('Door frame requires a raised landing and explicit bays and pier dimensions')
                if type(frame['bays']) is not int or not 1<=frame['bays']<=6:
                    raise ValueError('Door frame bays must be an integer from 1 to 6')
                if any(type(frame[k]) not in (int,float) or not math.isfinite(frame[k]) for k in ('pierWidth','pierDepth')):
                    raise ValueError('Door frame pier dimensions must be finite numbers')
                pw,pd=frame['pierWidth'],frame['pierDepth']
                if not .25<=pw<=1.2 or not .6<=pd<=1.4 or width/frame['bays']-pw<.9:
                    raise ValueError('Door frame piers must fit beneath the canopy and leave usable openings')
                if (width+pw)/2>min(t,1-t)*length:
                    raise ValueError('Outer door frame piers extend beyond the attached facade')
            resolved = {**e,'center':[a[i]+(c[i]-a[i])*t for i in (0,1)],
                'bearing':math.degrees(math.atan2(n[0],n[1]))%360,
                'status':provenance['entrances']['status'],'basis':provenance['entrances']['note']}
            if 'stairFlight' in e:
                if 'landingHeight' not in e:raise ValueError('Stair flight requires a simple raised landing')
                from entrance_stairs_data import resolve_stair_flight
                resolved['stairFlight']=resolve_stair_flight(b,resolved,e['stairFlight'],length)
            if 'attachedPortico' in e:
                if any(key in e for key in ('recess','steps','stepBaseHeight')):
                    raise ValueError('Attached portico cannot combine with recessed entrance configuration')
                resolved['attachedPortico']=resolve_attached_portico(b,resolved,e['attachedPortico'],length,form['parts'])
            if 'recess' in e:
                recess = positive(e['recess'],'entrance recess')
                front = resolved['center']; back = [front[i]-n[i]*recess for i in (0,1)]
                route = LineString([front,back]); tangent = [(c[i]-a[i])/length for i in (0,1)]
                door = LineString([[back[i]+tangent[i]*offset for i in (0,1)] for offset in (-width/2,width/2)])
                porches = [p for p in form['parts'] if 'openBelow' in p and
                    unary_union([Polygon(r[0],r[1:]) for r in p['polygons']]).buffer(1e-5).covers(route)]
                body = unary_union([Polygon(r[0],r[1:]) for p in form['parts'] if 'openBelow' not in p for r in p['polygons']])
                # Mapped front and rear canopy edges may differ by millimetres
                # in direction; allow 1 cm, not a free-floating door position.
                if len(porches)!=1 or not body.boundary.buffer(.01).covers(door):
                    raise ValueError('Recessed entrance must cross a portico and meet a main-body wall')
                porch=porches[0]
                if 'stepBaseHeight' in e:
                    base = e['stepBaseHeight']
                    if type(base) not in (int,float) or not math.isfinite(base) or not 0 <= base < porch['openBelow']['floorHeight']:
                        raise ValueError('Step base must be finite, nonnegative and below the platform')
                for column in porch['openBelow']['columns']:
                    support=translate(rotate(box(-column['width']/2,-column['depth']/2,column['width']/2,column['depth']/2),column['angle'],use_radians=True),*column['center'])
                    if support.intersects(route.buffer(.6)):
                        raise ValueError('Portico column blocks the central entrance route')
                resolved.update(center=back,outerCenter=front,porticoId=porch['id'],
                    platformHeight=porch['openBelow']['floorHeight'],porticoWidth=length)
            elif 'stepBaseHeight' in e:
                raise ValueError('Step base requires a recessed entrance')
            entrances.append(resolved)
        if not entrances or sum(e['primary'] for e in entrances)!=1:
            raise ValueError('Exactly one primary entrance is required')
        form['entrances']=entrances
    if 'parts' in record or 'facadeRules' in record:
        form['facades']=resolve_facades(b,form,record.get('facadeRules',[]))
    provenance.setdefault('archetype',{'status':'estimated','sourceRefs':['osm'],
        'note':'按名称、OSM用途和现有形制规则推定'})
    provenance.setdefault('floorHeight',{'status':'estimated','sourceRefs':[],
        'note':'默认3.3米层高；独立OSM高度存在时不以此覆盖高度'})
    provenance.setdefault('roof.type',{'status':'osm' if tags.get('roof:shape') in ('flat','hipped','gabled') else 'estimated',
        'sourceRefs':['osm'] if tags.get('roof:shape') in ('flat','hipped','gabled') else [],
        'note':form['roof']['basis']})
    provenance.setdefault('roof.rise',{'status':'estimated','sourceRefs':[],
        'note':'平屋面屋脊增量为0；有坡屋面但没有屋脊尺寸时采用2.3米展示估算'})
    provenance.setdefault('entrances',{'status':'estimated','sourceRefs':[],
        'note':'无定位依据，最长外边中点示意入口；不声称朝向正确'})
    provenance.setdefault('facadeRules',{'status':'estimated','sourceRefs':[],
        'note':'默认窗距和窗尺寸；资料未覆盖的立面继续按类型推定'})
    b.update(form=form,archetype=form['archetype'],roofBasis=form['roof']['basis'])
    if record:
        b['calibration']={'schemaVersion':1,'footprintRevision':footprint_revision(b),
                          'evidence':provenance,'review':copy.deepcopy(record.get('review',{})), 'warnings':warnings}
        b['sourceRefs']=sorted({'osm'} | {ref for p in provenance.values() for ref in p['sourceRefs']})
        b['heightBasis']=provenance['height']['note']
        b['facadeBasis']='逐字段资料校准；未确认入口、立面和尺寸仍为示意，见校准记录'
    else:
        b.pop('calibration',None)
        b['heightBasis']='OSM高度或层数' if height or levels else '按类型估算'
        if building.get('calibration'):
            b['facadeBasis']='按建筑类型推定'
            b['sourceRefs']=['osm']
    return b


def prepare_existing_overrides():
    out=ROOT/'public/data'; buildings=read_json(out/'buildings.json'); catalogue=load_catalogue()
    validate_ids(catalogue,buildings); sources=source_catalogue(); source_ids={s['id'] for s in sources}
    resolved=[resolve_building(b,catalogue.get(b['id']),source_ids) for b in buildings]
    from attached_gallery_data import validate_gallery_context
    validate_gallery_context(resolved)
    geo=read_json(out/'geography.geojson'); features={f['id']:f for f in geo['features']}
    props=('height','levels','heightBasis','facadeBasis','archetype','roofBasis','sourceRefs','calibration')
    for b in resolved:
        if ordinary(b):
            target=features[b['id']]['properties']
            for key in props:
                if key in b:target[key]=b[key]
                else:target.pop(key,None)
    overview=read_json(out/'overview.json')
    overview['estimatedHeights']=sum(b['heightBasis']=='按类型估算' for b in resolved)
    overview['buildingCalibrations']=calibration_stats(resolved,catalogue)
    # All validation finishes before replacing any public data.
    for name,data in [('buildings.json',resolved),('geography.geojson',geo),('overview.json',overview),
                      ('sources.json',{'version':1,'sources':sources})]:
        (out/name).write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')))
    report={'buildings':[{'id':b['id'],'name':b['name'],'before':{k:resolve_building(old)[k] for k in ('height','levels')},
                          'after':{'height':b['height'],'levels':b['levels']},'calibration':b['calibration']}
                         for old,b in zip(buildings,resolved) if b['id'] in catalogue]}
    (ROOT/'docs/model-checks/refinement/s2-calibrations.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(f'Applied {len(catalogue)} attributed ordinary-building records; preserved site/terrain/tree files')


def calibration_stats(buildings,catalogue):
    return {'records':len(catalogue),
        'documentedLevels':sum(b.get('calibration',{}).get('evidence',{}).get('levels',{}).get('status')=='confirmed' for b in buildings),
        'documentedBodyHeights':sum(b.get('calibration',{}).get('evidence',{}).get('height',{}).get('status')=='confirmed' for b in buildings)}


if __name__ == '__main__':
    prepare_existing_overrides()
