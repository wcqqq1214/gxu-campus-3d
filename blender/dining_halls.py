"""Dining hall exteriors. Dimensions and unphotographed returns are estimates."""

import math
from dataclasses import dataclass
from pathlib import Path

from beiyuan import east_front, west_front
from bihuyuan_stair import exterior_stair
from bihuyuan_stair import finishes as stair_finishes
from bocui import bocui
from cuiyuan import cui, upper_court, wing
from dongyuan import cast_letter as dong_letter
from dongyuan import finishes as dong_finishes
from dongyuan import north_window as dong_window
from dongyuan import west_front as dong_west
from geometry import Mesh, material, tile_material
from south_gate import inscription
from xiuyuan import xiuyuan

CUI = 'way/759337794'
BO = 'way/1544361473'
DONG = 'way/759191485'
XIU = 'way/822812186'
BI = 'way/759609659'
BEI = 'way/760187419'

# Edges of the mapped outer ring and the storeys replaced by the photo facade.
# Opposite one another across the forecourt, Cui faces south and Bo faces north.
FRONTS = {
    CUI: {edge: (0, 1) for edge in (10, 9, 8, 7, 6, 11, 0, 1, 2)},
    BO: {1: tuple(range(6))},
    DONG: {3: (0, 1, 2, 3), 2: (0, 1, 2, 3)},
    XIU: {4: (0, 1, 2, 3, 4)},
    BI: {1: (0, 1), 0: (0,)},
    BEI: {0: (0, 1, 2, 3, 4), 2: (0, 1, 2, 3, 4)},
}


@dataclass
class Elevation:
    structure: Mesh
    glazing: Mesh
    colors: dict
    length: float
    height: float
    detail: bool

    def box(self, x, out, z, width, depth, height, finish):
        self.structure.box(x, -out, z, width, depth, height, self.colors[finish])

    def trim(self, x, out, z, width, depth, height, finish):
        self.glazing.box(x, -out, z, width, depth, height, self.colors[finish])

    def cladding(self, left, right, bottom, top, out, finish, repeat=0.8):
        # Metre-based UVs keep the small tile joints aligned across neighbouring bays.
        coords = [
            (left, -out, bottom),
            (right, -out, bottom),
            (right, -out, top),
            (left, -out, top),
        ]
        self.structure.face(
            coords,
            self.colors[finish],
            [(x / repeat, z / repeat) for x, _, z in coords],
        )

    def pane(
        self,
        x,
        out,
        bottom,
        width,
        height,
        columns=2,
        *,
        sash=True,
        glass='residenceGlass',
    ):
        center = bottom + height / 2
        g, c = self.glazing, self.colors
        g.box(x, -out, center, width, 0.09, height, c['dark'])
        g.box(
            x,
            -out - 0.055,
            center,
            width - 0.12,
            0.045,
            height - 0.12,
            c[glass],
        )
        if self.detail:
            for col in range(1, columns):
                g.box(
                    x + width * (col / columns - 0.5),
                    -out - 0.10,
                    center,
                    0.06,
                    0.055,
                    height,
                    c['metal'],
                )
            if sash:
                g.box(
                    x,
                    -out - 0.10,
                    bottom + height * 0.72,
                    width,
                    0.055,
                    0.06,
                    c['metal'],
                )

    def door(self, x, out, bottom, width, height):
        self.pane(x, out, bottom, width, height, 4)
        for offset in (-0.13, 0.13):
            self.glazing.box(
                x + offset,
                -out - 0.19,
                bottom + 1.13,
                0.045,
                0.08,
                0.57,
                self.colors['metal'],
            )
        self.glazing.box(
            x,
            -out - 0.14,
            bottom + height * 0.77,
            width,
            0.10,
            0.10,
            self.colors['dark'],
        )


def dong_front(e):
    # North short end, adjoining the main west frontage.
    dong_finishes(e)
    w = e.length
    tile_material(e.colors, 'dongPorcelain', 'dong-porcelain.png', (0.74, 0.74, 0.71))
    e.cladding(-w / 2, w / 2, 0, e.height, 0.045, 'dongPorcelain')

    # The signed end has four narrow stacks, a wider paired stack, then
    # one narrow stack beside the raised sign pier (project booklet, p. 39).
    for x, span, upper_sill, opening in [
        (-12.734, 1.401, 10.412, 1.616),
        (-9.922, 1.459, 10.4, 1.613),
        (-7.08, 1.353, 10.334, 1.695),
        (-4.182, 1.464, 10.486, 1.616),
        (0.124, 2.292, 10.377, 1.703),
        (4.454, 1.47, 10.281, 1.767),
    ]:
        for level in range(4):
            if level == 0 and (x > 3 or -8.3 < x < -4.5):
                continue
            bottom = upper_sill - (3 - level) * 3.23
            dong_window(e, x, bottom, span, opening)
            e.box(x, 0.26, bottom - 0.038, span + 0.20, 0.34, 0.10, 'paleRoof')
    e.pane(-w * 0.23, 0.26, 0.08, 3.35, 2.78, 3)
    # The project booklet and northwest street view show one continuous canopy.
    e.box(-2.40, 0.99, 3.13, 16.40, 1.98, 0.26, 'paleRoof')
    e.door(4.10, 0.25, 0.10, 1.78, 2.67)
    if e.detail:
        for j in range(69):
            e.glazing.box(
                -10.48 + j * 0.237, -1.92, 3.56, 0.032, 0.035, 0.62, e.colors['metal']
            )
        e.glazing.box(-2.40, -1.92, 3.88, 16.32, 0.055, 0.055, e.colors['metal'])
    # The sign panel rises above the regular eave and meets the corner service strip.
    width = w / 2 - 2.85
    e.box(w / 2 - width / 2, -0.10, e.height + 1.05, width, 0.44, 2.1, 'white')
    e.cladding(2.85, w / 2, e.height, e.height + 2.10, 0.125, 'dongPorcelain')
    for char, x, z, width, height in [
        ('东', 11.278, 11.029, 0.95, 0.904),
        ('苑', 11.288, 8.607, 1.045, 0.8),
        ('餐', 11.272, 6.258, 1.067, 0.898),
        ('厅', 11.272, 3.784, 0.97, 0.822),
    ]:
        dong_letter(e, char, x, -0.21, z, width, height, 'gateRed')
    if e.detail:
        e.glazing.box(4.10, -0.37, 2.58, 1.73, 0.048, 0.32, e.colors['dongRed'])
        for u in [4.41, 0.06, -4.17]:
            for i in range(-4, 5):
                e.glazing.box(
                    u + i * 0.133, -0.282, 4.86, 0.018, 0.03, 1.38, e.colors['dongSash']
                )
    if e.detail:
        start, stop = -w / 2 + 0.36, 2.82
        for i in range(11):
            e.glazing.box(
                start + (stop - start) * i / 10,
                0.16,
                e.height + 0.43,
                0.047,
                0.048,
                0.86,
                e.colors['metal'],
            )
        for h in (0.39, 0.80):
            e.glazing.box(
                (start + stop) / 2,
                0.16,
                e.height + h,
                stop - start,
                0.046,
                0.045,
                e.colors['metal'],
            )

    # A dark recessed service strip at the outside corner, crossed by short collars.
    e.box(w * 0.48, 0.16, e.height / 2, 0.27, 0.22, e.height, 'dark')
    e.glazing.cylinder(
        w * 0.48, -0.34, e.height / 2, 0.075, e.height, e.colors['metal'], n=10
    )
    if e.detail:
        for height in (1.9, 4.9, 8.1, 11.4):
            e.glazing.box(w * 0.48, -0.32, height, 0.29, 0.18, 0.05, e.colors['dark'])
    for x, z in [(-9.9, 4.55), (-4.32, 9.94), (-0.10, 9.94)]:
        e.box(x, 0.40, z, 0.83, 0.66, 0.63, 'paleRoof')
        if e.detail:
            for j in range(6):
                e.glazing.box(
                    x,
                    -0.742,
                    z - 0.20 + j * 0.083,
                    0.60,
                    0.018,
                    0.029,
                    e.colors['metal'],
                )


# South-edge frame. The last arched bay, balcony and stair share a street face.
BI_STAIR_Y = 7.32
BI_SHOP_WALL_Y = 4.78
BI_ARCADE_Y = 2.63


def bihuyuan_shell(b):
    # Recess the shop wall behind the arcade while keeping both mapped entrances.
    ring = b['polygons'][0][0]
    se, sw = ring[1:3]
    length = math.dist(se, sw)
    dx, dy = (se[0] - sw[0]) / length, (se[1] - sw[1]) / length
    south = [[x - dy * BI_SHOP_WALL_Y, y + dx * BI_SHOP_WALL_Y] for x, y in (se, sw)]
    return {**b, 'polygons': [[[ring[0], *south, *ring[3:]]]]}


def bihuyuan_grille(e, x, front, bottom, spring, radius, rise):
    # Fine upright guards in front of the wider window sashes.
    for col in range(1, 32):
        u = (col / 16 - 1) * radius
        top = spring + rise * math.sqrt(1 - (u / radius) ** 2)
        e.glazing.face(
            [
                (x + u + dx, -front, z)
                for dx, z in (
                    (-0.008, bottom),
                    (0.008, bottom),
                    (0.008, top),
                    (-0.008, top),
                )
            ],
            e.colors['biGrille'],
        )


def bihuyuan_arcade(e):
    w = e.length
    left, end = -w / 2 + 0.26, w / 2 - 0.88
    bays = round((end - left) / 3.48)
    span = (end - left) / bays
    front = BI_SHOP_WALL_Y - BI_ARCADE_Y
    sill, spring, head, cap = 4.45, 6.88, 7.59, 7.98
    for j in range(bays):
        x = left + (j + 0.5) * span
        if abs(x) < span / 2:
            e.door(x, 0.15, 0.09, span - 0.40, 2.66)
        else:
            e.pane(x, 0.15, 0.17, span - 0.40, 2.58, 4, glass='biWindow')
            if e.detail and j < bays - 1:
                bihuyuan_grille(e, x, 0.29, 0.17, 2.75, (span - 0.40) / 2, 0)
        x -= 0.029
        r = (span - 0.39) / 2
        for lo, hi in [(x - span / 2 - 0.02, x - r), (x + r, x + span / 2 + 0.045)]:
            e.cladding(lo, hi, sill, head, front, 'biIvoryTile')
        e.pane(
            x, front - 0.11, sill, 2 * r, spring - sill, 1, sash=False, glass='biWindow'
        )
        for k in range(16):
            a, b = math.pi * k / 16, math.pi * (k + 1) / 16
            u0, h0 = x + r * math.cos(a), spring + 0.34 * math.sin(a)
            u1, h1 = x + r * math.cos(b), spring + 0.34 * math.sin(b)
            e.glazing.face(
                [(x, -front, spring), (u0, -front, h0), (u1, -front, h1)],
                e.colors['biWindow'],
            )
            e.structure.face(
                [
                    (u0, -front, h0),
                    (u0, -front, head),
                    (u1, -front, head),
                    (u1, -front, h1),
                ],
                e.colors['biIvoryTile'],
                [
                    (u0 / 0.8, h0 / 0.8),
                    (u0 / 0.8, head / 0.8),
                    (u1 / 0.8, head / 0.8),
                    (u1 / 0.8, h1 / 0.8),
                ],
            )
            if e.detail:
                e.glazing.line(
                    (u0, -front - 0.03, h0),
                    (u1, -front - 0.03, h1),
                    0.026,
                    e.colors['metal'],
                )
        if e.detail:
            bihuyuan_grille(e, x, front + 0.01, sill, spring, r, 0.34)
            for col in range(1, 4):
                u = 2 * r * (col / 4 - 0.5)
                h = spring - sill + 0.34 * math.sqrt(max(0, 1 - (u / r) ** 2))
                e.glazing.box(
                    x + u,
                    -front - 0.025,
                    sill + h / 2,
                    0.033,
                    0.022,
                    h,
                    e.colors['biGrille'],
                )
            for up in (0.41, 1.43, 2.40):
                e.glazing.box(
                    x,
                    -front - 0.046,
                    sill + up,
                    2 * r,
                    0.025,
                    0.025,
                    e.colors['biGrille'],
                )
        x += 0.029
        for bottom, top in [(3.45, sill), (head, cap)]:
            e.box(x, front / 2, (bottom + top) / 2, span, front, top - bottom, 'stone')
            e.cladding(
                x - span / 2, x + span / 2, bottom, top, front + 0.012, 'biIvoryTile'
            )
            e.cladding(
                x - span / 2,
                x + span / 2,
                bottom + (0.43 if bottom < sill else 0.18),
                bottom + (0.56 if bottom < sill else 0.31),
                front + 0.022,
                'biRoseTile',
            )
        e.cladding(
            x - 0.28, x + 0.28, head + 0.12, head + 0.36, front + 0.032, 'biRoseTile'
        )
    for j in range(bays + 1):
        x = left + j * span
        e.box(x, front - 0.02, (3.34 + cap) / 2, 0.32, 0.54, cap - 3.34 + 0.15, 'stone')
        e.cladding(x - 0.16, x + 0.16, 3.265, cap + 0.075, front + 0.255, 'biIvoryTile')
        e.box(x, 0.48, 1.9, 0.31, 0.48, 3.8, 'stone')
    # The upper strip closes the back of the gallery above the main flat roof.
    e.box(
        (end + left) / 2,
        -0.15,
        (cap + e.height) / 2,
        end - left,
        0.34,
        cap - e.height,
        'stone',
    )
    # Open end bay. The fascia returns north to the narrower sloping cover.
    tip = w / 2 + 0.67
    center, width = (end + tip) / 2, tip - end
    rear = BI_SHOP_WALL_Y - BI_STAIR_Y
    depth, out = front - rear, (front + rear) / 2
    for bottom, top in ((3.05, 3.28), (7.33, 7.84)):
        e.box(center, out, (top + bottom) / 2, width, depth, top - bottom, 'stone')
    for bottom, top, stripe in ((3.05, 4.31, 3.83), (7.33, 7.84, 7.52)):
        e.box(
            center, front - 0.09, (bottom + top) / 2, width, 0.18, top - bottom, 'stone'
        )
        e.cladding(end, tip, bottom, top, front + 0.01, 'biIvoryTile')
        e.cladding(end, tip, stripe, stripe + 0.14, front + 0.02, 'biRoseTile')
        turn = BI_STAIR_Y - 0.44 - BI_ARCADE_Y
        for lo, hi, finish in (
            (bottom, top, 'biIvoryTile'),
            (stripe, stripe + 0.14, 'biRoseTile'),
        ):
            x = tip + (0.012 if finish == 'biRoseTile' else 0.0)
            e.structure.face(
                [
                    (x, -front, lo),
                    (x, -front + turn, lo),
                    (x, -front + turn, hi),
                    (x, -front, hi),
                ],
                e.colors[finish],
                [
                    (0, lo / 0.8),
                    (turn / 0.8, lo / 0.8),
                    (turn / 0.8, hi / 0.8),
                    (0, hi / 0.8),
                ],
            )
    post = tip - 0.26
    e.box(post, front - 0.68, 3.67, 0.25, 0.35, 7.34, 'stone')
    e.cladding(post - 0.125, post + 0.125, 0.05, 7.34, front - 0.50, 'biIvoryTile')
    e.pane(end - 0.8, 0.10, 4.12, 1.58, 2.12, 3)
    shop = end - span / 2
    e.box(shop, front - 0.10, 2.85, span - 0.12, 0.24, 1.03, 'white')
    e.box(shop, front + 0.045, 2.85, span * 0.58, 0.045, 0.72, 'gateRed')
    if e.detail:
        e.glazing.extend(
            inscription(
                '粉之都',
                shop,
                -front - 0.075,
                2.88,
                span * 0.49,
                0.41,
                e.colors['white'],
                False,
            )
        )
    for i in range(2):
        e.box(
            end - span * (1.50 + i * 0.29),
            front + 0.17,
            4.42,
            0.84,
            0.51,
            0.64,
            'paleRoof',
        )
        if e.detail:
            x = end - span * (1.50 + i * 0.29)
            e.glazing.line(
                (x - 0.09, -front - 0.427, 4.42),
                (x - 0.09, -front - 0.44, 4.42),
                0.24,
                e.colors['dark'],
                n=20,
            )
            for row in range(-3, 4):
                e.glazing.box(
                    x - 0.09,
                    -front - 0.447,
                    4.42 + row * 0.055,
                    0.37,
                    0.014,
                    0.010,
                    e.colors['biGrille'],
                )


def bihuyuan(e):
    stair_finishes(e.colors)
    if 'biWindow' not in e.colors:
        e.colors['biWindow'] = material('biWindow', (0.065, 0.084, 0.080), 0.30, 0.17)
    if 'biGrille' not in e.colors:
        e.colors['biGrille'] = material('biGrille', (0.55, 0.57, 0.54), 0.58, 0.24)
    arcade = Elevation(Mesh(), Mesh(), e.colors, e.length, e.height, e.detail)
    bihuyuan_arcade(arcade)
    place(arcade.structure, e.structure, 0, BI_SHOP_WALL_Y, 0, 0)
    place(arcade.glazing, e.glazing, 0, BI_SHOP_WALL_Y, 0, 0)
    # Site B on the orthophoto is an eastward projection near the south corner.
    # The stair is drawn along +X (east), with the south host edge as the Y datum.
    stair = Elevation(Mesh(), Mesh(), e.colors, e.length, e.height, e.detail)
    exterior_stair(stair)
    place(stair.structure, e.structure, e.length / 2, BI_STAIR_Y, 0, 0)
    place(stair.glazing, e.glazing, e.length / 2, BI_STAIR_Y, 0, 0)
    e.box(
        0, (1.20 - BI_SHOP_WALL_Y) / 2, 0.045, 5.4, 1.20 + BI_SHOP_WALL_Y, 0.09, 'stone'
    )


FLAVOR_HALF_WIDTH = 6.36


def flavor_window(e, x):
    # The 2016 courtyard views expose the outer jambs cut off by the close-up.
    width, sill, head = 2.84, 0.94, 3.69
    e.pane(x, 0.26, sill, width, head - sill, 1, sash=False, glass='flavorGlass')
    if e.detail:
        grille = e.colors['flavorAluminium']
        for i in range(28):
            u = x + (i / 27 - 0.5) * (width - 0.06)
            e.glazing.box(
                u, -0.355, (sill + head) / 2, 0.017, 0.023, head - sill, grille
            )
        for z in (sill, 1.46, 2.03, 2.53, 3.09, head):
            e.glazing.box(x, -0.367, z, width, 0.028, 0.027, grille)
    e.box(x, 0.27, sill - 0.034, width + 0.09, 0.26, 0.068, 'stone')


def flavor_entry(e):
    # The basketball-court panoramas place the entrance between paired grilles.
    if 'flavorGlass' not in e.colors:
        e.colors['flavorGlass'] = material(
            'flavorGlass', (0.011, 0.018, 0.024), 0.19, 0.22
        )
    for key, rgb, rough, metallic in (
        ('flavorEnamel', (0.029, 0.004, 0.072), 0.62, 0.52),
        ('flavorAluminium', (0.39, 0.40, 0.39), 0.38, 0.63),
        ('flavorJamb', (0.095, 0.094, 0.088), 0.44, 0.48),
        ('flavorBlock', (0.25, 0.25, 0.24), 0.92, 0.0),
        ('flavorPaving', (0.245, 0.235, 0.219), 0.92, 0.0),
        ('flavorGrout', (0.15, 0.15, 0.14), 0.95, 0.0),
    ):
        if key not in e.colors:
            e.colors[key] = material(key, rgb, rough, metallic)
    # The second-floor landing joins this wall south of the restaurant.
    e.door(-e.length / 2 + 6.22, 0.10, 3.28, 1.32, 2.12)
    half_width = FLAVOR_HALF_WIDTH
    stair_finishes(e.colors)
    e.box(0, 0.075, 2.18, 2 * half_width, 0.145, 4.36, 'stone')
    e.cladding(-half_width, half_width, 0.85, 4.36, 0.15, 'biIvoryTile')
    e.box(0, 0.15, 0.425, 2 * half_width, 0.026, 0.85, 'flavorGrout')
    # Staggered dark masonry below the cream tiles.
    for row in range(3):
        x = -half_width - row % 2 * 0.28
        while x < half_width:
            lo, hi = max(x, -half_width), min(x + 0.56, half_width)
            e.box(
                (lo + hi) / 2,
                0.169,
                (row + 0.5) * 0.85 / 3,
                hi - lo - 0.009,
                0.022,
                0.275,
                'flavorBlock',
            )
            x += 0.56
    e.box(0, 0.23, 4.41, 2 * half_width, 0.52, 0.12, 'stone')
    # A single continuous step, with a separate stone slab across the opening.
    e.box(0, 0.53, 0.06, 2 * half_width, 1.06, 0.12, 'flavorBlock')
    e.box(-0.255, 0.57, 0.064, 4.15, 1.14, 0.128, 'flavorBlock')
    e.box(-0.255, 0.57, 0.139, 4.15, 1.14, 0.022, 'flavorPaving')
    for lo, hi in ((-half_width, -2.33), (1.82, half_width)):
        count = round((hi - lo) / 0.52)
        for i in range(count):
            pitch = (hi - lo) / count
            e.box(
                lo + (i + 0.5) * pitch,
                0.53,
                0.132,
                pitch - 0.009,
                1.06,
                0.024,
                'flavorPaving',
            )
    e.box(0, 0.22, 1.245, 2.84, 0.11, 2.19, 'flavorJamb')
    e.pane(0, 0.28, 0.19, 2.24, 2.14, 1, sash=False, glass='flavorGlass')
    e.box(0, 0.335, 0.199, 2.25, 0.075, 0.087, 'flavorAluminium')
    if e.detail:
        for i in range(6):
            e.glazing.box(
                -1.095 + i * 0.438,
                -0.37,
                1.26,
                0.036,
                0.042,
                2.14,
                e.colors['flavorAluminium'],
            )
        for side in (-1, 1):
            for i in range(9):
                e.glazing.box(
                    side * (1.14 + i * 0.032),
                    -0.284,
                    1.245,
                    0.013,
                    0.021,
                    2.19,
                    e.colors['flavorAluminium'],
                )
    # Thin metal rim around the purple enamel panel and an independent top drip.
    e.box(0, 0.235, 2.973, 2.84, 0.17, 1.266, 'flavorJamb')
    e.box(0.022, 0.332, 2.96, 2.75, 0.032, 1.216, 'flavorEnamel')
    e.box(0, 0.257, 3.633, 2.89, 0.14, 0.078, 'flavorJamb')
    e.glazing.extend(
        inscription(
            '风味餐厅',
            0.01,
            -0.355,
            2.95,
            2.43,
            0.63,
            e.colors['white'],
            False,
            flat=not e.detail,
            font_path=Path(__file__).parent / 'fonts/GXUFlavorSign.ttf',
        )
    )
    for x in (-4.30, 4.365):
        flavor_window(e, x)
    for x in (-4.30, 0, 4.365):
        e.pane(x, 0.085, 4.63, 2.62, 1.46, 4)
    for x in (-8.05, 7.99, 11.7):
        e.pane(x, 0.12, 0.78, 2.13, 2.22, 3)
    if e.detail:
        # Two small stone bollards stand just beyond the north end of the threshold slab.
        for x in (2.76, 3.09):
            e.glazing.ellipsoid(
                x,
                -1.19,
                0.145,
                0.16,
                0.16,
                0.15,
                e.colors['flavorPaving'],
                n=16,
                rings=8,
            )
        # Wall plate, vertical downpipe, sign conduit and slim overhead luminaire.
        e.glazing.box(-2.047, -0.169, 2.465, 0.93, 0.027, 0.38, e.colors['white'])
        pipe = e.colors['white']
        e.glazing.line((-2.64, -0.244, 0.15), (-2.62, -0.244, 4.38), 0.054, pipe, n=12)
        for z in (0.47, 1.61, 3.15):
            e.glazing.box(
                -2.625, -0.246, z, 0.123, 0.11, 0.032, e.colors['flavorAluminium']
            )
        cable = [
            (-1.52, -0.20, 4.38),
            (-1.48, -0.20, 3.93),
            (-1.49, -0.23, 3.72),
            (-1.40, -0.34, 3.55),
        ]
        for a, b in zip(cable, cable[1:]):
            e.glazing.line(a, b, 0.018, e.colors['flavorJamb'])
        e.glazing.box(
            -0.02, -0.236, 3.74, 1.14, 0.14, 0.046, e.colors['flavorAluminium']
        )
        e.glazing.box(-0.02, -0.31, 3.726, 1.03, 0.018, 0.024, e.colors['white'])


def place(mesh, result, x, y, z, angle):
    c, s = math.cos(angle), math.sin(angle)
    mesh.v = [(x + c * u - s * v, y + s * u + c * v, z + h) for u, v, h in mesh.v]
    result.extend(mesh)


def photographed_facade(b, z, colors, detail):
    if b['id'] == BO and 'diningLetterRed' not in colors:
        colors['diningLetterRed'] = material(
            'diningLetterRed', (0.66, 0.047, 0.063), 0.45, 0.10
        )
    structure, glazing = Mesh(), Mesh()
    ring = b['polygons'][0][0]
    builders = {
        CUI: [cui, *([wing] * 8)],
        BO: [bocui],
        DONG: [dong_front, dong_west],
        XIU: [xiuyuan],
        BI: [bihuyuan, flavor_entry],
        BEI: [east_front, west_front],
    }
    if b['id'] == CUI:
        # The photographed wing cladding projects beyond the mapped structural outline.
        ring = [(x, y - 1.04 if 6 <= i <= 9 else y) for i, (x, y) in enumerate(ring)]
    for edge, build in zip(FRONTS[b['id']], builders[b['id']], strict=True):
        a, c = ring[edge : edge + 2]
        # The rings run clockwise. Orient local +X to the viewer's right.
        length = math.dist(a, c)
        angle = math.atan2(a[1] - c[1], a[0] - c[0])
        e = Elevation(Mesh(), Mesh(), colors, length, b['height'], detail)
        if build is bocui:
            entry = next(entry for entry in b['form']['entrances'] if entry['primary'])
            offset = length * (0.5 - entry['t'])
            bocui(e, offset)
            for mesh in (e.structure, e.glazing):
                mesh.v = [(x + offset, y, height) for x, y, height in mesh.v]
        elif build is wing:
            wing(e, edge)
        else:
            build(e)
        if b['id'] == CUI and edge in (6, 8):
            e.box(0, -0.52, 4.85, length, 1.05, 9.70, 'cuiStone')
        if b['id'] == CUI and edge == 9:
            # Exposed exhaust riser at the east return, visible in the 2025 maintenance photograph.
            e.box(0.10, 0.30, 5.39, 0.83, 0.60, 8.75, 'cuiCanopy')
            if detail:
                for h in (2.90, 4.14, 5.40, 6.67, 7.90, 9.10):
                    e.trim(0.10, 0.61, h, 0.85, 0.05, 0.045, 'cuiSash')
        for mesh, target in ((e.structure, structure), (e.glazing, glazing)):
            place(mesh, target, (a[0] + c[0]) / 2, (a[1] + c[1]) / 2, z, angle)
    if b['id'] == CUI and b['form']['parts']:
        # On the shared partition only the taller block's upper storeys face the court.
        rear = next(part for part in b['form']['parts'] if part['id'] == 'north-block')
        ring = rear['polygons'][0][0]
        a, c = min(zip(ring, ring[1:]), key=lambda edge: (edge[0][1] + edge[1][1]) / 2)
        left, right = sorted((a[0], c[0]))
        facade = Elevation(Mesh(), Mesh(), colors, right - left, rear['height'], detail)
        upper_court(facade, left, right)
        for mesh, target in ((facade.structure, structure), (facade.glazing, glazing)):
            place(mesh, target, 0, (a[1] + c[1]) / 2, z, 0)
    return structure, glazing


def north_roof(b, z, C):
    # Orthophoto shows a long green roof west of centre, and a narrow light-covered
    # strip near the east edge. Pitches and parapet heights are estimated.
    roof = Mesh()
    for x, w, d, mat, lift in [
        (-12.5, 19.3, 44.0, 'slate', 1.12),
        (27.1, 6.9, 46, 'paleRoof', 0.52),
    ]:
        for side in (-1, 1):
            slope = [
                (x + side * w / 2, -d / 2, 0.15),
                (x, -d / 2, lift),
                (x, d / 2, lift),
                (x + side * w / 2, d / 2, 0.15),
            ]
            roof.face(slope if side < 0 else list(reversed(slope)), C[mat])
        for y in (-d / 2, d / 2):
            roof.face(
                [(x - w / 2, y, 0.15), (x + w / 2, y, 0.15), (x, y, lift)], C['stone']
            )
    a, c = b['polygons'][0][0][1:3]
    angle = math.atan2(a[1] - c[1], a[0] - c[0])
    result = Mesh()
    place(roof, result, *b['center'], z + b['height'], angle)
    return result
