"""Recesses, spandrels and masonry finishes on the remaining residence elevations."""

from generic_buildings import facade_segments
from geometry import Mesh
from humanities_facades import finish as paint

from .measured import east19, east21, east33
from .sections import PLANS
from .wall import Wall, discard_faces, pocket, remove_fittings


def _bays(surface):
    kind = surface.kind
    length = surface.length
    if kind == 'east27_end':
        return [
            (length * (c - d / 2), length * (c + d / 2), 'glass')
            for c, d in ((0.17, 0.048), (0.495, 0.258), (0.805, 0.048))
        ]
    if kind == 'slot':
        return [(length * 0.425, length * 0.575, 'loggia')]
    pitch = {
        'red_bays': 4.25,
        'peijia': 3.95,
        'paired': 4.30,
        'east27': 3.55,
        'mixed': 4.10,
        'ribbon': 7.7,
    }[kind]
    count = max(1, round(length / pitch))
    pitch = length / count
    out = []
    for j in range(count):
        mid = pitch * (j + 0.5)
        if kind == 'paired':
            out.extend(
                [
                    (mid - 0.38 * pitch, mid + 0.08 * pitch, 'glass'),
                    (mid + 0.24 * pitch, mid + 0.37 * pitch, 'small'),
                ]
            )
            continue
        west_fraction = mid / length if surface.t[0] > 0 else 1 - mid / length
        loggia = (
            kind in ('red_bays', 'mixed')
            and j % 3 != 1
            and surface.loggia_range[0] <= west_fraction <= surface.loggia_range[1]
        )
        width = (
            0.84
            if loggia
            else 0.72
            if kind == 'ribbon' and j % 3 != 0
            else 0.50
            if kind == 'ribbon'
            else 0.58
        )
        out.append(
            (
                mid - pitch * width / 2,
                mid + pitch * width / 2,
                'loggia' if loggia else 'glass',
            )
        )
    return out


def _elevation(
    surface, patch, left, right, bottom, top, wallmat, levels, z, colors, detail
):
    base, trim, glass, frame, ivory = colors
    if surface.kind == 'pier':
        step = (top - z) / levels
        surface.rect(patch, left, right, bottom, z + step, 0, base)
        cursor = z + step
        for i in range(1, levels):
            hi = z + i * step + 0.054
            # Inset mortar joint occupies its own section of the host wall.
            surface.face(
                patch,
                [
                    (left, 0, cursor),
                    (right, 0, cursor),
                    (right, -0.018, cursor),
                    (left, -0.018, cursor),
                ],
                trim,
            )
            surface.rect(patch, left, right, cursor, hi, -0.018, trim)
            surface.face(
                patch,
                [
                    (right, 0, hi),
                    (left, 0, hi),
                    (left, -0.018, hi),
                    (right, -0.018, hi),
                ],
                trim,
            )
            cursor = z + (i + 1) * step
            surface.rect(patch, left, right, hi, cursor, 0, wallmat)
        return
    step = (top - (bottom if surface.kind.startswith('east27') else z)) / levels
    first = bottom if surface.kind.startswith('east27') else z + step
    surface.rect(
        patch,
        left,
        right,
        bottom,
        first,
        0,
        base if surface.kind == 'slot' else wallmat,
    )
    bays = _bays(surface)
    count = levels if surface.kind.startswith('east27') else levels - 1
    for k in range(count):
        floor = first + k * step
        paintmat = ivory if surface.kind == 'peijia' and k == count - 1 else wallmat
        # Keep solid masonry between individual openings, including at corners.
        panel_bottom = floor
        if surface.kind in ('peijia', 'red_bays'):
            courses = (
                [(0.075, ivory), (0.12, paintmat), (0.05, ivory)]
                if surface.kind == 'peijia'
                else [(0.085, ivory)]
            )
            for height, material in courses:
                surface.rect(
                    patch, left, right, panel_bottom, panel_bottom + height, 0, material
                )
                panel_bottom += height
        if surface.kind == 'slot':
            for height, material in ((0.04, trim), (0.14, wallmat), (0.034, trim)):
                for pier_left, pier_right in ((left, bays[0][0]), (bays[0][1], right)):
                    surface.rect(
                        patch,
                        pier_left,
                        pier_right,
                        panel_bottom,
                        panel_bottom + height,
                        0,
                        material,
                    )
                panel_bottom += height
        cursor = left
        for bay_left, bay_right, kind in bays:
            if kind == 'small':
                lo, hi = floor + 0.47 * step, floor + 0.72 * step
            elif kind == 'loggia':
                lo, hi = floor + 0.10, floor + step - 0.25
            else:
                lo, hi = floor + 0.25 * step, floor + 0.74 * step
            surface.rect(
                patch, cursor, bay_left, panel_bottom, floor + step, 0, paintmat
            )
            surface.rect(
                patch,
                bay_left,
                bay_right,
                floor if surface.kind == 'slot' else panel_bottom,
                lo,
                0,
                paintmat,
            )
            surface.rect(patch, bay_left, bay_right, hi, floor + step, 0, paintmat)
            pocket(
                surface,
                patch,
                bay_left,
                bay_right,
                lo,
                hi,
                0.96 if kind == 'loggia' else 0.22,
                ivory if surface.kind == 'red_bays' and kind == 'loggia' else paintmat,
                glass,
                frame,
                kind,
                detail,
            )
            cursor = bay_right
        surface.rect(patch, cursor, right, panel_bottom, floor + step, 0, paintmat)


def finish_elevations(b, z, C, detail, mesh, n):
    levels, plan = PLANS[n]
    edges = facade_segments(b)
    # Restrict the inferred open bays to the portions supported by the
    # opposite facade. Fractions are measured west to east.
    loggia_range = {
        29: (0, 0.46),
        30: (0, 0.67),
        34: (0.69, 1),
        35: (0.55, 1),
    }.get(n, (0, 1))
    walls = [Wall(edges[i], kind, loggia_range) for i, kind in plan.items()]
    patch = Mesh()
    discard = set()
    colors = (
        paint(C, 'eastDormStonePlinth', (0.42, 0.418, 0.374), 0.91),
        paint(C, 'eastDormMortarJoint', (0.44, 0.426, 0.38), 0.92),
        paint(C, 'eastDormRecessGlass', (0.106, 0.149, 0.164), 0.45),
        paint(C, 'eastDormWindowMetal', (0.45, 0.452, 0.425), 0.65),
        paint(C, 'dormPeijiaIvory', (0.76, 0.70, 0.60), 0.88),
    )
    for i, face in enumerate(mesh.f):
        if len(face) != 4:
            continue
        vs = [mesh.v[j] for j in face]
        bottom, top = vs[0][2], vs[2][2]
        if (
            top - bottom < 12
            or abs(vs[1][2] - bottom) > 0.002
            or abs(vs[3][2] - top) > 0.002
        ):
            continue
        for surface in walls:
            loc = [surface.local(v) for v in vs]
            if surface.kind == 'pier' and all(abs(d + 0.96) < 0.015 for _, d in loc):
                # The old notch uses the outer-wall paint on its sheltered
                # return. Only the recessed back is a darker neutral finish.
                us = [u for u, _ in loc]
                if min(us) > 0.24 * surface.length and max(us) < 0.76 * surface.length:
                    mesh.m[i] = paint(
                        C, 'eastDormGalleryBacking', (0.238, 0.236, 0.212), 0.92
                    )
                continue
            if any(abs(d) > 0.015 for _, d in loc):
                continue
            left, right = sorted([loc[0][0], loc[1][0]])
            if left < -0.02 or right > surface.length + 0.02 or right - left < 1:
                continue
            if surface.kind != 'pier' and (
                abs(left) > 0.02 or abs(right - surface.length) > 0.02
            ):
                continue
            surface.host.append((i, left, right, bottom, top))
            discard.add(i)
            _elevation(
                surface,
                patch,
                left,
                right,
                bottom,
                top,
                mesh.m[i],
                levels,
                z,
                colors,
                detail,
            )
            break
    for surface in walls:
        if not surface.host:
            raise ValueError(
                f'Missing locked wall in {b["id"]} at {surface.a} ({surface.kind})'
            )

    if n == 27 and detail:
        # The independently generated dining block shares its fittings part
        # between ground floor and upper wings; retain the entire ground floor.
        for wall in walls:
            _, _, _, bottom, top = wall.host[0]
            remove_fittings(
                mesh,
                wall,
                discard,
                '04_供餐窗与桌椅',
                0.005,
                wall.length - 0.005,
                bottom - 0.08,
                top - 0.001,
                -0.32,
                2.0,
            )
    measured = Mesh()
    if n in (19, 20, 33):
        {19: east19, 20: east21, 33: east33}[n](
            b, z, C, detail, mesh, measured, discard
        )
    discard_faces(mesh, discard)
    mesh.add_part('东区宿舍二次立面', patch)
    if measured.v:
        mesh.add_part('照片校准的住宿外立面', measured)
    return mesh
