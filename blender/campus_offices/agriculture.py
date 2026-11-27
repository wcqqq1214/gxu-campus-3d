"""Only way/759096561 and way/759185166. Campus-world Mesh in either production LOD."""

import math
from bisect import bisect_left

from geometry import Mesh

MODEL_IDS = ('way/759096561', 'way/759185166')


def agriculture_end(b, z, C, mesh):
    ring = b['polygons'][0][0]
    origin = ring[6]
    unit = [ring[5][j] - origin[j] for j in (0, 1)]
    w = math.hypot(*unit)
    ex, ey = [t / w for t in unit]

    def world(x, y, h):
        return (origin[0] + x * ex - y * ey, origin[1] + x * ey + y * ex, z + h)

    # Coordinates are (world XYZ, UV, along, inward, relative height).
    def tag(v, uv):
        dx, dy = v[0] - origin[0], v[1] - origin[1]
        return (*v, *uv, dx * ex + dy * ey, -dx * ey + dy * ex, v[2] - z)

    def clip(poly, axis, limit):
        a = poly[-1]
        inside = []
        outside = []
        for p in poly:
            da, dp = a[axis] - limit, p[axis] - limit
            if da * dp < 0:
                t = da / (da - dp)
                cross = tuple(x + (y - x) * t for x, y in zip(a, p))
                inside.append(cross)
                outside.append(cross)
            if dp >= 0:
                inside.append(p)
            if dp <= 0:
                outside.append(p)
            a = p
        return inside, outside

    def remove_corner(poly, depth, top):
        # Remove the intersection x>0, y<depth, h>top. Return disjoint
        # remaining polygon pieces with linearly interpolated original UVs.
        if (
            max(t[5] for t in poly) < 0.003
            or min(t[6] for t in poly) >= depth
            or max(t[7] for t in poly) <= top
        ):
            return [poly]
        out = []
        for axis, limit, positive in [(5, 0, True), (6, depth, False), (7, top, True)]:
            # Coplanar faces on a retained boundary stay whole.
            if all(abs(t[axis] - limit) < 1e-8 for t in poly):
                return out + [poly]
            pos, neg = clip(poly, axis, limit)
            stay, poly = (neg, pos) if positive else (pos, neg)
            if len(stay) >= 3:
                out.append(stay)
            if len(poly) < 3:
                return out
        return out

    new = Mesh()
    starts = []
    ends = []
    for i, (face, material) in enumerate(zip(mesh.f, mesh.m)):
        starts.append(min(face))
        ends.append(len(new.v))
        uvs = mesh.face_uvs.get(i)
        poly = [
            tag(mesh.v[j], uvs[k] if uvs else (0.0, 0.0)) for k, j in enumerate(face)
        ]
        for q in remove_corner(poly, 32.0, 13.20):
            for t in remove_corner(q, 16.0, 9.90):
                xyz = [p[:3] for p in t]
                if len(set(xyz)) >= 3:
                    new.face(xyz, material, uvs=[p[3:5] for p in t] if uvs else None)
    ends.append(len(new.v))
    for label, start, end in mesh.parts:
        a, bb = ends[bisect_left(starts, start)], ends[bisect_left(starts, end)]
        if bb > a:
            new.parts.append((label, a, bb))
    new.xy_uv_materials = mesh.xy_uv_materials.copy()
    new.ground_uv_bounds = list(mesh.ground_uv_bounds)
    cap = Mesh()
    angle = math.atan2(ey, ex)

    def box(x, y, h, width, depth, height, mat):
        cap.box(*world(x, y, h), width, depth, height, C[mat], angle)

    # Retained western boundary and the 15.54 m front follow the source footprint.
    # A solid fourth/fifth level closer to the street would occlude the
    # observed open slots. Depths 16 and 32 m are sightline estimates.
    for low, high, h in ((0, 16.0, 9.9), (16.0, 32.0, 13.2)):
        cap.face(
            [world(0, low, h), world(w, low, h), world(w, high, h), world(0, high, h)],
            C['paleRoof'],
        )
        parapet = 1.60 if low == 0 else 0.48
        box(w / 2, low + 0.1, h + parapet / 2, w, 0.2, parapet, 'pink')
        box(w - 0.10, (high + low) / 2, h + 0.28, 0.20, high - low, 0.56, 'pink')
        left = max(2.18, low)
        cap.face(
            [
                world(0, left, h),
                world(0, high, h),
                world(0, high, 16.5),
                world(0, left, 16.5),
            ],
            C['pink'],
        )
    for depth, bottom, top in ((16.0, 9.9, 13.2), (32.0, 13.2, 16.5)):
        cap.face(
            [
                world(0, depth, bottom),
                world(w, depth, bottom),
                world(w, depth, top),
                world(0, depth, top),
            ],
            C['pink'],
        )
    # Slender horizontal roof frame and visible uprights, distinct from a full storey.
    # Five visible piers, the main south wall closes the western return.
    for x in (1.03, 3.89, 6.38, 8.73, 10.84):
        box(x, 1.10, 11.48, 0.28, 0.23, 2.74, 'stone')
    box(5.52, 1.10, 12.80, 11.20, 0.33, 0.44, 'stone')
    # Integral centre projection on the south end, seen above the tree canopy.
    box(w * 0.50, -0.30, 8.0, 3.65, 0.65, 3.0, 'pink')
    box(w * 0.50, -0.65, 8.15, 2.96, 0.09, 2.05, 'glass')
    for dx in (-0.98, 0, 0.98):
        box(w * 0.50 + dx, -0.72, 8.15, 0.08, 0.06, 2.12, 'white')
    box(w * 0.50, -0.72, 7.53, 3.02, 0.06, 0.08, 'white')
    new.add_part('农学楼东端临前场退台与凸窗', cap)
    return new
