"""Two photo-located paved approaches at the electrical engineering building."""

from functools import lru_cache

from mathutils.bvhtree import BVHTree

from civil_forecourt_grade import grade_mesh
from geometry import Mesh

# Street 13° and the western oblique show two shallow noses and a smooth
# adjoining stone strip under the existing south canopy, not a full-width stair.
SILL_LEFT, SILL_SPLIT, SILL_RIGHT = -365.02, -361.35, -358.85
SILL_TOE = 826.0


def south_sill(mesh, z, mat):
    rear = 824.19

    def p(x, t, h):
        return (x, -t, z + h)

    for x0, x1, steps in (
        (SILL_LEFT, SILL_SPLIT, True),
        (SILL_SPLIT, SILL_RIGHT, False),
    ):
        for t0, t1, h0, h1 in [
            (rear, 824.86, 0.30, 0.30),
            (824.86, 825.43, 0.30, 0.15),
            (825.43, SILL_TOE, 0.15, 0.0),
        ]:
            front = h0 if steps else h1
            mesh.face(
                [p(x0, t0, h0), p(x0, t1, front), p(x1, t1, front), p(x1, t0, h0)], mat
            )
            if steps and h0 > h1:
                mesh.face(
                    [p(x0, t1, h0), p(x0, t1, h1), p(x1, t1, h1), p(x1, t1, h0)], mat
                )
                mesh.face([p(x1, t0, h0), p(x1, t1, h0), p(x1, t1, h1)], mat)
            x = x0 if steps else x1
            cheek = [p(x, t0, h0), p(x, t0, 0), p(x, t1, 0)]
            if front:
                cheek.append(p(x, t1, front))
            mesh.face(cheek if steps else cheek[::-1], mat)


def electrical_approaches(terrain, roads, datum, colors):
    # At the south-west door stone extends to the court road. At the east
    # gallery a red sidewalk runs between the grey apron and the kerb.
    # Use each retained street edge in plan and elevation, including its crown.
    def street_tree():
        verts, faces = [], []
        for face in roads.f:
            pts = [roads.v[i] for i in face]
            if (
                all(x < -373 for x, _, _ in pts)
                or all(x > -292 for x, _, _ in pts)
                or all(y < -850 for _, y, _ in pts)
                or all(y > -802 for _, y, _ in pts)
            ):
                continue
            start = len(verts)
            verts.extend(pts)
            faces.append(tuple(range(start, start + len(pts))))
        return BVHTree.FromPolygons(verts, faces)

    street = street_tree()
    site = Mesh()
    for east, left, right in [(False, -369.3, -355.75), (True, -824.20, -805.32)]:

        def xy(s, t):
            return (t, s) if east else (s, -t)

        @lru_cache(maxsize=None)
        def edge(s):
            lo, hi = (-303.0, -298.0) if east else (839.5, 845.0)

            def sample(t):
                return street.ray_cast((*xy(s, t), 30), (0, 0, -1))[0]

            if sample(lo) is not None or sample(hi) is None:
                raise ValueError(
                    f'Missing electrical approach road edge at {xy(s, hi)}'
                )
            for _ in range(22):
                mid = (lo + hi) / 2
                if sample(mid) is None:
                    lo = mid
                else:
                    hi = mid
            return hi, sample(hi + 0.008).z

        inner = -306.48 if east else 824.19

        def top(s, t):
            s = max(left, min(right, s))
            limit, height = edge(s)
            # A low upstand at the east sidewalk is visible in both panoramas.
            # The south apron reaches the paved court without a full-width step.
            outer = height + (0.10 if east else 0)
            start = outer + 0.035 if east else datum - 0.012
            start_at = inner if east else SILL_TOE
            k = min(1, max(0, (t - start_at) / (limit - start_at)))
            return start + (outer - start) * k

        stations = sorted({left, right, *range(int(left) + 1, int(right) + 1)})
        if not east:
            stations = sorted({*stations, SILL_LEFT, SILL_RIGHT})
            south_sill(site, datum - 0.012, colors['stone'])
        ends = [edge(s)[0] for s in stations]
        if east:
            core = [inner, left, max(ends), right]
        else:
            core = [left, -max(ends), right, -inner]
        area = [core[0] - 1.1, core[1] - 1.1, core[2] + 1.1, core[3] + 1.1]

        def bedding(x, y):
            s, t = (y, x) if east else (x, -y)
            # The east kerb rises above the street; keep subgrade below that
            # retained surface where the two rows meet.
            return top(s, t) - (0.145 if east else 0.055)

        terrain = grade_mesh(
            terrain, dict(extent=area, core=core, meshStep=1.0), target_height=bedding
        )

        def cross(s):
            stop, _ = edge(s)
            if east:
                return [inner, stop - 2.65, stop - 0.14, stop]
            return [inner, SILL_TOE, stop - 1.02, stop - 0.86, stop]

        finishes = (
            ('stone', 'pavingRed', 'curb')
            if east
            else ('stone', 'stone', 'bridgeJoint', 'stone')
        )
        for a, b in zip(stations, stations[1:]):

            def points(s):
                return [(*xy(s, t), top(s, t)) for t in cross(s)]

            av, bv = points(a), points(b)
            for j, mat in enumerate(finishes):
                if not east and j == 0 and SILL_LEFT <= a < SILL_RIGHT:
                    continue
                quad = [av[j], av[j + 1], bv[j + 1], bv[j]]
                for tri in (quad[:3], [quad[0], quad[2], quad[3]]):
                    site.face(tri, colors[mat], [(x, y) for x, y, _ in tri])

            def side(u, v, depth):
                site.face(
                    [u, (*u[:2], u[2] - depth), (*v[:2], v[2] - depth), v],
                    colors['curb'],
                )

            side(av[-1], bv[-1], 0.15 if east else 0.065)
            depth = 0.19 if east else 0.10
            if a == left:
                for u, v in zip(av, av[1:]):
                    side(u, v, depth)
            if b == right:
                for u, v in zip(bv, bv[1:]):
                    side(v, u, depth)
    return terrain, site
