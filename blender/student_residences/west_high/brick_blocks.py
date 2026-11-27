"""Short red gallery blocks and the longer brick residences 21 and 27."""

from pathlib import Path

import geometry
from geometry import Mesh

from .walls import (
    _attic,
    _edges,
    _glazing,
    _paint_walls,
    _range,
    _remove_faces,
    _retain_part,
    _window,
    finish_material,
    local_texture,
)


def _frame(m, w, l, r, lo, hi, mat, detail, trim=0.118):
    # One continuous cast surround. Its inner lip turns back to the glazing plane.
    corners = [(l, lo), (r, lo), (r, hi), (l, hi)]
    inner = [
        (l + trim, lo + trim),
        (r - trim, lo + trim),
        (r - trim, hi - trim),
        (l + trim, hi - trim),
    ]
    for j in range(4):
        k = (j + 1) % 4
        m.face(
            [
                w.point(*corners[j]),
                w.point(*corners[k]),
                w.point(*corners[k], 0.115),
                w.point(*corners[j], 0.115),
            ],
            mat['reveal'],
        )
        m.face(
            [
                w.point(*corners[j], 0.115),
                w.point(*corners[k], 0.115),
                w.point(*inner[k], 0.115),
                w.point(*inner[j], 0.115),
            ],
            mat['reveal'],
        )
        m.face(
            [
                w.point(*inner[j], 0.115),
                w.point(*inner[k], 0.115),
                w.point(*inner[k]),
                w.point(*inner[j]),
            ],
            mat['reveal'],
        )
    _glazing(m, w, l + trim, r - trim, lo + trim, hi - trim, mat, detail)


def _north_core(b, C, detail, w):
    h = b['height']
    levels = int(b['levels'])
    step = h / levels
    mat = {
        k: C['WestDormExterior_' + v]
        for k, v in [('reveal', 'cream'), ('frame', 'metal'), ('glass', 'glass')]
    }
    clay = C['WestDormExterior_clay']
    part = Mesh()
    for level in range(levels):
        base = level * step
        # The three readable upper rows in the north photograph have short, raised flank lights.
        slot_sill, slot_head = (1.885, 2.685) if level >= levels - 3 else (1.29, 2.36)
        layouts = (
            [(0.28, 1.52, 0.96, 2.49), (0.72, 1.52, 0.96, 2.49)]
            if level == 0
            else [
                (0.085, 0.51, slot_sill, slot_head),
                (0.35, w.width * 0.15, 0.95, 2.54),
                (0.65, w.width * 0.15, 0.95, 2.54),
                (0.915, 0.51, slot_sill, slot_head),
            ]
        )
        openings = [
            (u * w.width, width, base + lo, base + hi) for u, width, lo, hi in layouts
        ]
        last = 0.0
        for mid, width, lo, hi in openings:
            left, right = mid - width / 2, mid + width / 2
            w.face(part, last, left, base, base + step, clay)
            w.face(part, left, right, base, lo, clay)
            w.face(part, left, right, hi, base + step, clay)
            if level and width > 1:
                _frame(part, w, left, right, lo, hi, mat, detail, trim=0.07)
                if level >= levels - 3:
                    # Both units lie at the outer jamb, between sill and transom, in the north photo.
                    u = mid + (-1 if mid < w.width / 2 else 1) * (width / 2 + 0.44)
                    ac = local_texture(
                        C, 'West17NorthUnit', (0.34, 0.35, 0.33), 'north-unit.png'
                    )
                    case = finish_material(
                        C, 'West17EquipmentCase', (0.39, 0.395, 0.375)
                    )
                    w.ledge(
                        part,
                        u - 0.365,
                        u + 0.365,
                        lo + 0.13,
                        lo + 0.67,
                        0,
                        0.365,
                        case,
                        ac,
                    )
            else:
                _glazing(part, w, left, right, lo, hi, mat, detail)
            last = right
        w.face(part, last, w.width, base, base + step, clay)
        if level:
            w.ledge(
                part,
                0.235 * w.width,
                0.765 * w.width,
                base + 0.22,
                base + 0.40,
                0,
                0.07,
                mat['reveal'],
            )
    return part


def _west_window_pair(b, C, detail, mesh, w, axis):
    h = b['height']
    levels = int(b['levels'])
    step = h / levels
    mat = {
        k: C['WestDormExterior_' + v]
        for k, v in [('reveal', 'cream'), ('frame', 'metal'), ('glass', 'glass')]
    }
    clay = C['WestDormExterior_clay']
    part = Mesh()
    for level in range(levels):
        base = level * step
        last = 0
        for mid in (axis - 1.26, axis + 1.26):
            l, r = mid - 0.84, mid + 0.84
            lo, hi = base + 0.94, base + 2.52
            w.face(part, last, l, base, base + step, clay)
            w.face(part, l, r, base, lo, clay)
            w.face(part, l, r, hi, base + step, clay)
            _frame(part, w, l, r, lo, hi, mat, detail)
            if level < 3:
                il, ir = l + 0.118, r - 0.118
                bottom, top = lo + 0.118, hi - 0.118
                rail = C['WestDormExterior_metal']
                count = 10 if detail else 4
                for j in range(1, count + 1):
                    u = il + (ir - il) * j / (count + 1)
                    w.face(part, u - 0.01, u + 0.01, bottom, top, rail, -0.048)
                for f in (0.48, 0.76):
                    bar = bottom + (top - bottom) * f
                    w.ledge(part, il, ir, bar, bar + 0.025, -0.051, -0.034, rail)
            last = r
        w.face(part, last, w.width, base, base + step, clay)
    mesh.add_part('西27西山墙双窗与浅色凸框', part)


def gallery_block(b, z, C, mats, detail, baseline):
    mesh, fac, roof = Mesh(), Mesh(), Mesh()
    ring = b['polygons'][0][0]
    x0, y0, x1, y1 = b['bounds']
    h, levels = b['height'], int(b['levels'])
    pitch = h / levels
    # Actual north outline steps forward at the enclosed middle bay.
    gables = Mesh()
    end_tile = finish_material(
        C,
        'WestGableSmallFaceTile' if detail else 'WestGableDistantTile',
        (0.45, 0.194, 0.126),
        Path(geometry.__file__).parent / 'textures/west23/masonry.jpg'
        if detail
        else None,
    )
    plinth = finish_material(C, 'WestGableRedPlinth', (0.225, 0.095, 0.068))
    for e in _edges(ring):
        L = e.length
        upper = z + h
        gallery = e.ny > 0.9 and e.a[1] < y1 - 1.0 and L > 9
        core = e.ny > 0.9 and e.a[1] > y1 - 1 and L > 8
        if gallery:
            back = -1.15
            e.panel(fac, 0, L, z, upper, back, mats['shade'])
            # The outward-facing end bay is enclosed, as seen on the oblique courtyard views.
            near_start = e.a[0] < x0 + 1 or e.a[0] > x1 - 1
            cap = min(3.0, L * 0.2)
            a, bend = (0, cap) if near_start else (L - cap, L)
            e.block(fac, a, bend, z, upper, back, 0.013, mats['clay'])
            for u in (0, L - 0.18):
                e.block(fac, u, u + 0.18, z, upper, back, 0.02, mats['clay'])
            for floor in range(levels):
                base = z + floor * pitch
                _window(
                    fac, e, (a + bend) / 2, 1.32, base + 0.95, base + 2.44, mats, detail
                )
                if floor:
                    e.block(
                        fac, 0, L, base - 0.14, base + 0.82, back, 0.02, mats['clay']
                    )
                    e.block(
                        fac,
                        0,
                        L,
                        base - 0.14,
                        base + 0.035,
                        -0.07,
                        0.065,
                        mats['cream'],
                    )
                bays = max(3, round(L / 3.65))
                for k in range(1, bays):
                    u = k * L / bays
                    e.block(
                        fac,
                        u - 0.095,
                        u + 0.095,
                        base,
                        base + pitch,
                        -0.94,
                        -0.74,
                        mats['tile'],
                    )
            e.block(fac, 0, L, upper - 0.34, upper + 0.12, back, 0.06, mats['chalk'])
        else:
            if core and b['id'] == 'way/759129517':
                north_core = _north_core(b, C, detail, e.wall(z))
                e.block(
                    fac, 0, L, upper - 0.12, upper + 0.31, -0.12, 0.06, mats['chalk']
                )
                continue
            if abs(e.nx) > 0.98 and L > 7:
                w = e.wall(z)
                w.face(gables, 0, w.width, 0, 0.46, plinth)
                w.face(gables, 0, w.width, 0.46, h, end_tile)
            else:
                e.panel(fac, 0, L, z, upper, 0, mats['clay'])
            for floor in range(levels):
                base = z + floor * pitch
                if floor:
                    e.block(
                        fac, 0, L, base - 0.06, base + 0.11, -0.015, 0.07, mats['cream']
                    )
                if core:
                    for u in (L * 0.28, L * 0.72):
                        _window(fac, e, u, 1.52, base + 0.96, base + 2.49, mats, detail)
                elif e.ny < -0.9:
                    # Paired, deep, vertically aligned facade bays alternate with much smaller punched lights.
                    pairs = max(4, round(L / 7.4))
                    pitch_x = L / pairs
                    for k in range(pairs):
                        u = (k + 0.5) * pitch_x
                        for side in (-1, 1):
                            mid = u + side * 0.82
                            e.panel(
                                fac,
                                mid - 0.68,
                                mid + 0.68,
                                base + 0.27,
                                base + pitch - 0.18,
                                0.037,
                                mats['shade'],
                            )
                            _window(
                                fac,
                                e,
                                mid + side * 1.49,
                                0.65,
                                base + 1.57,
                                base + 2.27,
                                mats,
                                detail,
                            )
                        for post in (-1.55, 0, 1.55):
                            e.block(
                                fac,
                                u + post - 0.085,
                                u + post + 0.085,
                                base,
                                base + pitch,
                                -0.01,
                                0.40,
                                mats['cream'],
                            )
                        e.block(
                            fac,
                            u - 1.64,
                            u + 1.64,
                            base + 0.14,
                            base + 0.28,
                            -0.01,
                            0.40,
                            mats['tile'],
                        )
            e.block(
                fac,
                0,
                L,
                upper - 0.12,
                upper + (0.31 if core else 0.12),
                -0.12,
                0.06,
                mats['chalk'],
            )
    flat = [p for r in b['polygons'][0] for p in r[:-1]]
    tri = b['roofTriangles'][0]
    for k in range(0, len(tri), 3):
        pts = [(*flat[i], z + h + 0.01) for i in tri[k : k + 3]]
        roof.face(
            pts
            if (pts[1][0] - pts[0][0]) * (pts[2][1] - pts[0][1])
            > (pts[1][1] - pts[0][1]) * (pts[2][0] - pts[0][0])
            else pts[::-1],
            mats['roof'],
        )
    # The southern roof strip is warm toned in the overhead image; no slope is measurable.
    roof.box(
        (x0 + x1) / 2,
        y0 + 1.86,
        z + h + 0.035,
        x1 - x0 - 0.38,
        3.40,
        0.035,
        mats['roofRed'],
    )
    mesh.add_part('主体与北廊', fac)
    mesh.add_part('屋面与南缘色带', roof)
    _retain_part(baseline, mesh, '03_')
    mesh.add_part('砖质实山墙与暗红勒脚', gables)
    if b['id'] == 'way/759129517':
        mesh.add_part('西17北凸部双宽窗与侧缝窗', north_core)
    return mesh


def brick_block(b, z, C, mats, detail, baseline, number):
    m, fac = Mesh(), Mesh()
    # Retain mapped body and roof, replace the generic grid on these two blocks.
    for prefix in ('01_', '02_', '03_'):
        _retain_part(baseline, m, prefix)
    h, levels = b['height'], int(b['levels'])
    pitch = h / levels
    _paint_walls(m, mats['clay'])
    ring = b['polygons'][0][0]
    if number == 21:
        _attic(m, z + h - pitch + 0.1, mats['chalk'])
        # The first point splits a single straight north edge in the source way.
        ring = ring[1:-1] + [ring[1]]
    edges = _edges(ring)
    if number == 27:
        west_edge = max((e for e in edges if e.nx < -0.98), key=lambda e: e.length)
        west = west_edge.wall(z)
        lo, hi = _range(m, '01_')
        west_shell = set()
        for i, f in enumerate(m.f):
            if lo <= f[0] < hi:
                us, ds = zip(*(west.uv_depth(m.v[k]) for k in f))
                if (
                    max(abs(v) for v in ds) < 1e-4
                    and max(us) - min(us) > 0.95 * west.width
                ):
                    west_shell.add(i)
        _remove_faces(m, west_shell)
    for e in edges:
        L = e.length
        for f in range(levels):
            base = z + f * pitch
            if f:
                e.block(fac, 0, L, base - 0.07, base + 0.09, 0.005, 0.12, mats['cream'])
            if L < 5 or (number == 27 and e is west_edge):
                continue
            if abs(e.ny) > 0.9:
                groups = max(1, round(L / (7.2 if number == 21 else 5.8)))
                spacing = L / groups
                for k in range(groups):
                    u = (k + 0.5) * spacing
                    for side in (-1, 1):
                        _window(
                            fac,
                            e,
                            u + side * spacing * 0.19,
                            1.40,
                            base + 0.93,
                            base + 2.45,
                            mats,
                            detail,
                        )
                    if number == 21:
                        for side in (-1, 1):
                            mid = u + side * spacing * 0.395
                            e.panel(
                                fac,
                                mid - 0.38,
                                mid + 0.38,
                                base + 1.74,
                                base + 2.42,
                                0.038,
                                mats['glass'],
                            )
                        e.block(
                            fac,
                            u - 0.105,
                            u + 0.105,
                            base + 0.10,
                            base + pitch - 0.08,
                            -0.005,
                            0.22,
                            mats['cream'],
                        )
                    elif e.ny > 0.9 and f:
                        for dx in (-spacing * 0.37, 0, spacing * 0.37):
                            e.block(
                                fac,
                                u + dx - 0.10,
                                u + dx + 0.10,
                                base,
                                base + pitch,
                                -0.005,
                                0.48,
                                mats['cream'],
                            )
                        e.block(
                            fac,
                            u - spacing * 0.38,
                            u + spacing * 0.38,
                            base + 0.1,
                            base + 0.23,
                            -0.005,
                            0.46,
                            mats['tile'],
                        )
            else:
                for t in (0.33, 0.50, 0.67) if number == 21 else (0.37, 0.60):
                    _window(fac, e, L * t, 1.42, base + 1.03, base + 2.42, mats, detail)
    m.add_part('层带与成组窗洞', fac)
    if number == 27:
        # Preserve the paired windows' centreline (48.5% along the surveyed edge).
        axis = west.uv_depth(west_edge.point(0.485 * west_edge.length, 0, z))[0]
        _west_window_pair(b, C, detail, m, west, axis)
    return m
