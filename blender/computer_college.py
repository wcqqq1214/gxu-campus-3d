"""North entrance of the computer college. The adjoining west wing is a separate ID."""

import json
import math
import sys
from functools import lru_cache
from pathlib import Path

from college_details import pane, shell, sign
from computer_site import CENTER_X, COURT_Z, NORTH, WIDTH
from geometry import Mesh


@lru_cache(maxsize=1)
def ground_levels():
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / 'scripts'))
    from terrain_elevation import make_elevation

    return make_elevation(json.loads((root / 'public/data/terrain.json').read_text()))


def bed_exposed_walls(mesh, ring, datum, finish):
    # Extend the existing closed shell only where it would end above the
    # published ground. The eastern alley shows a stone plinth below windows.
    # The hidden southern return inherits this finish as an estimate.
    soil = ground_levels()
    for a, b in zip(ring, ring[1:]):
        if min(a[1], b[1]) > NORTH - 0.1 or max(a[0], b[0]) < -236:
            continue
        n = max(1, math.ceil(math.dist(a, b) / 2))
        pts = [
            (a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n)
            for i in range(n + 1)
        ]
        for p, q in zip(pts, pts[1:]):
            top = datum - 0.50
            zp, zq = (min(top, soil(*v) - 0.18) for v in (p, q))
            if min(zp, zq) < top:
                # Clockwise ring: normal faces left of the edge.
                mesh.face([(*q, zq), (*p, zp), (*p, top), (*q, top)], finish)


def computer_college(landmark, b, z, C, detail):
    m = shell(b, z, 32.4, C['gateStone'], C['paleRoof'])
    f = Mesh()
    # Gallery 25 and the 180 degree view are taken NORTH of the building:
    # the pink mass on the left of the photograph is the geographic east end.
    north = NORTH
    m.box(-198.6, north + 0.09, z + 16.22, 7.65, 0.31, 32.45, C['pink'])
    m.box(-204.28, north + 0.12, z + 15.36, 3.48, 0.37, 30.72, C['libraryMullion'])
    for level in range(8):
        h = z + 2.0 + level * 4.02
        for x in (-197.2, -198.5):
            pane(f, x, north + 0.32, h, 0.73, 2.05, (0, 1), C, detail)
        pane(f, -204.28, north + 0.33, h, 3.18, 3.84, (0, 1), C, detail)
        if level:
            for i in range(7):
                pane(
                    f,
                    -208.0 - i * 4.23,
                    north,
                    h + (COURT_Z - z) * (8 - level) / 7,
                    2.47,
                    2.09,
                    (0, 1),
                    C,
                    detail,
                )
        m.box(-198.6, north + 0.24, h - 1.50, 7.57, 0.12, 0.09, C['libraryStone'])
    # Preserve side and return windows on the mapped polygon (the old cuboid
    # obscured the adjacent institute and filled the southwest setback).
    ring = b['polygons'][0][0]
    for a, c in zip(ring, ring[1:]):
        dx, dy = c[0] - a[0], c[1] - a[1]
        length = math.hypot(dx, dy)
        if min(a[1], c[1]) > north - 0.1 or max(a[0], c[0]) < -236:
            continue
        normal = (-dy / length, dx / length)  # clockwise exterior
        n = max(1, round(length / 4))
        for j in range(n):
            t = (j + 0.5) / n
            for k in range(8):
                pane(
                    f,
                    a[0] + dx * t,
                    a[1] + dy * t,
                    z + 1.8 + k * 4.02,
                    2.15,
                    1.8,
                    normal,
                    C,
                    False,
                )
    bed_exposed_walls(m, ring, z, C['wallStone'])
    x = CENTER_X
    entry_z = COURT_Z
    m.box(x, north + 1.54, entry_z + 0.25, WIDTH, 3.17, 0.90, C['gateJoint'])
    for i in range(4):
        h = (4 - i) * 0.175
        y = north + 3.125 + (i + 0.5) * 0.34
        # Dark riser face and pale stone nosing visible in stations 6 and 7.
        m.box(
            x,
            y,
            entry_z + (h - 0.025 - 0.20) / 2,
            WIDTH,
            0.34,
            h - 0.025 + 0.20,
            C['residencePodium'],
        )
        m.box(x, y + 0.008, entry_z + h - 0.0125, WIDTH, 0.356, 0.025, C['drainStone'])
    m.box(x, north + 1.67, entry_z + 4.25, 28.5, 3.72, 0.56, C['gateStone'])
    for px in (-232.57, -224.55, -216.54, -208.52):
        m.cylinder(px, north + 3.06, entry_z + 2.34, 0.43, 3.30, C['libraryStone'], 16)
        m.cylinder(px, north + 3.06, entry_z + 0.81, 0.51, 0.22, C['libraryStone'], 16)
    for px in (-230, -225.3, -220.6, -215.9, -211.2):
        pane(
            f,
            px,
            north,
            entry_z + 2.22,
            4.15,
            2.95,
            (0, 1),
            C,
            detail,
            C['huicuiFrame'],
        )
        if detail:
            for dx in (-1.37, 1.37):
                m.box(
                    px + dx, north + 0.27, entry_z + 2.22, 0.075, 0.08, 2.92, C['metal']
                )
    if detail:
        sign(
            f,
            '计算机与电子信息学院',
            x,
            north + 3.55,
            entry_z + 4.28,
            16,
            0.49,
            C['timeLetter'],
            math.pi,
        )
    # The north composition has an open roof gallery and a raised square
    # shelter at its west end. Clear space and thin piers show below each cap.
    for x in (-229.7, -225.9, -222.1, -218.3, -214.5, -210.7, -206.9):
        m.box(x, -751.51, z + 32.97, 0.32, 0.48, 1.15, C['gateStone'])
    m.box(-217.9, -752.16, z + 33.66, 25.4, 5.12, 0.31, C['gateTrim'])
    for x in (-234.95, -230.10):
        for y in (-751.38, -754.55):
            m.box(x, y, z + 33.36, 0.42, 0.53, 1.96, C['gateStone'])
    m.box(-232.52, -752.95, z + 34.52, 8.80, 7.20, 0.35, C['gateTrim'])
    m.add_part('计算机学院北立面', f)
    return m


RESEARCH_WING = 'way/880036328'


def computer_west_wing(b, z, C, detail):
    """Separate mapped footprint attached to the computer building's north frontage."""
    h = 30.5
    m = shell(b, z, h, C['pink'], C['paleRoof'])
    f = Mesh()
    x0, y = -267.94, -750.36
    width = 31.65
    spacing = width / 9
    for level in range(8):
        wall_z = z + 1.42 + level * 3.81
        for j in range(9):
            x = x0 + (j + 0.5) * spacing
            # Trees hide the ground-floor door positions; keep the darker
            # recessed bays without assigning an institute entrance or sign.
            pane(
                f,
                x,
                y,
                wall_z,
                2.46,
                2.37 if level else 2.62,
                (0, 1),
                C,
                detail,
                C['libraryMullion'] if not level else C['residenceGlass'],
            )
        if level:
            m.box(
                x0 + width / 2, y + 0.16, wall_z - 1.64, width, 0.44, 0.34, C['tenWall']
            )
    for j in range(10):
        m.box(x0 + j * spacing, y + 0.30, z + 14.68, 0.44, 0.74, 29.38, C['pink'])
    for j in range(6):
        m.box(
            x0 + 0.72 + j * 6.04, y - 0.42, z + 31.18, 0.34, 0.54, 1.37, C['gateStone']
        )
    m.box(x0 + width / 2, y - 0.82, z + 32.04, width + 1.28, 3.60, 0.35, C['gateTrim'])
    for j in range(9):
        x = x0 + (j + 0.5) * spacing
        m.box(x, y + 0.24, z + 29.55, 2.61, 0.49, 1.01, C['libraryMullion'])
    m.add_part('西邻研究楼北面柱网与凹窗', f)
    return m
