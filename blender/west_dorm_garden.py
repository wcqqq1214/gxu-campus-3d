"""Entrance lodge and cast-iron boundary beside the west residence gardens."""

import json
import math
from functools import lru_cache
from pathlib import Path

from geometry import Mesh
from low_planting import profiled_hedge
from new_east_neighbours import paving_height


@lru_cache(maxsize=1)
def grade():
    """Contacts sampled from the published path, curb and uncut upper terrace."""
    return json.loads(
        (Path(__file__).resolve().parents[1] / 'data/west-dorm-grade.json').read_text()
    )


def cross_section(mesh, rows, finish):
    """Stitch successive left-to-right profiles with an upward-facing surface."""
    for a, b in zip(rows, rows[1:]):
        for left, right, end_left, end_right in zip(a, a[1:], b, b[1:]):
            mesh.face([left, end_left, end_right, right], finish)


def close_ends(mesh, profiles, finish):
    """Bed ends meet the lawn at the entry flares and beside the lodge spur."""
    for row, reverse in ((profiles[0], False), (profiles[-1], True)):
        for a, b in zip(row, row[1:]):
            if a[:2] == b[:2]:
                continue
            base_a = (*a[:2], min(a[2] - 0.03, paving_height(*a[:2]) - 0.24))
            base_b = (*b[:2], min(b[2] - 0.03, paving_height(*b[:2]) - 0.24))
            face = [a, b, base_b, base_a]
            mesh.face(face[::-1] if reverse else face, finish)


def gate_lodge(C, detail):
    mesh = Mesh()
    x, y = -19.3, -548.2
    z = paving_height(x, y)
    mesh.box(x, y, z - 0.02, 5.55, 4.00, 0.90, C['dormWindow'])
    mesh.box(x, y, z + 1.74, 5.45, 3.85, 2.62, C['lodgePlaster'])
    roof_z = z + 3.06
    mesh.roof(x, y, roof_z, 6.30, 4.65, 0.92, C['lodgeRoof'])
    # Courses run around the hips and stop at the rising ridge. Overlapping
    # lower edges catch the light at street level without a second roof shell.
    if detail:

        def ring(t):
            half_x = 3.15 - (3.15 - 6.30 * 0.26) * t
            half_y = 2.325 * (1 - t)
            return [
                (x + sx * half_x, y + sy * half_y, roof_z + 0.92 * t + 0.009)
                for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))
            ]

        for course in range(10):
            lower, upper = ring(course / 10), ring((course + 0.96) / 10)
            for edge in range(4):
                nxt = (edge + 1) % 4
                count = max(1, round(math.dist(lower[edge], lower[nxt]) / 0.24))
                for i in range(count):
                    face = []
                    for band, t, lip in (
                        (lower, i / count, 0.021),
                        (lower, (i + 0.97) / count, 0.021),
                        (upper, (i + 0.97) / count, 0),
                        (upper, i / count, 0),
                    ):
                        a, b = band[edge], band[nxt]
                        tx, ty, tz = (v + t * (w - v) for v, w in zip(a, b))
                        face.append((tx, ty, tz + lip))
                    color = (
                        'lodgeTile'
                        if (i * 5 + course * 3 + edge) % 7 < 3
                        else 'lodgeRoof'
                    )
                    mesh.face(face, C[color])
        for a, b in zip(ring(0), ring(1)):
            mesh.line(a, b, 0.044, C['lodgeTile'], 6)
    mesh.line((x - 1.65, y, z + 4.0), (x + 1.65, y, z + 4.0), 0.06, C['lodgeTile'], 6)
    mesh.box(x, y, z + 3.01, 6.30, 4.65, 0.10, C['lodgePlaster'])
    mesh.box(x, y, z + 2.93, 6.07, 4.43, 0.065, C['lodgeRoof'])
    mesh.box(x, y, z + 2.84, 5.53, 3.94, 0.065, C['dormWindow'])
    for dx in (-1.75, 1.57):
        mesh.box(x + dx, y + 1.95, z + 1.75, 1.30, 0.08, 1.44, C['white'])
        mesh.box(x + dx, y + 2.01, z + 1.75, 1.13, 0.06, 1.27, C['dormWindow'])
        mesh.box(x + dx, y + 2.05, z + 1.75, 0.05, 0.035, 1.27, C['white'])
    mesh.box(x, y + 1.96, z + 1.41, 0.94, 0.12, 2.02, C['dark'])
    mesh.box(x - 2.74, y, z + 1.75, 0.09, 1.45, 1.42, C['white'])
    mesh.box(x - 2.80, y, z + 1.75, 0.06, 1.29, 1.27, C['dormWindow'])
    mesh.box(x - 2.84, y, z + 1.75, 0.04, 0.05, 1.27, C['white'])

    if detail:
        # The west-facing window has a projecting sill beneath a shallow tiled eave.
        mesh.box(x - 2.82, y, z + 1.03, 0.21, 1.55, 0.08, C['stone'])
        for dx in (-1.75, 1.57):
            mesh.box(x + dx, y + 2.05, z + 1.03, 1.41, 0.19, 0.08, C['stone'])

    # A short garden rail finishes the planting beside the lodge window.
    rail_x = x - 3.19
    posts = [y - 2.65, y - 0.68, y + 1.29]
    tops = []
    for py in posts:
        foot = paving_height(rail_x, py)
        mesh.box(rail_x, py, foot + 0.04, 0.19, 0.19, 0.23, C['stone'])
        mesh.box(rail_x, py, foot + 0.62, 0.072, 0.072, 1.14, C['lodgeUnderleaf'])
        mesh.box(rail_x, py, foot + 1.21, 0.12, 0.12, 0.06, C['lodgeUnderleaf'])
        tops.append((rail_x, py, foot + 1.12))
    for a, b in zip(tops, tops[1:]):
        mesh.line(a, b, 0.031, C['lodgeUnderleaf'], 6)
        if detail:
            mesh.line(
                (*a[:2], a[2] - 0.42),
                (*b[:2], b[2] - 0.42),
                0.023,
                C['lodgeUnderleaf'],
                6,
            )

    return mesh


def west_one_awning(mesh, center, normal, z, C):
    """The shallow arched cover photographed outside West 1 in March 2025."""
    nx, ny = normal

    def point(u, depth, h):
        return (center[0] + u * ny + depth * nx, center[1] - u * nx + depth * ny, z + h)

    ribs = 8
    strips = []
    for i in range(ribs + 1):
        u = 2 * i / ribs - 1
        h = 2.48 + 0.47 * (1 - u * u)
        strips.append([point(1.65 * u, 0.07, h), point(1.65 * u, 2.34, h)])
    for a, b in zip(strips, strips[1:]):
        # A thin shell also reads correctly when seen from beneath the cover.
        top = [a[0], b[0], b[1], a[1]]
        bottom = [(x, y, h - 0.035) for x, y, h in reversed(top)]
        mesh.face(top, C['dormAwning'])
        mesh.face(bottom, C['dormAwning'])
        mesh.line(a[1], b[1], 0.031, C['metal'], 5)
    for i in (0, ribs):
        a, b = strips[i]
        mesh.line(a, b, 0.032, C['metal'], 5)
        mesh.line(
            (b[0], b[1], paving_height(b[0], b[1]) - 0.12), b, 0.035, C['metal'], 6
        )
    for a, b in strips[2:-1:2]:
        mesh.line(a, b, 0.022, C['metal'], 5)


def brick_shoulders(mesh, rows, side, detail, C):
    """Brick walks along Yanshan Road turn into both sides of the gate apron."""
    profiles = []
    for i, (x, y, span, h, south, north) in enumerate(rows[:3]):
        inner = y + side * (span + 0.17)
        edge_height = h + (south if side < 0 else north)
        lip = 0.018 if i == 0 else 0.105
        # The street slopes north; grade the bricks across their full width.
        outer = rows[0][1] + side * 10.0
        outer_z = edge_height + lip + (outer - inner) * -0.047
        profiles.append(((x, inner, edge_height + lip), (x, outer, outer_z)))
    for left, right in zip(profiles, profiles[1:]):

        def point(t, u, dz=0):
            a, b = [
                tuple(v + t * (w - v) for v, w in zip(k, m))
                for k, m in zip(left, right)
            ]
            x, y, z = (v + u * (w - v) for v, w in zip(a, b))
            return (x, y, z + dz)

        face = [point(0, 0), point(1, 0), point(1, 1), point(0, 1)]
        width = right[0][0] - left[0][0]
        # Flush stone trim at the street edge of the Yanshan Road brick walk.
        trim = 0.14 / width if left is profiles[0] else 0
        start, end = point(trim, 0), point(trim, 1)
        if trim:
            mesh.face([face[0], start, end, face[3]][::side], C['dormPaverGrey'])
        mesh.face([start, face[1], face[2], end][::side], C['dormBrickClay'])
        if detail:
            courses = max(1, round((1 - trim) * width / 0.16))
            count = max(1, round(math.dist(left[0], left[1]) / 0.32))
            for j in range(courses):
                shift = 0.5 if j % 2 else 0
                for k in range(-1, count):
                    u, v = (
                        max(0, (k + shift + 0.018) / count),
                        min(1, (k + shift + 0.98) / count),
                    )
                    if v <= u:
                        continue
                    a = trim + (1 - trim) * (j + 0.03) / courses
                    b = trim + (1 - trim) * (j + 0.97) / courses
                    tile = [
                        point(a, u, 0.012),
                        point(b, u, 0.012),
                        point(b, v, 0.012),
                        point(a, v, 0.012),
                    ]
                    finish = (
                        'dormStoneWarm' if (j + 3 * k) % 9 == 0 else 'dormPaverRose'
                    )
                    mesh.face(tile[::side], C[finish])
        # Return exposed paving edges into the ground at the street and ends.
        exposed = [(face[2], face[3])]
        if left is profiles[0]:
            exposed.append((face[3], face[0]))
        for a, b in exposed:
            mesh.face(
                [
                    a,
                    b,
                    (*b[:2], paving_height(*b[:2]) - 0.15),
                    (*a[:2], paving_height(*a[:2]) - 0.15),
                ][::-side],
                C['stone'],
            )
    # A planted shoulder grades from the back of the walk down to the existing lawn.
    a, b = profiles[-1]
    near = (a[0] + 0.90, a[1] + side * 0.7)
    far = (b[0] + 0.9, b[1])
    mesh.face(
        [
            a,
            (*near, paving_height(*near) - 0.06),
            (*far, paving_height(*far) - 0.06),
            b,
        ][::side],
        C['grass'],
    )


def leaf_clump(mesh, x, y, z, turn, C):
    for k in range(7):
        angle = 2.40 * k + turn
        ux, uy = math.cos(angle), math.sin(angle)
        reach = 0.19 + 0.04 * (k % 3)
        root = (x, y, z - 0.035)
        lx, ly = x + 0.54 * reach * ux, y + 0.54 * reach * uy
        left = (lx - 0.029 * uy, ly + 0.029 * ux, z + 0.16)
        right = (lx + 0.029 * uy, ly - 0.029 * ux, z + 0.15)
        tip = (x + reach * ux, y + reach * uy, z + 0.06)
        color = C['leaf' if k % 3 else 'lodgeUnderleaf']
        mesh.face([root, right, left], color)
        mesh.face([left, right, tip], color)


def groundcover(mesh, leaves, C):
    """Distribute arching leaves over the actual crown of the planting bed."""
    for start, end in zip(leaves, leaves[1:]):
        count = max(1, round(math.dist(start[2], end[2]) / 0.34))
        for j in range(count):
            for strip in range(4):
                t = (j + 0.30 + 0.35 * (strip % 2)) / count
                across = 0.48 + 0.18 * math.sin(j + strip)
                a, b = [
                    tuple(v + t * (w - v) for v, w in zip(start[k], end[k]))
                    for k in (strip, strip + 1)
                ]
                x, y, z = (v + across * (w - v) for v, w in zip(a, b))
                leaf_clump(mesh, x, y, z, j + 1.7 * strip, C)


def apron_pours(mesh, apron, C):
    # Cast concrete at the entrance reads as broad pours. Keep the surveyed
    # crown, and the narrow transition to the existing road at either end.
    joints = [
        apron[0][0][0] + 0.09,
        -22.35,
        -18.6,
        -14.85,
        -11.1,
        apron[-1][0][0] - 0.09,
    ]
    for left, right in zip(apron, apron[1:]):
        x0, x1 = left[0][0], right[0][0]
        cuts = sorted(
            [x0, x1] + [x for at in joints for x in (at, at + 0.025) if x0 < x < x1]
        )
        for x, end in zip(cuts, cuts[1:]):
            mid = (x + end) / 2
            contact = (
                mid < joints[0]
                or mid > joints[-1]
                or any(0 <= mid - j <= 0.025 for j in joints)
            )
            for lane in (0, 1):
                corners = []
                for along, index in (
                    (x, lane),
                    (end, lane),
                    (end, lane + 1),
                    (x, lane + 1),
                ):
                    t = (along - x0) / (x1 - x0)
                    corners.append(
                        tuple(
                            a + t * (b - a) for a, b in zip(left[index], right[index])
                        )
                    )
                finish = (
                    'path' if contact else ('dormConcrete', 'dormConcreteLight')[lane]
                )
                mesh.face(corners, C[finish])


def west_entry(C, detail):
    mesh = gate_lodge(C, detail)
    rows = grade()['gateSections']
    apron = []
    for x, y, span, h, south, north in rows:
        apron.append(
            [
                (x, y - span, h + south + 0.020),
                (x, y, h + 0.026),
                (x, y + span, h + north + 0.020),
            ]
        )
    apron_pours(mesh, apron, C)
    close_ends(mesh, apron, C['stone'])
    # Curved planting shoulders follow the apron crown and feather into the lawn.
    for side in (-1, 1):
        edging, bank, leaves = [], [], []
        for idx, (x, y, span, h, south, north) in enumerate(rows):
            edge = y + side * span
            surface = h + (south if side == -1 else north)
            # Flush flares at both ends meet the road and the narrower garden walk.
            height = 0.018 if idx in (0, len(rows) - 1) else 0.105
            top = surface + height
            outer = edge + side * 0.17
            toe = outer + side * 1.05
            profile = [(x, edge, surface - 0.18), (x, edge, top), (x, outer, top)]
            # At the mouth the paved shoulder meets daylight. Bury only the
            # planted bank farther along, where its toe blends into the terrain.
            toe_z = paving_height(x, toe) + (0.018 if idx <= 2 else -0.22)
            earth = [(x, outer, top - 0.03), (x, toe, toe_z)]
            edging.append(profile[::side])
            bank.append(earth[::side])
            # Low clipped groundcover follows the curved brick borders in the street view.
            rise = min(
                0.20, max(0, (x - rows[2][0]) * 0.15), max(0, (rows[-1][0] - x) * 0.18)
            )
            leaves.append(
                [
                    (x, outer + side * d, top + dz)
                    for d, dz in [
                        (0.04, -0.06),
                        (0.14, 0.65 * rise),
                        (0.36, rise),
                        (0.73, 0.85 * rise),
                        (0.91, -0.10),
                    ]
                ][::side]
            )
        # Set the planting back from the road mouth. Cap each exposed soil edge
        # so the lawn remains solid in the street-level view down the slope.
        brick_shoulders(mesh, rows, side, detail, C)
        if detail:
            groundcover(mesh, leaves[2:5], C)
            groundcover(mesh, leaves[5:-1] if side < 0 else leaves[4:-1], C)
        for profiles, finish in ((edging, 'stone'), (bank, 'grass'), (leaves, 'leaf2')):
            first, last = (2, len(rows) - 1) if finish == 'leaf2' else (0, len(rows))
            if finish == 'grass':
                first = 2
            spans = (
                [profiles[first:last]]
                if side > 0
                else [profiles[first:5], profiles[5:last]]
            )
            for span in spans:
                cross_section(mesh, span, C[finish])
                close_ends(mesh, span, C[finish])
    # Low foliage returns around the lodge wall and the shade tree at the
    # opposite corner, inside the planted ground behind the brick walks.
    for cx, cy, rx, ry in ((-22.65, -548.5, 0.62, 2.35), (-21.3, -536.8, 1.15, 1.75)):
        for j in range(-6, 7):
            for k in range(-4, 5):
                dx, dy = (k + 0.40 * (j % 2)) * 0.32, j * 0.36
                if (dx / rx) ** 2 + (dy / ry) ** 2 > 1:
                    continue
                x, y = cx + dx, cy + dy
                z = paving_height(x, y)
                if detail:
                    leaf_clump(mesh, x, y, z + 0.075, 0.83 * j + k, C)
                elif j % 2 == 0 and k % 2 == 0:
                    mesh.ellipsoid(x, y, z, 0.34, 0.41, 0.14, C['lodgeUnderleaf'], 6, 3)
    middle = -19.3
    landing = paving_height(middle, -548.2) + 0.055
    # The lodge spur fills the break between the two beds. Its mouth shares
    # both corners with the crowned apron, then narrows at the first tread.
    spur = []
    for t in (0, 0.28, 0.65, 1):
        ease = t * (2 - t)
        row = []
        for start, end_x in zip(
            (apron[4][0], apron[5][0]), (middle - 0.76, middle + 0.76)
        ):
            x = start[0] + (end_x - start[0]) * ease
            y = start[1] + (-546.32 - start[1]) * t
            row.append((x, y, start[2] + (landing - start[2]) * t))
        spur.append(row)
    for a, b in zip(spur, spur[1:]):
        mesh.face([a[0], b[0], b[1], a[1]], C['dormConcrete'])
        for index in (0, 1):
            x0 = apron[4 + index][0][0]
            u, v = a[index], b[index]
            soil_u = (x0, u[1], min(u[2], paving_height(x0, u[1]) - 0.04))
            soil_v = (x0, v[1], min(v[2], paving_height(x0, v[1]) - 0.04))
            shoulder = [u, soil_u, soil_v, v]
            mesh.face(shoulder if index == 0 else shoulder[::-1], C['grass'])
    for cy, depth, rise in [(-545.94, 0.46, 0.17), (-546.25, 0.25, 0.34)]:
        mesh.box(middle, cy, landing + rise / 2, 1.38, depth, rise, C['stone'])
    # Folded silver lattice and low entrance furniture visible beside the lodge.
    x, y, _, h, _, _ = rows[4]
    for j in range(6):
        cy = y + 0.65 + j * 0.28
        mesh.box(x, cy, h + 0.74, 0.10, 0.065, 1.29, C['metal'])
        if j in (0, 2, 5):
            mesh.box(x, cy, h + 0.098, 0.42, 0.10, 0.14, C['dark'])
        if j == 5:
            break
        for px in (x - 0.18, x + 0.18) if detail else (x,):
            mesh.line(
                (px, cy, h + 0.22), (px, cy + 0.28, h + 1.19), 0.033, C['metal'], 4
            )
            mesh.line(
                (px, cy, h + 1.19), (px, cy + 0.28, h + 0.22), 0.033, C['metal'], 4
            )
    for dy in (-1.75, -0.63):
        mesh.box(x, y + dy, h + 0.45, 0.40, 0.18, 0.82, C['metal'])
        mesh.box(x, y + dy, h + 0.77, 0.41, 0.19, 0.075, C['dormRose'])
        mesh.box(x, y + dy, h + 0.88, 0.44, 0.21, 0.055, C['dark'])
    return mesh


WALK_WIDTH = 1.75


def garden_banks(C):
    """Grade the exposed lawn up to both edges of the elevated interior walks."""
    mesh = Mesh()
    for run in grade()['gardenBanks']:
        dx = run[-1][0] - run[0][0]
        dy = run[-1][1] - run[0][1]
        length = math.hypot(dx, dy)
        nx, ny = -dy / length, dx / length
        for side in (-1, 1):
            profiles = []
            for x, y, right_path, right_lawn, left_path, left_lawn in run:
                path, lawn = (
                    (right_path, right_lawn) if side == -1 else (left_path, left_lawn)
                )
                rows = [
                    (1.01, path - 0.035),
                    (1.24, path - 0.06),
                    (1.60, 0.70 * path + 0.30 * lawn - 0.065),
                    (2.04, 0.20 * path + 0.80 * lawn - 0.050),
                    (2.35, lawn - 0.045),
                ]
                profile = [
                    (x + side * nx * offset, y + side * ny * offset, z)
                    for offset, z in rows
                ]
                profiles.append(profile[::side])
            cross_section(mesh, profiles, C['grass'])
    return mesh


def front_section(x):
    rows = grade()['frontWalk']
    for a, b in zip(rows, rows[1:]):
        if a[0] <= x <= b[0]:
            t = (x - a[0]) / (b[0] - a[0])
            return [u + (v - u) * t for u, v in zip(a[1:], b[1:])]
    raise ValueError('South entrance falls outside the dormitory frontage')


def front_walk(C):
    mesh = Mesh()
    surface = []
    shoulder = []
    for x, y, outer, inner in grade()['frontWalk']:
        surface.append([(x, y, outer), (x, y + WALK_WIDTH, inner)])
        # Bury the foot of the lawn slope in the campus terrain to avoid a seam.
        toe = y + WALK_WIDTH + 0.85
        shoulder.append(
            [(x, y + WALK_WIDTH, inner - 0.018), (x, toe, paving_height(x, toe) - 0.22)]
        )
    # The north-south garden walk already owns the surface between these contacts.
    split = next(i for i, r in enumerate(surface) if r[0][0] == 43.0)
    for strip, material in ((surface, C['path']), (shoulder, C['grass'])):
        cross_section(mesh, strip[:split], material)
        cross_section(mesh, strip[split:], material)
    for a, b in zip(surface, surface[1:]):
        p, q = a[0], b[0]
        if q[0] == 43.0:
            continue
        mesh.face([p, (*p[:2], p[2] - 0.55), (*q[:2], q[2] - 0.55), q], C['stone'])
    return mesh


def approach(mesh, b, z, C, number):
    x, y = b['form']['entrances'][0]['center']
    start = y - 1.90
    sides = (-1.24, 1.24)
    if number < 4:
        ends = grade()['walkContacts'][str(number)]
    else:
        ends = []
        for dx in sides:
            edge, _, inner = front_section(x + dx)
            ends.append((edge + WALK_WIDTH - 0.07, inner))
    rows = []
    for j in range(11):
        t = j / 10
        row = []
        for side, (end, eh) in zip(sides, ends):
            py = start + (end - start) * t
            height = (z + 0.075) * (1 - t) + (eh + 0.012) * t
            row.append((x + side, py, height))
        rows.append(row)
    for a, b_end in zip(rows, rows[1:]):
        mesh.face([a[0], b_end[0], b_end[1], a[1]], C['path'])
    if number == 1:
        # A low, planted verge sits above the concrete beside the awning.
        # Taper it back to the lawn before the approach joins the main walk.
        bed = []
        for j, row in enumerate(rows[:6]):
            px, py, h = row[0]
            rise = min(0.12, (5 - j) * 0.045)
            toe = px - 0.74
            bed.append(
                [
                    (px, py, h - 0.04),
                    (px, py, h + rise),
                    (px - 0.13, py, h + rise),
                    (px - 0.18, py, h + rise - 0.02),
                    (toe, py, paving_height(toe, py) - 0.08),
                ]
            )
        for a, b_end in zip(bed, bed[1:]):
            for j in range(4):
                mesh.face(
                    [a[j], a[j + 1], b_end[j + 1], b_end[j]],
                    C['grass' if j == 3 else 'curb'],
                )
        close_ends(mesh, bed, C['stone'])
    for side in (0, 1):
        for a, b_end in zip(rows, rows[1:]):
            l, r = a[side], b_end[side]
            mesh.face(
                [
                    l,
                    r,
                    (*r[:2], min(r[2] - 0.14, paving_height(*r[:2]) - 0.20)),
                    (*l[:2], min(l[2] - 0.14, paving_height(*l[:2]) - 0.20)),
                ][:: -1 if side == 0 else 1],
                C['stone'],
            )


def street_hedges(b, C):
    """Two clipped beds flank the walk to each Bocui Road entrance."""
    x0, y0, x1, _ = b['bounds']
    mid = b['form']['entrances'][0]['center'][0]
    y = y0 - (1.0 if b['id'] == 'way/759158608' else 3.55)
    borders = Mesh()

    def grounded(rows):
        return [[*row, paving_height(*row[:2]) - 0.055] for row in rows]

    for left, right in ((x0 + 0.60, mid - 1.60), (mid + 1.60, x1 - 0.60)):
        bed = {
            'line': [(left, y), (right, y)],
            'widthMeters': 1.0 if b['id'] == 'way/759158608' else 1.55,
            'heightMeters': 0.77,
        }
        borders.extend(profiled_hedge(bed, C, grounded))
    return borders
