from geometry import MATERIALS, material

_HEIGHTS = {
    9: (0.57, 0.33, 0.68),
    10: (0.61, 0.35, 0.66),
    11: (0.57, 0.34, 0.68),
}


def _core_paint(n):
    # Qualitative estimates from the core alongside each wing in the same photo.
    # All calibrated windows share the campus glass and frame materials.
    name = f'West{n}_NorthCorePlaster'
    index = next((i for i, m in enumerate(MATERIALS) if m.name == name), None)
    if index is None:
        tones = {9: (211, 190, 174), 10: (188, 151, 149), 11: (211, 183, 169)}
        rgb = tuple(((v / 255 + 0.055) / 1.055) ** 2.4 for v in tones[n])
        index = material(name, rgb, 0.88)
    return index


def _opening(p, a, b, lo, hi, left, right, sill, head, wall, C, near, tall):
    p.rect(a, b, lo, sill, 0, wall)
    p.rect(a, b, head, hi, 0, wall)
    p.rect(a, left, sill, head, 0, wall)
    p.rect(right, b, sill, head, 0, wall)
    d = -0.15
    # One front wall with a true reveal. The frame and glass tile the
    # back of the opening, without an uncut wall or overlapping frame boxes.
    p.face(
        [(left, 0, sill), (right, 0, sill), (right, d, sill), (left, d, sill)],
        C['dormStonePale'],
    )
    p.face(
        [(right, 0, head), (left, 0, head), (left, d, head), (right, d, head)],
        C['dormConcrete'],
    )
    p.face(
        [(left, 0, head), (left, 0, sill), (left, d, sill), (left, d, head)],
        C['dormConcreteLight'],
    )
    p.face(
        [(right, 0, sill), (right, 0, head), (right, d, head), (right, d, sill)],
        C['dormConcrete'],
    )
    rim = 0.047
    p.rect(left, right, sill, sill + rim, d, C['metal'])
    p.rect(left, right, head - rim, head, d, C['metal'])
    p.rect(left, left + rim, sill + rim, head - rim, d, C['metal'])
    p.rect(right - rim, right, sill + rim, head - rim, d, C['metal'])
    x1, x2 = left + rim, right - rim
    if not tall:
        p.rect(x1, x2, sill + rim, head - rim, d, C['dormWindow'])
        return
    t = sill + (head - sill) * 0.75
    p.rect(x1, x2, t - 0.025, t + 0.025, d, C['metal'])
    p.rect(x1, x2, t + 0.025, head - rim, d, C['dormWindow'])
    if near:
        mid = (left + right) / 2
        p.rect(x1, mid - 0.024, sill + rim, t - 0.025, d, C['dormWindow'])
        p.rect(mid - 0.024, mid + 0.024, sill + rim, t - 0.025, d, C['metal'])
        p.rect(mid + 0.024, x2, sill + rim, t - 0.025, d, C['dormWindow'])
    else:
        p.rect(x1, x2, sill + rim, t - 0.025, d, C['dormWindow'])


def core(p, height, floors, n, C, near):
    L = p.w.length
    story = height / floors
    tall, small, ground = _HEIGHTS[n]
    paint = _core_paint(n)
    for level in range(floors):
        base = level * story
        lo = base if level else -0.55
        # The ground tier has only the middle pair. The two inner axes then
        # continue upward, with a small lower-headed opening to either side.
        axes = (0.365, 0.635) if not level else (0.15, 0.365, 0.635, 0.85)
        split = [0] + [L * (x + y) / 2 for x, y in zip(axes, axes[1:])] + [L]
        for i, x in enumerate(axes):
            inner = 0.2 < x < 0.8
            opening_height = story * (
                ground if level == 0 else tall if inner else small
            )
            width = L * ((0.090 if level == 0 else 0.084) if inner else 0.062)
            sill = base + story * (0.13 if level == 0 else 0.22)
            if n == 10 and level == 0:
                # The north street view puts both heads about 4 px below the
                # underside of the stripe, against an 80 px opening.
                sill = story - 0.13 - (1.05 * opening_height)
            _opening(
                p,
                split[i],
                split[i + 1],
                lo,
                base + story - 0.13,
                L * x - width / 2,
                L * x + width / 2,
                sill,
                sill + opening_height,
                paint,
                C,
                near,
                inner,
            )
        p.rect(0, L, base + story - 0.13, base + story, 0, C['dormBlush'])
