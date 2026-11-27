import copy
import math

from geometry import Mesh
from west_dorms import Wall, roof_frame

from .balcony import screen
from .elevations import court_palette, finish_kind, finishes, terminal
from .north_windows import core
from .surface import Surface

_NUMBERS = {
    'way/759158610': 1,
    'way/759158609': 2,
    'way/759158607': 3,
    'way/759158606': 4,
    'way/759158608': 5,
    'way/759147082': 6,
    'way/759147080': 7,
    'way/759147081': 8,
    'way/759147072': 9,
    'way/759147073': 10,
    'way/759147074': 11,
    'way/759147075': 12,
    'way/759147063': 13,
    'way/759147064': 14,
    'way/759147076': 15,
}
IDS = set(_NUMBERS)


def _edges(b):
    ring = b['polygons'][0][0]
    clockwise = sum(a[0] * c[1] - c[0] * a[1] for a, c in zip(ring, ring[1:])) < 0
    return [Wall(a, c, clockwise) for a, c in zip(ring, ring[1:]) if a != c]


def _point(w, u, d, h):
    return (w.x + u * w.tx + d * w.nx, w.y + u * w.ty + d * w.ny, h)


def _strip(m, w, start, end, depth, lo, hi, mat):
    pts = [
        _point(w, start, depth, lo),
        _point(w, end, depth, lo),
        _point(w, end, depth, hi),
        _point(w, start, depth, hi),
    ]
    if w.tx * w.ny - w.ty * w.nx > 0:
        pts.reverse()
    m.face(pts, mat)


def _uv(w, point):
    dx, dy = point[0] - w.x, point[1] - w.y
    return dx * w.tx + dy * w.ty, dx * w.nx + dy * w.ny


def _custom_five(b, z, C, baseline, number):
    result = copy.deepcopy(baseline)
    mesh = Mesh()
    top = z + b['height']
    walls = _edges(b)
    roof_range = next((a, c) for name, a, c in result.parts if name.startswith('02_'))
    if number <= 2:
        # The aerial shows a substantial dark field between the pale roof edges.
        for i, face in enumerate(result.f):
            if (
                roof_range[0] <= face[0] < roof_range[1]
                and result.m[i] == C['paleRoof']
                and all(abs(result.v[k][2] - top) < 0.0001 for k in face)
            ):
                result.m[i] = C['dormConcrete' if number == 1 else 'dormCollector']
        ux, uy, left, bottom, right, _ = roof_frame(b)
        a = left + (9 if number == 1 else 1.1)
        c = right - (5.2 if number == 1 else 1.1)
        if number == 2:
            a = (a + c) / 2 + 2
        # Light transverse divisions enclose the long dark rows. End the trim
        # at the existing collector edge; the opposite wing of W2 is bare.
        for fraction in (0, 0.5, 1):
            x = a + 0.10 + (c - a - 0.20) * fraction
            for row in range(3):
                y = bottom + 2.7 + 2.95 * row
                lo = (ux * x - uy * (y - 0.85), uy * x + ux * (y - 0.85), top + 0.212)
                hi = (ux * x - uy * (y + 0.85), uy * x + ux * (y + 0.85), top + 0.739)
                mesh.line(lo, hi, 0.065, C['paleRoof'], 6)
    elif number == 3:
        # Cut the small sky opening through the existing curved north screen.
        w = next(w for w in walls if w.ny > 0.98 and 10 < w.length < 16)
        span = w.length
        for face in result.f:
            idx = face[0]
            if not roof_range[0] <= idx < roof_range[1] - 23 or len(face) != 4:
                continue
            if not all(abs(result.v[k][2] - top) < 0.0001 for k in face):
                continue
            v = result.v[idx : idx + 24]
            us, ds = zip(*[_uv(w, p) for p in v])
            if (
                abs(max(us) - min(us) - span / 21) > 0.001
                or abs(sum(us) / 24 - span / 2) > 0.001
                or abs(min(ds) + 0.245) > 0.001
                or abs(max(ds) - 0.005) > 0.001
                or max(p[2] for p in v) < top + 1.34
            ):
                continue
            start = min(us)
            end = max(us)
            # Preserve the original curved upper edge and open the middle.
            for k in range(idx, idx + 24):
                x, y, h = result.v[k]
                if abs(h - top) < 0.0001:
                    result.v[k] = (x, y, top + 1.15)
            w.box(
                mesh,
                (start + end) / 2,
                -0.12,
                top + 0.32,
                end - start,
                0.25,
                0.64,
                C['white'],
            )
            break
        if not mesh.v:
            raise ValueError('West 3 north screen topology changed')
    else:
        # The two outer shoulders step above the front eave in both street views.
        w = max((w for w in walls if w.ny < -0.96), key=lambda w: w.length)
        width = w.length * (0.119 if number == 4 else 0.115)
        for end in (False, True):
            u = w.length - width / 2 if end else width / 2
            w.box(mesh, u, -0.16, top + 0.51, width, 0.29, 1.02, C['white'])
            w.box(
                mesh,
                u,
                -0.16,
                top + 1.045,
                width + 0.07,
                0.36,
                0.075,
                C['dormStonePale'],
            )
    result.add_part('本楼实景屋面与轮廓', mesh)
    return result


def _kind(number, w):
    if 7 <= number <= 12:
        if w.ny > 0.93:
            return 'tower' if w.length < 17 else 'gallery'
        if abs(w.nx) > 0.93:
            return 'end' if w.length > 8.7 else 'return'
        if number in (7, 9, 10, 11, 12) and w.ny < -0.93:
            return 'balcony'
    if number == 6 and w.x > 112 and w.length < 1.5:
        return 'curved-end'
    if number == 6 and w.length > 45:
        return 'swept' if w.ny > 0 else 'balcony'
    if number == 15:
        if w.ny > 0.95:
            return 'round'
        if w.ny < -0.95:
            return 'balcony'
        return 'slit'
    if number == 13 and w.ny > 0.95:
        return 'bay'
    if number == 13 and w.nx > 0.95:
        return 'brick-end'
    if number == 14 and w.ny > 0.95:
        return 'gallery'
    return None


def _soffit(m, w, pts, level, thick, mat, *, sides=(True, True, True, True)):
    # Extruded balcony footprint, including a curved outer line where observed.
    ring = [_point(w, u, d, level) for u, d in pts]
    signed = sum(a[0] * b[1] - a[1] * b[0] for a, b in zip(ring, ring[1:] + ring[:1]))
    if signed < 0:
        ring.reverse()
    top = [(x, y, z + thick) for x, y, z in ring]
    # Split the possibly concave strip into quads before export in _ledge.
    m.face(ring[::-1], mat)
    m.face(top, mat)
    for i, a in enumerate(ring):
        j = (i + 1) % len(ring)
        # The mask follows the footprint edges in their original winding.
        edge = len(ring) - 1 - j if signed < 0 else i
        if sides[edge]:
            m.face([a, ring[j], top[j], top[i]], mat)


def _ledge(m, w, start, end, inner, outer, z, thick, mat):
    _soffit(
        m,
        w,
        [(start, inner), (end, inner), (end, outer), (start, outer)],
        z,
        thick,
        mat,
    )


def _curved(m, w, z, number, C):
    # Northern W6B has a broad shallow forward sweep; W15 has two separate
    # round noses near the ends with straight gallery between them.
    L = w.length
    steps = 40

    def profile(t):
        if number == 6:
            return 0.62 + 1.22 * max(0, 1 - ((t - 0.5) / 0.26) ** 2) ** 1.35
        return (
            0.55
            + 2.13
            * max([0] + [1 - ((t - center) / 0.064) ** 2 for center in (0.106, 0.894)])
            ** 0.5
        )

    def ribbon(inner, outer, bottom, thickness, mat):
        sections = []
        for i in range(steps + 1):
            t = i / steps
            d = profile(t)
            low = inner(d)
            high = outer(d)
            sections.append(
                [
                    _point(w, L * t, offset, bottom + h)
                    for offset, h in (
                        (low, 0),
                        (high, 0),
                        (high, thickness),
                        (low, thickness),
                    )
                ]
            )
        left_normal = w.tx * w.ny - w.ty * w.nx > 0

        def face(pts):
            m.face(pts if left_normal else pts[::-1], mat)

        face(sections[0][::-1])
        face(sections[-1])
        for a, b in zip(sections, sections[1:]):
            for i in range(4):
                j = (i + 1) % 4
                face([a[i], a[j], b[j], b[i]])

    ribbon(lambda d: -0.92, lambda d: d, z, 0.16, C['white'])
    ribbon(lambda d: d - 0.15, lambda d: d, z + 0.16, 0.76, C['white'])
    if number == 6:
        ribbon(lambda d: d - 0.02, lambda d: d + 0.012, z + 0.23, 0.10, C['dormBlush'])


def _front(m, w, kind, z, height, floors, number, C, detail, finish):
    L = w.length
    story = height / floors
    for level in range(floors):
        base = z + level * story
        lo = base if level else z - 0.55
        lower = level < 2
        warm = C['dormRose'] if number != 13 else C['dormBrickClay']
        fill = warm if lower or number == 13 else C['white']
        if kind in ('return', 'end', 'slit'):
            if finish != 'base' or level not in (0, 2):
                _strip(m, w, 0, L, 0, lo, base + story, fill)
            w.box(
                m,
                L / 2,
                0.006,
                base + story - 0.10,
                L,
                0.055,
                0.085,
                C['dormBlush'] if lower else C['dormRose'],
            )
            if kind == 'slit' and level >= 2:
                for f in (0.52, 0.67):
                    w.box(
                        m,
                        L * f,
                        0.035,
                        base + story * 0.58,
                        0.62,
                        0.07,
                        0.45,
                        C['dormWindow'],
                    )
            continue
        if kind in ('tower', 'bay'):
            tint = C['dormBlush'] if number in (7, 12) else C['dormStonePale']
            if kind == 'bay':
                tint = C['dormRose']
            _strip(m, w, 0, L, 0, lo, base + story, tint)
            if kind == 'bay':
                _court_band(m, w, base + story - 0.10, C['white'])
            else:
                w.box(m, L / 2, 0.02, base + story - 0.10, L, 0.075, 0.10, C['white'])
            if kind == 'tower':
                for f, width in ((0.14, 0.64), (0.39, 1.0), (0.62, 1.0), (0.86, 0.64)):
                    w.box(
                        m,
                        L * f,
                        0.045,
                        base + story * 0.53,
                        width,
                        0.09,
                        1.44,
                        C['dormWindow'],
                    )
                    if detail:
                        w.box(
                            m,
                            L * f,
                            0.10,
                            base + story * 0.65,
                            width,
                            0.04,
                            0.055,
                            C['white'],
                        )
            else:
                for f in (0.13, 0.38, 0.63, 0.88):
                    u = L * f
                    half = L * 0.058
                    profile = [
                        (u - half, 0.015),
                        (u - half * 0.74, 0.54),
                        (u + half * 0.74, 0.54),
                        (u + half, 0.015),
                    ]
                    sill = base + story * 0.32
                    head = base + story * 0.85
                    for (a, da), (c, dc) in zip(profile, profile[1:]):
                        pts = [
                            _point(w, a, da, sill),
                            _point(w, c, dc, sill),
                            _point(w, c, dc, head),
                            _point(w, a, da, head),
                        ]
                        if w.tx * w.ny - w.ty * w.nx > 0:
                            pts.reverse()
                        m.face(pts, C['dormWindow'])
                    _soffit(m, w, profile, sill - 0.09, 0.10, C['white'])
                    _soffit(m, w, profile, head, 0.11, C['white'])
                    if detail:
                        for a, da in profile[1:3]:
                            w.box(
                                m,
                                a,
                                da,
                                (head + sill) / 2,
                                0.06,
                                0.06,
                                head - sill,
                                C['metal'],
                            )
            continue
        if kind == 'swept' and lower:
            _strip(m, w, 0, L, 0, lo, base + story, warm)
            count = round(L / 3.8)
            for i in range(count):
                w.box(
                    m,
                    (i + 0.5) * L / count,
                    0.045,
                    base + story * 0.56,
                    1.6,
                    0.10,
                    1.55,
                    C['dormWindow'],
                )
            w.box(m, L / 2, 0.04, base + story - 0.08, L, 0.16, 0.13, C['dormBlush'])
            continue
        back = -0.98
        # Openings are relief behind the floor edge. Only exterior-facing surfaces.
        _strip(m, w, 0, L, back, lo, base + story, C['dormConcreteLight'])
        count = max(3, round(L / (4.25 if kind == 'gallery' else 3.95)))
        width = L / count
        for i in range(count):
            u = width * (i + 0.5)
            w.box(
                m,
                u,
                back + 0.037,
                base + story * 0.58,
                width * 0.42,
                0.07,
                story * 0.43,
                C['dormWindow'],
            )
            if kind == 'balcony':
                w.box(
                    m,
                    i * width + 0.13,
                    -0.43,
                    base + story / 2,
                    0.25,
                    1.09,
                    story,
                    fill,
                )
                if number == 15 and not lower:
                    continue
                par = width - 0.26 if lower else width * 0.51
                w.box(
                    m,
                    u,
                    0.038,
                    base + 0.52,
                    par,
                    0.16,
                    0.9,
                    C['dormBlush'] if number != 6 else C['dormButter'],
                )
                if detail and not lower:
                    w.box(
                        m, u, 0.039, base + 1.0, width - 0.25, 0.065, 0.07, C['metal']
                    )
            elif kind == 'gallery' and i % 2 == 0:
                w.box(m, u, -0.05, base + story / 2, 0.19, 0.23, story, fill)
        if kind in ('swept', 'round') and level >= (1 if number == 15 else 2):
            _curved(m, w, base, number, C)
        else:
            _ledge(m, w, 0, L, back, 0.16, base, 0.17, C['white'])
            if kind != 'balcony':
                w.box(m, L / 2, 0.025, base + 0.56, L, 0.17, 0.82, fill)
        # Side returns close the back wall at each end of the new recess.
        for u in (0.08, L - 0.08):
            w.box(m, u, -0.46, base + story / 2, 0.16, 1.09, story, fill)
    if kind == 'balcony' and number == 15:
        # The south street view shows broader full-height paired-bay divisions
        # and a shallow rose ridge over the central bays.
        n = round(L / 3.95)
        for i in (2, 5, n - 5, n - 2):
            w.box(m, L * i / n, 0.11, z + height / 2, 0.68, 0.27, height, C['white'])
        for j in range(20):
            a = (0.26 + 0.48 * j / 20) * L
            c = (0.26 + 0.48 * (j + 1) / 20) * L

            def edge(u):
                return 0.82 + 0.62 * max(0, 1 - abs((u / L - 0.50) / 0.24))

            vs = [
                _point(w, a, 0.13, z + height + 0.79),
                _point(w, c, 0.13, z + height + 0.79),
                _point(w, c, 0.13, z + height + edge(c)),
                _point(w, a, 0.13, z + height + edge(a)),
            ]
            back = [(x - 0.26 * w.nx, y - 0.26 * w.ny, h) for x, y, h in vs]
            if w.tx * w.ny - w.ty * w.nx > 0:
                vs.reverse()
                back.reverse()
            m.face(vs, C['dormRose'])
            m.face(back[::-1], C['dormRose'])
            for k in range(4):
                l = (k + 1) % 4
                if (
                    abs(vs[k][2] - vs[l][2]) < 0.20
                    and min(vs[k][2], vs[l][2]) > z + height + 0.80
                ):
                    m.face([vs[l], vs[k], back[k], back[l]], C['white'])
        for u in (L * 0.064, L * 0.936):
            w.box(m, u, -0.09, z + height + 1.0, L * 0.098, 0.30, 0.40, C['white'])


def _court_band(m, w, z, mat):
    # The east face of West 13's north band meets the solid gable.
    # Only the west end of this strip has an exposed cap.
    band = Mesh()
    w.box(band, w.length / 2, 0.02, z, w.length, 0.075, 0.10, mat)
    east_u = w.length if w.tx > 0 else 0
    for face in band.f:
        points = [band.v[i] for i in face]
        if any(abs(_uv(w, p)[0] - east_u) > 0.001 for p in points):
            m.face(points, mat)


def _crown(m, w, top, C):
    L = w.length
    # Shallow paired shoulders over the visible central bay, one continuous crown.
    for j in range(12):
        a, c = L * j / 12, L * (j + 1) / 12
        h0 = 0.81 + 0.94 * (1 - (2 * a / L - 1) ** 2)
        h1 = 0.81 + 0.94 * (1 - (2 * c / L - 1) ** 2)
        ring = [
            _point(w, a, -0.17, top + 0.79),
            _point(w, c, -0.17, top + 0.79),
            _point(w, c, -0.17, top + h1),
            _point(w, a, -0.17, top + h0),
        ]
        face = [
            _point(w, a, 0.07, top + 0.79),
            _point(w, c, 0.07, top + 0.79),
            _point(w, c, 0.07, top + h1),
            _point(w, a, 0.07, top + h0),
        ]
        m.face(ring, C['white'])
        m.face(face[::-1], C['white'])
        m.face([ring[3], ring[2], face[2], face[3]], C['white'])
        if j == 0:
            m.face([ring[0], ring[3], face[3], face[0]], C['white'])
        if j == 11:
            m.face([ring[1], face[1], face[2], ring[2]], C['white'])


def _clip_terminal(pts, w, span):
    # Clip continuous gallery slabs at the inner jamb, retaining the volume
    # of the adjacent bays. The new return closes the section at the cut.
    a, b = span
    cut = b if a == 0 else a
    distances = [(_uv(w, p)[0] - cut) * (1 if a == 0 else -1) for p in pts]
    if min(distances) >= -1e-7:
        return pts
    if max(distances) < 1e-7:
        return []
    polygon = []
    for j, p in enumerate(pts):
        q = pts[j - 1]
        dp = distances[j]
        dq = distances[j - 1]
        if (dp >= 0) != (dq >= 0):
            t = dq / (dq - dp)
            polygon.append(tuple(q[k] + t * (p[k] - q[k]) for k in range(3)))
        if dp >= 0:
            polygon.append(p)
    cleaned = []
    for p in polygon:
        if not cleaned or math.dist(p, cleaned[-1]) > 1e-7:
            cleaned.append(p)
    if len(cleaned) > 1 and math.dist(cleaned[0], cleaned[-1]) < 1e-7:
        cleaned.pop()
    return cleaned if len(cleaned) >= 3 else []


def _exterior(b, z, C, detail, number, selected, exterior, calibrated):
    height = b['height']
    roof = z + height
    levels = int(b['levels'])
    if number == 6:
        rim = [w for w, kind in selected if kind == 'curved-end']
        first, last = rim[0], rim[-1]
        end = _point(last, last.length, 0, 0)[:2]
        chord = Wall(end, (first.x, first.y), False)
        outline = [(w.x, w.y) for w in rim] + [end]
        # Keep the mapped end profile and open the upper spaces behind its
        # curved spandrels. The chord is the visible recessed backing plane.
        datum = z
        story = height / int(b['levels'])
        for level in range(int(b['levels'])):
            floor = datum + level * story
            _strip(
                exterior,
                chord,
                0,
                chord.length,
                0,
                floor,
                floor + story,
                C['dormConcreteLight'],
            )
            face = [(x, y, floor + 0.13) for x, y in reversed(outline)]
            exterior.face(face, C['white'])
            exterior.face([(x, y, floor) for x, y in outline], C['white'])
            for w in rim:
                _strip(
                    exterior,
                    w,
                    0,
                    w.length,
                    0,
                    floor,
                    floor + (0.9 if level else story),
                    C['dormRose'] if level < 2 else C['white'],
                )
                _strip(
                    exterior,
                    w,
                    0,
                    w.length,
                    0.004,
                    floor + 0.18,
                    floor + 0.29,
                    C['dormBlush'],
                )

    for w, kind in selected:
        end = finish_kind(number, w)
        if (
            kind == 'curved-end'
            or (number == 14 and end == 'court')
            or (number == 13 and end == 'brick-end')
        ):
            continue
        if kind == 'tower' and number in (9, 10, 11):
            _crown(exterior, w, roof, C)
            core(Surface(w, calibrated, z), height, levels, number, C, detail)
            continue
        if number == 15 and kind == 'balcony':
            count = round(w.length / 3.95)
            step = w.length / count
            broad = {2, 5, count - 5, count - 2}
            surface = Surface(w, calibrated, z)
            for level in range(2, levels):
                for i in range(count):
                    left = i * step + (0.34 if i in broad else 0.255)
                    right = (i + 1) * step - (
                        0.34 if i + 1 in broad else 0.16 if i + 1 == count else -0.005
                    )
                    screen(
                        surface,
                        left,
                        right,
                        level * (height / levels),
                        height / levels,
                        C,
                    )
        if end == 'gallery-end':
            segment = GallerySegment(w, terminal(w, b, number))
            _front(segment, w, kind, z, height, levels, number, C, detail, end)
            exterior.extend(segment)
        else:
            _front(exterior, w, kind, z, height, levels, number, C, detail, end)
    if number in (9, 10, 11):
        # Photographed dark fields flank the raised core, leaving the middle clear.
        for w, kind in selected:
            if kind != 'gallery':
                continue
            for row in range(3):
                depth = -2.4 - 3.1 * row
                width = w.length - 1.5
                w.box(
                    exterior,
                    w.length * 0.5,
                    depth,
                    roof + 0.44,
                    width,
                    1.65,
                    0.20,
                    C['dormCollector'],
                )
                w.box(
                    exterior,
                    w.length * 0.5,
                    depth + 0.82,
                    roof + 0.56,
                    width,
                    0.10,
                    0.08,
                    C['metal'],
                )
                for f in (0.04, 0.50, 0.96):
                    w.box(
                        exterior,
                        0.75 + width * f,
                        depth,
                        roof + 0.56,
                        0.10,
                        1.68,
                        0.08,
                        C['paleRoof'],
                    )
    if number == 15:
        w = next(w for w, kind in selected if kind == 'round')
        for center in (0.106, 0.894):
            radius = w.length * 0.060
            for i in range(10):
                a = -1 + 2 * i / 10
                c = -1 + 2 * (i + 1) / 10
                p = w.length * center
                _soffit(
                    exterior,
                    w,
                    [
                        (p + radius * a, -1.6),
                        (p + radius * c, -1.6),
                        (p + radius * c, 0.55 + 2.13 * math.sqrt(max(0, 1 - c * c))),
                        (p + radius * a, 0.55 + 2.13 * math.sqrt(max(0, 1 - a * a))),
                    ],
                    roof + 0.28,
                    0.13,
                    C['dormRose'],
                    sides=(True, i == 9, True, i == 0),
                )
    if number in (13, 14):
        for w in _edges(b):
            w.box(
                exterior,
                w.length / 2,
                0.11,
                roof + 0.72,
                w.length + 0.16,
                0.5,
                0.23,
                C['white'],
            )


class GallerySegment(Mesh):
    # Truncate slabs, backing and trim at the jamb of the solid terminal bay.
    def __init__(self, wall, span):
        super().__init__()
        self.wall = wall
        self.span = span

    def face(self, coords, mat, uvs=None):
        kept = _clip_terminal(coords, self.wall, self.span)
        if kept:
            super().face(kept, mat, uvs)


def _on_rebuilt_wall(w, center):
    u, d = _uv(w, center)
    return -0.04 < u < w.length + 0.04 and -0.20 < d < 1.43


def _retain(b, z, C, baseline, number, selected, targets):
    height = b['height']
    storey = height / b['levels']
    result = Mesh()
    result.ground_uv_bounds = baseline.ground_uv_bounds.copy()
    result.xy_uv_materials = baseline.xy_uv_materials.copy()
    j = 0
    for name, _, end in baseline.parts:
        part = Mesh()
        detail_part = name.startswith('04_')
        shell = name.startswith('01_')
        while j < len(baseline.f) and baseline.f[j][0] < end:
            face = baseline.f[j]
            mat = baseline.m[j]
            uvs = baseline.face_uvs.get(j)
            j += 1
            pts = [baseline.v[k] for k in face]
            if detail_part or shell:
                center = tuple(sum(p[k] for p in pts) / len(pts) for k in (0, 1))
                lo = min(p[2] for p in pts) - z
                hi = max(p[2] for p in pts) - z
                if detail_part or (len(pts) == 4 and hi - lo > height - 0.02):
                    if any(_on_rebuilt_wall(w, center) for w, _ in selected):
                        continue
                if _replaced(
                    pts, center, lo, hi, detail_part, mat, C, targets, storey, height
                ):
                    continue
                if (
                    shell
                    and number >= 6
                    and all(abs(p[2] - (z + height)) < 0.001 for p in pts)
                ):
                    mat = C['white' if number in (8, 13, 14) else 'dormCollector']
            part.face(pts, mat, uvs)
        if part.v:
            result.add_part(name, part)
    return result


def _replaced(pts, center, lo, hi, detail_part, mat, C, targets, storey, height):
    for w, kind in targets:
        if kind in ('gallery-end', 'base'):
            continue
        u, d = _uv(w, center)
        if u < -0.045 or u > w.length + 0.045 or d < -1.52 or d > 1.55:
            continue
        if kind == 'one-east':
            if (
                (detail_part or mat == C['glass'])
                and -0.015 <= d <= 0.11
                and 0.65 < u < w.length - 0.65
            ):
                return True
            continue
        if detail_part:
            if kind != 'one-west' and -0.22 < d < 1.48:
                return True
            continue
        us, ds = zip(*[_uv(w, p) for p in pts])
        onwall = (
            all(abs(v) < 0.0001 for v in ds) and max(us) - min(us) > w.length - 0.03
        )
        if onwall and (
            abs(lo) < 0.002 and abs(hi - storey) < 0.002
            if kind == 'one-west'
            else hi - lo > height - 0.02
        ):
            return True
    return False


def refine(b, z, C, detail, baseline):
    """Build the surveyed exterior on the ordinary campus mesh for this residence."""
    number = _NUMBERS[b['id']]
    if number <= 5:
        baseline = _custom_five(b, z, C, baseline, number)
        if number != 1:
            return baseline
    if number in (13, 14):
        C = court_palette(C)
    walls = _edges(b)
    selected = [(w, kind) for w in walls if (kind := _kind(number, w))]
    targets = [(w, kind) for w in walls if (kind := finish_kind(number, w))]
    result = _retain(b, z, C, baseline, number, selected, targets)
    exterior, trim, calibrated = Mesh(), Mesh(), Mesh()
    if number >= 6:
        _exterior(b, z, C, detail, number, selected, exterior, calibrated)
        result.add_part('按本楼照片重塑的外立面和屋面', exterior)
    finishes(trim, targets, b, z, number, C, detail)
    if trim.v:
        result.add_part('四向外观复核修饰', trim)
    if calibrated.v:
        result.add_part('实拍校准 · 北凸部窗与南阳台栏板', calibrated)
    return result
