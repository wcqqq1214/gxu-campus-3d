"""North-side stair at the east terrace of relation/11564999.

Two independent panorama rays locate the flight about 13.5 m outside the east
facade. W increases to the south; D increases towards the west in the existing
entry frame. Levels tie to the existing cross-landing; they are not survey data.
"""

import math
from functools import lru_cache

from geometry import Mesh

W0, W1 = -21.0, -9.0
D0, D1 = -20.0, -8.4
NOSE = -20.16
WALL_END = -19.75
THICKNESS = 0.38
TOE, HEAD = -17.0, -13.05
EAST, WEST = -14.47, -12.45
COUNT = 11
RISE = 0.15


def applies(entry):
    x, y = entry['center']
    return (
        entry['id'] == 'east-recessed-entry'
        and abs(x + 510.212) < 0.1
        and abs(y + 899.493) < 0.1
    )


def frame(entry, z):
    a = math.radians(entry['bearing'])
    ox, oy = entry['center']
    sn, cs = math.sin(a), math.cos(a)

    def point(w, d, h):
        return ox + cs * w - sn * d, oy - sn * w - cs * d, z + h

    def local(p):
        x, y = p[0] - ox, p[1] - oy
        return cs * x - sn * y, -sn * x - cs * y, p[2] - z

    return point, local


def subtract_patch(source, first, local):
    """Trim only old plaza/parking finishes, interpolating original UV seams."""
    result = Mesh()
    for index, (face, mat) in enumerate(zip(source.f, source.m)):
        pts = [source.v[i] for i in face]
        uvs = source.face_uvs.get(index)
        corners = [
            (*local(p)[:2], *p, *(uvs[j] if uvs else ())) for j, p in enumerate(pts)
        ]
        if index < first or (
            max(p[0] for p in corners) <= W0
            or min(p[0] for p in corners) >= W1
            or max(p[1] for p in corners) <= D0
            or min(p[1] for p in corners) >= D1
        ):
            result.face(pts, mat, uvs)
            continue
        for axis, edge, side in [(0, W0, 1), (0, W1, -1), (1, D0, 1), (1, D1, -1)]:
            inside = []
            outside = []
            for a, b in zip(corners, corners[1:] + corners[:1]):
                ha = (a[axis] - edge) * side
                hb = (b[axis] - edge) * side
                if ha >= -1e-9:
                    inside.append(a)
                if ha <= 1e-9:
                    outside.append(a)
                if ha * hb < 0 and abs(ha) > 1e-9 and abs(hb) > 1e-9:
                    t = ha / (ha - hb)
                    q = tuple(v + t * (e - v) for v, e in zip(a, b))
                    inside.append(q)
                    outside.append(q)
            if len(outside) >= 3 and any(
                (p[axis] - edge) * side < -1e-9 for p in outside
            ):
                result.face(
                    [p[2:5] for p in outside],
                    mat,
                    [p[5:] for p in outside] if uvs else None,
                )
            corners = inside
            if len(corners) < 3:
                break
    return result


def surfaces(entry, z, C):
    from entry_guardrails import guard

    config = entry['recessedStairEntry']
    terrace = config['baseHeight']
    # Use a short transition to the existing terrace instead of concentrating
    # the full discrepancy between its datum and the old parking at the toe.
    top = terrace + 0.36
    foot = top - COUNT * RISE
    point, local = frame(entry, z)
    patches = config['landscape']['groundPatches']
    verts = []
    faces = []
    for patch in patches:
        start = len(verts)
        verts.extend(patch['vertices'])
        ids = patch['triangles']
        faces.extend(
            tuple(start + j for j in ids[i : i + 3]) for i in range(0, len(ids), 3)
        )

    @lru_cache(maxsize=None)
    def old(w, d):
        for ia, ib, ic in faces:
            a, b, c = verts[ia], verts[ib], verts[ic]
            den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
            if abs(den) < 1e-12:
                continue
            u = ((b[1] - c[1]) * (w - c[0]) + (c[0] - b[0]) * (d - c[1])) / den
            v = ((c[1] - a[1]) * (w - c[0]) + (a[0] - c[0]) * (d - c[1])) / den
            if min(u, v, 1 - u - v) >= -1e-7:
                return u * a[2] + v * b[2] + (1 - u - v) * c[2]
        raise ValueError(f'Materials side stair outside prepared forecourt at {w}, {d}')

    mesh, bed = Mesh(), Mesh()
    step_run = (HEAD - TOE) / COUNT
    ws = sorted(
        {
            W0,
            NOSE,
            -19.6,
            -18.4,
            TOE,
            *[TOE + i * step_run for i in range(1, COUNT)],
            HEAD,
            -11.2,
            W1,
        }
    )
    ds = [D0, D0 + 0.24, WALL_END, -18.21, -17.5, -15.5, EAST, WEST, -10.0, D1]

    def relief(w, d, zone, step):
        old_z = old(w, d)
        if zone == 'lower' and w >= TOE and d >= WEST:
            rise = 0.30 * min(1, (w - TOE) / (HEAD - TOE))
            if d >= -10 and w < HEAD:
                from materials_east_passage import approach_height

                t = (d + 10) / (D1 + 10)
                return (foot + rise) * (1 - t) + approach_height(old, w, D1) * t
            return foot + rise
        if zone == 'stair':
            return foot + (step + 1) * RISE
        if zone == 'upper':
            # Level exit onto the cross landing, with a transition in the
            # unseen inside corner towards the original plaza.
            blend = min(
                1, (w - W0) / 1.4, (W1 - w) / (W1 + 11.2), (d - D0) / (EAST - D0)
            )
            if d >= EAST and w >= HEAD:
                blend = max(
                    blend,
                    min(1, (d - EAST) / (D1 - EAST)) * min(1, (W1 - w) / (W1 + 11.2)),
                )
            if w >= NOSE and d <= EAST:
                blend = min(1, (d - (D0 + 0.24)) / 1.55, (W1 - w) / (W1 + 11.2))
            level = top - (top - terrace) * max(0, (d - WEST) / (D1 - WEST))
            return old_z + (level - old_z) * max(0, blend)
        # The light-coloured foot walk runs west to the access alley.
        blend = min(1, (w - W0) / 2.6, (D1 - d) / (D1 + 10.0))
        if w <= TOE:
            blend = min(
                1,
                (w - W0) / (NOSE - W0),
                (D1 - d) / (D1 + 10.0),
                (d - (D0 + 0.24)) / 1.55,
            )
        return old_z + max(0, blend) * (foot - old_z)

    def top_face(points, material):
        q = [point(*p) for p in reversed(points)]
        for tri in [q[:3], [q[0], q[2], q[3]]]:
            uv = (
                [
                    ((local(q)[0] + 20.86) / 1.2, (local(q)[1] + 19.185) / 2.6)
                    for q in tri
                ]
                if material == 'path'
                else None
            )
            mesh.face(tri, C[material], uv)
            bed.face(tri, C['grass'])

    heights = {}
    for i, (a, b) in enumerate(zip(ws, ws[1:])):
        for j, (l, r) in enumerate(zip(ds, ds[1:])):
            w, d = (a + b) / 2, (l + r) / 2
            step = math.floor((w - TOE) / step_run)
            is_stair = TOE < w < HEAD and EAST < d < WEST
            zone = (
                'stair'
                if is_stair
                else 'upper'
                if (d < EAST and w > NOSE) or w > HEAD
                else 'lower'
            )
            material = 'stone' if zone in ('stair', 'upper') else 'path'
            corners = [(a, l), (b, l), (b, r), (a, r)]
            pts = [(x, y, relief(x, y, zone, step)) for x, y in corners]
            top_face(pts, material)
            heights[i, j] = pts

    def riser(edge, opposite, stone):
        a, b = edge
        c, d = opposite
        if max(abs(a[2] - c[2]), abs(b[2] - d[2])) < 0.0005:
            return
        # Orient the exposed face towards the lower adjacent finish.
        q = [point(*a), point(*b), point(*d), point(*c)]
        mesh.face(q, C['wallStone' if stone else 'stone'])

    for (i, j), p in heights.items():
        if (i + 1, j) in heights:
            n = heights[i + 1, j]
            riser(
                [p[1], p[2]],
                [n[0], n[3]],
                abs(ws[i + 1] - HEAD) < 1e-8 and ds[j] >= WEST,
            )
        if (i, j + 1) in heights:
            n = heights[i, j + 1]
            riser(
                [p[2], p[3]],
                [n[1], n[0]],
                abs(ds[j + 1] - EAST) < 1e-8 or abs(ds[j + 1] - WEST) < 1e-8,
            )
    # Contact at D1 is the existing raised cross-landing for w >= -16
    # and the existing parking surface farther north.
    for (i, j), p in heights.items():
        if j != len(ds) - 2:
            continue
        a, b = p[2], p[3]
        from materials_east_passage import approach_height

        edge = [
            (
                w,
                d,
                approach_height(old, w, d)
                if -16 <= w < -12.82
                else terrace
                if w >= -16
                else old(w, d),
            )
            for w, d, _ in (a, b)
        ]
        riser([a, b], edge, False)

    from materials_east_finishes import apply_finishes, grade_apron

    # Seal the surveyed finishes across the slim source parking/road seam.
    north = next(p for p in patches if p['id'] == 'north-parking')
    north_edge = sorted((d, w) for w, d in north['boundary'] if w < -21)

    def edge(d):
        for (da, wa), (db, wb) in zip(north_edge, north_edge[1:]):
            if da <= d <= db and db > da:
                return wa + (wb - wa) * (d - da) / (db - da)
        raise ValueError('Missing north parking edge')

    for da, db in zip(range(-20, -4), range(-19, -3)):
        # The old contact has a 3–4 cm open band. Underlap the lane by
        # 8 cm with a 4 cm fall; the original parking/road levels stay joined.
        a, b = edge(da), edge(db)
        ha, hb = old(a + 0.00001, da), old(b + 0.00001, db)
        ring = [
            (a, da, ha),
            (a - 0.09, da, ha - 0.04),
            (b - 0.09, db, hb - 0.04),
            (b, db, hb),
        ]
        mesh.face(
            [point(*v) for v in ring],
            C['path'],
            [((w + 20.86) / 1.2, (d + 19.185) / 2.6) for w, d, _ in ring],
        )
    apply_finishes(mesh, 0, point, frame(entry, z)[1], C)
    grade_apron(mesh, 0, point, frame(entry, z)[1])

    def box(w, d, h, width, depth, height, material):
        mesh.box(
            *point(w, d, h),
            width,
            depth,
            height,
            C[material],
            -math.radians(entry['bearing']),
        )

    from materials_east_passage import passage

    bed.passage_start = len(bed.f)
    passage(mesh, bed, point, old, box, C)
    for edge in (EAST + 0.045, WEST - 0.045):
        guard(
            mesh, point, box, C, TOE, edge, HEAD, edge, foot + RISE, top, glazed=False
        )
    # The low side faces north along the parking bays and turns south along
    # the flight. Both arms share their solid masonry corner and jointed cap.
    add_retaining_walls(mesh, point, C, foot, top)
    guard(
        mesh, point, box, C, NOSE + 0.19, WALL_END, NOSE + 0.19, EAST - 0.19, top, top
    )
    guard(mesh, point, box, C, NOSE + 0.19, EAST - 0.19, TOE, EAST - 0.19, top, top)
    guard(
        mesh,
        point,
        box,
        C,
        HEAD + 0.05,
        WEST,
        HEAD + 0.05,
        -10.0,
        top,
        relief(HEAD + 0.05, -10.0, 'upper', 0),
    )
    return mesh, bed


def add_retaining_walls(mesh, point, C, foot, top):
    from geometry import tile_material

    tile_material(
        C,
        'materialsRetainingStone',
        'materials-retaining-stone.jpg',
        (0.47, 0.42, 0.36),
    )

    def shell(ring, low, high, mat, surface=point):
        # Clockwise in local coordinates is counterclockwise in world XY.
        low_ring = [surface(w, d, low) for w, d in ring]
        high_ring = [surface(w, d, high) for w, d in ring]

        def area(poly):
            return sum(
                a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1])
            )

        if area(high_ring) < 0:
            high_ring.reverse()
            low_ring.reverse()
        mesh.face(high_ring, C[mat], [(p[0] / 2.4, p[1] / 1.32) for p in high_ring])
        mesh.face(low_ring[::-1], C[mat])
        u = 0
        for i, a in enumerate(low_ring):
            j = (i + 1) % len(ring)
            span = math.dist(a, low_ring[j]) / 2.4
            mesh.face(
                [a, low_ring[j], high_ring[j], high_ring[i]],
                C[mat],
                [
                    (u, 0),
                    (u + span, 0),
                    (u + span, (high - low) / 1.32),
                    (u, (high - low) / 1.32),
                ],
            )
            u += span

    # Keep the stone skin just outside its structural seat. The raised cap
    # overhangs the stone by 25 mm, except at the upper route where it ends.
    def corner(lip):
        n, e = NOSE - 0.014 - lip, EAST + 0.014 + lip
        return [
            (n, WALL_END - lip),
            (n, e),
            (HEAD, e),
            (HEAD, EAST - THICKNESS - lip),
            (NOSE + THICKNESS + lip, EAST - THICKNESS - lip),
            (NOSE + THICKNESS + lip, WALL_END - lip),
        ]

    shell(corner(0), foot - 0.10, top + 0.012, 'materialsRetainingStone')
    shell(corner(0.025), top + 0.012, top + 0.087, 'gateStone')

    def back(lip):
        return [
            (HEAD - 0.018 - lip, WEST),
            (HEAD - 0.018 - lip, -9.26 + lip),
            (HEAD + 0.32 + lip, -9.26 + lip),
            (HEAD + 0.32 + lip, WEST),
        ]

    # The existing landing falls gently westwards. Follow that fall on the cap.
    def sloping(w, d, h):
        return point(w, d, h - 0.36 * max(0, (d - WEST) / (D1 - WEST)))

    shell(back(0), foot - 0.12, top + 0.012, 'materialsRetainingStone', sloping)
    shell(back(0.025), top + 0.012, top + 0.087, 'gateStone', sloping)


def finish_materials_road(roads, entry, z, C, *, terrain=None):
    from materials_east_finishes import apply_finishes, grade_apron

    if applies(entry):
        from materials_east_finishes import cut_parking_seam

        cut_parking_seam(roads, entry, *frame(entry, z), C)
        apply_finishes(roads, 0, *frame(entry, z), C)
        grade_apron(roads, 0, *frame(entry, z))
        if terrain is not None:
            from materials_north_road import bed_north_road
            from materials_road_connections import tie_materials_lane

            bed_north_road(terrain, roads, *frame(entry, z))
            tie_materials_lane(terrain, roads, *frame(entry, z), C)


def replace_finishes(mesh, first, entry, z, C):
    _, local = frame(entry, z)
    result = subtract_patch(mesh, first, local)
    from materials_east_finishes import apply_finishes, grade_apron

    point, local = frame(entry, z)
    apply_finishes(result, first, point, local, C)
    grade_apron(result, first, point, local)
    from materials_east_passage import open_mouth

    result = open_mouth(result, point, local, first)
    detail, _ = surfaces(entry, z, C)
    result.extend(detail)
    return result


def seat_stair(terrain, entry, z, C):
    from paving_geometry import clear_paving_ground

    _, bed = surfaces(entry, z, C)
    xs, ys, _ = zip(*bed.v)
    from shore_geometry import bounds, overlaps

    area = [min(xs), min(ys), max(xs), max(ys)]
    exterior, local = Mesh(), Mesh()
    exterior.ground_uv_bounds = list(terrain.ground_uv_bounds)
    exterior.xy_uv_materials = set(terrain.xy_uv_materials)
    for i, face in enumerate(terrain.f):
        pts = [terrain.v[k] for k in face]
        target = local if overlaps(bounds(pts), area) else exterior
        target.face(pts, terrain.m[i], terrain.face_uvs.get(i))
    lowered, _ = clear_paving_ground(
        local, bed, dict(bounds=area, groundClearance=0.04, roundoffTolerance=0.001)
    )
    exterior.extend(lowered)
    from materials_east_finishes import grade_apron, seat_passage_floor

    point, local = frame(entry, z)
    grade_apron(exterior, 0, point, local, soil=True)
    seat_passage_floor(exterior, bed, point, local)
    return exterior
