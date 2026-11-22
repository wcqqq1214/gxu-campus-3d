"""West residence gate forecourt: join the documented apron to the existing lane."""

from copy import copy
from math import hypot

from next_terrain_north import cut_bed, has_area, replace_local
from west22_ground import split

# Existing road-edge vertices, in generator XY and Z metres.
EDGE = (
    (-148.29789084, 84.39289465, 1.94006915),
    (-150.15546436, 101.73718756, 1.76126164),
    (-149.63743318, 106.93692702, 1.79954790),
)
# Frontage retained inside the envelope from the March 2019 ground photographs.
ROWS = ((100.4, 0.55), (EDGE[1][1], 1.32), (103.9, 2.55), (104.8, 1.20))
BOUNDS = (-156.0, 96.0, -146.0, 109.0)


def road_edge(y):
    a, b = EDGE[:2] if y <= EDGE[1][1] else EDGE[1:]
    u = (y - a[1]) / (b[1] - a[1])
    return a[0] + u * (b[0] - a[0]), a[2] + u * (b[2] - a[2])


def top(x, y):
    east, z = road_edge(y)
    return z + 0.014 * (east - x)


def apron_row(y, width):
    east, z = road_edge(y)
    return (east - width, y, top(east - width, y)), (east, y, z)


def support_planes():
    # The supporting soil finishes 25 mm below the hard surface.
    # The eastern support line extends slightly beneath the carriageway edge.
    rim = [(road_edge(y)[0] - w, y) for y, w in reversed(ROWS)]
    rim.extend([(-149.55, ROWS[0][0]), (-149.55, ROWS[-1][0])])

    def grade(p):
        return top(p[0], p[1]) - 0.025

    planes = [grade]
    for a, b in zip(rim, rim[1:] + rim[:1]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = hypot(dx, dy)

        def shoulder(p, a=a, dx=dx, dy=dy, length=length):
            # Positive inside the support; feather into the original soil at 1:2.
            return grade(p) + 0.5 * (dx * (p[1] - a[1]) - dy * (p[0] - a[0])) / length

        planes.append(shoulder)
    return planes


def build(base, colors):
    original = base['roads']
    road = copy(original)
    road.v, road.f, road.m = list(original.v), list(original.f), list(original.m)
    road.face_uvs = dict(original.face_uvs)
    rings = [apron_row(y, w) for y, w in ROWS]
    for (west, east), (next_west, next_east) in zip(rings, rings[1:]):
        road.face([west, east, next_east], colors['path'])
        road.face([west, next_east, next_west], colors['path'])

    planes = support_planes()
    negative = [lambda p, plane=plane: -plane(p) for plane in planes]

    def invert(p):
        return (p[0], p[1], -p[2], *p[3:])

    def support(poly):
        north, south = split(poly, lambda p: p[1] - EDGE[1][1])
        for part in (north, south):
            if has_area(part):
                for piece in cut_bed([invert(p) for p in part], negative):
                    yield [invert(p) for p in piece]

    soil = replace_local(base['terrain'], BOUNDS, colors['grass'], support)
    base['roads'], base['terrain'] = road, soil
