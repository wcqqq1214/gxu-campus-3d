"""Street-facing glazing and retractable cloth along the south arcade."""

import math


def cloth(mesh, center, width, red, linen, tube):
    # One broad scallop spans four stripes. Pleats continue around the front rail.
    stripes = 40
    left = center - width / 2
    for strip in range(stripes):
        mat = red if strip % 2 == 0 else linen
        for s in range(3):
            corners = []
            for t in (strip + s / 3, strip + (s + 1) / 3):
                x = left + t * width / stripes
                wave = math.cos(t * math.pi / 2)
                fold = 0.018 * math.cos(t * math.pi)
                lip = -1.58 + 0.023 * wave + fold
                corners.append(
                    [
                        (x, 0.04, 3.34),
                        (x, -0.82, 3.01 + 0.022 * wave),
                        (x, lip, 2.80),
                        (x, lip - 0.026, 2.55 + 0.014 * wave),
                        (x, lip + 0.015 + fold, 2.27 + 0.045 * wave),
                    ]
                )
            a, b = corners
            for k in range(4):
                mesh.face([a[k], a[k + 1], b[k + 1], b[k]], mat)
    mesh.box(center, 0.01, 3.36, width + 0.10, 0.088, 0.078, tube)
    mesh.box(center, -1.565, 2.805, width + 0.04, 0.042, 0.042, tube)
    for mounting_x in (left + 0.29, left + width - 0.29):
        mesh.face(
            [
                (mounting_x, 0.02, 2.88),
                (mounting_x, -1.49, 2.78),
                (mounting_x, -1.49, 2.75),
                (mounting_x, 0.02, 2.82),
            ],
            tube,
        )


def shopfront(mesh, bay, y, mat, detail):
    glass, etched, jamb, aluminium, bricks, blue, red, rubber, head = mat
    front = y + 1.05

    def plate(x0, x1, lo, hi, at, finish):
        mesh.face([(x0, at, lo), (x1, at, lo), (x1, at, hi), (x0, at, hi)], finish)

    doorways = {2: (1.5 * bay + 1.45, 2.98), 4: (3.5 * bay + 1.20, 1.70)}
    for j in range(1, 6):
        center = j * bay
        l = center - bay / 2 + 0.30
        r = center + bay / 2 - 0.30
        spans = [(l, r, False)]
        if j in doorways:
            x, w = doorways[j]
            a = x - w / 2
            b = x + w / 2
            spans = [(l, a, False), (a, b, True), (b, r, False)]
        for a, b, door in spans:
            if b <= a:
                continue
            width = b - a
            xx = (a + b) / 2
            sill = 0.038 if door else 0.245
            mesh.box(
                xx, front + 0.031, (2.35 + sill) / 2, width, 0.065, 2.35 - sill, glass
            )
            if not door:
                mesh.box(xx, front + 0.04, sill / 2, width, 0.17, sill, bricks)
                plate(a + 0.025, b - 0.025, sill + 0.018, 0.995, front - 0.008, etched)
            count = (4 if j == 2 else 2) if door else max(1, round(width / 2.15))
            for i in range(count + 1):
                mesh.box(
                    a + i * width / count,
                    front - 0.021,
                    (2.34 + sill) / 2,
                    0.018,
                    0.035,
                    2.34 - sill,
                    jamb,
                )
            if detail:
                for z, finish in ((1.016, red), (1.082, blue)):
                    plate(
                        a + 0.012,
                        b - 0.012,
                        z - 0.029,
                        z + 0.029,
                        front - 0.048,
                        finish,
                    )
            if door:
                mesh.box(xx, front - 0.02, 0.019, width, 0.16, 0.038, aluminium)
                pairs = (xx - width / 4, xx + width / 4) if count == 4 else (xx,)
                for hx in (mid + s for mid in pairs for s in (-0.091, 0.091)):
                    mesh.box(hx, front - 0.104, 0.913, 0.024, 0.035, 0.48, aluminium)
                    for h in (0.687, 1.139):
                        mesh.box(hx, front - 0.064, h, 0.025, 0.085, 0.026, aluminium)
                mesh.box(xx, front - 0.80, 0.012, width + 0.13, 1.56, 0.024, rubber)
        mesh.box(center, front + 0.02, 2.46, r - l, 0.19, 0.22, head)
    # Under the projecting slab, the brick lintel ends in a darker recessed fascia.
    mesh.box(3 * bay, y + 0.07, 2.65, 5 * bay, 0.66, 0.24, bricks)
