"""Photo-derived framed glass guards, scoped to the materials entry."""

import math

from geometry import MATERIALS, material


def glass_material(C):
    if 'entryGuardGlass' not in C:
        C['entryGuardGlass'] = material(
            'entryGuardGlass', (0.29, 0.40, 0.40), 0.3, 0.05
        )
        m = MATERIALS[C['entryGuardGlass']]
        m.diffuse_color = (0.29, 0.40, 0.40, 0.22)
        m.node_tree.nodes.get('Principled BSDF').inputs['Alpha'].default_value = 0.22
        m.surface_render_method = 'DITHERED'
        m.use_backface_culling = False
    return C['entryGuardGlass']


def guard(mesh, point, box, C, w0, d0, w1, d1, h0, h1, *, glazed=True):
    length = math.hypot(w1 - w0, d1 - d0)
    count = max(1, math.ceil(length / 1.4))

    def at(f, lift):
        return point(w0 + (w1 - w0) * f, d0 + (d1 - d0) * f, h0 + (h1 - h0) * f + lift)

    for i in range(count + 1):
        f = i / count
        box(
            w0 + (w1 - w0) * f,
            d0 + (d1 - d0) * f,
            h0 + (h1 - h0) * f + 0.53,
            0.065,
            0.065,
            1.06,
            'dark',
        )
    for lift in (0.16, 1.05) if glazed else (0.5, 1.05):
        mesh.line(at(0, lift), at(1, lift), 0.035, C['dark'], n=6)
    if glazed:
        mat = glass_material(C)
        for i in range(count):
            a = i / count + 0.045 / length
            b = (i + 1) / count - 0.045 / length
            mesh.face([at(a, 0.20), at(b, 0.20), at(b, 0.96), at(a, 0.96)], mat)
