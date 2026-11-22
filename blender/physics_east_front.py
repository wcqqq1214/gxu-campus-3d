"""Street elevation of way/957404989. Y increases from photo left to right.

Hualan 14611 and the designer's oblique aerial locate the two white end
walls on different storeys. The connector steps back below the roofline.
"""

import math

from geometry import MATERIALS, tile_material
from physics_pilotis import PORTAL, SOUTH_FRAME_BAY, UPPER_SOFFIT
from physics_right_wall import SOUTH as NAME_START
from physics_right_wall import trim_shell

JOINT = (-887.95, -881.85)
LINK_TOP = 26.55


# Keep the existing lower-storey grid and shift rooftop fittings rigidly.
SOURCE_ROOF = 29.7
ADOPTED_ROOF = 36.1
UPPER_BASE = 16.52


def source_grid(building):
    form = building['form']
    return dict(
        building,
        height=SOURCE_ROOF,
        form=dict(
            form,
            height=SOURCE_ROOF,
            parts=[dict(part, height=SOURCE_ROOF) for part in form['parts']],
            facades=[dict(f, height=SOURCE_ROOF) for f in form['facades']],
            roofDome=dict(form['roofDome'], baseHeight=SOURCE_ROOF),
        ),
    )


def fit_upper_storeys(mesh, z, roof):
    # Cached pre-calibration catalogues still carry nine times 3.3 metres.
    delta = (ADOPTED_ROOF if math.isclose(roof, SOURCE_ROOF) else roof) - SOURCE_ROOF

    def raised(h):
        if h <= z + UPPER_BASE:
            return h
        if h >= z + SOURCE_ROOF:
            return h + delta
        return h + delta * (h - z - UPPER_BASE) / (SOURCE_ROOF - UPPER_BASE)

    mesh.v = [(x, y, raised(h)) for x, y, h in mesh.v]


def wall_x(f, y):
    a, b = f['start'], f['end']
    return a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1])


def split(poly, axis, bound):
    """Split a convex polygon at a campus-coordinate plane, retaining winding."""
    sides = ([], [])
    for a, b in zip(poly, poly[1:] + poly[:1]):
        da, db = a[axis] - bound, b[axis] - bound
        if da <= 0:
            sides[0].append(a)
        if da >= 0:
            sides[1].append(a)
        if da * db < 0:
            t = da / (da - db)
            p = tuple(x + t * (y - x) for x, y in zip(a, b))
            for side in sides:
                side.append(p)
    return sides


def remove_region(mesh, bounds, select=None):
    # Shell and parapet are untextured convex faces at this construction stage.
    # Retain untouched indices; produce only pieces outside all half-spaces.
    assert not mesh.face_uvs, (
        'Physics shell relief expects plain masonry and roof faces'
    )
    faces, materials = mesh.f, mesh.m
    mesh.f, mesh.m = [], []
    for indices, mat in zip(faces, materials):
        poly = [mesh.v[i] for i in indices]
        if (select is not None and not select(poly)) or any(
            max(p[k] * direction for p in poly) <= value * direction + 1e-7
            for k, value, direction in bounds
        ):
            mesh.f.append(indices)
            mesh.m.append(mat)
            continue
        for axis, bound, direction in bounds:
            if min(p[axis] * direction for p in poly) >= bound * direction - 1e-7:
                continue
            low, high = split(poly, axis, bound)
            keep, poly = (low, high) if direction == 1 else (high, low)
            if len(keep) >= 3:
                mesh.face(keep, mat)
            if len(poly) < 3:
                break


def east_shell(body, roof, b, z, C):
    """Cut the upper connector and the name-wall return before grouping the shell."""
    f = {f['edge']: f for f in b['form']['facades']}
    south, north = JOINT
    # This strip is strictly inside the south lightwell's Y range. Its western
    # boundary is facade 2, so no other occupied wing is shortened.
    gap = [(1, south, 1), (1, north, -1), (0, -649, 1)]
    for part in (body, roof):
        remove_region(part, gap + [(2, z + LINK_TOP, 1)])
    # Shift only the front of the glazed link inward. The court-side wall stays.
    link_x = -641.10
    remove_region(body, gap + [(0, link_x, 1), (2, z + UPPER_SOFFIT + 0.19, 1)])
    # Middle gallery floor and soffit already exist below this cut.
    base = UPPER_SOFFIT + 0.19
    for y, north_end in ((south, False), (north, True)):
        east, west = wall_x(f[16], y), wall_x(f[2], y)
        for x0, x1, h in ((west, link_x, LINK_TOP), (link_x, east, base)):
            pts = [(x0, y, z + h), (x0, y, z + 29.7), (x1, y, z + 29.7), (x1, y, z + h)]
            body.face(pts if not north_end else pts[::-1], C['libraryTrim'])
        # Return the parapet across the clipped roof at each end.
        roof.box(
            (east + west) / 2,
            y + (0.12 if north_end else -0.12),
            z + 30.10,
            east - west,
            0.24,
            0.80,
            C['white'],
        )
    body.face(
        [
            (wall_x(f[2], south), south, z + LINK_TOP),
            (link_x, south, z + LINK_TOP),
            (link_x, north, z + LINK_TOP),
            (wall_x(f[2], north), north, z + LINK_TOP),
        ],
        C['bridgeConcrete'],
    )
    body.face(
        [
            (link_x, south, z + base),
            (link_x, north, z + base),
            (link_x, north, z + LINK_TOP),
            (link_x, south, z + LINK_TOP),
        ],
        C['huicuiFrame'],
    )
    south = PORTAL[1]
    # The side of the existing stair opening meets the new recessed cheek.
    # Include its original face in the cut, while preserving the lower bearing.
    remove_region(
        body,
        [
            (1, south - 0.002, 1),
            (1, NAME_START, -1),
            (0, -642, 1),
            (2, z + 3.30, 1),
            (2, z + 13.02, -1),
        ],
        select=lambda poly: (
            all(abs(x - wall_x(f[16], y)) < 0.0001 for x, y, _ in poly)
            or all(abs(y - south) < 0.0001 for _, y, _ in poly)
        ),
    )

    trim_shell(body, z, remove_region)


def far_panel(C, name, texture, alpha=False):
    if name not in C:
        tile_material(C, name, texture, (0.3, 0.33, 0.35))
        mat = MATERIALS[C[name]]
        shader = mat.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Roughness'].default_value = 0.38
        if alpha:
            image = next(n for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE')
            mat.node_tree.links.new(image.outputs['Alpha'], shader.inputs['Alpha'])
            mat.surface_render_method = 'DITHERED'
    return C[name]


def street_registers(mesh, f, z, C, detail):
    south, north = sorted((f['start'][1], f['end'][1]))
    white, tile = 'libraryTrim', 'huicuiFrame'

    def quad(a, b, lo, hi, d, mat):
        mesh.face(
            [
                (wall_x(f, y) + d, y, z + h)
                for y, h in ((a, lo), (b, lo), (b, hi), (a, hi))
            ],
            C[mat],
        )

    def block(a, b, lo, hi, back, front, mat):
        # Closed fascia with returns and real underside, on the nearly N/S edge.
        x0, x1 = wall_x(f, a), wall_x(f, b)
        mesh.box(
            (x0 + x1 + back + front) / 2,
            (a + b) / 2,
            z + (lo + hi) / 2,
            math.hypot(b - a, x1 - x0),
            front - back,
            hi - lo,
            C[mat],
            math.atan2(b - a, x1 - x0),
        )

    def lights(a, b, lo, hi, count, rows, feature_pair=False):
        if not detail:
            mat = far_panel(C, 'physicsFarBays', 'physics-far-bay.png')
            # Same 14/86 percent bay edges and 20/80 percent spandrels
            # as the near mesh. Only the unresolvable five-centimetre
            # relief is baked into the far material.
            mesh.face(
                [
                    (wall_x(f, y) + 0.235, y, z + h)
                    for y, h in ((a, lo), (b, lo), (b, hi), (a, hi))
                ],
                mat,
                [(0, 0), (count, 0), (count, rows), (0, rows)],
            )
            return
        pitch = (b - a) / count
        step = (hi - lo) / rows
        for row in range(rows):
            base = lo + row * step
            sill, head = base + 0.20 * step, base + 0.80 * step
            # Continuous opaque spandrel / masonry piers surround the lights.
            quad(a, b, base, sill, 0.235, tile)
            quad(a, b, head, base + step, 0.235, tile)
            for j in range(count):
                left = a + j * pitch
                l, r = left + 0.14 * pitch, left + 0.86 * pitch
                quad(left, l, sill, head, 0.235, tile)
                quad(r, left + pitch, sill, head, 0.235, tile)
                quad(l, r, sill, head, 0.185, 'residenceGlass')
                # Rows at the two central stair lights show horizontal louvres.
                if feature_pair and j in (13, 14):
                    for ratio in (0.28, 0.61):
                        h = sill + (head - sill) * ratio
                        quad(l, r, h, h + 0.085, 0.21, 'bridgeJoint')
                elif detail:
                    for k in (1, 2):
                        mid = l + (r - l) * k / 3
                        quad(mid - 0.032, mid + 0.032, sill, head, 0.216, 'fenceIron')
                    for ratio in (0.16, 0.76):
                        h = sill + (head - sill) * ratio
                        quad(l, r, h, h + 0.058, 0.221, 'fenceIron')

    j0, j1 = JOINT
    lo, hi = 16.52, 30.50
    # The slit glazing and caps are physically set behind the two stone piers.
    for left, right in ((south, -903.95), (-902.39, j0)):
        block(left, right, lo, hi, -0.04, 0.82, white)
    block(-903.95, -902.39, hi - 1.65, hi, -0.04, 0.82, white)
    block(-903.95, -902.39, lo, lo + 0.54, -0.04, 0.82, white)
    quad(-903.95, -902.39, lo + 0.54, hi - 1.65, 0.12, 'libraryMullion')
    for k in range(4):
        h = lo + 0.86 + k * 3.10
        quad(-903.77, -902.57, h, h + 1.73, 0.14, 'residenceGlass')
        if detail:
            quad(-903.2, -903.14, h, h + 1.73, 0.155, 'fenceIron')
    # Real connector rear plane, with its own roof one register below the eaves.
    for row in range(3):
        low = lo + row * 3.25 + 0.45
        for k in range(3):
            a = j0 + k * (j1 - j0) / 3 + 0.12
            b = a + (j1 - j0) / 3 - 0.24
            mesh.face(
                [
                    (-641.085, y, z + h)
                    for y, h in ((a, low), (b, low), (b, low + 2.27), (a, low + 2.27))
                ],
                C['residenceGlass'],
            )
    block(j1, j1 + 0.69, lo, hi, -0.12, 1.02, white)
    grid_start, grid_end = j1 + 0.69, north - 1.70
    lights(grid_start, grid_end, lo + 0.53, hi - 1.65, 31, 4, True)
    block(j1, north + 0.08, hi - 1.65, hi, -0.32, 1.45, white)
    block(j1, north + 0.08, lo, lo + 0.53, -0.32, 1.38, white)
    quad(grid_end, north, lo + 0.53, hi - 1.65, 0.16, tile)
    # Independent lower frame: retain the surveyed sky bay and the stair pier.
    block(south, PORTAL[0] + 0.30, 11.94, 13.22, -0.18, 0.87, white)
    block(south, south + 1.22, 3.3, 11.94, -0.06, 0.83, white)
    block(south, SOUTH_FRAME_BAY, 3.26, 3.60, -0.09, 0.82, white)
    lights(south + 1.22, SOUTH_FRAME_BAY, 3.60, 11.94, 25, 3)
