class Surface:
    """Draw in edge coordinates. Depth increases towards the street."""

    def __init__(self, wall, mesh, datum):
        self.w, self.mesh, self.datum = wall, mesh, datum

    def point(self, u, d, h):
        w = self.w
        return (w.x + w.tx * u + w.nx * d, w.y + w.ty * u + w.ny * d, self.datum + h)

    def face(self, local, material):
        points = [self.point(*p) for p in local]
        if self.w.tx * self.w.ny - self.w.ty * self.w.nx > 0:
            points.reverse()
        self.mesh.face(points, material)

    def panel(self, a, b, lo, hi, mat, d=0):
        if b - a > 1e-6 and hi - lo > 1e-6:
            self.rect(a, b, lo, hi, d, mat)

    def slope(self, a, b, z1, z2, d1, d2, mat):
        self.face([(a, d1, z1), (b, d1, z1), (b, d2, z2), (a, d2, z2)], mat)

    def side(self, u, outer, inner, lo, hi, mat):
        self.face([(u, outer, lo), (u, inner, lo), (u, inner, hi), (u, outer, hi)], mat)

    def soffit(self, a, b, inner, outer, height, mat, top=True):
        self.slope(
            a, b, height, height, outer if top else inner, inner if top else outer, mat
        )

    def window(self, a, b, lo, hi, left, right, sill, head, wall, C, detail, depth=0):
        """Wall segments meet the reveal; the glass is behind its outer edges."""
        self.panel(a, b, lo, sill, wall, depth)
        self.panel(a, b, head, hi, wall, depth)
        self.panel(a, left, sill, head, wall, depth)
        self.panel(right, b, sill, head, wall, depth)
        back = depth - 0.12
        self.side(left, depth, back, sill, head, C['dormConcrete'])
        self.side(right, back, depth, sill, head, C['dormConcrete'])
        self.soffit(left, right, back, depth, sill, C['dormStonePale'])
        self.soffit(left, right, back, depth, head, C['dormConcrete'], False)
        edge = 0.065
        self.panel(left, right, sill, sill + edge, C['metal'], back)
        self.panel(left, right, head - edge, head, C['metal'], back)
        mid = (left + right) / 2
        self.panel(left, left + edge, sill + edge, head - edge, C['metal'], back)
        self.panel(right - edge, right, sill + edge, head - edge, C['metal'], back)
        if detail:
            self.panel(
                left + edge,
                mid - 0.026,
                sill + edge,
                head - edge,
                C['dormWindow'],
                back,
            )
            self.panel(
                mid - 0.026, mid + 0.026, sill + edge, head - edge, C['metal'], back
            )
            self.panel(
                mid + 0.026,
                right - edge,
                sill + edge,
                head - edge,
                C['dormWindow'],
                back,
            )
        else:
            self.panel(
                left + edge,
                right - edge,
                sill + edge,
                head - edge,
                C['dormWindow'],
                back,
            )

    def plinth(self, a, b, h, C, detail, stone, finish=None):
        """Plinth courses form the wall surface itself, including its narrow bevel."""
        base = (
            finish
            if finish is not None
            else C['dormPaverGrey']
            if stone
            else C['dormConcrete']
        )
        foot = -0.55
        self.panel(a, b, foot, 0, base, 0.045)
        if stone and detail:
            rows = max(1, round(h / 0.28))
            for j in range(rows):
                lo, hi = j * h / rows, (j + 1) * h / rows
                self.panel(a, b, lo, lo + 0.014, C['dormConcrete'], 0.045)
                x = a
                while x < b - 0.0001:
                    c = min(b, x + (0.39 if j % 2 and x == a else 0.78))
                    joint = min(0.016, c - x)
                    self.panel(x, x + joint, lo + 0.014, hi, C['dormConcrete'], 0.045)
                    self.panel(x + joint, c, lo + 0.014, hi, base, 0.045)
                    x = c
        else:
            self.panel(a, b, 0, h, base, 0.045)
        self.slope(a, b, h, h + 0.06, 0.045, 0, C['dormConcreteLight'])

    def rect(self, a, b, bottom, top, depth, mat, reverse=False):
        pts = [(a, depth, bottom), (b, depth, bottom), (b, depth, top), (a, depth, top)]
        self.face(pts[::-1] if reverse else pts, mat)
