"""Repair local terrain poke-through by splitting road faces at terrain planes.

Only the portion below terrain + clearance is lifted. Existing road faces and
UVs stay exact elsewhere; no floating overlay or extra overlapping road layer.
"""
import json
import math
from pathlib import Path
from road_display_cleanup import area, clip_edge, subtract

ROOT = Path(__file__).resolve().parents[1]


def load_repairs(root=ROOT, ids=None):
    repairs = json.loads((root/'data/road-surface-clearance.json').read_text())['repairs']
    if len({r['id'] for r in repairs}) != len(repairs):
        raise ValueError('Duplicate road clearance repair ID')
    for i, repair in enumerate(repairs):
        x0, y0, x1, y1 = repair['bounds']
        if (not all(math.isfinite(v) for v in (*repair['bounds'], repair['clearance'], repair['maxLift']))
                or x0 >= x1 or y0 >= y1 or not 0 < repair['clearance'] <= repair['maxLift']):
            raise ValueError('Invalid road clearance repair dimensions')
        if repair.get('material', 'asphalt') not in {'asphalt', 'road', 'path'}:
            raise ValueError('Unsupported road clearance material')
        for other in repairs[:i]:
            a, b, c, d = other['bounds']
            if (repair.get('material', 'asphalt') == other.get('material', 'asphalt')
                    and max(a, x0) < min(c, x1) and max(b, y0) < min(d, y1)):
                raise ValueError('Overlapping repairs would create duplicate road faces')
    if ids is not None:
        unknown = set(ids) - {r['id'] for r in repairs}
        if unknown:
            raise ValueError(f'Unknown road clearance repairs: {sorted(unknown)}')
        repairs = [r for r in repairs if r['id'] in ids]
    return repairs


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


def conform_repaired_edges(mesh, repairs, targets):
    """Retain shared split vertices and loop UVs through GLB triangulation.

    A long neighboring edge must be split before Draco quantization, or its
    rounded endpoints can pull it away from the newly subdivided edge.
    """
    epsilon, cell = 1e-5, 2
    selected = []
    for i, (face, mat) in enumerate(zip(mesh.f, mesh.m)):
        points = [mesh.v[j] for j in face]
        if area(points) > 1e-9 and any(mat == targets[r.get('material', 'asphalt')]
               and max(p[0] for p in points) >= r['bounds'][0]
               and min(p[0] for p in points) <= r['bounds'][2]
               and max(p[1] for p in points) >= r['bounds'][1]
               and min(p[1] for p in points) <= r['bounds'][3] for r in repairs):
            selected.append(i)
    buckets, seen = {}, set()
    for i in selected:
        for j in mesh.f[i]:
            x, y = mesh.v[j][:2]
            key = (round(x, 6), round(y, 6))
            if key not in seen:
                seen.add(key)
                buckets.setdefault((math.floor(x/cell), math.floor(y/cell)), []).append((x,y))
    selected = set(selected)
    faces, materials, indices, loop_uvs = [], [], [], []
    uvs = getattr(mesh, 'source_uvs', None)
    for i, (face, mat) in enumerate(zip(mesh.f, mesh.m)):
        original = [tuple(mesh.v[j]) for j in face]
        if uvs is not None:
            original = [p+tuple(uv) for p,uv in zip(original,uvs[i])]
        ring, changed = [], False
        if i in selected:
            for a, b in zip(original, original[1:]+original[:1]):
                ring.append(a)
                dx, dy = b[0]-a[0], b[1]-a[1]
                length2 = dx*dx+dy*dy
                if length2 < epsilon**2:
                    continue
                cuts = []
                for ix in range(math.floor((min(a[0],b[0])-epsilon)/cell), math.floor((max(a[0],b[0])+epsilon)/cell)+1):
                    for iy in range(math.floor((min(a[1],b[1])-epsilon)/cell), math.floor((max(a[1],b[1])+epsilon)/cell)+1):
                        for x,y in buckets.get((ix,iy), []):
                            t = ((x-a[0])*dx+(y-a[1])*dy)/length2
                            if epsilon < t < 1-epsilon and abs((x-a[0])*dy-(y-a[1])*dx) < epsilon*math.sqrt(length2):
                                cuts.append((t, (x,y,*(u+(v-u)*t for u,v in zip(a[2:],b[2:])))))
                last = -1
                for t, point in sorted(cuts):
                    if t-last > epsilon:
                        ring.append(point); changed = True; last = t
        if not changed and (i not in selected or len(original) <= 3):
            faces.append(face); materials.append(mat); indices.append(mesh.source_face_indices[i])
            if uvs is not None:
                loop_uvs.append(uvs[i])
            continue
        center = tuple(sum(p[k] for p in original)/len(original) for k in range(len(original[0])))
        for a,b in zip(ring, ring[1:]+ring[:1]):
            triangle = [center,a,b]
            if area(triangle) < 1e-9:
                continue
            start = len(mesh.v)
            mesh.v.extend(p[:3] for p in triangle)
            faces.append((start,start+1,start+2)); materials.append(mat); indices.append(mesh.source_face_indices[i])
            if uvs is not None:
                loop_uvs.append([p[3:] for p in triangle])
        mesh.changed_materials.add(mat)
    mesh.f, mesh.m, mesh.source_face_indices = faces, materials, indices
    if uvs is not None:
        mesh.source_uvs = loop_uvs
    return mesh


def repair_clearance(mesh, terrain, materials, repairs):
    # Keep the original asphalt-only call compatible with existing scripts.
    if isinstance(materials, int):
        materials = {'asphalt': materials}
    targets = {r.get('material', 'asphalt'): materials[r.get('material', 'asphalt')] for r in repairs}
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
        if mat in targets.values():
            bounds = (min(p[0] for p in original),min(p[1] for p in original),
                      max(p[0] for p in original),max(p[1] for p in original))
            for repair, ground, footprint, box in prepared:
                if mat != targets[repair.get('material', 'asphalt')]:
                    continue
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
    if report['changedFaces']:
        out = conform_repaired_edges(out, repairs, targets)
    return out, report
