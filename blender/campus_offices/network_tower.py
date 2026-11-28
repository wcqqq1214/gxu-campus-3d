"""Curved communications tower; its separately mapped southern podium has its own ID."""

import json
from functools import lru_cache
from pathlib import Path

from geometry import Mesh

from .masonry import Wall


# Each station resolves the opening onto its own finite brick face.
# Distances are from that face's start in campus metres; the glass is recessed 0.21 m.
# The east image resolves most upper rows. The west camera is cropped above floor five.
@lru_cache(maxsize=1)
def southeast_window_grid():
    return json.loads(Path(__file__).with_name('tower-balance.json').read_text())


def end_windows(w, edge, height):
    if edge == 6:
        grid = southeast_window_grid()
        positions = grid['axes']
        width = grid['windowWidth']
        centers = grid['centers']
    else:
        positions = (1.02, 2.41)
        width = 0.75
        centers = (
            2.42,
            6.97,
            10.28,
            13.54,
            16.97,
            19.91,
            22.85,
            25.79,
            28.73,
            31.67,
            34.61,
        )
    last = 0.02
    for i, z in enumerate(centers):
        top = (centers[i + 1] + z) / 2 if i + 1 < len(centers) else height
        half = grid['windowHeight'] / 2 if edge == 6 else (0.86 if i == 0 else 0.77)
        gaps = [
            (x - width / 2, x + width / 2, z - half, z + half, 0.21, 'shadowGlass', 1)
            for x in positions
        ]
        w.row(last, top, gaps, 'porcelain')
        last = top


def tower(b, datum, paint, detail):
    form = b['form']
    part = form['parts'][0]
    ring = part['polygons'][0][0][:-1]
    h = part['height']
    storeys = int(form['levels'])
    step = h / storeys
    walls = Mesh()
    for facade in form['facades']:
        i = facade['edge']
        w = Wall(walls, facade['start'], facade['end'], facade['normal'], datum, paint)
        L = w.length
        w.panel(0, L, -0.5, 0.02, 0, 'joint')
        # The two street stations look onto opposite ends of the convex south wall.
        # North-band geometry is independently constrained by the northwest station.
        ribbons = i in (0, 1, 2, 3, 7, 8, 9)
        spine = i in (5, 12)
        if i in (6, 10):
            end_windows(w, i, h)
        for level in range(0 if i in (6, 10) else storeys):
            bottom = 0.02 if level == 0 else step * level
            top = step * (level + 1)
            if ribbons:
                # The upper east ribbon has a masonry pier across the edge 7/8 turn.
                # Each face supplies half its estimated 0.56 m unfolded width.
                left_jamb = 0.28 if i == 8 and level >= 3 else 0.12
                right_jamb = 0.28 if i == 7 and level >= 3 else 0.12
                gaps = [
                    (
                        left_jamb,
                        L - right_jamb,
                        bottom + 0.89,
                        top - 0.79,
                        0.235,
                        'green',
                        max(2, round(L / 1.06)) if detail else max(2, round(L / 2)),
                    )
                ]
            elif spine:
                # The stair spine projects between two vertical green-glazed returns.
                # All sections share edges; neither channel is superimposed on a solid facade.
                left, right = 1.68, L - 1.48
                for l, r in [(0, left), (right, L)]:
                    w.panel(l, r, bottom, top - 0.075, 0.095, 'green')
                    w.panel(l, r, top - 0.075, top, 0.095, 'alloy')
                w.panel(left, right, bottom, top, -0.31, 'porcelain')
                for l, direction in ((left, 1), (right, -1)):
                    w.face(
                        [
                            (l, 0.095, bottom),
                            (l, -0.31, bottom),
                            (l, -0.31, top),
                            (l, 0.095, top),
                        ][::direction],
                        'reveal',
                    )
                if level == storeys - 1:
                    w.face(
                        [
                            (left, 0.095, top),
                            (right, 0.095, top),
                            (right, -0.31, top),
                            (left, -0.31, top),
                        ],
                        'porcelain',
                    )
                continue
            elif i in (4, 13):
                # Pairs sit next to the horizontal ribbon, including on the two southeast photos.
                center = L * (0.74 if i == 13 else 0.26)
                gaps = [
                    (
                        center + o - 0.34,
                        center + o + 0.34,
                        bottom + 0.84,
                        top - 0.71,
                        0.21,
                        'shadowGlass',
                        1,
                    )
                    for o in (-0.65, 0.65)
                ]
            else:
                gaps = []
            w.row(bottom, top, gaps, 'porcelain')
        if ribbons:
            # Open roof screen between piers, solid high cheeks at the two ends.
            w.box(L / 2, 0.165, h + 0.155, L, 0.33, 0.31, 'spandrel')
            w.box(L / 2, 0.17, h + 2.055, L, 0.34, 0.36, 'porcelain')
            w.box(0.16, 0.17, h + 1.095, 0.32, 0.34, 1.57, 'porcelain')
        else:
            w.panel(0, L, h, h + 2.24, 0, 'porcelain')
            w.panel(0, L, h, h + 2.24, 0.28, 'reveal')
            w.face(
                [
                    (0, 0, h + 2.24),
                    (L, 0, h + 2.24),
                    (L, 0.28, h + 2.24),
                    (0, 0.28, h + 2.24),
                ],
                'porcelain',
            )
    tris = part['triangles'][0]
    for j in range(0, len(tris), 3):
        xy = [ring[k] for k in tris[j : j + 3]]
        walls.face([(x, y, datum + h) for x, y in xy], paint['floor'])
        walls.face([(x, y, datum - 0.5) for x, y in xy[::-1]], paint['joint'])
    result = Mesh()
    result.add_part('C | 塔楼透空冠檐、凹入弧窗与端部双竖槽', walls)
    return result
