"""南苑第二餐厅, modelled from the signed street view, rooftop photo and oblique aerials."""

import hashlib
import json
import math
from pathlib import Path

from mathutils import Vector
from mathutils.geometry import tessellate_polygon

from geometry import Mesh, material
from nanyuan_shopfront import shopfront
from south_gate import inscription

CANTEEN_ID = 'way/948683821'


def north_stair(mesh, C):
    """Flight seen rising westwards behind the middle ground-floor opening."""
    start, run, rise = 6.12, 5.72, 3.31
    count, depth, clear_width = 20, 2.05, 1.70
    going, riser = run / count, rise / count
    for n in range(count):
        mesh.box(
            start + (n + 0.5) * going,
            depth,
            (n + 1) * riser - 0.12,
            going,
            clear_width,
            0.24,
            C['stone'],
        )

    def incline(v, lift, breadth, thickness, material):
        beam = Mesh()
        length = math.hypot(run, rise)
        beam.box(0, 0, 0, length, breadth, thickness, material)
        a, b = run / length, rise / length
        beam.v = [
            (start + run / 2 + a * u - b * h, v + y, rise / 2 + lift + b * u + a * h)
            for u, y, h in beam.v
        ]
        mesh.extend(beam)

    for v in (depth - clear_width / 2 + 0.055, depth + clear_width / 2 - 0.055):
        incline(v, -0.12, 0.15, 0.24, C['stone'])
        incline(v, 0.94, 0.055, 0.065, C['metal'])
        for n in range(0, count + 1, 4):
            mesh.box(
                start + n * going, v, n * riser + 0.48, 0.045, 0.045, 0.94, C['metal']
            )
    # The second-floor slab forms the landing at the top of the flight.


def nanyuan(b, z, C, detail):
    # Work from the mapped NE corner, looking south: west is right on the signed wall.
    ring = b['polygons'][0][0]
    footprint = json.dumps(b['polygons'], separators=(',', ':')).encode()
    if hashlib.sha256(footprint).hexdigest() != (
        '75b16a7d582236e2ab17eca84e2bdc9c5a9a7a97b61532f4d25b5d08980d034b'
    ):
        raise ValueError('Recheck the north elevation against the mapped footprint')
    x, y = ring[5]
    angle = math.atan2(ring[4][1] - y, ring[4][0] - x)
    co, si = math.cos(angle), math.sin(angle)
    outline = [
        ((px - x) * co + (py - y) * si, (py - y) * co - (px - x) * si)
        for px, py in ring[:-1]
    ]
    height = b['height']
    width = outline[4][0]
    south = outline[16][1]
    east = outline[7][0]
    main = [*outline[:8], (east, south), outline[16]]
    wing = [*outline[7:16], (east, south)]
    body, roof, arcade, windows, sign = (Mesh() for _ in range(5))
    if 'nanyuanGlass' not in C:
        C['nanyuanGlass'] = material('nanyuanGlass', (0.055, 0.19, 0.31), 0.18, 0.46)
    if 'nanyuanSpandrel' not in C:
        C['nanyuanSpandrel'] = material('nanyuanSpandrel', (0.19, 0.21, 0.23), 0.76)
    wall, trim, glass, frame = (
        C[k] for k in ('white', 'stone', 'nanyuanGlass', 'dark')
    )

    def slab(mesh, points, h, material):
        coords = [Vector((u, v, h)) for u, v in points]
        for ids in tessellate_polygon([coords]):
            a, p, q = (coords[i] for i in ids)
            if (p - a).cross(q - a).z < 0:
                p, q = q, p
            mesh.face([tuple(a), tuple(p), tuple(q)], material)

    def wall_face(a, p, bottom, top, material=wall):
        body.face([(*a, top), (*p, top), (*p, bottom), (*a, bottom)], material)

    def window(a, p, u, sill, w, h, *, columns=2, transoms=(0.67,), flush=False):
        length = math.dist(a, p)
        tx, ty = (p[0] - a[0]) / length, (p[1] - a[1]) / length
        theta = math.atan2(ty, tx)

        def panel(offset, lift, span, tall, out, mat):
            if not detail:
                # At campus scale only the exposed front surface of each pane is visible.
                face_out = out + (0.006 if flush else 0.025)
                windows.face(
                    [
                        (
                            a[0] + (u + offset + du) * tx - face_out * ty,
                            a[1] + (u + offset + du) * ty + face_out * tx,
                            sill + lift + dz,
                        )
                        for du, dz in (
                            (span / 2, -tall / 2),
                            (-span / 2, -tall / 2),
                            (-span / 2, tall / 2),
                            (span / 2, tall / 2),
                        )
                    ],
                    mat,
                )
                return
            windows.box(
                a[0] + (u + offset) * tx - out * ty,
                a[1] + (u + offset) * ty + out * tx,
                sill + lift,
                span,
                0.012 if flush else 0.05,
                tall,
                mat,
                theta,
            )

        panel(0, h / 2, w + 0.10, h + 0.10, 0.106 if flush else 0.04, frame)
        panel(0, h / 2, w, h, 0.120 if flush else 0.10, glass)
        if detail:
            for i in range(1, columns):
                panel(
                    w * (i / columns - 0.5),
                    h / 2,
                    0.055,
                    h,
                    0.135 if flush else 0.15,
                    frame,
                )
            for t in transoms:
                panel(0, t * h, w, 0.055, 0.135 if flush else 0.15, frame)

    # Leave the north end open for the arcades. On the east return the mapped
    # wall slopes away from the corner. Follow that slope with each gallery floor.
    recess_w, recess_d = 4.0, 4.8
    east_return = (0, recess_d)
    east_step, east_join, east_end = 10.0, 16.6, 30.3
    terrace_z, upper_x = 17.30, 4.00
    # The ground outline flares east. Above it the north-east gallery has a
    # straight return, then two narrow upper windows before the roof steps back.
    upper_main = [
        *main[:6],
        (0, east_step),
        (upper_x, east_step),
        (upper_x, east_end),
        (east, east_end),
        *main[7:],
    ]
    for i, a in enumerate(main):
        if i not in (4, 5, 6):
            wall_face(a, main[(i + 1) % len(main)], -0.60, height)
    wall_face(outline[5], outline[6], -0.60, 3.15)
    wall_face(outline[6], (east, east_join), -0.60, 3.15)
    slab(roof, [outline[5], outline[6], (east, east_join), (0, east_join)], 3.15, wall)
    wall_face(east_return, (0, east_step), 3.15, height)
    wall_face((0, east_step), (0, east_join), 3.15, terrace_z)
    wall_face((0, east_join), (east, east_join), 3.15, terrace_z)
    wall_face((east, east_join), outline[7], -0.60, terrace_z)
    wall_face((0, east_step), (upper_x, east_step), terrace_z, height)
    wall_face((upper_x, east_step), (upper_x, east_end), terrace_z, height)
    wall_face((upper_x, east_end), (east, east_end), terrace_z, height)
    wall_face((east, east_end), outline[7], terrace_z, height)
    slab(
        roof,
        [
            (0, east_step),
            (0, east_join),
            (east, east_join),
            (east, east_end),
            (upper_x, east_end),
            (upper_x, east_step),
        ],
        terrace_z,
        C['paleRoof'],
    )
    # South extension is visible behind the main hall in oblique views.
    wing_height = height * 0.79
    for a, end in zip(wing, wing[1:]):
        wall_face(a, end, -0.60, wing_height)
    slab(roof, wing, wing_height, C['paleRoof'])
    slab(roof, upper_main, height, C['paleRoof'])

    # The photo shows three open passages at pavement level. They share a
    # sheltered rear wall. The open upper bays sit over the eastern passage.
    wall_face((recess_w, recess_d), (recess_w, 0), 3.15, height)
    wall_face(east_return, (recess_w, recess_d), 3.15, height, C['gateRecess'])
    wall_face((width, recess_d), east_return, -0.60, 3.15, C['gateRecess'])
    for left, right in [(0, 0.48), (6.12, 6.5), (11.64, 12.15), (width - 0.48, width)]:
        body.box((left + right) / 2, 0.22, 1.275, right - left, 0.44, 3.75, wall)
    body.box((width + 12.15) / 2, 0.16, 2.68, width - 12.15, 0.32, 0.94, wall)
    wall_face((width, 0), (recess_w, 0), 3.15, height)
    # Elevations of sill and soffit were read separately on each storey.
    galleries = [
        (4.76, 7.03),
        (8.89, 11.27),
        (13.31, 16.09),
        (18.00, 19.8),
        (21.64, 23.48),
    ]
    plate = [(0, 0), (recess_w, 0), (recess_w, recess_d), east_return]
    bottom = 3.15
    for sill, soffit in galleries:
        slab(arcade, plate, bottom, wall)
        slab(arcade, plate, bottom + 0.16, trim)
        arcade.box(
            recess_w / 2, 0.12, (bottom + sill) / 2, recess_w, 0.24, sill - bottom, wall
        )
        wall_face((0, 0), east_return, bottom, sill)
        arcade.box(0.29, 0.22, (sill + soffit) / 2, 0.58, 0.44, soffit - sill, wall)
        bottom = soffit
    slab(arcade, plate, bottom, wall)
    arcade.box(
        recess_w / 2, 0.12, (height + bottom) / 2, recess_w, 0.24, height - bottom, wall
    )
    wall_face((0, 0), east_return, bottom, height)
    # Leave the stairwell open at the second-floor landing.
    for u0, u1, v0, v1 in [
        (recess_w, 6.1, 0, recess_d),
        (11.84, width, 0, recess_d),
        (6.1, 11.84, 0, 1.12),
        (6.1, 11.84, 2.98, recess_d),
    ]:
        arcade.box((u0 + u1) / 2, (v0 + v1) / 2, 3.23, u1 - u0, v1 - v0, 0.16, wall)
    # Recessed doors are visible below the sign. Keep the pavement passages open.
    back = ((width, recess_d), east_return)
    for station, span in [(2.2, 2.55), (6.8, 3.9), (12.0, 3.2)]:
        window(*back, station, 0.12, span, 2.57, columns=4)
    # The lower two gallery interiors show a door/window in the shadow of the slab.
    for sill, soffit in galleries[:2]:
        window(
            (recess_w, recess_d),
            east_return,
            2.6,
            sill - 0.35,
            3.5,
            soffit - sill + 0.12,
            columns=3,
            transoms=(),
        )
    strip_end = 6.36
    windows.box(
        (recess_w + strip_end) / 2,
        -0.025,
        (height + 3.15) / 2,
        strip_end - recess_w,
        0.05,
        height - 3.15,
        C['paleRoof'],
    )
    north_wall = ((width, 0), (0, 0))
    for i, (sill, soffit) in enumerate(galleries):
        window(
            *north_wall,
            width - (strip_end + recess_w) / 2,
            sill,
            strip_end - recess_w - 0.10,
            soffit - sill,
            transoms=(0.24, 0.68) if i == 2 else (0.46,),
        )
    if detail:
        for h in (3.5, 7.6, 12.0, 16.8, 20.45, 24.4):
            windows.box(
                (width + strip_end) / 2, -0.02, h, width - strip_end, 0.025, 0.021, trim
            )

    # A stepped blank screen carries the six characters, independently of the roof plant.
    roof.box((6.44 + width) / 2, 0.16, height + 1.15, width - 6.44, 0.32, 2.30, wall)
    roof.box(width - 0.16, 0.98, height + 1.15, 0.32, 1.96, 2.30, wall)
    for v in (0.55, 0.90, 1.25):
        roof.box(6.52, v, height + 0.96, 0.13, 0.15, 1.92, wall)
    for i, glyph in enumerate(b['name']):
        letter = inscription(
            glyph,
            13.33,
            -0.10,
            height - 0.14 - i * 1.81,
            1.28,
            1.10,
            C['timeLetter'],
            False,
            flat=not detail,
            curve_resolution=3 if detail else 1,
            font_path=Path(__file__).resolve().parents[1] / 'app/fonts/gxu-serif.woff2',
        )
        sign.extend(letter)

    # Two longitudinal roof strips with repeated transverse dark panels on the east.
    roof.box(10.45, south / 2, height + 0.34, 7.9, south - 0.7, 0.68, C['paleRoof'])
    for row in range(15):
        v = 1.95 + row * 2.44
        left = upper_x + 0.15 if east_step - 0.90 < v < east_end + 0.90 else 0.15
        roof.box(
            (left + 6.19) / 2, v, height + 0.16, 6.19 - left, 1.79, 0.32, C['fenceIron']
        )
    for u in (6.50, 14.40):
        roof.box(u, south / 2, height + 0.84, 0.20, south - 0.7, 0.32, wall)
    # Small cylindrical roof fitting seen immediately above the signed north screen.
    roof.cylinder(8.95, 2.25, height + 2.12, 1.12, 2.88, C['metal'], n=20)
    roof.cylinder(8.95, 2.25, height + 3.56, 1.16, 0.12, C['paleRoof'], n=20)
    for h in (1.42, 2.36, 3.27):
        roof.cylinder(8.95, 2.25, height + h, 1.15, 0.06, C['metal'], n=20)
    for a, end in zip(upper_main, upper_main[1:] + upper_main[:1]):
        roof.box(
            (a[0] + end[0]) / 2,
            (a[1] + end[1]) / 2,
            height + 0.18,
            math.dist(a, end),
            0.19,
            0.36,
            wall,
            math.atan2(end[1] - a[1], end[0] - a[0]),
        )
    # The rear block projects at the eastern end of the south extension.
    # Its western jamb and the dark rooftop strip are distinct in the drone frame.
    # The rooftop photo shows two uninterrupted spandrel strips separated
    # by three small window stacks. The easternmost blank pier rises above them.
    rear_y = 42.35
    block = [
        (-15.90, rear_y),
        (-15.91, 44.34),
        outline[14],
        outline[15],
        (east, south),
        (east, rear_y),
    ]
    shoulder = 24.55
    for a, end in zip(block, block[1:] + block[:1]):
        wall_face(a, end, wing_height, shoulder)
    slab(roof, block, shoulder, C['paleRoof'])
    crown = [*block[:4], (-6.5, south), (-6.5, rear_y)]
    plant_top = height + 1.90
    for a, end in zip(crown, crown[1:] + crown[:1]):
        wall_face(a, end, shoulder, plant_top)
    slab(roof, crown, plant_top, C['paleRoof'])
    for a, end in zip(crown, crown[1:] + crown[:1]):
        roof.box(
            (a[0] + end[0]) / 2,
            (a[1] + end[1]) / 2,
            plant_top - 0.08,
            math.dist(a, end),
            0.14,
            0.16,
            wall,
            math.atan2(end[1] - a[1], end[0] - a[0]),
        )
    window((-6.5, south), (-6.5, rear_y), 3.16, shoulder + 0.65, 2.4, 1.3)

    entry = shopfront(*outline[1:3], C, detail, windows, sign, window)
    north_stair(entry, C)
    # Long west face: continuous upper rows between full-height end bays.
    west = (outline[1], outline[2])
    for v in (7.7, 14.4, 21.1, 27.8, 34.5, 39.15):
        body.box(15.12, v, 7.85, 0.68, 0.46, 15.7, wall)
    for h in (4.10, 8.45, 12.91, 17.1, 20.6, 24.55):
        body.box(15.10, 22.58, h, 0.66, 35.0, 0.32, wall)
    for sill, top in galleries[2:]:
        for n in range(10):
            window(
                *west,
                (n + 0.5) * math.dist(*west) / 10,
                sill,
                2.99,
                top - sill,
                columns=3,
            )
    # Between the old shop headers and the next continuous row.
    for n in range(6):
        window(*west, (n + 0.5) * math.dist(*west) / 6, 10.2, 4.8, 1.7, columns=4)
    for a, end in [(outline[3], outline[4]), (outline[16], outline[0])]:
        length = math.dist(a, end)
        for sill, top in galleries:
            window(a, end, length / 2, sill, length - 0.92, top - sill, columns=3)

    # Two small upper lights sit over each larger dining-room bay on the east return.
    east_wall = ((0, 0), (0, east_join))
    # Casement edges measured in the rectified street view. The two small lights
    # share a module; the dining-room windows below are wider and have transoms.
    for station, sill, span, opening in [
        (6.28, 21.71, 0.99, 1.36),
        (8.68, 21.64, 0.95, 1.33),
        (6.32, 18.09, 1.01, 1.36),
        (8.73, 18.06, 0.94, 1.32),
    ]:
        window(*east_wall, station, sill, span, opening, transoms=(), flush=True)
    for sill, opening in [(4.48, 2.21), (8.40, 2.79), (12.98, 2.73)]:
        for v, span in ((7.86, 3.42), (13.10, 2.73)):
            window(
                *east_wall,
                v,
                sill,
                span,
                opening,
                columns=3,
                transoms=(0.76,),
                flush=True,
            )
    if detail:
        windows.cylinder(-0.10, 4.97, 14.25, 0.080, 21.2, trim, n=8)
        for z_clip in (6.6, 11.0, 15.4, 19.2, 23.2):
            windows.box(-0.10, 4.97, z_clip, 0.20, 0.19, 0.055, trim)
        arcade.box(2.05, 1.9, 16.05, 0.94, 0.69, 0.065, frame)
        # The street photo shows a top-hung light tilted out of the wide bay.
        # Rotating the pane gives it its own reflection with the same glass.
        sash = Mesh()
        sash.box(0, 0, -0.30, 0.05, 1.04, 0.60, frame)
        sash.box(-0.032, 0, -0.30, 0.025, 0.96, 0.52, glass)
        tilt = math.radians(18)
        sash.v = [
            (
                -0.16 + u * math.cos(tilt) + h * math.sin(tilt),
                7.90 + v,
                galleries[2][1] - 0.25 - u * math.sin(tilt) + h * math.cos(tilt),
            )
            for u, v, h in sash.v
        ]
        windows.extend(sash)
    for i, (sill, top) in enumerate(galleries):
        segments = (
            [
                ((upper_x, east_step), (upper_x, east_end)),
                ((east, east_end), outline[7]),
            ]
            if i >= 3
            else [((east, east_join), outline[7])]
        )
        for a, end in segments:
            length = math.dist(a, end)
            bays = round(length / 4)
            for n in range(bays):
                window(
                    a,
                    end,
                    (n + 0.5) * length / bays,
                    sill,
                    length / bays * (0.53 if i >= 3 else 0.78),
                    top - sill,
                )
    # Front of the south extension is coplanar with the main south wall.
    # Draw the five stacks on one datum so they continue across the footprint seam.
    south_wall = (outline[15], outline[16])
    for centre, span in [(6.08, 2.98), (-8.10, 3.14)]:
        windows.box(
            centre, south + 0.032, 13.15, span + 0.17, 0.06, 19.9, C['nanyuanSpandrel']
        )
    # The camera sees the right stack just below the centre lights. Keep the
    # rows level within each stack and carry the spandrels through the floor slabs.
    for centre, span, upper_rows in [
        (-8.1, 3.13, [(11.68, 2.22), (15.54, 2.30), (19.32, 2.55)]),
        (-3.63, 1.63, [(11.81, 1.89), (15.72, 2.02), (19.64, 2.11)]),
        (-0.78, 1.50, [(11.86, 1.90), (15.72, 1.97), (19.64, 2.04)]),
        (2.39, 1.45, [(11.92, 1.86), (15.72, 1.86), (19.64, 1.95)]),
        (6.08, 2.96, [(11.66, 2.19), (15.66, 2.07), (19.55, 2.03)]),
    ]:
        inset = 0.17 if span < 2 else 0
        rows = [
            (3.4 + inset, 2.66 - 2 * inset),
            (7.5 + inset, 2.66 - 2 * inset),
            *upper_rows,
        ]
        for sill, opening in rows:
            window(
                *south_wall,
                centre - outline[15][0],
                sill,
                span,
                opening,
                columns=2,
                transoms=(0.66,),
            )
    for centre, span in [(13.65, 2.35), (10.55, 2.64), (6.85, 3.1), (3.1, 3.48)]:
        window(
            *south_wall,
            centre - outline[15][0],
            24.3,
            span,
            0.85,
            columns=1,
            transoms=(),
        )
    # Narrow vertical slots on the east-facing return of the raised south pier.
    for sill in (4.6, 8.6, 12.6, 16.6, 20.6, 24.6):
        window(outline[14], outline[15], 2.75, sill, 0.60, 2.17, columns=1, transoms=())
    for a, end in zip(wing[:6], wing[1:7]):
        length = math.dist(a, end)
        if length < 3:
            continue
        for sill, top in galleries[:3]:
            bays = max(1, round(length / 4))
            for n in range(bays):
                window(
                    a,
                    end,
                    (n + 0.5) * length / bays,
                    sill,
                    min(2.2, length / bays - 0.75),
                    top - sill,
                )

    result = Mesh()
    for label, mesh in [
        ('01_主体轮廓', body),
        ('02_屋顶轮廓', roof),
        ('03_入口与平台', entry),
        ('04_转角开廊', arcade),
        ('05_立面窗格', windows),
        ('06_竖排楼名', sign),
    ]:
        result.add_part(label, mesh)
    result.v = [
        (x + u * co - v * si, y + u * si + v * co, z + h) for u, v, h in result.v
    ]
    return result
