"""Three-dimensional returns, structural bays and roof steps traced in the additional views."""

import math

from geometry import Mesh

from .facades import measured
from .forms import parts


def full_details(key, z, C, detail):
    m = Mesh()

    def box(x, y, h, w, d, thick, finish, angle=0):
        m.box(x, y, z + h, w, d, thick, C['Office ' + finish], angle)

    if key == '1501460942':
        terrace = next(
            p for p in parts('graduate-parts.json') if p['id'] == 'open-return'
        )
        # The NW end is open above the two-storey wing. Slab thickness and gallery depth
        # remain estimates. Rear masonry provides the shadow behind each landing.
        theta = math.atan2(0.696, -0.718)
        for h in (10.5, 13.8, 17.1):
            m.extrude(
                terrace['polygons'],
                terrace['triangles'],
                z + h - 0.20,
                0.20,
                C['Office ceramic'],
                C['Office ivory'],
            )
            x = 575.6 + 5.75 * (-0.718) - 3.72 * 0.696
            y = -518.72 + 5.75 * 0.696 - 3.72 * 0.718
            box(x, y, h + 0.39, 0.18, 5.70, 0.78, 'ivory', theta)
        for d in (-6.8, -11.0):
            x = 575.6 + 5.55 * (-0.718) + d * 0.696
            y = -518.72 + 5.55 * 0.696 + d * 0.718
            box(x, y, 12.25, 0.26, 0.26, 9.60, 'ceramic', theta)

        # Lower-wing window rhythm is interrupted by piers. Add the recess head
        # and jambs aligned to the front of the actual low wing, not to the tower.
        def wing(u, d):
            return (575.6 - u * 0.718 + d * 0.696, -518.72 + u * 0.696 + d * 0.718)

        for a, b in [(5.9, 13.35), (13.67, 18.48), (18.80, 22.2)]:
            for h in (0.66, 4.19):
                for elev in (h - 0.035, h + 1.50):
                    box(
                        *wing((a + b) / 2, 0.38),
                        elev,
                        b - a - 0.25,
                        0.18,
                        0.086,
                        'lintel',
                        theta,
                    )
                for u in (a + 0.16, b - 0.16):
                    box(*wing(u, 0.38), h + 0.74, 0.075, 0.17, 1.51, 'wood', theta)
    if key == '759337787':
        # Central portal is reached by a full-width flight. Thick stepped cheeks are
        # visible on both sides. The entrance glazing sits under a stacked stone lintel.
        for sign in (-1, 1):
            x = -521.05 + sign * 4.45
            for j in range(6):
                box(
                    x,
                    -605.86 + j * 0.24,
                    0.54 - j * 0.077,
                    0.33,
                    0.27,
                    0.94 - j * 0.14,
                    'stone',
                )
        for y, h, d, w, t, finish in [
            (-605.93, 3.50, 1.18, 8.42, 0.23, 'base'),
            (-605.89, 3.74, 1.27, 8.54, 0.14, 'stone'),
            (-605.94, 4.01, 1.14, 8.45, 0.24, 'pinkband'),
        ]:
            box(-521.06, y, h, w, d, t, finish)
    if key == '759147086':
        # The archival foundation photograph resolves the suspended white slab,
        # three recessed door leaves and a continuous platform with a low riser.
        box(50.95, -614.05, 2.89, 8.9, 1.93, 0.16, 'cream')
        box(50.95, -614.06, 2.78, 8.75, 1.82, 0.085, 'stone')
        for w, y, d, h in [(9.60, -614.08, 2.06, 0.24), (9.95, -613.85, 2.49, 0.115)]:
            box(50.95, y, h * 0.5, w, d, h, 'rose')
        for x in (48.18, 49.51, 52.03, 53.50):
            box(x, -614.57, 1.40, 0.17, 0.32, 2.65, 'gold')
        # The openings in the central concrete screens have rounded corners. The
        # foundation close-up resolves individual blocks. The surrounding wall stays solid.
        for layer in measured()[key]['layers']:
            if not layer.get('piercedScreen'):
                continue
            pts = layer['points']
            x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
            h0, h1 = min(p[2] for p in pts), max(p[2] for p in pts)
            cols = max(2, round((x1 - x0) / 0.24))
            rows = max(3, round((h1 - h0) / 0.24))
            if not detail:
                cols = max(2, cols // 2)
                rows = max(3, rows // 2)
            dx = (x1 - x0) / cols
            dh = (h1 - h0) / rows
            y = pts[0][1] + 0.84
            for i in range(cols):
                for j in range(rows):
                    cx = x0 + dx * (i + 0.5)
                    ch = z + h0 + dh * (j + 0.5)
                    outer = [
                        (1, 0),
                        (1, 1),
                        (0, 1),
                        (-1, 1),
                        (-1, 0),
                        (-1, -1),
                        (0, -1),
                        (1, -1),
                    ]
                    inner = [
                        (
                            0.73 * math.cos(k * math.pi / 4),
                            0.73 * math.sin(k * math.pi / 4),
                        )
                        for k in range(8)
                    ]

                    def pt(q):
                        return (cx + q[0] * dx / 2, y, ch + q[1] * dh / 2)

                    for k in range(8):
                        l = (k + 1) % 8
                        m.face(
                            [pt(outer[k]), pt(inner[k]), pt(inner[l]), pt(outer[l])],
                            C['Office cream'],
                        )
    if key == '759096563':
        # The low blue fascia fronts a projecting canopy; above-grade geometry does not
        # include the motorcycles, banner, planters or portable signage in the image.
        box(-318.24, -781.50, 3.04, 1.72, 3.32, 0.17, 'stone')
        box(-317.52, -781.50, 3.28, 0.15, 3.28, 0.47, 'teal')
        for y in (-783.07, -779.90):
            box(-318.20, y, 3.24, 1.49, 0.12, 0.35, 'cream')
        for i in range(3):
            box(
                -318.62 + i * 0.19,
                -781.50,
                0.27 - i * 0.085,
                1.15 + 0.36 * i,
                2.34 + 0.14 * i,
                0.16,
                'stone',
            )
        for y in (-790.80, -775.92):
            box(-337.72, y, 0.48, 37.42, 0.20, 0.62, 'lintel')
            box(-337.72, y, 6.55, 38.24, 0.78, 0.12, 'tile')
        # Small triangular vent within the east hip, visible in the university photograph.
        lo = [
            (-321.9, -785.40, z + 9.26),
            (-321.9, -781.42, z + 9.26),
            (-321.9, -783.41, z + 11.40),
        ]
        back = [(x - 3.05, y, h) for x, y, h in lo]
        m.face(lo, C['Office deep'])
        for i, j in [(0, 2), (2, 1)]:
            m.face([lo[i], lo[j], back[j], back[i]], C['Office tile'])
        if detail:
            for h, w in [(9.37, 3.30), (9.63, 2.72), (9.91, 2.13), (10.21, 1.58)]:
                box(-321.86, -783.41, h, 0.08, w, 0.065, 'wood')
    if key == '11564704':
        # Horizontal heads extend across each bank of six photographed floors.
        theta = math.atan2(0.196, 0.9805)

        def xy(s, d):
            return (228.18 + s * 0.9805 - d * 0.196, -251.70 + s * 0.196 + d * 0.9805)

        for a, b, top in [(0, 35.80, 21.08), (35.80, 62.8, 20.15)]:
            box(
                *xy((a + b) / 2, 0.01),
                top - 0.17,
                b - a,
                0.55,
                0.34,
                'animalWest' if a == 0 else 'animalMiddle',
                theta,
            )
            for j in range(1, 6):
                box(
                    *xy((a + b) / 2, 0.12),
                    j * top / 6,
                    b - a,
                    0.39,
                    0.15,
                    'animalCourse',
                    theta,
                )
        # Short soffit beams visible above the recessed windows on the south gallery.
        a, b = (306.1277, -248.0210), (329.3635, -243.3678)
        for h in (6.60, 9.90, 13.20, 16.50):
            for i in range(1, 6):
                x = a[0] + (b[0] - a[0]) * i / 6 - 0.196 * 0.67
                y = a[1] + (b[1] - a[1]) * i / 6 + 0.981 * 0.67
                box(x, y, h - 0.24, 0.30, 1.36, 0.16, 'ceramic', theta)
    return m
