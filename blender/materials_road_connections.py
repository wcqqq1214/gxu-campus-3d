"""Tie the materials-college lawn lane into the east street and civil spur."""

from functools import lru_cache

from mathutils.bvhtree import BVHTree

from materials_north_road import warp


def eased_distance(t, end_fraction):
    """Constant grade between two short parabolic vertical curves."""
    t = min(1.0, max(0.0, t))
    if t < end_fraction:
        return t * t / (2 * end_fraction * (1 - end_fraction))
    if t > 1 - end_fraction:
        return 1 - eased_distance(1 - t, end_fraction)
    return (t - end_fraction / 2) / (1 - end_fraction)


def tie_materials_lane(terrain, roads, point, local, colors):
    # W points south and D west. Work on the already-finished road, keeping
    # its actual asphalt levels at both ends and the photo-located lawn corner.
    # The civil connections start at W=-37.4. Their paving is a separate owner.
    ws = (
        -37.35,
        -36.5,
        -34,
        -32,
        -30.55,
        -30.25,
        -30,
        -29.8,
        -29.6,
        -28,
        -26.65,
        -25.65,
        -25.45,
        -25.39,
        -23,
        -22.3,
        -22.13,
        -21.96,
        -21.65,
        -20.3,
    )
    ds = (
        -49,
        -46,
        -40,
        -33,
        -27,
        -23,
        -21,
        -19.75,
        -17,
        -15,
        -12,
        -9,
        -7.4,
        -6,
        -4,
        -2,
    )
    # The export inlays paint into cut-outs in the asphalt. Include that surface
    # when reading its level or an entire column can miss the carriageway.
    surfaces = {colors[key] for key in ('road', 'asphalt', 'roadWhite', 'roadYellow')}
    bounds = [
        point(w, d, 0) for w in (ws[0] - 2, ws[-1] + 2) for d in (ds[0] - 2, ds[-1] + 2)
    ]
    x0, x1 = min(p[0] for p in bounds), max(p[0] for p in bounds)
    y0, y1 = min(p[1] for p in bounds), max(p[1] for p in bounds)

    def tree(mesh, allowed=None):
        verts, faces = [], []
        for face, mat in zip(mesh.f, mesh.m):
            if allowed is not None and mat not in allowed:
                continue
            pts = [mesh.v[i] for i in face]
            if (
                all(p[0] < x0 for p in pts)
                or all(p[0] > x1 for p in pts)
                or all(p[1] < y0 for p in pts)
                or all(p[1] > y1 for p in pts)
            ):
                continue
            k = len(verts)
            verts.extend(pts)
            faces.append(tuple(range(k, k + len(pts))))
        return BVHTree.FromPolygons(verts, faces)

    paving, soil = tree(roads, surfaces), tree(terrain)
    kerb = tree(roads, {colors['curb']})

    @lru_cache(maxsize=12000)
    def level(surface, w, d):
        # Imported triangles can miss a ray exactly on their shared edge.
        # Opposite 2 mm offsets recover the same pavement plane in that case.
        def probe(a, b):
            pos = surface.ray_cast(point(a, b, 25), (0, 0, -1))[0]
            return pos.z if pos is not None else None

        z = probe(w, d)
        if z is not None:
            return z
        for radius in (0.002, 0.04):
            heights = [
                p
                for a, b in ((radius, 0), (-radius, 0), (0, radius), (0, -radius))
                if (p := probe(w + a, d + b)) is not None
            ]
            if heights:
                return sum(heights) / len(heights)
        return None

    def clamp(t):
        return min(1.0, max(0.0, t))

    lawn = level(paving, -25.65, -11.91)

    @lru_cache(maxsize=30000)
    def offsets(w, d):
        # Outside the two lanes use the adjoining strip's displacement, fading
        # across the verge. Existing material boundaries and road ownership remain
        # on the original mesh, including the road-to-paver seam.
        ew = min(-22.8, max(-29.45, w))
        bd = min(-9.0, max(-12.0, d))
        east_weight = clamp((w + 35.2) / 4.8) * clamp((-20.3 - w) / 1.55)
        branch_weight = clamp((d + 21) / 6) * clamp((-2 - d) / 4)
        old = level(paving, w, d)
        if old is None:
            old = level(kerb, w, d)
        reference = old if old is not None else level(paving, ew, d)
        mouth = lawn - 0.035 * clamp((-25.39 - w) / 0.06) + 0.016 * max(0, -25.65 - w)
        shift = 0.0
        # Both ends of the east lane follow the actual retained surface.
        if d < -19.75 and reference is not None:
            start = level(paving, ew, ds[0])
            end = level(paving, ew, -19.75)
            if end is None:
                end = lawn + max(0, w + 25.39) * 0.048
            end += clamp((-25.39 - w) / 0.26) * (mouth - end)
            mix = eased_distance((d - ds[0]) / (-19.75 - ds[0]), 0.10)
            target = start + mix * (end - start)
            shift = east_weight * (target - reference)
        elif w < -25.39 and reference is not None:
            shift = east_weight * clamp((-2 - d) / 4) * (mouth - reference)
        if w < -26.65 and branch_weight:
            # The annex approach at W=-37.4 fixes the upstream level. The
            # branch meets the calibrated carriageway at its lower end.
            north = level(paving, ws[0], bd)
            branch_old = old if old is not None else level(paving, w, bd)
            if branch_old is not None:
                t = (w - ws[0]) / (-26.65 - ws[0])
                target = north + eased_distance(t, 0.08) * (lawn - 0.019 - north)
                shift += branch_weight * (target - branch_old - shift)
        # Feather the fill below the road while preserving the existing slab
        # and the retained road/soil separation at every outer cut.
        bw = clamp((w - ws[0]) / 1.2) * clamp((ws[-1] - w) / 1.8)
        bw *= clamp((d - ds[0]) / 2.5) * clamp((ds[-1] - d) / 2)
        east_bed = east_weight * clamp((-19.75 - d) / 2)
        branch_bed = branch_weight * clamp((-26.65 - w) / 1.4)
        support = level(soil, w, d)
        fill = 0.0
        if old is not None and support is not None:
            fill = bw * max(east_bed, branch_bed) * max(0.0, old - support - 0.075)
        # Source crossfall may vary at the long outside boundaries. Zero the
        # final residual there rather than assuming level kerbs at other W/D.
        tie = clamp((d - ds[0]) / 1.5) * clamp((w - ws[0]) / 0.18)
        return tie * shift, tie * shift + fill

    # Keep existing triangles and UVs. Split across the profile stations so
    # a long DEM triangle cannot span a vertical curve or the narrow kerb lip.
    zero = [[0.0] * len(ds) for _ in ws]
    for layer, mesh in enumerate((roads, terrain)):
        first_vertex = len(mesh.v)
        warp(mesh, 0, point, local, ws, ds, zero)
        for i in range(first_vertex, len(mesh.v)):
            x, y, z = mesh.v[i]
            w, d, _ = local((x, y, z))
            if ws[0] < w < ws[-1] and ds[0] < d < ds[-1]:
                dz = offsets(round(w, 5), round(d, 5))[layer]
                mesh.v[i] = (x, y, z + dz)

    # The branch already has side faces. On the east lane the original strips
    # have an open outer edge; close only their daylighted sides to the soil.
    surface_tree = tree(roads)
    # The old DEM triangles cross both kerb footprints at a shallow angle.
    # Seat the narrow earth shoulder against the *finished* cap, continuing
    # its bed a short distance outside the edge before feathering into the bank.
    for i in range(first_vertex, len(terrain.v)):
        x, y, z = terrain.v[i]
        w, d, _ = local((x, y, z))
        if not -49 < d < -19.75:
            continue
        edge = -30 if w < -26 else -22
        edge += 0.00458 * (d + 20)  # two existing straight kerb runs in the site frame
        weight = clamp((0.65 - abs(w - edge)) / 0.3)
        if weight:
            inward = 1 if w < -26 else -1
            probe_w = edge + inward * max(0.045, (w - edge) * inward)
            top = level(surface_tree, probe_w, d)
            if top is not None:
                weight *= clamp((d + 49) / 0.7) * clamp((-19.75 - d) / 0.7)
                bed = min(top - 0.065, max(z, top - 0.115))
                terrain.v[i] = (x, y, z + weight * (bed - z))
    finished_soil = tree(terrain)
    seen = set()
    sides = []
    for face, mat in zip(roads.f, roads.m):
        if mat != colors['curb']:
            continue
        for ia, ib in zip(face, (*face[1:], face[0])):
            a, b = roads.v[ia], roads.v[ib]
            wa, da, _ = local(a)
            wb, db, _ = local(b)
            w, d = (wa + wb) / 2, (da + db) / 2
            if (
                not -49 < d < -19.75
                or abs(da - db) < 0.0002
                or abs(wa - wb) > 0.02 * abs(da - db)
            ):
                continue
            if -30.4 < w < -29.65:
                outside = -1
            elif -22.3 < w < -21.7:
                outside = 1
            else:
                continue

            def hit(dw):
                return surface_tree.ray_cast(point(w + dw, d, 25), (0, 0, -1))[0]

            if hit(outside * 0.008) is not None or hit(-outside * 0.008) is None:
                continue
            key = tuple(
                sorted(((round(wa, 4), round(da, 4)), (round(wb, 4), round(db, 4))))
            )
            if key in seen:
                continue
            floor_a = level(finished_soil, wa, da)
            floor_b = level(finished_soil, wb, db)
            if floor_a is None or floor_b is None:
                continue
            za = min(a[2], floor_a - 0.015)
            zb = min(b[2], floor_b - 0.015)
            if max(a[2] - za, b[2] - zb) < 0.001:
                continue
            side = [a, b, (b[0], b[1], zb), (a[0], a[1], za)]
            if (db - da) * outside < 0:
                side.reverse()
            sides.append(side)
            seen.add(key)
    for side in sides:
        roads.face(side, colors['curb'])
