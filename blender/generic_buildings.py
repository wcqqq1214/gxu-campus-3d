"""Ordinary buildings: one architectural form, two levels of facade detail."""
import hashlib
import math
from geometry import Mesh
from facade_corridors import add_corridor
from attached_gallery import add_attached_gallery
from facade_windows import add_grid_pilasters, add_grid_windows
from attached_portico import add_attached_portico
from facade_bands import add_band_ledges, add_band_windows, band_replaces_window
from facade_panels import add_panels, panel_replaces_window


def compact_form_source(obj):
    """Weld source vertices without dropping groups at shared wall/roof edges."""
    from huicui import compact_source
    membership = {}
    key = lambda point: tuple(round(v, 5) for v in point)
    for vertex in obj.data.vertices:
        membership.setdefault(key(vertex.co), set()).update(g.group for g in vertex.groups)
    compact_source(obj)
    grouped = {group.index: [] for group in obj.vertex_groups}
    for vertex in obj.data.vertices:
        for group in membership.get(key(vertex.co), ()):
            grouped[group].append(vertex.index)
    for group, indices in grouped.items():
        if indices:
            obj.vertex_groups[group].add(indices, 1.0, 'REPLACE')


def wall_material(b, C):
    # A shared small palette keeps the all-campus base batched. Per-building
    # warm/cool material slots added >15% draw calls in the measured pilot.
    wall = C['pink' if b['category'] == 'living' else 'stone' if b['category'] == 'academic' else 'white']
    if b['tags'].get('building:colour', '').lower() == '#f0a0a0':
        wall = C['pink']
    return wall


def shared_form(b, z, C):
    """All silhouette-defining components; never receives a detail flag."""
    form = b['form']; h = form['height']; roof = form['roof']; wall = wall_material(b, C)
    result = Mesh(); body = Mesh(); top = Mesh(); entrance = Mesh(); panels = Mesh()
    parts = form['parts'] or [{'polygons': b['polygons'], 'triangles': b['roofTriangles'], 'height': h, 'roof':roof}]
    for part in parts:
        part_body = Mesh()
        roof = part['roof']; h = part['height']
        triangles = part['triangles'] if roof['type'] == 'flat' else [[] for _ in part['polygons']]
        if 'openBelow' in part:
            opening=part['openBelow'];soffit=opening['clearHeight'];floor=opening['floorHeight']
            part_body.extrude(part['polygons'],triangles,z+soffit,h-soffit,wall,C['paleRoof'])
            # Explicit underside and floor; the original footprint remains the canopy outline.
            for poly,indices in zip(part['polygons'],triangles):
                vertices=[p for ring in poly for p in ring[:-1]]
                for i in range(0,len(indices),3):
                    part_body.face([(vertices[k][0],vertices[k][1],z+soffit) for k in reversed(indices[i:i+3])],wall)
            part_body.extrude(part['polygons'],triangles,z-.15,floor+.15,C['stone'],C['stone'])
            for column in opening['columns']:
                part_body.box(*column['center'],z+(floor+soffit)/2,column['width'],column['depth'],soffit-floor,wall,column['angle'])
        else:
            part_body.extrude(part['polygons'], triangles, z-.5, h+.5, wall, C['paleRoof'])
        for facade in form.get('facades',[]):
            if facade['part']==part.get('id','body') and 'openCorridor' in facade['rule']:
                add_corridor(part_body,facade,z,wall,C['white'],C['white'],pitched_roof=roof['type']!='flat')
        body.extend(part_body)
        if roof['type'] != 'flat':
            geometry = roof['geometry']
            for i in range(0, len(geometry['triangles']), 3):
                top.face([(geometry['vertices'][k][0], geometry['vertices'][k][1], z+h+geometry['vertices'][k][2])
                          for k in geometry['triangles'][i:i+3]], C['red'])
        else:
            # Parapets follow each actual terrace elevation in both LODs.
            edges = part.get('parapetEdges', [(a,c) for poly in part['polygons']
                                             for ring in poly for a,c in zip(ring,ring[1:])])
            for a,c in edges:
                length = math.dist(a, c)
                if length < 2: continue
                top.box((a[0]+c[0])/2, (a[1]+c[1])/2, z+h+.4, length, .25, .8,
                        C['white'], math.atan2(c[1]-a[1], c[0]-a[0]))
    for facade in form.get('facades',[]):
        if 'attachedGallery' in facade:
            add_attached_gallery(body,facade,z,wall,C)
        if 'panels' in facade['rule']:
            add_panels(panels,facade,z,C)
        if 'windowGrid' in facade['rule']:
            add_grid_pilasters(body,facade,z,C)
        if 'windowBands' in facade['rule']:
            add_band_ledges(body,facade,z,C)
    for e in form['entrances']:
        if 'attachedPortico' in e:
            add_attached_portico(entrance,e,z,C)
            continue
        x, y = e['center']; bearing = math.radians(e['bearing'])
        nx, ny = math.sin(bearing), math.cos(bearing)
        theta = -bearing
        width = e['width']
        if e.get('porticoId'):
            floor=e['platformHeight'];front=e['outerCenter'];pw=e['porticoWidth']
            entrance.box(x+nx*.04,y+ny*.04,z+floor+1.4,width,.10,2.8,C['glass'],theta)
            entrance.box(x+nx*.06,y+ny*.06,z+floor+2.83,width+.2,.14,.12,C['white'],theta)
            # Counts can be sourced separately from estimated dimensions.
            steps=e.get('steps',3)
            step_base=e.get('stepBaseHeight',0)
            for i in range(steps):
                height=(floor-step_base)*(steps-i)/steps
                entrance.box(front[0]+nx*(i+.5)*.3,front[1]+ny*(i+.5)*.3,z+step_base+height/2,pw,.32,height,C['stone'],theta)
            continue
        # Reuse facade glass and stone to avoid two extra draw calls per chunk.
        landing=e.get('landingHeight',0)
        frame=e.get('doorFrame')
        if frame:
            bay=width/frame['bays'];pw=frame['pierWidth'];pd=frame['pierDepth']
            tx,ty=ny,-nx
            for i in range(frame['bays']):
                offset=-width/2+(i+.5)*bay
                entrance.box(x+tx*offset,y+ty*offset,z+landing+1.3,bay-pw,.35,2.6,C['glass'],theta)
            for i in range(frame['bays']+1):
                offset=-width/2+i*bay
                entrance.box(x+tx*offset+nx*(pd/2-.2),y+ty*offset+ny*(pd/2-.2),
                             z+landing+2.775/2,pw,pd,2.775,C['stone'],theta)
            # The continuous header meets the existing canopy soffit. There
            # is no glass hidden behind the intermediate solid piers.
            entrance.box(x+nx*(pd/2-.2),y+ny*(pd/2-.2),z+landing+(2.6+2.775)/2,
                         width+pw,pd,.175,C['stone'],theta)
        else:
            entrance.box(x, y, z+landing+1.3, width, .35, 2.6, C['glass'], theta)
        entrance.box(x, y, z+landing+2.9, width+1.3, 2.5, .25, C['white'], theta)
        if 'stairFlight' in e:
            p=e['stairFlight'];bottom=p['baseHeight']-.15
            entrance.box(x+nx*(p['landingDepth']-.15)/2,y+ny*(p['landingDepth']-.15)/2,
                         z+(landing+bottom)/2,p['width'],p['landingDepth']+.15,landing-bottom,C['stone'],theta)
            for i in range(1,p['riserCount']):
                stair_top=landing-(landing-p['baseHeight'])*i/p['riserCount']
                distance=p['landingDepth']+(i-.5)*p['tread']
                entrance.box(x+nx*distance,y+ny*distance,z+(stair_top+bottom)/2,
                             p['width'],p['tread']+.01,stair_top-bottom,C['stone'],theta)
        elif landing:
            # Explicitly calibrated two-level landing: both solids reach
            # below the building datum, rather than floating thin slabs.
            for distance,w,depth,landing_top in [(.65,width+1.2,1.6,landing),(.9,width+1.6,2,landing/2)]:
                entrance.box(x+nx*distance,y+ny*distance,z+(landing_top-.15)/2,w,depth,landing_top+.15,C['stone'],theta)
        else:
            entrance.box(x+nx*.65, y+ny*.65, z+.12, width+1.2, 1.6, .20, C['stone'], theta)
            entrance.box(x+nx*.9, y+ny*.9, z+.035, width+1.6, 2, .08, C['stone'], theta)
    result.add_part('01_主体轮廓', body)
    result.add_part('02_屋顶轮廓', top)
    result.add_part('03_入口与平台', entrance)
    if panels.f:
        result.add_part('05_立面专项', panels)
    return result


def facade_segments(b):
    if 'facades' in b['form']:
        return b['form']['facades']
    result=[]
    for poly in b['polygons']:
        for ri,ring in enumerate(poly):
            area=sum(a[0]*c[1]-c[0]*a[1] for a,c in zip(ring,ring[1:]))
            sign=(1 if area>0 else -1)*(-1 if ri else 1)
            for a,c in zip(ring,ring[1:]):
                length=math.dist(a,c)
                if length<.01:continue
                result.append({'start':a,'end':c,'normal':[(c[1]-a[1])/length*sign,-(c[0]-a[0])/length*sign],
                    'height':b['form']['height'],'levels':b['form']['levels'],'rule':{}})
    return result


def ordinary_building(b, z, C, detail):
    if b.get('form', {}).get('version') != 1:
        raise ValueError(f"{b['id']}: run data:prepare before rebuilding ordinary buildings")
    m = shared_form(b, z, C)
    windows = Mesh(); form = b['form']; h = form['height']; wall = wall_material(b, C)
    seed = int(hashlib.sha256(b['id'].encode()).hexdigest()[:8], 16)
    levels = max(1, round(form['levels']))
    balconies = form['archetype'] in ('dormitory', 'residential-block')
    for facade in facade_segments(b):
        a,c=facade['start'],facade['end'];rule=facade['rule']
        if rule.get('windows') is False:continue
        if 'windowGrid' in rule:
            add_grid_windows(windows,facade,z,C,detail)
            continue
        if 'windowBands' in rule:
            add_band_windows(windows,facade,z,C,detail)
        h=facade['height'];levels=max(1,round(facade['levels']))
        dx, dy = c[0]-a[0], c[1]-a[1]; length = math.hypot(dx, dy)
        if length < 2: continue
        nx, ny = facade['normal']
        theta = math.atan2(dy, dx); num = max(1, int(length/rule.get('spacing',4)))
        for level in range(levels):
            gallery=facade.get('attachedGallery')
            if gallery and level>0:continue
            corridor=rule.get('openCorridor')
            recessed=corridor is not None and level>=corridor['firstLevel']
            for i in range(num):
                f = (i+.5)/num; x, y = a[0]+dx*f+nx*.07, a[1]+dy*f+ny*.07
                if gallery:
                    x+=nx*gallery['depth'];y+=ny*gallery['depth']
                if recessed:
                    if not corridor['endInset']+.2 < f*length < length-corridor['endInset']-.2:
                        continue
                    x-=nx*corridor['depth'];y-=ny*corridor['depth']
                zz = z+(level+.56)*h/levels; ww = min(2.1, length/num*.60); wh = min(1.9, h/levels*.55)
                if band_replaces_window(facade,level,f,ww):continue
                if panel_replaces_window(facade,f,ww,zz-z,wh):continue
                if zz-wh/2 < z+facade.get('minimumHeight',0): continue
                blocked_by_door=False
                for entry in form['entrances']:
                    if 'attachedPortico' not in entry and 'doorFrame' not in entry:continue
                    bearing=math.radians(entry['bearing']);enx,eny=math.sin(bearing),math.cos(bearing)
                    ex,ey=entry['center'];floor=z+(entry['attachedPortico']['platformHeight'] if 'attachedPortico' in entry else entry['landingHeight'])
                    doorway_width=entry['width']+entry.get('doorFrame',{}).get('pierWidth',0)
                    if (nx*enx+ny*eny>.999 and abs((x-ex)*enx+(y-ey)*eny)<.3
                            and abs((x-ex)*eny-(y-ey)*enx)<(doorway_width+ww+.3)/2
                            and zz-wh/2<floor+2.8 and zz+wh/2>floor):
                        blocked_by_door=True;break
                if blocked_by_door:continue
                if detail:
                    windows.box(x, y, zz, ww+.30, .22, wh+.30, C['white'], theta)
                    windows.box(x+nx*.13, y+ny*.13, zz, ww, .10, wh,
                                C['shadeGlass'] if (seed+i*7+level*13)%7 < 2 else C['glass'], theta)
                    windows.box(x+nx*.2, y+ny*.2, zz, .055, .10, wh, C['white'], theta)
                    if not recessed and rule.get('balconies',balconies) and i%2 == 0:
                        windows.box(x+nx*.65, y+ny*.65, zz-wh*.52, ww+.5, 1.3, .14, C['white'], theta)
                        windows.box(x+nx*1.15, y+ny*1.15, zz-wh*.25, ww+.5, .1, .65, wall, theta)
                else:
                    ux, uy = dx/length*ww/2, dy/length*ww/2
                    windows.face([(x-ux,y-uy,zz-wh/2),(x+ux,y+uy,zz-wh/2),
                                  (x+ux,y+uy,zz+wh/2),(x-ux,y-uy,zz+wh/2)], C['glass'])
    m.add_part('04_立面窗格', windows)
    return m
