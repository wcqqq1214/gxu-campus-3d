"""Clip only the observed facade volumes. Preserve original UVs, material and part ranges."""

from bisect import bisect_left
from math import atan2, hypot

from geometry import Mesh


class Facade:
    def __init__(self, x, y, nx, ny, datum):
        length = hypot(nx, ny)
        self.x, self.y, self.nx, self.ny, self.z = x, y, nx / length, ny / length, datum
        self.tx, self.ty = -self.ny, self.nx
        self.angle = atan2(self.ty, self.tx)

    def point(self, u, v, h):
        return (
            self.x + self.tx * u + self.nx * v,
            self.y + self.ty * u + self.ny * v,
            self.z + h,
        )

    def local(self, p):
        x, y, z = p
        x -= self.x
        y -= self.y
        return (x * self.tx + y * self.ty, x * self.nx + y * self.ny, z - self.z)

    def box(self, m, C, u0, u1, v0, v1, h0, h1, mat):
        m.box(
            *self.point((u0 + u1) / 2, (v0 + v1) / 2, (h0 + h1) / 2),
            u1 - u0,
            v1 - v0,
            h1 - h0,
            C['Office ' + mat],
            self.angle,
        )


def cut(mesh, frame, limits):
    cuts = [(3 + i // 2, v, 1 if i % 2 == 0 else -1) for i, v in enumerate(limits)]
    out = Mesh()
    starts = []
    offsets = []
    for idx, (face, mat) in enumerate(zip(mesh.f, mesh.m)):
        starts.append(min(face))
        offsets.append(len(out.v))
        uv = mesh.face_uvs.get(idx)
        pending = [
            (*mesh.v[j], *frame.local(mesh.v[j]), *(uv[n] if uv else (0, 0)))
            for n, j in enumerate(face)
        ]
        pieces = []
        if any(max((p[i] - v) * sign for p in pending) <= 1e-7 for i, v, sign in cuts):
            pieces.append(pending)
        else:
            for i, v, sign in cuts:
                inside = []
                outside = []
                a = pending[-1]
                for b in pending:
                    da = (a[i] - v) * sign
                    db = (b[i] - v) * sign
                    if da * db < 0:
                        t = da / (da - db)
                        cross = tuple(a0 + (b0 - a0) * t for a0, b0 in zip(a, b))
                        inside.append(cross)
                        outside.append(cross)
                    if db >= 0:
                        inside.append(b)
                    if db <= 0:
                        outside.append(b)
                    a = b
                if len(outside) >= 3:
                    pieces.append(outside)
                pending = inside
                if len(pending) < 3:
                    break
        for poly in pieces:
            clean = []
            for p in poly:
                if not clean or p[:3] != clean[-1][:3]:
                    clean.append(p)
            if len(clean) > 1 and clean[0][:3] == clean[-1][:3]:
                clean.pop()
            if len({p[:3] for p in clean}) < 3:
                continue
            out.face(
                [p[:3] for p in clean], mat, uvs=[p[6:8] for p in clean] if uv else None
            )
    offsets.append(len(out.v))
    for label, a, b in mesh.parts:
        lo = offsets[bisect_left(starts, a)]
        hi = offsets[bisect_left(starts, b)]
        if hi > lo:
            out.parts.append((label, lo, hi))
    out.xy_uv_materials = mesh.xy_uv_materials.copy()
    out.ground_uv_bounds = list(mesh.ground_uv_bounds)
    return out


def opening(m, f, C, left, right, base, top, depth, divisions, detail, door=False):
    # The glazing and sash frames sit in front of the recess back, behind the soffit.
    f.box(m, C, left, right, depth, depth + 0.06, base, top, 'opening')
    for i in range(divisions + 1):
        x = left + (right - left) * i / divisions
        f.box(
            m, C, x - 0.031, x + 0.031, depth + 0.06, depth + 0.115, base, top, 'frame'
        )
    for h in [base + 0.03, top - 0.03] + ([top - 0.48] if detail else []):
        f.box(
            m,
            C,
            left,
            right,
            depth + 0.06,
            depth + 0.116,
            h - 0.028,
            h + 0.028,
            'frame',
        )
    if door and detail:
        for i in range(divisions):
            x = left + (right - left) * (i + 0.86) / divisions
            f.box(
                m,
                C,
                x - 0.017,
                x + 0.017,
                depth + 0.115,
                depth + 0.18,
                base + 0.76,
                base + 1.05,
                'iron',
            )


def recess_shell(m, f, C, a, b, depth, front, lo, hi, material, back=True):
    # Side, floor and ceiling solids close the hole all the way to the retained shell.
    if back:
        f.box(m, C, a, b, -depth - 0.10, -depth, lo, hi, material)
    for x in (a, b):
        f.box(m, C, x - 0.055, x + 0.055, -depth, front, lo, hi, material)
    for z in (lo, hi):
        f.box(m, C, a, b, -depth, front, z - 0.075, z + 0.075, material)
