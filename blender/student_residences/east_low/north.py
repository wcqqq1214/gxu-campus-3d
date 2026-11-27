"""Surveyed portions of East 13–16, retaining the campus mesh on other sides."""

import math
from bisect import bisect_left
from math import cos, pi, sin

from geometry import Mesh

from .blocks import facade
from .walls import Edge, cell, clockwise, sash


def local_point(e, p):
    x, y = p[0] - e.a[0], p[1] - e.a[1]
    return x * e.ux + y * e.uy, x * e.nx + y * e.ny, p[2]


def discard_faces(m, removed):
    keep = [i for i in range(len(m.f)) if i not in removed]
    used = sorted({v for i in keep for v in m.f[i]})
    remap = {original: compact for compact, original in enumerate(used)}
    m.face_uvs = {j: m.face_uvs[i] for j, i in enumerate(keep) if i in m.face_uvs}
    m.f = [tuple(remap[v] for v in m.f[i]) for i in keep]
    m.m = [m.m[i] for i in keep]
    m.parts = [
        (label, bisect_left(used, start), bisect_left(used, end))
        for label, start, end in m.parts
    ]
    m.v = [m.v[v] for v in used]


def strip_wall(m, e, z, h, *, west_tip=False):
    removed = set()
    for i, f in enumerate(m.f):
        coords = [local_point(e, m.v[k]) for k in f]
        if west_tip:
            on_wall = all(
                -0.15 < t < e.length + 0.15
                and -0.25 < d < 1.75
                and z - 0.02 <= height <= z + h + 0.025
                for t, d, height in coords
            )
        else:
            on_wall = all(
                -0.12 <= t <= e.length + 0.12
                and -0.24 <= d <= 1.7
                and height <= z + h + 0.02
                for t, d, height in coords
            )
        if on_wall:
            removed.add(i)
    discard_faces(m, removed)


def north_roof(b, z, P, m):
    # Local rectangular deck fields visible within the mapped footprint.
    # Positions are relative to the longest east-west roof axis.
    fields = {
        'way/760176670': [(-36.5, 1, 17, 11), (1, 1, 38, 10), (32, 1, 14, 10)],
        'way/760176671': [(-2, 1, 27, 5.6), (15, 0.6, 6.3, 5.8)],
        'way/760176668': [(0.8, 0.7, 9.6, 5.2)],
    }
    r = clockwise(b['polygons'][0][0])
    a, c = max(zip(r, r[1:] + r[:1]), key=lambda p: math.dist(*p))
    if a[0] > c[0]:
        a, c = c, a
    e = Edge(a, c)
    cx, cy = b['center']
    roof = z + b['height']
    for u, v, w, d in fields[b['id']]:
        x = cx + e.ux * u - e.uy * v
        y = cy + e.uy * u + e.ux * v
        m.box(x, y, roof + 0.09, w, d, 0.18, P['roof'], e.angle)
        for side in (-1, 1):
            k = side * (d - 0.13) / 2
            m.box(
                x - e.uy * k,
                y + e.ux * k,
                roof + 0.24,
                w,
                0.13,
                0.12,
                P['band'],
                e.angle,
            )
        for side in (-1, 1):
            k = side * (w - 0.13) / 2
            m.box(
                x + e.ux * k,
                y + e.uy * k,
                roof + 0.24,
                0.13,
                d - 0.26,
                0.12,
                P['band'],
                e.angle,
            )


def curved_end(m, e, z, h, mat, trim):
    # Open-front half-elliptical balconies spring from the solid end wall.
    t = e.length * 0.51
    steps = 12
    arc = [
        (t + 2.25 * math.cos(math.pi * j / steps), 1.48 * math.sin(math.pi * j / steps))
        for j in range(steps + 1)
    ]
    inner = [
        (t + 2.08 * math.cos(math.pi * j / steps), 1.29 * math.sin(math.pi * j / steps))
        for j in range(steps + 1)
    ]
    for floor in range(2, 7):
        base = z + h * floor / 7
        bottom = [e.p(x, y, base) for x, y in arc]
        upper = [e.p(x, y, base + 0.14) for x, y in arc]
        m.face(upper, trim)
        m.face(bottom[::-1], mat)
        for i in range(steps):
            j = i + 1
            m.face([bottom[i], bottom[j], upper[j], upper[i]], mat)
            lo = base + 0.14
            hi = base + 0.49 * h / 7 if e.nx < 0 else lo + 0.91
            a, b = arc[i], arc[j]
            c, d = inner[i], inner[j]
            m.face([e.p(*a, lo), e.p(*b, lo), e.p(*b, hi), e.p(*a, hi)], mat)
            m.face([e.p(*d, lo), e.p(*c, lo), e.p(*c, hi), e.p(*d, hi)], mat)
            m.face([e.p(*a, hi), e.p(*b, hi), e.p(*d, hi), e.p(*c, hi)], trim)


def balcony_back(m, e, z, h, p, near):
    w = e.length
    west = e.uy > 0
    for j in range(7):
        low = z + j * h / 7
        high = low + h / 7
        u = 0.34 * w
        v = 0.67 * w
        for l, r in [(0, u), (v, w)]:
            if (l == 0) == west:
                mid = (l + r) * 0.5
                cell(
                    m,
                    e,
                    l,
                    r,
                    low,
                    high,
                    mid - 0.70,
                    mid + 0.70,
                    low + 0.89,
                    high - 0.57,
                    0,
                    0.16,
                    p['cream'],
                    p,
                    near,
                )
            else:
                e.rect(m, l, r, low, high, 0, p['cream'])
        sill = low + (0.22 if j >= 2 else 0.75)
        head = high - 0.37
        e.rect(m, u, v, low, sill, 0, p['cream'])
        e.rect(m, u, v, head, high, 0, p['cream'])
        e.reveal(m, u, v, sill, head, 0, -0.44, p['cream'])
        for k in range(3):
            left = u + (v - u) * k / 3
            right = u + (v - u) * (k + 1) / 3
            sash(m, e, left, right, sill, head, -0.44, p, near)


def curved_coping(m, e, z, h, p):
    joint_height = 0.49 * h / 7
    roof = z + h
    center = 0.51 * e.length
    left, right = center - 2.25, center + 2.25
    shell = Mesh()
    # The ordinary campus mesh provides the outer face of the roof parapet.
    # Split it at the chord of the curved cap so there is no internal double wall.
    matches = []
    for i, face in enumerate(m.f):
        if len(face) != 4:
            continue
        offsets = [local_point(e, m.v[j]) for j in face]
        along, depth, height = zip(*offsets)
        if (
            min(along) < left < right < max(along)
            and min(depth) > 0.115
            and max(depth) < 0.14
            and abs(min(height) - roof) < 0.03
            and 0.6 < max(height) - roof < 1
        ):
            matches.append(
                (i, min(along), max(along), depth[0], min(height), max(height))
            )
    [(face_index, start, end, attach, low, high)] = matches
    base = high - 0.19
    for a, c, bot, top in [
        (start, left, low, high),
        (right, end, low, high),
        (left, right, low, base),
    ]:
        e.rect(shell, a, c, bot, top, attach, m.m[face_index])
    arc = [
        (center + 2.25 * cos(pi * j / 16), attach + (1.48 - attach) * sin(pi * j / 16))
        for j in range(17)
    ]
    bottom = [e.p(t, d, base) for t, d in arc]
    top = [e.p(t, d, base + joint_height) for t, d in arc]
    shell.face(top, p['band'])
    shell.face(bottom[::-1], p['cream'])
    for j in range(len(arc) - 1):
        shell.face([bottom[j], bottom[j + 1], top[j + 1], top[j]], p['cream'])
    e.rect(
        shell, left, right, high, base + joint_height, attach, p['cream'], reverse=True
    )
    discard_faces(m, {face_index})
    m.extend(shell)


def west_tip(m, e, z, h, p):
    strip_wall(m, e, z, h, west_tip=True)
    step = h / 8
    width = e.length
    # From the west a single narrow stack is visible towards the south.
    for floor in range(8):
        low = z + floor * step
        high = low + step
        if floor == 0:
            e.rect(m, 0, width, low, low + 0.30, 0, p['blueGrey'])
            e.rect(m, 0, width, low + 0.30, high - 0.04, 0, p['render'])
        else:
            u = width * 0.29
            v = u + 1.77
            sill = low + 0.22
            head = high - 0.44
            for l, r, bot, top in [
                (0, u, low, high - 0.04),
                (v, width, low, high - 0.04),
                (u, v, low, sill),
            ]:
                e.rect(m, l, r, bot, top, 0, p['render'])
            if floor in (1, 2):
                # The 2019 west-end photograph shows a narrow recessed panel
                # immediately above each of the two visible openings.
                a, c = u + 0.23 * (v - u), v - 0.23 * (v - u)
                bottom, top = head + 0.08, high - 0.12
                for l, r, lo, hi in [
                    (u, a, head, high - 0.04),
                    (c, v, head, high - 0.04),
                    (a, c, head, bottom),
                    (a, c, top, high - 0.04),
                ]:
                    e.rect(m, l, r, lo, hi, 0, p['render'])
                e.reveal(m, a, c, bottom, top, 0, -0.10, p['render'])
                e.rect(m, a, c, bottom, top, -0.10, p['blueGrey'])
            else:
                e.rect(m, u, v, head, high - 0.04, 0, p['render'])
            e.reveal(m, u, v, sill, head, 0, -0.71, p['render'])
            e.rect(m, u, v, sill, head, -0.71, p['shade'])
            for rank in range(6):
                bar = sill + 0.13 + rank * 0.153
                e.rect(m, u, v, bar - 0.020, bar + 0.020, -0.063, p['metal'])
                e.rect(
                    m, u, v, bar - 0.020, bar + 0.020, -0.117, p['metal'], reverse=True
                )
                e.strip(m, u, v, -0.063, -0.117, bar + 0.020, p['metal'])
                e.strip(m, u, v, -0.063, -0.117, bar - 0.020, p['metal'], ceiling=True)
        e.rect(m, 0, width, high - 0.04, high, 0, p['band'])


def north_facade(m, b, z, C, P, detail):
    key = b['id']
    h = b['height']
    r = clockwise(b['polygons'][0][0])
    # Existing core geometry is retained on the occluded sides.
    m.m = [P['cream'] if mat == C['pink'] else mat for mat in m.m]
    for a, c in zip(r, r[1:] + r[:1]):
        e = Edge(a, c)
        if key == 'way/760176670' and abs(e.nx) > 0.94 and e.length > 17:
            strip_wall(m, e, z, h)
            balcony_back(m, e, z, h, P, detail)
            for j in range(7):
                top = z + (j + 1) * h / 7
                e.beam(
                    m, 0.025, e.length - 0.025, top - 0.11, top, 0.018, 0.065, P['band']
                )
            if e.nx < 0:
                curved_coping(m, e, z, h, P)
            curved_end(m, e, z, h, P['cream'], P['band'])
        if key == 'way/760176670' and e.ny < -0.94 and e.length > 15:
            strip_wall(m, e, z, h)
            facade(m, e, z, 7, h / 7, 'framed', P, detail)
        if key != 'way/760176670' and e.ny > 0.94 and e.length > 15:
            strip_wall(m, e, z, h)
            facade(m, e, z, 6, h / 6, 'framed', P, detail)
            if key == 'way/760176671':
                # North elevation has projecting horizontal window heads.
                n = round(e.length / 4.4)
                for i in range(n):
                    mid = (i + 0.5) * e.length / n
                    for j in range(1, 6):
                        top = z + (j + 1) * h / 6 - 0.46
                        e.beam(
                            m,
                            mid - 1.2,
                            mid + 1.2,
                            top - 0.12,
                            top,
                            0.145,
                            0.36,
                            P['cream'],
                        )
    north_roof(b, z, P, m)
    return m


def dorm16(m, b, z, P, detail):
    # Keep the courtyard and eastern street-facing block. Replace only the south
    # face of the projecting west wing, from the observed plaza-facing grid.
    outer = b['polygons'][0][0]
    a, c = outer[-2], outer[-1]
    e = Edge(a, c)
    if e.ny > 0:
        e = Edge(c, a)
    h = b['height']
    strip_wall(m, e, z, h)
    n = round(e.length / 3.45)
    floor = h / 8
    glazing = Mesh()
    for i in range(n):
        l, r = e.length * i / n, e.length * (i + 1) / n
        for j in range(8):
            lo = z + j * floor
            hi = lo + floor
            u = l + 0.16
            v = r - 0.16
            e.rect(m, l, u, lo, hi, 0, P['render'])
            e.rect(m, v, r, lo, hi, 0, P['render'])
            e.rect(m, u, v, lo, lo + 0.51, 0, P['blueGrey'])
            e.rect(m, u, v, hi - 0.2, hi, 0, P['render'])
            e.reveal(m, u, v, lo + 0.51, hi - 0.2, 0, -0.28, P['render'])
            sash(glazing, e, u, v, lo + 0.51, hi - 0.2, -0.28, P, detail)
        e.beam(m, l + 0.02, l + 0.16, z + 0.25, z + h, 0.12, 0.32, P['render'])
    west_tip(m, Edge(outer[0], outer[1]), z, h, P)
    m.extend(glazing)
    return m
