"""East Residence 27 and its ground-floor serving hall, recorded in 2024 and 2026."""

import math

from dining_interiors import interior_finish
from geometry import MATERIALS, Mesh, tile_material

EAST27_ID = 'relation/12774256'
# Local x follows the long wings eastwards. The origin is on the photographed counter.
COUNTER_STATION = 98.0
COUNTER_INSET = 15.5


def hall_frame(b):
    ring = b['polygons'][0][0]
    west, east = ring[2], ring[1]
    angle = math.atan2(east[1] - west[1], east[0] - west[0])
    c, s = math.cos(angle), math.sin(angle)
    return (
        west[0] + COUNTER_STATION * c - COUNTER_INSET * s,
        west[1] + COUNTER_STATION * s + COUNTER_INSET * c,
        angle,
    )


def east27(b, z, colors, detail):
    body, roof, entry, finish = Mesh(), Mesh(), Mesh(), Mesh()
    ox, oy, angle = hall_frame(b)
    c, s = math.cos(angle), math.sin(angle)

    def to_local(point):
        x, y = point[0] - ox, point[1] - oy
        return [x * c + y * s, -x * s + y * c]

    polygons = [
        [[to_local(v) for v in ring] for ring in polygon] for polygon in b['polygons']
    ]

    def paint(name, rgb, rough=0.68, metal=0):
        return interior_finish(colors, 'east27' + name, rgb, rough, metal)

    white = paint('Ceramic', (0.86, 0.86, 0.84), 0.35)
    shell = paint('Concrete', (0.72, 0.72, 0.68))
    floor = paint('Terrazzo', (0.64, 0.64, 0.49), 0.50)
    trim = paint('Aluminium', (0.41, 0.43, 0.42), 0.32, 0.52)
    steel = paint('DarkSteel', (0.041, 0.044, 0.044), 0.49, 0.38)
    glass = paint('DormGlass', (0.13, 0.19, 0.20), 0.28, 0.38)
    shelf = paint('Worktop', (0.63, 0.65, 0.61), 0.32, 0.45)
    ochre = paint('Orange', (0.79, 0.41, 0.057))
    pink = paint('Laminate', (0.84, 0.81, 0.82), 0.42)
    teal = paint('Runner', (0.024, 0.070, 0.080), 0.52)
    red = paint('SupplyPipe', (0.48, 0.048, 0.027), 0.48)
    blue = paint('Display', (0.085, 0.18, 0.24), 0.35)
    light = paint('Tube', (0.98, 0.98, 0.89), 0.38)
    shader = MATERIALS[light].node_tree.nodes.get('Principled BSDF')
    shader.inputs['Emission Color'].default_value = (1, 0.98, 0.90, 1)
    shader.inputs['Emission Strength'].default_value = 2.0
    tile_material(colors, 'east27Menus', 'east27-menu.png', (0.90, 0.76, 0.49))
    menu = colors['east27Menus']
    tile_material(colors, 'east27Table', 'east27-table.png', (0.75, 0.80, 0.78))
    height = b['height']
    # Preserve the OSM courtyard in the floor, upper shell and roof.
    body.extrude(polygons, b['roofTriangles'], -0.5, 0.57, shell, floor)
    body.extrude(polygons, b['roofTriangles'], 3.64, height - 3.64, shell)
    roof.extrude(polygons, b['roofTriangles'], height, 0.12, shell, colors['paleRoof'])
    east_end = polygons[0][0][1][0]
    parapet = paint('Parapet', (0.70, 0.68, 0.62))
    deck = paint('RoofDeck', (0.42, 0.39, 0.34), 0.93)
    collector = paint('Collector', (0.20, 0.22, 0.24), 0.44, 0.26)
    # The aerial shows the long roof edges and the low upstand around the court.
    for contour in polygons[0]:
        for start, end in zip(contour, contour[1:]):
            dx, dy = end[0] - start[0], end[1] - start[1]
            roof.box(
                (start[0] + end[0]) / 2,
                (start[1] + end[1]) / 2,
                height + 0.34,
                math.hypot(dx, dy),
                0.20,
                0.54,
                parapet,
                math.atan2(dy, dx),
            )
    # Paved cross-path between the two planted beds at the bottom of the court.
    entry.box(-34, 16.55, 0.045, 121.1, 20.1, 0.09, floor)
    grass = paint('CourtLawn', (0.12, 0.24, 0.11), 0.96)
    for x in (-64.2, -3.55):
        entry.box(x, 16.55, 0.10, 55.4, 15.2, 0.04, grass)
    # Underside of the floor above the canteen, with openings to the outside at grade.
    body.box(-7.5, -6.35, 3.635, 51, 18.5, 0.07, white)
    ring = polygons[0][0]
    span = math.dist(ring[1], ring[2])
    # Other ground-floor walls follow the two outlines. Along the public side the
    # hall occupies part of the residential wing, opening between square columns.
    for contour in polygons[0]:
        for a, end in zip(contour, contour[1:]):
            length = math.dist(a, end)
            theta = math.atan2(end[1] - a[1], end[0] - a[0])
            ux, uy = (end[0] - a[0]) / length, (end[1] - a[1]) / length
            south_edge = contour is ring and a == ring[1] and end == ring[2]
            sections = (
                [(0, span - COUNTER_STATION - 18), (span - COUNTER_STATION + 33, span)]
                if south_edge
                else [(0, length)]
            )
            for start, stop in sections:
                t = (start + stop) / 2
                body.box(
                    a[0] + ux * t,
                    a[1] + uy * t,
                    1.855,
                    stop - start,
                    0.20,
                    3.57,
                    white,
                    theta,
                )
            # Bands of dormitory windows above the open service floor.
            if contour is ring and a == ring[0] and end == ring[1]:
                # East gable has two small vertical window stacks flanking a wider one.
                for level in range(6):
                    h = 1.88 + level * (height - 0.72) / 6
                    for mid, width in ((-4.5, 3.1), (16.4, 16.7), (36.4, 3.1)):
                        entry.box(east_end + 0.045, mid, h, 0.10, width, 1.65, glass)
                        entry.box(
                            east_end + 0.12,
                            mid,
                            h - 0.85,
                            0.32,
                            width + 0.34,
                            0.15,
                            parapet,
                        )
                        if detail and width > 4:
                            finish.box(east_end + 0.13, mid, h, 0.14, 0.30, 1.63, white)
                continue
            count = max(1, round(length / 3.55))
            for level in range(1, round(b['levels'])):
                h = 3.64 + (level - 1) * (height - 3.64) / (b['levels'] - 1)
                if detail:
                    for i in range(count):
                        t = length * (i + 0.5) / count
                        finish.box(
                            a[0] + ux * t,
                            a[1] + uy * t,
                            h + 1.57,
                            length / count * 0.58,
                            0.24,
                            1.48,
                            glass,
                            theta,
                        )
    for x in range(-32, 18, 8):
        body.box(x, -15.3, 1.86, 0.48, 0.50, 3.58, white)
    # One low continuous apron. The precise outside threshold is undocumented.
    entry.box(-7.5, -15.77, -0.024, 51.1, 1.22, 0.174, floor)
    # The clear route to the counter is on the side facing the near table row.
    body.box(-7.5, 2.85, 1.83, 51, 0.2, 3.56, white)
    for x in (-33, 18):
        body.box(x, -6.35, 1.84, 0.19, 18.5, 3.56, white)
    first = -6
    for i in range(first, 2):
        x = i * 4.5
        variant = (-i) % 4
        entry.box(x + 2.25, 0.18, 0.50, 4.49, 0.56, 0.86, white)
        entry.box(x + 2.25, -0.01, 0.955, 4.50, 0.81, 0.09, shelf)
        entry.box(x + 2.25, 0.10, 2.425, 4.50, 0.23, 1.55, ochre)
        # The orange fascia is above the menu panels, with an open serving slot below.
        left = (variant % 2) * 0.5
        right = left + 0.5
        top = 1 - (variant // 2) * 0.5
        bottom = top - 0.5
        entry.face(
            [
                (x, -0.024, 1.65),
                (x + 4.5, -0.024, 1.65),
                (x + 4.5, -0.024, 3.20),
                (x, -0.024, 3.20),
            ],
            menu,
            [(left, bottom), (right, bottom), (right, top), (left, top)],
        )
        if detail:
            for dx in (0.04, 2.25, 4.46):
                finish.box(x + dx, -0.045, 1.30, 0.045, 0.055, 0.68, trim)
            finish.box(x + 2.25, -0.085, 1.65, 4.50, 0.075, 0.065, trim)
            for dx in (1.10, 3.20):
                finish.box(x + dx, -0.23, 1.04, 0.06, 0.09, 0.13, steel)
                finish.box(x + dx, -0.23, 1.18, 0.23, 0.075, 0.16, blue)
                finish.box(x + dx, -0.275, 1.18, 0.19, 0.014, 0.12, light)
                finish.box(x + dx, 1.15, 1.02, 1.75, 0.69, 0.11, shelf)
                finish.box(x + dx, 1.14, 1.35, 1.75, 0.39, 0.06, shelf)
                for post in (-0.77, 0.77):
                    finish.box(x + dx + post, 1.18, 1.20, 0.044, 0.044, 0.33, trim)
                for pan, filling in enumerate((ochre, teal, red)):
                    px = x + dx + (pan - 1) * 0.46
                    finish.box(px, 0.53, 1.00, 0.43, 0.31, 0.06, shelf)
                    # The underside sits inside the metal pan.
                    finish.box(
                        px, 0.53, 1.032, 0.37, 0.26, 0.009, filling, bottom=False
                    )
    # Exposed white beams, red supply lines and suspended strip lights run above
    # the file of square piers between the seats and the serving windows.
    for i in range(-7, 5):
        x = -1.08 + i * 4.5
        if i != 1:
            body.box(x, -2.60, 1.85, 0.78, 0.70, 3.56, white)
        body.box(x, -6.35, 3.42, 0.38, 18.40, 0.43, shell)
        if detail:
            if i < 0:
                finish.box(x, -2.962, 1.71, 0.28, 0.022, 0.44, blue)
            if i != 1:
                for h in (0.71, 1.35, 1.99, 2.63, 3.27):
                    finish.box(x, -2.954, h, 0.77, 0.009, 0.008, trim)
            finish.box(x, -8.7, 3.18, 0.72, 0.58, 0.18, white)
            for offset in (-0.29, 0.29):
                finish.box(x + offset, -8.7, 3.40, 0.017, 0.017, 0.36, trim)
            finish.box(x, -5.7, 3.13, 1.12, 0.095, 0.057, light)
            finish.box(x, -0.96, 3.1, 1.13, 0.08, 0.052, light)
    body.box(-1.08, -6.9, 1.85, 0.72, 0.72, 3.56, white)
    if detail:
        for y in (-2.55, -9.32):
            finish.line((-33, y, 3.14), (18, y, 3.14), 0.080, red, 10)
            finish.box(-7.5, y - 0.18, 3.31, 51, 0.14, 0.14, trim)

        def table(x, y, crosswise, runner, featured=False):
            theta = math.pi / 2 if crosswise else 0

            def part(dx, dy, h, length, width, depth, material):
                if featured:
                    dx *= 0.63
                    length *= 0.63
                px, py = (-dy, dx) if crosswise else (dx, dy)
                finish.box(x + px, y + py, h, length, width, depth, material, theta)

            if featured:
                # The two short ends are visible in the welcome inspection photo.
                finish.box(x, y, 0.805, 0.71, 1.17, 0.05, pink)
                finish.face(
                    [
                        (x + dx, y + dy, 0.832)
                        for dx, dy in (
                            (-0.355, -0.585),
                            (0.355, -0.585),
                            (0.355, 0.585),
                            (-0.355, 0.585),
                        )
                    ],
                    colors['east27Table'],
                    [(0, 0), (0, 1), (1, 1), (1, 0)],
                )
            else:
                part(0, 0, 0.805, 1.86, 0.76, 0.05, pink)
            if runner:
                part(0, 0, 0.832, 1.85, 0.245, 0.004, teal)
            for dy in (-0.31, 0.31):
                part(0, dy, 0.76, 1.66, 0.042, 0.044, steel)
                for dx in (-0.80, 0.80):
                    part(dx, dy, 0.42, 0.048, 0.048, 0.70, steel)
            for dy in (-0.63, 0.63):
                part(0, dy, 0.475, 1.72, 0.26, 0.045, pink)
                for dx in (-0.75, 0.75):
                    part(dx, dy, 0.35, 0.042, 0.045, 0.20, steel)
                    part(dx, dy * 0.76, 0.25, 0.042, 0.34, 0.045, steel)
            for dy in (-0.18, 0, 0.18):
                part(0, dy, 0.49, 1.63, 0.016, 0.025, steel)

        for j, y in enumerate((-5.15, -7.75, -10.35, -12.95)):
            for i in range(15):
                x = -29 + i * 3.12
                if abs(x - 1.35) < 2 and abs(y + 8.9) < 2:
                    continue
                if abs(x - 8.55) < 2 and abs(y + 10.3) < 2:
                    continue
                table(x, y, True, i % 5 == 0 and j < 2)
        table(1.33, -8.54, True, False, featured=True)
        table(8.55, -10.42, True, False)
        # The aerial and overhead image show paired equipment fields at both ends.
        for bed in (-63.8, -3.55):
            for station in range(-2, 3):
                x = bed + station * 7.10
                finish.cylinder(x, 16.8, 0.14, 0.11, 1.45, colors['wood'], 7)
                finish.ellipsoid(x, 16.8, 2.10, 1.85, 1.78, 1.32, grass, 9, 5)
        for mid in (-4.55, 38.0):
            finish.box(-31.0, mid, height + 0.137, 126.9, 20.2, 0.025, deck)
            finish.box(-47.4, mid, height + 0.285, 93.7, 0.18, 0.27, parapet)
            for x in (-71.7, -44.1, -16.5, 1.4):
                finish.box(x, mid, height + 0.25, 0.18, 20.2, 0.20, parapet)
            for start in (-94.8, -81.05, east_end - 29.1, east_end - 15.35):
                for i in range(5):
                    for j in range(7):
                        x = start + (i + 0.5) * 2.57
                        y = mid + (j - 3) * 2.72
                        finish.box(x, y, height + 0.32, 2.40, 2.54, 0.24, collector)
                        finish.box(x, y - 1.12, height + 0.46, 2.40, 0.095, 0.05, trim)
                finish.box(start + 13.2, mid, height + 0.30, 0.23, 19.8, 0.22, parapet)
    m = Mesh()
    for name, part in [
        ('01_主体轮廓', body),
        ('02_屋顶轮廓', roof),
        ('03_入口与平台', entry),
        ('04_供餐窗与桌椅', finish),
    ]:
        if part.v:
            m.add_part(name, part)
    m.v = [(ox + x * c - y * s, oy + x * s + y * c, z + h) for x, y, h in m.v]
    return m
