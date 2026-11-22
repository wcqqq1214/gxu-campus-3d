"""Verify accepted materials-college entry geometry in source, base and near assets.

Run Blender with --check-root=/path/to/candidate and --report=/path/to/report.json.
Photo proportions are estimated; these checks do not validate real-world dimensions.
"""

import json
import math
import re
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

R = Path(__file__).resolve().parents[1]
P = next(
    (
        Path(a.split('=', 1)[1]).resolve()
        for a in sys.argv
        if a.startswith('--check-root=')
    ),
    R,
)
REPORT = next(
    (Path(a.split('=', 1)[1]).resolve() for a in sys.argv if a.startswith('--report=')),
    R / 'work/materials-entry-geometry.json',
)
sys.path.insert(0, str(R / 'blender'))
bs = json.loads((P / 'public/data/buildings.json').read_text())
b = next(b for b in bs if b['id'] == 'relation/11564999')
e = b['form']['entrances'][0]
p = e['recessedStairEntry']
z = b['elevation']
angle = math.radians(e['bearing'])
n = Vector((math.sin(angle), math.cos(angle), 0))
u = Vector((n.y, -n.x, 0))
front = Vector((*e['center'], z))
up = Vector((0, 0, 1))
point = lambda w, d, h: front + u * w - n * d + up * h


def in_northeast_stair(w, d):
    # Bounds of the surveyed side-flight replacement in the original entry frame.
    return (
        -21 <= w < -9
        and -20 < d < -8.4
        or -25.39 < w < -16
        and -20 < d <= -4
        or -16.4 <= w < -12.82
        and -8.415 < d <= -0.3
        or -12.82 <= w < -9.42
        and -7.49 < d < -5.44
    )


def finish_name(name):
    return re.sub(r'\.\d+$', '', name).replace('entryBorderStone', 'stone')


def trees(objects, *, upward_only=False):
    result = []
    for o in objects:
        if o.type != 'MESH':
            continue
        faces = o.data.polygons
        if upward_only:
            normal_matrix = o.matrix_world.to_3x3().inverted_safe().transposed()
            faces = [f for f in faces if (normal_matrix @ f.normal).z > 0.93]
            if not faces:
                continue
        result.append(
            (
                BVHTree.FromPolygons(
                    [o.matrix_world @ v.co for v in o.data.vertices],
                    [tuple(f.vertices) for f in faces],
                ),
                [finish_name(o.data.materials[f.material_index].name) for f in faces],
            )
        )
    return result


def ray(ts, start, direction, distance):
    hits = []
    for tree, mats in ts:
        pos, normal, index, dist = tree.ray_cast(start, direction, distance)
        if pos is not None:
            hits.append((dist, pos, normal, mats[index]))
    return min(hits, key=lambda x: x[0], default=None)


def parking_joint_alignment(objects):
    # Inspect actual source/exported UVs after batching and quantization.
    # Hole centres must sit halfway between texture joints in both directions.
    triangles = []
    for o in objects:
        if o.type != 'MESH' or not o.data.uv_layers.active:
            continue
        mesh = o.data
        uvs = mesh.uv_layers.active.data
        for f in mesh.polygons:
            if re.sub(r'\.\d+$', '', mesh.materials[f.material_index].name) != 'path':
                continue
            verts = []
            for loop in f.loop_indices:
                q = (
                    o.matrix_world @ mesh.vertices[mesh.loops[loop].vertex_index].co
                    - front
                )
                verts.append((q.dot(u), -q.dot(n), tuple(uvs[loop].uv)))
            for i in range(1, len(verts) - 1):
                a, b, c = verts[0], verts[i], verts[i + 1]
                den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
                if abs(den) > 1e-9:
                    triangles.append((a, b, c, den))
    errors = []
    for w0 in (-20.7, 16.5):
        for i in range(7):
            for j in range(28):
                w = w0 + i * 0.6 + 0.14
                d = -19 + j * 0.65 + 0.14
                if in_northeast_stair(w, d):
                    continue
                sample = None
                for a, b, c, den in triangles:
                    aa = ((b[1] - c[1]) * (w - c[0]) + (c[0] - b[0]) * (d - c[1])) / den
                    bb = ((c[1] - a[1]) * (w - c[0]) + (a[0] - c[0]) * (d - c[1])) / den
                    if min(aa, bb, 1 - aa - bb) < -1e-6:
                        continue
                    sample = [
                        aa * a[2][k] + bb * b[2][k] + (1 - aa - bb) * c[2][k]
                        for k in (0, 1)
                    ]
                    break
                assert sample is not None, ('missing parking UV probe', w, d)
                error = max(
                    abs((sample[0] * 2) % 1 - 0.5), abs((sample[1] * 4) % 1 - 0.5)
                )
                assert error < 0.012, (
                    'paving joint crosses grass-cell centre',
                    w,
                    d,
                    sample,
                    error,
                )
                errors.append(error)
    return max(errors)


def border_course_alignment(objects):
    # Find the lowest horizontal stone finish below the projecting coping.
    # Test transverse joints on both legs of the border after export.
    tris = []
    nose_corners = []
    for o in objects:
        if o.type != 'MESH' or not o.data.uv_layers.active:
            continue
        m = o.data
        uv = m.uv_layers.active.data
        for f in m.polygons:
            if (
                re.sub(r'\.\d+$', '', m.materials[f.material_index].name)
                != 'entryBorderStone'
            ):
                continue
            vs = []
            for loop in f.loop_indices:
                q = o.matrix_world @ m.vertices[m.loops[loop].vertex_index].co - front
                vs.append((q.dot(u), -q.dot(n), q.z, tuple(uv[loop].uv)))
            nose_corners.extend(
                v[3][1] * 4
                for v in vs
                if abs(v[1] + 8.8) < 0.015 and 15.99 < abs(v[0]) < 16.08
            )
            for i in range(1, len(vs) - 1):
                a, b, c = vs[0], vs[i], vs[i + 1]
                den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
                if abs(den) > 1e-9:
                    tris.append((a, b, c, den))
    assert nose_corners and min(nose_corners) > 15.995 and max(nose_corners) < 16.04, (
        'nose short-cut stone',
        nose_corners,
    )
    probes = [
        (side * 16.12, -19 + j * 0.65 + 0.14, 1, 4)
        for side in (-1, 1)
        for j in range(17, 28)
    ]
    nose_probes = [
        (side * 16.03, d, 1, 4)
        for side in (-1, 1)
        for d in (-8.79, -8.77, -8.74, -8.6, -8.4)
    ]
    probes += [
        (w0 + i * 0.6 + 0.14, -0.38, 0, 2) for w0 in (-20.7, 16.5) for i in range(7)
    ]
    errors = []
    for w, d, axis, factor in probes + nose_probes:
        if in_northeast_stair(w, d) or (w < 0 and abs(d + 8.4) < 0.001):
            continue
        candidates = []
        for a, b, c, den in tris:
            aa = ((b[1] - c[1]) * (w - c[0]) + (c[0] - b[0]) * (d - c[1])) / den
            bb = ((c[1] - a[1]) * (w - c[0]) + (a[0] - c[0]) * (d - c[1])) / den
            if min(aa, bb, 1 - aa - bb) < -1e-6:
                continue
            candidates.append(
                (
                    aa * a[2] + bb * b[2] + (1 - aa - bb) * c[2],
                    aa * a[3][axis] + bb * b[3][axis] + (1 - aa - bb) * c[3][axis],
                )
            )
        assert candidates, ('missing border UV', w, d)
        value = min(candidates)[1]
        if (w, d, axis, factor) in nose_probes:
            # The first 40 cm belong to one cut stone, with no interior seam/sliver.
            # Allow the measured UV quantization error at the starting boundary.
            assert 16.0 - 0.015 < value * factor < 16.75, (
                'fragmented wall-foot nose',
                w,
                d,
                value * factor,
            )
            continue
        error = abs((value * factor) % 1 - 0.5)
        assert error < 0.015, ('border course joint alignment', w, d, error)
        errors.append(error)
    return max(errors)


def check_northeast_site(building, roads, ground, tol):
    # Independent positions and tolerance bands from the three panoramas.
    surfaces = building + roads

    def finish(w, d, expected, start=5.10):
        hit = ray(surfaces, point(w, d, start), -up, 8)
        assert hit and hit[3] == expected and hit[2].z > 0.65, (
            'east entrance finish',
            w,
            d,
            expected,
            hit,
        )
        return hit[1].z - z

    for w, d, name in [
        (-24.23, -10.15, 'grass'),
        (-22.64, -9.53, 'grass'),
        (-15.8, -11.4, 'grass'),
        (-18.65, -13.4, 'stone'),
        (-18.4, -9.85, 'stone'),
        (-18.38, -6.2, 'asphalt'),
        (-23.28, -14.92, 'materialsGrassPaver'),
        (-21.48, -15.60, 'materialsGrassPaver'),
        (-14.5, -3, 'grass'),
        (-14, -6.2, 'asphalt'),
        (-11.56, -6.5, 'asphalt'),
    ]:
        finish(w, d, name)
    # The upper east pier, soffit and the two perpendicular stone returns
    # must be real surfaces. Rays also detect a fascia painted across the entry.
    for w, d, direction in [(-20.65, -16.1, u), (-18.53, -14.0, n)]:
        hit = ray(building, point(w, d, 3.65), direction, 0.85)
        assert (
            hit and hit[3] == 'materialsRetainingStone' and hit[2].dot(direction) < -0.9
        ), ('stone face', w, d, hit)
    for d in [-16.8, -15.08]:
        assert abs(finish(-20.1, d, 'gateStone', 4.65) - 4.447) < tol + 0.006, (
            'stone cap',
            d,
        )
    l = ray(building, point(-12.48, -6.4, 3.3), up, 4)
    assert l and l[2].z < -0.98 and abs(l[1].z - z - 6.45) < tol + 0.008, (
        'passage soffit',
        l,
    )
    for d in (-7.15, -6.43, -5.80):
        assert ray(building, point(-15.7, d, 4.74), u, 6.05) is None, (
            'first passage bay obstructed',
            d,
        )
        h = finish(-11.56, d, 'asphalt')
        soil = ray(ground, point(-11.56, d, 3.5), -up, 2.5)
        assert soil and 0.004 < h + z - soil[1].z < 0.09, (
            'first bay bedding',
            d,
            h,
            soil,
        )
        assert abs(h - 3.08) < tol + 0.006, ('passage floor', d, h)
    assert 3.30 < l[1].z - z - 3.08 < 3.45
    # Probe individual sections through the previously visible west lawn hump.
    # Three independent street views put the outer lawn corner below the wall foot.
    corner = ray(surfaces, point(-25.39254, -11.91251, 3.8), -up, 2.0)
    wall_foot = ray(surfaces, point(-20.18575, -14.41659, 2.96), -up, 0.9)
    assert corner and wall_foot, (
        'missing paired lawn/wall benchmarks',
        corner,
        wall_foot,
    )
    relative = corner[1].z - wall_foot[1].z
    assert -0.30 < relative < -0.205, (
        'street lawn relative to retaining wall foot',
        relative,
    )
    profile = []
    for d in (-11.25, -10.1, -9.05, -8.55):
        hs = []
        for w in (
            -24.9,
            -24.4,
            -23.9,
            -23.4,
            -22.9,
            -22.4,
            -21.9,
            -21.4,
            -20.9,
            -20.4,
            -19.9,
            -19.4,
        ):
            hit = ray(surfaces, point(w, d, 6), -up, 7)
            assert hit, ('north lawn/parking seam', w, d)
            hs.append(hit[1].z - z)
        assert (
            0.15 < hs[-1] - hs[0] < 0.34
            and min(y - x for x, y in zip(hs, hs[1:])) > -tol - 0.008
        ), (
            'west lawn reverses slope',
            d,
            hs,
        )
        profile.append(hs)
    hs = [
        finish(-18.37, d, 'stone')
        for d in (-13.5, -12.7, -11.9, -10.8, -9.9, -8.7, -8.0)
    ]
    assert max(hs) - min(hs) < 0.075 + tol, ('crosswalk has a ridge', hs)
    return dict(
        sideStairSamples=33,
        coveredPassageClearance=l[1].z - z - 3.08,
        crosswalkRange=max(hs) - min(hs),
        westLawnSections=profile,
        lawnMinusWallFootMeters=relative,
    )


def check(objects, ground, tol, roads):
    ts = trees(objects)
    rows = []

    def top(kind, w, d, h):
        hit = ray(ts, point(w, d, h + 0.12), -up, 0.3)
        assert hit and abs(hit[1].z - z - h) < tol, (kind, w, d, h, hit)
        if kind == 'canopy-crossbeam' and hit[2].z < 0:
            # At the front crossbeam the 15-bit export snaps an existing
            # soffit face onto the beam top. BVH tie order depends on the
            # whole chunk. Require an upward face at the same XY, Z and material.
            face = ray(
                trees(objects, upward_only=True), point(w, d, h + 0.12), -up, 0.3
            )
            assert face and face[3] == hit[3] and abs(face[1].z - hit[1].z) < 0.0005, (
                'missing coplanar beam top',
                face,
                hit,
            )
            hit = face
        assert hit[2].z > 0.93, (kind, 'top facing down', hit)
        rows.append(dict(kind=kind, w=w, d=d, expected=h, actual=hit[1].z - z))

    # Independently fixed accepted rise/run, not values inferred from mesh.
    for i in range(13):
        d = -5.4 + (i + 0.5) * 0.3
        h = 4.0 + 2.6 * (i + 1) / 14
        for w in (-5, 0, 5):
            top('outer-tread', w, d, h)
        assert ray(ts, point(0, d, h + 0.1), up, 2) is None, ('blocked outer flight', i)
    for i in range(21):
        d = p['innerStart'] + (i + 0.5) * 0.3
        h = 6.6 + 3.3 * (i + 1) / 22
        for w in (-3, 0, 3):
            top('inner-tread', w, d, h)
        assert ray(ts, point(0, d, h + 0.1), up, 2) is None, ('blocked inner flight', i)
    for w in (-3, 0, 3):
        top('intermediate', w, 6.2, 6.6)
        top('rear-landing', w, 15.2, 9.9)
    for w in (-4.5, 4.5):
        for d in (1.3, 7.1):
            hit = ray(ts, point(w, d, 8) + n, -n, 1.2)
            assert hit and hit[3] == 'white' and abs(hit[0] - 0.675) < tol + 0.01, (
                'round support',
                w,
                d,
                hit,
            )
            hit = ray(ts, point(w, d, 6.85) + n, -n, 1.2)
            assert hit and hit[3] == 'dark', ('column foot sleeve missing', w, d)
    for side in (-1, 1):
        hit = ray(ts, point(side * 5.5, 4, 7.2), u * side, 0.6)
        assert hit and hit[3] == 'entryGuardGlass', (
            'landing guard panel missing',
            side,
        )
        hit = ray(ts, point(side * 5.88, 4, 7.8), -up, 0.3)
        assert hit and hit[3] == 'dark' and abs(hit[1].z - z - 7.68) < tol + 0.02, (
            'guard top proportion',
            side,
        )
    for d in (0.8, 7.6):
        top('canopy-crossbeam', 0, d, 14.4)
    if 'portalBeam' in p['canopy']:
        top('portal-beam', 0, 1.3, 18.8)
        hit = ray(ts, point(0, 1.3, 17.4), up, 0.6)
        assert hit and abs(hit[1].z - z - 17.7) < tol and hit[2].z < -0.93, (
            'portal beam soffit',
            hit,
        )
        for w in (-4.5, 4.5):
            hit = ray(ts, point(w, 1.3, 15) + n, -n, 1.2)
            assert hit and hit[3] == 'white', ('upper column shaft missing', w, hit)
    # Mid-bay holes stay open below the existing high lattice.
    assert ray(ts, point(0, 2, 14.2), up, 2) is None, 'low lattice accidentally filled'
    top('canopy-rib', 5 / 7, 2, 14.4)
    hall = p.get('hall')
    door_d = p['recess'] + (hall['depth'] if hall else 0) - 0.08
    hit = ray(ts, point(1, door_d - 0.4, 11.3), -n, 0.6)
    assert hit and hit[3] == 'glass', ('rear glass door', hit)
    if hall:
        # Independently probe the full walking volume, including the old facade
        # plane. A door painted over an intact wall must fail these rays.
        for w in (-4.8, -2, 0, 2, 4.8):
            for h in (10.3, 11.3, 12.8, 14):
                assert ray(ts, point(w, p['recess'] - 0.3, h), -n, 4.8) is None, (
                    'hall blocked',
                    w,
                    h,
                )
            for d in (16.5, 18, 20):
                top('hall-floor', w, d, 9.9)
                hit = ray(ts, point(w, d, 14), up, 0.6)
                assert hit and abs(hit[1].z - z - 14.3) < tol and hit[2].z < -0.93, (
                    'hall ceiling',
                    w,
                    d,
                    hit,
                )
        for w in (-5.2, 5.2):
            for d in (3, 8, 12):
                top('side-gallery', w, d, 9.9)
        # No guard crosses the transition from stair landing into side aisles.
        for side in (-1, 1):
            assert ray(ts, point(side * 3.8, 15, 10.4), u * side, 1.8) is None, (
                'gallery access blocked'
            )
    # Separate lower flight, raised cross-landing and genuinely open side courts.
    for i in range(7):
        for w in (-8, 0, 8):
            top('lower-tread', w, -10.5 + (i + 0.5) * 0.3, 2.8 + 0.15 * (i + 1))
    for w in (-14, -6, 0, 6, 14):
        if w != -14:  # The north end is the surveyed passage approach.
            top('raised-terrace', w, -7, 4)
    for side in (-1, 1):
        for d in (-4.5, -3, -1):
            top('sunken-floor', side * 8.5, d, 1.3)
            assert ray(ts, point(side * 8.5, d, 1.4), up, 5) is None, (
                'sunken court capped',
                side,
                d,
            )
        for i in range(15):
            top(
                'court-descending-tread',
                side * 12.1,
                -5.4 + (i + 0.5) * 0.25,
                4 - 0.16875 * (i + 1),
            )
        assert ray(ts, point(side * 12.1, -5.7, 4.5), -n, 0.5) is None, (
            'descending stair entrance blocked'
        )
        for d in (-1.5, -0.5):
            top('court-bottom-landing', side * 12.1, d, 1.3)
        assert ray(ts, point(side * 12.1, -1, 1.8), -u * side, 3) is None, (
            'lower landing cannot turn into court'
        )
        # Paired sloping handrails above the descending flight, below the
        # separate level retaining-wall guard.
        for w in (11.45, 12.75):
            hit = ray(ts, point(side * w, -3.525, 3.7), -up, 0.5)
            assert hit and hit[3] == 'dark', ('descending handrail missing', side, w)
        if side > 0:
            top('outer-walk', side * 14.5, -3, 4)
    # Ground and pavement samples span every external patch, plus the low approach.
    # The outer grade now continues all the way to the level stair approach;
    # no abrupt change of slope is left at the old two-metre perimeter strip.
    plaza = p['landscape']['groundPatches'][0]

    def plaza_height(w, d):
        vs = plaza['vertices']
        ids = plaza['triangles']
        for i in range(0, len(ids), 3):
            a, b, c = [vs[k] for k in ids[i : i + 3]]
            den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
            u = ((b[1] - c[1]) * (w - c[0]) + (c[0] - b[0]) * (d - c[1])) / den
            v = ((c[1] - a[1]) * (w - c[0]) + (a[0] - c[0]) * (d - c[1])) / den
            if min(u, v, 1 - u - v) >= -1e-6:
                return u * a[2] + v * b[2] + (1 - u - v) * c[2]
        raise AssertionError('Plaza sample outside paving')

    for w in (-15, -8, 0, 8, 15):
        for d in (-23.5, -21, -18, -15, -12.1):
            if not in_northeast_stair(w, d):
                top('graded-plaza', w, d, plaza_height(w, d))
    for w in (-8, 0, 8):
        for d in (-11.9, -11.2, -10.6):
            top('level-stair-approach', w, d, 2.8)
    # Field views at 183°, 152° and 211° fix a north-facing stair. Check the
    # flight and its two exits in place of the former parking/plaza samples.
    for i in range(11):
        w = -17 + (i + 0.5) * 3.95 / 11
        h = 2.71 + (i + 1) * 0.15
        for d in (-14.15, -13.46, -12.76):
            top('northeast-side-tread', w, d, h)
            soil = ray(ground, point(w, d, h + 0.2), -up, 10)
            assert soil and soil[1].z < z + h - 0.004, ('soil through side stair', w, d)
        assert ray(ts, point(w, -13.46, h + 0.08), up, 1.9) is None, (
            'blocked side stair',
            i,
        )
    for d in (-14.425, -12.495):
        rail = ray(ts, point(-15.025, d, 5.11), -up, 0.9)
        assert rail and rail[3] == 'dark', ('missing side-flight handrail', d, rail)
    top('northeast-foot-walk', -17.45, -13.45, 2.71)
    top('northeast-exit', -12.0, -11.0, 4.36 - 0.36 * 1.45 / 4.05)
    assert ray(ts, point(-12.0, -8.6, 4.7), -n, 0.45) is None, (
        'blocked side-to-terrace exit'
    )
    clearances = []
    for patch in p['landscape']['groundPatches']:
        vs = patch['vertices']
        indices = patch['triangles']
        for i in range(0, len(indices), 3):
            tri = [vs[k] for k in indices[i : i + 3]]
            w, d, h = [sum(v[k] for v in tri) / 3 for k in (0, 1, 2)]
            if in_northeast_stair(w, d):
                continue
            hit = ray(ts, point(w, d, h + 0.15), -up, 0.3)
            g = ray(ground, point(w, d, h + 1), -up, 10)
            assert hit and g, ('missing external paving', patch['id'], w, d)
            clearance = hit[1].z - g[1].z
            assert 0.002 < clearance < 0.09, (
                'paving bedding contact',
                patch['id'],
                w,
                d,
                clearance,
            )
            clearances.append(clearance)
    for w in (-8, 0, 8):
        hit = ray(ts, point(w, -11.9, 3.2), -up, 1)
        g = ray(ground, point(w, -11.9, 4), -up, 5)
        assert hit and g and 0.002 < hit[1].z - g[1].z < 0.09, (
            'low approach bedding clearance'
        )
    # Probe the visible lawn side, not just the hidden soil under a paving
    # centroid: a deep skirt used to hide an artificially lowered perimeter.
    edges = [(w, -24, 0, -1) for w in (-15, -10, -5, 0, 5, 10, 15)]
    edges += [(side * 16, d, side, 0) for side in (-1, 1) for d in (-23, -21)]
    edges += [(w, -20, 0, -1) for w in (-21, -19, -17, 17, 19, 23, 26, 29)]
    edges += [(w, -0.3, 0, 1) for w in (-21, -19, -17, 17, 19, 23, 26, 29)]
    edge_steps = []
    for w, d, dw, dd in edges:
        # Start below the projecting information screen when reading ground finishes.
        paving = ray(ts, point(w - dw * 0.08, d - dd * 0.08, 6), -up, 12)
        lawn = ray(ground, point(w + dw * 0.08, d + dd * 0.08, 12), -up, 15)
        assert paving and lawn, ('missing outer edge', w, d)
        step = paving[1].z - lawn[1].z
        assert -0.04 < step < 0.13, (
            'outer paving looks like a raised plinth',
            w,
            d,
            step,
            paving,
            lawn,
        )
        edge_steps.append(step)
    for w in (-10, -5, 0, 5, 10):
        for d in (-1, -3, -4.5):
            assert ray(roads, point(w, d, 10), -up, 20) is None, (
                'old road remains below entrance',
                w,
                d,
            )
    # Parking / side access must meet the actual retained road mesh in height.
    joins = []
    for patch in p['landscape']['groundPatches']:
        if patch['id'] not in ('north-parking', 'south-access'):
            continue
        side = -1 if patch['id'] == 'north-parking' else 1
        for d in (-18, -15, -12, -9, -6, -3, -1, -0.5):
            edges = []
            ring = patch['boundary']
            for a, b in zip(ring, ring[1:]):
                if min(a[1], b[1]) <= d <= max(a[1], b[1]) and abs(b[1] - a[1]) > 1e-7:
                    edges.append(a[0] + (b[0] - a[0]) * (d - a[1]) / (b[1] - a[1]))
            w = min(edges) if side < 0 else max(edges)
            if side < 0 and -20 < d < -4:
                # The new continuous inlay spans the old gap. The boundary
                # between road-owned and building-owned faces moved 9 cm.
                w -= 0.09
            paving = ray(ts, point(w - side * 0.08, d, 6), -up, 15)
            road = ray(roads, point(w + side * 0.08, d, 12), -up, 15)
            assert paving and road, ('missing parking/road contact', patch['id'], d)
            step = paving[1].z - road[1].z
            assert abs(step) < 0.12, (
                'parking edge suspended above or below road',
                patch['id'],
                d,
                step,
            )
            joins.append(step)
    # The lane also wraps behind both parking areas. These checks must not
    # silently skip asphalt when checking the rear edge against nearby soil.
    rear_joins = []
    # At w=21 the two differently quantized paving materials meet.
    # Check both adjacent surfaces against the road, 2 cm from the joint.
    for w in (
        -21.5,
        -21,
        -20,
        -19,
        -18,
        -17,
        17,
        18,
        19,
        20,
        20.98,
        21.02,
        23,
        25,
        27,
        28,
        29,
    ):
        paving = ray(ts, point(w, -0.38, 6), -up, 15)
        road = ray(roads, point(w, -0.22, 12), -up, 15)
        assert paving and road, ('missing rear parking/road join', w)
        step = paving[1].z - road[1].z
        assert -0.04 < step < 0.12, ('rear parking/road step', w, step)
        rear_joins.append(step)
    # South parking and access share one grading field. A narrow trough or
    # ridge on their seam must not be hidden by matching the edge height only.
    seam_breaks = []
    for d in (-6, -4, -2, -0.5):
        # The two materials quantize separately; sample either side, then
        # extrapolate both planes to the seam instead of casting on its edge.
        hits = [ray(ts, point(w, d, 12), -up, 15) for w in (20.8, 20.96, 21.04, 21.2)]
        assert all(hits), ('missing parking/access seam', d)
        heights = [h[1].z for h in hits]
        left = (heights[1] - heights[0]) / 0.16
        right = (heights[3] - heights[2]) / 0.16
        assert (
            abs(heights[1] + left * 0.04 - heights[2] + right * 0.04) < tol + 0.008
        ), ('parking/access height seam', d)
        bend = abs(right - left)
        assert bend < 0.06, ('parking/access slope break', d, bend)
        seam_breaks.append(bend)
    # The adjusted parking plane must meet the outside retaining face below
    # its coping, without exposing a floating wall foot or filling the court.
    for side in (-1, 1):
        for d in (-6, -4, -2, -0.6):
            if side < 0:  # Replaced at W=-16 by the open north approach, tested below.
                continue
            paving = ray(ts, point(side * 16.25, d, 12), -up, 15)
            assert paving, ('missing wall-side parking', side, d)
            h = paving[1].z - z + 0.15
            wall = ray(ts, point(side * 16.25, d, h), -u * side, 0.4)
            assert wall and wall[3] == 'stone' and abs(wall[0] - 0.25) < tol + 0.01, (
                'parking/retaining wall gap',
                side,
                d,
                wall,
            )
    # Sample below the projecting wall coping: the narrow margin must sit on
    # the parking grade, not on a new raised foundation or kerb.
    wall_slopes = []
    for side in (1,):
        for d in (-6, -4, -2):
            a = ray(ts, point(side * 16.3, d, 3.8), -up, 3)
            b = ray(ts, point(side * 16.8, d, 3.8), -up, 3)
            assert a and b, ('missing wall-foot paving', side, d)
            slope = (b[1].z - a[1].z) / 0.5
            assert 0 < slope < (0.14 if side < 0 else 0.06), (
                'steep or reversed wall-side crossfall',
                side,
                d,
                slope,
            )
            wall_slopes.append(abs(slope))
            trim = ray(ts, point(side * 16.12, d, 3.8), -up, 3)
            expected = a[1].z - slope * 0.18
            assert (
                trim and trim[3] == 'stone' and abs(trim[1].z - expected) < 0.02 + tol
            ), ('wall-foot trim not flush', side, d, trim)
            assert ray(ts, trim[1] - up * 0.002, -up, 0.02) is None, (
                'stacked paving below wall-foot inlay',
                side,
                d,
            )
        corner = ray(ts, point(side * 16.35, -0.65, 3.8), -up, 3)
        assert corner and corner[3] == 'stone', (
            'missing bevel at rear wall-foot return',
            side,
        )
        for w, d, material in (
            (16.03, -8.76, 'stone'),
            (16.15, -8.65, 'path'),
            (16.13, -8.4, 'stone'),
            (16.22, -8.25, 'path'),
            (16.22, -7.95, 'stone'),
        ):
            if side < 0 and d <= -8.4:
                continue
            end = ray(ts, point(side * w, d, 3.8), -up, 3)
            assert end and end[3] == material, (
                'wall-foot inlay has a blunt start',
                side,
                d,
                end,
            )
    # The north rear margin ends with a finite, flush mouth at the lane,
    # rather than a zero-width triangle that can collapse during quantization.
    for w, d, material in (
        (-21.84, -0.33, 'stone'),
        (-21.84, -0.40, 'path'),
        (-21.6, -0.37, 'stone'),
    ):
        hit = ray(ts, point(w, d, 3.8), -up, 3)
        assert hit and hit[3] == material, ('rear inlay/lane junction', w, d, hit)
    # The stone rear course must continue down the road-facing shallow edge.
    for w in (-20, -18, 18, 20):
        top = ray(ts, point(w, -0.33, 3.8), -up, 3)
        assert top and top[3] == 'stone', ('rear border top', w, top)
        edge = ray(ts, point(w, -0.55, top[1].z - z - 0.04), -n, 0.35)
        assert edge and edge[3] == 'stone' and abs(edge[0] - 0.25) < 0.02 + tol, (
            'rear stone edge material discontinuity',
            w,
            edge,
        )
    # Closely probe rear grass-cell edges as well as their centres. A reduced
    # lift must remain clear of the paving after each LOD's quantization.
    grass_clearances = []
    for w0 in (-20.7, 16.5):
        for i in range(7):
            for j in range(14, 28):
                for dw, dd in (
                    (0.14, 0.14),
                    (0.03, 0.03),
                    (0.25, 0.03),
                    (0.03, 0.25),
                    (0.25, 0.25),
                ):
                    w = w0 + i * 0.6 + dw
                    d = -19 + j * 0.65 + dd
                    if in_northeast_stair(w, d):
                        continue
                    grass = ray(ts, point(w, d, 6), -up, 6)
                    assert grass and grass[3] == 'green', (
                        'missing or buried grass-cell edge',
                        w,
                        d,
                        grass,
                    )
                    paving = ray(ts, grass[1] - up * 0.0002, -up, 0.025)
                    assert paving and paving[3] == 'path', (
                        'grass-cell backing missing',
                        w,
                        d,
                        paving,
                    )
                    clearance = grass[1].z - paving[1].z
                    assert 0.0004 < clearance < 0.012, (
                        'grass-cell lift or intersection',
                        w,
                        d,
                        clearance,
                    )
                    grass_clearances.append(clearance)
    # Check the neighbouring grades as well as the last road-matching strip:
    # moving the whole slope break one station inward is not a smooth join.
    transition_bends = []
    for w in (-20, -18, -16.3, 16.3, 18, 20, 20.9, 21.1, 23, 25, 27, 29):
        stations = (-10, -8, -6, -4, -2, -0.9, -0.34)
        stations = tuple(d for d in stations if not in_northeast_stair(w, d))
        if len(stations) < 3:
            continue
        heights = []
        for d in stations:
            hit = ray(ts, point(w, d, 3.8), -up, 3)
            # Grass-cell lifts vary between 4 and 8 mm above the paving grade.
            if hit and hit[3] == 'green':
                hit = ray(ts, hit[1] - up * 0.0002, -up, 0.03)
            assert hit, ('missing rear blending station', w, d)
            heights.append(hit[1].z)
        slopes = [
            (b - a) / (db - da)
            for a, b, da, db in zip(heights, heights[1:], stations, stations[1:])
        ]
        bend = max(abs(b - a) for a, b in zip(slopes, slopes[1:]))
        inner_bend = max(
            (abs(b - a) for a, b in zip(slopes[2:], slopes[3:])), default=0
        )
        assert inner_bend < 0.055, (
            'concentrated parking grade change before rear edge',
            w,
            inner_bend,
        )
        assert bend < 0.06, ('upstream parking grade change', w, bend)
        transition_bends.append(bend)
    # The last paving strip meets the slope of the retained lane, rather than
    # only matching its edge height. Avoid the two existing south road planes'
    # junction and the narrow side-edge blend when probing this transition.
    rear_bends = []
    for w in (-20, -18, -17, 17, 19, 20, 23, 25, 27):
        a = ray(ts, point(w, -0.8, 3.8), -up, 3)
        b0 = ray(ts, point(w, -0.55, 3.8), -up, 3)
        assert a and b0, ('missing rear transition', w)
        paving_slope = (b0[1].z - a[1].z) / 0.25
        # The lane is clipped to a narrow remnant behind this edge. Its decoded
        # sliver normals are unstable, so all LODs use the retained source road
        # plane as the slope reference; actual decoded edge heights are tested above.
        road_slope = road_reference_slopes[w]
        bend = abs(paving_slope - road_slope)
        assert bend < 0.03, (
            'abrupt rear paving/road slope',
            w,
            bend,
            paving_slope,
            road_slope,
        )
        rear_bends.append(bend)
    # Existing upper frame, side voids and courtyard opening remain.
    for w in (-6.6, 6.6):
        assert ray(ts, point(w, 15, 20), -up, 19) is None, ('court side filled', w)
    assert ray(ts, point(0, 15, 20), -up, 9.5) is None, 'rear court capped'
    return dict(
        passed=True,
        borderJointPhaseError=border_course_alignment(objects),
        parkingJointPhaseError=parking_joint_alignment(objects),
        grassMinClearance=min(grass_clearances),
        grassMaxClearance=max(grass_clearances),
        probes=rows,
        apronMinClearance=min(clearances),
        apronMaxClearance=max(clearances),
        canopyGaps=True,
        rearDoor=True,
        passageClear=True,
        northeastSite=check_northeast_site(ts, roads, ground, tol),
        parkingRoadMaxStep=max(abs(v) for v in joins),
        outerEdgeMaxStep=max(edge_steps),
        rearParkingRoadMaxStep=max(abs(v) for v in rear_joins),
        parkingAccessMaxSlopeBreak=max(seam_breaks),
        wallSideMaxCrossfall=max(wall_slopes),
        wallFootTrim=True,
        rearRoadMaxSlopeBreak=max(rear_bends),
        rearTransitionMaxSlopeBreak=max(transition_bends),
    )


def root_name(o):
    while o.parent:
        o = o.parent
    return re.sub(r'\.\d+$', '', o.name)


report = {}
bpy.ops.wm.open_mainfile(filepath=str(P / 'blender/gxu-campus.blend'))
road_reference_slopes = {}
source_roads = trees([bpy.data.objects['roads']])
for w in (-20, -18, -17, 17, 19, 20, 23, 25, 27):
    hit = ray(source_roads, point(w, -0.22, 12), -up, 15)
    assert hit, ('missing source rear road reference', w)
    road_reference_slopes[w] = hit[2].dot(n) / hit[2].z
report['source'] = check(
    [o for o in bpy.context.scene.objects if o.get('featureId') == b['id']],
    trees(
        [o for o in bpy.context.scene.objects if o.get('layer') in ('terrain', 'roads')]
    ),
    0.008,
    trees([bpy.data.objects['roads']]),
)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(P / 'public/models/base.glb'))
bpy.context.view_layer.update()


def exported_road(o):
    name = root_name(o)
    return name == 'roads' or name.startswith('paving-') and name.endswith('-export')


road_objects = [o for o in bpy.context.scene.objects if exported_road(o)]
ground = trees(
    road_objects + [o for o in bpy.context.scene.objects if root_name(o) == 'terrain']
)
roads = trees(road_objects)
report['base'] = check(
    [o for o in bpy.context.scene.objects if root_name(o) == b['chunk']],
    ground,
    0.05,
    roads,
)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(P / f'public/models/{b["chunk"]}.glb'))
bpy.context.view_layer.update()
report['near'] = check(list(bpy.context.scene.objects), ground, 0.02, roads)
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(
    'Source/base/near: stair treads, apron grounding, door, lattice gaps and courtyard probes passed'
)
