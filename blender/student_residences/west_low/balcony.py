def screen(p, a, b, base, story, C):
    # Trace one solid panel between existing piers. In the photographed
    # middle bays the centre web takes about two fifths of the clear span.
    width = b - a
    xs = [
        a,
        a + 0.027 * width,
        a + 0.30 * width,
        a + 0.70 * width,
        a + 0.973 * width,
        b,
    ]
    bottom = base + 0.17
    height = 0.32 * story
    zs = [bottom, bottom + 0.09 * height, bottom + 0.87 * height, bottom + height]
    front, back = 0.10, -0.06
    filled = {
        (i, j) for i in range(5) for j in range(3) if not (j == 1 and i in (1, 3))
    }
    for i, j in sorted(filled):
        u, v = xs[i : i + 2]
        lo, hi = zs[j : j + 2]
        p.rect(u, v, lo, hi, front, C['dormBlush'])
        p.rect(u, v, lo, hi, back, C['dormBlush'], True)
        if (i, j + 1) not in filled:
            p.face(
                [(u, front, hi), (v, front, hi), (v, back, hi), (u, back, hi)],
                C['dormStonePale'],
            )
        if j > 0 and (i, j - 1) not in filled:
            p.face(
                [(v, front, lo), (u, front, lo), (u, back, lo), (v, back, lo)],
                C['dormConcreteLight'],
            )
        if i > 0 and (i - 1, j) not in filled:
            p.face(
                [(u, front, lo), (u, front, hi), (u, back, hi), (u, back, lo)],
                C['dormBlush'],
            )
        if i < 4 and (i + 1, j) not in filled:
            p.face(
                [(v, front, hi), (v, front, lo), (v, back, lo), (v, back, hi)],
                C['dormBlush'],
            )
