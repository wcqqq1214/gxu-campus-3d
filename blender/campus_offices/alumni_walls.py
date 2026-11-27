"""Punched masonry, jambs, seated sills, side-hung timber lights and cast screens."""

import math

from geometry import Mesh

from .mesh_parts import pigment


def finishes(C):
    return {
        k: pigment(C, '6A ' + k, value)
        for k, value in {
            'plaster': 'c89e56',
            'jamb': 'ac8043',
            'wood': '634037',
            'glass': '403a39',
            'transom': '534d49',
            'dark': '352d29',
            'cream': 'd6d0b8',
            'sill': 'cfc8b7',
            'soffit': 'b7b1a4',
            'deck': '998f81',
            'gallery lime': 'b8a17b',
            'foot': '756358',
            'base': 'b28c48',
            'iron': '706557',
            'gate': 'd1c9aa',
        }.items()
    }


class Wall:
    def __init__(self, start, end, normal, z, colors, detail):
        self.start, self.end = start, end
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        self.length = math.hypot(dx, dy)
        self.tx, self.ty = dx / self.length, dy / self.length
        self.nx, self.ny = normal
        self.z = z
        self.m = colors
        self.near = detail
        self.wall = Mesh()
        self.trim = Mesh()
        self.lights = Mesh()
        self.grilles = Mesh()
        self.holes = []

    def p(self, u, d, h):
        return (
            self.start[0] + u * self.tx + d * self.nx,
            self.start[1] + u * self.ty + d * self.ny,
            self.z + h,
        )

    def face(self, mesh, points, finish):
        pts = [self.p(*p) for p in points]
        if self.tx * self.ny - self.ty * self.nx > 0:
            pts.reverse()
        mesh.face(pts, self.m[finish])

    def panel(self, mesh, l, r, lo, hi, d, finish):
        self.face(mesh, [(l, d, lo), (r, d, lo), (r, d, hi), (l, d, hi)], finish)

    def box(self, mesh, l, r, lo, hi, back, front, finish):
        # Closed section; the back sits inside the jamb or in its bedding joint.
        points = [(l, lo), (r, lo), (r, hi), (l, hi)]
        self.panel(mesh, l, r, lo, hi, front, finish)
        self.face(mesh, [(u, back, h) for u, h in reversed(points)], finish)
        for (u, h), (v, k) in zip(points, points[1:] + points[:1]):
            self.face(
                mesh, [(u, back, h), (v, back, k), (v, front, k), (u, front, h)], finish
            )

    def aperture(self, u, w, lo, hi, kind, open_side=0):
        l, r = u - w / 2, u + w / 2
        if l < 0.05 or r > self.length - 0.03:
            return
        self.holes.append((l, r, lo, hi, kind, open_side))

    def pier(self, u, lo, hi, w=0.20, depth=0.145, finish='plaster'):
        self.box(self.trim, u - w / 2, u + w / 2, lo, hi, -0.03, depth, finish)

    def pipe(self, u, height):
        p = self.p(u, 0.082, height / 2)
        self.trim.cylinder(*p, 0.057, height, self.m['base'], 10 if self.near else 6)
        if self.near:
            for h in range(1, int(height), 3):
                self.trim.cylinder(
                    *self.p(u, 0.082, h), 0.068, 0.047, self.m['iron'], 8
                )

    def add_window(self, l, r, lo, hi, leaf):
        m = self.lights
        width = r - l
        h = hi - lo
        frame = 0.049 if self.near else 0.077
        # Glazing and frame are behind the opening. The projecting sill has a
        # sloped stone top running continuously from the glass rebate to its drip.
        self.panel(m, l, r, lo, hi, -0.235, 'glass')
        trans = lo + h * 0.69
        for u in (l + frame / 2, r - frame / 2, (l + r) / 2):
            self.box(m, u - frame / 2, u + frame / 2, lo, hi, -0.23, -0.158, 'wood')
        for a in (lo, trans, hi - frame):
            self.box(m, l, r, a, a + frame, -0.23, -0.147, 'wood')
        for a, b in [
            (l + frame, (l + r) / 2 - frame / 2),
            ((l + r) / 2 + frame / 2, r - frame),
        ]:
            self.panel(m, a, b, trans + frame, hi - frame, -0.224, 'transom')
        if self.near:
            for u in (l + width * 0.23, l + width * 0.77):
                self.box(
                    m,
                    u - 0.015,
                    u + 0.015,
                    trans + frame,
                    hi - frame,
                    -0.22,
                    -0.173,
                    'wood',
                )
        if leaf:
            hinge = r - frame if leaf > 0 else l + frame
            w = width * 0.38
            free = hinge - leaf * 0.72 * w
            depth = -0.13 + w * 0.70
            a = self.p(hinge, -0.13, lo + frame)
            b = self.p(free, depth, lo + frame)
            top = trans if self.near else hi - frame
            # Rectangular solid rails with a pane between the timber members.
            run = math.hypot(b[0] - a[0], b[1] - a[1])
            angle = math.atan2(b[1] - a[1], b[0] - a[0])
            for pt in (a, b):
                m.box(
                    pt[0],
                    pt[1],
                    self.z + (lo + top) / 2,
                    0.047,
                    0.060,
                    top - lo,
                    self.m['wood'],
                    angle,
                )
            for elev in (lo + 0.04, (lo + top) * 0.5, top - 0.02):
                m.box(
                    (a[0] + b[0]) / 2,
                    (a[1] + b[1]) / 2,
                    self.z + elev,
                    run,
                    0.061,
                    0.046,
                    self.m['wood'],
                    angle,
                )
            if self.near:
                # Bronze reflection on the open leaf is brighter than its empty reveal.
                m.box(
                    (a[0] + b[0]) / 2,
                    (a[1] + b[1]) / 2,
                    self.z + (lo + top) * 0.5,
                    run - 0.045,
                    0.019,
                    top - lo - 0.095,
                    self.m['transom'],
                    angle,
                )

    def sill(self, l, r, h):
        # A single stone profile, seated in the reveal with a bevel under its nose.
        section = [
            (-0.25, h),
            (0.125, h - 0.018),
            (0.125, h - 0.067),
            (0.085, h - 0.088),
            (-0.25, h - 0.088),
        ]
        l -= 0.043
        r += 0.043
        for (d, z), (e, k) in zip(section, section[1:] + section[:1]):
            self.face(self.trim, [(l, d, z), (r, d, z), (r, e, k), (l, e, k)], 'sill')
        for u in (l, r):
            self.face(self.trim, [(u, d, k) for d, k in section], 'sill')

    def screen(self, l, r, lo, hi):
        near = self.near
        cols = max(2, round((r - l) / (0.205 if near else 0.40)))
        rows = max(2, round((hi - lo) / (0.205 if near else 0.40)))
        du, dh = (r - l) / cols, (hi - lo) / rows
        square = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
        for ix in range(cols):
            for iz in range(rows):
                u = l + (ix + 0.5) * du
                h = lo + (iz + 0.5) * dh
                # Alternating cast round apertures; finite throat, with masonry
                # edge completely captured by the jamb on the four panel sides.
                outer = [(u + x * du / 2, -0.135, h + y * dh / 2) for x, y in square]
                inner = [
                    (
                        u + du * 0.39 * math.cos(i * math.pi / 4),
                        -0.135,
                        h + dh * 0.39 * math.sin(i * math.pi / 4),
                    )
                    for i in range(8)
                ]
                for i in range(8):
                    j = (i + 1) % 8
                    self.face(
                        self.grilles, [outer[i], outer[j], inner[j], inner[i]], 'cream'
                    )
                    a, _, c = inner[i]
                    b, _, d = inner[j]
                    self.face(
                        self.grilles,
                        [
                            (a, -0.135, c),
                            (b, -0.135, d),
                            (b, -0.245, d),
                            (a, -0.245, c),
                        ],
                        'sill',
                    )

    def diamond(self, l, r, lo, hi):
        # The three panels above the landing share one deep aperture. Clip each
        # diagonal flat bar to its panel's inset, including the top and bottom.
        cuts = [l, l + (r - l) * 0.24, l + (r - l) * 0.76, r]
        for a, b in zip(cuts, cuts[1:]):
            for u in (a + 0.025, b - 0.025):
                self.box(
                    self.grilles, u - 0.025, u + 0.025, lo, hi, -0.217, -0.089, 'gate'
                )
            for h in (lo + 0.03, hi - 0.085):
                self.box(self.grilles, a, b, h, h + 0.06, -0.20, -0.085, 'gate')
            for sign in (-1, 1):
                slope = sign * 1.17
                step = 0.47 if self.near else 0.67
                low = -abs(slope) * (b - a) - step
                while low < hi - lo + abs(slope) * (b - a):
                    end = low + slope * (b - a)
                    v0 = max(lo + 0.08, min(lo + low, lo + end))
                    v1 = min(hi - 0.06, max(lo + low, lo + end))
                    if v1 - v0 > 0.065:
                        u0 = a + (v0 - lo - low) / slope
                        u1 = a + (v1 - lo - low) / slope
                        self.grilles.line(
                            self.p(u0, -0.155 + (sign + 1) * 0.013, v0),
                            self.p(u1, -0.155 + (sign + 1) * 0.013, v1),
                            0.047,
                            self.m['gate'],
                            4,
                        )
                    low += step

    def build(self, mesh, height, label, entry=None, fascia=True):
        # Generate only the masonry intervals between actual holes.
        bands = sorted(
            {-0.5, height, *[v for l, r, a, b, _, _ in self.holes for v in (a, b)]}
        )
        for low, high in zip(bands, bands[1:]):
            gaps = sorted(
                (l, r)
                for l, r, a, b, _, _ in self.holes
                if a <= (low + high) * 0.5 <= b
            )
            start = 0
            for l, r in gaps + [(self.length, self.length)]:
                if l > start + 0.001:
                    self.panel(self.wall, start, l, low, high, 0, 'plaster')
                start = max(start, r)
        for l, r, lo, hi, kind, side in self.holes:
            depth = {
                'balcony': 1.25,
                'vent': 0.22,
                'window': 0.245,
                'screen': 0.49,
                'diamond': 0.66,
                'door': 0.50,
                'glazed': 0.50,
            }[kind]
            corners = [(l, lo), (r, lo), (r, hi), (l, hi)]
            for (a, h), (b, k) in zip(corners, corners[1:] + corners[:1]):
                self.face(
                    self.wall,
                    [(a, 0, h), (b, 0, k), (b, -depth, k), (a, -depth, h)],
                    'jamb',
                )
            if kind == 'window':
                self.add_window(l, r, lo, hi, side)
                self.sill(l, r, lo)
            else:
                self.panel(self.wall, l, r, lo, hi, -depth, 'dark')
                if kind == 'balcony':
                    self.box(
                        self.trim, l, r, lo + 0.08, lo + 0.22, -0.19, 0.06, 'cream'
                    )
                    self.box(
                        self.trim, l, r, lo + 0.80, lo + 0.89, -0.19, 0.06, 'cream'
                    )
                    for j in range(8):
                        u = l + (j + 0.5) * (r - l) / 8
                        self.box(
                            self.trim,
                            u - 0.063,
                            u + 0.063,
                            lo + 0.22,
                            lo + 0.80,
                            -0.134,
                            -0.022,
                            'cream',
                        )
                if kind == 'screen':
                    self.screen(l, r, lo, hi)
                    self.sill(l, r, lo)
                if kind == 'diamond':
                    self.diamond(l, r, lo, hi)
                if kind in ('door', 'glazed'):
                    for u in (l + 0.027, r - 0.027):
                        self.box(
                            self.trim,
                            u - 0.027,
                            u + 0.027,
                            lo,
                            hi,
                            -depth,
                            -depth + 0.071,
                            'wood',
                        )
                    self.box(
                        self.trim, l, r, hi - 0.07, hi, -depth, -depth + 0.072, 'wood'
                    )
                    if kind == 'glazed':
                        self.panel(
                            self.lights,
                            l + 0.055,
                            r - 0.055,
                            lo + 0.08,
                            hi - 0.07,
                            -depth + 0.02,
                            'glass',
                        )
                        self.box(
                            self.trim,
                            l,
                            r,
                            hi - 0.74,
                            hi - 0.67,
                            -depth,
                            -depth + 0.084,
                            'wood',
                        )
                        self.box(
                            self.trim,
                            (l + r) / 2 - 0.025,
                            (l + r) / 2 + 0.025,
                            lo,
                            hi,
                            -depth,
                            -depth + 0.07,
                            'wood',
                        )
        spans = (
            [(0, self.length)]
            if not entry
            else [(0, entry[0]), (entry[1], self.length)]
        )
        for l, r in spans:
            if r - l < 0.001:
                continue
            # Thin base returns to the wall. Sill nose and plinth meet below the glazing.
            self.box(self.trim, l, r, -0.26, 0.19, -0.017, 0.044, 'foot')
            self.box(self.trim, l, r, 0.19, 1.015, -0.018, 0.027, 'base')
            self.box(self.trim, l, r, 1.015, 1.095, -0.025, 0.085, 'sill')
        if fascia:
            self.box(
                self.trim,
                0,
                self.length,
                height - 0.08,
                height + 0.066,
                -0.095,
                0.25,
                'sill',
            )
        for part, name in [
            (self.wall, '砌体及窗洞'),
            (self.trim, '线脚及门框'),
            (self.lights, '木窗扇'),
            (self.grilles, '花格'),
        ]:
            if part.f:
                mesh.add_part(label + '｜' + name, part)
