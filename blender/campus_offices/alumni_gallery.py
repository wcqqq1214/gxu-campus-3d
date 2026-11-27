"""The mapped SW notch is a corner loggia in the independent 078° and 079° views."""

from mathutils import Vector
from mathutils.geometry import tessellate_polygon

from geometry import Mesh

from .alumni_walls import Wall
from .mesh_parts import remove_faces


def rung(part, tag, ring, height):
    v = [Vector((*p, 0)) for p in ring]
    ids = []
    for a, b, c in tessellate_polygon([v]):
        if (v[b] - v[a]).cross(v[c] - v[a]).z < 0:
            b, c = c, b
        ids.extend([a, b, c])
    return {
        **part,
        'id': tag,
        'height': height,
        'levels': round(height / 3.3),
        'polygons': [[ring + [ring[0]]]],
        'triangles': [ids],
        'parapetEdges': [],
    }


def west_form(b):
    f = b['form']
    p = next(x for x in f['parts'] if x['id'] == 'west-service')
    r = p['polygons'][0][0]
    cut = [
        r[6][0],
        r[8][1] + (r[9][1] - r[8][1]) * (r[6][0] - r[8][0]) / (r[9][0] - r[8][0]),
    ]
    inner = [r[4][0], r[6][1] - 0.008]
    parts = [s for s in f['parts'] if s is not p]
    parts.extend(
        [
            rung(p, 'west-service', r[6:9] + [cut], 13.2),
            rung(p, 'west6a-gallery-back', r[:5] + [inner, r[6], cut, r[9]], 16.5),
        ]
    )
    faces = []
    for fac in f['facades']:
        if fac['part'] != 'west-service':
            faces.append(fac)
            continue
        e = fac['edge']
        if e in (15, 16):
            continue
        if e == 19:
            faces.extend(
                [
                    {**fac, 'start': r[8], 'end': cut, 'levels': 4, 'height': 13.2},
                    {
                        **fac,
                        'start': cut,
                        'end': r[9],
                        'part': 'west6a-gallery-back',
                        'levels': 5,
                        'height': 16.5,
                    },
                ]
            )
            continue
        high = e in (0, 1, 13, 14)
        faces.append(
            {
                **fac,
                'height': 16.5 if high else 13.2,
                'levels': 5 if high else 4,
                'part': 'west6a-gallery-back' if high else 'west-service',
                'rule': {**fac['rule'], 'windows': False}
                if e in (14, 17)
                else fac['rule'],
            }
        )
    return {**b, 'form': {**f, 'parts': parts, 'facades': faces, 'entrances': []}}


def add_gallery(mesh, z, M, detail, building, C):
    x0, x1, y0, y1 = 2.442, 9.715, -627.447, -622.357

    def inside_walls(pts, mat):
        xs, ys, hs = zip(*pts)
        l, r = min(xs), max(xs)
        a, b = min(ys), max(ys)
        # Remove both original inner wall surfaces at the notch and the generic
        # window boxes/sills of the adjoining south and west returns.
        if (
            l >= -18.44
            and r <= x0 + 0.10
            and a >= y1 - 2.40
            and b <= y1 + 0.083
            and max(hs) < z + 13.21
        ):
            return True
        if l >= x0 - 0.04 and r <= x1 + 0.04 and a >= y1 - 0.055 and b <= y1 + 0.055:
            return True
        if l >= x1 - 0.045 and r <= x1 + 0.045 and a >= y0 - 0.025 and b <= y1 + 0.035:
            return True
        if l >= x1 - 0.035 and r <= x1 + 0.035 and a >= -630.79 and b <= y0 + 0.05:
            return True
        return (
            l >= x1 - 1.60
            and r <= x1 + 0.08
            and a >= -630.79
            and b <= y0 + 0.05
            and max(hs) - min(hs) < 3.15
        )

    remove_faces(mesh, inside_walls)
    # Through-height solid shoulder beside the recessed gallery (both stations).
    shoulder = Wall((9.705, -630.773), (x1, y0), (-1, 0), z, M, detail)
    shoulder.build(mesh, 16.5, '西南廊侧无窗端墙', fascia=False)
    west = Wall((-18.404, -622.334), (x0, y1), (0, -1), z, M, detail)
    for j, x in enumerate((-17.55, -13.38, -9.25, -5.23, -1.10)):
        for floor in range(4):
            lo = 1.11 + 3.12 * floor
            west.aperture(
                x - west.start[0],
                1.36,
                lo,
                lo + 1.91,
                'window',
                1 if (j, floor) in ((3, 2), (4, 1)) else 0,
            )
            if floor:
                west.aperture(x - west.start[0], 0.24, lo - 0.48, lo - 0.31, 'vent')
    west.build(mesh, 13.2, '西南廊外四层翼墙')
    s = Mesh()
    # Distinct deck, edge and soffit on one closed slab, with no coplanar layers.
    for h in (0.11, 3.30, 6.60, 9.90, 13.20, 16.50):
        corners = [(x0 - 0.10, y0 - 0.10), (x1, y0 - 0.10), (x1, y1), (x0 - 0.10, y1)]
        lower = [(x, y, z + h - 0.17) for x, y in corners]
        upper = [(x, y, z + h) for x, y in corners]
        s.face(lower[::-1], M['soffit'])
        s.face(upper, M['deck'])
        for i in range(4):
            j = (i + 1) % 4
            s.face([lower[i], lower[j], upper[j], upper[i]], M['sill'])
    # The masonry core projects into the notch, giving two covered passages
    # around a right-angled back wall. Passage widths are photo estimates.
    cx, cy = 4.88, -624.68
    for a, b, n, doors in [
        ((x0, y1), (cx, y1), (0, -1), []),
        ((cx, cy), (cx, y1), (-1, 0), [(1, 1.24), (2, 1.24)]),
        ((cx, cy), (x1, cy), (0, -1), [(1, 2.73), (2, 2.73)]),
        ((x1, y0), (x1, cy), (-1, 0), []),
    ]:
        wall = Wall(a, b, n, z, M, detail)
        L = wall.length
        for floor in range(5):
            lo = 3.30 * floor + 0.006
            hi = 3.3 * (floor + 1) - 0.17
            cuts = [pos for level, pos in doors if level == floor]
            if not cuts:
                wall.panel(s, 0, L, lo, hi, 0, 'gallery lime')
                continue
            mid = cuts[0]
            l, r = mid - 0.45, mid + 0.45
            top = lo + 2.06
            wall.panel(s, 0, l, lo, hi, 0, 'gallery lime')
            wall.panel(s, r, L, lo, hi, 0, 'gallery lime')
            wall.panel(s, l, r, top, hi, 0, 'gallery lime')
            for (u, h), (v, k) in [
                ((l, lo), (r, lo)),
                ((r, lo), (r, top)),
                ((r, top), (l, top)),
                ((l, top), (l, lo)),
            ]:
                wall.face(
                    s, [(u, 0, h), (v, 0, k), (v, -0.29, k), (u, -0.29, h)], 'jamb'
                )
            wall.panel(s, l, r, lo, top, -0.29, 'dark')
    for j in range(1, 5):
        h0 = j * 3.30 + 0.025
        h1 = (j + 1) * 3.30 - 0.17
        for x, y, w, d in [
            (x0 + 0.23, y0 + 0.21, 0.46, 0.46),
            (x1 - 0.22, y0 + 0.18, 0.44, 0.43),
            (x0 + 0.15, y1 - 0.68, 0.39, 1.36),
        ]:
            s.box(x, y, z + (h0 + h1) / 2, w, d, h1 - h0, M['plaster'])
    # Concealed top of the enclosed corner; the outer roof already covers it.
    for tag, a, b, n in [
        ('西', (x0, y0), (x0, y1), (-1, 0)),
        ('南', (x0, y0), (x1, y0), (0, -1)),
    ]:
        wall = Wall(a, b, n, z, M, detail)
        count = 2 if tag == '西' else 3
        for j in range(count):
            u = (j + 0.5) * wall.length / count
            if tag == '南' and j == 0:
                wall.aperture(u, 1.04, 0.10, 2.36, 'door')
            else:
                wall.aperture(u, wall.length / count - 0.29, 0.91, 2.91, 'screen')
        wall.build(mesh, 3.22, '西廊首层' + tag, entry=(0, wall.length), fascia=False)
        for level in (3.3, 6.6, 9.9, 13.2):
            for left, right in [(0.46, wall.length - (1.36 if tag == '西' else 0.44))]:
                for h, t in [(level + 0.12, 0.16), (level + 0.87, 0.11)]:
                    wall.box(s, left, right, h, h + t, -0.19, 0.03, 'cream')
                count = (
                    max(2, round((right - left) / 0.34))
                    if detail
                    else max(2, round((right - left) / 0.54))
                )
                for j in range(count):
                    u = left + (j + 0.5) * (right - left) / count
                    wall.box(
                        s,
                        u - 0.058,
                        u + 0.058,
                        level + 0.28,
                        level + 0.87,
                        -0.14,
                        -0.027,
                        'cream',
                    )
                    if detail:
                        wall.box(
                            s,
                            u - 0.087,
                            u + 0.087,
                            level + 0.28,
                            level + 0.37,
                            -0.151,
                            -0.018,
                            'cream',
                        )
    mesh.add_part('西南转角｜敞廊楼板、方柱和栏杆', s)

    # The earlier photo-overlay generator culls by face centre and can remove
    # a nonvertical triangle in this newly split wing. Restore missing cap
    # triangles from the authoritative part rings; never overlay an existing cap.
    def signature(pts):
        return tuple(sorted(tuple(round(v, 4) for v in pt) for pt in pts))

    present = {
        signature([mesh.v[i] for i in face])
        for face, mat in zip(mesh.f, mesh.m)
        if mat == C['paleRoof']
    }
    cap = Mesh()
    for part in building['form']['parts']:
        if part['id'] not in ('west-service', 'west6a-gallery-back'):
            continue
        ring = part['polygons'][0][0]
        idx = part['triangles'][0]
        height = z + part['height']
        for i in range(0, len(idx), 3):
            pts = [(*ring[k], height) for k in idx[i : i + 3]]
            if signature(pts) not in present:
                cap.face(pts, C['paleRoof'])
    if cap.f:
        mesh.add_part('西南廊｜闭合屋面', cap)
