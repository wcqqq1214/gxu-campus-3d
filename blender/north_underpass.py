"""Open the mapped passage below retained roads; no pavement over the arterial."""

from foundation_geometry import clipped_mesh, masks_for
from geometry import Mesh
from infrastructure import frames


def road_height_sampler(source, elevation):
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree

    data = bpy.data.meshes.new('north-road-sampling')
    data.from_pydata(source.v, [], source.f)
    data.calc_loop_triangles()
    tree = BVHTree.FromPolygons(
        [v.co for v in data.vertices],
        [tuple(t.vertices) for t in data.loop_triangles],
        all_triangles=True,
    )
    bpy.data.meshes.remove(data)

    def height(x, y):
        p = tree.ray_cast(Vector((x, y, 50)), Vector((0, 0, -1)), 100)[0]
        return p.z if p is not None else elevation(x, y) + 0.4

    return height


def upper_road_model(b, c, height):
    """Continuous same-width asphalt deck, joined to original boundary heights."""
    m = Mesh()
    for repair in b['upperRoadRepairs']:
        a, d = repair['a'], repair['b']
        ux, uy = repair['direction']
        w = repair['width']
        # Independently quantized GLB nodes can pull shared edges apart by
        # millimeters. Extend the same surface across the cut at both joins.
        a = [a[0] - ux * 0.08, a[1] - uy * 0.08]
        d = [d[0] + ux * 0.08, d[1] + uy * 0.08]
        offsets = (
            [-w / 2 - 0.45, -w / 2]
            + [-w / 2 + w * i / 14 for i in range(1, 14)]
            + [w / 2, w / 2 + 0.45]
        )
        left = [
            height(a[0] - ux * 0.04 - uy * v, a[1] - uy * 0.04 + ux * v)
            for v in offsets
        ]
        right = [
            height(d[0] + ux * 0.04 - uy * v, d[1] + uy * 0.04 + ux * v)
            for v in offsets
        ]

        def point(t, j):
            v = offsets[j]
            return (
                a[0] * (1 - t) + d[0] * t - uy * v,
                a[1] * (1 - t) + d[1] * t + ux * v,
                left[j] * (1 - t) + right[j] * t,
            )

        for j in range(len(offsets) - 1):
            m.face(
                [point(0, j), point(1, j), point(1, j + 1), point(0, j + 1)],
                c['white' if j in (0, len(offsets) - 2) else 'asphalt'],
            )
    return m


def underpass_model(b, c, elevation):
    m = Mesh()
    path = b['path']
    axes = frames(path)
    half = b['clearWidth'] / 2
    lo, hi = b['coveredRange']
    soffit = b['soffit']
    for i, (a, d) in enumerate(zip(path, path[1:])):

        def point(p, axis, u, z):
            return (p[0] - axis[1] * u, p[1] + axis[0] * u, z)

        aa, dd = axes[i : i + 2]
        m.face(
            [
                point(a, aa, -half, a[2]),
                point(d, dd, -half, d[2]),
                point(d, dd, half, d[2]),
                point(a, aa, half, a[2]),
            ],
            c['road'],
        )
        for side in (-1, 1):
            inner = side * half
            outer = side * b['cutHalfWidth']
            za = elevation(a[0] - aa[1] * outer, a[1] + aa[0] * outer) + 0.1
            zd = elevation(d[0] - dd[1] * outer, d[1] + dd[0] * outer) + 0.1
            m.face(
                [
                    point(a, aa, inner, a[2] - 0.1),
                    point(a, aa, inner, za),
                    point(d, dd, inner, zd),
                    point(d, dd, inner, d[2] - 0.1),
                ][::side],
                c['paleRoof'],
            )
            m.face(
                [
                    point(a, aa, inner, za),
                    point(a, aa, outer, za),
                    point(d, dd, outer, zd),
                    point(d, dd, inner, zd),
                ][::-side],
                c['white'],
            )
        # Roof stays below the arterial deck, with exposed portal edges.
        if a[4] <= hi and d[4] >= lo:
            start = max(lo, a[4])
            end = min(hi, d[4])

            def at(t):
                f = (t - a[4]) / (d[4] - a[4])
                return [a[k] + (d[k] - a[k]) * f for k in range(5)]

            p, q = at(start), at(end)
            m.face(
                [
                    point(p, aa, -half, soffit),
                    point(p, aa, half, soffit),
                    point(q, dd, half, soffit),
                    point(q, dd, -half, soffit),
                ],
                c['paleRoof'],
            )
            # Restore only the earth cap underneath the retained road deck.
            m.face(
                [
                    point(p, aa, -b['cutHalfWidth'], elevation(*p[:2]) + 0.04),
                    point(q, dd, -b['cutHalfWidth'], elevation(*q[:2]) + 0.04),
                    point(q, dd, b['cutHalfWidth'], elevation(*q[:2]) + 0.04),
                    point(p, aa, b['cutHalfWidth'], elevation(*p[:2]) + 0.04),
                ],
                c['grass'],
            )
            for t, r, axis, reverse in [(start, p, aa, False), (end, q, dd, True)]:
                if abs(t - lo) < 1e-5 or abs(t - hi) < 1e-5:
                    top = elevation(*r[:2]) + 0.08
                    pts = [
                        point(r, axis, -half, soffit),
                        point(r, axis, half, soffit),
                        point(r, axis, half, top),
                        point(r, axis, -half, top),
                    ]
                    m.face(pts[::-1] if reverse else pts, c['white'])
    return m


def cut_meshes(base, b):
    for key, mask in [('terrain', 'terrainMasks'), ('roads', 'roadMasks')]:
        original = base[key]
        base[key], _ = clipped_mesh(base[key], masks_for(b[mask]), b['bounds'])
        base[key].ground_uv_bounds = original.ground_uv_bounds
        base[key].xy_uv_materials = original.xy_uv_materials
