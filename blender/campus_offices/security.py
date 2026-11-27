"""Clay hip and eave construction, louvred dormer and projected blue entrance fascia."""

import math

from mathutils import Vector

from geometry import Mesh

from .mesh_parts import pigment, remove_faces


def refine_security(mesh, z, C, detail):
    clay = pigment(C, 'fired clay', 'a87665')
    cap = pigment(C, 'tile crest', 'b58372')
    blue = pigment(C, 'turquoise fascia', '65a7ac')
    # Re-centre the old solid canopy slab and side returns over the observed entrance.
    # Both dated panoramas place its fascia north of the old canopy axis.
    moved = set()
    for face, mat in zip(mesh.f, mesh.m):
        pts = [mesh.v[i] for i in face]
        if mat in (C['Office cream'], C['Office stone']) and all(
            -319.22 < x < -317.0 and -784 < y < -778.7 and 2.78 < h - z < 3.53
            for x, y, h in pts
        ):
            moved.update(face)
    for i in moved:
        x, y, h = mesh.v[i]
        mesh.v[i] = (x, y + 0.48, h)
    # Rectify the photo-traced plaster backing under a level eave. Keep the
    # measured window centres. Its inclined white photographic trim is replaced below.
    begin, end = next((a, b) for name, a, b in mesh.parts if name == '实拍可见立面')
    for f, mat in zip(mesh.f, mesh.m):
        if mat == C['Office salmon'] and all(begin <= i < end for i in f):
            for i in f:
                x, y, h = mesh.v[i]
                if h > z + 5.95:
                    mesh.v[i] = (x, y, z + 6.46)

    def remove(points, mat):
        x, y, h = zip(*points)
        return (
            (mat == C['Office cream'] and min(x) > -319 and min(h) > z + 5.9)
            or (
                mat == C['Office lintel']
                and min(y) > -776.0
                and max(y) < -775.4
                and max(h) < z + 1.2
            )
            or mat == C['Office teal']
            or (
                min(x) > -325.1
                and max(x) < -321.7
                and min(h) > z + 9.15
                and mat in [C['Office ' + t] for t in ('deep', 'wood', 'tile')]
            )
            or (min(h) > z + 6.46 and max(h) < z + 6.63 and mat == C['Office tile'])
            or (
                min(h) > z + 0.15
                and max(h) < z + 0.82
                and min(x) < -355
                and max(x) > -320
                and mat == C['Office lintel']
            )
        )

    remove_faces(mesh, remove)
    mesh.m = [
        clay if m == C['red'] else blue if m == C['Office teal'] else m for m in mesh.m
    ]
    roof = Mesh()
    trim = Mesh()

    def pt(x, y, h):
        return Vector((x, y, z + h))

    a, b, c, d = [
        pt(x, y, 6.6)
        for x, y in [
            (-318.56, -775.61),
            (-318.58, -791.16),
            (-356.90, -791.12),
            (-356.88, -775.56),
        ]
    ]
    e, f = pt(-324, -783.38, 11.4), pt(-349.11, -783.35, 11.4)

    def rolled(start, end, r, segmented=False):
        # Separate tapered units butt together. Their stepped lips cast a shadow.
        n = max(1, round((end - start).length / 0.53)) if segmented and detail else 1
        direction = (end - start).normalized()
        u = Vector((-direction.y, direction.x, 0)).normalized()
        v = direction.cross(u)
        for j in range(n):
            centre0 = start.lerp(end, j / n)
            centre1 = start.lerp(end, (j + 1) / n)

            def sect(centre, scale):
                return [
                    centre
                    + scale
                    * r
                    * (math.cos(t * math.pi / 6) * u + math.sin(t * math.pi / 6) * v)
                    for t in range(7)
                ]

            p, q = sect(centre0, 0.83 if n > 1 else 1), sect(centre1, 1)
            for k in range(6):
                roof.face([p[k], p[k + 1], q[k + 1], q[k]], cap)
            roof.face(q, cap)
        roof.face((p if n == 1 else sect(start, 0.83))[::-1], cap)

    for start, end in ((a, e), (b, e), (c, f), (d, f), (e, f)):
        rolled(start, end, 0.125, True)
    for start, end in ((a, b), (b, c), (c, d), (d, a)):
        mid = (start + end) / 2
        span = end - start
        angle = math.atan2(span.y, span.x)
        trim.box(
            mid.x,
            mid.y,
            mid.z - 0.088,
            span.length,
            0.145,
            0.175,
            C['Office tile'],
            angle,
        )
        towards = Vector((-337.73, -783.36, mid.z)) - mid
        normal = towards - span.normalized() * towards.dot(span.normalized())
        normal.normalize()
        strip = mid + normal * 0.26
        trim.box(
            strip.x,
            strip.y,
            mid.z - 0.14,
            span.length - 0.16,
            0.41,
            0.075,
            C['Office cream'],
            angle,
        )
    if detail:
        # Actual relief: clay roll tiles run down each pitch to the projecting lip.
        # Clip to the hip boundary; end rows taper into the hip instead of crossing it.
        for low0, low1, high0, high1 in [(d, a, f, e), (c, b, f, e), (b, a, e, e)]:
            n = round((low1 - low0).length / 0.27)
            for j in range(1, n):
                p = low0.lerp(low1, j / n)
                if high0 == high1:
                    centre = (low0 + low1) / 2
                    amount = 1 - min(1, abs((j / n - 0.5) * 2))
                    q = p + (high0 - centre) * amount
                    if q.x < -321.8 and abs(q.y + 783.41) < 2.15:
                        # Stop where the dormer cuts the east pitch.
                        q = p.lerp(q, min(1, (-321.77 - p.x) / (q.x - p.x)))
                else:
                    xx = max(high0.x, min(high1.x, p.x))
                    proj = high0.lerp(high1, (xx - high0.x) / (high1.x - high0.x))
                    if p.x < high0.x:
                        proj = low0.lerp(high0, (p.x - low0.x) / (high0.x - low0.x))
                    if p.x > high1.x:
                        proj = low1.lerp(high1, (p.x - low1.x) / (high1.x - low1.x))
                    q = proj
                if (q - p).length > 0.22:
                    rolled(p, q, 0.041)
    # Face recessed behind pitched verge boards, with separate inclined louvre blades.
    x = -321.91
    y = -783.41
    floor = 9.25
    peak = 11.05
    half = 1.96

    def triangle(x, edges, top, bottom):
        return [pt(x, y - edges, bottom), pt(x, y + edges, bottom), pt(x, y, top)]

    outer = triangle(x + 0.14, half, peak, floor)
    inner = triangle(x + 0.14, half - 0.31, peak - 0.40, floor + 0.09)
    recess = triangle(x - 0.18, half - 0.31, peak - 0.40, floor + 0.09)
    back = triangle(x - 2.26, half, peak, floor)
    roof.face(recess, C['Office deep'])
    for k in range(3):
        j = (k + 1) % 3
        roof.face([outer[k], outer[j], inner[j], inner[k]], C['Office wood'])
        roof.face([inner[k], inner[j], recess[j], recess[k]], C['Office wood'])
        if k:
            roof.face([outer[j], outer[k], back[k], back[j]], clay)
            rolled(outer[k], outer[j], 0.076)
    for h in (9.49, 9.75, 10.01, 10.27, 10.53):
        width = 2 * (half - 0.31) * (peak - 0.40 - h) / (peak - 0.40 - floor - 0.09)
        if width < 0.22:
            continue
        # An inclined solid blade and its visible front lip.
        section = [
            (x - 0.14, h + 0.066),
            (x + 0.045, h - 0.02),
            (x + 0.045, h - 0.085),
            (x - 0.14, h + 0.001),
        ]
        ends = [
            [pt(px, y + side * width / 2, hh) for px, hh in section] for side in (-1, 1)
        ]
        for i in range(4):
            j = (i + 1) % 4
            roof.face(
                [ends[0][i], ends[0][j], ends[1][j], ends[1][i]], C['Office wood']
            )
        for side in ends:
            roof.face(side, C['Office wood'])
    # The two street stations resolve a tall enamel fascia, above the canopy slab.
    trim.box(-317.52, -781.02, z + 3.36, 0.15, 3.09, 1.13, blue)
    for h in (2.822, 3.892):
        trim.box(-317.419, -781.02, z + h, 0.06, 3.09, 0.056, C['Office cream'])
    for yy in (-782.541, -779.499):
        trim.box(-317.419, yy, z + 3.36, 0.06, 0.052, 1.025, C['Office cream'])
    for yy in (-782.50, -779.54):
        trim.line(
            pt(-318.77, yy, 3.39), pt(-317.59, yy, 3.73), 0.049, C['Office iron'], 6
        )
    # Profiled stone footing: the old continuous stripe crossed the base of the windows.
    # The street entry interrupts the short-end course.
    for x0, y0, x1, y1 in [
        (-356.50, -775.94, -318.94, -775.99),
        (-318.96, -790.78, -356.52, -790.74),
        (-318.94, -775.99, -318.95, -779.71),
        (-318.95, -783.29, -318.96, -790.78),
    ]:
        start = Vector((x0, y0))
        end = Vector((x1, y1))
        t = (end - start).normalized()
        normal = Vector((-t.y, t.x))
        profile = [
            (0, -0.05),
            (0.125, -0.05),
            (0.125, 0.30),
            (0.088, 0.35),
            (0.082, 0.53),
            (0.03, 0.58),
            (0.03, 1.05),
            (0.10, 1.079),
            (0.10, 1.145),
            (0, 1.175),
        ]
        mats = [
            'stone',
            'base',
            'stone',
            'stone',
            'stone',
            'ochre',
            'lintel',
            'lintel',
            'lintel',
        ]

        def corner(origin, section):
            depth, h = section
            offset = 0.245 + depth
            q = origin + normal * offset
            if origin.x > -320 and (origin.y > -776.1 or origin.y < -790.6):
                q += (-t if origin == start else t) * offset
            return pt(q.x, q.y, h)

        for a, b, mat in zip(profile, profile[1:], mats):
            trim.face(
                [corner(start, a), corner(end, a), corner(end, b), corner(start, b)],
                C['Office ' + mat],
            )
        for side in (start, end):
            if side.x < -320 or -790.6 < side.y < -776.1:
                trim.face([corner(side, p) for p in profile], C['Office stone'])
    mesh.add_part('保卫处｜卷瓦、斜脊与百叶老虎窗', roof)
    mesh.add_part('保卫处｜双层檐口及门厅边框', trim)
    return mesh
