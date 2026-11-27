"""Wall-local geometry and indexed mesh operations."""

import math
from bisect import bisect_left


class Wall:
    def __init__(self, edge, kind, loggia_range=(0.0, 1.0)):
        self.a = edge['start']
        self.length = math.dist(self.a, edge['end'])
        self.t = tuple((b - a) / self.length for a, b in zip(self.a, edge['end']))
        self.n = edge['normal']
        self.kind = kind
        self.loggia_range = loggia_range
        self.sign = self.t[1] * self.n[0] - self.t[0] * self.n[1]
        self.host = []

    def local(self, point):
        dx, dy = point[0] - self.a[0], point[1] - self.a[1]
        return dx * self.t[0] + dy * self.t[1], dx * self.n[0] + dy * self.n[1]

    def point(self, u, d, h):
        return (
            self.a[0] + u * self.t[0] + d * self.n[0],
            self.a[1] + u * self.t[1] + d * self.n[1],
            h,
        )

    def face(self, patch, points, mat):
        ordered = points if self.sign > 0 else reversed(points)
        patch.face([self.point(*p) for p in ordered], mat)

    def rect(self, patch, left, right, low, high, depth, mat):
        if high - low > 0.0001 and right - left > 0.0001:
            self.face(
                patch,
                [
                    (left, depth, low),
                    (right, depth, low),
                    (right, depth, high),
                    (left, depth, high),
                ],
                mat,
            )

    def reveal(self, patch, left, right, low, high, depth, material):
        front = [(left, 0, low), (right, 0, low), (right, 0, high), (left, 0, high)]
        back = [(u, depth, z) for u, _, z in front]
        for i in range(4):
            j = (i + 1) % 4
            self.face(patch, [front[i], front[j], back[j], back[i]], material)


def pocket(
    surface, p, left, right, low, high, depth, wall, glass, frame, style, detail
):
    surface.reveal(p, left, right, low, high, -depth, wall)
    if style == 'loggia':
        # The exterior back has a solid spandrel and sides; everything fits
        # behind the original wall plane and terminates at the two reveals.
        bottom = low + 0.24
        head = high - 0.20
        margin = (right - left) * 0.11
        surface.rect(p, left, right, low, bottom, -depth, wall)
        surface.rect(p, left, right, head, high, -depth, wall)
        surface.rect(p, left, left + margin, bottom, head, -depth, wall)
        surface.rect(p, right - margin, right, bottom, head, -depth, wall)
        surface.rect(p, left + margin, right - margin, bottom, head, -depth, glass)
        # Open-ended rail profiles are seated between the jambs, with no end
        # faces shared with the wall. Leave an actual air gap above the parapet.
        rails = (
            [
                (low, low + 0.34),
                (low + 0.53, low + 0.58),
                (low + 0.75, low + 0.80),
                (low + 0.95, low + 1.0),
            ]
            if surface.kind == 'slot'
            else [(low, low + 0.51), (low + 0.76, low + 0.82)]
        )
        for h0, h1 in rails:
            a, b = -0.09, -0.20
            material = wall if h0 == low else frame
            surface.rect(p, left, right, h0, h1, a, material)
            surface.face(
                p,
                [(right, b, h0), (left, b, h0), (left, b, h1), (right, b, h1)],
                material,
            )
            surface.face(
                p,
                [(left, a, h1), (right, a, h1), (right, b, h1), (left, b, h1)],
                material,
            )
            if h0 > low:
                surface.face(
                    p,
                    [(right, a, h0), (left, a, h0), (left, b, h0), (right, b, h0)],
                    material,
                )
    else:
        # Partition the actual back face to make mullions, without layering
        # a glass plane or frame over another surface.
        divisions = (
            1
            if not detail
            else (3 if right - left > 3 else 2 if right - left > 1.15 else 1)
        )
        x = left
        for i in range(1, divisions):
            mid = left + (right - left) * i / divisions
            surface.rect(p, x, mid - 0.033, low, high, -depth, glass)
            surface.rect(p, mid - 0.033, mid + 0.033, low, high, -depth, frame)
            x = mid + 0.033
        surface.rect(p, x, right, low, high, -depth, glass)


def discard_faces(mesh, indices):
    kept = [i for i in range(len(mesh.f)) if i not in indices]
    used = sorted({v for i in kept for v in mesh.f[i]})
    remap = {a: b for b, a in enumerate(used)}
    mesh.face_uvs = {
        j: mesh.face_uvs[i] for j, i in enumerate(kept) if i in mesh.face_uvs
    }
    mesh.f = [tuple(remap[v] for v in mesh.f[i]) for i in kept]
    mesh.m = [mesh.m[i] for i in kept]
    mesh.parts = [
        (name, bisect_left(used, a), bisect_left(used, b)) for name, a, b in mesh.parts
    ]
    mesh.v = [mesh.v[v] for v in used]


def remove_fittings(
    mesh, wall, remove, part, lo, hi, bottom, top, min_depth, max_depth
):
    """Remove entire window, grid or crown primitives within the chosen section."""
    start, end = next((a, e) for n, a, e in mesh.parts if n == part)
    i = 0
    while i < len(mesh.f):
        face = mesh.f[i]
        if not start <= face[0] < end:
            i += 1
            continue
        pts = [mesh.v[j] for j in face]
        group = 1
        if (
            len(pts) == 4
            and max(v[2] for v in pts) - min(v[2] for v in pts) < 0.00001
            and i + 5 < len(mesh.f)
        ):
            lid = [mesh.v[j] for j in mesh.f[i + 5]]
            if min(v[2] for v in lid) > pts[0][2] and {v[:2] for v in pts} == {
                v[:2] for v in lid
            }:
                group = 6
                pts += lid
        if all(bottom - 0.001 <= p[2] <= top + 0.001 for p in pts) and all(
            lo - 0.005 <= u <= hi + 0.005 and min_depth <= d <= max_depth
            for u, d in (wall.local(p) for p in pts)
        ):
            remove.update(range(i, i + group))
        i += group
