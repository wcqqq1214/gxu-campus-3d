"""East end of the mapped building. Four floors are visible at two independent stations."""

import math

from mathutils import Vector
from mathutils.geometry import tessellate_polygon

from geometry import Mesh

from .mesh_parts import pigment, remove_faces

CUT = 104.9
HEIGHT = 13.2


def split_ring(ring, east):
    pts = []
    for a, b in zip(ring, ring[1:]):
        inside = lambda p: (p[0] >= CUT) == east
        if inside(a):
            pts.append(list(a))
        if inside(a) != inside(b):
            t = (CUT - a[0]) / (b[0] - a[0])
            pts.append([CUT, a[1] + t * (b[1] - a[1])])
    return pts + [pts[0]]


def east_body(b):
    form = b['form']
    orig = next(p for p in form['parts'] if p['id'] == 'east-end')
    others = [p for p in form['parts'] if p is not orig]
    for east in (False, True):
        ring = split_ring(orig['polygons'][0][0], east)
        vs = [Vector((x, y, 0)) for x, y in ring[:-1]]
        idx = []
        for a, bx, c in tessellate_polygon([vs]):
            if (vs[bx] - vs[a]).cross(vs[c] - vs[a]).z < 0:
                bx, c = c, bx
            idx.extend((a, bx, c))
        edges = [
            (a, b)
            for a, b in zip(ring, ring[1:])
            if min(a[0], b[0]) < CUT - 0.01 and max(a[0], b[0]) > 90.01
        ]
        # Roof guard is directly visible on the east and north edges of the lower wing.
        others.append(
            {
                **orig,
                'id': 'team-b-east-tip' if east else orig['id'],
                'polygons': [[ring]],
                'triangles': [idx],
                'parapetEdges': [] if east else edges,
                'levels': 4 if east else orig['levels'],
                'height': HEIGHT if east else orig['height'],
            }
        )
    facades = []
    for fac in form['facades']:
        if fac['part'] != 'east-end':
            facades.append(fac)
            continue
        a, bp = fac['start'], fac['end']
        ts = [0.0, 1.0]
        if (a[0] - CUT) * (bp[0] - CUT) < 0:
            ts.insert(1, (CUT - a[0]) / (bp[0] - a[0]))
        for t, u in zip(ts, ts[1:]):
            point = lambda s: [p + (q - p) * s for p, q in zip(a, bp)]
            east = point((t + u) / 2)[0] > CUT
            f = {**fac, 'start': point(t), 'end': point(u)}
            if east:
                f.update(part='team-b-east-tip', height=HEIGHT, levels=4)
                if fac['edge'] in (7, 8):
                    f['rule'] = {**f['rule'], 'windows': False}
            facades.append(f)
    return {**b, 'form': {**form, 'facades': facades, 'parts': others}}


def refine_alumni(mesh, b, z, C, detail):
    facade = Mesh()
    screen = Mesh()
    windows = Mesh()
    rim = Mesh()
    part = next(p for p in b['form']['parts'] if p['id'] == 'team-b-east-tip')
    center = [p for p in part['polygons'][0][0][:-1] if p[0] > 118]
    ne = max(center, key=lambda p: p[1])
    se = min(center, key=lambda p: p[1])
    nw = max([p for p in part['polygons'][0][0] if p[0] < 105], key=lambda p: p[1])

    # Remove the two original full wall surfaces and any residual generic sill details.
    def covered(points, mat):
        x, y, h = zip(*points)
        if max(abs(i - CUT) for i in x) < 0.001 and max(h) - min(h) > 1:
            return True
        if max(h) - min(h) < 0.01 and max(x) - min(x) > 4 and max(y) - min(y) > 4:
            return False
        return (
            min(x) > 119.12
            and min(y) > se[1] - 0.55
            and max(y) < ne[1] + 0.55
            or min(x) >= CUT - 0.001
            and min(y) > ne[1] - 0.055
            and max(h) < z + HEIGHT + 0.12
        )

    remove_faces(mesh, covered)
    # The lower and upper roofs meet at one exposed step. Remove both coplanar
    # internal walls, then close only the visible difference between roof heights.
    sy = min(p[1] for p in part['polygons'][0][0] if p[0] < 105)
    ny = max(p[1] for p in part['polygons'][0][0] if p[0] < 105)
    facade.face(
        [
            (CUT, sy, z + HEIGHT),
            (CUT, ny, z + HEIGHT),
            (CUT, ny, z + 16.5),
            (CUT, sy, z + 16.5),
        ],
        C['Office gold'],
    )
    gold = C['Office gold']
    stone = C['Office cream']
    wood = pigment(C, 'painted casements', '664438')
    glass = C['Office opening']
    shade = C['Office deep']

    def wall(start, end, openings):
        a = Vector(start)
        b = Vector(end)
        t = (b - a).normalized()
        n = Vector((t.y, -t.x))
        L = (b - a).length

        def coord(u, d, h):
            q = a + t * u + n * d
            return (q.x, q.y, z + h)

        def panel(target, poly, d, mat):
            target.face([coord(u, d, h) for u, h in poly], mat)

        def rect(target, l, r, lo, hi, d, mat):
            panel(target, [(l, lo), (r, lo), (r, hi), (l, hi)], d, mat)

        def solid(target, l, r, lo, hi, d0, d1, mat):
            # Four sides plus exterior face, open only where bonded to masonry.
            rec = [(l, lo), (r, lo), (r, hi), (l, hi)]
            panel(target, rec, d1, mat)
            for p, q in zip(rec, rec[1:] + rec[:1]):
                target.face(
                    [
                        coord(*[p[0], d0, p[1]]),
                        coord(q[0], d0, q[1]),
                        coord(q[0], d1, q[1]),
                        coord(p[0], d1, p[1]),
                    ],
                    mat,
                )

        us = sorted({0, L, *[i for l, r, lo, hi, typ in openings for i in (l, r)]})
        hs = sorted(
            {-0.5, HEIGHT, *[i for l, r, lo, hi, typ in openings for i in (lo, hi)]}
        )
        for l, r in zip(us, us[1:]):
            for lo, hi in zip(hs, hs[1:]):
                if not any(
                    i <= (l + r) / 2 <= j and k <= (hi + lo) / 2 <= v
                    for i, j, k, v, _ in openings
                ):
                    rect(facade, l, r, lo, hi, 0, gold)
        for l, r, lo, hi, kind in openings:
            depth = -0.32 if kind == 'screen' else -0.235
            corners = [(l, lo), (r, lo), (r, hi), (l, hi)]
            for p, q in zip(corners, corners[1:] + corners[:1]):
                facade.face(
                    [
                        coord(p[0], 0, p[1]),
                        coord(q[0], 0, q[1]),
                        coord(q[0], depth, q[1]),
                        coord(p[0], depth, p[1]),
                    ],
                    gold,
                )
            rect(
                facade,
                l,
                r,
                lo,
                hi,
                depth - 0.043,
                shade if kind in ('door', 'screen', 'vent') else glass,
            )
            if kind == 'vent':
                continue
            if kind == 'door':
                solid(
                    facade,
                    l - 0.22,
                    r + 0.22,
                    hi + 0.035,
                    hi + 0.11,
                    -0.015,
                    0.64,
                    stone,
                )
                continue
            solid(facade, l - 0.085, r + 0.085, lo - 0.072, lo, 0, 0.135, stone)
            if kind == 'screen':
                # A square block with a round hole and visible internal reveal; back is recessed.
                cols = max(3, round((r - l) / (0.255 if detail else 0.41)))
                rows = max(3, round((hi - lo) / (0.255 if detail else 0.41)))
                du = (r - l) / cols
                dh = (hi - lo) / rows
                square = [
                    (1, 0),
                    (1, 1),
                    (0, 1),
                    (-1, 1),
                    (-1, 0),
                    (-1, -1),
                    (0, -1),
                    (1, -1),
                ]
                for col in range(cols):
                    for row in range(rows):
                        u = l + (col + 0.5) * du
                        h = lo + (row + 0.5) * dh

                        def ring(pts, d):
                            return [
                                coord(u + x * du / 2, d, h + y * dh / 2) for x, y in pts
                            ]

                        hole = [
                            (
                                0.69 * math.cos(i * math.pi / 4),
                                0.69 * math.sin(i * math.pi / 4),
                            )
                            for i in range(8)
                        ]
                        outer = ring(square, -0.12)
                        inner = ring(hole, -0.12)
                        back = ring(hole, -0.225)
                        for i in range(8):
                            j = (i + 1) % 8
                            screen.face([outer[i], outer[j], inner[j], inner[i]], stone)
                            screen.face(
                                [inner[i], inner[j], back[j], back[i]],
                                C['Office lintel'],
                            )
            else:
                for u in (l + 0.032, r - 0.032):
                    solid(windows, u - 0.032, u + 0.032, lo, hi, depth, -0.08, wood)
                solid(
                    windows,
                    l + 0.065,
                    r - 0.065,
                    lo + 0.61 * (hi - lo),
                    lo + 0.61 * (hi - lo) + 0.065,
                    depth,
                    -0.075,
                    wood,
                )
                if detail:
                    # Side-hinged leaf projecting out of the opening in the 243-degree close-up.
                    hinge = l + 0.065
                    edge = hinge + (r - l) * 0.32
                    for h in (lo + 0.05, lo + 0.62 * (hi - lo), hi - 0.06):
                        windows.line(
                            coord(hinge, -0.075, h),
                            coord(edge, 0.34, h),
                            0.032,
                            wood,
                            4,
                        )
                    windows.line(
                        coord(edge, 0.34, lo + 0.05),
                        coord(edge, 0.34, hi - 0.06),
                        0.034,
                        wood,
                        4,
                    )

        # Continuous stone plinth moulding, interrupted at the entrance door.
        spans = [(0, L)]
        for l, r, lo, hi, kind in openings:
            if kind == 'door':
                spans = [(0, l), (r, L)]
        for l, r in spans:
            solid(facade, l, r, 0.69, 0.78, 0, 0.078, stone)
        solid(rim, 0, L, HEIGHT - 0.10, HEIGHT + 0.11, -0.12, 0.32, stone)
        for h in (HEIGHT + 0.54, HEIGHT + 0.83):
            rim.line(
                coord(0.035, -0.07, h),
                coord(L - 0.035, -0.07, h),
                0.024,
                C['Office iron'],
                6,
            )
        count = math.ceil(L / (0.74 if detail else 1.45))
        for i in range(count + 1):
            u = 0.035 + (L - 0.07) * i / count
            rim.line(
                coord(u, -0.07, HEIGHT + 0.1),
                coord(u, -0.07, HEIGHT + 0.83),
                0.021,
                C['Office iron'],
                6,
            )
        return coord

    # Local axis follows the wall with outward normal on the right.
    cu = -612.40 - se[1]
    east = [(cu - 0.75, cu + 0.75, 0.0, 2.74, 'door')]
    east += [
        (cu - 0.63, cu + 0.63, lo, hi, 'screen')
        for lo, hi in [(3.94, 6.04), (7.18, 9.33), (10.29, 12.48)]
    ]
    wall(se, ne, east)
    north = [
        (1.58, 3.07, lo, hi, 'screen')
        for lo, hi in [(2.64, 3.78), (5.72, 7.16), (8.84, 10.16)]
    ]
    for u in (5.12, 8.28, 11.10, 13.28):
        for lo in (0.82, 4.03, 7.18, 10.39):
            north.append((u - 0.52, u + 0.52, lo, lo + 1.90, 'casement'))
            if lo > 1:
                north.append((u - 0.085, u + 0.085, lo - 0.34, lo - 0.21, 'vent'))
    to_world = wall(ne, nw, north)
    for u in (1.50, 3.14):
        rim.line(
            to_world(u, 0.072, 0.06), to_world(u, 0.072, HEIGHT - 0.13), 0.05, stone, 8
        )
    mesh.add_part('西6A｜四层端墙、深窗洞及挑檐', facade)
    mesh.add_part('西6A｜透空混凝土花格', screen)
    mesh.add_part('西6A｜侧悬木窗扇与石窗台', windows)
    mesh.add_part('西6A｜线脚、雨水管与屋顶栏杆', rim)
    return mesh
