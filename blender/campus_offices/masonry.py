"""Local coordinates for masonry openings. Depth is positive into the building."""

import math

from geometry import material

FINISH = {
    'porcelain': 'e5e5df',
    'joint': 'a6aba4',
    'green': '557369',
    'shadowGlass': '3e5452',
    'spandrel': 'deded7',
    'reveal': 'c1c2b5',
    'alloy': 'a1a79f',
    'shell': 'c9c5b8',
    'brick': 'cbc6b7',
    'terracotta': 'af6d57',
    'dark': '535a50',
    'bar': '8b8980',
    'floor': 'b9b5a7',
}


def finishes(C):
    table = {}
    for key, hex_color in FINISH.items():
        name = 'GXU six C ' + key
        if name not in C:
            rgb = [int(hex_color[i : i + 2], 16) / 255 for i in (0, 2, 4)]
            C[name] = material(
                name,
                [
                    ((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92
                    for v in rgb
                ],
            )
        table[key] = C[name]
    return table


class Wall:
    def __init__(self, m, a, b, normal, z, palette):
        self.m, self.a, self.z, self.c = m, a, z, palette
        self.length = math.dist(a, b)
        self.u = tuple((b[i] - a[i]) / self.length for i in range(2))
        self.n = normal
        self.forward = self.u[1] * normal[0] - self.u[0] * normal[1] > 0
        self.angle = math.atan2(self.u[1], self.u[0])

    def point(self, x, d, h):
        return (
            self.a[0] + x * self.u[0] - d * self.n[0],
            self.a[1] + x * self.u[1] - d * self.n[1],
            self.z + h,
        )

    def face(self, coords, kind):
        pts = [self.point(*v) for v in coords]
        self.m.face(pts if self.forward else pts[::-1], self.c[kind])

    def panel(self, x, r, b, t, d, kind):
        if r - x > 0.0001 and t - b > 0.0001:
            self.face([(x, d, b), (r, d, b), (r, d, t), (x, d, t)], kind)

    def box(self, x, d, h, w, depth, height, kind):
        self.m.box(*self.point(x, d, h), w, depth, height, self.c[kind], self.angle)

    def member(self, x, d, h, r, dr, hr, width, kind):
        # Rectangular brace, oriented in the elevation plane; the four edges have depth.
        length = math.hypot(r - x, hr - h)
        ox = (hr - h) * width / (2 * length)
        oz = (x - r) * width / (2 * length)
        ring = [
            (x + ox, h + oz),
            (r + ox, hr + oz),
            (r - ox, hr - oz),
            (x - ox, h - oz),
        ]
        front = [(s, d, v) for s, v in ring]
        back = [(s, dr, v) for s, v in ring]
        self.face(front, kind)
        self.face(back[::-1], kind)
        for i in range(4):
            j = (i + 1) % 4
            self.face([front[i], back[i], back[j], front[j]], kind)

    def hole(
        self, l, r, b, t, depth, fill, columns=1, bar='alloy', width=0.055, rail=None
    ):
        if fill == 'oculus':
            cx = (l + r) / 2
            cz = (b + t) / 2
            rim = []
            for k in range(24):
                theta = math.tau * k / 24
                dx = math.cos(theta)
                dz = math.sin(theta)
                corner = max(abs(dx), abs(dz))
                rim.append(
                    (
                        (
                            cx + (r - l) * dx / (2 * corner),
                            0,
                            cz + (t - b) * dz / (2 * corner),
                        ),
                        (cx + (r - l) * dx / 2, 0, cz + (t - b) * dz / 2),
                    )
                )
            for i, (outer, inner) in enumerate(rim):
                nxt, arc = rim[(i + 1) % len(rim)]
                self.face([outer, nxt, arc, inner], 'brick')
                self.face(
                    [inner, arc, (arc[0], depth, arc[2]), (inner[0], depth, inner[2])],
                    'reveal',
                )
            self.face([(inner[0], depth, inner[2]) for _, inner in rim], 'shadowGlass')
            return
        front = [(l, 0, b), (r, 0, b), (r, 0, t), (l, 0, t)]
        inner = [(s, depth, h) for s, _, h in front]
        for i in range(4):
            j = (i + 1) % 4
            self.face([front[i], front[j], inner[j], inner[i]], 'reveal')
        if fill == 'open':
            return
        self.panel(l, r, b, t, depth, fill)
        for j in range(1, columns):
            self.box(
                l + (r - l) * j / columns,
                depth - 0.042,
                (b + t) / 2,
                width,
                0.070,
                t - b,
                bar,
            )
        if rail is not None:
            self.box(
                (l + r) / 2, depth - 0.060, b + (t - b) * rail, r - l, 0.08, 0.055, bar
            )

    def row(self, b, t, holes, wall, start=0, end=None):
        last = start
        for l, r, sill, head, depth, glass, count in holes:
            self.panel(last, l, b, t, 0, wall)
            self.panel(l, r, b, sill, 0, wall)
            self.panel(l, r, head, t, 0, wall)
            self.hole(l, r, sill, head, depth, glass, count)
            last = r
        self.panel(last, self.length if end is None else end, b, t, 0, wall)
