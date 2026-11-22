"""Grade the connected materials/civil drives in the materials entrance frame."""

from bisect import bisect_right
from functools import lru_cache

from mathutils.bvhtree import BVHTree

from geometry import Mesh
from materials_north_road import split
from materials_northeast_stair import frame
from site_geometry import mesh_triangles

# The three panorama intersections put the civil annex stair foot only 0.22 m
# above the materials grass corner. Shift the connected civil building rigidly
# together with both existing stair-to-road meshes.
CIVIL = 'relation/12875606'
CIVIL_SHIFT = -2.88
CIVIL_PATHS = ('site-civil-main-front-connection', 'site-civil-annex-stair-connection')


def ramp(x, lo, hi):
    return min(1.0, max(0.0, (x - lo) / (hi - lo)))


def along(x, knots):
    i = max(0, min(len(knots) - 2, bisect_right(knots, (x, float('inf'))) - 1))
    (a, u), (b, v) = knots[i : i + 2]
    return u + (v - u) * ramp(x, a, b)


def mix(a, b, weight):
    return a + weight * (b - a)


# Relative elevations. The external north/south road passes between two
# building pads. Continue along the actual carriageway to both unchanged ends.
TRUNK = (
    (-161, 2.51),
    (-156, 2.86),
    (-148, 2.92),
    (-130, 3.08),
    (-115, 3.11),
    (-80, 3.16),
    (-55, 3.31),
    (-32, 3.48),
    (-23, 3.48),
    (0, 4.12),
    (24, 4.43),
    (40, 4.35),
    (45, 4.398),
    (54, 3.90),
)
W = (
    -161,
    -148,
    -130,
    -120,
    -115,
    -100,
    -84,
    -80,
    -73,
    -67,
    -65,
    -61,
    -59.7,
    -58,
    -57.85,
    -57.3,
    -57,
    -55.7,
    -54,
    -52,
    -51,
    -50,
    -47,
    -44,
    -40,
    -39,
    -37.35,
    -37.15,
    -36.85,
    -36,
    -35.5,
    -35,
    -33,
    -32.6,
    -32.48,
    -32,
    -31.9,
    -30.15,
    -30,
    -29.6,
    -28,
    -26.65,
    -25.65,
    -25.39,
    -23,
    -22,
    -20.3,
    -17,
    0,
    12,
    24,
    40,
    54,
    66,
)
D = (
    -132,
    -115,
    -95,
    -75,
    -63,
    -59.7,
    -59,
    -56,
    -52,
    -49,
    -48,
    -47.5,
    -46,
    -45.7,
    -42,
    -38,
    -35,
    -30,
    -26,
    -23,
    -21.8,
    -20.8,
    -19.75,
    -17,
    -14,
    -13.8,
    -12.35,
    -12.23,
    -11,
    -8.33,
    -8.21,
    -7.75,
    -6.7,
    -6,
    -5.3,
    -4.2,
    -4,
    -3.9,
    -2.52,
    0,
    4.7,
    5,
    12,
    23,
    36,
    38.9,
    40,
    40.55,
    43.5,
    45,
    45.3,
    54,
    70,
    80,
)


# Rigid support areas come from the existing footprints and the annex toe.
# Split at their boundaries so a large terrain triangle cannot tilt a sill.
PADS = (
    (-114, -60, -34.7, 23.5, CIVIL_SHIFT),
    (-72.55, -51.5, -0.5, 39.4, CIVIL_SHIFT),
    (-55, -34.65, 1.45, 39.4, CIVIL_SHIFT),
    (-51.6, -37.45, -4.96, 3, CIVIL_SHIFT),
    (-87, -57.12, -123, -59.35, 0),
    (-63.8, -46.85, 44.35, 79, 0),
    (-20.2, 43, -206, -61.2, 0),
)


# Extra cuts are restricted to faces meeting the pad, not full-campus grid lines.
def pad_shift(w, d, dz):
    for a, b, l, r, height in PADS:
        gap = max(a - w, w - b, l - d, d - r, 0.0)
        if gap < 0.85:
            dz = mix(height, dz, ramp(gap, 0, 0.85))
    return dz


def prepare(base, entrance, z, colors):
    point, local = frame(entrance, z)
    x0, y0, _ = point(W[-1], D[-1], 0)
    x1, y1, _ = point(W[0], D[0], 0)
    bounds = (x0 - 2, y0 - 2, x1 + 2, y1 + 2)

    def inside(pts):
        return (
            max(p[0] for p in pts) >= bounds[0]
            and min(p[0] for p in pts) <= bounds[2]
            and max(p[1] for p in pts) >= bounds[1]
            and min(p[1] for p in pts) <= bounds[3]
        )

    def tree(mesh, allowed=None):
        verts, faces = [], []
        for f, mat in zip(mesh.f, mesh.m):
            if allowed and mat not in allowed:
                continue
            pts = [mesh.v[i] for i in f]
            if inside(pts):
                start = len(verts)
                verts.extend(pts)
                faces.append(tuple(range(start, start + len(pts))))
        return BVHTree.FromPolygons(verts, faces)

    roads = base['roads']
    car = tree(
        roads, {colors[s] for s in ('road', 'asphalt', 'roadYellow', 'roadWhite')}
    )
    ground = tree(base['terrain'])
    road_skin = tree(roads)

    @lru_cache(maxsize=80000)
    def probe(t, w, d):
        for dw, dd in ((0, 0), (0.003, 0), (-0.003, 0), (0, 0.003), (0, -0.003)):
            p = t.ray_cast(point(w + dw, d + dd, 30), (0, 0, -1), 75)[0]
            if p is not None:
                return p.z - z
        return None

    @lru_cache(maxsize=70000)
    def street(w):
        # Transfer the central longitudinal datum to the complete road section.
        h = probe(car, w, -52)
        if h is None:
            h = probe(ground, w, -52)
        return along(w, TRUNK) - h if h is not None else 0

    @lru_cache(maxsize=65000)
    def lane_height(w, d):
        target = 2.437 + 0.0345 * max(0, -d - 19.75) + 0.018 * max(0, -w - 26.65)
        if d > -4:
            end = probe(car, min(-25.65, max(-29.5, w)), 30)
            if end is None and d > 4:
                # The outer station clips the kerb at D=30. Use the adjacent
                # asphalt rather than dropping the western grade reference.
                inner = probe(car, -29.3, 30)
                if inner is not None:
                    end = mix(target, inner, ramp(d, 4, 14))
            if end is not None:
                target = mix(target, end, ramp(d, -4, 30))
        if -33 < d < -19.75 and w > -25.65:
            apron = probe(car, min(-22.7, w), -20.5)
            if apron is not None:
                target += (
                    (apron - 2.463) * ramp(w, -25.65, -25.39) * ramp(d, -33, -20.5)
                )
        return target

    def offset(w, d, h, kind):
        # Constant across the civil footprint and original platforms. Across the
        # public street the flank tapers before neighbouring building footprints.
        north = ramp(w, -161, -116)
        south = 1 - ramp(w, -35.4, -29.6)
        west = 1 - ramp(d, 40, mix(78, 45, ramp(w, -73, -64) * (1 - ramp(w, -46, -40))))
        civil = CIVIL_SHIFT * north * south * west
        s = street(w) * ramp(w, -161, -148) * (1 - ramp(w, 40, 45))
        side = ramp(d, -59.7, -56)
        # Through street east of the civil bend: distribute the remaining
        # correction along the road, tapering laterally before either building.
        cross = ramp(w, -57.85, -57.3) * (1 - ramp(w, -50, -44))
        side = max(side, cross * ramp(d, -132, -56))
        # way/842784672 meets the east-west street at grade. Carry its
        # junction adjustment south along the path, clear of the road centre.
        footway = ramp(w, -57.85, -57.3) * (1 - ramp(w, -50, -10))
        side = max(side, footway * ramp(d, -66, -59.7) * ramp(d, -132, -56))
        trunk = s * side
        blend = 1 - ramp(d, -50, -33.5)
        dz = mix(civil, trunk, blend)
        full = (
            ramp(d, -57, -55.7)
            * (1 - ramp(d, -47.5, -45.6))
            * ramp(w, -161, -148)
            * (1 - ramp(w, 40, 45))
        )
        full *= ramp(w, -39, -32) * (1 - ramp(w, 14, 22))
        if full:
            surface = along(w, TRUNK) + 0.005 * (d + 52)
            if kind == 'terrain':
                surface -= 0.09
            ref = h
            if kind == 'curb':
                # Translate caps and risers by the same adjacent carriageway
                # correction. The inset stays within the asphalt edge.
                inward = 0.32 if d < -52 else -0.32
                ref = probe(car, w, d + inward)
                if ref is None:
                    ref = probe(car, w, d + 2 * inward)
            if ref is not None:
                dz = mix(dz, surface - ref, full)
        if w >= -25.39 and d >= -20.8:
            return 0.0
        # Within the two photographed approaches remove the previous convex
        # DEM ramp. Soil, shoulders, tile and carriageway have separate levels.
        east = ramp(d, -52, -49) * (1 - ramp(d, 28, 37))
        east *= ramp(w, -39, -36) * (1 - ramp(w, -22, -18))
        branch = ramp(w, -42, -39) * (1 - ramp(w, -26.65, -25.39))
        branch *= ramp(d, -28, -18) * (1 - ramp(d, -4, 12))
        weight = max(east, branch)
        weight *= 1 - ramp(-w, 36.2, 37.4) * (1 - ramp(-d, 8.65, 9.45))
        if weight:
            target = lane_height(w, d)
            # Keep the previously registered kerb height at the near lawn edge.
            if kind == 'terrain':
                target -= 0.082
            if kind == 'curb':
                target += 0.042
            # The old parking, grass rim and retaining wall form one assembly.
            if w >= -25.65:
                weight *= 1 - ramp(w, -25.65, -25.39) * ramp(d, -21.8, -20.8)
            if w >= -23:
                weight *= 1 - ramp(w, -23, -21.95) * ramp(d, -26, -21)
            # Use a common pavement reference on vertical kerb faces: a vertical
            # column must translate, never collapse its side faces onto the cap.
            if kind == 'curb':
                ref = probe(car, min(-22.7, max(-29.4, w)), d)
                if ref is None:
                    ref = probe(car, w, -10)
                if ref is not None:
                    h = ref
                    target -= 0.042
            dz = mix(dz, target - h, weight)
        # The western retained service lane already rises northwards. Distribute
        # its change on its own alignment instead of moving it with the side
        # of the civil pad. Its southern intersection keeps its original grade.
        west_axis = along(
            w,
            (
                (-108.2, 37.3),
                (-92.3, 34),
                (-83.8, 37.1),
                (-75.8, 40.4),
                (-66.7, 42.4),
                (-25.7, 41.7),
            ),
        )
        # At the T junction the narrow northbound arm opens onto the
        # east-west asphalt. Feather its adjustment along that carriageway.
        shoulder = 3.1 + 15 * ramp(w, -37, -31)
        west_lane = (
            (1 - ramp(abs(d - west_axis), 1.5, shoulder))
            * ramp(w, -103, -95)
            * (1 - ramp(w, -29, -25.7))
        )
        if d > west_axis and -37 < w < -25.7:
            west_lane *= 1 - ramp(w, -37, -31) * ramp(d, 46, 50)
        if west_lane:
            surface = along(
                w,
                (
                    (-103, 2.1),
                    (-95, 2.28),
                    (-84, 2.54),
                    (-67, 3.00),
                    (-48, 3.52),
                    (-34, 3.58),
                    (-25.7, 3.38),
                ),
            )
            if kind == 'terrain':
                surface -= 0.09
            dz = mix(dz, surface - h, west_lane)
        # Keep the southbound materials service turn and its retained
        # threshold profile through the junction with the west arm.
        dz *= 1 - ramp(w, -28.8, -26.1) * (1 - ramp(abs(d + 2.52), 1.4, 2.9))
        return pad_shift(w, d, dz)

    # Back-project the three-station mouth and grass corners on the fitted
    # road plane. The separate apron/planting-brick strip is south of this cut.
    def spur_edges(w):
        t = ramp(w, -35.5, -32.48)
        shift = ramp(w, -37.15, -35.5)
        return -12.23 - 0.62 * shift - 1.05 * t, -8.33 - 0.22 * shift + 0.83 * t

    def finish(w, d):
        # Former OSM junction returns overlap below the strip. Replace their
        # visible faces together rather than lifting two layers onto one plane.
        if -29.6 <= w < -28 and -14 < d < -6:
            return 'asphalt'
        if not (-37.15 < w < -29.6 and -49 < d < -3.9):
            return None
        if d < -46:
            return 'asphalt'
        left, right = spur_edges(w)
        if w > -32.48 or left < d < right:
            return 'asphalt'
        if min(abs(d - left), abs(d - right)) < 0.12 or -32.60 < w < -32.48:
            return 'curb'
        if w > -35.5:
            return 'pavingRed'
        return 'grass'

    @lru_cache(maxsize=9000)
    def retained_top(w, d):
        levels = []
        for surface, kind in ((ground, 'terrain'), (road_skin, 'road')):
            old = probe(surface, w, d)
            if old is not None:
                levels.append(old + offset(w, d, old, kind))
        return max(levels)

    def join_height(u, v, h):
        # The reconstructed grass and asphalt share a real boundary with a
        # separately-owned raised road contact at the annex. Match that upper
        # surface, including the original crossfall, for the last 1.5 m.
        if -37.15 - 1e-5 <= u < -35.5:
            target = retained_top(-37.151, round(v, 5))
            h = mix(target, h, ramp(u, -37.15, -35.5))
        if -49 - 1e-5 <= v < -48 and u < -29.6:
            h = mix(retained_top(round(u, 5), -49.001), h, ramp(v, -49, -48))
        if -5.3 < v <= -3.9 + 1e-5 and u < -29.6:
            h = mix(h, retained_top(round(u, 5), -3.899), ramp(v, -5.3, -3.9))
        return h

    added = Mesh()

    def edit(mesh, owner):
        new = Mesh()
        new.v = mesh.v.copy()
        ngons = Mesh()
        indices = []
        for i, face in enumerate(mesh.f):
            if len(face) > 3:
                pts = [mesh.v[j] for j in face]
                if inside(pts):
                    ngons.face(pts, 0)
                    indices.append(i)
        cuts = {}
        if ngons.f:
            for tri, j in mesh_triangles(ngons):
                cuts.setdefault(indices[j], []).append(
                    tuple(k - ngons.f[j][0] for k in tri)
                )
        for i, (face, mat) in enumerate(zip(mesh.f, mesh.m)):
            pts = [mesh.v[j] for j in face]
            uv = mesh.face_uvs.get(i)
            if not inside(pts):
                if uv:
                    new.face_uvs[len(new.f)] = uv
                new.f.append(face)
                new.m.append(mat)
                continue
            poly = [(*local(p), *(uv[j] if uv else ())) for j, p in enumerate(pts)]
            parts = [[poly[k] for k in tri] for tri in cuts[i]] if i in cuts else [poly]
            ws, ds = W, D
            wl, wh = min(q[0] for q in poly), max(q[0] for q in poly)
            dl, dh = min(q[1] for q in poly), max(q[1] for q in poly)
            if wh < -42 or wl > -18 or dh < -52 or dl > 37:
                ws = tuple(
                    i
                    for i in W
                    if i <= -40 or i >= -26.65 or i in (-37.15, -35.5, -32, -30, -29.6)
                )
                ds = tuple(i for i in D if i <= -30 or i >= 23)
            rigid = next(
                (
                    height
                    for a, b, l, r, height in PADS
                    if a <= wl <= wh <= b and l <= dl <= dh <= r
                ),
                None,
            )
            if rigid is not None and (owner == 'terrain' or mat != colors['road']):
                new.face([(x, y, hh + rigid) for x, y, hh in pts], mat, uv)
                continue
            if (
                (wl >= -25.39 and dl >= -20.8)
                or wh < W[0]
                or wl > 45
                or dh < D[0]
                or dl > D[-1]
            ):
                new.face(pts, mat, uv)
                continue
            # Stop the walkway runout before the international building pad.
            if wl < -10 and wh > -58 and dl < -66 < dh:
                ds = tuple(sorted((*ds, -66)))
            for a, b, l, r, _ in PADS:
                if wh < a - 1 or wl > b + 1 or dh < l - 1 or dl > r + 1:
                    continue
                ws = tuple(sorted(set((*ws, a - 0.85, a, b, b + 0.85))))
                ds = tuple(sorted(set((*ds, l - 0.85, l, r, r + 0.85))))
            # Existing triangles resolve the smooth outer runouts. Cut only at
            # profile breaks and material boundaries in the photographed region.
            for axis, stations in enumerate((ws, ds)):
                lo, hi = min(p[axis] for p in poly), max(p[axis] for p in poly)
                for cut in stations[
                    bisect_right(stations, lo + 1e-7) : bisect_right(
                        stations, hi - 1e-7
                    )
                ]:
                    parts = [
                        q
                        for poly0 in parts
                        for q in split(poly0, lambda v: v[axis] - cut)
                    ]
            if owner in ('roads', 'terrain') and any(
                -40 < p[0] < -28 for piece in parts for p in piece
            ):
                for edge, delta in ((0, -0.12), (0, 0), (1, 0), (1, 0.12)):
                    parts = [
                        part
                        for q in parts
                        for part in split(
                            q, lambda v: v[1] - spur_edges(v[0])[edge] - delta
                        )
                    ]
            for part in parts:
                w = sum(p[0] for p in part) / len(part)
                d = sum(p[1] for p in part) / len(part)
                projected = finish(w, d)
                if projected and owner == 'roads':
                    continue
                name = mat
                spur = -54 < w < -29.6 and -14 < d < -6
                if (
                    owner in ('roads', *CIVIL_PATHS)
                    and mat == colors['road']
                    and (spur or (-61 < w < -51 and -47 < d < -8.2))
                ):
                    name = colors['asphalt']
                if (
                    owner == 'roads'
                    and -29.6 < w < -22
                    and -46 < d < -4
                    and mat in (colors['roadWhite'], colors['roadYellow'])
                ):
                    name = colors['asphalt']
                # Reuse the actual top face for the sidewalk. The spur cuts
                # through it at grade; no coincident sheets across the junction.
                if spur and owner == 'roads' and mat == colors['road']:
                    if d < -12.35 or d > -8.21:
                        name = colors['grass']
                    elif d < -12.23 or d > -8.33:
                        name = colors['curb']
                if mat == colors['curb']:
                    kind = 'curb'
                elif owner == 'terrain':
                    kind = 'terrain'
                else:
                    kind = 'road'
                xyz = []
                for p in part:
                    u, v, h = p[:3]
                    dz = offset(round(u, 5), round(v, 5), h, kind)
                    xyz.append(point(u, v, h + dz))
                if projected and owner == 'terrain':
                    targetpts = []
                    for u, v, *_ in part:
                        # Use the same profile on both sides of the old road
                        # cut. Land on the pre-existing road exactly at its ends.
                        hh = lane_height(round(u, 5), round(v, 5))
                        l, r = spur_edges(u)
                        lip = (
                            0.035
                            * ramp(-u, 32.48, 32.60)
                            * max(ramp(l - v, 0, 0.12), ramp(v - r, 0, 0.12))
                        )
                        hh += (
                            lip
                            * ramp(v, -46, -45.7)
                            * (1 - ramp(v, -4.2, -3.9))
                            * ramp(u, -37.15, -36.85)
                        )
                        targetpts.append(point(u, v, join_height(u, v, hh)))
                    if projected != 'grass':
                        added.face(targetpts, colors[projected])
                        xyz = [(x, y, z0 - 0.055) for x, y, z0 in targetpts]
                    else:
                        xyz = targetpts
                    name = colors['grass']
                texture_uv = [p[3:] for p in part] if uv else None
                if (
                    mat in (colors['roadWhite'], colors['roadYellow'])
                    and name == colors['asphalt']
                ):
                    texture_uv = [(x / 4, y / 4) for x, y, _ in xyz]
                new.face(xyz, name, texture_uv)
        mesh.v, mesh.f, mesh.m, mesh.face_uvs = new.v, new.f, new.m, new.face_uvs

    for owner in ('terrain', 'roads', *CIVIL_PATHS):
        edit(base[owner], owner)
    base['roads'].extend(added)
    return tree(base['terrain']), local


def build_materials_civil_lanes(base, entrance, z, colors, trees):
    import bpy

    bed, local = prepare(base, entrance, z, colors)
    from vegetation_layout import tree_rotation, tree_scale

    for i, row in enumerate(trees):
        x, y = row[:2]
        # The original schematic tree fell on the now-located red walk.
        # Keep it on the adjacent grass; match the normal instance transform.
        if (x, y) == (-488.2, -864.5):
            y = row[1] = -862.6
        w, d, _ = local((x, y, 0))
        if not W[0] < w < W[-1] or not D[0] < d < D[-1]:
            continue
        hit = bed.ray_cast((x, y, 80), (0, 0, -1), 160)[0]
        if hit is not None:
            row[4] = round(hit.z, 6)
            obj = bpy.data.objects.get(f'树木示意-{i:04}')
            if obj is not None:
                obj.location = (x, y, row[4])
                if (x, y) == (-488.2, -862.6):
                    obj.scale = tree_scale(x, y, row[2])
                    obj.rotation_euler.z = tree_rotation(x, y)
