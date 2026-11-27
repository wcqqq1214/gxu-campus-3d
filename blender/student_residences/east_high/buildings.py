"""Campus-coordinate exterior revisions for the Peijiayuan and Xingjian residences."""

import math

from generic_buildings import facade_segments, ordinary_building, wall_material
from geometry import Mesh
from humanities_facades import finish

from .sections import omit_replaced_rows


def _residence_facades(building):
    return [
        dict(edge, part='body', rule=dict(edge['rule']))
        for edge in facade_segments(building)
    ]


def _arm(edge):
    a, b = edge['start'], edge['end']
    length = math.dist(a, b)
    ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
    nx, ny = edge['normal']

    def box(m, u, d, z, w, depth, h, mat):
        m.box(
            a[0] + ux * u + nx * d,
            a[1] + uy * u + ny * d,
            z,
            w,
            depth,
            h,
            mat,
            math.atan2(uy, ux),
        )

    return length, box


def _crown_and_loggias(m, edge, z, h, levels, C):
    length, box = _arm(edge)
    count = max(2, round(length / 4.25))
    pitch, step = length / count, h / levels
    # The filled brick-red bays alternate with deep openings in a white frame.
    # Solid base wall is the back plane. Slabs and fronts project towards the camera.
    for k in range(1, levels):
        for j in range(count):
            if j % 3 == 1:
                continue
            u = (j + 0.5) * pitch
            box(m, u, 0.68, z + k * step + 0.08, pitch - 0.10, 1.36, 0.16, C['white'])
            box(m, u, 1.30, z + k * step + 0.65, pitch - 0.12, 0.08, 0.075, C['stone'])
            for dx in (-0.31, 0, 0.31):
                box(
                    m,
                    u + dx * pitch,
                    1.30,
                    z + k * step + 0.38,
                    0.04,
                    0.05,
                    0.50,
                    C['stone'],
                )
    for j in range(count + 1):
        u = 0.13 + (length - 0.26) * j / count
        box(m, u, 1.20, z + (step + h) / 2, 0.23, 0.30, h - step, C['white'])
        box(m, u, -0.30, z + h + 1.05, 0.22, 0.25, 2.10, C['white'])
    box(m, length / 2, -0.30, z + h + 2.03, length, 0.30, 0.23, C['white'])


def _peijia(b, z, C, detail, n):
    # Geometry and facade rules are copied before overriding any generic surface.
    form = dict(b['form'])
    b = dict(b, form=form)
    edges = _residence_facades(b)
    for e in edges:
        # Preserve the inherited treatment on faces not seen in ground views.
        ny = e['normal'][1]
        y = min(e['start'][1], e['end'][1])
        if (
            (n == 19 and ny > 0.98)
            or (n == 20 and y < -432)
            or (n == 22 and ny < -0.98 and y < -550)
        ):
            e['rule'] = {'balconies': False}
    if n == 20:
        # The 318° photograph shows a blank red east end on the south bar.
        for e in edges:
            if e['normal'][0] > 0.98 and min(e['start'][0], e['end'][0]) > 647:
                e['rule'] = {'windows': False}
    if n == 19:
        # Keep the original rear windows inside the new projecting open bays.
        for e in edges:
            if e['normal'][1] > 0.98 and math.dist(e['start'], e['end']) > 17:
                e['rule'].update(spacing=4.25)
    omit_replaced_rows(n, edges, round(form['levels']))
    if n == 19:
        edges[5]['rule']['skipWindowLevels'] = range(1, round(form['levels']))
    form['facades'] = edges
    m = ordinary_building(b, z, C, detail)
    terra = finish(C, 'dormPeijiaTerracotta', (0.50, 0.161, 0.083), 0.87)
    ivory = finish(C, 'dormPeijiaIvory', (0.76, 0.70, 0.60), 0.88)
    roof = finish(C, 'dormPeijiaWeatheredDeck', (0.25, 0.235, 0.21), 0.94)
    base_wall = wall_material(b, C)
    h = form['height']
    levels = round(form['levels'])

    def street_wall(y):
        return n == 19 or (n == 20 and y < -432)

    for i, f in enumerate(m.f):
        if m.m[i] == C['paleRoof']:
            m.m[i] = roof
        elif m.m[i] == base_wall:
            coords = [m.v[j] for j in f]
            y = sum(v[1] for v in coords) / len(coords)
            m.m[i] = terra if street_wall(y) else ivory
    trim = Mesh()
    for index, e in enumerate(edges):
        a, c = e['start'], e['end']
        nx, ny = e['normal']
        length, box = _arm(e)
        if n == 19 and ny > 0.98 and length > 17 and index != 5:
            _crown_and_loggias(trim, e, z, h, levels, C)
        elif n == 20 and (
            ny < -0.98 and length > 60 or nx > 0.98 and min(a[0], c[0]) > 647
        ):
            for floor in range(1, levels):
                for dz, tall in ((-0.10, 0.12), (0.18, 0.07)):
                    box(
                        trim,
                        length / 2,
                        0.035,
                        z + floor * h / levels + dz,
                        length,
                        0.075,
                        tall,
                        C['white'],
                    )
            # Paint the upper-storey wall itself: split its host quad at the colour break.
            for i, f in enumerate(list(m.f)):
                if len(f) != 4 or m.m[i] != terra:
                    continue
                coords = [m.v[j] for j in f]
                if (
                    math.dist(coords[0][:2], a) > 0.03
                    or math.dist(coords[1][:2], c) > 0.03
                ):
                    continue
                split = z + h - h / levels
                p, q = (*a, split), (*c, split)
                m.v[f[2]] = q
                m.v[f[3]] = p
                trim.face([p, q, coords[2], coords[3]], ivory)
        elif n == 22 and ny < -0.98 and min(a[1], c[1]) < -550 and length > 25:
            # Small openings sit between the taller original rows on the visible south wing.
            bays = int(length / 4)
            for level in range(2, levels):
                for j in range(1, bays):
                    box(
                        trim,
                        length * j / bays,
                        0.055,
                        z + (level + 0.60) * h / levels,
                        0.45,
                        0.12,
                        0.60,
                        C['glass'],
                    )
    if trim.v:
        m.add_part('培佳园实拍立面', trim)
    return m


# Along-roof fractions read independently on the imagery for each wing.
_ROOF_BAYS = {
    29: ((0.12, 0.37, 0.62, 0.87), (0.12, 0.39, 0.64, 0.86)),
    30: ((0.10, 0.34, 0.60, 0.86), (0.13, 0.40, 0.66, 0.87)),
    31: ((0.15, 0.38, 0.61, 0.84), (0.14, 0.39, 0.65, 0.88)),
    33: ((0.10, 0.24, 0.38, 0.62, 0.76, 0.89),),
    34: ((0.17, 0.43, 0.52, 0.80),),
    35: ((0.17, 0.43, 0.52, 0.80),),
}


def _notched_end(mesh, e, z, h, C, wall):
    a, c = e['start'], e['end']
    span, box = _arm(e)
    opening = min(2.45, span * 0.2)
    lo = (span - opening) / 2
    hi = lo + opening
    nx, ny = e['normal']

    def pt(u, depth, up):
        return (
            a[0] + (c[0] - a[0]) * u / span + nx * depth,
            a[1] + (c[1] - a[1]) * u / span + ny * depth,
            z + up,
        )

    for i, f in enumerate(mesh.f):
        if len(f) != 4 or mesh.m[i] != wall:
            continue
        vs = [mesh.v[j] for j in f]
        if math.dist(vs[0][:2], a) > 0.02 or math.dist(vs[1][:2], c) > 0.02:
            continue
        if vs[2][2] - vs[0][2] < h * 0.9:
            continue
        floor = vs[0][2] - z
        top = vs[2][2] - z
        mesh.v[f[1]] = pt(lo, 0, floor)
        mesh.v[f[2]] = pt(lo, 0, top)
        for first, last in [
            ((lo, 0), (lo, -0.96)),
            ((lo, -0.96), (hi, -0.96)),
            ((hi, -0.96), (hi, 0)),
            ((hi, 0), (span, 0)),
        ]:
            mesh.face(
                [pt(*first, floor), pt(*last, floor), pt(*last, top), pt(*first, top)],
                wall,
            )
        for level in range(1, 7):
            zz = z + h * level / 7
            box(mesh, span / 2, -0.43, zz + 0.08, opening, 0.99, 0.16, wall)
            for dy in (0.43, 0.70, 0.97):
                box(mesh, span / 2, 0.02, zz + dy, opening, 0.06, 0.055, C['stone'])
            box(mesh, span / 2, 0.02, zz + 0.58, 0.065, 0.07, 0.90, C['stone'])
        break


def _north_front(mesh, e, z, h, C, wall, n):
    length, box = _arm(e)
    bays = max(2, round(length / 3.65))
    pitch = length / bays
    eastward = e['start'][0] < e['end'][0]
    for k in range(bays):
        west_fraction = (k + 0.5) / bays if eastward else 1 - (k + 0.5) / bays
        if n == 29 and west_fraction > 0.46:
            continue
        if n == 30 and west_fraction > 0.67:
            continue
        if n == 35 and west_fraction < 0.55:
            continue
        if n == 34 and west_fraction < 0.69:
            continue
        if k % 3 == 1:
            continue
        u = (k + 0.5) * pitch
        for level in range(1, 7):
            zz = z + level * h / 7
            box(mesh, u, 0.56, zz + 0.08, pitch * 0.87, 1.12, 0.16, wall)
            box(mesh, u - pitch * 0.42, 0.55, zz + h / 14, 0.16, 1.10, h / 7, wall)
            box(mesh, u, 1.06, zz + 0.32, pitch * 0.82, 0.12, 0.45, wall)
            for up in (0.68, 0.90):
                box(mesh, u, 1.07, zz + up, pitch * 0.82, 0.065, 0.05, C['stone'])
            box(mesh, u, 1.07, zz + 0.70, 0.05, 0.06, 0.45, C['stone'])


def _roof_depth(edge, u, rings):
    a, c = edge['start'], edge['end']
    length = math.dist(a, c)
    x = a[0] + (c[0] - a[0]) * u / length
    y = a[1] + (c[1] - a[1]) * u / length
    rx, ry = (-v for v in edge['normal'])
    hits = []
    for ring in rings:
        for p, q in zip(ring, ring[1:]):
            sx, sy = q[0] - p[0], q[1] - p[1]
            cross = rx * sy - ry * sx
            if abs(cross) < 1e-8:
                continue
            dx, dy = p[0] - x, p[1] - y
            t = (dx * sy - dy * sx) / cross
            v = (dx * ry - dy * rx) / cross
            if t > 0.03 and 0 <= v <= 1:
                hits.append(t)
    return min(hits) if hits else 0


def _north(b, z, C, detail, n):
    # Both the seven-storey planning labels and the stacked south elevations
    # are legible. Metric heights are inferred, not a surveyed datum.
    levels = 7
    height = levels * 3.13
    form = dict(b['form'], height=height, levels=levels)
    host = dict(b, height=height, levels=levels, form=form)
    facades = _residence_facades(host)
    outer_count = len(b['polygons'][0][0]) - 1
    ends = []
    for idx, edge in enumerate(facades):
        if idx >= outer_count:
            continue
        xs = [edge['start'][0], edge['end'][0]]
        nx, ny = edge['normal']
        # East 33–35, the west end of 32 and the 30 west return have direct views.
        if (
            (n in (33, 34, 35) and nx > 0.94)
            or (n == 32 and nx < -0.94 and max(xs) < -535)
            or (n == 30 and nx < -0.94 and min(xs) < -175)
        ):
            if math.dist(edge['start'], edge['end']) > 7:
                edge['rule'] = {'windows': False}
                ends.append(edge)
        if n == 33 and ny > 0.94 and math.dist(edge['start'], edge['end']) > 60:
            edge['rule'] = {'windows': False}
    omit_replaced_rows(n, facades, levels)
    form['facades'] = facades
    if n in (34, 35):
        form['archetype'] = 'generic'
    mesh = ordinary_building(host, z, C, detail)
    original_wall = wall_material(host, C)
    wall = finish(C, 'dormXingjianOffWhite', (0.76, 0.735, 0.65), 0.86)
    deck = finish(C, 'dormXingjianDeck', (0.30, 0.275, 0.239), 0.94)
    mesh.m = [
        wall if mat == original_wall else deck if mat == C['paleRoof'] else mat
        for mat in mesh.m
    ]
    roof = Mesh()
    # These are the south faces of the individual roof bars, including the
    # bend on East 32. Small opposite courtyard connectors do not receive bays.
    edges = facades[:outer_count]
    long = [
        e
        for e in edges
        if abs(e['normal'][1]) > 0.92 and math.dist(e['start'], e['end']) > 50
    ]
    if n <= 31:
        selected = [
            max(
                (e for e in long if e['normal'][1] > 0),
                key=lambda e: math.dist(e['start'], e['end']),
            ),
            max(
                (e for e in long if e['normal'][1] < 0),
                key=lambda e: math.dist(e['start'], e['end']),
            ),
        ]
    elif n == 32:
        selected = sorted(
            (e for e in long if e['normal'][1] < 0),
            key=lambda e: min(e['start'][0], e['end'][0]),
        )
    else:
        selected = [
            max(
                (e for e in long if e['normal'][1] < 0),
                key=lambda e: math.dist(e['start'], e['end']),
            )
        ]
    for k, e in enumerate(selected):
        length, box = _arm(e)
        eastward = e['start'][0] < e['end'][0]
        if n == 32:
            fractions = (0.18, 0.28, 0.96) if k == 0 else (0.78,)
        else:
            fractions = _ROOF_BAYS[n][k]
        for f in fractions:
            u = length * (f if eastward else 1 - f)
            # Low transverse raised, light-coloured strips. Installation type
            # cannot be resolved; model the silhouette and top ribs only.
            w = 6.0 if n in (33, 34, 35) else 6.8
            capacity = min(
                _roof_depth(e, u + du, b['polygons'][0])
                for du in (-w * 0.5, 0, w * 0.5)
            )
            depth = min(8.1, capacity - 1.0)
            if depth <= 0:
                continue
            inset = min(6.3, capacity - 0.45 - depth / 2)
            box(roof, u, -inset, z + height + 0.32, w, depth, 0.64, deck)
            if detail:
                for rib in range(7):
                    box(
                        roof,
                        u,
                        -inset + (rib - 3) * depth / 6.75,
                        z + height + 0.69,
                        w,
                        0.22,
                        0.12,
                        wall,
                    )
            else:
                box(roof, u, -inset, z + height + 0.68, w, depth - 0.04, 0.08, wall)
    if n == 31:
        # The image looking north beside Beiyuan shows stacked open south bays
        # at the eastern ends. Limit the extension to the visible end section.
        edge = max(
            (e for e in selected if e['normal'][1] < 0),
            key=lambda e: max(e['start'][0], e['end'][0]),
        )
        span, box = _arm(edge)
        for j in range(2):
            u = (j + 0.5) * 3.8
            if edge['start'][0] < edge['end'][0]:
                u = span - u
            for level in range(1, levels):
                base = z + level * height / levels
                box(roof, u, 0.65, base + 0.09, 3.66, 1.30, 0.18, wall)
                box(
                    roof,
                    u + 1.75,
                    0.63,
                    base + height / levels / 2,
                    0.17,
                    1.26,
                    height / levels,
                    wall,
                )
                box(roof, u, 1.23, base + 0.40, 3.50, 0.15, 0.63, wall)
                for up in (0.82, 1.02):
                    box(roof, u, 1.23, base + up, 3.50, 0.06, 0.055, C['stone'])
                box(roof, u, 1.23, base + 0.85, 0.055, 0.055, 0.40, C['stone'])
    for edge in ends:
        _notched_end(mesh, edge, z, height, C, wall)
    for e in long:
        length, box = _arm(e)
        ny = e['normal'][1]
        if (n in (29, 30, 32) and ny < -0.95) or (n in (34, 35) and ny > 0.95):
            _north_front(roof, e, z, height, C, wall, n)
        if n == 33 and ny > 0.95:
            # North street elevation alternates wide horizontal glazing with solid piers.
            count = max(2, round(length / 10))
            for k in range(count):
                u = (k + 0.5) * length / count
                for level in range(7):
                    if level and k in (5, 6):
                        continue  # These two bays use the measured four-opening section.
                    zz = z + (level + 0.56) * height / 7
                    w = length / count * (0.74 if k % 3 != 0 else 0.40)
                    box(roof, u, 0.055, zz, w, 0.12, 1.34, C['glass'])
                    if detail:
                        for j in range(1, 4):
                            box(
                                roof,
                                u + (j / 4 - 0.5) * w,
                                0.126,
                                zz,
                                0.055,
                                0.035,
                                1.34,
                                wall,
                            )
        if n in (29, 30, 32, 33) and ny < -0.95:
            # Short open crown spans on the portions visible above the trees.
            positions = {29: [0.24], 30: [0.23], 32: [0.32, 0.68], 33: [0.30]}[n]
            for f in positions:
                u = length * (f if e['start'][0] < e['end'][0] else 1 - f)
                for dx in (-3.4, 3.4):
                    box(roof, u + dx, -0.45, z + height + 1.03, 0.26, 0.32, 2.06, wall)
                box(roof, u, -0.45, z + height + 1.99, 7.06, 0.33, 0.22, wall)
    if n == 35:
        e = selected[0]
        length, box = _arm(e)
        box(
            roof,
            length * (0.29 if e['start'][0] > e['end'][0] else 0.71),
            -6.5,
            z + height + 0.12,
            8.5,
            9.6,
            0.24,
            finish(C, 'dormXingjianBlueGrey', (0.25, 0.32, 0.37), 0.81),
        )
    mesh.add_part('实景分段屋面', roof)
    return mesh


def _east27(b, z, C, detail, mesh):
    from east27_dining import hall_frame

    ox, oy, angle = hall_frame(b)
    co, si = math.cos(angle), math.sin(angle)
    h = b['height']
    dark = finish(C, 'dormEast27RoofStrip', (0.113, 0.125, 0.126), 0.72, 0.14)

    def local(x, y):
        return (x - ox) * co + (y - oy) * si, -(x - ox) * si + (y - oy) * co

    if detail:
        # Select roof collector faces by both material and elevation. The shared
        # finish part also contains the original dining mesh below this cutoff.
        for i, f in enumerate(mesh.f):
            if mesh.m[i] != C['east27Collector']:
                continue
            vs = [mesh.v[k] for k in f]
            if min(v[2] for v in vs) < z + h:
                continue
            y = sum(local(*v[:2])[1] for v in vs) / len(vs)
            mid = min((-4.55, 38.0), key=lambda v: abs(y - v))
            if round((y - mid) / 2.72) % 2 == 0:
                mesh.m[i] = dark
    else:
        end = local(*b['polygons'][0][0][1])[0]
        roof = Mesh()

        def block(x, y, level, w, d, t, mat):
            roof.box(
                ox + x * co - y * si,
                oy + x * si + y * co,
                z + h + level,
                w,
                d,
                t,
                mat,
                angle,
            )

        for mid in (-4.55, 38.0):
            block(-31, mid, 0.137, 126.9, 20.2, 0.025, C['east27RoofDeck'])
            for start in (-94.8, -81.05, end - 29.1, end - 15.35):
                block(
                    start + 6.425, mid, 0.32, 12.68, 18.86, 0.24, C['east27Collector']
                )
                for j in (-2, 0, 2):
                    block(start + 6.425, mid + j * 2.72, 0.455, 12.68, 2.52, 0.03, dark)
        mesh.add_part('住宿双翼屋面分区（远景）', roof)
    return mesh


def residence(b, z, C, detail, baseline, n):
    if n == 27:
        return _east27(b, z, C, detail, baseline)
    if n >= 29:
        return _north(b, z, C, detail, n)
    if n != 25:
        return _peijia(b, z, C, detail, n)
    # The opposite courtyard views and the 6F planning label agree. Reuse
    # the dedicated street-side generator at its corrected storey count.
    b = dict(b, levels=6, height=19.8, form=dict(b['form'], levels=6, height=19.8))
    baseline = ordinary_building(b, z, C, detail)
    roof = Mesh()
    for e in facade_segments(b):
        length, box = _arm(e)
        if e['normal'][1] < 0.98 or length < 20:
            continue
        count = max(2, round(length / 7.8))
        pitch = length / count
        for k in range(count):
            u = (k + 0.5) * pitch
            for level in (3, 4, 5):
                zz = z + 3.3 * level
                w = pitch * 0.82
                box(roof, u, 0.73, zz + 0.09, w, 1.46, 0.18, C['eastNeighbourWhite'])
                for side in (-1, 1):
                    box(
                        roof,
                        u + side * (w - 0.18) / 2,
                        0.72,
                        zz + 1.65,
                        0.18,
                        1.44,
                        3.3,
                        C['eastNeighbourWhite'],
                    )
                box(
                    roof,
                    u,
                    1.39,
                    zz + 0.26,
                    w - 0.36,
                    0.12,
                    0.25,
                    C['eastNeighbourWhite'],
                )
                for h in (0.55, 0.78, 1.0):
                    box(roof, u, 1.40, zz + h, w - 0.36, 0.06, 0.045, C['stone'])
                box(roof, u, 1.40, zz + 0.70, 0.055, 0.06, 0.64, C['stone'])
            box(
                roof,
                u,
                0.72,
                z + 19.8 + 0.08,
                pitch * 0.82,
                1.44,
                0.16,
                C['eastNeighbourWhite'],
            )
    e = max(
        (e for e in facade_segments(b) if e['normal'][1] < -0.95),
        key=lambda e: math.dist(e['start'], e['end']),
    )
    length, box = _arm(e)
    deck = finish(C, 'dormPeijiaWeatheredDeck', (0.25, 0.235, 0.21), 0.94)
    u = length * (0.42 if e['start'][0] < e['end'][0] else 0.58)
    box(roof, u, -4.2, z + b['height'] + 0.35, length * 0.59, 4.1, 0.70, deck)
    if detail:
        for j in range(16):
            box(
                roof,
                u + (j - 7.5) * length * 0.59 / 16,
                -4.2,
                z + b['height'] + 0.74,
                0.11,
                4.1,
                0.08,
                C['stone'],
            )
    baseline.add_part('东25北面三层阳台及南缘长条屋面', roof)
    return baseline
