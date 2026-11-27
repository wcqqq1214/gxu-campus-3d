"""Pierced concrete panels in coordinates local to a straight balcony front."""


class Plate:
    """A front panel with real openings. The host already supplies the cap and base."""

    def __init__(self, mesh, transform, inner, outer, mat, reveal):
        self.mesh = mesh
        self.xyz = transform
        self.inner = inner
        self.outer = outer
        self.mat = mat
        self.reveal = reveal

    def patch(self, polygon):
        self.mesh.face([self.xyz(x, self.outer, h) for x, h in polygon], self.mat)
        self.mesh.face(
            [self.xyz(x, self.inner, h) for x, h in reversed(polygon)], self.mat
        )

    def rectangle(self, a, b, lo, hi):
        if b > a and hi > lo:
            self.patch([(a, lo), (b, lo), (b, hi), (a, hi)])

    def perforated(self, a, b, lo, hi, count, diamond):
        step = (b - a) / count
        for j in range(count):
            l = a + j * step
            r = l + step
            shell = [(l, lo), (r, lo), (r, hi), (l, hi)]
            if diamond:
                # A slim cast web between adjacent lozenges.
                c = (l + r) / 2
                h = (lo + hi) / 2
                hole = [
                    (c, lo + 0.06 * (hi - lo)),
                    (r - step * 0.07, h),
                    (c, hi - 0.06 * (hi - lo)),
                    (l + step * 0.07, h),
                ]
            else:
                gap = step * 0.10
                hole = [
                    (l + gap, lo + 0.045),
                    (r - gap, lo + 0.045),
                    (r - gap, hi - 0.045),
                    (l + gap, hi - 0.045),
                ]
            for k in range(4):
                nxt = (k + 1) % 4
                self.patch([shell[k], shell[nxt], hole[nxt], hole[k]])
                a0, h0 = hole[k]
                a1, h1 = hole[nxt]
                self.mesh.face(
                    [
                        self.xyz(a0, self.outer, h0),
                        self.xyz(a1, self.outer, h1),
                        self.xyz(a1, self.inner, h1),
                        self.xyz(a0, self.inner, h0),
                    ],
                    self.reveal,
                )

    def diagonal_modules(self, a, b, lo, hi, count):
        # A rectangular cast cell with a rising web, visible on the western stack of 10.
        step = (b - a) / count
        for j in range(count):
            l = a + j * step
            r = l + step
            u = l + 0.08 * step
            v = r - 0.08 * step
            z0 = lo + 0.025
            z1 = hi - 0.025
            outside = [(l, lo), (r, lo), (r, hi), (l, hi)]
            inside = [(u, z0), (v, z0), (v, z1), (u, z1)]
            web = 0.12 * (v - u)
            rise = 0.12 * (z1 - z0)
            A = (u + web, z0)
            B = (v, z1 - rise)
            F = (v - web, z1)
            E = (u, z0 + rise)
            for k in range(4):
                nxt = (k + 1) % 4
                self.patch([outside[k], outside[nxt], inside[nxt], inside[k]])
            self.patch([(u, z0), A, B, (v, z1), F, E])
            for hole in [[A, (v, z0), B], [E, F, (u, z1)]]:
                for k, (x0, h0) in enumerate(hole):
                    x1, h1 = hole[(k + 1) % 3]
                    self.mesh.face(
                        [
                            self.xyz(x0, self.outer, h0),
                            self.xyz(x1, self.outer, h1),
                            self.xyz(x1, self.inner, h1),
                            self.xyz(x0, self.inner, h0),
                        ],
                        self.reveal,
                    )
