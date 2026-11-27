"""GXU north office, way/671978896. Estimates in metres, see the two 2019 north views."""

from copy import deepcopy

from facade_bands import frame
from geometry import Mesh
from humanities_facades import finish


def north_office_model(building, datum, palette, detail, ordinary):
    b = deepcopy(building)
    colors = palette
    for name, rgb, roughness, metal in [
        ('officeWarmGrey', (0.40, 0.385, 0.365), 0.84, 0),
        ('officeCornice', (0.53, 0.49, 0.43), 0.76, 0),
        ('officeRoseStone', (0.37, 0.235, 0.18), 0.60, 0.04),
        ('officeFrame', (0.34, 0.33, 0.31), 0.49, 0.30),
        ('officeUpperGlass', (0.205, 0.24, 0.225), 0.34, 0.20),
        ('officeEntryGlass', (0.068, 0.082, 0.076), 0.26, 0.32),
    ]:
        finish(colors, name, rgb, roughness, metal)
    form = b['form']
    central, wings = form['parts']
    assert central['id'] == 'central-four' and len(wings['polygons']) == 2
    west, east = deepcopy(wings), deepcopy(wings)
    for wing, i in ((west, 0), (east, 1)):
        wing['polygons'] = [wings['polygons'][i]]
        wing['triangles'] = [wings['triangles'][i]]
        wing['wallFinish'] = 'officeWarmGrey'
    assert min(pt[0] for pt in east['polygons'][0][0]) > -236
    east.update(id='east-four', height=12.0, levels=4)
    central['wallFinish'] = 'officeWarmGrey'
    form['parts'] = [central, west, east]
    form['entrances'] = []  # Replace the generic three equal glazed bays.
    facades = form['facades']
    front = next(f for f in facades if f['edge'] == 1)
    # Recess the central structural backing; front cladding restores the surveyed
    # parapet and base plane above and below the actual inset upper glazing.
    for ring in central['polygons'][0]:
        for xy in ring:
            if abs(xy[1] - front['start'][1]) < 0.03:
                xy[1] -= 0.44
    west['parapetEdges'] = [
        (a, c)
        for poly in west['polygons']
        for ring in poly
        for a, c in zip(ring, ring[1:])
        if not (abs(a[1] + 629.06) < 0.08 and abs(c[1] + 629.06) < 0.08)
    ]
    for f in facades:
        if f['part'] == wings['id'] and min(f['start'][0], f['end'][0]) > -236:
            f.update(part='east-four', height=east['height'], levels=4)
        if f['edge'] in (0, 1, 2, 3, 5, 10, 11):
            f['rule'] = {**f['rule'], 'windows': False}
        if f['edge'] in (3, 11):
            f['rule'].pop('horizontalLedges', None)

    rear = next(f for f in facades if f['edge'] == 7 and f['part'] == 'east-four')
    rear_length = frame(rear)[0]
    # The first 4.6 m along this mapped edge are visible beyond the south
    # office. This solid also suppresses intersecting generic window frames.
    rear['rule'] = {
        **rear['rule'],
        'panels': [
            dict(
                id='visible-southeast-wall',
                type='solid',
                to=4.60 / rear_length,
                bottom=0,
                top=12.0,
                columns=1,
                rows=1,
                frameWidth=0.06,
                depth=0.012,
                finish='officeWarmGrey',
                **{'from': 0.0},
            )
        ],
    }

    # Keep the existing lettering and four upper windows, adjusting the physical openings
    # and lintel to the new photo survey. The production sign reads this same sign panel.
    by_id = {p['id']: p for p in front['rule']['panels']}
    panel = by_id['top-sign-wall']
    panel.update(bottom=8.91, top=12.48, finish='officeWarmGrey')
    panels = [panel]
    for name, x0, x1 in [
        ('top-west-1', -7.73, -6.91),
        ('top-west-2', -6.61, -5.76),
        ('top-east-1', 5.61, 6.36),
        ('top-east-2', 6.62, 7.51),
    ]:
        p = by_id[name]
        p.update(
            {
                'from': 0.5 + x0 / 17.9936355,
                'to': 0.5 + x1 / 17.9936355,
                'bottom': 9.67,
                'top': 11.87,
                'rowFractions': [0.60],
                'frameFinish': 'officeFrame',
            }
        )
        panels.append(p)
    front['rule']['panels'] = panels
    del front['rule']['horizontalLedges']
    m = ordinary(b, datum, colors, detail)
    for label, first, end in m.parts:
        if label == '办公北楼北面题字':
            for j in range(first, end):
                x, y, z = m.v[j]
                # The survey placed all three glyph centres about .35 m west of
                # their inherited positions. Preserve the source font and ordering.
                m.v[j] = (x - 0.34, y, z - 0.76)

    def placer(mesh, facade):
        length, _, _, angle, at = frame(facade)

        def box(u, width, z0, z1, back, face, mat):
            x, y = at(0.5 + u / length, (back + face) / 2)
            mesh.box(
                x,
                y,
                datum + (z0 + z1) / 2,
                width,
                face - back,
                z1 - z0,
                colors[mat],
                angle,
            )

        return length, box

    port = Mesh()
    length, box = placer(port, front)
    box(0, length, 8.40, 13.20, -0.46, 0.001, 'officeWarmGrey')
    box(0, length, 13.20, 14, -0.44, 0.125, 'officeCornice')
    box(0, length, -0.01, 5.18, -0.45, -0.085, 'officeWarmGrey')

    def glazing(u0, u1, bottom, top, mat, columns, transom, depth=0.02):
        width = u1 - u0
        mid = (u0 + u1) / 2
        box(mid, width, bottom, top, depth - 0.048, depth, mat)
        frame_width = 0.058
        for x in (u0 + frame_width / 2, u1 - frame_width / 2):
            box(x, frame_width, bottom, top, depth, depth + 0.045, 'officeFrame')
        for h in (bottom, top - frame_width):
            box(
                mid,
                width - 2 * frame_width,
                h,
                h + frame_width,
                depth,
                depth + 0.045,
                'officeFrame',
            )
        if detail:
            for col in range(1, columns):
                box(
                    u0 + width * col / columns,
                    0.047,
                    bottom,
                    top,
                    depth,
                    depth + 0.035,
                    'officeFrame',
                )
        box(
            mid,
            width - 2 * frame_width,
            transom - 0.025,
            transom + 0.025,
            depth + 0.035,
            depth + 0.060,
            'officeFrame',
        )

    # Four engaged rose-coloured pilasters. The middle span is wider. The vertical
    # ribs, square bases and slightly wider capitals are visible in both stations.
    for x in [-8.46, -3.68, 3.59, 8.34]:
        box(x, 1.16, 0.03, 1.16, -0.010, 0.31, 'officeRoseStone')
        box(x, 1.20, 1.16, 1.29, -0.010, 0.34, 'officeRoseStone')
        box(x, 0.82, 1.29, 7.65, -0.01, 0.26, 'officeRoseStone')
        if detail:
            for d in (-0.33, -0.10, 0.10, 0.33):
                box(x + d, 0.078, 1.30, 7.64, 0.25, 0.295, 'officeRoseStone')
        box(x, 1.07, 7.65, 8.43, -0.01, 0.33, 'officeRoseStone')
    # Measured visible edges of glazing in two panoramas. Extend the backing
    # glass behind the pilasters at the edges to avoid bright vertical seams.
    uppers = [(-8.16, -4.31), (-3.27, 3.13), (4.18, 7.92)]
    bays = [(-8.13, -4.28, 5), (-3.30, 3.06, 8), (4.08, 7.87, 5)]
    for i, (u0, u1, n) in enumerate(bays):
        glazing(*uppers[i], 5.33, 7.35, 'officeUpperGlass', n, 6.70, depth=-0.27)
        if i == 1:
            # Door surround replaces the middle portion; side lights remain glazed.
            glazing(u0, -2.24, 0.74, 3.81, 'officeEntryGlass', 1, 2.52)
            glazing(2.08, u1, 0.74, 3.81, 'officeEntryGlass', 1, 2.52)
            glazing(-2.24, 2.08, 2.52, 3.81, 'officeEntryGlass', 4, 2.56)
            box(-0.08, 4.32, 2.15, 2.52, 0.03, 0.21, 'officeFrame')
            for x in [-2.24 + 0.16, 2.08 - 0.16]:
                box(x, 0.32, 0.04, 2.15, 0.03, 0.21, 'officeFrame')
            glazing(-1.92, 1.76, 0.04, 2.15, 'officeEntryGlass', 3, 2.08, 0.115)
        else:
            glazing(u0, u1, 0.74, 3.81, 'officeEntryGlass', 4, 2.52)
        if i != 1:
            box((u0 + u1) / 2, u1 - u0, 0, 0.74, -0.018, 0.074, 'officeRoseStone')
    for u0, u1 in [(-3.15, -2.24), (2.08, 3.03)]:
        box((u0 + u1) / 2, u1 - u0, 0, 0.74, -0.018, 0.074, 'officeRoseStone')
    # Parallel stepped edges are visible at the parapet crown and sign band.
    for u, w, z0, z1, depth in [
        (0, length, 8.41, 8.71, 0.32),
        (0, length + 0.18, 8.71, 8.88, 0.44),
        (-0.09, 11.75, 8.84, 9.02, 0.50),
        (0, length + 0.12, 12.42, 12.60, 0.32),
        (0, length + 0.20, 12.60, 12.73, 0.40),
        (0, length, 13.75, 13.89, 0.20),
        (0, length + 0.14, 13.89, 14, 0.26),
    ]:
        box(u, w, z0, z1, -0.10, depth, 'officeCornice')
    m.add_part('北门厅柱列、窗带及叠檐', port)

    elevations = Mesh()
    for f in facades:
        edge = f['edge']
        if edge not in (0, 2, 3, 5, 10, 11):
            continue
        length, wall = placer(elevations, f)
        if edge in (0, 2):
            # The stepped foyer returns in the booklet and NE view show three
            # narrow barred ground openings, clear first-floor panes and upper lights.
            positions = [(0.12 + i * 0.19) * length for i in range(3)]
            # edge 0 ends at the north face, edge 2 begins there.
            centers = [
                length / 2 - p if edge == 0 else p - length / 2 for p in positions
            ]
            for u in centers:
                for bottom, top in [(0.80, 3.83), (5.30, 7.17), (9.73, 11.84)]:
                    wall(u, 1.02, bottom, top, 0.015, 0.115, 'officeUpperGlass')
                    if detail:
                        wall(u, 0.055, bottom, top, 0.115, 0.145, 'officeFrame')
                        wall(
                            u, 1.02, top - 0.51, top - 0.46, 0.115, 0.15, 'officeFrame'
                        )
                        if bottom < 1:
                            for off in [-0.32, -0.16, 0.16, 0.32]:
                                wall(
                                    u + off,
                                    0.035,
                                    bottom,
                                    top - 0.49,
                                    0.115,
                                    0.15,
                                    'officeFrame',
                                )
            wall(0, length, 8.48, 8.77, -0.01, 0.25, 'officeCornice')
            wall(0, length, 12.48, 12.73, -0.01, 0.25, 'officeCornice')
            continue
        if edge == 10:  # West end shows four individually spaced window axes.
            cols, rows = 4, 3
        elif edge == 11:
            cols, rows = 8, 3
        elif edge == 5:
            cols, rows = 4, 4
        else:
            cols, rows = 8, 4
        floor = (12.0 if rows == 4 else 9.9) / rows
        for r in range(rows):
            base = r * floor
            wall(
                0,
                length,
                base + 2.43,
                base + floor + 0.055,
                -0.01,
                0.052,
                'officeCornice',
            )
            for j in range(cols):
                u = ((j + 0.5) / cols - 0.5) * length
                width = 1.2 if edge in (5, 10) else min(2.14, length / cols * 0.7)
                wall(
                    u, width, base + 0.86, base + 2.43, 0.012, 0.095, 'officeUpperGlass'
                )
                if detail:
                    wall(u, 0.07, base + 0.86, base + 2.43, 0.095, 0.13, 'officeFrame')
                    wall(
                        u, width, base + 2.01, base + 2.065, 0.095, 0.13, 'officeFrame'
                    )
        if edge == 11:
            # The survey's west roof steps upward over its last five metres.
            cap = 5.05
            wall(-length / 2 + cap / 2, cap, 9.90, 10.70, -0.12, 0.13, 'officeCornice')
            wall(cap / 2, length - cap, 9.90, 10.17, -0.12, 0.13, 'officeCornice')
            wall(cap / 2, length - cap, 10.04, 10.17, -0.02, 0.22, 'officeCornice')
        else:
            wall(
                0,
                length,
                rows * floor + 0.62,
                rows * floor + 0.80,
                -0.015,
                0.22,
                'officeCornice',
            )
    south_return = Mesh()
    L, wall = placer(south_return, rear)
    # Survey the two upper rows, then repeat their measured storey pitch.
    # The two lower rows are held out from the geometry fit.
    for level in range(4):
        sill = 9.94 - (3 - level) * 3.04
        head = 11.45 - (3 - level) * 3.06
        for distance in (1.64, 3.09):
            u = distance - L / 2
            width = 0.91
            wall(u, width, sill, head, 0.028, 0.073, 'officeUpperGlass')
            for dx in (-width / 2 + 0.025, width / 2 - 0.025):
                wall(u + dx, 0.05, sill, head, 0.073, 0.112, 'officeFrame')
            wall(u, width, sill, sill + 0.055, 0.073, 0.114, 'officeFrame')
            wall(u, width, head - 0.055, head, 0.073, 0.114, 'officeFrame')
            wall(u, width, head - 0.48, head - 0.425, 0.073, 0.114, 'officeFrame')
            if detail:
                wall(u, 0.052, sill + 0.055, head - 0.48, 0.074, 0.114, 'officeFrame')
    end_face = next(f for f in facades if f['edge'] == 6)
    for facade, span in ((rear, 4.60), (end_face, frame(end_face)[0])):
        length, ribbon = placer(south_return, facade)
        u = (span - length) / 2
        for level in range(3):
            h = 2.47 + 3.05 * level
            ribbon(u, span, h, h + 1.12, -0.01, 0.048, 'officeCornice')
        ribbon(u, span, 0.03, 0.60, -0.01, 0.06, 'officeRoseStone')
        ribbon(u, span, 11.89, 12.08, -0.02, 0.47, 'officeCornice')
    m.add_part('东翼南面两列窗与转角腰线', south_return)
    m.add_part('北侧两翼窗列与门厅侧窗', elevations)
    return m
