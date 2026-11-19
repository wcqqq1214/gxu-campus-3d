"""South branch of the West 5 junction, bounded by the original approach edge."""

import math

from shapely.geometry import LineString, Point, Polygon, box

from surroundings_data import tiled_triangles


def prepare_junction(path, frames, branch):
    # The bounds end on straight portions of the three streets. The north
    # edge of the cut lies inside the already excavated main carriageway.
    west, east, south = 110, 137, -623
    cut = [(west, south), (east, south), (east, -579), (west, -587)]
    window = Polygon(cut)
    edge = [(p[0] + 5 * uy, p[1] - 5 * ux, p[2]) for p, (ux, uy) in zip(path, frames)]
    line = LineString([p[:2] for p in edge])
    main = Polygon([*line.coords, (edge[-1][0], -500), (edge[0][0], -500)])
    branch_asphalt = branch.buffer(3.72, cap_style=2)
    road = main.union(branch_asphalt)
    # Close only the re-entrant corners with tangent circular returns.
    road = road.buffer(4.8, quad_segs=12).buffer(-4.8, quad_segs=12).union(road)
    approach = window.difference(main)
    curb_edge = road.buffer(0.28)
    walk_edge = road.buffer(3.5)
    center_x = branch.intersection(LineString([(west, south), (east, south)])).x
    # Brick paving follows both returns and narrows into the existing branch kerbs.
    widths = []
    for y in range(-616, -599):
        progress = (y + 616) / 16
        width = 4 + 3.5 * progress**2 * (3 - 2 * progress)
        widths.append((width, y))
    taper = Polygon(
        [(center_x - w, y) for w, y in widths]
        + [(center_x + w, y) for w, y in reversed(widths)]
    ).union(box(west - 10, -600, east + 10, -570))
    paving = curb_edge.union(walk_edge.intersection(taper))
    layers = []
    for material, shape in (
        ('asphalt', road),
        ('curb', curb_edge.difference(road)),
        ('pavingRed', paving.difference(curb_edge)),
        ('grass', approach.difference(paving)),
    ):
        layer = tiled_triangles(shape.intersection(approach), step=2)
        layers.append({'material': material, **layer})
    # Distances to the edge keep the shoulders graded to the original ground.
    turf = layers[-1]
    turf['edgeDistances'] = [paving.distance(Point(x, y)) for x, y in turf['vertices']]

    # The campus terrain and the branch use independent Draco grids. Back the
    # grass seam below its finished surface so quantization cannot expose sky.
    seam = window.boundary.intersection(approach.difference(paving))
    backing = tiled_triangles(seam.buffer(0.12, cap_style=2), step=2)
    layers.append(
        {
            'material': 'grass',
            'zOffset': -0.08,
            **backing,
            'edgeDistances': [
                paving.distance(Point(x, y)) for x, y in backing['vertices']
            ],
        }
    )

    mouth = LineString([(west, south), (east, south)]).intersection(road)
    layers.append(
        {
            'material': 'asphalt',
            'zOffset': -0.025,
            **tiled_triangles(mouth.buffer(0.15, cap_style=2), step=2),
        }
    )

    def boundary_lines(boundary):
        lines = [boundary] if boundary.geom_type == 'LineString' else boundary.geoms
        result = []
        for curve in lines:
            if curve.geom_type != 'LineString' or curve.length < 0.05:
                continue
            coords = list(curve.coords)
            for a, b in zip(coords, coords[1:]):
                n = max(1, math.ceil(math.dist(a, b)))
                result.append(
                    [
                        [a[k] + (b[k] - a[k]) * i / n for k in (0, 1)]
                        for i in range(n + 1)
                    ]
                )
        return result

    return {
        'sourceWay': 'way/759147084',
        'south': south,
        'mainEdge': edge,
        'cut': {
            'id': 'bocui-south-junction',
            'polygon': cut,
            'bounds': list(window.bounds),
        },
        'layers': layers,
        'kerbs': boundary_lines(
            road.boundary.intersection(approach).difference(line.buffer(0.001))
        ),
        'walkEdges': boundary_lines(
            paving.boundary.intersection(approach).difference(
                window.boundary.buffer(0.001)
            )
        ),
    }
