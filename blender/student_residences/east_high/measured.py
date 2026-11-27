"""Street-facing window groups and the East 19 roof frame."""

from generic_buildings import facade_segments
from humanities_facades import finish as paint

from .wall import Wall, pocket, remove_fittings


def wall_section(mesh, surface, patch, remove, x0, x1, bottom, top):
    """Subtract the patch rectangle from each relevant original, even at paint breaks."""
    covered = 0.0
    for i, f in enumerate(mesh.f):
        if len(f) != 4:
            continue
        pts = [mesh.v[j] for j in f]
        coords = [surface.local(v) for v in pts]
        if max(abs(d) for _, d in coords) > 0.008:
            continue
        us = [u for u, _ in coords]
        if abs(min(us)) > 0.01 or abs(max(us) - surface.length) > 0.01:
            continue
        low, high = (
            min(element[2] for element in pts),
            max(element[2] for element in pts),
        )
        cut_bottom, cut_top = max(low, bottom), min(high, top)
        if high - low < 2 or cut_top - cut_bottom < 0.01:
            continue
        mat = mesh.m[i]
        surface.rect(patch, 0, surface.length, low, cut_bottom, 0, mat)
        surface.rect(patch, 0, surface.length, cut_top, high, 0, mat)
        surface.rect(patch, 0, x0, cut_bottom, cut_top, 0, mat)
        surface.rect(patch, x1, surface.length, cut_bottom, cut_top, 0, mat)
        remove.add(i)
        covered += cut_top - cut_bottom
    if abs(covered - (top - bottom)) > 0.02:
        raise ValueError(f'Locked shell coverage mismatch on {surface.a}: {covered}')


def window(surface, patch, left, right, low, high, lining, C, detail, style):
    depth = -0.19
    surface.reveal(patch, left, right, low, high, depth, lining)
    # Frame and glazing partition the same back plane, so they cannot flicker.
    # On the long north band the 186-degree image resolves several narrow lights.
    width = right - left
    leaves = (
        (9 if width > 5 else 2 if width > 1.25 else 1)
        if detail
        else (3 if width > 5 else 1)
    )
    transom = style == 'west_light' or (detail and surface.kind == 'peijia')
    glass = C['eastDormRecessGlass']
    metal = (
        paint(C, 'dormEast33DarkSash', (0.091, 0.099, 0.099), 0.65)
        if style in ('west_light', 'long_band')
        else C['eastDormWindowMetal']
    )
    edge = 0.045 if detail else 0.035
    surface.rect(patch, left, right, low, low + edge, depth, metal)
    surface.rect(patch, left, right, high - edge, high, depth, metal)
    levels = [(low + edge, high - edge)]
    if transom:
        joint = high - (0.4 if style == 'west_light' else 0.28) * (high - low)
        surface.rect(patch, left, right, joint - 0.025, joint + 0.025, depth, metal)
        levels = [(low + edge, joint - 0.025), (joint + 0.025, high - edge)]
    for a, b in levels:
        surface.rect(patch, left, left + edge, a, b, depth, metal)
        surface.rect(patch, right - edge, right, a, b, depth, metal)
        x = left + edge
        for k in range(1, leaves):
            axis = left + k * width / leaves
            surface.rect(patch, x, axis - 0.025, a, b, depth, glass)
            surface.rect(patch, axis - 0.025, axis + 0.025, a, b, depth, metal)
            x = axis + 0.025
        surface.rect(patch, x, right - edge, a, b, depth, glass)


def storey(
    patch,
    surface,
    left_end,
    right_end,
    floor,
    step,
    holes,
    wall,
    C,
    detail,
    red=False,
):
    """Tile the host around holes. All reveals terminate at a recessed exterior back."""
    cursor = left_end
    for left, right, lo, hi, style in holes:
        surface.rect(patch, cursor, left, floor, floor + step, 0, wall)
        surface.rect(patch, left, right, floor, lo, 0, wall)
        surface.rect(patch, left, right, hi, floor + step, 0, wall)
        lining = C['dormPeijiaIvory'] if red and style == 'loggia' else wall
        if style == 'loggia':
            pocket(
                surface,
                patch,
                left,
                right,
                lo,
                hi,
                1.06,
                lining,
                C['eastDormRecessGlass'],
                C['eastDormWindowMetal'],
                style,
                detail,
            )
        else:
            window(surface, patch, left, right, lo, hi, lining, C, detail, style)
        cursor = right
    surface.rect(patch, cursor, right_end, floor, floor + step, 0, wall)


def crown(surface, patch, left, right, roof, step, C):
    # 188° and 198° both show six openings over nine upper-storey bays.
    # A single extruded outline avoids intersecting beam/post solids.
    thick = 0.28
    pitch = (right - left - thick) / 6
    # Three internal cross-ribs per bay approximate the visible porous soffit.
    # The camera resolves the six front bays but not the exact depth or rib count.
    strips = [(left + j * pitch, left + j * pitch + thick, True) for j in range(7)]
    for j in range(6):
        for k in (1, 2, 3):
            mid = left + (j + k / 4) * pitch + thick / 2
            strips.append((mid - 0.057, mid + 0.057, False))
    xs = sorted({x for a, b, _ in strips for x in (a, b)})
    ds = [-2.50, -2.24, -0.64, -0.32]
    soffit = roof + 0.8 + 0.64 * step
    zs = [roof, soffit, soffit + 0.12, soffit + 0.27]
    cells = set()
    for i, (u, v) in enumerate(zip(xs, xs[1:])):
        mid = (u + v) / 2
        post = any(a <= mid <= b and main for a, b, main in strips)
        rib = any(a <= mid <= b for a, b, _ in strips)
        for j in range(3):
            for k in range(3):
                if (j in (0, 2) and (k > 0 or post)) or (j == 1 and rib and k == 2):
                    cells.add((i, j, k))
    # Emit just the boundary of the fascia, rear beam, piers and slats.
    # Coordinates are in outward-depth convention (larger d faces the street).
    for i, j, k in sorted(cells):
        u, v = xs[i : i + 2]
        a, b = ds[j : j + 2]
        lo, hi = zs[k : k + 2]
        if (i, j + 1, k) not in cells:
            surface.rect(patch, u, v, lo, hi, b, C['white'])
        if (i, j - 1, k) not in cells:
            surface.face(
                patch, [(v, a, lo), (u, a, lo), (u, a, hi), (v, a, hi)], C['white']
            )
        if (i + 1, j, k) not in cells:
            surface.face(
                patch, [(v, b, lo), (v, a, lo), (v, a, hi), (v, b, hi)], C['white']
            )
        if (i - 1, j, k) not in cells:
            surface.face(
                patch, [(u, a, lo), (u, b, lo), (u, b, hi), (u, a, hi)], C['white']
            )
        if (i, j, k + 1) not in cells:
            surface.face(
                patch, [(u, b, hi), (v, b, hi), (v, a, hi), (u, a, hi)], C['white']
            )
        if k and (i, j, k - 1) not in cells:
            surface.face(
                patch, [(v, b, lo), (u, b, lo), (u, a, lo), (v, a, lo)], C['white']
            )


def east19(b, z, C, detail, mesh, patch, discard):
    surface = Wall(facade_segments(b)[5], 'red_bays')
    h = b['form']['height']
    step = h / 7
    low = z + step
    roof = z + h
    wall_section(mesh, surface, patch, discard, 0, surface.length, low, roof)
    # The west return in the photograph has its own stacked openings and
    # occupies about one crown interval beyond the last roof post.
    stop = surface.length / 7
    start = stop + 0.07
    end = surface.length - 0.20
    pitch = (end - start) / 9
    for level in range(1, 7):
        floor = z + step * level
        mat = C['dormPeijiaIvory'] if level == 6 else C['dormPeijiaTerracotta']
        holes = [
            (
                0.25 * stop,
                0.73 * stop,
                floor + 0.26 * step,
                floor + 0.75 * step,
                'glass',
            )
        ]
        for j in range(9):
            mid = start + (j + 0.5) * pitch
            if j % 3 == 1:
                for delta in (-0.20, 0.20):
                    u = mid + delta * pitch
                    holes.append(
                        (
                            u - 0.105 * pitch,
                            u + 0.105 * pitch,
                            floor + 0.42 * step,
                            floor + 0.75 * step,
                            'glass',
                        )
                    )
            else:
                holes.append(
                    (
                        mid - 0.445 * pitch,
                        mid + 0.445 * pitch,
                        floor + 0.15,
                        floor + step - 0.24,
                        'loggia',
                    )
                )
        # Painted slab fascia is part of the wall surface, without overlays.
        surface.rect(
            patch, 0, surface.length, floor, floor + 0.14, 0, C['dormPeijiaIvory']
        )
        storey(
            patch,
            surface,
            0,
            surface.length,
            floor + 0.14,
            step - 0.14,
            holes,
            mat,
            C,
            detail,
            True,
        )
    crown(surface, patch, start, end, roof, step, C)


def east21(b, z, C, detail, mesh, patch, discard):
    surface = Wall(facade_segments(b)[15], 'peijia')
    heights = b['form']['height']
    step = heights / 7
    # Limit the extension to the visible eastern portion, ending between
    # existing pairs of axes at a whole multiple of the original grid.
    length = 8 * surface.length / int(surface.length / 4)
    pitch = length / 4
    wall_section(mesh, surface, patch, discard, 0, length, z + step, z + heights)
    remove_fittings(
        mesh,
        surface,
        discard,
        '04_立面窗格',
        0,
        length,
        z + step,
        z + heights,
        -0.25,
        1.6,
    )
    for level in range(1, 7):
        floor = z + level * step
        mat = C['dormPeijiaIvory'] if level == 6 else C['dormPeijiaTerracotta']
        holes = []
        for j in range(4):
            for frac, narrow in (
                (0.16, False),
                (0.40, True),
                (0.60, True),
                (0.84, False),
            ):
                u = (j + frac) * pitch
                width = pitch * (0.077 if narrow else 0.205)
                hh = step * (0.254 if narrow else 0.51)
                head = floor + 0.78 * step
                holes.append((u - width / 2, u + width / 2, head - hh, head, 'glass'))
        storey(patch, surface, 0, length, floor, step, holes, mat, C, detail)


def east33(b, z, C, detail, mesh, patch, discard):
    surface = Wall(facade_segments(b)[3], 'ribbon')
    pitch = surface.length / 12
    left, right = 5 * pitch, 7 * pitch
    step = 3.13
    wall_section(mesh, surface, patch, discard, left, right, z + step, z + 7 * step)
    for level in range(1, 7):
        floor = z + level * step
        holes = []
        # The 186° station resolves the narrow west light next to the long band.
        # The 150° station resolves the pair to its east.
        for u, width, tall, style in [
            (51.90, 0.85, 0.30, 'west_light'),
            (56.75, 7.50, 0.495, 'long_band'),
            (62.8, 1.53, 0.30, 'glass'),
            (65.87, 1.59, 0.30, 'glass'),
        ]:
            holes.append(
                (
                    u - width / 2,
                    u + width / 2,
                    floor + (0.74 - tall) * step,
                    floor + 0.74 * step,
                    style if level in (1, 2) else 'glass',
                )
            )
        storey(
            patch,
            surface,
            left,
            right,
            floor,
            step,
            holes,
            C['dormXingjianOffWhite'],
            C,
            detail,
        )
