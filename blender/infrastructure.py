"""Public road, grade-separated crossings and mapped lake bridges.

Positional geometry is OSM-derived. Section sizes and unsighted components are
explicit estimates in infrastructure.json, not a claim of engineering accuracy.
"""

import math

from geometry import Mesh
from new_east_neighbours import paving_height
from west_dorm_garden import front_section, grade


def frames(path):
    result = []
    for i, p in enumerate(path):
        a = path[max(0, i - 1)]
        b = path[min(len(path) - 1, i + 1)]
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        length = math.hypot(dx, dy)
        result.append((dx / length, dy / length))
    return result


def ribbon(m, path, left, right, mat, raise_z=0, axes=None):
    left = [left] * len(path) if isinstance(left, (int, float)) else left
    right = [right] * len(path) if isinstance(right, (int, float)) else right
    axes = axes or frames(path)
    for i, (a, b) in enumerate(zip(path, path[1:])):
        al, ar = sorted([left[i], right[i]])
        bl, br = sorted([left[i + 1], right[i + 1]])
        ux, uy = axes[i]
        vx, vy = axes[i + 1]
        m.face(
            [
                (a[0] - uy * al, a[1] + ux * al, a[2] + raise_z),
                (b[0] - vy * bl, b[1] + vx * bl, b[2] + raise_z),
                (b[0] - vy * br, b[1] + vx * br, b[2] + raise_z),
                (a[0] - uy * ar, a[1] + ux * ar, a[2] + raise_z),
            ],
            mat,
        )


def edge_box(m, a, b, offset, width, height, mat, zoffset=0, axes=None):
    if axes is None:
        axes = frames([a, b])
    (ux, uy), (vx, vy) = axes
    nx = -uy
    ny = ux
    mx = -vy
    my = vx
    oa, ob = (offset, offset) if isinstance(offset, (int, float)) else offset
    # Sloping box faces rather than horizontal blocks keep ramp curbs continuous.
    for side in [-1, 1]:
        off = oa + side * width / 2
        end = ob + side * width / 2
        face = [
            (a[0] + nx * off, a[1] + ny * off, a[2] + zoffset),
            (b[0] + mx * end, b[1] + my * end, b[2] + zoffset),
            (b[0] + mx * end, b[1] + my * end, b[2] + zoffset + height),
            (a[0] + nx * off, a[1] + ny * off, a[2] + zoffset + height),
        ]
        m.face(face if side < 0 else face[::-1], mat)
    m.face(
        [
            (
                a[0] + nx * (oa - width / 2),
                a[1] + ny * (oa - width / 2),
                a[2] + zoffset + height,
            ),
            (
                b[0] + mx * (ob - width / 2),
                b[1] + my * (ob - width / 2),
                b[2] + zoffset + height,
            ),
            (
                b[0] + mx * (ob + width / 2),
                b[1] + my * (ob + width / 2),
                b[2] + zoffset + height,
            ),
            (
                a[0] + nx * (oa + width / 2),
                a[1] + ny * (oa + width / 2),
                a[2] + zoffset + height,
            ),
        ],
        mat,
    )


def fence_panel(m, a, b, side, C, detail, axes, offsets):
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    length = math.hypot(dx, dy)
    nx = -dy / length
    ny = dx / length
    angle = math.atan2(dy, dx)
    edge_box(m, a, b, offsets, 0.35, 0.52, C['wallStone'], 0.14, axes)
    if not detail:
        return

    def point(t, h):
        return (
            a[0] * (1 - t)
            + b[0] * t
            - axes[0][1] * offsets[0] * (1 - t)
            - axes[1][1] * offsets[1] * t,
            a[1] * (1 - t)
            + b[1] * t
            + axes[0][0] * offsets[0] * (1 - t)
            + axes[1][0] * offsets[1] * t,
            a[2] * (1 - t) + b[2] * t + h,
        )

    x, y, z = point(0, 0.14)
    for h, w, d, hh in [
        (0.95, 0.48, 0.48, 1.9),
        (1.96, 0.61, 0.61, 0.14),
        (2.07, 0.51, 0.51, 0.1),
    ]:
        m.box(x, y, z + h, w, d, hh, C['wallStone'], angle)
    for h in [0.7, 1.78]:
        m.line(point(0, h), point(1, h), 0.038, C['fenceIron'], 4)
    # The 2023 photograph shows inward-leaning pickets between square uprights.
    count = max(6, round(length / 0.23))
    for j in range(1, count):
        t = j / count
        pinch = 0.5 + (t - 0.5) * 0.67
        m.line(point(t, 0.64), point(pinch, 1.24), 0.023, C['fenceIron'], 4)
        m.line(point(pinch, 1.24), point(t, 1.9), 0.023, C['fenceIron'], 4)
    for t in [0.05, 0.5, 0.95]:
        m.line(point(t, 0.64), point(t, 1.92), 0.032, C['fenceIron'], 4)
    # Schematic planting: photo-supported species / colour, not surveyed flower positions.
    if int(abs(a[0]) + abs(a[1])) % 4 == 0:
        for t in [0.28, 0.62, 0.85]:
            px, py, pz = point(t, 1.65)
            m.ellipsoid(px, py, pz, 0.65, 0.56, 0.5, C['leaf2'], 6, 3)
            m.ellipsoid(
                px + nx * 0.2,
                py + ny * 0.2,
                pz + 0.18,
                0.58,
                0.48,
                0.36,
                C['gateFlower'],
                6,
                3,
            )


def residence_fence_panel(m, a, b, offsets, axes, C, detail):
    """West-dorm street view 3: stone courses, capped piers and paired iron fans."""
    from new_east_neighbours import paving_height

    def station(t, inset, rise):
        ends = [
            (p[0] - uy * (off + inset), p[1] + ux * (off + inset), p[2] + rise)
            for p, (ux, uy), off in zip((a, b), axes, offsets)
        ]
        return tuple(u + (v - u) * t for u, v in zip(*ends))

    angle = math.atan2(b[1] - a[1], b[0] - a[0])
    # Pavement, wall footing and the lawn behind it share the road cross section.
    edge_box(m, a, b, offsets, 0.42, 0.65, C['wallStone'], -0.06, axes)
    edge_box(m, a, b, offsets, 0.48, 0.075, C['curb'], 0.59, axes)
    shoulders = []
    for t in (0, 1):
        foot = station(t, -0.70, 0.17)
        plinth = station(t, -0.20, 0.17)
        p = station(t, 0.18, 0.46)
        q = station(t, 0.83, 0.39)
        toe = station(t, 2.35, 0)
        shoulders.append(
            [foot, plinth, p, q, (*toe[:2], paving_height(*toe[:2]) - 0.22)]
        )
    for j, mat in [(0, 'pavingRed'), (2, 'grass'), (3, 'grass')]:
        a0, a1 = shoulders[0][j : j + 2]
        b0, b1 = shoulders[1][j : j + 2]
        m.face([a0, b0, b1, a1], C[mat])
    x, y, z = station(0, 0, 0)
    for width, bottom, top in [
        (0.48, 0.08, 2.12),
        (0.55, 2.12, 2.20),
        (0.67, 2.20, 2.30),
        (0.70, 2.30, 2.35),
    ]:
        m.box(
            x,
            y,
            z + (top + bottom) / 2,
            width,
            width,
            top - bottom,
            C['wallStone'],
            angle,
        )
    for level in (0.72, 1.99):
        m.line(station(0, 0, level), station(1, 0, level), 0.045, C['fenceIron'], 4)
    count = 8 if detail else 4
    for left, right in [(0.08, 0.49), (0.51, 0.92)]:
        for j in range(count):
            t = (j + 0.5) / count
            bottom = left + (right - left) * t
            outer = left if left < 0.5 else right
            top = outer + (bottom - outer) * 0.55
            m.line(
                station(bottom, 0, 0.72),
                station(top, 0, 1.99),
                0.022 if detail else 0.03,
                C['fenceIron'],
                4,
            )
    if detail:
        for t in (0.08, 0.50, 0.92):
            m.line(station(t, 0, 0.69), station(t, 0, 2.01), 0.034, C['fenceIron'], 4)
        # Warm ashlar facing with staggered joints and the original continuous cap.
        for row, (low, high) in enumerate(((0.17, 0.37), (0.38, 0.585))):
            stops = (
                (0, 0.23, 0.48, 0.73, 1) if row == 0 else (0, 0.12, 0.37, 0.62, 0.87, 1)
            )
            for j, (left, right) in enumerate(zip(stops, stops[1:])):
                finish = 'dormStoneWarm' if (j + row) % 3 == 0 else 'dormStonePale'
                m.face(
                    [
                        station(left + 0.002, -0.219, low),
                        station(right - 0.002, -0.219, low),
                        station(right - 0.002, -0.219, high),
                        station(left + 0.002, -0.219, high),
                    ],
                    C[finish],
                )


def residence_paving(mesh, path, axes, inner, outer, C, detail):
    """Muted red and grey paving fields along the Nongyuan Road frontage."""
    cuts = 4 if detail else 2
    grid = []
    for p, (ux, uy), start, end in zip(path, axes, inner, outer):
        row = []
        for j in range(cuts + 1):
            off = start + (end - start) * j / cuts
            row.append((p[0] - uy * off, p[1] + ux * off, p[2] + 0.17))
        grid.append(row)
    # Follow each end's road frame so adjacent tiles share their edges on bends.
    for i in range(cuts):
        for j in range(cuts):
            quad = []
            for t, col in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)):
                a, b = grid[0][col], grid[1][col]
                quad.append(tuple(x + (y - x) * t / cuts for x, y in zip(a, b)))
            mid = cuts // 2
            color = 'dormPaverGrey' if (i < mid) == (j < mid) else 'dormPaverRose'
            mesh.face(quad, C[color])


def road_chunk(chunk, C, detail):
    m = Mesh()
    p = chunk['path']
    axes = chunk['frames']
    sections = chunk['sections']
    fill_bays = set(chunk.get('fillBays', ()))
    carleft = [s[0] for s in sections]
    carright = [s[1] for s in sections]
    centers = [(a + b) / 2 for a, b in zip(carleft, carright)]
    ribbon(m, p, carleft, carright, C['asphalt'], axes=axes)
    for k, side in enumerate([-1, 1]):
        inner = [s[k] for s in sections]
        outer = [s[k + 2] for s in sections]
        tactile = [(a + b) / 2 for a, b in zip(inner, outer)]
        ribbon(
            m,
            p,
            [o - 0.175 for o in tactile],
            [o + 0.175 for o in tactile],
            C['tactile'],
            0.185,
            axes,
        )
        for i, (a, b) in enumerate(zip(p, p[1:])):
            edge_box(
                m, a, b, inner[i : i + 2], 0.25, 0.18, C['curb'], axes=axes[i : i + 2]
            )
            west_residence = (
                side == 1
                and chunk['id'] in ('infra-road-02', 'infra-road-03')
                and -554 < (a[1] + b[1]) / 2 < -450
            )
            segment = slice(i, i + 2)
            if i in fill_bays:
                # Close the raised approaches down to the surrounding ground,
                # leaving the span and the campus street below it fully open.
                wall = []
                for q, (tx, ty), off in zip(p[segment], axes[segment], outer[segment]):
                    x, y = q[0] - ty * off, q[1] + tx * off
                    wall.append(
                        [
                            (x, y, q[2] + 0.16),
                            (x, y, min(q[2], paving_height(x, y)) - 0.20),
                        ]
                    )
                m.face(
                    [wall[0][0], wall[1][0], wall[1][1], wall[0][1]][::side],
                    C['bridgeConcrete'],
                )
            if west_residence:
                residence_paving(
                    m,
                    p[segment],
                    axes[segment],
                    inner[segment],
                    outer[segment],
                    C,
                    detail,
                )
            else:
                ribbon(
                    m,
                    p[segment],
                    inner[segment],
                    outer[segment],
                    C['pavingRed'],
                    0.17,
                    axes[segment],
                )
            if (
                chunk['fence'][i][0 if side == -1 else 1]
                and chunk['fence'][i + 1][0 if side == -1 else 1]
            ):
                panel_axes = axes[i : i + 2]
                offsets = [o + side * 0.7 for o in outer[i : i + 2]]
                if west_residence:
                    residence_fence_panel(m, a, b, offsets, panel_axes, C, detail)
                else:
                    fence_panel(m, a, b, side, C, detail, panel_axes, offsets)
    # Dashed centre line is visible even in the inexpensive overview mesh.
    for i in range(0, len(p) - 1, 3):
        ribbon(
            m,
            p[i : i + 2],
            [o - 0.07 for o in centers[i : i + 2]],
            [o + 0.07 for o in centers[i : i + 2]],
            C['roadYellow'],
            0.035,
            axes[i : i + 2],
        )
    if detail:
        for offsets in [[o + 0.35 for o in carleft], [o - 0.35 for o in carright]]:
            ribbon(
                m,
                p,
                [o - 0.055 for o in offsets],
                [o + 0.055 for o in offsets],
                C['roadWhite'],
                0.035,
                axes,
            )
        for i in range(5, len(p) - 1, 10):
            x, y, z = p[i]
            ux, uy = axes[i]
            nx = -uy
            ny = ux
            off = sections[i][3] - 0.3
            x += nx * off
            y += ny * off
            m.cylinder(x, y, z + 3.8, 0.105, 7.2, C['lampMetal'], 8)
            m.line(
                (x, y, z + 7.3),
                (x - nx * 1.4, y - ny * 1.4, z + 7.6),
                0.065,
                C['lampMetal'],
                6,
            )
            m.box(
                x - nx * 1.5,
                y - ny * 1.5,
                z + 7.58,
                0.8,
                0.34,
                0.16,
                C['lampMetal'],
                math.atan2(ny, nx),
            )
            m.box(
                x - nx * 1.5,
                y - ny * 1.5,
                z + 7.48,
                0.62,
                0.24,
                0.025,
                C['lampGlass'],
                math.atan2(ny, nx),
            )
        for i in range(12, len(p) - 1, 22):
            x, y, z = p[i]
            ux, uy = axes[i]
            nx = -uy
            ny = ux
            for side in [-1, 1]:
                # Direction arrows, drawn as flat original geometry.
                off = centers[i] + side * (carright[i] - carleft[i]) * 0.24
                cx = x + nx * off
                cy = y + ny * off
                tx = -ux * side
                ty = -uy * side
                arrow = [
                    (cx + tx * 2, cy + ty * 2, z + 0.04),
                    (cx - tx * 0.1 + nx * 0.7, cy - ty * 0.1 + ny * 0.7, z + 0.04),
                    (cx + tx * 0.3 + nx * 0.18, cy + ty * 0.3 + ny * 0.18, z + 0.04),
                    (cx - tx * 1.5 + nx * 0.18, cy - ty * 1.5 + ny * 0.18, z + 0.04),
                    (cx - tx * 1.5 - nx * 0.18, cy - ty * 1.5 - ny * 0.18, z + 0.04),
                    (cx + tx * 0.3 - nx * 0.18, cy + ty * 0.3 - ny * 0.18, z + 0.04),
                    (cx - tx * 0.1 - nx * 0.7, cy - ty * 0.1 - ny * 0.7, z + 0.04),
                ]

                # Drape paint onto the same local slope as the asphalt ribbon.
                def paint_height(q):
                    along = (q[0] - x) * ux + (q[1] - y) * uy
                    neighbor = p[i + 1] if along >= 0 else p[i - 1]
                    run = (neighbor[0] - x) * ux + (neighbor[1] - y) * uy
                    return (q[0], q[1], z + (neighbor[2] - z) * along / run + 0.045)

                arrow = [paint_height(q) for q in arrow]
                m.face(arrow if side < 0 else arrow[::-1], C['roadWhite'])
    return m


def dorm_frontage_bank(walls, walkpath, axes, width, grass):
    bank = []
    for w, (tx, ty) in zip(walkpath, axes):
        x, y = w[0] - ty * width, w[1] + tx * width
        sections = grade()['frontWalk']
        if not sections[0][0] <= x <= sections[-1][0]:
            return False
        edge_y, edge_z, _ = front_section(x)
        if edge_y <= y:
            return False
        bank.append([(x, y, w[2]), (x, edge_y, edge_z)])
    walls.face([bank[0][0], bank[1][0], bank[1][1], bank[0][1]], grass)
    return True


def dorm_street_pavement(mesh, points, walk, axes, side, inner, outer, start_x, C):
    a, c = points
    # Ease the broad apron at the join into the narrow roadside kerb.
    # The paved surface falls gently towards it for drainage.
    profiles = []
    for point, w, (tx, ty) in zip(points, walk, axes):
        blend = min(1, max(0, (point[0] - start_x) / 5))
        blend *= min(1, max(0, (0.20 - (w[2] - point[2])) / 0.05))
        boundary = inner - (inner - 5.28) * blend
        lip = point[2] + 0.15 - 0.025 * blend
        profiles.append(
            [
                (point[0] - ty * side * off, point[1] + tx * side * off, z)
                for off, z in ((5, lip), (boundary, lip), (outer, w[2]))
            ]
        )
    for k, finish in enumerate(('curb', 'pavingRed')):
        face = [
            profiles[0][k],
            profiles[1][k],
            profiles[1][k + 1],
            profiles[0][k + 1],
        ]
        mesh.face(face[::side], C[finish])
    lip_a, lip_c = profiles[0][0], profiles[1][0]
    face = [
        (*lip_a[:2], a[2] - 0.04),
        (*lip_c[:2], c[2] - 0.04),
        lip_c,
        lip_a,
    ]
    mesh.face(face[::side], C['curb'])


def bocui_bank(mesh, points, walk, axes, outer, side, bridge, grass):
    # Continue the planted slope behind the portal wing, past the end of the
    # span. Sample perpendicular distance to the upper road on this skew bridge.
    ab, cd = bridge['upper']
    dx, dy = cd[0] - ab[0], cd[1] - ab[1]
    length = math.hypot(dx, dy)
    rows = []
    on_slope = []
    for q, w, (tx, ty) in zip(points, walk, axes):
        section = []
        active = False
        for offset in (outer, outer + 3, outer + 6, length / 2 + 1, length / 2 + 5):
            x, y = q[0] - ty * side * offset, q[1] + tx * side * offset
            gap = (
                abs((-(x - ab[0]) * dy + (y - ab[1]) * dx) / length)
                - bridge['deckWidth'] / 2
            )
            t = min(1, max(0, gap / 12))
            t = t * t * (3 - 2 * t)
            active |= t < 1
            soil = paving_height(x, y) - 0.12
            at_edge = max(w[2] + 0.02, q[3] + 0.12)
            blend = min(1, (offset - outer) / 5)
            foot = at_edge * (1 - blend) + soil * blend
            z = (1 - t) * (bridge['deckElevation'] - 0.20) + t * foot
            section.append((x, y, z))
        rows.append(section)
        on_slope.append(active)
    if any(on_slope):
        for left, right, far_left, far_right in zip(
            rows[0], rows[0][1:], rows[1], rows[1][1:]
        ):
            mesh.face([left, far_left, far_right, right][::side], grass)
        for row, raised, sign in zip(rows, on_slope, (side, -side)):
            if not raised:
                for left, right in zip(row, row[1:]):
                    toe_l = (*left[:2], min(left[2], paving_height(*left[:2])) - 0.65)
                    toe_r = (
                        *right[:2],
                        min(right[2], paving_height(*right[:2])) - 0.65,
                    )
                    mesh.face([left, right, toe_r, toe_l][::sign], grass)
        for row in rows:
            # The outside cut meets the DEM at the foot of the slope.
            end = row[-1]
            row.append((*end[:2], min(end[2], paving_height(*end[:2]) - 0.40)))
        mesh.face([rows[0][-2], rows[1][-2], rows[1][-1], rows[0][-1]][::side], grass)
    return [r[0][2] for r in rows]


def approaches(b, C):
    m = Mesh()
    road = Mesh()
    walks = Mesh()
    walls = Mesh()
    path = b['underpass']
    axes = frames(path)
    walk = b['pedestrian']
    walkpath = walk['path']
    inner = walk['innerOffset']
    outer = inner + walk['width']
    trim = b.get('joinTrim', 0)
    if trim:
        path = path[trim:-trim]
        axes = axes[trim:-trim]
        walkpath = walkpath[trim:-trim]
    ba, bc = b['upper']
    dx = bc[0] - ba[0]
    dy = bc[1] - ba[1]
    length = math.hypot(dx, dy)

    def covered_segment(a, c, side, local_axes):
        points = []
        for p, (ux, uy) in zip([a, c], local_axes):
            x = p[0] - uy * side * walk['cutHalfWidth'] - ba[0]
            y = p[1] + ux * side * walk['cutHalfWidth'] - ba[1]
            points.append(((x * dx + y * dy) / length, (-x * dy + y * dx) / length))
        return (
            min(q[0] for q in points) < length + 0.5
            and max(q[0] for q in points) > -0.5
            and min(q[1] for q in points) < b['deckWidth'] / 2 + 0.5
            and max(q[1] for q in points) > -b['deckWidth'] / 2 - 0.5
        )

    ribbon(road, path, -5, 5, C['asphalt'], axes=axes)
    for side in [-1, 1]:
        for i, (a, c) in enumerate(zip(path, path[1:])):
            ux, uy = axes[i]
            vx, vy = axes[i + 1]
            wa, wc = walkpath[i : i + 2]
            bay_axes = axes[i : i + 2]
            street = b['id'] == 'bocui-bridge'
            if street:
                dorm_street_pavement(
                    walks, (a, c), (wa, wc), bay_axes, side, inner, outer, path[0][0], C
                )
            else:
                ribbon(road, [a, c], side * 5, side * inner, C['curb'], 0.15, bay_axes)
                ribbon(
                    walks,
                    [wa, wc],
                    side * inner,
                    side * outer,
                    C['path'],
                    axes=bay_axes,
                )
            covered = covered_segment(a, c, side, axes[i : i + 2])
            # Terminate the outer wall inside the edge beam so their junction
            # closes, while staying below the public-road wearing surface.
            ceiling = b['deckElevation'] - 0.2
            wall_top = tuple(
                min(p[3] + 0.25, ceiling) if covered else p[3] + 0.25 for p in [a, c]
            )
            if street:
                wall_top = bocui_bank(
                    walls, (a, c), (wa, wc), bay_axes, outer, side, b, C['grass']
                )
            # On the dorm side a planted bank rises from the brick footway
            # to the existing upper walk. Close its toe at the actual road edge.
            planted = (
                street
                and side == 1
                and dorm_frontage_bank(walls, (wa, wc), bay_axes, outer, C['grass'])
            )
            # Inner wall supports the raised walk; outer wall meets the terrain.
            # Neither the walk nor its railing inherits the uncut DEM elevation.
            for offset, lower, upper in [
                (inner, (a[2] - 0.1, c[2] - 0.1), (wa[2], wc[2])),
                (
                    outer,
                    tuple(
                        min(w[2] - 0.15, q[3] - 0.55) if street else w[2] - 0.15
                        for w, q in ((wa, a), (wc, c))
                    ),
                    wall_top,
                ),
            ]:
                if (planted and offset == outer) or (street and offset == inner):
                    continue
                off = side * offset
                wall = [
                    (a[0] - uy * off, a[1] + ux * off, lower[0]),
                    (c[0] - vy * off, c[1] + vx * off, lower[1]),
                    (c[0] - vy * off, c[1] + vx * off, upper[1]),
                    (a[0] - uy * off, a[1] + ux * off, upper[0]),
                ]
                walls.face(wall if side > 0 else wall[::-1], C['bridgeConcrete'])
            if not street:
                edge_box(
                    walls, wa, wc, side * inner, 0.24, 0.10, C['curb'], axes=bay_axes
                )
            # The outer cap also covers the small construction joint to the cut.
            top = [a[0], a[1], a[3]]
            top2 = [c[0], c[1], c[3]]
            # An untrimmed terrain-height cap would cut across the public road.
            if not covered and not planted and not street:
                edge_box(
                    walls,
                    top,
                    top2,
                    side * walk['cutHalfWidth'],
                    0.3,
                    0.25,
                    C['curb'],
                    axes=axes[i : i + 2],
                )
            if not street:
                edge_box(road, a, c, side * 5, 0.22, 0.18, C['curb'], axes=bay_axes)
    crossing = set()
    if b['id'] == 'bocui-bridge':
        # Street views place the zebra crossing just east of the central doorway.
        mid = min(range(len(path)), key=lambda i: abs(path[i][0] - 101.5))
        crossing = {mid - 1, mid}
        for i in sorted(crossing):
            for stripe in range(-5, 6):
                offset = stripe * 0.86
                ribbon(
                    road,
                    path[i : i + 2],
                    offset - 0.23,
                    offset + 0.23,
                    C['roadWhite'],
                    0.014,
                    axes[i : i + 2],
                )
    for i in range(0, len(path) - 1, 4):
        if i not in crossing:
            ribbon(
                road,
                path[i : i + 2],
                -0.07,
                0.07,
                C['roadYellow'],
                0.014 if b['id'] == 'bocui-bridge' else 0.035,
                axes[i : i + 2],
            )
    if junction := b.get('sideJunction'):
        from north_underpass import road_height_sampler
        from road_display_cleanup import trim_mesh

        m.bank_height = road_height_sampler(walls, lambda x, y: -100)
        walks, _ = trim_mesh(walks, [junction['cut']])
        walls, _ = trim_mesh(walls, [junction['cut']])
    m.add_part('下穿车行道与排水边带', road)
    m.add_part('两侧抬高人行步道', walks)
    m.add_part('步道支挡与外侧挡墙', walls)
    return m


def fitted_deck(b, C, detail, cx, cy, angle):
    """A constrained bridge uses the same section edges as its wearing surface."""
    m = Mesh()
    z = b['deckElevation']
    slab = b['slabThickness']
    g = b['deckGeometry']
    m.extrude(
        [g['rings']], [g['triangles']], z - slab, slab - 0.04, C['bridgeConcrete']
    )
    flat = [p for ring in g['rings'] for p in ring[:-1]]
    for i in range(0, len(g['triangles']), 3):
        m.face(
            [
                (flat[k][0], flat[k][1], z - slab)
                for k in g['triangles'][i : i + 3][::-1]
            ],
            C['bridgeConcrete'],
        )
    profile = b['roadProfile']
    ca = math.cos(angle)
    sa = math.sin(angle)
    path = [
        ((p[0] - cx) * ca + (p[1] - cy) * sa, -(p[0] - cx) * sa + (p[1] - cy) * ca, z)
        for p in profile['path']
    ]
    axes = [(u * ca + v * sa, -u * sa + v * ca) for u, v in profile['frames']]
    sections = profile['sections']
    for k, side in enumerate([-1, 1]):
        outer = [s[k + 2] for s in sections]
        railing = []
        for p, (ux, uy), off in zip(path, axes, outer):
            railing.append(
                (p[0] - uy * (off - side * 0.16), p[1] + ux * (off - side * 0.16), z)
            )
        for i, (a, c) in enumerate(zip(path, path[1:])):
            edge_box(
                m,
                a,
                c,
                [o - side * 0.2 for o in outer[i : i + 2]],
                0.55,
                0.6,
                C['bridgeEdge'],
                -0.65,
                axes[i : i + 2],
            )
            edge_box(
                m,
                a,
                c,
                [o - side * 0.16 for o in outer[i : i + 2]],
                0.3,
                0.5,
                C['curb'],
                0.03,
                axes[i : i + 2],
            )
        # Subdivide rail bays without shifting their endpoints off the deck edge.
        for a, c in zip(railing, railing[1:]):
            count = max(1, math.ceil(math.dist(a, c) / 2))
            for j in range(count):
                start = tuple(a[k] + (c[k] - a[k]) * j / count for k in range(3))
                end = tuple(a[k] + (c[k] - a[k]) * (j + 1) / count for k in range(3))
                if detail:
                    m.box(start[0], start[1], z + 0.85, 0.09, 0.09, 1.1, C['lampMetal'])
                    for h in [0.62, 1.3]:
                        m.line(
                            (start[0], start[1], z + h),
                            (end[0], end[1], z + h),
                            0.033,
                            C['lampMetal'],
                            4,
                        )
                    for h0, h1 in [(0.64, 1.23), (1.23, 0.64)]:
                        m.line(
                            (start[0], start[1], z + h0),
                            (end[0], end[1], z + h1),
                            0.027,
                            C['lampMetal'],
                            4,
                        )
                else:
                    m.line(
                        (start[0], start[1], z + 0.9),
                        (end[0], end[1], z + 0.9),
                        0.04,
                        C['lampMetal'],
                        4,
                    )
        if detail:
            m.box(
                railing[-1][0],
                railing[-1][1],
                z + 0.85,
                0.09,
                0.09,
                1.1,
                C['lampMetal'],
            )
    if detail:
        for fraction in [0.1, 0.3, 0.5, 0.7, 0.9]:
            offsets = [s[0] + (s[1] - s[0]) * fraction for s in sections]
            for i, (a, c) in enumerate(zip(path, path[1:])):
                edge_box(
                    m,
                    a,
                    c,
                    offsets[i : i + 2],
                    0.24,
                    0.25,
                    C['bridgeEdge'],
                    -slab - b['beamDepth'],
                    axes[i : i + 2],
                )
                ribbon(
                    m,
                    [a, c],
                    [o - 0.12 for o in offsets[i : i + 2]],
                    [o + 0.12 for o in offsets[i : i + 2]],
                    C['bridgeEdge'],
                    -slab - b['beamDepth'],
                    axes[i : i + 2],
                )
                m.f[-1] = m.f[-1][::-1]
    return m


def bridge(b, C, detail):
    m = Mesh()
    a, c = b['upper']
    dx = c[0] - a[0]
    dy = c[1] - a[1]
    length = math.hypot(dx, dy)
    angle = math.atan2(dy, dx)
    cx = (a[0] + c[0]) / 2
    cy = (a[1] + c[1]) / 2
    z = b['deckElevation']
    width = b['deckWidth']
    floor = b['floorElevation']
    slab = b['slabThickness']
    deck = fitted_deck(b, C, detail, cx, cy, angle) if 'deckGeometry' in b else Mesh()
    if 'deckGeometry' not in b:
        deck.box(
            0, 0, z - (slab + 0.04) / 2, length, width, slab - 0.04, C['bridgeConcrete']
        )
    for abutment in b['abutments']:
        # Abutments support the slab from below; their old road-height caps
        # overlapped the continuous asphalt and produced mottled end seams.
        deck.extrude(
            [abutment['rings']],
            [abutment['triangles']],
            floor,
            z - slab - floor,
            C['bridgeConcrete'],
        )
    for side in [] if 'deckGeometry' in b else [-1, 1]:
        deck.box(
            0,
            side * (width / 2 - 0.2),
            z - 0.35,
            length + 0.3,
            0.55,
            0.6,
            C['bridgeEdge'],
        )
        # Vehicle parapets / railings above the public road.
        deck.box(0, side * (width / 2 - 0.16), z + 0.28, length, 0.3, 0.5, C['curb'])
        if detail:
            for xx in range(math.ceil(-length / 2), math.floor(length / 2), 2):
                deck.box(
                    xx,
                    side * (width / 2 - 0.16),
                    z + 0.85,
                    0.09,
                    0.09,
                    1.1,
                    C['lampMetal'],
                )
            for h in [0.62, 1.3]:
                deck.box(
                    0,
                    side * (width / 2 - 0.16),
                    z + h,
                    length,
                    0.065,
                    0.065,
                    C['lampMetal'],
                )
            for xx in range(math.ceil(-length / 2), math.floor(length / 2) - 2, 2):
                for sign in [-1, 1]:
                    deck.line(
                        (
                            xx,
                            side * (width / 2 - 0.16),
                            z + 0.64 if sign == 1 else z + 1.23,
                        ),
                        (
                            xx + 2,
                            side * (width / 2 - 0.16),
                            z + 1.23 if sign == 1 else z + 0.64,
                        ),
                        0.027,
                        C['lampMetal'],
                        4,
                    )
        else:
            deck.box(
                0,
                side * (width / 2 - 0.16),
                z + 0.9,
                length,
                0.08,
                0.08,
                C['lampMetal'],
            )
    if detail and 'deckGeometry' not in b:
        # The wearing surface comes only from the continuous road ribbon.
        # Unsurveyed transverse joint boxes used to sit on top of that surface.
        for yy in [-4, -2, 0, 2, 4]:
            deck.box(
                0,
                yy,
                z - slab - b['beamDepth'] + 0.125,
                length - 1,
                0.24,
                0.25,
                C['bridgeEdge'],
            )
    deck.rotate_z(0, 0, angle)
    deck.v = [(x + cx, y + cy, h) for x, y, h in deck.v]
    m.add_part('桥面梁板与桥台', deck)
    path = b['underpass']
    axes = frames(path)
    if b['id'] == 'bocui-bridge':
        # Two lateral openings carry the flat brick sidewalks through the bridge.
        ux, uy = axes[len(axes) // 2]
        span = b['deckWidth'] / abs((dx * uy - dy * ux) / length)
        for side in (-1, 1):
            off = 5.58 * side
            x, y = b['center']
            # Intersect the offset street with the oblique bridge centreline.
            along = -off * (dx * ux + dy * uy) / (dx * uy - dy * ux)
            m.box(
                x - uy * off + ux * along,
                y + ux * off + uy * along,
                (z - slab + floor) / 2,
                span,
                0.50,
                z - slab - floor,
                C['bridgeConcrete'],
                math.atan2(uy, ux),
            )
    if b['id'] == 'chongzuo-bridge':
        # Historical photo shows a median pier. Align it with the campus road.
        bearing = math.radians(b['frontBearing'])
        ux = math.sin(bearing)
        uy = math.cos(bearing)
        m.box(
            *b['center'],
            (z - slab + floor) / 2,
            16,
            0.65,
            z - slab - floor,
            C['bridgeConcrete'],
            math.atan2(uy, ux),
        )
    if detail:
        rails = Mesh()
        drains = Mesh()
        walk = b['pedestrian']
        walkpath = walk['path']
        for i, (a, c) in enumerate(zip(path, path[1:])):
            trim = b.get('joinTrim', 0)
            if i < trim or i >= len(path) - 1 - trim:
                continue
            if b['id'] == 'bocui-bridge':
                continue
            ux, uy = axes[i]
            theta = math.atan2(uy, ux)
            for side in [-1, 1]:
                off = side * walk['innerOffset']
                vx, vy = axes[i + 1]
                start = (a[0] - uy * off, a[1] + ux * off, walkpath[i][2] + 0.1)
                end = (c[0] - vy * off, c[1] + vx * off, walkpath[i + 1][2] + 0.1)

                def rail_point(t, h):
                    return tuple(
                        start[k] * (1 - t) + end[k] * t + (h if k == 2 else 0)
                        for k in range(3)
                    )

                rails.cylinder(*rail_point(0, 0.58), 0.045, 1.16, C['lampMetal'], 6)
                if i == len(path) - 2:
                    rails.cylinder(*rail_point(1, 0.58), 0.045, 1.16, C['lampMetal'], 6)
                for h in [0.12, 1.12]:
                    rails.line(
                        rail_point(0, h), rail_point(1, h), 0.04, C['lampMetal'], 5
                    )
                # Chongzuo's photographed rail has alternating solid round panels
                # and upright bars. Other unsighted bridge rails stay generic.
                segment = math.dist(start[:2], end[:2])
                for t in [0.16, 0.32, 0.68, 0.84]:
                    rails.line(
                        rail_point(t, 0.12),
                        rail_point(t, 1.08),
                        0.019,
                        C['lampMetal'],
                        4,
                    )
                if b['id'] == 'chongzuo-bridge':
                    radius = 0.39 if i % 2 == 0 else 0.19
                    circle = [
                        rail_point(
                            0.5 + radius * math.cos(j * math.tau / 16) / segment,
                            0.6 + radius * math.sin(j * math.tau / 16),
                        )
                        for j in range(16)
                    ]
                    rails.face(circle, C['curb'])
                    rails.face(circle[::-1], C['curb'])
                    for u, v in zip(circle, circle[1:] + circle[:1]):
                        rails.line(u, v, 0.022, C['lampMetal'], 4)
                # Covered drainage channel and paired drain slots beside the retaining wall.
                qx = a[0] - uy * side * 5.7
                qy = a[1] + ux * side * 5.7
                drains.box(qx, qy, a[2] + 0.2, 1.6, 0.68, 0.12, C['drainStone'], theta)
                for t in [-0.42, 0, 0.42]:
                    drains.box(
                        qx + ux * t,
                        qy + uy * t,
                        a[2] + 0.267,
                        0.3,
                        0.10,
                        0.014,
                        C['bridgeJoint'],
                        theta,
                    )
        m.add_part(
            '坡道圆纹金属护栏（照片参照）'
            if b['id'] == 'chongzuo-bridge'
            else '坡道金属护栏（估算）',
            rails,
        )
        m.add_part('下穿排水沟与盖板', drains)
        for side in [-1, 1]:
            ux = dx / length
            uy = dy / length
            for j in [-0.28, 0.28]:
                x = cx + ux * length * j - uy * side * 4
                y = cy + uy * length * j + ux * side * 4
                m.box(x, y, z - slab - 0.16, 0.65, 0.26, 0.08, C['lampGlass'], angle)
    return m


def lake_bridge(b, C, detail):
    m = Mesh()
    path = b['path']
    half = b['width'] / 2
    ribbon(m, path, -half, half, C['bridgeConcrete'])
    for side in [-1, 1]:
        for a, c in zip(path, path[1:]):
            edge_box(m, a, c, side * half, 0.2, 0.16, C['curb'], -0.16)
            edge_box(m, a, c, side * half, 0.1, 0.1, C['lampMetal'], 1.03)
        if detail:
            for p, (ux, uy) in zip(path, frames(path)):
                x = p[0] - uy * side * half
                y = p[1] + ux * side * half
                m.cylinder(x, y, p[2] + 0.52, 0.05, 1.04, C['lampMetal'], 6)
            ribbon(
                m,
                path,
                side * (half - 0.45),
                side * (half - 0.2),
                C['pavingRed'],
                0.025,
            )
    for i in range(1, len(path) - 1, max(2, len(path) // 3)):
        x, y, z = path[i]
        bottom = b['waterLevel'] - 1
        m.box(
            x,
            y,
            (z + bottom) / 2,
            0.65,
            b['width'] * 0.75,
            z - bottom,
            C['bridgeConcrete'],
            math.atan2(path[-1][1] - path[0][1], path[-1][0] - path[0][0]),
        )
    return m
