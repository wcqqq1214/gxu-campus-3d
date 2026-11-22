"""West frontage seen at 00:00–00:11 of BV1bC411L7SJ (April 2024)."""

import math

from geometry import Mesh
from south_gate import inscription


def shopfront(a, p, C, detail, windows, signs, window):
    # Along the street the red sign, dark sign and two noodle-shop signs
    # run from south to north. Bay widths and distances to the curb are estimates.
    length = math.dist(a, p)
    tx, ty = (p[0] - a[0]) / length, (p[1] - a[1]) / length
    angle = math.atan2(ty, tx)
    entry = Mesh()

    def box(mesh, station, offset, z, w, d, h, material):
        mesh.box(
            a[0] + station * tx - offset * ty,
            a[1] + station * ty + offset * tx,
            z,
            w,
            d,
            h,
            C[material],
            angle,
        )

    # The canopy and stair tread run across the shops, including the tile-clad piers.
    pitch = 5.40
    first = 6.8
    total = pitch * 5
    mid = first + 2 * pitch
    box(entry, mid, 0.76, 3.47, total + 0.48, 1.60, 0.26, 'white')
    box(entry, mid, 0.80, -0.08, total + 0.5, 1.65, 0.78, 'stone')
    box(entry, mid, 1.82, -0.16, total + 0.5, 0.40, 0.62, 'stone')
    for i in range(5):
        station = first + i * pitch
        window(a, p, station, 0.34, 4.80, 2.31, columns=4, transoms=())
        color = ('white', 'gateRed', 'fenceIron', 'dark', 'dark')[i]
        if i:
            box(entry, station, 0.31, 2.98, pitch - 0.08, 0.64, 0.72, color)
        # Bright tile piers with a dark stone skirting at sidewalk level.
        pier = station - pitch / 2
        box(entry, pier, 0.11, 1.64, 0.48, 0.28, 2.65, 'wallStone')
        box(entry, pier, 0.15, 0.59, 0.48, 0.27, 0.55, 'dark')
        if detail:
            for du in (-0.14, 0.14):
                box(windows, station + du, 0.16, 1.35, 0.045, 0.05, 0.54, 'metal')
        # Red brick spandrels inside a white structural frame. The shop
        # video shows these above the soffit, behind exterior AC units.
        for level in (1, 2):
            bottom = 3.60 + (level - 1) * 3.1
            box(entry, station, 0.055, bottom + 0.42, pitch - 0.24, 0.12, 0.84, 'red')
            box(entry, station, 0.055, bottom + 2.88, pitch - 0.24, 0.12, 0.44, 'red')
            box(entry, pier, 0.12, bottom + 1.55, 0.26, 0.26, 3.10, 'white')
            box(entry, station, 0.16, bottom + 3.06, pitch, 0.32, 0.16, 'white')
            window(
                a,
                p,
                station,
                bottom + 0.84,
                pitch - 0.64,
                1.81,
                columns=5,
                transoms=(0.75,),
            )
        if detail and i in (1, 3):
            box(windows, pier + 0.7, 0.35, 3.98, 0.72, 0.39, 0.55, 'white')
            for slat in range(6):
                box(
                    windows,
                    pier + 0.7,
                    0.56,
                    3.79 + slat * 0.067,
                    0.55,
                    0.025,
                    0.026,
                    'metal',
                )
        if detail and i in (1, 3, 4):
            title = '蜜雪冰城' if i == 1 else '三品王牛肉粉'
            letters = inscription(
                title,
                0,
                -0.68,
                2.98,
                3.88,
                0.44,
                C['timeLetter' if i >= 3 else 'white'],
                False,
            )
            for k, (u, v, z) in enumerate(letters.v):
                # Glyphs face local -Y; the tangent must run north to south.
                letters.v[k] = (
                    a[0] + (station - u) * tx + v * ty,
                    a[1] + (station - u) * ty - v * tx,
                    z,
                )
            signs.extend(letters)
    return entry
