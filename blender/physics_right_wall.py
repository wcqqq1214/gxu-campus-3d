"""East-facing physics name wall and the photographed lower north-facing wing.

Distances are relative to the northeast white corner and the adopted building
datum. The photo-derived proportions have to fit below the retained soffit
and above the actual exported terrain and the enclosed ground floor.
"""

import json
from functools import lru_cache
from pathlib import Path

from entry_guardrails import glass_material
from geometry import MATERIALS, material, tile_material

FRONT = -636.18
NORTH = -808.74
WIDTH = 12.93
SOUTH = NORTH - WIDTH
WEST = -647.24  # length of the confirmed ground-floor corner return
FRAME_WEST = -701.10
GALLERY_WEST, GALLERY_EAST = FRONT - 18.1, FRONT - 9.9
BOTTOM = 4.70
TOP = 20.25
LID = TOP + 2.32
SLOT = (SOUTH + WIDTH * 0.073, SOUTH + WIDTH * 0.186)
SILL = BOTTOM - 3.06
BACK_X = FRONT - 2.12


def trim_shell(body, z, cut):
    # Remove the old external shell/quarter-storey fittings from inside the
    # new reveal and base glazing. Stop before the connected gallery soffit.
    cut(body, [(1, SOUTH, 1), (0, BACK_X - 0.06, 1), (2, z + 16.32, -1)])
    cut(body, [(0, WEST, 1), (1, NORTH - 2.06, 1), (2, z + 16.32, -1)])

    cut(
        body,
        [
            (0, FRAME_WEST + 0.45, 1),
            (1, NORTH - 1.52, 1),
            (2, z + 1.59, 1),
            (2, z + 16.32, -1),
        ],
    )
    cut(
        body,
        [
            (0, GALLERY_WEST, 1),
            (0, GALLERY_EAST, -1),
            (1, NORTH - 3.40, 1),
            (2, z + 1.59, 1),
            (2, z + 15.12, -1),
        ],
    )


def trim_north_finish(mesh, z, cut):
    # Edge 15's full lower register is replaced. Only the northeast corner
    # also replaces the old ground-floor panes below it.
    cut(mesh, [(0, WEST, 1), (2, z + 1.59, -1)])
    cut(mesh, [(2, z + 1.59 - 0.001, 1), (2, z + 15.12, -1)])


@lru_cache(maxsize=1)
def glyphs():
    return json.loads((Path(__file__).parent / 'fonts/physics-name.json').read_text())


def right_wall(mesh, z, C, detail):
    trim = 'libraryTrim'

    def shade(name, rgb, rough, metal=0):
        if name not in C:
            C[name] = material(name, rgb, rough, metal)

    shade('physicsPier', (0.112, 0.094, 0.086), 0.89)
    shade('physicsWindow', (0.055, 0.079, 0.091), 0.24, 0.42)
    shade('physicsPlinth', (0.155, 0.166, 0.176), 0.86)
    shade('physicsGlazingBar', (0.026, 0.029, 0.032), 0.41, 0.23)
    shade('physicsJoint', (0.355, 0.34, 0.32), 0.9)
    shade('physicsNameInk', (0.032, 0.039, 0.046), 0.48, 0.20)
    finish = 'physicsWallCeramic' if detail else 'libraryTrim'
    if detail:
        tile_material(C, finish, 'physics-wall-ceramic.png', (0.65, 0.63, 0.61))
        MATERIALS[C[finish]].node_tree.nodes.get('Principled BSDF').inputs[
            'Roughness'
        ].default_value = 0.83

    def block(x0, x1, y0, y1, lo, hi, mat):
        mesh.box(
            (x0 + x1) / 2,
            (y0 + y1) / 2,
            z + (lo + hi) / 2,
            x1 - x0,
            y1 - y0,
            hi - lo,
            C[mat],
        )

    def face(pts, mat, uv=None):
        mesh.face([(x, y, z + h) for x, y, h in pts], C[mat], uv)

    def east(y0, y1, lo, hi, x, mat):
        pts = [(x, y0, lo), (x, y1, lo), (x, y1, hi), (x, y0, hi)]
        uv = (
            [((y - SOUTH) / 0.72, h / 0.72) for _, y, h in pts]
            if mat == finish and detail
            else None
        )
        face(pts, mat, uv)

    def north(x0, x1, lo, hi, y, mat):
        pts = [(x1, y, lo), (x0, y, lo), (x0, y, hi), (x1, y, hi)]
        uv = (
            [((FRONT - x) / 0.72, h / 0.72) for x, _, h in pts]
            if mat == finish and detail
            else None
        )
        face(pts, mat, uv)

    # Ceramic field with shallow joints and a genuinely missing vertical bay.
    # Back, ends and reveals are modeled independently of the decorated fronts.
    s0, s1 = SLOT
    height = TOP - BOTTOM
    foot, head = BOTTOM + 0.073 * height, BOTTOM + 0.878 * height
    lower_board, upper_board = (BOTTOM + f * height - 0.175 for f in (0.344, 0.629))
    for a, b, lo, hi in [
        (SOUTH, s0, BOTTOM, TOP),
        (s1, NORTH, BOTTOM, TOP),
        (s0, s1, BOTTOM, foot),
        (s0, s1, head, TOP),
    ]:
        # Split the front surface at joints; adjacent intervals have no overlay.
        joints = (
            [
                j
                for j in (
                    foot,
                    lower_board,
                    lower_board + 0.70,
                    upper_board,
                    upper_board + 0.70,
                    head,
                )
                if lo + 0.03 < j < hi - 0.03
            ]
            if detail
            else []
        )
        cursor = lo
        for h in joints:
            east(a, b, cursor, h - 0.013, FRONT, finish)
            east(a, b, h - 0.013, h + 0.013, FRONT, 'physicsJoint')
            cursor = h + 0.013
        east(a, b, cursor, hi, FRONT, finish)
    for y, x0, x1, lo, hi, reverse in [
        (s0, BACK_X, FRONT, foot, head, True),
        (s1, BACK_X, FRONT, foot, head, False),
    ]:
        pts = [(x0, y, lo), (x1, y, lo), (x1, y, hi), (x0, y, hi)]
        face(pts[::-1] if reverse else pts, trim)
    for a, b, lo, up in [
        (SOUTH, NORTH - 0.67, BOTTOM, False),
        (SOUTH, NORTH - 0.67, TOP, True),
        (s0, s1, foot, True),
        (s0, s1, head, False),
    ]:
        pts = [(BACK_X, a, lo), (FRONT, a, lo), (FRONT, b, lo), (BACK_X, b, lo)]
        face(pts if up else pts[::-1], trim)
    # A tiled back plane closes the occupied wing. Two recessed floor edges,
    # each with a dark inset guard, separate the three openings.
    # Behind the split the rails rise away from the street. The actual back
    # wall is farther in; do not close the slot with an opaque window decal.
    depth = FRONT - 3.28
    east(s0, s1, foot, head, depth, 'physicsPier')
    for y, flip in ((s0, True), (s1, False)):
        pts = [(depth, y, foot), (BACK_X, y, foot), (BACK_X, y, head), (depth, y, head)]
        face(pts[::-1] if flip else pts, trim)
    for lo, hi in (
        (foot, lower_board),
        (lower_board + 0.35, upper_board),
        (upper_board + 0.35, head),
    ):
        # The banner resolves raking rails, not a tread count inside the slit.
        for x in (FRONT - 0.92, FRONT - 1.85, FRONT - 2.78):
            h = lo + 1.02 + (FRONT - 0.92 - x) * 0.55
            y = s0 + 0.23 + (FRONT - 0.92 - x) * 0.50
            block(x - 0.024, x + 0.024, y - 0.024, y + 0.024, h - 0.95, h, 'lampMetal')
        mesh.line(
            (FRONT - 0.92, s0 + 0.23, z + lo + 1.02),
            (FRONT - 2.78, s0 + 1.16, z + lo + 2.043),
            0.034,
            C['lampMetal'],
            4,
        )
    for h in (lower_board, upper_board):
        block(BACK_X, FRONT - 0.38, s0, s1, h, h + 0.35, trim)
        block(FRONT - 0.56, FRONT - 0.50, s0, s1, h + 0.35, h + 0.99, 'huicuiFrame')
        block(FRONT - 0.60, FRONT - 0.49, s0, s1, h + 0.99, h + 1.04, 'lampMetal')
    # Ground-level view, station 285 degrees: narrow pair, tile pier, wider
    # multi-light group and solid northeast bearing. Glass is behind the lip.
    inset = FRONT - 0.88
    corner = NORTH - 1.76
    pier0, pier1 = SOUTH + 2.77, SOUTH + 3.87
    block(BACK_X, inset + 0.14, SOUTH, SOUTH + 0.34, SILL, BOTTOM, 'physicsPier')
    block(BACK_X, inset + 0.14, pier0, pier1, SILL, BOTTOM, 'physicsPier')
    block(BACK_X, inset + 0.22, corner, NORTH - 0.49, SILL, BOTTOM, 'physicsPier')
    for a, b, n in [(SOUTH + 0.34, pier0, 2), (pier1, corner, 6)]:
        east(a, b, SILL, BOTTOM, inset, 'physicsWindow')
        for j in range(n + 1):
            y = a + (b - a) * j / n
            if detail:
                block(
                    inset,
                    inset + 0.082,
                    y - 0.054,
                    y + 0.054,
                    SILL,
                    BOTTOM,
                    'physicsGlazingBar',
                )
            else:
                east(
                    y - 0.054,
                    y + 0.054,
                    SILL,
                    BOTTOM,
                    inset + 0.082,
                    'physicsGlazingBar',
                )
        for h in (SILL + 0.64 * (BOTTOM - SILL), SILL + 0.82 * (BOTTOM - SILL)):
            block(inset, inset + 0.082, a, b, h - 0.048, h + 0.048, 'physicsGlazingBar')
    block(
        BACK_X, FRONT - 0.12, SOUTH, NORTH - 0.49, BOTTOM - 0.17, BOTTOM, 'physicsPier'
    )
    # Continuous stone plinth. The dark course follows the slab and dies into
    # the rising ground, retaining contact even at the high end of the wall.
    block(BACK_X, inset + 0.18, SOUTH, NORTH - 0.49, -1.79, -0.73, 'huicuiFrame')
    block(BACK_X, inset + 0.23, SOUTH, NORTH - 0.49, -0.73, SILL, 'physicsPlinth')
    if detail:
        for j in range(1, 12):
            y = SOUTH + j * 1.04
            east(y - 0.006, y + 0.006, -0.73, SILL, inset + 0.235, 'physicsPier')
        east(SOUTH, NORTH - 0.49, -0.50, -0.487, inset + 0.235, 'physicsPier')

    # Hualan's ground oblique: three rows of narrow punched windows, three
    # stacked recessed galleries and a longer window field inside one frame.
    recess = NORTH - 0.65
    jamb = FRONT - 1.45
    far_jamb = FRAME_WEST + 1.13
    low, high = BOTTOM + 0.64, TOP - 1.27
    north(FRAME_WEST, FRONT, BOTTOM, low, NORTH, finish)
    north(FRAME_WEST, FRONT, high, TOP, NORTH, finish)
    for left, right in ((FRAME_WEST, far_jamb), (jamb, FRONT)):
        north(left, right, low, high, NORTH, finish)
    for h, up in ((BOTTOM, False), (low, True), (high, False), (TOP, True)):
        # End against the east panel's return so neither underside overlaps.
        pts = [
            (FRAME_WEST, recess, h),
            (FRONT, recess, h),
            (FRONT, NORTH, h),
            (FRAME_WEST, NORTH, h),
        ]
        face(pts if up else pts[::-1], trim)
    for x, normal in ((jamb, -1), (far_jamb, 1)):
        pts = [(x, recess, low), (x, NORTH, low), (x, NORTH, high), (x, recess, high)]
        face(pts if normal == 1 else pts[::-1], trim)
    # End the frame on its own short west return rather than a naked butt edge.
    for h0, h1 in ((BOTTOM, low), (low, high), (high, TOP)):
        pts = [
            (FRAME_WEST, NORTH - 1.55, h0),
            (FRAME_WEST, NORTH, h0),
            (FRAME_WEST, NORTH, h1),
            (FRAME_WEST, NORTH - 1.55, h1),
        ]
        face(pts[::-1], trim)
    story = (high - low) / 3
    for left, right, count in [(far_jamb, GALLERY_WEST, 20), (GALLERY_EAST, jamb, 4)]:
        if not detail and count == 20:
            from physics_east_front import far_panel

            mat = far_panel(C, 'physicsFarNorthBays', 'physics-far-north.png')
            mesh.face(
                [
                    (x, recess, z + h)
                    for x, h in ((right, low), (left, low), (left, high), (right, high))
                ],
                mat,
                [(0, 0), (count, 0), (count, 3), (0, 3)],
            )
            continue
        punched = count == 4
        if not punched:
            north(left, right, low, high, recess, 'physicsPier')
        pitch = (right - left) / count
        for row in range(3):
            base = low + row * story
            sill, head = base + 0.21 * story, base + 0.88 * story
            if punched:
                north(left, right, base, sill, recess, 'physicsPier')
                north(left, right, head, base + story, recess, 'physicsPier')
            for j in range(count):
                a = left + (j + 0.16) * pitch
                b = left + (j + 0.84) * pitch
                glazing = recess - 0.31 if punched else recess + 0.035
                if punched:
                    north(left + j * pitch, a, sill, head, recess, 'physicsPier')
                    north(b, left + (j + 1) * pitch, sill, head, recess, 'physicsPier')
                    for x, flip in ((a, False), (b, True)):
                        pts = [
                            (x, glazing, sill),
                            (x, recess, sill),
                            (x, recess, head),
                            (x, glazing, head),
                        ]
                        face(pts[::-1] if flip else pts, 'physicsPier')
                    for h, flip in ((sill, False), (head, True)):
                        pts = [
                            (a, glazing, h),
                            (b, glazing, h),
                            (b, recess, h),
                            (a, recess, h),
                        ]
                        face(pts[::-1] if flip else pts, 'physicsPier')
                north(a, b, sill, head, glazing, 'physicsWindow')
                if detail:
                    north(
                        a,
                        b,
                        base + 0.03 * story,
                        base + 0.17 * story,
                        recess + 0.035,
                        'huicuiFrame',
                    )
                    for k in (1, 2):
                        x = a + (b - a) * k / 3
                        north(
                            x - 0.030,
                            x + 0.030,
                            sill,
                            head,
                            glazing + 0.030,
                            'fenceIron',
                        )
                    north(
                        a,
                        b,
                        sill + 0.70 * (head - sill),
                        sill + 0.70 * (head - sill) + 0.071,
                        glazing + 0.035,
                        'fenceIron',
                    )
    rear = NORTH - 3.34
    west, east_end = GALLERY_WEST, GALLERY_EAST
    north(west, east_end, low, high, rear, 'physicsPier')
    for x, positive in ((west, True), (east_end, False)):
        pts = [(x, rear, low), (x, recess, low), (x, recess, high), (x, rear, high)]
        face(pts if positive else pts[::-1], 'physicsPier')
    glass = glass_material(C)
    for row in range(3):
        level = low + row * story
        block(west, east_end, rear, recess, level, level + 0.28, 'physicsPier')
        block(west, east_end, rear, recess, level + 0.28, level + 0.35, trim)
        north(
            west + 0.34,
            east_end - 0.34,
            level + 0.37,
            level + story - 0.26,
            rear + 0.045,
            'physicsWindow',
        )
        for j in (1, 2, 3) if detail else (2,):
            x = west + j * (east_end - west) / 4
            north(
                x - 0.046,
                x + 0.046,
                level + 0.37,
                level + story - 0.26,
                rear + 0.07,
                'fenceIron',
            )
        guard_y = recess - 0.16
        mesh.face(
            [
                (x, guard_y, z + h)
                for x, h in (
                    (east_end, level + 0.38),
                    (west, level + 0.38),
                    (west, level + 1.19),
                    (east_end, level + 1.19),
                )
            ],
            glass,
        )
        block(
            west,
            east_end,
            guard_y - 0.03,
            guard_y + 0.03,
            level + 1.18,
            level + 1.23,
            'lampMetal',
        )
        for j in range(4):
            x = west + 0.18 + j * (east_end - west - 0.36) / 3
            block(
                x - 0.027,
                x + 0.027,
                guard_y - 0.03,
                guard_y + 0.03,
                level + 0.35,
                level + 1.20,
                'lampMetal',
            )
    block(west, east_end, rear, recess, high - 0.12, high, trim)
    # Backing between the new upper frame and the retained upper soffit.
    north(FRAME_WEST + 0.4, FRONT - 1.15, TOP, LID, NORTH - 1.45, 'physicsWindow')
    # Base turns with the same solid northeast bearing under the white frame.
    block(WEST, BACK_X, NORTH - 2.10, NORTH - 0.49, -1.79, -0.73, 'huicuiFrame')
    block(WEST, BACK_X, NORTH - 2.10, NORTH - 0.49, -0.73, SILL, 'bridgeConcrete')
    north(WEST, BACK_X, SILL, BOTTOM, NORTH - 1.15, 'physicsWindow')
    for x in (WEST + 0.88, WEST + 4.16, WEST + 7.32):
        block(
            x - 0.14, x + 0.14, NORTH - 2.10, NORTH - 1.04, SILL, BOTTOM, 'physicsPier'
        )
    # High recessed glazing behind the head. The calibrated shared floor and
    # soffit remain behind, and connect to the rooms through the original wing.
    east(SOUTH, NORTH - 0.54, TOP, LID, FRONT - 1.73, 'physicsWindow')
    block(
        FRONT - 2.2, FRONT - 1.15, NORTH - 1.45, NORTH - 0.78, TOP, LID, 'physicsPier'
    )
    for y in (SOUTH + 0.54, SOUTH + 4.7, SOUTH + 8.6, NORTH - 1.12):
        block(FRONT - 1.83, FRONT - 1.53, y - 0.17, y + 0.17, TOP, LID, 'physicsPier')
    # Keep the same artwork and registration at both LODs.
    if not detail:
        # Same registered glyphs on a single sampled far face.
        from physics_east_front import far_panel

        mat = far_panel(C, 'physicsFarName', 'physics-far-name.png', True)
        lo = z + BOTTOM + height * 0.851 - 0.305
        a, b = (SOUTH + WIDTH * k for k in (0.259, 0.927))
        mesh.face(
            [
                (FRONT + 0.038, y, h)
                for y, h in ((a, lo), (b, lo), (b, lo + 0.61), (a, lo + 0.61))
            ],
            mat,
            [(0, 0), (1, 0), (1, 1), (0, 1)],
        )
        return
    g = glyphs()
    pts = [
        (
            FRONT + 0.038,
            SOUTH + WIDTH * (0.259 + (0.927 - 0.259) * u / g['width']),
            z + BOTTOM + height * 0.851 + 0.305 - 0.61 * v / g['height'],
        )
        for u, v in g['points']
    ]
    for i, j, k in g['triangles']:
        mesh.face([pts[i], pts[k], pts[j]], C['physicsNameInk'])
