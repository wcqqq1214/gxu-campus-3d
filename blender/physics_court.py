"""North courtyard and east entry of way/957404989. Campus coordinates in metres.

Hualan's completed aerial (GXHL, project 887, photo 3) locates the paired
white courts behind the framed entrance. Photo 16705 shows the hard surface,
with planting beyond it. The designer distinguishes the first-floor activity
yard from the second-floor stair terrace and the upper innovation gallery.
"""

# The central court fits between the north and middle wings. Preserve the
# exposed planting at the west end and the separate south light court.
COURT_WEST = -691.0
COURT_EAST = -647.55
COURT_SOUTH = -848.80
COURT_NORTH = -831.05
COURT_HEIGHT = 0.60
SHARED_DEPTH = 6.60
SOUTH_ROOM_END = -856.00
NORTH_ROOM_START = -819.80


def north_court(mesh, z, C):
    floor = z + COURT_HEIGHT

    def block(w, e, s, n, low, top, finish):
        mesh.box(
            (w + e) / 2,
            (s + n) / 2,
            (low + top) / 2,
            e - w,
            n - s,
            top - low,
            C[finish],
        )

    def surface(w, e, s, n, h, finish):
        mesh.face([(w, s, h), (e, s, h), (e, n, h), (w, n, h)], C[finish])

    # Ground-bearing paving. The subgrade passes below the old DEM to avoid
    # a floating edge; the east notch respects the courtyard-side end walls.
    block(
        COURT_WEST,
        COURT_EAST,
        COURT_SOUTH,
        COURT_NORTH,
        z - 0.75,
        floor,
        'bridgeConcrete',
    )
    block(COURT_EAST, -642.90, -844.60, -831.05, z - 0.75, floor, 'bridgeConcrete')
    # The west photo shows a pedestrian exit beneath the link, with planted
    # shoulders. Follow the retained terrain section on the narrow path.
    path_s, path_n = -841.50, -838.10
    for s, n in ((COURT_SOUTH, path_s), (path_n, COURT_NORTH)):
        mesh.face(
            [
                (COURT_WEST - 2.6, s, z + 0.37),
                (COURT_WEST, s, floor),
                (COURT_WEST, n, floor),
                (COURT_WEST - 2.6, n, z + 0.37),
            ],
            C['bridgeConcrete'],
        )
    # The source terrain slopes 7.67% to the west and 1.22% across the lane.
    # At the field edge the profile flattens to match the activity surface.
    stations = [
        (COURT_WEST, floor, floor),
        (-694.0, z + 0.614, z + 0.572),
        (-702.0, z + 1.224, z + 1.182),
    ]
    for (east, se, ne), (west, sw, nw) in zip(stations, stations[1:]):
        # Explicit triangles for the transition from zero to terrain crossfall.
        a, b, c, d = (
            (west, path_s, sw),
            (east, path_s, se),
            (east, path_n, ne),
            (west, path_n, nw),
        )
        mesh.face([a, b, c], C['bridgeConcrete'])
        mesh.face([a, c, d], C['bridgeConcrete'])
        for low, high in ((a, b), (c, d)):
            mesh.face(
                [
                    (low[0], low[1], low[2] - 0.29),
                    (high[0], high[1], high[2] - 0.29),
                    high,
                    low,
                ],
                C['bridgeConcrete'],
            )
    west, sw, nw = stations[-1]
    mesh.face(
        [
            (west, path_n, nw - 0.10),
            (west, path_s, sw - 0.10),
            (west, path_s, sw),
            (west, path_n, nw),
        ],
        C['bridgeConcrete'],
    )

    # Two parallel doubles badminton markings: paint subdivides into strips
    # at the intersections. No opaque base plate or permanently installed net.
    # The building-local footprint is fitted to the aerial, not a survey.
    w, e = -663.35, -649.95
    half = 0.022
    paint = floor + 0.009
    for cy in (-843.62, -836.12):
        s, n = cy - 3.05, cy + 3.05
        for y in (s, s + 0.46, n - 0.46, n):
            surface(w, e, y - half, y + half, paint, 'sportWhite')
        for x in (w, w + 0.76, (w + e) / 2 - 1.98, (w + e) / 2 + 1.98, e - 0.76, e):
            for y0, y1 in (
                (s + half, s + 0.46 - half),
                (s + 0.46 + half, n - 0.46 - half),
                (n - 0.46 + half, n - half),
            ):
                surface(x - half, x + half, y0, y1, paint, 'sportWhite')
        for x0, x1 in (
            (w + half, w + 0.76 - half),
            (w + 0.76 + half, (w + e) / 2 - 1.98 - half),
            ((w + e) / 2 + 1.98 + half, e - 0.76 - half),
            (e - 0.76 + half, e - half),
        ):
            surface(x0, x1, cy - half, cy + half, paint, 'sportWhite')


def court_joints(mesh, z, C):
    """Near-view control joints, below the paint; the far LOD keeps one finish."""
    h = z + COURT_HEIGHT + 0.0035

    def strip(w, e, s, n):
        mesh.face([(w, s, h), (e, s, h), (e, n, h), (w, n, h)], C['gateJoint'])

    for x in (-686.0, -680.5, -675.0, -669.5, -664.0, -658.5, -653.0):
        strip(x - 0.009, x + 0.009, COURT_SOUTH, COURT_NORTH)
    for y in (-844.35, -839.90, -835.45):
        strip(COURT_WEST, COURT_EAST, y - 0.009, y + 0.009)
