"""West residences 1–5, built within their mapped rings in east/north metres."""

import math

from mathutils import Vector
from mathutils.geometry import tessellate_polygon

from geometry import Mesh
from west_dorm_garden import (
    approach,
    front_walk,
    garden_banks,
    street_hedges,
    west_entry,
    west_one_awning,
)

NUMBERS = {
    'way/759158610': 1,
    'way/759158609': 2,
    'way/759158607': 3,
    'way/759158606': 4,
    'way/759158608': 5,
}

WELL_DEPTH = 3.5

# The two lower storeys are rose render. The balcony infill varies by block.
FINISHES = {
    'dormTile': '#82483e',
    'dormRose': '#b9827c',
    'dormButter': '#e9d6a7',
    'dormBlush': '#e6d5d2',
    'dormScreen': '#78877b',
    'dormCollector': '#404b4c',
    'dormRecess': '#a58e79',
    'dormWindow': '#434d4b',
    'dormPaverRose': '#b48a7e',
    'dormBrickClay': '#aa8070',
    'dormConcrete': '#aba69b',
    'dormConcreteLight': '#b6afa2',
    'lodgePlaster': '#b47174',
    'lodgeRoof': '#683f39',
    'lodgeTile': '#795049',
    'lodgeUnderleaf': '#41563e',
    'dormAwning': '#d4c59c',
    'dormStoneWarm': '#af8c74',
    'dormStonePale': '#b99d86',
    'dormPaverGrey': '#99978d',
}


class Wall:
    """Place boxes along one exterior edge, positive depth towards the street."""

    def __init__(self, a, b, clockwise):
        self.x, self.y = a
        dx, dy = b[0] - a[0], b[1] - a[1]
        self.length = math.hypot(dx, dy)
        self.tx, self.ty = dx / self.length, dy / self.length
        sign = 1 if clockwise else -1
        self.nx, self.ny = -sign * self.ty, sign * self.tx
        self.angle = math.atan2(dy, dx)

    def box(self, mesh, u, offset, z, width, depth, height, material):
        mesh.box(
            self.x + self.tx * u + self.nx * offset,
            self.y + self.ty * u + self.ny * offset,
            z,
            width,
            depth,
            height,
            material,
            self.angle,
        )


def balcony(w, mesh, trim, base, floor, level, center, width, number, C, detail):
    lower = level < 2
    pier = 0.66 if lower else 0.22
    finish = C['dormBlush' if number in (3, 5) else 'dormButter']
    outer = C['dormRose' if lower else 'white']
    # Full-depth party walls cast shadows and leave an open drying balcony.
    w.box(
        mesh,
        center - width / 2 + pier / 2,
        -0.78,
        base + floor / 2,
        pier,
        1.58,
        floor,
        outer,
    )
    w.box(mesh, center, -1.51, base + floor / 2, width, 0.16, floor, C['dormRecess'])
    w.box(
        mesh,
        center + width * 0.13,
        -1.408,
        base + 1.59,
        width * 0.48,
        0.05,
        1.1,
        C['dormWindow'],
    )
    w.box(mesh, center - width * 0.29, -1.406, base + 1.1, 0.85, 0.055, 2.15, C['dark'])
    clear = width - pier
    x = center + pier / 2
    if lower or level == 2:
        h = 0.72 if level == 2 else 0.98
        w.box(mesh, x, -0.08, base + h / 2, clear, 0.16, h, finish)
    else:
        w.box(mesh, x, -0.08, base + 0.48, clear * 0.54, 0.16, 0.96, finish)
    w.box(mesh, x, -0.07, base + 0.98, clear, 0.065, 0.075, C['metal'])
    w.box(
        mesh, x, -0.10, base + floor - 0.25, clear, 0.20, 0.50 if lower else 0.22, outer
    )
    if not detail:
        return
    barred = level == 0 or (level == 1 and number in (3, 5))
    if barred:
        for j in range(1, 13):
            w.box(
                trim,
                x + clear * (j / 13 - 0.5),
                -0.035,
                base + floor / 2 + 0.23,
                0.031,
                0.04,
                floor - 1.0,
                C['metal'],
            )
        w.box(trim, x, -0.027, base + 1.98, clear, 0.04, 0.04, C['metal'])
    elif level > 2:
        for sign in (-1, 1):
            for h in (0.37, 0.66):
                w.box(
                    trim,
                    x + sign * clear * 0.383,
                    -0.07,
                    base + h,
                    clear * 0.23,
                    0.04,
                    0.035,
                    C['metal'],
                )
    # The drying rails sit behind the parapet. Vary the hanging textiles by bay.
    bay = round(center / width - 0.5)
    pattern = (bay * 11 + level * 7 + number) % 17
    if level and pattern % 5:
        w.box(
            trim, x, -0.62, base + floor - 0.39, clear - 0.3, 0.035, 0.035, C['metal']
        )
        finishes = ['dark', 'white', 'glass', 'dormBlush', 'stone', 'dormCollector']
        for i in range(2 + pattern % 4):
            u = x - clear * 0.36 + ((i + pattern % 3) % 6) * clear * 0.135
            length = 0.72 + (pattern + i * 7) % 6 * 0.105
            color = C[finishes[(i * 5 + pattern) % len(finishes)]]
            w.box(
                trim,
                u,
                -0.61,
                base + floor - 0.39 - length / 2,
                0.25 + (pattern + i) % 3 * 0.066,
                0.075,
                length,
                color,
            )
    # Paired stacks sit at alternating piers in the street photographs.
    if round((center - width / 2) / width) % 2 == 0:
        w.box(
            trim,
            center - width / 2 + pier / 2,
            0.18 if lower else -0.48,
            base + 2.1,
            0.72,
            0.38,
            0.51,
            C['paleRoof'],
        )
        w.box(
            trim,
            center - width / 2 + pier / 2,
            0.39 if lower else -0.27,
            base + 2.1,
            0.49,
            0.03,
            0.36,
            C['metal'],
        )


def arched_screen(w, mesh, z, span, C, pierced=False):
    """Two curved shoulders with real square apertures over the south entrance."""
    count = 21
    step = span / count
    for i in range(count):
        u = (i + 0.5) * step - span / 2
        h = 0.48 + 1.06 * max(0, 1 - (2 * u / span) ** 2)
        x = w.length / 2 + u
        # The paired crests above the central stair are separated by a narrow joint.
        if pierced and i == count // 2:
            w.box(mesh, x, -0.12, z + 0.14, step, 0.25, 0.28, C['dormRose'])
            for side in (-1, 1):
                w.box(
                    mesh,
                    x + side * step * 0.37,
                    -0.12,
                    z + h / 2,
                    step * 0.26,
                    0.25,
                    h,
                    C['white'],
                )
            continue
        before = len(mesh.v)
        if pierced and i in (5, 7, 9, 11, 13, 15):
            w.box(mesh, x, -0.12, z + 0.24, step, 0.25, 0.48, C['white'])
            w.box(mesh, x, -0.12, z + (h + 0.83) / 2, step, 0.25, h - 0.83, C['white'])
        else:
            w.box(mesh, x, -0.12, z + h / 2, step, 0.25, h, C['white'])
        for k in range(before, len(mesh.v)):
            px, py, pz = mesh.v[k]
            if abs(pz - (z + h)) < 0.001:
                pos = (px - w.x) * w.tx + (py - w.y) * w.ty - w.length / 2
                mesh.v[k] = (
                    px,
                    py,
                    z + 0.48 + 1.06 * max(0, 1 - (2 * pos / span) ** 2),
                )


def stair_screen(w, body, fine, z, h, width, C, detail):
    mid = w.length / 2
    bottom, top = 2.78, h - 0.40
    back = -WELL_DEPTH
    screen = back + 0.64
    w.box(body, mid, back - 0.08, z + h / 2, width, 0.17, h, C['dormRecess'])
    w.box(body, mid, back + 0.04, z + 1.13, 2.0, 0.08, 2.25, C['dark'])
    w.box(
        body,
        mid,
        back + 0.025,
        z + (bottom + top) / 2,
        width,
        0.045,
        top - bottom,
        C['dark'],
    )
    # The reveal returns from both front piers to the recessed screen.
    for side in (-1, 1):
        u = mid + side * (width / 2 - 0.06)
        w.box(body, u, back / 2, z + h / 2, 0.12, WELL_DEPTH, h, C['white'])
        w.box(
            body,
            u - side * 0.015,
            back / 2,
            z + 3.3,
            0.13,
            WELL_DEPTH,
            6.6,
            C['dormRose'],
        )
    cols = 11 if detail else 6
    rows = round((top - bottom) / (0.35 if detail else 0.62))
    for col in range(cols + 1):
        w.box(
            fine,
            mid + width * (col / cols - 0.5),
            screen,
            z + (top + bottom) / 2,
            0.066,
            0.12,
            top - bottom,
            C['dormScreen'],
        )
    for row in range(rows + 1):
        w.box(
            fine,
            mid,
            screen,
            z + bottom + (top - bottom) * row / rows,
            width,
            0.12,
            0.07,
            C['dormScreen'],
        )


def north_gallery(w, mesh, trim, base, floor, lower, C, detail):
    end = 1.75
    wall = C['dormRose' if lower else 'white']
    w.box(mesh, w.length / 2, -1.40, base + floor / 2, w.length, 0.18, floor, wall)
    for u in (end / 2, w.length - end / 2):
        w.box(mesh, u, -0.70, base + floor / 2, end, 1.4, floor, wall)
        w.box(mesh, u, 0.022, base + 1.67, end * 0.64, 0.045, 1.32, C['glass'])
    length = w.length - 2 * end
    bays = max(1, round(length / 3.7))
    for i in range(bays):
        u = end + (i + 0.5) * length / bays
        w.box(mesh, u, -1.285, base + 1.09, 0.91, 0.055, 2.15, C['dark'])
        w.box(mesh, u + 1.0, -1.285, base + 2.07, 0.47, 0.055, 0.45, C['glass'])
    w.box(mesh, w.length / 2, -0.085, base + 0.31, length, 0.17, 0.62, C['white'])
    w.box(mesh, w.length / 2, -0.085, base + 1.02, length, 0.07, 0.07, C['metal'])
    if detail:
        for j in range(bays * 3):
            w.box(
                trim,
                end + (j + 0.5) * length / (bays * 3),
                -0.085,
                base + 0.81,
                0.04,
                0.055,
                0.4,
                C['metal'],
            )
        w.box(trim, w.length / 2, -0.08, base + 0.80, length, 0.05, 0.04, C['metal'])


def roof_frame(b):
    ring = b['polygons'][0][0]
    a, b_end = max(zip(ring, ring[1:]), key=lambda edge: math.dist(*edge))
    length = math.dist(a, b_end)
    ux, uy = (b_end[0] - a[0]) / length, (b_end[1] - a[1]) / length
    if ux < 0:
        ux, uy = -ux, -uy
    local = [(ux * x + uy * y, -uy * x + ux * y) for x, y in ring]
    x0, x1 = min(x for x, _ in local), max(x for x, _ in local)
    y0, y1 = min(y for _, y in local), max(y for _, y in local)
    return ux, uy, x0, y0, x1, y1


def roof_equipment(b, number, roof, z, C):
    ux, uy, x0, y0, x1, y1 = roof_frame(b)
    first = len(roof.v)
    # Paired dark arrays with transverse seams. The west half of W4 is pale
    # exposed roof in the overhead image, W1 has a shorter south roof edge.
    left = x0 + (9 if number == 1 else 1.1)
    right = x1 - (5.2 if number == 1 else 1.1)
    # The April 2024 pass shows bare, dark waterproofing on W2's west
    # wing and a pale surface on W4. Both have tilted rows on their east wing.
    start = (left + right) / 2 + 2 if number in (2, 4) else left
    if number == 2:
        roof.box(
            (left + start) / 2,
            y0 + 5.25,
            z + 0.025,
            start - left,
            8.1,
            0.05,
            C['dormCollector'],
        )
    for row in range(3):
        count = max(1, round((right - start) / 4))
        step = (right - start) / count
        for i in range(count):
            x = start + (i + 0.5) * step
            y = y0 + 2.7 + row * 2.95
            before = len(roof.v)
            roof.box(x, y, z + 0.42, step - 0.12, 1.7, 0.10, C['dormCollector'])
            for k in range(before, len(roof.v)):
                px, py, pz = roof.v[k]
                roof.v[k] = (px, py, pz + (py - y) * 0.31)
            roof.box(x, y + 0.65, z + 0.28, 0.10, 0.10, 0.56, C['metal'])
    if number != 1:
        tower_x = (left + right) / 2
        tower_y = y1 - 4.7
        roof.box(tower_x, tower_y, z + 0.52, 4.25, 4.65, 1.04, C['residenceStone'])
        roof.box(tower_x, tower_y, z + 1.07, 4.39, 4.8, 0.13, C['paleRoof'])
    for f in (0.18, 0.82):
        w = (right - left) * 0.22
        x = left + (right - left) * f
        roof.box(x, y0 + 0.72, z + 0.27, w, 1.35, 0.32, C['red'])

    for i in range(first, len(roof.v)):
        x, y, h = roof.v[i]
        roof.v[i] = (ux * x - uy * y, uy * x + ux * y, h)


def floor_outline(ring, clockwise):
    """Cut the open lightwell from intermediate slabs, keeping the roof over it."""
    outline = []
    for a, b in zip(ring, ring[1:]):
        outline.append(a)
        wall = Wall(a, b, clockwise)
        if wall.ny < -0.98 and wall.length > 34:
            for frac, depth in [
                (6 / 13, 0),
                (6 / 13, -WELL_DEPTH),
                (7 / 13, -WELL_DEPTH),
                (7 / 13, 0),
            ]:
                outline.append(
                    [
                        a[0] + frac * (b[0] - a[0]) + wall.nx * depth,
                        a[1] + frac * (b[1] - a[1]) + wall.ny * depth,
                    ]
                )
    if clockwise:
        outline.reverse()
    triangles = tessellate_polygon([[Vector((x, y, 0)) for x, y in outline]])
    return [[outline + [outline[0]]]], [[i for tri in triangles for i in tri]]


def eave_outline(ring, clockwise, number):
    # Narrow end caps and a deeper overhang above the north and south balconies.
    walls = [Wall(a, b, clockwise) for a, b in zip(ring, ring[1:])]
    offsets = [abs(w.nx) * 0.08 + abs(w.ny) * 0.52 for w in walls]
    if number == 1:
        # W1 has a stepped west wing and a shallower eave over its long south wall.
        offsets = [abs(w.nx) * 0.08 + abs(w.ny) * 0.25 for w in walls]
        west = min(range(len(walls)), key=lambda i: (ring[i][0] + ring[i + 1][0]) / 2)
        south = max(
            (i for i, w in enumerate(walls) if w.ny < -0.9),
            key=lambda i: walls[i].length,
        )
        offsets[west] = 0.10
        offsets[south] = 0.15
    outline = []
    for i, (x, y) in enumerate(ring[:-1]):
        prev, cur = walls[i - 1], walls[i]
        dp, dc = offsets[i - 1], offsets[i]
        det = prev.nx * cur.ny - cur.nx * prev.ny
        outline.append(
            [
                x + (dp * cur.ny - dc * prev.ny) / det,
                y + (prev.nx * dc - cur.nx * dp) / det,
            ]
        )
    return [[outline + [outline[0]]]]


def west_one_entry_finish(wall, mesh, z, C):
    """Stone skirting and the shaded concrete shelf visible above the curved canopy."""
    middle = wall.length / 2
    # Leave the doorway clear between the two ends of the tiled plinth.
    span = (wall.length - 1.86) / 2
    for side in (-1, 1):
        u = middle + side * (0.93 + span / 2)
        wall.box(mesh, u, 0.035, z + 0.32, span, 0.08, 0.64, C['stone'])
        for row in range(2):
            for col in range(4):
                left = max(0, (col - 0.5 * row) * span / 3)
                right = min(span, (col + 1 - 0.5 * row) * span / 3)
                if right > left:
                    wall.box(
                        mesh,
                        u - span / 2 + (left + right) / 2,
                        0.08,
                        z + 0.16 + 0.32 * row,
                        right - left - 0.012,
                        0.024,
                        0.305,
                        C['dormPaverGrey'],
                    )
    wall.box(mesh, middle, 0.49, z + 3.36, 2.91, 1.05, 0.18, C['stone'])
    wall.box(mesh, middle, 0.07, z + 3.82, 1.58, 0.10, 0.73, C['dormWindow'])
    for h in (3.50, 3.82, 4.14):
        wall.box(mesh, middle, 0.14, z + h, 1.6, 0.07, 0.055, C['dormScreen'])
    for i in range(7):
        wall.box(
            mesh,
            middle + (i - 3) * 0.25,
            0.14,
            z + 3.82,
            0.055,
            0.07,
            0.68,
            C['dormScreen'],
        )


def west_dorm(b, z, C, detail):
    number = NUMBERS[b['id']]
    ring = b['polygons'][0][0]
    clockwise = sum(a[0] * c[1] - c[0] * a[1] for a, c in zip(ring, ring[1:])) < 0
    floors = int(b['form']['levels'])
    height = b['form']['height']
    floor = height / floors
    body, roof, entry, trim = Mesh(), Mesh(), Mesh(), Mesh()
    body.extrude(b['polygons'], b['roofTriangles'], z - 1.4, 1.54, C['stone'])
    wing_poly, wing_tri = (
        floor_outline(ring, clockwise)
        if number != 1
        else (b['polygons'], b['roofTriangles'])
    )
    eaves = eave_outline(ring, clockwise, number)
    for level in range(1, floors + 1):
        slab = roof if level == floors else body
        polys, triangles = (
            (eaves, b['roofTriangles']) if level == floors else (wing_poly, wing_tri)
        )
        slab.extrude(
            polys,
            triangles,
            z + level * floor - 0.16,
            0.16,
            C['white'],
            C['paleRoof'],
        )
        # The underside is visible when looking up from a recessed balcony.
        for poly, tri in zip(polys, triangles):
            pts = [p for r in poly for p in r[:-1]]
            for i in range(0, len(tri), 3):
                slab.face(
                    [
                        (*pts[k], z + level * floor - 0.16)
                        for k in reversed(tri[i : i + 3])
                    ],
                    C['white'],
                )
    doorway = b['form']['entrances'][0]
    for edge, (a, c) in enumerate(zip(ring, ring[1:])):
        w = Wall(a, c, clockwise)
        entry_wall = number == 1 and edge == doorway['edge']
        if entry_wall and detail:
            west_one_entry_finish(w, trim, z, C)
        south = w.ny < -0.98 and w.length > 34
        gallery = w.ny > 0.98 and w.length > 16
        tower = number != 1 and w.ny > 0.98 and 10 < w.length < 16
        south_entry = south and number != 1
        if south_entry:
            stair_width = w.length / 13
            stair_screen(w, entry, trim, z, height, stair_width, C, detail)
            arched_screen(w, roof, z + height, w.length * 0.39, C, pierced=True)
        if tower:
            arched_screen(w, roof, z + height, w.length, C)
        for level in range(floors):
            base = z + level * floor
            lower = level < 2
            if south:
                count = 13 if south_entry else 10
                width = w.length / count
                for i in range(count):
                    if south_entry and i == count // 2:
                        continue
                    balcony(
                        w,
                        body,
                        trim,
                        base,
                        floor,
                        level,
                        (i + 0.5) * width,
                        width,
                        number,
                        C,
                        detail,
                    )
                # Close the last bay at the end wall and reveal the recessed portal.
                for u in (
                    [w.length - 0.12, w.length / 2 - stair_width / 2]
                    if south_entry
                    else [w.length - 0.12]
                ):
                    w.box(
                        body,
                        u,
                        -0.78,
                        base + floor / 2,
                        0.24,
                        1.58,
                        floor,
                        C['dormRose' if lower else 'white'],
                    )
            elif gallery:
                north_gallery(w, body, trim, base, floor, lower, C, detail)
            else:
                w.box(
                    body,
                    w.length / 2,
                    -0.10,
                    base + floor / 2,
                    w.length,
                    0.20,
                    floor,
                    C['dormRose' if lower else 'white'],
                )
                has_windows = tower or (
                    w.length < 9 and (number == 1 or abs(w.nx) > 0.98)
                )
                if has_windows and not (entry_wall and level < 2):
                    panes = 4 if tower else 2 if w.length > 5 else 1
                    for i in range(panes):
                        u = (i + 0.5) * w.length / panes
                        width = (0.66 if i in (0, 3) else 1.14) if tower else 0.85
                        w.box(
                            body, u, 0.025, base + 1.72, width, 0.06, 1.42, C['glass']
                        )
                        if detail:
                            w.box(
                                trim, u, 0.07, base + 1.72, 0.05, 0.04, 1.42, C['white']
                            )
                w.box(
                    body,
                    w.length / 2,
                    0.015,
                    base + floor - 0.12,
                    w.length,
                    0.09,
                    0.13,
                    C['white' if lower else 'dormRose'],
                )
        w.box(
            roof,
            w.length / 2,
            -0.10,
            z + height + 0.105,
            w.length,
            0.20,
            0.21,
            C['white'],
        )
    roof_equipment(b, number, roof, z + height, C)
    x, y = doorway['center']
    angle = -math.radians(doorway['bearing'])
    nx, ny = math.sin(-angle), math.cos(angle)
    entry.box(
        x + 0.91 * nx,
        y + 0.91 * ny,
        z + 0.025,
        doorway['width'] + 0.76,
        1.98,
        0.10,
        C['stone'],
        angle,
    )
    approach(entry, b, z, C, number)
    if number == 1:
        west_one_awning(entry, (x, y), (nx, ny), z, C)
        entry.box(
            x + nx * 0.07, y + ny * 0.07, z + 1.13, 1.7, 0.17, 2.25, C['dark'], angle
        )
    result = Mesh()
    for name, mesh in [
        ('01_主体轮廓', body),
        ('02_屋顶轮廓', roof),
        ('03_入口与平台', entry),
        ('04_立面窗格', trim),
    ]:
        if mesh.v:
            result.add_part(name, mesh)
    if number == 2:
        result.add_part('05_园区入口与门房', west_entry(C, detail))
    if number == 3:
        result.add_part('05_楼间步道草坡', garden_banks(C))
    if number == 4:
        result.add_part('06_沿街步道与边坡', front_walk(C))
    if number in (4, 5):
        result.add_part('05_沿街绿篱', street_hedges(b, C))
    return result
