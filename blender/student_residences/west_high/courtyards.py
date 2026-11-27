"""Pale west residences and the open courts of the double wings and West 28."""

from math import cos, pi, sin

from geometry import Mesh

from .walls import (
    _edges,
    _glazing,
    _paint_walls,
    _range,
    _remove_faces,
    _ring_walls,
    finish_material,
)


def _rounded_ends(b, z, mats, detail, mesh):
    part = Mesh()
    h, levels = b['height'], int(b['levels'])
    x0, _, x1, _ = b['bounds']
    for e in _edges(b['polygons'][0][0]):
        if e.nx < 0.9 or e.a[0] < x1 - 3:
            continue
        # Two balconies sit side by side on each end: one has open metal rails,
        # the other a warm solid upstand. A thin wall separates their stacks.
        mid = e.length * 0.51
        e.block(part, mid - 0.12, mid + 0.12, z, z + h, -0.025, 1.62, mats['chalk'])
        for f in range(1, levels):
            base = z + f * h / levels
            for left, right, open_rails in (
                (0.30, mid - 0.12, False),
                (mid + 0.12, e.length - 0.30, True),
            ):
                a = e.point(left, 0.01, base)
                bb = e.point(right, 0.01, base)
                points = [
                    e.point(
                        (left + right) / 2 + (right - left) / 2 * cos(k * pi / 12),
                        0.16 + 1.86 * sin(k * pi / 12),
                        base,
                    )
                    for k in range(13)
                ]
                ring = [bb] + points + [a]
                top = [(x, y, v + 0.04) for x, y, v in ring]
                low = [(x, y, v - 0.17) for x, y, v in ring]
                part.face(top, mats['chalk'])
                part.face(low[::-1], mats['cream'])
                for k in range(len(ring)):
                    j = (k + 1) % len(ring)
                    part.face([low[k], low[j], top[j], top[k]], mats['cream'])
                for k, (a, bb) in enumerate(zip(points, points[1:])):
                    ax, ay, _ = a
                    bx, by, _ = bb
                    if not open_rails:
                        part.face(
                            [
                                (ax, ay, base + 0.03),
                                (bx, by, base + 0.03),
                                (bx, by, base + 0.55),
                                (ax, ay, base + 0.55),
                            ],
                            mats['tile'],
                        )
                    if detail or k % 2 == 0:
                        part.line(
                            (ax, ay, base + (0.05 if open_rails else 0.55)),
                            (ax, ay, base + 0.95),
                            0.033,
                            mats['metal'],
                            5,
                        )
                    part.line(
                        (ax, ay, base + 0.95),
                        (bx, by, base + 0.95),
                        0.046,
                        mats['metal'],
                        5,
                    )
        e.block(
            part,
            0.16,
            e.length - 0.16,
            z + h - 0.06,
            z + h + 0.11,
            -0.03,
            1.42,
            mats['chalk'],
        )
    mesh.add_part('双翼东端弧形阳台', part)


def _replace_baseline_walls(b, z, mesh, selected, body_mat):
    """Clear the ordinary-building shell and window panels on the new elevations."""
    blo, bhi = _range(mesh, '01_')
    flo, fhi = _range(mesh, '04_')
    doomed = set()
    for i, f in enumerate(mesh.f):
        is_body = blo <= f[0] < bhi
        is_window = flo <= f[0] < fhi
        if not (is_body or is_window):
            continue
        pts = [mesh.v[k] for k in f]
        if is_body:
            if max(p[2] for p in pts) - min(p[2] for p in pts) < 1:
                continue
            mesh.m[i] = body_mat
            for w in selected:
                uv = [w.uv_depth(p) for p in pts]
                if (
                    max(abs(d) for _, d in uv) < 0.0001
                    and max(u for u, _ in uv) - min(u for u, _ in uv) > w.width - 0.02
                ):
                    doomed.add(i)
                    break
        else:
            if (
                b['id'] == 'relation/11970576'
                and max(p[2] for p in pts) < z + b['height'] / b['levels'] - 0.01
            ):
                continue
            x = sum(p[0] for p in pts) / len(pts)
            y = sum(p[1] for p in pts) / len(pts)
            for w in selected:
                u, d = w.uv_depth((x, y))
                if 0.38 < u < w.width - 0.38 and -0.10 < d < 1.52:
                    doomed.add(i)
                    break
    _remove_faces(mesh, doomed)


def _pale_finishes(C):
    return dict(
        shell=finish_material(C, 'GXUWestPaleTile', (0.64, 0.626, 0.56)),
        courtyard=finish_material(C, 'GXUWestCourtyardTile', (0.68, 0.69, 0.66)),
        side=finish_material(C, 'GXUWestBalconyReveal', (0.43, 0.411, 0.35)),
        shade=finish_material(C, 'GXUWestBalconyShadow', (0.201, 0.21, 0.191)),
        sand=finish_material(C, 'GXUWestBalconySpandrel', (0.462, 0.302, 0.195)),
        frame=finish_material(C, 'GXUWestPaleAluminium', (0.45, 0.465, 0.443)),
        glass=finish_material(C, 'GXUWestGreyWindow', (0.092, 0.122, 0.12)),
        reveal=finish_material(C, 'GXUWestPaleJamb', (0.475, 0.463, 0.407)),
        rail=finish_material(C, 'GXUWestRail', (0.23, 0.25, 0.23)),
    )


def _wings(b, z, C, detail, mesh):
    colors = _pale_finishes(C)

    surfaces = [
        w
        for w in _ring_walls(b['polygons'][0][0], z)
        if abs(w.ny) > 0.98 and w.width > 35
    ]
    _replace_baseline_walls(b, z, mesh, surfaces, colors['shell'])
    part = Mesh()
    for w in surfaces:
        # Two arm ends retain their separate paired curved balconies from the previous build.
        n = max(5, round(w.width / 6.4))
        pitch = b['height'] / b['levels']
        for level in range(int(b['levels'])):
            base = level * pitch
            for k in range(n):
                left = k * w.width / n
                right = (k + 1) * w.width / n
                c = (left + right) / 2
                if not level:
                    w.face(part, left, c - 0.76, base, base + pitch, colors['shell'])
                    w.face(part, c + 0.76, right, base, base + pitch, colors['shell'])
                    w.face(part, c - 0.76, c + 0.76, base, base + 0.9, colors['shell'])
                    w.face(
                        part,
                        c - 0.76,
                        c + 0.76,
                        base + 2.32,
                        base + pitch,
                        colors['shell'],
                    )
                    _glazing(
                        part,
                        w,
                        c - 0.76,
                        c + 0.76,
                        base + 0.9,
                        base + 2.32,
                        colors,
                        detail,
                    )
                    continue
                start = left
                # Narrow paired lights flank the wider, recessed balcony stack.
                for mid, balcony in (
                    (left + 0.77, False),
                    (c, True),
                    (right - 0.77, False),
                ):
                    half = 1.16 if balcony else 0.36
                    l, r = mid - half, mid + half
                    lo = base + (0.20 if balcony else 1.03)
                    hi = base + (2.99 if balcony else 2.48)
                    w.face(part, start, l, base, base + pitch, colors['shell'])
                    w.face(part, l, r, base, lo, colors['shell'])
                    w.face(part, l, r, hi, base + pitch, colors['shell'])
                    if balcony:
                        w.cross_section(part, l, r, lo, hi, -0.70, colors['side'])
                        w.face(part, l, r, lo, hi, colors['shade'], -0.70)
                        w.ledge(part, l, r, lo, lo + 0.64, -0.08, 0.11, colors['sand'])
                        w.ledge(
                            part,
                            l,
                            r,
                            lo + 0.81,
                            lo + 0.86,
                            -0.015,
                            0.04,
                            colors['rail'],
                        )
                        for t in (0.18, 0.49, 0.81):
                            u = l + (r - l) * t
                            w.face(
                                part,
                                u - 0.024,
                                u + 0.024,
                                lo + 0.64,
                                lo + 0.81,
                                colors['rail'],
                                0.027,
                            )
                    else:
                        _glazing(part, w, l, r, lo, hi, colors, detail)
                    start = r
                w.face(part, start, right, base, base + pitch, colors['shell'])
    mesh.add_part('双翼长墙内凹阳台与窄窗', part)


def _court(b, z, C, detail, mesh):
    colors = _pale_finishes(C)
    surfaces = [
        w for w in _ring_walls(b['polygons'][0][1], z, hole=True) if w.width > 20
    ]
    _replace_baseline_walls(b, z, mesh, surfaces, colors['courtyard'])
    part = Mesh()
    pitch = b['height'] / b['levels']
    for w in surfaces:
        spans = round(w.width / 4.2)
        for lev in range(int(b['levels'])):
            base = lev * pitch
            for i in range(spans):
                l, r = w.width * i / spans, w.width * (i + 1) / spans
                if not lev:
                    w.face(part, l, r, base, base + pitch, colors['courtyard'])
                    continue
                a, bb = l + 0.15, r - 0.15
                lo, hi = base + 0.19, base + pitch - 0.17
                w.face(part, l, a, base, base + pitch, colors['courtyard'])
                w.face(part, bb, r, base, base + pitch, colors['courtyard'])
                w.face(part, a, bb, base, lo, colors['side'])
                w.face(part, a, bb, hi, base + pitch, colors['courtyard'])
                w.cross_section(part, a, bb, lo, hi, -0.87, colors['courtyard'])
                w.face(part, a, bb, lo, hi, colors['shade'], -0.87)
                # The handrail and uprights remain entirely behind the surveyed court edge.
                w.ledge(
                    part, a, bb, lo + 0.89, lo + 0.96, -0.15, -0.085, colors['rail']
                )
                for j in range(1, 8 if detail else 5):
                    u = a + (bb - a) * j / (8 if detail else 5)
                    w.face(
                        part,
                        u - 0.022,
                        u + 0.022,
                        lo,
                        lo + 0.89,
                        colors['rail'],
                        -0.117,
                    )
    mesh.add_part('环院长边廊柱、栏杆与楼板', part)


def pale_residence(number, b, z, C, detail, baseline, mats):
    if number == 24:
        _rounded_ends(b, z, mats, detail, baseline)
        lo, hi = _range(baseline, '01_')
        for i, face in enumerate(baseline.f):
            if lo <= face[0] < hi and all(
                abs(baseline.v[v][2] - z - b['height']) < 0.001 for v in face
            ):
                baseline.m[i] = mats['roofDark']
        _wings(b, z, C, detail, baseline)
        return baseline
    top = Mesh()
    x0, y0, x1, y1 = b['bounds']
    roof = z + b['height']
    # Read the actual upper roof face so caps clear the baseline roof finish.
    if number == 28:
        lo, hi = _range(baseline, '02_')
        roof = max(roof, max(v[2] for v in baseline.v[lo:hi]))
    # Flat roof triangles remain cut to the mapped shell, including the court.
    lo, hi = _range(baseline, '01_')
    for i, face in enumerate(baseline.f):
        if lo <= face[0] < hi and all(
            abs(baseline.v[v][2] - z - b['height']) < 0.001 for v in face
        ):
            baseline.m[i] = mats['chalk'] if number == 28 else mats['cream']
    if number == 26:
        for t in (0.095, 0.82):
            top.box(
                x0 + (x1 - x0) * t,
                (y0 + y1) / 2,
                roof + 0.09,
                3.45,
                3.35,
                0.18,
                mats['court'],
            )
            top.box(
                x0 + (x1 - x0) * t,
                (y0 + y1) / 2,
                roof + 0.19,
                2.53,
                2.45,
                0.055,
                mats['roof'],
            )
    else:
        for e in _edges(b['polygons'][0][1]):
            # Centre the coping over the actual courtyard rim on both LODs.
            e.block(top, 0, e.length, roof, roof + 0.16, -0.06, 0.09, mats['court'])
            e.block(
                top,
                0,
                e.length,
                roof + 0.16,
                roof + 0.24,
                -0.09,
                0.12,
                mats['chalk'],
            )
    baseline.add_part('屋面分区' if number == 26 else '天井四边压顶', top)
    if number == 26:
        _paint_walls(
            baseline, finish_material(C, 'West26GreyFacing', (0.62, 0.625, 0.59))
        )
    else:
        _court(b, z, C, detail, baseline)
    return baseline
