"""East main campus, south of Xiuxiang Avenue. Project XY metres, east/north.

Esri World Imagery / Vantor Vivid Advanced, 2025-03-25, 0.34 m GSD,
8.47 m stated accuracy. Origin WGS84 (108.2882 E, 22.84715 N).
Quadrilaterals follow visible bed edges. Colours represent cover at capture.
"""

from math import ceil, cos, hypot, pi, sin

from geometry import Mesh

# Each bed runs from its south edge (west, east) to its north edge.
# Width subdivisions represent grouped rows; pitch and vertical relief are schematic.
BEDS = (
    ((-63.8, 811.8), (-38.5, 819.4), (-60.9, 903.5), (-88.8, 898.8), 'leaf2'),
    ((-35.5, 820.7), (-13.5, 827.6), (-34.2, 907.4), (-59.2, 902.6), 'dormStoneWarm'),
    ((-9.6, 728.4), (13.0, 735.1), (-9.8, 820.0), (-32.9, 812.5), 'dormStoneWarm'),
    ((18.0, 735.7), (42.6, 742.6), (20.6, 827.1), (-6.1, 819.8), 'green'),
    ((43.9, 743.9), (67.6, 750.4), (45.6, 835.8), (22.3, 827.1), 'dormStoneWarm'),
    ((69.3, 751.2), (94.4, 759.0), (73.2, 843.5), (47.4, 835.8), 'dormStoneWarm'),
    ((96.5, 759.9), (120.2, 766.8), (96.5, 850.0), (75.4, 843.1), 'leaf2'),
    ((122.4, 767.6), (144.4, 773.7), (122.4, 856.0), (98.2, 850.0), 'grass'),
    ((146.5, 774.5), (168.1, 779.7), (147.4, 855.2), (124.5, 857.8), 'dormStoneWarm'),
    ((-53.3, 612.9), (-23.4, 621.9), (-41.9, 704.7), (-74.8, 694.0), 'green'),
    ((-7.0, 627.0), (40.7, 639.2), (17.0, 723.8), (-29.8, 709.4), 'grass'),
    ((45.4, 640.0), (67.2, 648.6), (41.2, 732.3), (21.5, 725.3), 'leaf2'),
    ((68.5, 650.3), (89.9, 656.4), (67.0, 739.6), (44.4, 732.3), 'leaf2'),
    ((82.4, 709.1), (106.0, 716.7), (96.9, 748.6), (74.1, 741.8), 'green'),
    ((108.6, 718.0), (130.2, 724.1), (120.7, 756.4), (100.8, 749.9), 'grass'),
    ((132.3, 724.5), (180.2, 737.0), (171.6, 769.4), (125.4, 757.3), 'leaf3'),
    ((88.6, 687.0), (126.7, 698.2), (122.0, 714.6), (84.3, 704.2), 'dormStoneWarm'),
    ((128.9, 699.5), (157.8, 706.8), (155.6, 715.0), (125.8, 707.2), 'grass'),
    ((97.4, 657.7), (118.1, 664.6), (113.3, 685.7), (91.3, 679.6), 'dormStoneWarm'),
    ((120.7, 666.3), (148.3, 673.6), (142.2, 695.2), (115.5, 686.5), 'dormStoneWarm'),
    ((150.0, 674.0), (169.4, 680.5), (163.4, 702.5), (144.8, 696.0), 'dormStoneWarm'),
    ((-101.0, 768.9), (-64.8, 778.8), (-70.4, 802.4), (-118.4, 788.7), 'green'),
    ((-55.3, 754.3), (-23.8, 763.7), (-36.3, 811.2), (-69.1, 802.6), 'leaf2'),
)

# Individual crown envelopes inside the wooded belt west of the main field.
# Existing campus crowns are reserved by the offline clearance check.
CROWNS = (
    (-387.7, 888.5, 4.1),
    (-383.3, 882.0, 4.0),
    (-377.2, 886.3, 4.3),
    (-369.7, 883.2, 4.1),
    (-359.8, 839.0, 3.8),
    (-343.2, 835.0, 3.6),
    (-285.2, 870.5, 4.0),
    (-294.2, 875.7, 4.3),
    (-311.7, 858.2, 3.7),
)


def _mix(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def site_meshes(elevation, C):
    beds = Mesh()
    for sw, se, ne, nw, cover in BEDS:
        rows = max(1, round(hypot(se[0] - sw[0], se[1] - sw[1]) / 3.2))
        steps = ceil(hypot(nw[0] - sw[0], nw[1] - sw[1]) / 6)
        for row in range(rows):
            for lo, hi, mat, rise0, rise1 in (
                (0, 0.19, 'bark', 0, 0.09),
                (0.19, 0.86, cover, 0.09, 0.09),
                (0.86, 1, 'bark', 0.09, 0),
            ):
                for j in range(steps):
                    points = []
                    for u, v, h in (
                        (lo, j, rise0),
                        (hi, j, rise1),
                        (hi, j + 1, rise1),
                        (lo, j + 1, rise0),
                    ):
                        a = _mix(sw, nw, v / steps)
                        b = _mix(se, ne, v / steps)
                        x, y = _mix(a, b, (row + u) / rows)
                        points.append((x, y, elevation(x, y) + 0.34 + h))
                    beds.face(points, C[mat])
    grove = Mesh()
    for i, (x, y, radius) in enumerate(CROWNS):
        z = elevation(x, y)
        grove.cylinder(x, y, z + 2, 0.19, 4, C['bark'], 6)
        ring = [
            (
                x + radius * cos(i + k * pi / 4),
                y + 0.88 * radius * sin(i + k * pi / 4),
                z + 4.5 + 0.3 * sin(k + i),
            )
            for k in range(8)
        ]
        shoulder = [
            (x + (px - x) * 0.64, y + (py - y) * 0.68, pz + radius * 0.48)
            for px, py, pz in ring
        ]
        for k, p in enumerate(ring):
            q = ring[(k + 1) % 8]
            t, u = shoulder[k], shoulder[(k + 1) % 8]
            leaf = C[('leaf', 'leaf2')[(i + k // 3) % 2]]
            grove.face([p, q, u, t], leaf)
            grove.face([t, u, (x + 0.32, y, z + 4.5 + radius * 0.72)], leaf)
            grove.face([q, p, (x, y, z + 2.8)], C['leaf'])
    return {'east-field-beds': beds, 'east-field-grove': grove}
