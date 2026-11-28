"""Existing East High faculty apartments. Heights and roof crowns are estimates."""

import math

from geometry import Mesh

IDS = frozenset(
    'east-north/old-high-' + station
    for station in (
        '9',
        '6',
        'mid-n-center',
        'mid-n-east',
        'mid-s-west',
        'mid-s-east',
        'south-west',
        'south-center',
        'south-east',
    )
)


def build(b, z, C, detail):
    mesh = Mesh()
    ring = b['polygons'][0][0]
    h = b['height']
    mesh.extrude(b['polygons'], b['roofTriangles'], z, h, C['white'], C['slate'])
    # Represent the repeated horizontal openings on long faces as recessed bands.
    for a, end in zip(ring, ring[1:]):
        dx, dy = end[0] - a[0], end[1] - a[1]
        width = math.hypot(dx, dy)
        if width < 6:
            continue
        ux, uy = dx / width, dy / width
        left = (a[0] + ux + uy * 0.04, a[1] + uy - ux * 0.04)
        right = (end[0] - ux + uy * 0.04, end[1] - uy - ux * 0.04)
        for level in range(1, b['levels'], 1 if detail else 2):
            sill = z + level * h / b['levels'] + 0.8
            mesh.face(
                [
                    (*left, sill),
                    (*right, sill),
                    (*right, sill + 1.25),
                    (*left, sill + 1.25),
                ],
                C['glass'],
            )
    # Each of the nine roofs shows a central reddish pyramidal crown.
    x, y = b['center']
    longest = max(zip(ring, ring[1:]), key=lambda edge: math.dist(*edge))
    angle = math.atan2(longest[1][1] - longest[0][1], longest[1][0] - longest[0][0])
    c, s = math.cos(angle), math.sin(angle)
    mesh.box(x, y, z + h + 0.7, 8, 7, 1.4, C['stone'], angle, bottom=False)
    corners = [
        (x + u * c - v * s, y + u * s + v * c, z + h + 1.4)
        for u, v in ((-4.6, -4), (4.6, -4), (4.6, 4), (-4.6, 4))
    ]
    for a, end in zip(corners, corners[1:] + corners[:1]):
        mesh.face([a, end, (x, y, z + h + 4)], C['red'])
    return mesh
