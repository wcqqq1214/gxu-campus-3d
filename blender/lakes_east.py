"""Reviewed east-campus water and local ground. XY metres east/north.

The lake IDs and water datums come from surfaces.json. Image controls refer to
the Esri north-up frames and GXU campus guide archived in work/lake-review.
Only horizontal extents were observable. Freeboard and blends are model ties.
"""

import hashlib
import json
import math

from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt

from geometry import Mesh
from shore_geometry import bounds, nearest, overlaps
from site_geometry import inside, mesh_triangles, ring_distance

YUEYA = 'way/535275551'
LVRONG = 'way/685589479'
BIYUN = 'way/760093710'
ZIJING = 'relation/11382821'
ISLAND_PATH = 'way/834160221'
# Indexed rings / bridge ends below are tied to this OSM snapshot.
REVISIONS = {
    YUEYA: '6d314eb03dd93efc6d8179645ffd4eeb9f21ab9ffc0b85bb4c619632296dd570',
    LVRONG: 'f3179be08e887bf0dd4f5f9347dab6d484aabe58ad84271d97b498814beb2e4a',
    BIYUN: 'fc7b4afcd358485571665fe3305306a54ca10273a0b9936d162585060f9787b0',
    ZIJING: 'd5c2a15e4bdddd78ba607c4eb38e7d65a1990c07505fc783e17506c91a1fdb0d',
    ISLAND_PATH: '4fa1559ba118ba4e08b4296675c32413ad113bfe9bb536d2af261ca083456371',
}

# Read the visible *water side* of the west bay, inside the vegetated margin.
# Esri frame (-25,194) top left, 3 pixels/m. Keep both OSM tie points.
BAY = [
    (u / 3 - 25, 194 - v / 3)
    for u, v in (
        (89, 455),
        (77, 442),
        (71, 430),
        (69, 418),
        (70, 408),
        (75, 394),
        (82, 382),
        (88, 373),
        (99, 362),
        (115, 353),
        (130, 347),
    )
]
# Low round planted end at the west landing, visible in both GXU and Esri.
# Frame (-10,394) top left, 3 pixels/m. Tree canopy is excluded.
LANDING = [
    (u / 3 - 10, 394 - v / 3)
    for u, v in (
        (215, 166),
        (220, 158),
        (228, 154),
        (238, 154),
        (246, 157),
        (252, 164),
        (254, 172),
        (251, 180),
        (245, 186),
        (235, 190),
        (225, 188),
        (218, 183),
        (215, 177),
    )
]


def _cdt(points, edges, faces, origin):
    # Local coordinates retain sub-millimetre edge precision in mathutils.
    x, y = origin
    xy = [Vector((p[0] - x, p[1] - y)) for p in points]
    verts, _, tris, sources, _, parents = delaunay_2d_cdt(
        xy, edges, faces, 1, 1e-6, True
    )
    positions = [
        tuple(points[ids[0]][:2]) if ids else (v.x + x, v.y + y)
        for v, ids in zip(verts, sources)
    ]
    return positions, tris, parents


def _water_patch(surface, outer, holes, material):
    points = []
    rings = []
    areas = []
    for ring in [outer, *holes]:
        area = (
            sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1]))
            / 2
        )
        areas.append(abs(area))
        if area < 0:
            ring = ring[::-1]
        start = len(points)
        points.extend(ring)
        rings.append(list(range(start, len(points))))
    xy, tris, parents = _cdt(points, [], rings, points[0])
    out = Mesh()
    level = surface['waterLevel']
    for tri, ids in zip(tris, parents):
        if ids == [0]:
            out.face([(*xy[i], level) for i in tri], material)
    area = sum(
        (b[0] - a[0]) * (c[1] - a[1]) / 2 - (b[1] - a[1]) * (c[0] - a[0]) / 2
        for f in out.f
        for a, b, c in [[out.v[i] for i in f]]
    )
    if not math.isclose(area, areas[0] - sum(areas[1:]), abs_tol=1e-4):
        raise ValueError(f'Incomplete east lake triangulation: {surface["id"]}')
    return out


def _face_ids(mesh, surface, water=False):
    # Uniquely identify the prepared feature inside the batched layer.
    ring = {tuple(p) for p in surface['vertices']}
    indices = {
        i
        for i, f in enumerate(mesh.f)
        if all(tuple(mesh.v[k][:2]) in ring for k in f)
        and (not water or all(mesh.v[k][2] == surface['waterLevel'] for k in f))
    }
    if len(indices) * 3 != len(surface['triangles']):
        raise ValueError(f'East lake faces changed for {surface["id"]}')
    return indices


def _splice(mesh, removed, replacement):
    # Mesh uses disjoint face corners. Keep all untouched positions, face UVs
    # and material IDs; compact only unused vertices before appending the patch.
    from bisect import bisect_left

    keep = [i for i in range(len(mesh.f)) if i not in removed]
    used = sorted({k for i in keep for k in mesh.f[i]})
    remap = {k: j for j, k in enumerate(used)}
    mesh.v = [mesh.v[k] for k in used]
    mesh.f = [tuple(remap[k] for k in mesh.f[i]) for i in keep]
    mesh.m = [mesh.m[i] for i in keep]
    mesh.face_uvs = {
        j: mesh.face_uvs[i] for j, i in enumerate(keep) if i in mesh.face_uvs
    }
    mesh.parts = [
        (name, bisect_left(used, a), bisect_left(used, b)) for name, a, b in mesh.parts
    ]
    mesh.extend(replacement)


def _plane(xy, tri):
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = tri
    x, y = xy[0] - ax, xy[1] - ay
    bx, by, cx, cy = bx - ax, by - ay, cx - ax, cy - ay
    det = bx * cy - by * cx
    return az + ((x * cy - y * cx) * (bz - az) + (bx * y - by * x) * (cz - az)) / det


def _grade(terrain, lines, margin, height):
    """Constrain the original terrain planes to shoreline and grade controls.

    Output inherits each source triangle's material. Faces outside the local
    selection stay intact. Every incident local triangle shares the same cuts.
    """
    x0, y0, x1, y1 = bounds([p for line in lines for p in line])
    area = (x0 - margin - 2, y0 - margin - 2, x1 + margin + 2, y1 + margin + 2)
    subset = Mesh()
    removed = set()
    for i, face in enumerate(terrain.f):
        verts = [terrain.v[k] for k in face]
        if overlaps(bounds(verts), area):
            subset.face(verts, terrain.m[i])
            removed.add(i)

    source = mesh_triangles(subset)
    points = list(subset.v)
    edges = []
    for line in lines:
        start = len(points)
        points.extend(line)
        edges.extend((j, j + 1) for j in range(start, len(points) - 1))
    # Sample the graded belts. Hard footprint and path boundaries are CDT edges.
    xs = range(math.floor(x0 - margin), math.ceil(x1 + margin) + 1, 2)
    ys = range(math.floor(y0 - margin), math.ceil(y1 + margin) + 1, 2)
    for row, y in enumerate(ys):
        for col, x in enumerate(xs):
            i = len(points)
            points.append((x, y))
            if col:
                edges.append((i - 1, i))
            if row:
                edges.append((i - len(xs), i))
    xy, tris, owners = _cdt(points, edges, [ids for ids, _ in source], (x0, y0))
    out = Mesh()
    for tri, owner in zip(tris, owners):
        if len(owner) != 1:
            raise ValueError('Overlapping east lake source terrain')
        ids, f = source[owner[0]]
        original = [subset.v[k] for k in ids]
        out.face(
            [(*xy[k], height(xy[k], _plane(xy[k], original))) for k in tri], subset.m[f]
        )
    _splice(terrain, removed, out)


def _island(terrain, ring, level, rise, extra_lines=(), east_tie=None):
    def height(xy, z):
        d = ring_distance(xy, ring)
        if inside(xy, ring):
            target = level + rise * min(1, d / 1.5)
        else:
            target = z + (level - z) * max(0, 1 - d / 1.5)
        if east_tie is not None:
            target = z + (target - z) * min(1, max(0, (east_tie - xy[0]) / 3))
        return target

    _grade(terrain, [ring + ring[:1], *extra_lines], 2, height)


def _west_access(roads, crest, material):
    # The imaged access meets the east edge of the existing lakeside path.
    # Insert its two ends into the same source edge so both surfaces quantize
    # to matching coordinates. Retain the original path triangle's plane.
    for face_id, face in enumerate(roads.f):
        a, b, c = (roads.v[k] for k in face[:3])
        if (
            math.dist(a[:2], (49.229293, 335.775330)) < 1e-4
            and math.dist(b[:2], (47.682760, 350.177002)) < 1e-4
        ):
            break
    else:
        raise ValueError('East lake west path edge needs a new tie')
    joint = []
    for y in (336.3, 339.2):
        t = (y - a[1]) / (b[1] - a[1])
        joint.append(tuple(a[i] + (b[i] - a[i]) * t for i in range(3)))
    i, j = len(roads.v), len(roads.v) + 1
    roads.v.extend(joint)
    roads.f[face_id] = (face[0], i, face[2])
    roads.f.extend([(i, j, face[2]), (j, face[1], face[2])])
    roads.m.extend([roads.m[face_id]] * 2)

    deck = [
        joint[0],
        (65.0, 336.1, crest + 0.035),
        (65.0, 339.0, crest + 0.035),
        joint[1],
    ]
    roads.face(deck, material)
    roads.face([(x, y, h - 0.14) for x, y, h in reversed(deck)], material)
    for a, b in zip(deck, deck[1:] + deck[:1]):
        roads.face(
            [(a[0], a[1], a[2] - 0.14), (b[0], b[1], b[2] - 0.14), b, a], material
        )


def _zijing_west_bank(terrain, surface):
    # A terrain facet clips the channel opposite the island. Trace the original
    # water edge and taper back to the old ground before the NW bridge landing.
    ring = surface['vertices'][:29]
    a, b = ring[1:3]
    start = tuple(p + 0.61 * (q - p) for p, q in zip(a, b))
    bank = [start, *ring[2:5]]
    length = sum(math.dist(p, q) for p, q in zip(bank, bank[1:]))
    level = surface['waterLevel']

    def height(xy, z):
        distance, along = nearest(bank, *xy)
        wet = inside(xy, ring)
        width = 9.0 if wet else 2.0
        fade = min(1.0, along / 4, (length - along) / 4, max(0.0, width - distance))
        cap = level + (-0.20 if wet else 0.35) * min(1.0, distance)
        return z + min(0.0, cap - z) * fade

    _grade(terrain, [bank], 9, height)


def apply_lakes(base, surfaces, C):
    """Apply to the existing ground, water and road batches after build_shores."""
    water, terrain, roads = (base[k] for k in ('water', 'terrain', 'roads'))
    if getattr(water, '_lakes_east_applied', False):
        return
    src = {s['id']: s for s in surfaces if s['id'] in REVISIONS}
    for key, expected in REVISIONS.items():
        data = json.dumps(src[key]['vertices'], separators=(',', ':')).encode()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError(f'East lake controls need review against {key}')

    old = _face_ids(water, src[YUEYA], True) | _face_ids(water, src[LVRONG], True)
    path_ids = _face_ids(roads, src[ISLAND_PATH])
    original = src[YUEYA]['vertices']
    bay = [original[10], *BAY, original[15]]
    outer = original[:10] + bay + original[16:]
    updated = _water_patch(src[YUEYA], outer, [], C['water'])
    updated.extend(
        _water_patch(src[LVRONG], src[LVRONG]['vertices'], [LANDING], C['water'])
    )
    bay_length = sum(math.dist(a, b) for a, b in zip(bay, bay[1:]))

    def bay_height(xy, z):
        d, along = nearest(bay, *xy)
        wet = inside(xy, outer)
        width = 3 if wet else 5
        weight = max(0, 1 - d / width) * min(1, along / 3, (bay_length - along) / 3)
        target = src[YUEYA]['waterLevel'] + (-1 if wet else 1) * min(0.25, d * 0.15)
        return z + weight * (target - z)

    _grade(terrain, [bay], 5, bay_height)

    # Existing two bridge spans end on the rectilinear island path at level+1.
    # Raise that same road to their datum, preserving its XY and face materials.
    path = src[ISLAND_PATH]['vertices']
    z = src[ZIJING]['waterLevel']
    _zijing_west_bank(terrain, src[ZIJING])
    _island(terrain, src[ZIJING]['vertices'][29:], z, 0.96, [path + path[:1]])
    for i in path_ids:
        for k in roads.f[i]:
            x, y, _ = roads.v[k]
            roads.v[k] = (x, y, z + 1)

    # Retain the mapped eastern neck. The grading tails out before the east road.
    peninsula = src[BIYUN]['vertices'][13:34] + [(524.5, -66), (524.5, -57)]
    _island(terrain, peninsula, src[BIYUN]['waterLevel'], 0.38, east_tie=524.5)

    z = src[LVRONG]['waterLevel']
    _island(terrain, LANDING, z, 0.34, [[(65.0, 336.1), (65.0, 339.0)]])
    _west_access(roads, z + 0.34, C['path'])

    _splice(water, old, updated)
    water._lakes_east_applied = True
