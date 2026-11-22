"""Tie the West 22/23 lower service lane into its north approach and south turn."""

from copy import copy

from shore_geometry import bounds, overlaps
from west22_ground import split

# The east footpath and stair landing already have a model datum of -0.76 m.
# Relative slopes are fitted between existing road ends, not survey levels.
LANE = (128.4, -924.5, 137.8, -822.0)
TURN = (92.0, -924.5, 137.8, -915.2)
LOW = -0.76
CORNER = LOW + 0.059 * (919.87 - 905.0)

# Each cap is the upper envelope of planes (dz/dx, dz/dy, z at XY origin).
# Side planes run back into the untouched ground before the building footings.
CAPS = (
    (
        LANE,
        (
            (0, 0, LOW),
            # Meet the separate east stair approach of the next dorm at y=-856.9.
            (0, 0.115, LOW + 0.115 * 887.6),
            (0, -0.059, LOW - 0.059 * 905.0),
            (-6.0, 0, LOW + 6.0 * 129.49),
            (6.0, 0, LOW - 6.0 * 134.69),
            (0, -6.0, LOW - 6.0 * 922.45),
            (0, 6.0, LOW + 6.0 * 825.0),
        ),
    ),
    (
        TURN,
        (
            (0, 0, CORNER),
            (-0.033, 0, CORNER + 0.033 * 129.56),
            (0, 6.0, CORNER + 6.0 * 917.32),
            (0, -6.0, CORNER - 6.0 * 922.45),
            (6.0, 0, CORNER - 6.0 * 134.69),
            (-6.0, 0, CORNER + 6.0 * 95.0),
        ),
    ),
)


def _z(plane, point):
    dx, dy, intercept = plane
    return dx * point[0] + dy * point[1] + intercept


def _area(poly):
    # Local coordinates avoid cancellation on narrow boundary fragments.
    a = poly[0]
    return (
        abs(
            sum(
                (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])
                for b, c in zip(poly[1:], poly[2:])
            )
        )
        / 2
    )


def _cut(poly, planes):
    if any(all(p[2] <= _z(q, p) + 1e-7 for p in poly) for q in planes):
        return [poly]
    inside = poly
    outside = []
    for plane in planes:
        inside, part = split(inside, lambda p: p[2] - _z(plane, p))
        if len(part) >= 3 and _area(part) > 1e-10:
            outside.append(part)
        if len(inside) < 3 or _area(inside) <= 1e-10:
            return [poly]
    # Split on the cap ridgelines before lowering, including the L-junction.
    for plane in planes:
        patch = inside
        for other in planes:
            if plane != other:
                patch, _ = split(patch, lambda p: _z(plane, p) - _z(other, p))
                if len(patch) < 3:
                    break
        if len(patch) >= 3 and _area(patch) > 1e-10:
            outside.append([(x, y, _z(plane, (x, y)), *uv) for x, y, _, *uv in patch])
    return outside


def _grade(mesh, clearance, road_mat=None):
    vertices = mesh.v
    changes = {}
    caps = [
        (area, [(a, b, h - clearance) for a, b, h in planes]) for area, planes in CAPS
    ]
    for i, (face, mat) in enumerate(zip(mesh.f, mesh.m)):
        if road_mat is not None and mat != road_mat:
            continue
        pts = [vertices[j] for j in face]
        bb = bounds(pts)
        active = [planes for area, planes in caps if overlaps(bb, area)]
        if not active:
            continue
        uvs = mesh.face_uvs.get(i) or [(x / 4, y / 4) for x, y, _ in pts]
        original = [(*v, *uv) for v, uv in zip(pts, uvs)]
        parts = [original]
        for planes in active:
            parts = [p for poly in parts for p in _cut(poly, planes)]
        if len(parts) != 1 or parts[0] is not original:
            changes[i] = parts
    if not changes:
        return mesh
    out = copy(mesh)
    # Vertex group ranges refer to original vertices. Keep those positions and
    # append only replacement faces, retaining every untouched face's indices.
    out.v = vertices.copy()
    out.f, out.m, out.face_uvs = [], [], {}
    for i, (face, mat) in enumerate(zip(mesh.f, mesh.m)):
        if i in changes:
            for patch in changes[i]:
                out.face([p[:3] for p in patch], mat, [p[3:] for p in patch])
        else:
            if i in mesh.face_uvs:
                out.face_uvs[len(out.f)] = mesh.face_uvs[i]
            out.f.append(face)
            out.m.append(mat)
    return out


def apply(base, colors):
    """Regrade the existing service surface and its immediate soil bed together."""
    road = _grade(base['roads'], 0.0, colors['road'])
    soil = _grade(base['terrain'], 0.045)
    base.update(roads=road, terrain=soil)
