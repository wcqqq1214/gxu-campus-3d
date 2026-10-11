"""Repair local terrain poke-through by splitting road faces at terrain planes.

Only the portion below terrain + clearance is lifted. Existing road faces and
UVs stay exact elsewhere; no floating overlay or extra overlapping road layer.
"""
import json
from pathlib import Path
from road_display_cleanup import area, clip_edge, subtract

ROOT = Path(__file__).resolve().parents[1]


def load_repairs(root=ROOT):
    return json.loads((root/'data/road-surface-clearance.json').read_text())['repairs']


def plane(a, b, c):
    ux, uy, uz = (b[i]-a[i] for i in range(3))
    vx, vy, vz = (c[i]-a[i] for i in range(3))
    nz = ux*vy-uy*vx
    if abs(nz) < 1e-9:
        return None
    x, y = (uy*vz-uz*vy)/-nz, (uz*vx-ux*vz)/-nz
    return x, y, a[2]-x*a[0]-y*a[1]


def intersect(poly, mask):
    for a, b in zip(mask, mask[1:]+mask[:1]):
        poly = clip_edge(poly, a, b, True)
        if len(poly) < 3:
            return []
    return poly


def below_plane(poly, ground, clearance):
    def delta(p):
        return ground[0]*p[0]+ground[1]*p[1]+ground[2]+clearance-p[2]
    out = []
    for a, b in zip(poly, poly[1:]+poly[:1]):
        da, db = delta(a), delta(b)
        if da >= 0:
            out.append(a)
        if da*db < 0:
            t = da/(da-db)
            out.append(tuple(u+(v-u)*t for u, v in zip(a, b)))
    return out


def repair_clearance(mesh, terrain, asphalt, repairs):
    if mesh.parts:
        raise ValueError('Repair aggregated road geometry')
    out = type(mesh)()
    out.v = list(mesh.v)
    out.ground_uv_bounds = list(mesh.ground_uv_bounds)
    out.xy_uv_materials = set(mesh.xy_uv_materials)
    out.changed_materials = set(getattr(mesh, 'changed_materials', ()))
    out.source_face_indices = []
    uvs = getattr(mesh, 'source_uvs', None)
    if uvs is not None:
        out.source_uvs = []
    prepared = []
    for repair in repairs:
        x0, y0, x1, y1 = repair['bounds']
        mask = [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]
        for face in terrain.f:
            for i in range(1, len(face)-1):
                triangle = [terrain.v[j] for j in (face[0], face[i], face[i+1])]
                if (max(p[0] for p in triangle) <= x0 or min(p[0] for p in triangle) >= x1
                        or max(p[1] for p in triangle) <= y0 or min(p[1] for p in triangle) >= y1):
                    continue
                ground = plane(*triangle)
                if ground is None:
                    continue
                xy = [p[:2] for p in triangle]
                if sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(xy,xy[1:]+xy[:1])) < 0:
                    xy.reverse()
                footprint = intersect(xy, mask)
                if len(footprint) >= 3 and area(footprint) > 1e-8:
                    bounds = (min(p[0] for p in footprint),min(p[1] for p in footprint),
                              max(p[0] for p in footprint),max(p[1] for p in footprint))
                    prepared.append((repair, ground, footprint, bounds))
    report = {'changedFaces': 0, 'raisedArea': 0, 'maxLift': 0}
    for index, (face, mat) in enumerate(zip(mesh.f, mesh.m)):
        original = [tuple(mesh.v[j]) for j in face]
        if uvs is not None:
            original = [p+tuple(uv) for p,uv in zip(original,uvs[index])]
        fragments, lifted = [original], []
        if mat == asphalt:
            bounds = (min(p[0] for p in original),min(p[1] for p in original),
                      max(p[0] for p in original),max(p[1] for p in original))
            for repair, ground, footprint, box in prepared:
                if bounds[2] <= box[0] or bounds[0] >= box[2] or bounds[3] <= box[1] or bounds[1] >= box[3]:
                    continue
                patch = below_plane(intersect(original, footprint), ground, repair['clearance'])
                if len(patch) < 3 or area(patch) < 1e-8:
                    continue
                heights = [ground[0]*p[0]+ground[1]*p[1]+ground[2]+repair['clearance'] for p in patch]
                lift = max(z-p[2] for p,z in zip(patch,heights))
                if lift < 1e-7:
                    continue
                if lift > repair['maxLift']:
                    raise ValueError(f'Unexpected terrain displacement: {lift}')
                fragments = [part for poly in fragments for part in subtract(poly, [p[:2] for p in patch])]
                lifted.append([(p[0],p[1],z,*p[3:]) for p,z in zip(patch,heights)])
                report['raisedArea'] += area(patch)
                report['maxLift'] = max(report['maxLift'],lift)
        old_index = getattr(mesh, 'source_face_indices', range(len(mesh.f)))[index]
        if not lifted:
            out.f.append(face); out.m.append(mat); out.source_face_indices.append(old_index)
            if uvs is not None:
                out.source_uvs.append(uvs[index])
            continue
        report['changedFaces'] += 1
        out.changed_materials.add(mat)
        for poly in fragments+lifted:
            out.face([p[:3] for p in poly],mat)
            out.source_face_indices.append(old_index)
            if uvs is not None:
                out.source_uvs.append([p[3:] for p in poly])
    return out, report
