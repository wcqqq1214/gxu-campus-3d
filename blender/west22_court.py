"""East approach from the raised West 22 courtyard to the perimeter path."""

import math


def east_steps(mesh, length, depth, concrete, wall, riser):
    # Match the outside edges of the landing and the foot in the southeast panorama.
    x0, y0 = length + 1.94, -8.01
    angle = math.radians(-2.45)
    cs, sn = math.cos(angle), math.sin(angle)

    def world(u, v, z):
        return (x0 + u * cs - v * sn, y0 + u * sn + v * cs, z)

    def flat(points, z, material):
        mesh.face([world(u, v, z) for u, v in points], material)

    def side(a, b, top_a, top_b, base, material):
        mesh.face(
            [world(*a, base), world(*b, base), world(*b, top_b), world(*a, top_a)],
            material,
        )

    w = 3.08
    half = w / 2
    run = 2.50
    count = 6
    base = -1.245
    rise = -base / (count + 1)
    # The near retaining wall follows the court out to the next dormitory.
    # A curb runs down its left wing, while the right cheek continues into the east wall.
    left = [(-2.21, -14), (-1.93, -8), (-1.75, -4.3), (-half, 0)]
    right = half + 0.62
    # Partition the L-shaped court into convex strips for the glTF triangulator.
    far = -length - 5
    for a, b in zip(left, left[1:]):
        flat([(far, a[1]), a, b, (far, b[1])], 0, concrete)
        side(a, b, 0.035, 0.035, base, wall)
        # Shallow coping with narrow inset joints along the edge.
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = max(1, round(math.hypot(dx, dy) / 1.7))
        for k in range(n):
            t0 = (k + 0.012) / n
            t1 = (k + 0.988) / n
            x, y = a[0] + t0 * dx, a[1] + t0 * dy
            xx, yy = a[0] + t1 * dx, a[1] + t1 * dy
            flat([(x - 0.17, y), (x, y), (xx, yy), (xx - 0.17, yy)], 0.035, concrete)
            side((x, y), (xx, yy), 0.035, 0.035, -0.075, wall)
    back = depth + 10
    flat([(far, 0), (right, 0), (right, back), (far, back)], 0, concrete)
    side((right, 0), (right, back), 0, 0, base, wall)
    side((-half, 0), (half, 0), 0, 0, -rise, riser)
    for k in range(count):
        v0 = -k * run / count
        v1 = -(k + 1) * run / count
        top = -(k + 1) * rise
        flat([(-half, v1), (half, v1), (half, v0), (-half, v0)], top, concrete)
        side((-half, v1), (half, v1), top, top, top - rise, riser)
    # Paved toe between the last riser and the shared east-side path.
    flat(
        [
            (-half - 0.16, -6.65),
            (right + 2.5, -6.65),
            (right + 2.5, -run),
            (-half - 0.16, -run),
        ],
        base,
        concrete,
    )
    # Continue the lower pavement along the outside of the court wall.
    flat(
        [(right, -run), (right + 2.5, -run), (right + 2.5, 3.0), (right, 3.0)],
        base + 0.022,
        concrete,
    )
    # Right sloping cheek is noticeably wider than the small left return.
    for u0, u1 in ((-half - 0.16, -half), (half, right)):
        top = 0.03
        toe = base + 0.10
        mesh.face(
            [
                world(u0, -run, toe),
                world(u1, -run, toe),
                world(u1, 0, top),
                world(u0, 0, top),
            ],
            concrete,
        )
        side((u0, -run), (u1, -run), toe, toe, base, wall)
        side((u1, -run), (u1, 0), toe, top, base, wall)
        side((u0, 0), (u0, -run), top, toe, base, wall)
