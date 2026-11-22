"""Close the diagonal seam on the southern approach to Middle 21."""

from copy import copy

from v5_west15_apron import build as build_gate_apron

# Transverse levels come from the two original edges of this carriageway.
SOUTH, NORTH = 410.999, 417.001


def lane_point(x, y):
    center = -46.55 + 0.378 * (y - 411.92)
    return abs(x - center) < 4.0


def edge_levels(faces, y):
    crossings = []
    for pts in faces:
        for a, b in zip(pts, pts[1:] + pts[:1]):
            if min(a[1], b[1]) <= y <= max(a[1], b[1]):
                if a[1] == b[1]:
                    crossings.extend([(a[0], a[2]), (b[0], b[2])])
                else:
                    t = (y - a[1]) / (b[1] - a[1])
                    crossings.append(
                        (a[0] + t * (b[0] - a[0]), a[2] + t * (b[2] - a[2]))
                    )
    return min(crossings), max(crossings)


def apply(base, colors):
    road = base['roads']
    if getattr(road, 'middle21_south_graded', False):
        return
    faces, rows = [], {}
    for face, material in zip(road.f, road.m):
        if material != colors['road']:
            continue
        pts = [road.v[index] for index in face]
        if max(p[1] for p in pts) < SOUTH or min(p[1] for p in pts) > NORTH:
            continue
        if not all(lane_point(x, y) for x, y, _ in pts):
            continue
        faces.append(pts)
        for index, (x, y, _) in zip(face, pts):
            if SOUTH < y < NORTH:
                rows.setdefault(y, set()).add(index)

    corrected = copy(road)
    corrected.v = list(road.v)
    for y, indices in rows.items():
        (left, low), (right, high) = edge_levels(faces, y)
        if right <= left:
            continue
        weight = min(1, max(0, (y - 411) / 1.5), max(0, (417 - y) / 1.5))
        for index in indices:
            x, _, z = road.v[index]
            crossfall = low + (high - low) * (x - left) / (right - left)
            on_seam = abs(x + 47.251558 - 0.761463 * (y - 411)) < 0.002
            height = crossfall if on_seam else z + weight * (crossfall - z)
            if abs(height - z) > 1e-7:
                corrected.v[index] = (x, y, height)
    corrected.middle21_south_graded = True
    base['roads'] = corrected
    build_gate_apron(base, colors)
