"""Open bays in the east spine of way/957404989, in campus metres.

Hualan's 14485 and 15244 show the set-back cross-bridge, coffered soffit
and enclosed rooms at its ends. Street station 09007200121903051340120769B
shows three grille-backed bays south of the glazed stair. Keep the other
ground-floor rooms and the west side of the E-shaped court intact.
"""

from entry_guardrails import glass_material
from physics_court import NORTH_ROOM_START, SHARED_DEPTH, SOUTH_ROOM_END, north_court

PORTAL = (-845.2, -829.4)
SOUTH_FRAME_BAY = -850.10
FRAME_SLOT = (-849.12, -846.70)
SOUTH_LIGHT_BAY = (-884.0, -878.40)
FRAME_DEPTH = 6.60
GROUND_BAYS = (-886.45, -867.85)
GALLERY_FLOOR = 13.2
UPPER_SOFFIT = 16.32
GALLERY_DEPTH = 3.15
BRIDGE_FRONT = 1.55
BRIDGE_BACK = 4.35


def open_physics_portal(mesh, b, z, C):
    facades = {f['edge']: f for f in b['form']['facades']}
    outer, inner = facades[16], facades[10]
    south, north = PORTAL
    ground_s, ground_n = GROUND_BAYS
    floor, lid = GALLERY_FLOOR, UPPER_SOFFIT

    def wall_x(f, y):
        a, e = f['start'], f['end']
        return a[0] + (e[0] - a[0]) * (y - a[1]) / (e[1] - a[1])

    def point(y, depth, h):
        return (wall_x(outer, y) - depth, y, z + h)

    def face(coords, material):
        mesh.face([point(*p) for p in coords], C[material])

    def panel(y0, y1, d, h0, h1, material):
        face([(y0, d, h0), (y1, d, h0), (y1, d, h1), (y0, d, h1)], material)

    def solid(y0, y1, d0, d1, h0, h1, material):
        # Eight corners follow the slightly skew mapped footprint edges.
        p = [
            (y0, d0, h0),
            (y1, d0, h0),
            (y1, d1, h0),
            (y0, d1, h0),
            (y0, d0, h1),
            (y1, d0, h1),
            (y1, d1, h1),
            (y0, d1, h1),
        ]
        for indices in (
            (3, 2, 1, 0),
            (0, 1, 5, 4),
            (1, 2, 6, 5),
            (2, 3, 7, 6),
            (3, 0, 4, 7),
            (4, 5, 6, 7),
        ):
            face([p[i] for i in indices], material)

    def cut_wall(f, holes):
        # Replace only the footprint's original exterior quad. The cuts are
        # disjoint in (world Y, relative Z); no footprint extrusion or boolean.
        ys = sorted((f['start'][1], f['end'][1]))
        matches = []
        for i, indices in enumerate(mesh.f):
            vs = [mesh.v[k] for k in indices]
            if len(vs) == 4 and all(abs(x - wall_x(f, y)) < 0.001 for x, y, _ in vs):
                if min(v[2] for v in vs) < z and max(v[2] for v in vs) > z + lid:
                    matches.append((i, vs))
        if len(matches) != 1:
            raise ValueError(f'Expected one physics shell face on edge {f["edge"]}')
        i, vs = matches[0]
        material = mesh.m.pop(i)
        mesh.f.pop(i)
        heights = [min(v[2] for v in vs) - z, max(v[2] for v in vs) - z]
        splits = sorted(set(ys + [y for a, b, _, _ in holes for y in (a, b)]))
        for a, b in zip(splits, splits[1:]):
            voids = sorted((lo, hi) for y0, y1, lo, hi in holes if y0 <= a and b <= y1)
            for lo, hi in zip(
                [heights[0]] + [v[1] for v in voids],
                [v[0] for v in voids] + [heights[1]],
            ):
                if hi - lo < 0.001:
                    continue
                pts = [
                    (wall_x(f, y), y, z + h)
                    for y, h in ((a, lo), (b, lo), (b, hi), (a, hi))
                ]
                mesh.face(pts if f['normal'][0] > 0 else pts[::-1], material)

    ends = sorted((outer['start'][1], outer['end'][1]))
    a, b_end = ends[0] + 2.4, ends[1] - 2.4
    gallery = ((a, south), (north, b_end))
    cut_wall(
        outer,
        [
            (ground_s, ground_n, -1.30, 3.28),
            (south, north, -0.12, lid),
            (SOUTH_FRAME_BAY, south, 2.74, floor - 0.18),
        ]
        + [(y0, y1, floor - 0.18, lid) for y0, y1 in gallery],
    )
    slot_s, slot_n = FRAME_SLOT
    cut_wall(inner, [(south, north, -0.12, lid), (slot_s, slot_n, 4.10, floor - 0.18)])
    light_s, light_n = SOUTH_LIGHT_BAY
    cut_wall(facades[2], [(light_s, light_n, floor - 0.18, lid)])

    # Three ground bays: a raised, gently graded passage behind freestanding
    # posts. The slats finish in front of a closed interior wall.
    depth, base, soffit = 3.25, -1.30, 3.28

    def deck(y):
        return -0.22 + 0.62 * (y - ground_s) / (ground_n - ground_s)

    face(
        [
            (ground_s, 0, deck(ground_s)),
            (ground_n, 0, deck(ground_n)),
            (ground_n, depth, deck(ground_n)),
            (ground_s, depth, deck(ground_s)),
        ],
        'residencePodium',
    )
    face(
        [
            (ground_s, 0, base),
            (ground_n, 0, base),
            (ground_n, 0, deck(ground_n)),
            (ground_s, 0, deck(ground_s)),
        ],
        'residencePodium',
    )
    panel(ground_s, ground_n, depth, base, soffit, 'stone')
    solid(ground_s, ground_n, 0, depth, soffit - 0.20, soffit, 'gateTrim')
    for y in (ground_s, ground_n):
        face(
            [(y, 0, base), (y, depth, base), (y, depth, soffit), (y, 0, soffit)][
                :: 1 if y == ground_s else -1
            ],
            'stone',
        )
    pitch = (ground_n - ground_s) / 3
    for k in range(4):
        y = ground_s + k * pitch
        solid(y - 0.25, y + 0.25, -0.02, 0.60, base, soffit - 0.20, 'bridgeConcrete')
    for k in range(3):
        left, right = ground_s + k * pitch, ground_s + (k + 1) * pitch
        panel(left + 0.55, right - 0.55, depth - 0.04, 0.55, 2.86, 'dark')
        for j in range(13):
            y = left + 0.7 + j * (pitch - 1.4) / 12
            solid(y - 0.065, y + 0.065, depth - 0.24, depth - 0.09, 0.55, 2.86, 'stone')
        for h in (0.45, 0.95):
            mesh.line(
                point(left + 0.25, 0.58, deck(left + 0.25) + h),
                point(right - 0.25, 0.58, deck(right - 0.25) + h),
                0.035,
                C['lampMetal'],
            )
        for j in range(1, 5):
            y = left + j * pitch / 5
            solid(
                y - 0.024, y + 0.024, 0.55, 0.61, deck(y), deck(y) + 0.96, 'lampMetal'
            )

    # The banner shows a full-height slot before the pale south jamb. In the
    # upward view (15244) its end wall is recessed, with an occupied wing
    # beyond. Leave the north return open to the portal, not to the labs.
    bay_start = SOUTH_FRAME_BAY
    # Frontal photo 14611 shows sky left of the courtyard-side glazed cheek.
    # Keep both end walls and the base, opening only the overlapping lightwell.
    for lo, hi in ((bay_start, slot_s), (slot_n, south)):
        panel(lo, hi, FRAME_DEPTH, 2.74, floor - 0.18, 'stone')
    panel(slot_s, slot_n, FRAME_DEPTH, 2.74, 4.10, 'stone')
    for y in (slot_s, slot_n):
        back = wall_x(outer, y) - wall_x(inner, y)
        face(
            [
                (y, FRAME_DEPTH, 4.10),
                (y, back, 4.10),
                (y, back, floor - 0.18),
                (y, FRAME_DEPTH, floor - 0.18),
            ][:: 1 if y == slot_s else -1],
            'huicuiFrame',
        )
    back_s = wall_x(outer, slot_s) - wall_x(inner, slot_s)
    back_n = wall_x(outer, slot_n) - wall_x(inner, slot_n)
    # Court-facing rail and continuation of the terrace, below the sky ray.
    solid(
        slot_s, slot_n, FRAME_DEPTH, min(back_s, back_n), 3.77, 4.10, 'residencePodium'
    )
    mesh.line(
        point(slot_s, back_s - 0.08, 5.09),
        point(slot_n, back_n - 0.08, 5.09),
        0.04,
        C['lampMetal'],
    )
    for y in (slot_s + 0.10, (slot_s + slot_n) / 2, slot_n - 0.10):
        d = wall_x(outer, y) - wall_x(inner, y) - 0.08
        solid(y - 0.035, y + 0.035, d - 0.03, d + 0.03, 4.10, 5.09, 'lampMetal')
    face(
        [
            (slot_s, back_s, floor - 0.18),
            (slot_n, back_n, floor - 0.18),
            (slot_n, FRAME_DEPTH, floor - 0.18),
            (slot_s, FRAME_DEPTH, floor - 0.18),
        ],
        'gateTrim',
    )

    face(
        [
            (bay_start, 0, 2.74),
            (bay_start, FRAME_DEPTH, 2.74),
            (bay_start, FRAME_DEPTH, floor - 0.18),
            (bay_start, 0, floor - 0.18),
        ],
        'huicuiFrame',
    )
    for h in (5.05, 8.35, 11.65):
        # The dark window strip turns onto the north cheek, leaving the
        # white sightline clear from the street as well as from the court.
        solid(
            slot_n + 0.12,
            south - 0.17,
            FRAME_DEPTH - 0.12,
            FRAME_DEPTH - 0.04,
            h - 0.94,
            h + 0.94,
            'residenceGlass',
        )
        solid(
            slot_n - 0.07,
            slot_n,
            FRAME_DEPTH + 0.22,
            back_n - 0.27,
            max(4.18, h - 0.94),
            h + 0.94,
            'residenceGlass',
        )
    # Cap the retained lower volume, then seat the side platform flush with
    # the existing ninth return tread. Keep the flight's full width clear.
    face(
        [
            (bay_start, 0, 2.74),
            (south, 0, 2.74),
            (south, FRAME_DEPTH, 2.74),
            (bay_start, FRAME_DEPTH, 2.74),
        ],
        'residencePodium',
    )
    # Open shared landings at the stair portal and one bay over the south
    # lightwell. The intermediate wing and the dark south-end glazing remain.
    zones = (
        (a, light_s, GALLERY_DEPTH),
        (light_s, light_n, GALLERY_DEPTH),
        (light_n, SOUTH_ROOM_END, GALLERY_DEPTH),
        (SOUTH_ROOM_END, south, SHARED_DEPTH),
        (north, NORTH_ROOM_START, SHARED_DEPTH),
        (NORTH_ROOM_START, b_end, GALLERY_DEPTH),
    )
    for y0, y1, depth in zones:
        common = depth == SHARED_DEPTH
        through = y0 == light_s
        if not through:
            panel(y0, y1, depth, floor, lid, 'huicuiFrame' if common else 'stone')
        for h in (floor, lid + 0.18):
            solid(y0, y1, 0, depth, h - 0.18, h, 'gateTrim')
        # Keep a solid edge in the lab stretches. The widened common landings
        # have a low kerb, projecting slab edge and an open post-and-rail face.
        curb_top = floor + (0.20 if common else 0.66)
        solid(y0, y1, 0, 0.16, floor, curb_top, 'gateStone')
        solid(y0, y1, 0.05, 0.11, floor + 0.90, floor + 0.96, 'lampMetal')
        if common:
            solid(y0, y1, 0.055, 0.10, floor + 0.52, floor + 0.56, 'lampMetal')
        n = 1 if through else max(2, round((y1 - y0) / 6.8))
        for i in range(n):
            left, right = y0 + i * (y1 - y0) / n, y0 + (i + 1) * (y1 - y0) / n
            if not through:
                sill = floor + (0.16 if common else 0.40)
                solid(
                    left + 0.42,
                    right - 0.42,
                    depth - 0.10,
                    depth - 0.04,
                    sill,
                    lid - 0.25,
                    'residenceGlass',
                )
                y = 0.5 * (left + right)
                solid(
                    y - 0.05,
                    y + 0.05,
                    depth - 0.13,
                    depth - 0.10,
                    sill,
                    lid - 0.25,
                    'libraryMullion',
                )
            posts = 3 if common else 1
            for j in range(posts):
                post_y = left + (j + 0.5) * (right - left) / posts
                solid(
                    post_y - 0.035,
                    post_y + 0.035,
                    0.04,
                    0.12,
                    curb_top,
                    floor + 0.90,
                    'lampMetal',
                )
        # The edge piers meet the occupied levels above and below.
        for i in range(n + (y1 in (south, b_end))):
            y = y0 + i * (y1 - y0) / n
            solid(y - 0.24, y + 0.24, 0.13, 0.72, floor, lid, 'bridgeConcrete')
    # The floor and soffit of the transverse bay extend to the actual inner
    # facade, with only a guard across the open edge above the planted court.
    back_s = wall_x(outer, light_s) - wall_x(facades[2], light_s)
    back_n = wall_x(outer, light_n) - wall_x(facades[2], light_n)
    ring = [
        (light_s, GALLERY_DEPTH),
        (light_n, GALLERY_DEPTH),
        (light_n, back_n),
        (light_s, back_s),
    ]
    for h in (floor, lid + 0.18):
        face([(y, d, h) for y, d in ring], 'gateTrim')
        face([(y, d, h - 0.18) for y, d in reversed(ring)], 'gateTrim')
        face(
            [
                (light_s, back_s, h - 0.18),
                (light_s, back_s, h),
                (light_n, back_n, h),
                (light_n, back_n, h - 0.18),
            ],
            'gateStone',
        )
    for y, back in ((light_s, back_s), (light_n, back_n)):
        face(
            [
                (y, GALLERY_DEPTH, floor),
                (y, back, floor),
                (y, back, lid),
                (y, GALLERY_DEPTH, lid),
            ][:: 1 if y == light_s else -1],
            'stone',
        )
    for h in (0.48, 0.98):
        mesh.line(
            point(light_s, back_s - 0.12, floor + h),
            point(light_n, back_n - 0.12, floor + h),
            0.04,
            C['lampMetal'],
        )
    for i in range(5):
        y = light_s + i * (light_n - light_s) / 4
        d = wall_x(outer, y) - wall_x(facades[2], y) - 0.12
        solid(y - 0.035, y + 0.035, d - 0.035, d + 0.035, floor, floor + 1, 'lampMetal')
    # A recess in the south end wall is visible down the shared gallery (14485).
    # The threshold returns to a closed glazed entry inside the wing.
    y = SOUTH_ROOM_END
    for d0, d1, lo, hi in (
        (GALLERY_DEPTH, 4.1, floor, lid),
        (5.85, SHARED_DEPTH, floor, lid),
        (4.1, 5.85, floor + 2.45, lid),
    ):
        face([(y, d0, lo), (y, d1, lo), (y, d1, hi), (y, d0, hi)], 'stone')
    solid(y - 1.20, y, 4.10, 5.85, floor - 0.18, floor, 'residencePodium')
    solid(y - 1.20, y, 4.10, 5.85, floor + 2.45, floor + 2.60, 'gateTrim')
    for d in (4.10, 5.85):
        panel(y - 1.20, y, d, floor, floor + 2.45, 'stone')
    solid(y - 1.24, y - 1.20, 4.10, 5.85, floor, floor + 2.45, 'residenceGlass')
    y = NORTH_ROOM_START
    face(
        [
            (y, d, h)
            for d, h in (
                (GALLERY_DEPTH, lid),
                (SHARED_DEPTH, lid),
                (SHARED_DEPTH, floor),
                (GALLERY_DEPTH, floor),
            )
        ],
        'stone',
    )
    for y in (a, b_end):
        face(
            [
                (y, 0, floor - 0.18),
                (y, GALLERY_DEPTH, floor - 0.18),
                (y, GALLERY_DEPTH, lid),
                (y, 0, lid),
            ][:: 1 if y == a else -1],
            'stone',
        )

    # Through the portal the upper occupied volume has a coffered underside.
    # The accessible bridge runs N/S, much narrower than the cantilever.
    for y in (south, north):
        back = wall_x(outer, y) - wall_x(inner, y)

        def reveal(d0, d1, h0, h1):
            face(
                [(y, d0, h0), (y, d1, h0), (y, d1, h1), (y, d0, h1)][
                    :: 1 if y == south else -1
                ],
                'gateStone',
            )

        if y == south:
            reveal(0, back, -0.12, 2.74)
            reveal(FRAME_DEPTH, back, 2.74, floor - 0.18)
        else:
            reveal(0, back, -0.12, floor - 0.18)
        reveal(SHARED_DEPTH, back, floor - 0.18, lid)
    inner_s = wall_x(outer, south) - wall_x(inner, south)
    inner_n = wall_x(outer, north) - wall_x(inner, north)
    face(
        [
            (south, inner_s, lid),
            (north, inner_n, lid),
            (north, 0, lid),
            (south, 0, lid),
        ],
        'gateTrim',
    )
    # The bridge flares into both landings while leaving light slots to its
    # east and west. Shared end sections are accessible at the same level.
    profile = (
        (south, 0.65, SHARED_DEPTH),
        (south + 2.5, BRIDGE_FRONT, BRIDGE_BACK),
        (north - 2.5, BRIDGE_FRONT, BRIDGE_BACK),
        (north, 0.65, SHARED_DEPTH),
    )
    bridge_glass = glass_material(C)
    for (y0, d0, b0), (y1, d1, b1) in zip(profile, profile[1:]):
        ring = [(y0, d0), (y1, d1), (y1, b1), (y0, b0)]
        face([(y, d, floor) for y, d in ring], 'residencePodium')
        face([(y, d, floor - 0.48) for y, d in reversed(ring)], 'residencePodium')
        for depth0, depth1, reverse in ((d0, d1, False), (b0, b1, True)):
            edge = [
                (y0, depth0, floor - 0.48),
                (y1, depth1, floor - 0.48),
                (y1, depth1, floor),
                (y0, depth0, floor),
            ]
            face(edge[::-1] if reverse else edge, 'huicuiFrame')
            mesh.face(
                [
                    point(y0, depth0, floor + 0.14),
                    point(y1, depth1, floor + 0.14),
                    point(y1, depth1, floor + 0.94),
                    point(y0, depth0, floor + 0.94),
                ][:: -1 if reverse else 1],
                bridge_glass,
            )
            mesh.line(
                point(y0, depth0, floor + 1.01),
                point(y1, depth1, floor + 1.01),
                0.045,
                C['lampMetal'],
            )
            post_count = round((y1 - y0) / 1.7)
            for j in range(post_count):
                t = j / post_count
                y = y0 + t * (y1 - y0)
                d = depth0 + t * (depth1 - depth0)
                solid(
                    y - 0.035,
                    y + 0.035,
                    d - 0.035,
                    d + 0.035,
                    floor,
                    floor + 1.01,
                    'lampMetal',
                )
    for y in (south + 0.34, north - 0.34):
        solid(
            y - 0.30,
            y + 0.30,
            BRIDGE_BACK - 0.54,
            BRIDGE_BACK + 0.08,
            -1.45,
            lid,
            'bridgeConcrete',
        )
    # The street lip overhangs the bridge; the longitudinal ribs land on the
    # side supports. The light coffers remain visible between the deeper ribs.
    solid(south, north, -1.38, 0, lid, 16.53, 'libraryTrim')
    solid(south, north, -1.38, -0.96, lid - 0.45, lid, 'libraryTrim')
    for i in range(1, 6):
        y = south + (north - south) * i / 6
        solid(
            y - 0.15,
            y + 0.15,
            -0.96,
            min(inner_s, inner_n),
            lid - 0.45,
            lid,
            'libraryTrim',
        )
    for d in (2.65, 5.20, 7.80):
        solid(south, north, d - 0.18, d + 0.18, lid - 0.52, lid, 'libraryTrim')

    north_court(mesh, z, C)
