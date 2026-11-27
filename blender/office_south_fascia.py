"""West lobby fascia matched to the 2025 Guangxi University maintenance photograph."""

import math
from pathlib import Path

from geometry import Mesh
from humanities_facades import finish
from south_gate import inscription

BUILDING_ID = 'way/759132930'
GROUP = '分析测试中心西门门额'
CHINESE = '分析测试中心'
ENGLISH = 'CENTER FOR INSTRUMENTAL ANALYSIS'
FONT = Path(__file__).parent / 'fonts/GXUOfficeSouthSign.ttf'


def fascia(building, z, colors, detail):
    """Build only the front skin above the existing open four-column lobby."""
    front = next(
        f
        for f in building['form']['facades']
        if f.get('part') == 'west-low-portico' and f['edge'] == 5
    )
    entry = next(e for e in building['form']['entrances'] if e['id'] == 'west-main')
    width = math.dist(front['start'], front['end'])
    cx, cy = entry['outerCenter']
    nx, ny = front['normal']
    # On a west-facing inscription, a reader's right is approximately south.
    ux, uy = -ny, nx
    low, roof = front['minimumHeight'], front['height']
    span = roof - low
    half = width / 2
    middle = width * 0.34
    mesh = Mesh()
    charcoal = finish(colors, 'officeSouthFasciaStone', (0.084, 0.087, 0.094), 0.64)
    pale = finish(colors, 'officeSouthFasciaBand', (0.58, 0.57, 0.55), 0.72)
    grille = finish(colors, 'officeSouthFasciaGrille', (0.048, 0.049, 0.051), 0.77)

    def xyz(u, outward, up):
        return cx + ux * u + nx * outward, cy + uy * u + ny * outward, z + up

    def strip(left, right, bottom, top, d0, d1, mat):
        mesh.face(
            [
                xyz(left, d0, bottom),
                xyz(right, d0, bottom),
                xyz(right, d1, top),
                xyz(left, d1, top),
            ],
            mat,
        )

    # Heights track the approved lobby soffit / roof. The uppermost band
    # covers the existing 0.8 m parapet, which projects 0.125 m at its face.
    levels = (
        low,
        low + span * 0.17,
        low + span / 3,
        low + span * 0.82,
        roof,
        roof + 0.8,
    )
    depths = (0.058, 0.088, 0.048, 0.088, 0.143)
    for i, (a, b, d, mat) in enumerate(
        zip(levels, levels[1:], depths, (charcoal, pale, charcoal, pale, charcoal))
    ):
        inner = 0.125 if i == 4 else 0.0
        if i == 2:
            for left, right in ((-half, -middle), (middle, half)):
                strip(left, right, a, b, d, d, grille)
                if detail:
                    # Simplified pitch. Folded faces express horizontal relief
                    # without assigning a mechanical purpose to the dark fields.
                    pitch = (b - a) / 12
                    for j in range(12):
                        bottom = a + j * pitch
                        strip(
                            left,
                            right,
                            bottom + pitch * 0.28,
                            bottom + pitch * 0.70,
                            d + 0.038,
                            d + 0.007,
                            charcoal,
                        )
            strip(-middle, middle, a, b, d, d, mat)
        elif detail and i in (1, 3):
            # Vertical joints are visible in both light courses. Their count and
            # width are estimates from the unobscured right half of the photo.
            count, gap, inset = 22, 0.025, 0.012
            pitch = width / count
            left = -half
            for j in range(1, count):
                center = -half + j * pitch
                end, start = center - gap / 2, center + gap / 2
                strip(left, end, a, b, d, d, mat)
                strip(end, start, a, b, d - inset, d - inset, charcoal)
                for u, depths_at_side in (
                    (end, (d, d - inset)),
                    (start, (d - inset, d)),
                ):
                    p, q = depths_at_side
                    mesh.face(
                        [xyz(u, p, a), xyz(u, q, a), xyz(u, q, b), xyz(u, p, b)], mat
                    )
                left = start
            strip(left, half, a, b, d, d, mat)
        else:
            strip(-half, half, a, b, d, d, mat)
        for u, reverse in ((-half, False), (half, True)):
            side = [xyz(u, inner, a), xyz(u, d, a), xyz(u, d, b), xyz(u, inner, b)]
            mesh.face(side[::-1] if reverse else side, mat)
        # Close the exposed horizontal lip only; do not overlay adjacent bands.
        previous = inner if i in (0, 4) else depths[i - 1]
        strip(-half, half, a, a, previous, d, mat)
    strip(-half, half, levels[-1], levels[-1], depths[-1], 0.125, charcoal)

    if detail:
        brass = finish(
            colors, 'officeSouthFasciaLetters', (0.82, 0.59, 0.23), 0.37, 0.42
        )
        line = (levels[2] + levels[3]) / 2
        # Six widely spaced Chinese characters above one narrower-height Latin line.
        for i, char in enumerate(CHINESE):
            glyph = inscription(
                char,
                0,
                0,
                0,
                0.80,
                0.80,
                brass,
                False,
                flat=True,
                curve_resolution=3,
                font_path=FONT,
            )
            glyph.v = [
                xyz(x + (i - 2.5) * width * 0.061, 0.074 - y, line + 0.22 + h)
                for x, y, h in glyph.v
            ]
            mesh.extend(glyph)
        glyph = inscription(
            ENGLISH,
            0,
            0,
            0,
            width * 0.335,
            0.36,
            brass,
            False,
            flat=True,
            curve_resolution=3,
            font_path=FONT,
        )
        glyph.v = [xyz(x, 0.074 - y, line - 0.48 + h) for x, y, h in glyph.v]
        mesh.extend(glyph)
    return mesh
