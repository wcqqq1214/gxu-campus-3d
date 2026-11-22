"""West-campus lake beds, shore contacts and two surveyed-image water cutouts.

Coordinates in lakes_west_profiles.json are local east/north metres. Profiles
come from the reviewed OSM rings, Esri World Imagery and the GXU civil works
record. Z offsets below are display clearances, not bathymetry or survey levels.
"""

import json
from bisect import bisect_left
from pathlib import Path

from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt

from shore_geometry import bounds, overlaps
from site_geometry import inside, mesh_triangles, ring_distance


def _contains(point, rings):
    return sum(inside(point, r) for r in rings) % 2 == 1


def _distance(point, rings):
    return min(ring_distance(point, r) for r in rings)


def _elevation(xy, original, p, level):
    if not _contains(xy, p['support']):
        return original
    distance = _distance(xy, p['outline'])
    if _contains(xy, p['outline']):
        # Leave a bed that is already submerged at its original elevation.
        bed = min(original, level - 0.45)
        target = level + (bed - level) * min(distance / 1.6, 1)
    else:
        crest = 0.48 if _contains(xy, p.get('island', [])) else 0.18
        target = level + crest * min(distance / 0.65, 1)
        if distance > 0.65:
            land = (
                max(original, level + crest)
                if _contains(xy, p.get('fill', []))
                or _contains(xy, p.get('island', []))
                else original
            )
            target += (land - target) * min((distance - 0.65) / 1.85, 1)
    weight = min(1, _distance(xy, p['support']))
    return original + (target - original) * weight


def _terrain_patch(mesh, triangles, profiles, levels):
    """Overlay grading contours on original triangles, retaining their planes at the rim."""
    vertices = []
    polygons = []
    sources = []
    for face_ids, face_index in triangles:
        points = [mesh.v[i] for i in face_ids]
        start = len(vertices)
        vertices.extend(Vector(p[:2]) for p in points)
        polygons.append((start, start + 1, start + 2))
        sources.append((points, face_index))
    edges = []
    for ring in (ring for p in profiles for ring in p['constraints']):
        start = len(vertices)
        vertices.extend(Vector(xy) for xy in ring)
        edges.extend((start + i, start + (i + 1) % len(ring)) for i in range(len(ring)))
    coords, _, faces, _, _, parents = delaunay_2d_cdt(
        vertices, edges, polygons, 1, 0.00001
    )
    pieces = {}
    for ids, parent in zip(faces, parents):
        if not parent:
            continue
        (a, b, c), face_index = sources[parent[0]]
        ux, uy = b[0] - a[0], b[1] - a[1]
        vx, vy = c[0] - a[0], c[1] - a[1]
        det = ux * vy - uy * vx
        if abs(det) < 1e-9:
            continue
        points = []
        for i in ids:
            x, y = coords[i]
            dx, dy = x - a[0], y - a[1]
            z = (
                a[2]
                + (
                    (dx * vy - dy * vx) * (b[2] - a[2])
                    + (ux * dy - uy * dx) * (c[2] - a[2])
                )
                / det
            )
            for p in profiles:
                x0, y0, x1, y1 = p['bounds']
                if x0 <= x <= x1 and y0 <= y <= y1:
                    z = _elevation((x, y), z, p, levels[p['id']])
            points.append((x, y, z))
        pieces.setdefault(face_index, []).append(points)
    return pieces


def _replace_faces(mesh, replacements):
    """Keep unaffected corners, UVs and part ranges, including patches from other regions."""
    if not replacements:
        return
    faces, materials, uvs = [], [], {}
    for i, (face, material) in enumerate(zip(mesh.f, mesh.m)):
        if i not in replacements:
            if i in mesh.face_uvs:
                uvs[len(faces)] = mesh.face_uvs[i]
            faces.append(face)
            materials.append(material)
            continue
        if i in mesh.face_uvs:
            raise ValueError('West lake source face acquired custom UVs')
        for points in replacements[i]:
            start = len(mesh.v)
            mesh.v.extend(points)
            faces.append(tuple(range(start, start + len(points))))
            materials.append(material)
    used = sorted({v for face in faces for v in face})
    remap = {v: i for i, v in enumerate(used)}
    mesh.parts = [
        (label, bisect_left(used, a), bisect_left(used, b))
        for label, a, b in mesh.parts
    ]
    mesh.v = [mesh.v[v] for v in used]
    mesh.f = [tuple(remap[v] for v in face) for face in faces]
    mesh.m, mesh.face_uvs = materials, uvs


def _signature(points):
    return tuple(sorted(tuple(round(axis, 5) for axis in point) for point in points))


def apply_lakes(base, surfaces, C):
    """Apply after base.update(shore_meshes), before foundation and export grading."""
    profiles = json.loads(
        Path(__file__).with_name('lakes_west_profiles.json').read_text()
    )
    water, terrain = base['water'], base['terrain']
    by_id = {s['id']: s for s in surfaces}
    water_faces = {
        _signature([water.v[k] for k in f]): i
        for i, f in enumerate(water.f)
        if water.m[i] == C['water']
    }
    water_edits = {}
    nearby = []
    west_bounds = (
        min(p['bounds'][0] for p in profiles),
        min(p['bounds'][1] for p in profiles),
        max(p['bounds'][2] for p in profiles),
        max(p['bounds'][3] for p in profiles),
    )
    for corners, i in mesh_triangles(terrain):
        box = bounds([terrain.v[v] for v in corners])
        if overlaps(box, west_bounds) and any(
            overlaps(box, p['bounds']) for p in profiles
        ):
            nearby.append((corners, i))
    for p in profiles:
        s = by_id[p['id']]
        level = s['waterLevel']
        if p['waterChanged']:
            indices = s['triangles']
            old_faces = [
                water_faces[
                    _signature([(*s['vertices'][v], level) for v in indices[i : i + 3]])
                ]
                for i in range(0, len(indices), 3)
            ]
            water_edits.update((i, []) for i in old_faces)
            water_edits[old_faces[0]] = [
                [(*point, level) for point in triangle]
                for triangle in p['waterTriangles']
            ]
    levels = {p['id']: by_id[p['id']]['waterLevel'] for p in profiles}
    ground_edits = _terrain_patch(terrain, nearby, profiles, levels)
    _replace_faces(terrain, ground_edits)
    _replace_faces(water, water_edits)
