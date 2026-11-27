"""Retain the locked court balconies, replace three host walls with recessed masonry."""

import bisect
import math

from geometry import Mesh

from .masonry import Wall


def discard(mesh, indices):
    """Preserve material, part and UV indices when cutting existing wall faces."""
    keep = [i for i in range(len(mesh.f)) if i not in indices]
    mesh.f = [mesh.f[i] for i in keep]
    mesh.m = [mesh.m[i] for i in keep]
    mesh.face_uvs = {
        j: mesh.face_uvs[i] for j, i in enumerate(keep) if i in mesh.face_uvs
    }
    used = sorted(set(j for f in mesh.f for j in f))
    remap = {j: i for i, j in enumerate(used)}
    mesh.f = [tuple(remap[j] for j in f) for f in mesh.f]
    mesh.v = [mesh.v[j] for j in used]
    mesh.parts = [
        (n, bisect.bisect_left(used, a), bisect.bisect_left(used, b))
        for n, a, b in mesh.parts
    ]


def remove_host_faces(mesh, walls):
    removed = set()
    for w in walls:
        match = []
        for i, face in enumerate(mesh.f):
            pts = [mesh.v[j] for j in face]
            if len(pts) != 4 or max(v[2] for v in pts) - min(v[2] for v in pts) < 6:
                continue
            local = [(x - w.a[0], y - w.a[1]) for x, y, _ in pts]
            if max(abs(x * w.n[0] + y * w.n[1]) for x, y in local) > 0.005:
                continue
            along = [x * w.u[0] + y * w.u[1] for x, y in local]
            if abs(min(along)) < 0.01 and abs(max(along) - w.length) < 0.01:
                match.append(i)
        if len(match) != 1:
            raise ValueError(('graduate host face', w.a, w.length, match))
        removed.update(match)
    discard(mesh, removed)


def low_front(w, detail):
    L = w.length
    spans = [(0.06, 7.26), (7.69, 12.40), (12.83, 17.0)]
    w.panel(0, L, -0.5, 0, 0, 'shell')
    for base, top, sill, heads in [
        (0, 3.68, 0.72, [2.15, 2.16, 2.17]),
        (3.68, 7.91, 4.28, [5.83, 5.87, 5.86]),
    ]:
        gaps = []
        for j, (a, b) in enumerate(spans):
            recessed = 2.10 if base and j == 0 else 0.34
            gaps.append(
                (
                    a,
                    b,
                    sill,
                    heads[j],
                    recessed,
                    'open' if base and j == 0 else 'shadowGlass',
                    4 if detail else 2,
                )
            )
        w.row(base, top, gaps, 'shell')
        for j, (a, b) in enumerate(spans):
            if base and j == 0:
                # Deep upper opening and its pale interior soffit, visible through the first bay.
                for f in (0.16, 0.39, 0.62, 0.87):
                    w.box(
                        a + (b - a) * f,
                        0.135,
                        (sill + heads[j]) / 2,
                        0.073,
                        0.15,
                        heads[j] - sill,
                        'alloy',
                    )
                for lo, hi in [(0.18, 0.37), (0.40, 0.57)]:
                    w.panel(
                        a + lo * (b - a),
                        a + hi * (b - a),
                        sill + 0.06,
                        heads[j] - 0.05,
                        0.20,
                        'green',
                    )
                w.box((a + b) / 2, 0.41, sill + 0.07, b - a, 0.78, 0.14, 'floor')
            else:
                count = max(1, round((b - a) / (0.21 if detail else 0.48)))
                for q in range(count):
                    u = a + (q + 0.5) * (b - a) / count
                    w.box(
                        u,
                        0.12,
                        (sill + heads[j]) / 2,
                        0.024 if detail else 0.035,
                        0.035,
                        heads[j] - sill,
                        'bar',
                    )
                w.box((a + b) / 2, 0.098, sill + 0.60, b - a, 0.044, 0.043, 'bar')


def south_wing(w, detail, radius):
    L = w.length
    # Four bays of recessed sashes and a braced bay sit between masonry piers.
    # The east end carries a full-height pale drum and slim blue stair glazing.
    w.panel(0, L - radius, -0.5, 0, 0, 'brick')
    bays = [
        (0.115 * L, 0.243 * L),
        (0.260 * L, 0.354 * L),
        (0.373 * L, 0.482 * L),
        (0.505 * L, 0.640 * L),
        (0.66 * L, 0.79 * L),
    ]
    for j in range(6):
        base = j * 3.3
        top = base + 3.3
        apertures = (
            [(0.015 * L, 0.062 * L, base + 1.08, base + 2.43, 0.24, 'oculus', 1)]
            if j
            else []
        )
        apertures += [(a, b, base + 0.20, top - 0.19, 1.20, 'open', 1) for a, b in bays]
        apertures.append(
            (0.811 * L, 0.844 * L, base + 0.04, top - 0.06, 0.19, 'green', 1)
        )
        w.row(base, top, apertures, 'brick', end=L - radius)
        for a, b in bays:
            w.panel(a, b, base + 0.20, base + 1.03, 1.20, 'brick')
            w.panel(a, b, base + 2.57, top - 0.19, 1.20, 'brick')
            w.panel(a, b, base + 1.03, base + 2.57, 1.20, 'shadowGlass')
            for f in (0.25, 0.50, 0.75) if detail else (0.50,):
                w.box(a + (b - a) * f, 1.15, base + 1.80, 0.06, 0.08, 1.54, 'alloy')
            w.box((a + b) / 2, 1.14, base + 2.17, b - a, 0.09, 0.06, 'alloy')
            if (a, b) != bays[-1]:
                w.box((a + b) / 2, 0.15, base + 0.55, b - a, 0.29, 0.70, 'shell')
                w.box((a + b) / 2, 0.13, base + 0.98, b - a, 0.105, 0.075, 'alloy')
                for f in (0.14, 0.50, 0.86):
                    w.box(
                        a + (b - a) * f, 0.13, base + 0.91, 0.045, 0.09, 0.12, 'alloy'
                    )
            w.box((a + b) / 2, 0.32, top - 0.31, b - a, 0.62, 0.26, 'reveal')
        a, b = bays[-1]
        for lo, hi in [(base + 0.24, top - 0.22), (top - 0.22, base + 0.24)]:
            w.member(a + 0.10, 0.11, lo, b - 0.10, 0.24, hi, 0.16, 'terracotta')


def east_end(w, detail, radius):
    L = w.length
    w.panel(radius, L, -0.5, 0, 0, 'brick')
    for j in range(6):
        base = j * 3.3
        w.row(
            base,
            base + 3.3,
            [(L * 0.45, L * 0.56, base + 0.86, base + 2.51, 0.25, 'shadowGlass', 1)],
            'brick',
            start=radius,
        )
        if j:
            w.box(
                (radius + L * 0.98) / 2,
                -0.23,
                base + 0.12,
                L * 0.98 - radius,
                0.46,
                0.27,
                'terracotta',
            )
    w.box(0.965 * L, -0.25, 10.0, 0.35, 0.47, 16.45, 'terracotta')


def round_corner(part, detail):
    from mathutils import Vector
    from mathutils.geometry import tessellate_polygon

    ring = part['polygons'][0][0][:-1]
    corner = ring[9]

    def unit(a, b):
        length = math.dist(a, b)
        return [(b[i] - a[i]) / length for i in range(2)]

    across = unit(ring[10], corner)
    back = unit(corner, ring[8])
    radius = 3.76
    start = [corner[i] - across[i] * radius for i in range(2)]
    arc = []
    for j in range(15 if detail else 8):
        angle = j * math.pi / (2 * (14 if detail else 7))
        arc.append(
            [
                start[i]
                + radius
                * (math.sin(angle) * across[i] + (1 - math.cos(angle)) * back[i])
                for i in range(2)
            ]
        )
    poly = ring[:9] + arc[::-1] + ring[10:]
    tri = tessellate_polygon([[Vector((x, y, 0)) for x, y in poly]])
    return (
        {
            **part,
            'polygons': [[poly + [poly[0]]]],
            'triangles': [[v for t in tri for v in t]],
        },
        arc,
        radius,
    )


def drum(shell, arc, z, paint):
    # Ground level is set behind the cantilever; a tiled quarter drum rises from its soffit.
    inner = (
        arc[0][0] + arc[-1][0] - 605.2384866971755,
        arc[0][1] + arc[-1][1] + 537.6533359999501,
    )
    for a, b in zip(arc, arc[1:]):
        shell.face(
            [(*a, z + 3.21), (*b, z + 3.21), (*b, z + 19.8), (*a, z + 19.8)],
            paint['brick'],
        )
        shell.face(
            [(*inner, z + 3.21), (*b, z + 3.21), (*a, z + 3.21)], paint['reveal']
        )
    for a, b in ((arc[0], inner), (inner, arc[-1])):
        shell.face(
            [(*a, z - 0.5), (*b, z - 0.5), (*b, z + 3.21), (*a, z + 3.21)],
            paint['reveal'],
        )
    shell.cylinder(
        arc[0][0] + 1.05, arc[-1][1] - 1.10, z + 1.6, 0.22, 3.20, paint['shell'], 12
    )


def roof_frames(shell, z, paint):
    # Southeast and southern stations both show the same orange triangular crown on the
    # high diagonal wing. The identical-looking truss farther behind the court is unlocated.
    from mathutils import Vector

    origin = Vector((577.9, -540.71, z + 19.8))
    along = Vector((0.699, 0.715, 0))
    back = Vector((-0.715, 0.699, 0))

    def point(u, d, h):
        return origin + along * u + back * d + Vector((0, 0, h))

    def beam(a, b):
        axis = (b - a).normalized()
        u = axis.cross(Vector((0, 0, 1)))
        if u.length < 0.02:
            u = Vector((1, 0, 0))
        u.normalize()
        v = axis.cross(u).normalized()
        rings = [
            [
                tuple(c + i * u * 0.095 + j * v * 0.105)
                for i, j in ((-1, -1), (1, -1), (1, 1), (-1, 1))
            ]
            for c in (a, b)
        ]
        for k in range(4):
            shell.face(
                [
                    rings[0][k],
                    rings[0][(k + 1) % 4],
                    rings[1][(k + 1) % 4],
                    rings[1][k],
                ],
                paint['terracotta'],
            )
        shell.face(rings[0][::-1], paint['terracotta'])
        shell.face(rings[1], paint['terracotta'])

    for d in (0.18, 3.7):
        # Two feet bear on the existing high roof. The outer half-truss cantilevers southwest.
        beam(point(0.18, d, 0), point(-2.75, d, 2.0))
        beam(point(-2.75, d, 2.0), point(-1.04, d, 3.76))
        beam(point(-1.04, d, 3.76), point(1.30, d, 0))
        beam(point(-2.75, d, 2.0), point(0.18, d, 2.0))
    for u, h in ((-2.75, 2.0), (-1.04, 3.76), (1.30, 0.12)):
        beam(point(u, 0.18, h), point(u, 3.70, h))


def graduate_school(b, datum, C, detail, ordinary, previous, paint):
    shell = Mesh()
    walls = []

    def revised(spec, z, colors, lod):
        form = spec['form']
        parts = []
        faces = []
        for p in form['parts']:
            if p['id'] == 'east-return':
                p, arc, radius = round_corner(p, lod)
                p = {
                    **p,
                    'height': 19.8,
                    'levels': 6,
                    'wallFinish': 'GXU six C brick',
                    'parapetEdges': [],
                }
                drum(shell, arc, z, paint)
                for a, bb in zip(arc, arc[1:]):
                    dx, dy = bb[0] - a[0], bb[1] - a[1]
                    length = math.hypot(dx, dy)
                    walls.append(
                        Wall(shell, a, bb, (dy / length, -dx / length), z, paint)
                    )
            if p['id'] == 'observed-gallery':
                p = {**p, 'height': 7.91}
                ring = p['polygons'][0][0]
                a, bb = ring[1:3]
                dx, dy = bb[0] - a[0], bb[1] - a[1]
                L = math.hypot(dx, dy)
                low = Wall(shell, a, bb, (dy / L, -dx / L), z, paint)
                walls.append(low)
                low_front(low, lod)
            parts.append(p)
        for f in form['facades']:
            if f['part'] == 'east-return':
                f = {**f, 'height': 19.8, 'levels': 6}
                if f['edge'] in (20, 21):
                    f = {**f, 'rule': {**f['rule'], 'windows': False}}
                    w = Wall(shell, f['end'], f['start'], f['normal'], z, paint)
                    if f['edge'] == 21:
                        south_wing(w, lod, radius)
                        walls.append(
                            Wall(shell, f['end'], arc[0], f['normal'], z, paint)
                        )
                    else:
                        east_end(w, lod, radius)
                        walls.append(
                            Wall(shell, arc[-1], f['start'], f['normal'], z, paint)
                        )
            faces.append(f)
        m = ordinary(
            {**spec, 'form': {**form, 'parts': parts, 'facades': faces}}, z, colors, lod
        )
        remove_host_faces(m, walls)
        return m

    m = previous(b, datum, C, detail, revised)
    # Remove the old raised graphic sheets and their strips only on the replaced low facade.
    ranges = [
        (a, b)
        for name, a, b in m.parts
        if name in ('实拍入口、屋面及阳台', '多角度屋体、窗框与门厅')
    ]
    removed = set()
    for i, f in enumerate(m.f):
        if not any(lo <= f[0] < hi for lo, hi in ranges):
            continue
        pts = [m.v[v] for v in f]
        along = [(x - 575.6) * (-0.718) + (y + 518.72) * 0.696 for x, y, _ in pts]
        if (
            min(along) > 5.84
            and max(along) <= 22.40
            and max(z for _, _, z in pts) <= datum + 7.55
        ):
            removed.add(i)
    if not removed:
        raise ValueError('old graduate facade not located')
    discard(m, removed)
    roof_frames(shell, datum, paint)
    m.add_part('C | 东翼凹廊、交叉撑及低翼凹窗', shell)
    return m
