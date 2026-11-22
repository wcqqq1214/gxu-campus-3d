"""Seat the two photographed south entrance forecourts on their existing stair feet."""

from bisect import bisect_right
from copy import copy

from mathutils.bvhtree import BVHTree

from geometry import Mesh
from materials_north_road import split
from site_geometry import mesh_triangles

# Actual lower-flight geometry in chemical_college and mechanical_college.
# Each tuple gives the node, far building mesh, stair centre, toe Y, width,
# approximate foot Z (used only as a ray origin), and depth of solid support.
ENTRIES = (
    (
        'site-terrain-west-chemistry-apron',
        'chunk-n2-n3',
        -516.8,
        -1045.56,
        15.3,
        3.4,
        6.6,
    ),
    (
        'site-terrain-west-mechanical-apron',
        'chunk-n1-n3',
        -268.35,
        -1029.105,
        11.2,
        1.74,
        3.8,
    ),
)
BED = 0.035
SLAB = 0.075  # Model depth seats the edge and soffit below the graded soil.
SHOULDER = 1.8


def clamp(x):
    return max(0.0, min(1.0, x))


def local_faces(mesh, box):
    """Filter by bounds, including big triangles that contain the whole patch."""
    xmin, ymin, xmax, ymax = box
    for i, f in enumerate(mesh.f):
        p = [mesh.v[k] for k in f]
        if (
            max(v[0] for v in p) >= xmin
            and min(v[0] for v in p) <= xmax
            and max(v[1] for v in p) >= ymin
            and min(v[1] for v in p) <= ymax
        ):
            yield i, p


def sample(mesh):
    return BVHTree.FromPolygons(
        mesh.v, [tri for tri, _ in mesh_triangles(mesh)], all_triangles=True
    )


def submesh(mesh, box):
    local = Mesh()
    for i, pts in local_faces(mesh, box):
        local.face(pts, mesh.m[i], mesh.face_uvs.get(i))
    return local


def hit_z(tree, x, y, ceiling):
    point = tree.ray_cast((x, y, ceiling), (0, 0, -1), 30)[0]
    return None if point is None else point.z


def rebuild_bed(soil, box, xs, edge, toe, back, grade):
    selected = list(local_faces(soil, box))
    local = Mesh()
    for i, pts in selected:
        local.face(pts, soil.m[i], soil.face_uvs.get(i))
    faces = {}
    for tri, i in mesh_triangles(local):
        uv = local.face_uvs.get(i)
        indices = local.f[i]
        uv_at = dict(zip(indices, uv)) if uv else {}
        pts = [(*local.v[k], *uv_at.get(k, ())) for k in tri]
        pieces = [pts]
        for x in xs:
            pieces = [q for part in pieces for q in split(part, lambda v: v[0] - x)]
        for cut in (
            lambda v: v[1] - edge(v[0])[0] + 1.25,
            lambda v: v[1] - edge(v[0])[0],
            lambda v: v[1] - toe,
            lambda v: v[1] - toe - 0.12,
            lambda v: v[1] - back,
            lambda v: v[1] - back - SHOULDER,
        ):
            pieces = [q for part in pieces for q in split(part, cut)]
        faces.setdefault(selected[i][0], []).extend(pieces)
    result = copy(soil)
    result.v = soil.v.copy()
    result.f, result.m, result.face_uvs = [], [], {}
    for i, (f, mat) in enumerate(zip(soil.f, soil.m)):
        if i not in faces:
            if i in soil.face_uvs:
                result.face_uvs[len(result.f)] = soil.face_uvs[i]
            result.f.append(f)
            result.m.append(mat)
            continue
        for poly in faces[i]:
            result.face(
                [grade(*q[:3]) for q in poly],
                mat,
                [q[3:] for q in poly] if i in soil.face_uvs else None,
            )
    return result


def build_entry(base, colors, node, chunk, cx, toe, width, datum, depth):
    left, right = cx - width / 2, cx + width / 2
    back = toe + depth
    box = (left - SHOULDER, toe - 13, right + SHOULDER, back + SHOULDER)
    ground_road = submesh(base['roads'], box)
    road = sample(ground_road)
    stairs = sample(submesh(base[chunk], box))
    first = hit_z(stairs, cx, toe + 0.14, datum + 0.9)
    second = hit_z(stairs, cx, toe + 0.50, datum + 0.9)
    if first is None or second is None or not 0.13 < second - first < 0.21:
        raise ValueError(f'{node}: lower flight does not match the registered entrance')
    foot = 2 * first - second

    def road_edge(x):
        # Walk out from the bottom tread to the first actual road facet. This
        # includes the existing kerb where present. Keep the carriageway intact.
        for i in range(1, 48):
            lo = toe - i * 0.25
            if hit_z(road, x, lo, foot + 4) is not None:
                hi = lo + 0.25
                for _ in range(19):
                    mid = (lo + hi) / 2
                    if hit_z(road, x, mid, foot + 4) is None:
                        hi = mid
                    else:
                        lo = mid
                return lo, hit_z(road, x, lo - 0.001, foot + 4)
        raise ValueError(f'{node}: missing lane edge at x={x}')

    # Include every original road-edge corner along the entrance. Interior
    # triangulation vertices do not need a station on this narrow forecourt.
    xx = {left, cx, right}
    for x, y, _ in ground_road.v:
        if left < x < right and toe - 12 < y < toe:
            yy, _ = road_edge(x)
            if abs(y - yy) < 0.025:
                xx.add(round(x, 5))
    xs = sorted(xx)
    sections = [road_edge(x) for x in xs]

    def edge(x):
        i = max(0, min(len(xs) - 2, bisect_right(xs, x) - 1))
        u = clamp((x - xs[i]) / (xs[i + 1] - xs[i]))
        return tuple(a + u * (b - a) for a, b in zip(sections[i], sections[i + 1]))

    def finish(x, y):
        ey, ez = edge(x)
        return ez + (foot - ez) * clamp((y - ey) / (toe - ey))

    def grade(x, y, z):
        ey, _ = edge(x)
        weight = clamp((x - box[0]) / SHOULDER) * clamp((box[2] - x) / SHOULDER)
        weight *= clamp((y - ey + 1.25) / 1.25) * clamp((box[3] - y) / SHOULDER)
        target = finish(x, y) - BED + (BED + 0.006) * clamp((y - toe) / 0.12)
        return x, y, z + (target - z) * weight

    apron = Mesh()

    def section(x):
        y, z = edge(x)
        return [(x, y, z), (x, toe, foot)]

    for a, b in zip(xs, xs[1:]):
        road_a, toe_a = section(a)
        road_b, toe_b = section(b)
        for tri in ([road_a, road_b, toe_b], [road_a, toe_b, toe_a]):
            apron.face(tri, colors['bridgeConcrete'])
            apron.face(
                [(x, y, z - SLAB) for x, y, z in reversed(tri)],
                colors['bridgeConcrete'],
            )
    perimeter = [section(x)[0] for x in xs] + [section(x)[1] for x in reversed(xs)]
    for a, b in zip(perimeter, perimeter[1:] + perimeter[:1]):
        apron.face(
            [b, a, (*a[:2], a[2] - SLAB), (*b[:2], b[2] - SLAB)],
            colors['bridgeConcrete'],
        )
    base['terrain'] = rebuild_bed(
        base['terrain'], box, [box[0], *xs, box[2]], edge, toe, back, grade
    )
    base[node] = apron


def apply(base, colors):
    """Run after the three road groups have supplied their final lane geometry."""
    for entry in ENTRIES:
        if entry[0] not in base:
            build_entry(base, colors, *entry)
