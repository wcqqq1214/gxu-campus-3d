"""Visible lower flight at the journalism teaching wing's southeast entrance."""

import math

from geometry import Mesh


def east_stair_entry(entry, z, soffit, colors, detail, pane):
    mesh = Mesh()
    east, south, north = entry['east'], entry['south'], entry['north']
    west = east - entry['depth']
    trim = colors['huicuiTrim']
    stone = colors['stone']
    rail = colors['huicuiFrame']
    mesh.face(
        [
            (west, south, z + soffit),
            (west, north, z + soffit),
            (east, north, z + soffit),
            (east, south, z + soffit),
        ],
        trim,
    )

    # A transverse low set of steps fronts the glazed bay. The main flight
    # beside it rises west into the shaded recess, visible from the street.
    glass_width = 5.5
    glass_y = south + glass_width / 2
    threshold = 0.48
    front = east + 0.76
    for n in range(3):
        h = (n + 1) * threshold / 3
        mesh.box(
            front - (n + 0.5) * 0.32,
            glass_y,
            z + (h - 0.38) / 2,
            0.32,
            glass_width,
            h + 0.38,
            stone,
        )
    door_x = east - 2.35
    landing_edge = front - 3 * 0.32
    mesh.box(
        (landing_edge + door_x) / 2,
        glass_y,
        z + (threshold - 0.38) / 2,
        landing_edge - door_x,
        glass_width,
        threshold + 0.38,
        stone,
    )
    # Glazing wraps the side of the entrance, immediately south of the flight.
    pane(
        mesh,
        door_x,
        glass_y,
        (soffit + threshold) / 2,
        glass_width,
        soffit - threshold,
        angle=math.pi / 2,
        divisions=3,
    )
    if detail:
        for offset in (-0.72, 0, 0.72):
            mesh.box(
                door_x + 0.19,
                glass_y + offset,
                z + threshold + 1.14,
                0.09,
                0.05,
                2.28,
                rail,
            )
        mesh.box(door_x + 0.19, glass_y, z + threshold + 2.28, 0.09, 1.48, 0.07, rail)
    for y in (south + 0.4, south + glass_width, north - 0.45):
        mesh.cylinder(
            east - 0.50,
            y,
            z + (soffit - 0.36) / 2,
            0.43,
            soffit + 0.36,
            trim,
            16 if detail else 10,
        )

    ymid = (south + glass_width + north) / 2
    width = 3.0
    first_x = east - 0.62
    steps, tread, rise = 14, 0.30, 0.16
    for n in range(steps):
        h = (n + 1) * rise
        mesh.box(
            first_x - (n + 0.5) * tread,
            ymid,
            z + (h - 0.38) / 2,
            tread,
            width,
            h + 0.38,
            stone,
        )
    last_x = first_x - steps * tread
    walk_height = steps * rise
    mesh.box(
        (west + last_x) / 2,
        ymid,
        z + walk_height - 0.10,
        last_x - west,
        width,
        0.20,
        trim,
    )
    for y in (ymid - width / 2 + 0.10, ymid + width / 2 - 0.10):
        for n in (0, 4, 8, 13):
            x = first_x - (n + 0.5) * tread
            foot = z + (n + 1) * rise
            mesh.line((x, y, foot), (x, y, foot + 0.89), 0.038, rail, 6)
        for offset in (0.89, 0.51) if detail else (0.89,):
            mesh.line(
                (first_x - tread / 2, y, z + rise + offset),
                (last_x + tread / 2, y, z + walk_height + offset),
                0.045,
                rail,
                8,
            )
            mesh.line(
                (last_x + tread / 2, y, z + walk_height + offset),
                (west + 0.03, y, z + walk_height + offset),
                0.045,
                rail,
                8,
            )
    # In the frontal photograph a white horizontal slab and an open railing
    # cross the bay above the stair mouth. The route behind it is occluded.
    balcony_front = east - 1.55
    balcony_back = balcony_front - 1.65
    slab_level = 4.32
    bay_width = north - south - glass_width
    mesh.box(
        (balcony_front + balcony_back) / 2,
        ymid,
        z + slab_level - 0.18,
        balcony_front - balcony_back,
        bay_width,
        0.36,
        trim,
    )
    for fraction in (0.04, 0.34, 0.66, 0.96):
        y = north - bay_width * fraction
        mesh.line(
            (balcony_front - 0.07, y, z + slab_level),
            (balcony_front - 0.07, y, z + slab_level + 0.88),
            0.035,
            rail,
            6,
        )
    for h in (0.46, 0.88) if detail else (0.88,):
        mesh.line(
            (balcony_front - 0.07, north - bay_width, z + slab_level + h),
            (balcony_front - 0.07, north, z + slab_level + h),
            0.045,
            rail,
            8,
        )
    # Street views show hard paving between the two thresholds and Yanshan
    # Road. Fit the outer lip to eight samples of the existing campus road;
    # the relative rise is model registration, not a surveyed outdoor grade.
    road_samples = (
        (-1.00, 9.7, 0.403),
        (0.94, 9.7, 0.481),
        (2.89, 9.8, 0.537),
        (4.83, 9.8, 0.58),
        (6.77, 9.8, 0.617),
        (8.72, 9.8, 0.656),
        (10.66, 9.8, 0.675),
        (12.60, 9.9, 0.678),
    )
    previous = None
    for offset, span, rise_at_road in road_samples:
        y = south + offset
        row = [
            (west, y, z + 0.035),
            (east + 1, y, z + 0.035),
            (east + span + 0.12, y, z + rise_at_road - 0.018),
        ]
        if previous is not None:
            for a, b, c, d in zip(previous, previous[1:], row, row[1:]):
                mesh.face([a, b, d, c], colors['path'])
        previous = row
        if offset in (road_samples[0][0], road_samples[-1][0]):
            for a, b in zip(row, row[1:]):
                side = [(a[0], y, z - 0.12), (b[0], y, z - 0.12), b, a]
                mesh.face(side if offset < 0 else side[::-1], trim)
    return mesh
