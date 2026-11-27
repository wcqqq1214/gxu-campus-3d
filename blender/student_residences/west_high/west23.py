"""West 23 brick elevations and exterior equipment on the eastern south bays."""

from geometry import Mesh

from .walls import (
    _attic,
    _glazing,
    _panel_course,
    _range,
    _remove_faces,
    _Wall,
    finish_material,
    local_texture,
)


def _profile(m, w, lo, levels, mat):
    """Open-backed course, drawn with one outward face per change in profile."""
    for (za, da), (zb, db) in zip(levels, levels[1:]):
        if abs(zb - za) > 0.0001 and abs(da - db) < 0.0001:
            w.face(m, 0, w.width, lo + za, lo + zb, mat, da)
        else:
            p = [
                w.point(0, lo + za, da),
                w.point(w.width, lo + za, da),
                w.point(w.width, lo + zb, db),
                w.point(0, lo + zb, db),
            ]
            m.face(p, mat)

    for u in (0, w.width):
        ring = [w.point(u, lo + v, depth) for v, depth in levels]
        m.face(ring if u == 0 else ring[::-1], mat)


def _bay_window(part, w, x0, x1, z0, z1, mat, deep, screen, detail):
    d = -0.37 if deep else -0.218
    w.cross_section(part, x0, x1, z0, z1, d, mat['jamb'])
    if deep:
        w.face(part, x0, x1, z0, z1, mat['shadow'], d)
        w.ledge(part, x0, x1, z0 + 0.20, z0 + 0.245, -0.23, -0.16, mat['rail'])
        return
    # Recessed glazing behind discrete rails; the cross rail is attached to both jambs.
    edge = 0.038
    for left, right, bottom, top in [
        (x0, x0 + edge, z0, z1),
        (x1 - edge, x1, z0, z1),
        (x0 + edge, x1 - edge, z0, z0 + edge),
        (x0 + edge, x1 - edge, z1 - edge, z1),
    ]:
        w.face(part, left, right, bottom, top, mat['frame'], d)
    mid = (x0 + x1) / 2
    for left, right, finish in (
        (x0 + edge, mid - 0.018, mat['glass']),
        (mid - 0.018, mid + 0.018, mat['frame']),
        (mid + 0.018, x1 - edge, mat['glass']),
    ):
        w.face(part, left, right, z0 + edge, z1 - edge, finish, d)
    if screen:
        # Eleven verticals are individually resolvable in both lower rows at the sampled bay.
        n = 11 if detail else 5
        for j in range(1, n + 1):
            cx = x0 + (x1 - x0) * j / (n + 1)
            w.face(part, cx - 0.009, cx + 0.009, z0, z1, mat['rail'], -0.092)
        w.ledge(
            part,
            x0,
            x1,
            z0 + (z1 - z0) * 0.49,
            z0 + (z1 - z0) * 0.49 + 0.026,
            -0.094,
            -0.072,
            mat['rail'],
        )


def _condenser(m, w, axis, base, mat, detail):
    bottom = base + 0.53
    top = bottom + 0.65
    inner, outer = 0.13, 0.622
    half = 0.40
    # Steel brackets run from masonry to the underside. The shell is separate from the sill.
    for dx in (-0.275, 0.275) if detail else (0,):
        u = axis + dx
        m.line(
            w.point(u, bottom - 0.28, 0),
            w.point(u, bottom, outer - 0.065),
            0.030 if detail else 0.048,
            mat['bracket'],
            6,
        )
        m.line(
            w.point(u, bottom - 0.04, 0),
            w.point(u, bottom - 0.02, outer - 0.04),
            0.027,
            mat['bracket'],
            6,
        )
    w.ledge(
        m, axis - half, axis + half, bottom, top, inner, outer, mat['case'], mat['fan']
    )
    # A rear face closes the housing; it stands clear of the wall on the brackets.
    m.face(
        [
            w.point(axis - half, bottom, inner),
            w.point(axis - half, top, inner),
            w.point(axis + half, top, inner),
            w.point(axis + half, bottom, inner),
        ],
        mat['case'],
    )


def _south_wall(b, z, C, detail, mesh, w, cladding):
    mat = dict(
        brick=cladding['brick'],
        top=cladding['top'],
        base=cladding['base'],
        glass=cladding['glass'],
        rail=finish_material(C, 'West23GalvanizedRail', (0.245, 0.255, 0.235)),
        frame=finish_material(C, 'West23RecessFrame', (0.19, 0.205, 0.20)),
        jamb=finish_material(C, 'West23BrickReveal', (0.26, 0.144, 0.105)),
        shadow=finish_material(C, 'West23GalleryShadow', (0.064, 0.067, 0.061)),
        bracket=finish_material(C, 'West23BracketGrey', (0.12, 0.126, 0.12)),
        case=finish_material(C, 'West23CaseGrey', (0.376, 0.37, 0.35)),
    )
    if detail:
        mat['tile'] = local_texture(
            C, 'West23GreyWhiteBond', (0.48, 0.48, 0.46), 'bond.png'
        )
        mat['edge'] = local_texture(
            C, 'West23LinedCornice', (0.51, 0.50, 0.48), 'course.png'
        )
        mat['fan'] = local_texture(
            C, 'West23DocumentedIntake', (0.43, 0.435, 0.42), 'condenser-grey.png'
        )
    else:
        mat['fan'] = local_texture(
            C, 'West23GreyIntakeLOD', (0.43, 0.435, 0.42), 'condenser-far.png'
        )
        mat['tile'] = finish_material(C, 'West23GreyWhiteDistant', (0.50, 0.50, 0.475))
        mat['edge'] = finish_material(C, 'West23CorniceDistant', (0.55, 0.54, 0.515))
    pitch = (b['height'] - 3.53) / 7
    centres = [(w.width - 19 * 6.5) / 2 + i * 6.5 for i in range(20)]
    p = Mesh()
    for level in range(8):
        base = -0.08 if level == 0 else 3.53 + (level - 1) * pitch
        top = 3.53 if level == 0 else 3.53 + level * pitch
        band = 0.38 if not level else (0.26 if level <= 2 else 0.185)
        if level == 0:
            w.face(p, 0, w.width, base, base + band, mat['base'])
        elif level <= 2:
            _profile(
                p,
                w,
                base,
                [
                    (0, 0),
                    (0.035, 0.08),
                    (0.08, 0.08),
                    (0.08, 0.14),
                    (0.205, 0.14),
                    (0.26, 0.10),
                    (0.26, 0),
                ],
                mat['edge'],
            )
        else:
            _profile(
                p,
                w,
                base,
                [(0, 0), (0, 0.027), (0.185, 0.027), (0.185, 0)],
                mat['tile'],
            )
        field = mat['top'] if level == 7 else mat['brick']
        start = 0.0
        for c in centres:
            east = w.width - 28 < c < w.width - 2
            if not level:
                holes = [(c, 2.70, 0.84, 2.32, False)]
            else:
                big = 1.51 if east else 1.45
                little = 0.76 if east else 0.82
                holes = sorted(
                    [
                        (
                            c + t,
                            big,
                            base + (1.035 if east else 0.91),
                            base + (2.65 if east else 2.49),
                            True,
                        )
                        for t in (-0.88, 0.88)
                    ]
                    + [
                        (
                            c + t,
                            little,
                            base + (1.77 if east else 1.72),
                            base + (2.52 if east else 2.46),
                            False,
                        )
                        for t in (-2.37, 2.37)
                    ]
                )
            for mid, width, bot, head, is_big in holes:
                l = mid - width / 2
                r = mid + width / 2
                w.face(p, start, l, base + band, top, field)
                w.face(p, l, r, base + band, bot, field)
                w.face(p, l, r, head, top, field)
                if east and level:
                    _bay_window(
                        p,
                        w,
                        l,
                        r,
                        bot,
                        head,
                        mat,
                        is_big and level >= 3,
                        is_big and level <= 2,
                        detail,
                    )
                else:
                    _glazing(
                        p,
                        w,
                        l,
                        r,
                        bot,
                        head,
                        cladding,
                        detail,
                    )
                start = r
            if level:
                # Separate actually bonded, lightly projecting tiled ribs from the condenser finish.
                w.ledge(
                    p, c - 0.123, c + 0.123, base + band, top, 0, 0.056, mat['tile']
                )
                if east:
                    for dx in (-0.615, 0.615):
                        _condenser(p, w, c + dx, base, mat, detail)
        w.face(p, start, w.width, base + band, top, field)
    u = centres[-2] - 0.475 * 6.5
    low, high = 0.47, b['height'] - 0.13
    x, y, _ = w.point(u, 0, 0.153)
    p.cylinder(
        x,
        y,
        z + (low + high) / 2,
        0.077,
        high - low,
        mat['case'],
        n=12 if detail else 6,
    )
    for i in range(1, 8, 1 if detail else 2):
        h = 3.53 + (i - 1) * pitch + 0.35
        w.ledge(p, u - 0.045, u + 0.045, h - 0.04, h + 0.04, 0, 0.086, mat['bracket'])
        p.cylinder(x, y, z + h, 0.085, 0.048, mat['bracket'], n=12 if detail else 6)
    mesh.add_part('西23南墙东段标定', p)


def west23(b, z, C, detail, mesh, mats):
    x0, _, x1, yn = b['bounds']
    south = yn - 15.32
    north_end = yn - 1.65
    walls = [
        _Wall((x0, south), (x1, south), z),
        _Wall((x1, south), (x1, north_end), z),
        _Wall((x0, north_end), (x0, south), z),
    ]
    lo, hi = _range(mesh, '01_')
    replaced = set()
    for i, f in enumerate(mesh.f):
        pts = [mesh.v[k] for k in f]
        # The north block has a second full-length sheet behind the south facade.
        inside = (
            len(f) == 4
            and max(p[0] for p in pts) - min(p[0] for p in pts) > 100
            and max(abs(walls[0].uv_depth(p)[1] + 0.20) for p in pts) < 0.0001
        )
        if inside or (
            lo <= f[0] < hi
            and max(p[2] for p in pts) - min(p[2] for p in pts) > 0.4
            and any(
                max(abs(w.uv_depth(p)[1]) for p in pts) < 0.0001
                and max(w.uv_depth(p)[0] for p in pts)
                - min(w.uv_depth(p)[0] for p in pts)
                > 0.5
                for w in walls
            )
        ):
            replaced.add(i)
    _remove_faces(mesh, replaced)
    _attic(mesh, z + b['height'] - b['height'] / b['levels'] + 0.1, mats['chalk'])
    suffix = '' if detail else '-base'
    mat = {
        k: C['w23-' + v + suffix]
        for k, v in [
            ('brick', 'face-brick'),
            ('sill', 'tile'),
            ('frame', 'aluminium'),
            ('reveal', 'soffit'),
            ('base', 'dark-red-skirting'),
        ]
    }
    mat['glass'] = finish_material(
        C, 'West23_outer_window_glass', (0.076, 0.092, 0.092)
    )
    mat['top'] = mats['chalk']
    floor = (b['height'] - 3.53) / 7
    for j, w in enumerate(walls[1:]):
        part = Mesh()
        for level in range(8):
            base = -0.08 if not level else 3.53 + (level - 1) * floor
            top = 3.53 + level * floor
            wall = mat['top'] if level == 7 else mat['brick']
            band = 0.38 if level == 0 else (0.21 if level <= 2 else 0.15)
            if level == 0:
                w.face(part, 0, w.width, base, base + band, mat['base'])
            else:
                w.ledge(
                    part,
                    0,
                    w.width,
                    base,
                    base + band,
                    0,
                    0.10 if level <= 2 else 0.045,
                    mat['sill'],
                )
            pos = (0.28, 0.50, 0.72) if j == 0 else (0.26, 0.49, 0.70)
            if level == 0:
                pos = (0.40, 0.68) if j == 0 else (0.42, 0.66)
            holes = [
                (t * w.width, 2.05 if level else 1.84, base + 1.0, base + 2.49)
                for t in pos
            ]
            _panel_course(part, w, base + band, top, holes, wall, mat, detail)
        mesh.add_part(('西23东山墙窗组', '西23西山墙窗组')[j], part)
    _south_wall(b, z, C, detail, mesh, walls[0], mat)
    return mesh
