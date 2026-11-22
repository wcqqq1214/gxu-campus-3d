"""First visible bay of the materials east-side passage, in entry W/D coordinates."""

from geometry import Mesh

# The left strip next to the east pier carries the upper stair exit. The
# narrower continuation beyond the mouth stays clear of the descending flight.
CUTS = [
    (-16.40, -12.82, -8.415, -0.29),
    (-12.82, -9.42, -7.49, -5.44),
]


def open_mouth(mesh, point, local, first_ground):
    """Cut the superseded north terrace end, including its guard and solid fascia."""
    result = Mesh()
    for i, (f, m) in enumerate(zip(mesh.f, mesh.m)):
        pts = [mesh.v[k] for k in f]
        uvs = mesh.face_uvs.get(i)
        poly = [(*local(p), *(uvs[k] if uvs else ())) for k, p in enumerate(pts)]
        remaining = [poly]
        for lo, hi, left, right in CUTS:
            # Include the full overhanging coping and rail of the superseded
            # terrace box, but preserve the parking finish at the rear edge.
            if i < first_ground and lo == -16.40:
                left, right = -8.61, -0.12
            if (
                min(p[0] for p in poly) > hi
                or max(p[0] for p in poly) < lo
                or min(p[1] for p in poly) > right
                or max(p[1] for p in poly) < left
            ):
                continue
            # Clip vertical faces as well as horizontal caps; the old shell
            # otherwise leaves a free-standing wall across the mouth.
            rest = []
            for part in remaining:
                inside = part
                for axis, edge, sign in [
                    (0, lo, 1),
                    (0, hi, -1),
                    (1, left, 1),
                    (1, right, -1),
                ]:
                    if not inside:
                        break
                    vals = [(p[axis] - edge) * sign for p in inside]
                    if max(vals) < -1e-8:
                        rest.append(inside)
                        inside = []
                        break
                    if min(vals) >= -1e-8:
                        continue
                    a = []
                    b = []
                    for k, p in enumerate(inside):
                        q = inside[(k + 1) % len(inside)]
                        da, db = vals[k], vals[(k + 1) % len(inside)]
                        if da >= -1e-8:
                            a.append(p)
                        if da <= 1e-8:
                            b.append(p)
                        if da * db < -1e-16:
                            t = da / (da - db)
                            v = tuple(x + (y - x) * t for x, y in zip(p, q))
                            a.append(v)
                            b.append(v)
                    if len(b) >= 3:
                        rest.append(b)
                    inside = a
            remaining = rest
        if len(remaining) == 1 and remaining[0] is poly:
            result.face(pts, m, mesh.face_uvs.get(i))
        else:
            for p in remaining:
                result.face(
                    [point(*v[:3]) for v in p], m, [v[3:] for v in p] if uvs else None
                )
    return result


def approach_height(old, w, d):
    if w < -16:
        return old(w, d)
    h = old(-16.00001, d)
    t = max(0, min(1, (w + 16) / 3.18))
    return h + t * (3.08 - h)


def passage(mesh, bed, point, old, box, C):
    # Inside front of the left pier and the soffit come from three stations.
    def approach(w, d):
        return approach_height(old, w, d)

    def plane(a, b, left, right, mat):
        ring = [(a, left), (a, right), (b, right), (b, left)]
        pts = [point(w, d, approach(w, d)) for w, d in ring]
        for ids in [(0, 1, 2), (0, 2, 3)]:
            face = [pts[k] for k in ids]
            mesh.face(face, C[mat], [(ring[k][0] / 2.6, ring[k][1] / 2.6) for k in ids])
            bed.face(face, C['grass'])
        # Fill below the approach into the native subgrade. The top and
        # adjoining cells share edges; side skins are only at the perimeter.
        for k, (w, d) in enumerate(ring):
            ww, dd = ring[(k + 1) % 4]
            if (w == ww and w in (-9.42, -16.4)) or (
                d == dd and d in (-8.415, -8.4, -0.3, -7.49, -5.44)
            ):
                mesh.face(
                    [
                        point(w, d, approach(w, d)),
                        point(ww, dd, approach(ww, dd)),
                        point(ww, dd, -0.30),
                        point(w, d, -0.30),
                    ],
                    C['wallStone'],
                )

    for a, b, left, right in [
        (-16.4, -16, -8.415, -0.3),
        (-16, -12.82, -8.4, -0.3),
        (-12.82, -9.42, -7.49, -5.44),
    ]:
        ds = sorted(
            {left, right, *[v for v in (-7.49, -5.44, -3.9, -2.14) if left < v < right]}
        )
        for l, r in zip(ds, ds[1:]):
            plane(a, b, l, r, 'asphalt' if l >= -7.49 and r <= -3.9 else 'grass')
    # Retaining faces along the retained raised strip and at the end of the
    # documented first bay. They join the actual floor to the 4 m upper walk.
    for a, b in [
        ((-13.05, -8.40), (-12.82, -8.40)),
        ((-12.82, -8.40), (-12.82, -7.49)),
        ((-12.82, -7.49), (-9.42, -7.49)),
        ((-9.42, -7.49), (-9.42, -5.44)),
        ((-9.42, -5.44), (-12.82, -5.44)),
    ]:
        mesh.face(
            [
                point(*a, approach(*a) - 0.05),
                point(*b, approach(*b) - 0.05),
                point(*b, 4.0),
                point(*a, 4.0),
            ],
            C['wallStone'],
        )
    # Two jambs and a real soffit produce shadow without a black front plane.
    underside = 6.45
    box(-10.91, -5.47, underside + 0.22, 4.06, 7.79, 0.44, 'gateStone')
    for w in (-12.54, -9.53):
        for d in (-8.91, -1.80):
            bottom = 2.60 if d < -8 else 1.25
            box(
                w,
                d,
                (bottom + underside) / 2,
                0.68,
                0.74,
                underside - bottom,
                'gateStone',
            )
    # Shade the photographed return on the west (right) side of the entrance.
    box(-11.04, -1.70, 4.32, 3.8, 0.36, 4.27, 'slate')
    # Thin top railing along the front edge of the upper gallery.
    from entry_guardrails import guard

    guard(mesh, point, box, C, -12.78, -8.9, -12.78, -1.75, 6.89, 6.89)
