"""Seat the shared court of West 22 and West 23 and its lower east path."""

from shore_geometry import bounds, overlaps

# Inner limits in campus metres. The plane rises outwards at the given slope
# until it meets the original surface. Neighbouring footprints keep their grade.
COURT = (-12.6, -899.5, 129.6, -866.0, 0.45, 0.85)
EAST_PATH = (125.0, -898.7, 134.2, -887.8, -0.76, 0.80)
EAST_APPROACH = (130.9, -905.0, 136.0, -891.0, -0.76, 0.75)


WEST23_COURT = (-11.8, -917.6, 126.2, -899.7, 0.39, 0.85)


def split(poly, distance):
    inside, outside = [], []
    for a, b in zip(poly[-1:] + poly[:-1], poly):
        da, db = distance(a), distance(b)
        if da * db < 0:
            t = da / (da - db)
            cross = tuple(x + (y - x) * t for x, y in zip(a, b))
            inside.append(cross)
            outside.append(cross)
        if db >= 0:
            inside.append(b)
        if db <= 0:
            outside.append(b)
    return inside, outside


def bed_surface(mesh, is_road, cuts=(COURT, EAST_PATH, EAST_APPROACH, WEST23_COURT)):
    from geometry import MATERIALS, Mesh

    result = Mesh()
    result.xy_uv_materials = mesh.xy_uv_materials.copy()
    result.ground_uv_bounds = list(mesh.ground_uv_bounds)
    for i, face in enumerate(mesh.f):
        points = [mesh.v[k] for k in face]
        if not overlaps(bounds(points), (-22, -928, 149, -856)):
            result.face(points, mesh.m[i], mesh.face_uvs.get(i))
            continue
        uvs = mesh.face_uvs.get(i) or [(x / 4, y / 4) for x, y, z in points]
        parts = [[(*pt, *uv) for pt, uv in zip(points, uvs)]]
        for left, south, right, north, height, slope in cuts:
            # Keep footpaths above the carriageway at crossings after grading.
            clearance = 0.022 if is_road and MATERIALS[mesh.m[i]].name == 'path' else 0
            h = height + clearance - (0 if is_road else 0.045)
            planes = [
                (0, 0, h),
                (-slope, 0, h + slope * left),
                (slope, 0, h - slope * right),
                (0, -slope, h + slope * south),
                (0, slope, h - slope * north),
            ]
            remaining = []
            for poly in parts:

                def altitude(plane, p):
                    return plane[0] * p[0] + plane[1] * p[1] + plane[2]

                # A whole triangle below any one plane lies outside the cut.
                if any(
                    all(p[2] <= altitude(q, p) + 1e-7 for p in poly) for q in planes
                ):
                    remaining.append(poly)
                    continue
                clipped = poly
                for q in planes:
                    clipped, outside = split(clipped, lambda p: p[2] - altitude(q, p))
                    if len(outside) >= 3:
                        remaining.append(outside)
                    if len(clipped) < 3:
                        break
                if len(clipped) < 3:
                    continue
                for q in planes:
                    patch = clipped
                    for other in planes:
                        if other != q:
                            patch, _ = split(
                                patch, lambda p: altitude(q, p) - altitude(other, p)
                            )
                            if len(patch) < 3:
                                break
                    if len(patch) >= 3:
                        remaining.append(
                            [
                                (x, y, altitude(q, (x, y)), u, v)
                                for x, y, z, u, v in patch
                            ]
                        )
            parts = remaining
        for poly in parts:
            result.face([p[:3] for p in poly], mesh.m[i], [p[3:] for p in poly])
    return result
