"""Local displacement of the existing north road, kerbs and subgrade at materials.

Translate each vertical column together. Split at the same survey-frame stations
on all owners so the old carriageway thickness, markings and side faces survive.
"""

from bisect import bisect_right

from geometry import Mesh

# The opposite college begins at W=-35.8. End the correction on this side.
W = (-35.2, -34, -32.5, -31, -29.5, -28, -26.2, -25.39, -24, -22.4, -21.5, -20.18)
D = (-47, -38, -33, -28, -23, -20, -17, -14.47, -11.9125, -8.4, -6, -4, 0, 4, 10, 16)
# Heights read from the 01:35 north road at the street-side kerb, in the
# building's local vertical datum. The median photo difference is -0.251 m.
RIM = (
    (-26, 6.438),
    (-20, 5.647),
    (-17, 5.316),
    (-14.47, 4.996),
    (-11.9125, 4.765),
    (-8.4, 4.405),
    (-6, 4.09),
    (-4, 3.912),
    (0, 3.506),
)


def smooth(value):
    t = min(1, max(0, value))
    return t * t * (3 - 2 * t)


def correction(w, d):
    north = smooth((w - W[0]) / 7.2)
    south = smooth((W[-1] - w) / 3.82)
    lateral = smooth((d - D[0]) / 30) * smooth((D[-1] - d) / 22)
    # Narrow the adjustment as it enters the parking strip. This keeps the
    # calibrated joins behind the building and its east shoulder unchanged.
    near = smooth((w + 25.39) / 3.39)
    inside = smooth((d + 20) / 3) * smooth((-4 - d) / 2)
    weight = north * south * lateral * (1 - near + near * inside)
    if not weight:
        return 0.0
    x = max(RIM[0][0], min(RIM[-1][0], d))
    i = next(i for i in range(len(RIM) - 1) if RIM[i + 1][0] >= x)
    (l, a), (r, b) = RIM[i : i + 2]
    original = a + (b - a) * (x - l) / (r - l)
    # The road falls toward the entrance before the outdoor carpet begins.
    street_rise = 0.105 * max(-1.5, min(3, -25.39 - w))
    return weight * (2.459 - original - street_rise)


DELTA = tuple(tuple(correction(w, d) for d in D) for w in W)


def displacement(w, d, ws, ds, levels):
    if w <= ws[0] or w >= ws[-1] or d <= ds[0] or d >= ds[-1]:
        return 0.0
    i, j = bisect_right(ws, w) - 1, bisect_right(ds, d) - 1
    u = (w - ws[i]) / (ws[i + 1] - ws[i])
    v = (d - ds[j]) / (ds[j + 1] - ds[j])
    a, b, c, e = levels[i][j], levels[i + 1][j], levels[i + 1][j + 1], levels[i][j + 1]
    return a + u * (b - a) + v * (c - b) if u >= v else a + u * (c - e) + v * (e - a)


def split(poly, signed):
    """Split in 3D, including vertical kerbs. Interpolate every UV corner."""
    ds = [signed(p) for p in poly]
    if min(ds) >= -1e-9 or max(ds) <= 1e-9:
        return [poly]
    lo, hi = [], []
    for i, p in enumerate(poly):
        j = (i + 1) % len(poly)
        a, b = ds[i], ds[j]
        if a <= 1e-9:
            lo.append(p)
        if a >= -1e-9:
            hi.append(p)
        if a < -1e-9 and b > 1e-9 or a > 1e-9 and b < -1e-9:
            t = a / (a - b)
            q = tuple(x + (y - x) * t for x, y in zip(p, poly[j]))
            lo.append(q)
            hi.append(q)
    return [p for p in (lo, hi) if len(p) >= 3]


def lower_north_street(mesh, first, point, local):
    warp(mesh, first, point, local, W, D, DELTA)


def warp(mesh, first, point, local, ws, ds, levels):
    bounds = [point(w, d, 0) for w in (ws[0], ws[-1]) for d in (ds[0], ds[-1])]
    xmin, xmax = min(p[0] for p in bounds), max(p[0] for p in bounds)
    ymin, ymax = min(p[1] for p in bounds), max(p[1] for p in bounds)
    kept = []
    mats = []
    uvs = {}
    new = Mesh()
    for idx, (face, mat) in enumerate(zip(mesh.f, mesh.m)):
        pts = [mesh.v[k] for k in face]
        uv = mesh.face_uvs.get(idx)
        if idx >= first and not (
            all(p[0] < xmin for p in pts)
            or all(p[0] > xmax for p in pts)
            or all(p[1] < ymin for p in pts)
            or all(p[1] > ymax for p in pts)
        ):
            polygon = [(*local(p), *(uv[i] if uv else ())) for i, p in enumerate(pts)]
            parts = [polygon]
            for axis, stations in [(0, ws), (1, ds)]:
                lo, hi = min(p[axis] for p in polygon), max(p[axis] for p in polygon)
                for cut in stations:
                    if lo < cut < hi:
                        parts = [
                            q
                            for part in parts
                            for q in split(part, lambda p: p[axis] - cut)
                        ]
            for part in parts:
                w = sum(p[0] for p in part) / len(part)
                d = sum(p[1] for p in part) / len(part)
                triangles = [part]
                if ws[0] < w < ws[-1] and ds[0] < d < ds[-1]:
                    i = bisect_right(ws, w) - 1
                    j = bisect_right(ds, d) - 1
                    triangles = split(
                        part,
                        lambda p: (
                            (p[0] - ws[i]) / (ws[i + 1] - ws[i])
                            - (p[1] - ds[j]) / (ds[j + 1] - ds[j])
                        ),
                    )
                for tri in triangles:
                    new.face(
                        [
                            point(
                                p[0],
                                p[1],
                                p[2] + displacement(p[0], p[1], ws, ds, levels),
                            )
                            for p in tri
                        ],
                        mat,
                        [p[3:] for p in tri] if uv else None,
                    )
            continue
        if uv:
            uvs[len(kept)] = uv
        kept.append(face)
        mats.append(mat)
    mesh.f, mesh.m, mesh.face_uvs = kept, mats, uvs
    mesh.extend(new)


def bed_north_road(terrain, roads, point, local):
    """Support the lowered carriageway and feather its fill into the old shoulder."""
    from mathutils.bvhtree import BVHTree

    ws = (
        -32.8,
        -31.8,
        -30.8,
        -30,
        -29.3,
        -28.7,
        -28.1,
        -27.5,
        -27.1,
        -26.6,
        -26.1,
        -25.39,
        -24.7,
        -24.1,
        -23.5,
    )
    ds = tuple(
        sorted(
            {
                -39,
                -36,
                -33,
                -30,
                -28,
                -26,
                -24,
                -22,
                -20,
                -19,
                -17,
                -14.47,
                -12.45,
                -11.9125,
                -10,
                -8.4,
                -7.47,
                -6,
                -4,
                -2,
                0,
                2,
                5,
                9,
            }
        )
    )
    bounds = [
        point(w, d, 0) for w in (ws[0] - 1, ws[-1] + 1) for d in (ds[0] - 1, ds[-1] + 1)
    ]
    xmin, xmax = min(p[0] for p in bounds), max(p[0] for p in bounds)
    ymin, ymax = min(p[1] for p in bounds), max(p[1] for p in bounds)

    def sampler(source):
        vs = []
        fs = []
        for face in source.f:
            pts = [source.v[i] for i in face]
            if (
                all(p[0] < xmin for p in pts)
                or all(p[0] > xmax for p in pts)
                or all(p[1] < ymin for p in pts)
                or all(p[1] > ymax for p in pts)
            ):
                continue
            k = len(vs)
            vs.extend(pts)
            fs.append(tuple(range(k, k + len(pts))))
        return BVHTree.FromPolygons(vs, fs)

    street, ground = sampler(roads), sampler(terrain)

    def gap(w, d):
        weight = (
            smooth((w - ws[0]) / 3.5)
            * smooth((ws[-1] - w) / 1.7)
            * smooth((d - ds[0]) / 15)
            * smooth((ds[-1] - d) / 11)
        )
        if not weight:
            return 0
        # Continue the measured bedding correction beneath the outside
        # verge if the original road terminates between two grid stations.
        for station in (w, min(-25.39, max(-28.7, w))):
            start = point(station, d, 35)
            direction = (0, 0, -1)
            road = street.ray_cast(start, direction)[0]
            soil = ground.ray_cast(start, direction)[0]
            if road is not None and soil is not None:
                return weight * max(0, road.z - 0.085 - soil.z)
        return 0

    levels = [[gap(w, d) for d in ds] for w in ws]
    warp(terrain, 0, point, local, ws, ds, levels)
