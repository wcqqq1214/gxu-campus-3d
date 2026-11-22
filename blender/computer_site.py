"""North forecourt of way/759129514, campus coordinates in metres."""

import math

from mathutils.bvhtree import BVHTree

from civil_forecourt_grade import grade_mesh
from geometry import Mesh
from site_geometry import mesh_triangles

BUILDING_ID = 'way/759129514'
NORTH = -750.40
CENTER_X = -220.55
WIDTH = 27.60
TOE = NORTH + 3.125 + 4 * 0.34
# Adopted from the published road at the middle of the entrance and the
# highest adjacent soil along the tread. The panorama supplies the stair
# count and continuous horizontal nosing, not an absolute survey datum.
COURT_Z = 3.4


def computer_forecourt(terrain, roads, C):
    """Tie the full stair width to the first existing road edge on each transect."""
    road = BVHTree.FromPolygons(
        roads.v, [f for f, _ in mesh_triangles(roads)], all_triangles=True
    )
    left, right = CENTER_X - WIDTH / 2, CENTER_X + WIDTH / 2
    count = math.ceil(WIDTH)
    xs = [left + WIDTH * i / count for i in range(count + 1)]

    def hit(x, y):
        return road.ray_cast((x, y, 80), (0, 0, -1))[0]

    def join(x):
        y = TOE
        while y < -727 and hit(x, y) is None:
            y += 0.25
        if y >= -727:
            raise ValueError(f'{BUILDING_ID}: missing north road at {x}')
        lo, hi = y - 0.25, y
        for _ in range(15):
            mid = (lo + hi) / 2
            if hit(x, mid) is None:
                lo = mid
            else:
                hi = mid
        near, near_z = hi, hit(x, hi + 0.003).z
        # The opposite road edge is also visible at the foot of the review
        # camera. Both edge heights come from the existing carriageway mesh.
        lo = near + 0.1
        hi = lo + 0.25
        while hi < -720 and hit(x, hi) is not None:
            lo, hi = hi, hi + 0.25
        if hi >= -720:
            raise ValueError(f'{BUILDING_ID}: missing opposite verge at {x}')
        for _ in range(15):
            mid = (lo + hi) / 2
            if hit(x, mid) is None:
                hi = mid
            else:
                lo = mid
        return near, near_z, lo, hit(x, lo - 0.003).z

    edges = [join(x) for x in xs]

    def edge(x):
        s = min(count, max(0, (x - left) * count / WIDTH))
        i = min(count - 1, int(s))
        return tuple(a + (b - a) * (s - i) for a, b in zip(edges[i], edges[i + 1]))

    def elevation(x, y):
        end, h, _, _ = edge(x)
        t = min(1, max(0, (y - TOE) / (end - TOE)))
        return COURT_Z + t * (h - COURT_Z)

    # Both the subgrade and the short grass shoulders return to the original
    # triangle elevations. The west boundary stops short of the party wall.
    footprint = dict(
        extent=[-236.2, -755, -201.5, -722.5],
        core=[left, NORTH, right, -727.2],
        meshStep=1.5,
    )

    def bedding(x, y):
        near, low, far, high = edge(x)
        if y >= near:
            t = max(0, min(1, (y - near) / (far - near)))
            return low + (high - low) * t - 0.025
        # Preserve clearance under the paving while bringing turf to the lip.
        inset = max(0, min(1, (x - left) / 1.25, (right - x) / 1.25))
        return elevation(x, y) - (0.025 + 0.06 * inset)

    terrain = grade_mesh(terrain, footprint, target_height=bedding)
    apron = Mesh()
    # The row of pale rectangular drain covers is visible in both frontal
    # photographs. Re-use campus finishes; the joints are coplanar strips.
    for i, (a, b) in enumerate(zip(xs, xs[1:])):

        def point(x, s):
            end, h, _, _ = edge(x)
            y = (TOE - 0.04, end - 0.86, end - 0.15, end, end + 0.12)[s]
            return (x, y, elevation(x, y) - (0.022 if s == 4 else 0))

        for s in range(4):

            def band(x0, x1, mat):
                q = [point(x0, s), point(x1, s), point(x1, s + 1), point(x0, s + 1)]
                apron.face(q[:3], mat)
                apron.face([q[0], q[2], q[3]], mat)

            if s == 1:
                band(a, b - 0.024, C['drainStone'])
                band(b - 0.024, b, C['slate'])
            else:
                band(a, b, C['path'])
    # Cover the bedding clearance at the two exposed paving edges, including
    # the road underlap. The bank below the edging is continuous with the lawn.
    for x in (left, right):
        end, h, _, _ = edge(x)
        stations = [TOE - 0.04, end - 0.86, end - 0.15, end, end + 0.12]
        for a, b in zip(stations, stations[1:]):
            za, zb = elevation(x, a), elevation(x, b) - (0.022 if b > end else 0)
            quad = [(x, a, za), (x, b, zb), (x, b, zb - 0.19), (x, a, za - 0.19)]
            apron.face(quad if x == left else quad[::-1], C['gateJoint'])
    for a, b in zip(xs, xs[1:]):
        _, _, ya, za = edge(a)
        _, _, yb, zb = edge(b)
        # Reconnect the thin, upward-facing published road triangles to the
        # turf. The short buried overlap handles independent GLB quantization.
        apron.face(
            [(b, yb, zb - 0.19), (a, ya, za - 0.19), (a, ya, za), (b, yb, zb)],
            C['road'],
        )
    return terrain, apron
