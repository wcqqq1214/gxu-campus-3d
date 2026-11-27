"""Local facade axes, finish palette and the openings used by East Campus residences."""

import math

from mathutils import Vector
from mathutils.geometry import tessellate_polygon

from geometry import material


def colors(C):
    swatches = {
        'brick': (0.47, 0.202, 0.15),
        'band': (0.85, 0.77, 0.66),
        'cream': (0.78, 0.69, 0.55),
        'shellPink': (0.78, 0.65, 0.62),
        'roof': (0.225, 0.22, 0.188),
        'render': (0.78, 0.79, 0.76),
        'blueGrey': (0.225, 0.26, 0.29),
        'yellow': (0.95, 0.62, 0.065),
        'plinth': (0.29, 0.23, 0.20),
    }
    result = {}
    for key, rgb in swatches.items():
        name = 'EastDorm_' + key
        if name not in C:
            C[name] = material(name, rgb, 0.87)
        result[key] = C[name]
    result['glass'] = C['glass']
    for key, rgb in {
        'sash': (0.31, 0.34, 0.32),
        'metal': (0.50, 0.51, 0.47),
        'shade': (0.42, 0.37, 0.30),
    }.items():
        name = 'EastDormFacade_' + key
        if name not in C:
            C[name] = material(name, rgb, 0.75)
        result[key] = C[name]
    return result


def clockwise(points):
    p = list(points)
    if p[0] == p[-1]:
        p = p[:-1]
    if sum(a[0] * b[1] - a[1] * b[0] for a, b in zip(p, p[1:] + p[:1])) > 0:
        p.reverse()
    return p


class Edge:
    def __init__(self, a, b):
        a, b = a[:2], b[:2]
        self.a = a
        self.length = math.dist(a, b)
        self.ux = (b[0] - a[0]) / self.length
        self.uy = (b[1] - a[1]) / self.length
        self.nx, self.ny = -self.uy, self.ux
        self.angle = math.atan2(self.uy, self.ux)

    def p(self, t, out, h):
        return (
            self.a[0] + t * self.ux + out * self.nx,
            self.a[1] + t * self.uy + out * self.ny,
            h,
        )

    def rect(self, m, a, b, low, high, offset, mat, reverse=False):
        if b - a > 0.0001 and high - low > 0.0001:
            pts = [
                self.p(t, offset, h)
                for t, h in [(b, low), (a, low), (a, high), (b, high)]
            ]
            m.face(pts[::-1] if reverse else pts, mat)

    def reveal(self, m, a, b, low, high, front, back, mat):
        corners = [(b, low), (a, low), (a, high), (b, high)]
        for start, end in zip(corners, corners[1:] + corners[:1]):
            m.face(
                [
                    self.p(t, d, h)
                    for ((t, h), d) in [
                        (start, front),
                        (end, front),
                        (end, back),
                        (start, back),
                    ]
                ],
                mat,
            )

    def strip(self, m, a, b, front, back, z, mat, ceiling=False):
        pts = [
            self.p(t, d, z) for t, d in [(b, front), (a, front), (a, back), (b, back)]
        ]
        m.face(pts[::-1] if ceiling else pts, mat)

    def beam(self, m, left, right, bottom, top, out, depth, mat, *, close_bottom=True):
        x, y, h = self.p((left + right) / 2, out, (bottom + top) / 2)
        m.box(
            x,
            y,
            h,
            right - left,
            depth,
            top - bottom,
            mat,
            self.angle,
            bottom=close_bottom,
        )

    def subsection(self, l, r):
        return Edge(self.p(l, 0, 0), self.p(r, 0, 0))


def cap(m, ring, height, mat):
    points = [Vector((x, y, height)) for x, y in ring]
    for tri in tessellate_polygon([points]):
        coords = [points[i] for i in tri]
        if (coords[1] - coords[0]).cross(coords[2] - coords[0]).z < 0:
            coords.reverse()
        m.face([tuple(p) for p in coords], mat)


def rails(m, e, a, b, lo, hi, offset, p, near):
    """Rectangular tube perimeter and slender pickets anchored into the curb."""
    e.beam(m, a, b, hi - 0.055, hi, offset, 0.055, p['metal'])
    n = max(2, round((b - a) / (0.30 if near else 0.59)))
    for i in range(n + 1):
        t = a + 0.033 + (b - a - 0.066) * i / n
        e.beam(m, t - 0.022, t + 0.022, lo, hi - 0.055, offset, 0.04, p['metal'])


def sash(m, e, a, b, lo, hi, d, p, near):
    """A continuous frame surrounding separate panes, all behind the masonry reveal."""
    rim = 0.065 if near else 0.085
    for l, r, h, k in [
        (a, a + rim, lo, hi),
        (b - rim, b, lo, hi),
        (a + rim, b - rim, lo, lo + rim),
        (a + rim, b - rim, hi - rim, hi),
    ]:
        e.rect(m, l, r, h, k, d, p['sash'])
    l, r = a + rim, b - rim
    bot, top = lo + rim, hi - rim
    e.reveal(m, l, r, bot, top, d, d - 0.032, p['sash'])
    mid = (l + r) / 2
    half = 0.026 if near else 0.039
    e.rect(m, mid - half, mid + half, bot, top, d - 0.032, p['metal'])
    for left, right in [(l, mid - half), (mid + half, r)]:
        if near and hi - lo > 1.25:
            head = top - min(0.37, (hi - lo) * 0.20)
            e.rect(m, left, right, bot, head, d - 0.032, p['glass'])
            e.rect(m, left, right, head, head + 0.035, d - 0.032, p['sash'])
            e.rect(m, left, right, head + 0.035, top, d - 0.032, p['glass'])
        else:
            e.rect(m, left, right, bot, top, d - 0.032, p['glass'])


def cell(m, e, l, r, lo, hi, u, v, sill, head, plane, depth, wall, p, near):
    for a, b, h, k in [
        (l, u, lo, hi),
        (v, r, lo, hi),
        (u, v, lo, sill),
        (u, v, head, hi),
    ]:
        e.rect(m, a, b, h, k, plane, wall)
    e.reveal(m, u, v, sill, head, plane, plane - depth, wall)
    sash(m, e, u, v, sill, head, plane - depth, p, near)


def gallery(m, e, lo, hi, depth, outer, colour, p, near, balcony):
    """Build a lowered gallery floor, attached rear windows and solid parapet returns."""
    w = e.length
    deck = lo - (0.84 if balcony else 0.93)
    lip = -0.14
    # Replace the threshold and jambs. The balcony's outside brick below the old
    # opening is cut down to the slab, while south galleries retain solid parapets.
    if balcony:
        front = 0.32
        e.strip(m, 0, w, front, -depth, deck, p['band'])
        e.strip(m, 0, w, front, 0, deck - 0.15, p['shade'], True)
        e.rect(m, 0, w, deck - 0.15, deck, front, p['band'])
        for t in (0, w):
            side = Edge(e.p(t, 0, 0), e.p(t, front, 0))
            side.rect(m, 0, front, deck - 0.15, deck, 0, p['band'], t == w)
        rails(m, e, 0.03, w - 0.03, deck, lo + 0.14, front - 0.04, p, near)
        for t in (0.03, w - 0.03):
            side = Edge(e.p(t, -0.04, 0), e.p(t, front - 0.04, 0))
            rails(m, side, 0, side.length, deck, lo + 0.14, 0, p, near)
        jamb_base = deck
    else:
        e.strip(m, 0, w, 0, lip, lo, p['band'])
        # Interior face of the masonry parapet faces into the gallery.
        a = Edge(e.p(w, lip, 0), e.p(0, lip, 0))
        a.rect(m, 0, w, deck, lo, 0, colour)
        e.strip(m, 0, w, lip, -depth, deck, p['shade'])
        jamb_base = lo
    e.strip(m, 0, w, 0, -depth, hi, p['cream'], True)
    for t in (0, w):
        side = Edge(e.p(t, 0, 0), e.p(t, -depth, 0))
        side.rect(m, 0, depth, jamb_base, hi, 0, outer, t == w)
        if not balcony:
            side.rect(m, -lip, depth, deck, lo, 0, outer, t == w)
    bays = max(1, round(w / 4.3))
    for n in range(bays):
        l, r = w * n / bays, w * (n + 1) / bays
        cell(
            m,
            e,
            l,
            r,
            deck,
            hi,
            l + 0.24 * (r - l),
            r - 0.24 * (r - l),
            deck + 0.70,
            hi - 0.19,
            -depth,
            0.10,
            p['shade'],
            p,
            near,
        )


def projecting_window(m, e, lo, hi, p, near):
    w = e.length
    out = 0.39
    # Slab and soffit have the same perimeter as the oriel. No wall behind the glass.
    for h, k in [(lo, lo + 0.12), (hi - 0.13, hi)]:
        e.strip(m, 0, w, out, 0, k, p['render'])
        e.strip(m, 0, w, out, 0, h, p['render'], True)
        e.rect(m, 0, w, h, k, out, p['render'])
    for t in (0, w):
        side = Edge(e.p(t, 0, 0), e.p(t, out, 0))
        side.rect(m, 0, out, lo, lo + 0.12, 0, p['render'], t == w)
        side.rect(m, 0, out, hi - 0.13, hi, 0, p['render'], t == w)
        side.rect(m, 0, 0.055, lo + 0.12, hi - 0.13, 0, p['sash'], t == w)
        side.rect(m, 0.055, out - 0.055, lo + 0.12, hi - 0.13, 0, p['glass'], t == w)
        side.rect(m, out - 0.055, out, lo + 0.12, hi - 0.13, 0, p['sash'], t == w)
    sash(m, e, 0, w, lo + 0.12, hi - 0.13, out, p, near)
