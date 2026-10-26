"""Photo-guided civil entrance grading, before roads and entry aprons sample soil.

The DEM is too coarse to describe this forecourt. Split the existing footprint
at a shared XY grid and apply the same bounded grade to soil and road finishes.
Do not add a second road overlay. Explicit context pads correct neighboring
coarse-DEM floor datums along with the ground; entrance/stair shapes are retained.
"""
import json
import math
from geometry import Mesh
from site_geometry import mesh_triangles, split_convex
from shore_geometry import bounds, overlaps, triangles_into, conform_edges


def load_grade(root):
    p = json.loads((root / 'data/civil-forecourt-grade.json').read_text())
    a, b, c, d = p['extent']; x, y, z, w = p['core']
    values = (*p['extent'], *p['core'], *p['origin'], *p['gradient'],
              p['groundHeight'], p['roadClearance'], p['meshStep'])
    if not all(math.isfinite(v) for v in values) or not (a < x < z < c and b < y < w < d):
        raise ValueError('Invalid civil forecourt grading domain')
    if not 0 < p['meshStep'] <= 10 or not 0 < p['roadClearance'] <= .2:
        raise ValueError('Invalid civil forecourt grading resolution/clearance')
    if 'detailBounds' in p:
        a0,b0,c0,d0=p['detailBounds']
        if (not all(math.isfinite(v) for v in (*p['detailBounds'],p['detailStep']))
                or not (a<=a0<c0<=c and b<=b0<d0<=d)
                or not 0<p['detailStep']<=min(4,p['meshStep'])):
            raise ValueError('Invalid detailed entrance grid')
    for region in p.get('preserve', []):
        x0,y0,x1,y1 = region['bounds']
        if (not all(math.isfinite(v) for v in (*region['bounds'],region['feather']))
                or x0>=x1 or y0>=y1 or region['feather']<=0):
            raise ValueError('Invalid preserved ground boundary')
    for pad in p.get('contextPads', []):
        x0,y0,x1,y1 = pad['bounds']
        if (not all(math.isfinite(v) for v in (*pad['bounds'],pad['datum'],pad['feather']))
                or x0>=x1 or y0>=y1 or pad['feather']<=0
                or not (x<=x0<x1<=z and y<=y0<y1<=w)):
            raise ValueError('Context floor pad must lie inside the grading core')
    for pad in p.get('edgePads', []):
        x0,y0,x1,y1=pad['bounds']
        if (not all(math.isfinite(v) for v in (*pad['bounds'],pad['datum'],pad['feather']))
                or x0>=x1 or y0>=y1 or pad['feather']<=0):
            raise ValueError('Invalid existing edge floor pad')
    if tie:=p.get('northTie'):
        if (not all(math.isfinite(tie[k]) for k in ('start','end','height'))
                or not b<tie['start']<w<tie['end']<=d):
            raise ValueError('Invalid north road tie')
    return p


def weight(x, y, p):
    a, b, c, d = p['extent']; lo, front, hi, back = p['core']
    def smooth(t):
        t = max(0., min(1., t)); return t * t * (3 - 2 * t)
    value = (smooth((x-a)/(lo-a)) * smooth((c-x)/(c-hi)) *
             smooth((y-b)/(front-b)) * smooth((d-y)/(d-back)))
    for region in p.get('preserve', []):
        x0,y0,x1,y1 = region['bounds']
        distance = math.hypot(max(x0-x,0,x-x1),max(y0-y,0,y-y1))
        value *= smooth(distance/region['feather'])
    return value


def height(x, y, p):
    z = p['groundHeight'] + sum((q-o)*g for q,o,g in zip((x,y),p['origin'],p['gradient']))
    if tie:=p.get('northTie'):
        t=max(0.,min(1.,(y-tie['start'])/(tie['end']-tie['start'])))
        t=t*t*(3-2*t)
        z=z*(1-t)+tie['height']*t
    for pad in p.get('edgePads', [])+p.get('contextPads', []):
        a,b,c,d = pad['bounds']
        t = min(1.,math.hypot(max(a-x,0,x-c),max(b-y,0,y-d))/pad['feather'])
        t = t*t*(3-2*t)
        z = z*t + (pad['datum']-.02)*(1-t)
    return z


def building_datum(building, default, p):
    return next((pad['datum'] for pad in p.get('contextPads', [])
                 if pad['buildingId']==building['id']),default)


def grade_mesh(mesh, p, clearance=0, original_ground=None):
    area = p['extent']; step = p['meshStep']; result = Mesh(); local = Mesh()
    result.ground_uv_bounds = list(mesh.ground_uv_bounds)
    result.xy_uv_materials = set(mesh.xy_uv_materials)
    selected = {i for i,f in enumerate(mesh.f) if overlaps(bounds([mesh.v[k] for k in f]),area)}
    for i,f in enumerate(mesh.f):
        if i not in selected:
            result.face([mesh.v[k] for k in f],mesh.m[i],mesh.face_uvs.get(i))
    # Include both fade endpoints and core boundaries; coarse source triangles
    # cannot bridge over the plateau or omit a transition altogether.
    xs = sorted({area[0],area[2],p['core'][0],p['core'][2]} |
                {i*step for i in range(math.ceil(area[0]/step),math.ceil(area[2]/step))})
    ys = sorted({area[1],area[3],p['core'][1],p['core'][3]} |
                {i*step for i in range(math.ceil(area[1]/step),math.ceil(area[3]/step))})
    if 'detailBounds' in p:
        a,b,c,d=p['detailBounds'];fine=p['detailStep']
        xs=sorted(set(xs)|{a,c}|{i*fine for i in range(math.ceil(a/fine),math.ceil(c/fine))})
        ys=sorted(set(ys)|{b,d}|{i*fine for i in range(math.ceil(b/fine),math.ceil(d/fine))})
    xs = sorted(set(xs) | {v for r in p.get('preserve',[]) for v in (r['bounds'][0],r['bounds'][2]) if area[0]<v<area[2]})
    ys = sorted(set(ys) | {v for r in p.get('preserve',[]) for v in (r['bounds'][1],r['bounds'][3]) if area[1]<v<area[3]})
    ring = [(area[0],area[1]),(area[2],area[1]),(area[2],area[3]),(area[0],area[3])]
    def transform(q):
        x,y,z=q; t=weight(x,y,p)
        if original_ground is not None and t>0:
            ground=original_ground(x,y)
            if ground is not None:
                # Coarse road/soil triangulations can leave an artificial air
                # gap in the fade. Ease out that excess as well as the DEM
                # height; t=0 retains the protected/outside road exactly.
                z-=max(0.,z-ground-clearance)*t
        return x,y,z*(1-t)+(height(x,y,p)+clearance)*t
    for ids,fi in mesh_triangles(mesh):
        if fi not in selected:continue
        original=[mesh.v[k] for k in ids]
        kept,outside=split_convex(original,ring)
        for part in outside:triangles_into(result,part,mesh.m[fi])
        if not kept:continue
        x0,y0,x1,y1=bounds(kept)
        for a,b in zip(xs,xs[1:]):
            if b<x0 or a>x1:continue
            for c,d in zip(ys,ys[1:]):
                if d<y0 or c>y1:continue
                piece,_=split_convex(kept,[(a,c),(b,c),(b,d),(a,d)])
                pieces=[piece] if piece else []
                # Floor contacts split only the cells they touch. Extending
                # every pad edge across the whole district creates thousands
                # of irrelevant slivers and needlessly exhausts the base budget.
                for pad in p.get('edgePads', [])+p.get('contextPads', []):
                    left,bottom,right,top=pad['bounds'];parts=[]
                    for part in pieces:
                        if not overlaps(bounds(part),pad['bounds']):
                            parts.append(part);continue
                        inside,outside=split_convex(part,[(left,bottom),(right,bottom),(right,top),(left,top)])
                        parts.extend(outside)
                        if inside:parts.append(inside)
                    pieces=parts
                for part in pieces:triangles_into(local,part,mesh.m[fi])
    # Pad cuts and pre-existing T junctions must agree BEFORE applying the
    # nonlinear grade. Conforming after grading would interpolate the already
    # bent long edge and retain a height mismatch at its new shared vertex.
    local = conform_edges(local, area)
    for face, material in zip(local.f, local.m):
        result.face([transform(local.v[k]) for k in face], material)
    return result


def grade_forecourt(terrain, roads, p):
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    soil=BVHTree.FromPolygons(terrain.v,[ids for ids,_ in mesh_triangles(terrain)],all_triangles=True)
    def original_ground(x,y):
        hit=soil.ray_cast(Vector((x,y,100)),Vector((0,0,-1)))[0]
        return hit.z if hit is not None else None
    return grade_mesh(terrain,p), grade_mesh(roads,p,p['roadClearance'],original_ground)
