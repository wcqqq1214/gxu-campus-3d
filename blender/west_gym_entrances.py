"""South entrance of way/699156920, in the stadium shell's world axes (metres)."""

from geometry import MATERIALS


def _profile(m, left, right, outline, material):
    """Extrude a counterclockwise YZ section in +X."""
    west = [(left, y, z) for y, z in outline]
    east = [(right, y, z) for y, z in outline]
    m.face(west[::-1], material)
    m.face(east, material)
    for i, p in enumerate(west):
        j = (i + 1) % len(west)
        m.face([p, west[j], east[j], east[i]], material)


def _forecourt(m, x, z, C):
    # The asphalt/curb mesh sits about 0.41 m above terrain. The south
    # seam follows the exported curb on its uninterrupted western section.
    # Rectangular forecourt with beds along the street and a short paved neck.
    # Split the wide rows at the neck endpoints so the curb return has no T seam.
    offsets = (-27, -12, 4, 27)
    rows = [
        [(x + u, -431, z - 0.39 + 0.0059 * (u + 12)) for u in offsets],
        [(x + u, -418, z - 0.10) for u in offsets],
        [(x + u, -412, z + 0.06) for u in offsets],
        [(x + u, -394, z + 0.06) for u in offsets],
    ]
    curb = [(x - 12, -438.332, z - 0.516), (x + 4, -437.852, z - 0.422)]
    sections = [(curb, rows[0][1:3])]
    sections.extend(zip(rows, rows[1:]))
    for a, b in sections:
        for i in range(len(a) - 1):
            m.face([a[i], a[i + 1], b[i + 1]], C['path'])
            m.face([a[i], b[i + 1], b[i]], C['path'])
    border = (
        [row[0] for row in rows[::-1]]
        + [rows[0][1]]
        + curb
        + [rows[0][2]]
        + [row[-1] for row in rows]
        + rows[-1][-2:0:-1]
    )
    for a, b in zip(border, border[1:] + border[:1]):
        m.face([(a[0], a[1], z - 1.15), (b[0], b[1], z - 1.15), b, a], C['stone'])
    for left, right in ((-26, -12.5), (4.5, 26)):
        cx, width = x + (left + right) / 2, right - left
        m.box(cx, -429.3, z - 0.16, width, 2.1, 0.70, C['paleRoof'])
        m.box(cx, -429.3, z + 0.25, width - 0.46, 1.63, 0.22, C['green'])


def add_entrances(m, l, b, z, C, detail):
    """Append both LODs' approach, raised gallery, doors and planted stair cheeks."""
    x = l['center'][0]
    wall, landing, toe = -394.0, -400.8, -411.3
    top, base = z + 4.26, z + 0.06
    stone = C['stone']
    # Give the steps their own Draco primitive. Sharing the roof primitive
    # would quantize millimetre-scale stair edges over the entire building.
    if 'gymTread' not in C:
        finish = MATERIALS[C['paleRoof']].copy()
        finish.name = 'gymTread'
        C['gymTread'] = len(MATERIALS)
        MATERIALS.append(finish)
    tread = C['gymTread']
    _forecourt(m, x, z, C)

    # Elevated gallery also shelters the ground level. Columns continue into soil.
    m.box(
        x,
        (wall + 0.10 + landing) / 2,
        top - 0.30,
        54,
        wall + 0.10 - landing,
        0.60,
        stone,
    )
    for offset in (-24, -16, -8, 0, 8, 16, 24):
        m.box(
            x + offset,
            landing + 1,
            (z - 0.55 + top - 0.6) / 2,
            0.70,
            0.85,
            top - 0.6 - (z - 0.55),
            stone,
        )
    for sign in (-1, 1):
        m.box(x + sign * 20.75, landing + 0.14, top + 0.44, 12.5, 0.28, 0.88, stone)
        m.box(
            x + sign * 26.86,
            (wall + landing) / 2,
            top + 0.44,
            0.28,
            wall - landing,
            0.88,
            stone,
        )

    # Both LODs use the same walking surface at every tread.
    count = 28
    # Seat the last tread just inside the gallery. Separately quantized
    # material edges can otherwise open a slit at their butt joint.
    profile = [
        (toe, base - 0.22),
        (landing + 0.012, base - 0.22),
        (landing + 0.012, top - 0.002),
        (landing, top),
    ]
    for i in range(count, 0, -1):
        y = toe + (landing - toe) * (i - 1) / count
        # A 30 mm batter on each 150 mm riser gives both Draco grids a
        # continuous surface at nosings, including the approach to the first.
        profile.append((y + 0.03, base + (top - base) * i / count))
        profile.append((y, base + (top - base) * (i - 1) / count))
    _profile(m, x - 14.5, x + 14.5, profile, tread)

    # Splayed-in-perspective in the street photograph, parallel in the aerial.
    for offset in (-14.15, -4.72, 4.72, 14.15):
        side = [
            (toe, base),
            (landing, top - 0.03),
            (landing, top + 0.80),
            (toe, base + 0.80),
        ]
        _profile(m, x + offset - 0.54, x + offset + 0.54, side, stone)
        planted = [
            (toe + 0.2, base + 0.87),
            (landing - 0.2, top + 0.71),
            (landing - 0.2, top + 0.96),
            (toe + 0.2, base + 1.02),
        ]
        _profile(m, x + offset - 0.40, x + offset + 0.40, planted, C['green'])

    # Upper doors overlay the shell's reserved lower wall. The main roof provides cover.
    for offset in (-9, -3, 3, 9):
        cx = x + offset
        m.box(cx, wall - 0.08, top + 1.55, 5.4, 0.22, 3.10, C['dark'])
        m.box(cx, wall - 0.20, top + 1.49, 5.14, 0.07, 2.88, C['glass'])
        if detail:
            for u in (-1.30, 0, 1.30):
                m.box(cx + u, wall - 0.25, top + 1.49, 0.075, 0.065, 2.88, C['metal'])
            m.box(cx, wall - 0.25, top + 2.33, 5.14, 0.065, 0.08, C['metal'])
