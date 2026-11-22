"""Incremental details on previously calibrated college buildings."""

import json
import math
from functools import lru_cache
from pathlib import Path

from college_details import sign
from geometry import Mesh
from physics_east_front import far_panel, remove_region, street_registers
from physics_pilotis import GROUND_BAYS
from physics_pilotis import PORTAL as PHYSICS_PORTAL
from physics_right_wall import SOUTH as NAME_WALL_SOUTH
from physics_right_wall import trim_north_finish
from physics_stairs import SHORT_WIDTH, stair_run

PHYSICS = 'way/957404989'
CIVIL = 'relation/12875606'
MATERIALS = 'relation/11564999'
# Two dark glazed registers separated by the existing recessed fourth-level
# gallery. These edges are the outside street faces, not the two light wells.
PHYSICS_STREET = {0, 6, 14, 15, 16, 17}


def physics_fronts(b, z, C, detail):
    m = Mesh()
    for f in b['form']['facades']:
        edge = f['edge']
        if edge not in PHYSICS_STREET:
            continue
        a, e = f['start'], f['end']
        nx, ny = f['normal']
        length = math.dist(a, e)
        ux, uy = (e[0] - a[0]) / length, (e[1] - a[1]) / length
        theta = math.atan2(uy, ux)

        edge_mesh = Mesh() if edge == 15 else m

        def box(s, out, h, w, d, ht, mat):
            if not detail and mat in (
                'dark',
                'residenceGlass',
                'libraryMullion',
                'glass',
            ):
                # Applied glass/frame facing the street. Omit the backs and
                # sub-decimetre returns of these bonded veneers in the far node.
                front = out + d / 2
                edge_mesh.face(
                    [
                        (
                            a[0] + ux * (s + u) + nx * front,
                            a[1] + uy * (s + u) + ny * front,
                            z + h + v,
                        )
                        for u, v in (
                            (w / 2, -ht / 2),
                            (-w / 2, -ht / 2),
                            (-w / 2, ht / 2),
                            (w / 2, ht / 2),
                        )
                    ],
                    C[mat],
                )
                return
            edge_mesh.box(
                a[0] + ux * s + nx * out,
                a[1] + uy * s + ny * out,
                z + h,
                w,
                d,
                ht,
                C[mat],
                theta,
            )

        n = max(3, round(length / 3.65))
        bay = length / n
        if edge == 16:
            street_registers(m, f, z, C, detail)
        else:
            for low, high in ((3.3, 13.16), (16.52, 29.7)):
                box(
                    length / 2,
                    0.12,
                    (low + high) / 2,
                    length,
                    0.29,
                    high - low,
                    'huicuiFrame',
                )
                for hh in (low, high):
                    box(length / 2, 0.33, hh, length + 0.50, 0.81, 0.48, 'gateStone')
                # Deeper pale stone returns wrap the street corners.
                for s in (bay * 0.25, length - bay * 0.25):
                    box(
                        s,
                        0.28,
                        (low + high) / 2,
                        bay * 0.5,
                        0.47,
                        high - low,
                        'gateStone',
                    )
            for k in (1, 2, 3, 5, 6, 7, 8):
                h = (k + 0.56) * 3.3
                if not detail and edge != 15:
                    mat = far_panel(
                        C, 'physicsFarWindowRow', 'physics-far-lights.png', True
                    )
                    m.face(
                        [
                            (
                                a[0] + ux * t + nx * 0.436,
                                a[1] + uy * t + ny * 0.436,
                                z + h + dh,
                            )
                            for t, dh in (
                                (length, -0.955),
                                (0, -0.955),
                                (0, 0.955),
                                (length, 0.955),
                            )
                        ],
                        mat,
                        [(n, 0), (0, 0), (0, 1), (n, 1)],
                    )
                    continue
                for j in range(n):
                    s = (j + 0.5) * bay
                    if detail:
                        box(s, 0.312, h, bay * 0.7, 0.13, 2.23, 'dark')
                    box(s, 0.396, h, bay * 0.61, 0.08, 1.91, 'residenceGlass')
                    if detail:
                        box(s, 0.452, h, 0.073, 0.053, 1.91, 'libraryMullion')
                        box(
                            s,
                            0.452,
                            h + 0.43,
                            bay * 0.61,
                            0.053,
                            0.068,
                            'libraryMullion',
                        )
        if edge in (15, 16, 17):
            # The lower glazed bays are behind a deep continuous pale lintel.
            for j in range(n):
                s = (j + 0.5) * bay
                y = a[1] + s * uy
                half_panel = bay * 0.41
                if edge == 16 and (
                    y + half_panel > NAME_WALL_SOUTH
                    or abs(y + 858.64) < 4.3
                    or GROUND_BAYS[0] - half_panel < y < GROUND_BAYS[1] + half_panel
                    or PHYSICS_PORTAL[0] - 1 < y < PHYSICS_PORTAL[1] + 1
                ):
                    continue
                box(s, 0.14, 1.65, bay * 0.82, 0.29, 2.31, 'libraryMullion')
                box(s, 0.32, 1.85, bay * 0.68, 0.10, 1.74, 'glass')
        if edge == 15:
            trim_north_finish(edge_mesh, z, remove_region)
            m.extend(edge_mesh)
    # Street 283 degrees locates the raised entrance at the east return;
    # the threshold height and landing extent are estimates.
    vestibule = Mesh()
    x, y = -637.03, -858.64
    vestibule.box(x, y - 1.12, z + 0.07, SHORT_WIDTH, 2.3, 2.42, C['residencePodium'])
    vestibule.box(x, y - 0.14, z + 2.71, 6.20, 0.33, 2.85, C['libraryMullion'])
    for dx in (-1.44, 1.44):
        vestibule.box(x + dx, y - 0.35, z + 2.65, 2.73, 0.10, 2.52, C['glass'])
    vestibule.rotate_z(x, y, math.pi / 2)
    m.extend(vestibule)
    # Street view 283° shows the glazed doorway and a separate railed flight.
    # Its threshold stays on the landing. The lower datum meets the modeled turf.
    stair_run(
        m,
        x + 2.27,
        y,
        SHORT_WIDTH,
        z + 1.28,
        z - 1.08,
        14,
        0.30,
        C['residencePodium'],
        C['lampMetal'],
        detail,
    )
    return m


@lru_cache(maxsize=1)
def civil_canopy_lettering():
    path = Path(__file__).parent / 'fonts/civil-canopy-sign.json'
    return json.loads(path.read_text())


def civil_details(b, z, C, detail):
    m, finish = Mesh(), Mesh()
    entry = next(e for e in b['form']['entrances'] if e['id'] == 'southeast-main')
    corner_x, wall_y = entry['flushEntrance']['returnGlazing']['corner']
    # Local east/north metres from the glass tower's southeast corner. The
    # roof turns at the freestanding blade. The inner glazing stays on the
    # building grid. The two shoulders and depth have independent evidence.
    west = (-16.46, -1.94)
    tip = (-6.30, -9.12)
    east = (2.42, -2.02)
    end = (0.08, 5.92)
    local_ring = [
        west,
        tip,
        east,
        end,
        (-0.08, 5.92),
        (-0.08, -0.05),
        (-16.58, -0.05),
        (-16.58, 0.94),
    ]
    ring = [(corner_x + u, wall_y + v) for u, v in local_ring]
    soffit, top = z + 6.83, z + 8.21
    # Convex front and two returns, triangulated separately so neither roof
    # nor underside crosses through the tower footprint.
    from mathutils import Vector
    from mathutils.geometry import tessellate_polygon

    flat = [Vector((x, y, 0)) for x, y in ring]
    for tri in tessellate_polygon([flat]):
        coords = [ring[i] for i in tri]
        m.face([(x, y, top) for x, y in coords], C['gateStone'])
        m.face([(x, y, soffit) for x, y in reversed(coords)], C['gateTrim'])
    for a, e in zip(ring, ring[1:] + ring[:1]):
        m.face([(*a, soffit), (*e, soffit), (*e, top), (*a, top)], C['gateTrim'])

    # Both front faces share the nose. The lettering
    # belongs to the southeast face only (318°, 294° and opposite 356° views).
    nose_x, nose_y = ring[1]
    for side, (a, e) in enumerate(zip(ring[:3], ring[1:4])):
        vx, vy = e[0] - a[0], e[1] - a[1]
        span = math.hypot(vx, vy)
        ux, uy = vx / span, vy / span
        nx, ny = uy, -ux
        if detail:
            for j in range(1, round(span)):
                t = j / round(span)
                finish.box(
                    a[0] + vx * t + nx * 0.012,
                    a[1] + vy * t + ny * 0.012,
                    (top + soffit) / 2,
                    0.022,
                    0.026,
                    top - soffit,
                    C['gateJoint'],
                    math.atan2(vy, vx),
                )
            finish.box(
                (a[0] + e[0]) / 2 + nx * 0.012,
                (a[1] + e[1]) / 2 + ny * 0.012,
                (top + soffit) / 2,
                span,
                0.026,
                0.023,
                C['gateJoint'],
                math.atan2(vy, vx),
            )
        if side == 1 and detail:
            wordmark = civil_canopy_lettering()
            width, height = wordmark['size']
            points = []
            for u, v in wordmark['vertices']:
                t = 0.17 + 0.70 * u / width
                points.append(
                    (
                        a[0] + vx * t + nx * 0.055,
                        a[1] + vy * t + ny * 0.055,
                        (top + soffit) / 2 + (0.5 - v / height) * 1.02,
                    )
                )
            for i, j, k in wordmark['triangles']:
                pi, pj, pk = (Vector(points[n]) for n in (i, j, k))
                if (pj - pi).cross(pk - pi).dot(Vector((nx, ny, 0))) < 0:
                    pj, pk = pk, pj
                finish.face([tuple(pi), tuple(pj), tuple(pk)], C['libraryInk'])

    # North/south blade centred on the tip, plaque stack faces the east walk.
    py = nose_y + 0.79
    m.box(nose_x, py, z + 4.66, 0.77, 1.93, 9.35, C['huicuiWall'])
    for i in range(8):
        m.box(
            nose_x + 0.404,
            py + 0.12,
            z + 1.58 + i * 0.64,
            0.06,
            1.40,
            0.53,
            C['courtMetal'],
        )
    # Four stone piers enclose three bays and the transom. Their bottoms in
    # the 356° view align with the long wing, independently of the two eaves.
    pier_x = [corner_x - 11.96 + 3.82 * i for i in range(4)]
    floor, head = z + 0.10, z + 6.86
    for px in pier_x:
        m.box(
            px,
            wall_y - 0.20,
            (head + floor) / 2,
            0.55,
            0.49,
            head - floor,
            C['huicuiWall'],
        )
    for j, (a, e) in enumerate(zip(pier_x, pier_x[1:])):
        mid = (a + e) / 2
        m.box(
            mid,
            wall_y - 0.11,
            (head + floor) / 2,
            e - a - 0.48,
            0.18,
            head - floor,
            C['huicuiFrame'],
        )
        for col in range(3):
            fx = mid + (col - 1) * 1.09
            m.box(
                fx,
                wall_y - 0.243,
                z + 1.38,
                1.03,
                0.08,
                2.54,
                C['dark'] if j == 1 else C['libraryMullion'],
            )
            m.box(fx, wall_y - 0.24, z + 4.73, 1.03, 0.08, 3.94, C['huicuiFrame'])
        m.box(mid, wall_y - 0.30, z + 2.71, 3.27, 0.10, 0.14, C['dark'])
        for u in (-1.64, -0.545, 0.545, 1.64):
            m.box(mid + u, wall_y - 0.30, z + 3.47, 0.061, 0.075, 6.72, C['dark'])
    # Side glazing turns north into the east wall. The two-storey stone beam
    # and flat paved sill are visible under the canopy at heading 281°.
    back = 4.60
    for y0, y1 in ((0.03, 2.27), (2.36, back)):
        m.box(
            corner_x + 0.12,
            wall_y + (y0 + y1) / 2,
            z + 3.37,
            0.20,
            y1 - y0,
            6.54,
            C['huicuiFrame'],
        )
        m.box(
            corner_x + 0.25,
            wall_y + (y0 + y1) / 2,
            z + 3.02,
            0.14,
            y1 - y0,
            0.34,
            C['huicuiWall'],
        )
    for v in (0.06, 2.31, back):
        m.box(corner_x + 0.20, wall_y + v, z + 3.45, 0.34, 0.23, 6.76, C['huicuiWall'])
    # Apron slopes up to the 0.10 m threshold. The outer edge follows the
    # declared 0.3% x/y site grade; steps in the western annex are separate.
    pad = [
        (-13.0, -0.54),
        (-13.70, -6.38),
        (-7.15, -9.52),
        (2.76, -5.02),
        (2.58, 4.67),
        (0.38, 4.67),
        (0.38, -0.54),
    ]

    def paving_height(u, v):
        site = (
            z
            - 0.02
            + 0.003
            * (corner_x + u - entry['center'][0] + wall_y + v - entry['center'][1])
        )
        ramp = min(1.0, max(0.0, (-v - 0.54) / 6.5))
        return (z + 0.10) * (1 - ramp) + (site + 0.018) * ramp

    pad_xyz = [(corner_x + u, wall_y + v, paving_height(u, v)) for u, v in pad]
    for tri in tessellate_polygon([[Vector((x, y, 0)) for x, y, _ in pad_xyz]]):
        m.face([pad_xyz[i] for i in tri], C['gateStone'])
    for a, e in zip(pad_xyz, pad_xyz[1:] + pad_xyz[:1]):
        m.face([(a[0], a[1], z - 0.18), (e[0], e[1], z - 0.18), e, a], C['gateStone'])
    # Alternating open lights on the existing tower.
    for col, row in ((1, 10), (4, 9), (2, 7), (4, 5), (1, 3), (3, 2)):
        m.box(
            -491.75 + col * 2.5,
            -838.21,
            z + 8.64 + row * 1.50,
            0.84,
            0.09,
            1.16,
            C['dark'],
        )
    return m, finish


def materials_screen(b, z, C, detail):
    m = Mesh()
    # College English exterior: screen on the north/right pier as seen
    # facing west, below the three-column upper glazing in the existing form.
    m.box(-510.04, -884.99, z + 12.23, 0.26, 10.23, 6.23, C['gateTrim'])
    m.box(-509.88, -884.99, z + 12.23, 0.14, 9.88, 5.89, C['libraryMullion'])
    # Real lettering stands above the front grille between the two white shafts.
    e = next(e for e in b['form']['entrances'] if 'recessedStairEntry' in e)
    ex, ey = e['center']
    canopy = e['recessedStairEntry']['canopy']
    fx = ex + canopy['frontOffset']
    top = z + canopy['topHeight']
    m.box(fx + 0.11, ey, top + 0.07, 0.23, 9.72, 0.14, C['dark'])
    if detail:
        sign(
            m,
            '资源环境与材料学院',
            fx + 0.24,
            ey,
            top + 0.64,
            9.64,
            1.00,
            C['gateTrim'],
            math.pi / 2,
        )
        sign(
            m,
            'SCHOOL OF RESOURCES ENVIRONMENT AND MATERIALS',
            fx + 0.25,
            ey,
            top + 0.16,
            9.68,
            0.21,
            C['gateTrim'],
            math.pi / 2,
        )
    return m


MATERIALS_REAR = {4, 5, 9}


def materials_rear(b, z, C, detail):
    """North-facing wings and west return visible from the 154-degree street station."""
    m = Mesh()
    for f in b['form']['facades']:
        if f['edge'] not in MATERIALS_REAR or f['part'] != 'high-body':
            continue
        a, c = f['start'], f['end']
        nx, ny = f['normal']
        length = math.dist(a, c)
        ux, uy = (c[0] - a[0]) / length, (c[1] - a[1]) / length
        angle = math.atan2(uy, ux)

        def box(s, out, h, w, d, ht, material):
            m.box(
                a[0] + ux * s + nx * out,
                a[1] + uy * s + ny * out,
                z + h,
                w,
                d,
                ht,
                C[material],
                angle,
            )

        bays = max(3, round(length / 3.85))
        spacing = length / bays
        for low, high in ((3.95, 17.48), (21.86, 47.36)):
            box(
                length / 2,
                0.13,
                (low + high) / 2,
                length,
                0.32,
                high - low,
                'huicuiFrame',
            )
            for end in (0.56, length - 0.56):
                box(end, 0.32, (low + high) / 2, 1.12, 0.73, high - low, 'gateStone')
            for h in (low, high):
                box(length / 2, 0.38, h, length + 0.34, 0.85, 0.56, 'gateStone')
        for k in range(11):
            h = (k + 0.52) * 48.1 / 11
            for j in range(bays):
                s = (j + 0.5) * spacing
                if k == 4:
                    box(s, 0.22, h, spacing * 0.88, 0.32, 2.33, 'libraryMullion')
                    box(s, 0.43, h, spacing * 0.79, 0.14, 2.14, 'residenceGlass')
                else:
                    box(s, 0.337, h, spacing * 0.67, 0.18, 2.58, 'dark')
                    box(
                        s, 0.443, h + 0.12, spacing * 0.60, 0.09, 2.01, 'residenceGlass'
                    )
                    box(s, 0.443, h - 1.05, spacing * 0.60, 0.09, 0.33, 'courtMetal')
                if detail:
                    for shift in (-0.13, 0.13):
                        box(
                            s + shift * spacing,
                            0.502,
                            h + 0.12,
                            0.065,
                            0.052,
                            1.99,
                            'huicuiFrame',
                        )
                    box(s, 0.502, h + 0.54, spacing * 0.60, 0.052, 0.08, 'huicuiFrame')
        for h in (17.48, 21.86):
            box(length / 2, 0.32, h, length, 0.67, 0.47, 'gateStone')
    return m
