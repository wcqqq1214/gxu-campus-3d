"""Wall coordinates, mesh partitioning and materials shared by the residences."""

from math import atan2, hypot
from pathlib import Path

import bpy

from geometry import MATERIALS, Mesh, material

_FINISHES = {
    'clay': (0.51, 0.225, 0.155),
    'tile': (0.50, 0.29, 0.215),
    'cream': (0.73, 0.665, 0.575),
    'chalk': (0.76, 0.755, 0.695),
    'glass': (0.095, 0.115, 0.115),
    'shade': (0.126, 0.094, 0.079),
    'roof': (0.36, 0.345, 0.30),
    'roofRed': (0.385, 0.225, 0.169),
    'roofDark': (0.145, 0.15, 0.124),
    'court': (0.405, 0.405, 0.365),
    'metal': (0.255, 0.25, 0.223),
}


def finish_material(C, name, color, image=None):
    if name not in C:
        index = C[name] = material(name, color)
        if image is not None:
            tree = MATERIALS[index].node_tree
            texture = tree.nodes.new('ShaderNodeTexImage')
            texture.image = bpy.data.images.load(str(image), check_existing=True)
            texture.image.pack()
            tree.links.new(
                texture.outputs['Color'],
                tree.nodes['Principled BSDF'].inputs['Base Color'],
            )
    return C[name]


def local_texture(C, name, color, filename):
    return finish_material(
        C, name, color, Path(__file__).with_name('textures') / filename
    )


def exterior_palette(C):
    return {
        name: finish_material(C, 'WestDormExterior_' + name, color)
        for name, color in _FINISHES.items()
    }


class _Edge:
    def __init__(self, a, b, sign):
        self.a, self.b = a, b
        self.sign = sign
        dx, dy = b[0] - a[0], b[1] - a[1]
        self.length = hypot(dx, dy)
        self.tx, self.ty = dx / self.length, dy / self.length
        self.nx, self.ny = sign * self.ty, -sign * self.tx
        self.angle = atan2(dy, dx)

    def wall(self, z):
        """Orient the wall so its positive depth faces the street."""
        a, b = (self.a, self.b) if self.sign > 0 else (self.b, self.a)
        return _Wall(a, b, z)

    def point(self, u, out, h):
        return (
            self.a[0] + u * self.tx + out * self.nx,
            self.a[1] + u * self.ty + out * self.ny,
            h,
        )

    def block(self, mesh, start, end, lo, hi, inner, outer, mat):
        p = self.point((start + end) / 2, (inner + outer) / 2, (lo + hi) / 2)
        mesh.box(*p, end - start, outer - inner, hi - lo, mat, self.angle)

    def panel(self, mesh, a, b, lo, hi, offset, mat):
        pts = [
            self.point(a, offset, lo),
            self.point(b, offset, lo),
            self.point(b, offset, hi),
            self.point(a, offset, hi),
        ]
        if self.ty * self.nx - self.tx * self.ny < 0:
            pts.reverse()
        mesh.face(pts, mat)


def _edges(ring):
    sign = (
        1 if sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:])) > 0 else -1
    )
    return [_Edge(a, b, sign) for a, b in zip(ring, ring[1:]) if a != b]


def _retain_part(source, target, prefix):
    for name, start, end in source.parts:
        if not name.startswith(prefix):
            continue
        part = Mesh()
        for i, face in enumerate(source.f):
            if start <= face[0] < end:
                part.face(
                    [source.v[v] for v in face], source.m[i], source.face_uvs.get(i)
                )
        if part.f:
            target.add_part(name, part)


def _window(mesh, edge, mid, width, lo, hi, mats, detail):
    # The light reveal and dark glass are on separate exterior planes.
    edge.panel(
        mesh,
        mid - width / 2 - 0.095,
        mid + width / 2 + 0.095,
        lo - 0.09,
        hi + 0.09,
        0.024,
        mats['cream'],
    )
    edge.panel(mesh, mid - width / 2, mid + width / 2, lo, hi, 0.04, mats['glass'])
    if detail and width > 1.3:
        edge.panel(mesh, mid - 0.031, mid + 0.031, lo, hi, 0.057, mats['metal'])


def _attic(mesh, zcut, mat):
    """Split only tall vertical shell quads. Preserve lower-face UVs by interpolation."""
    lo, hi = _range(mesh, '01_')
    first_new_vertex = len(mesh.v)
    for i, face in enumerate(mesh.f.copy()):
        if not lo <= face[0] < hi or len(face) != 4:
            continue
        pts = [mesh.v[v] for v in face]
        if not min(v[2] for v in pts) + 1 < zcut < max(v[2] for v in pts) - 0.1:
            continue
        uv = mesh.face_uvs.get(i)
        lower, upper, uv_low, uv_high = [], [], [], []
        for k, p in enumerate(pts):
            j = (k + 1) % 4
            q = pts[j]
            (lower if p[2] < zcut else upper).append(face[k])
            if uv:
                (uv_low if p[2] < zcut else uv_high).append(uv[k])
            if (p[2] < zcut) == (q[2] < zcut):
                continue
            t = (zcut - p[2]) / (q[2] - p[2])
            idx = len(mesh.v)
            mesh.v.append(tuple(a + (b - a) * t for a, b in zip(p, q)))
            lower.append(idx)
            upper.append(idx)
            if uv:
                pt = tuple(a + (b - a) * t for a, b in zip(uv[k], uv[j]))
                uv_low.append(pt)
                uv_high.append(pt)
        mesh.f[i] = tuple(lower)
        if uv:
            mesh.face_uvs[i] = uv_low
            mesh.face_uvs[len(mesh.f)] = uv_high
        mesh.f.append(tuple(upper))
        mesh.m.append(mat)
    mesh.parts.append(('顶层浅色面砖分界', first_new_vertex, len(mesh.v)))


def _paint_walls(mesh, mat):
    lo, hi = _range(mesh, '01_')
    for i, face in enumerate(mesh.f):
        if lo <= face[0] < hi:
            heights = [mesh.v[v][2] for v in face]
            if max(heights) - min(heights) > 1:
                mesh.m[i] = mat


class _Wall:
    """Wall trace ordered so the right-hand plan normal faces the viewer."""

    def __init__(self, a, b, z):
        self.x, self.y = a
        dx, dy = b[0] - a[0], b[1] - a[1]
        self.width = hypot(dx, dy)
        self.tx, self.ty = dx / self.width, dy / self.width
        self.nx, self.ny = self.ty, -self.tx
        self.z = z

    def point(self, u, v, d=0):
        return (
            self.x + u * self.tx + d * self.nx,
            self.y + u * self.ty + d * self.ny,
            self.z + v,
        )

    def uv_depth(self, p):
        x, y = p[0] - self.x, p[1] - self.y
        return x * self.tx + y * self.ty, x * self.nx + y * self.ny

    def face(self, m, l, r, b, t, mat, depth=0):
        if r - l < 0.00001 or t - b < 0.00001:
            return
        coords = [(l, b), (r, b), (r, t), (l, t)]
        m.face(
            [self.point(x, y, depth) for x, y in coords],
            mat,
            [(x / 4, y / 4) for x, y in coords],
        )

    def cross_section(self, m, l, r, b, t, depth, mat):
        # Four reveals between the outer aperture and its recessed glazing.
        corners = [(l, b), (r, b), (r, t), (l, t)]
        for i, (u, v) in enumerate(corners):
            x, y = corners[(i + 1) % 4]
            m.face(
                [
                    self.point(u, v),
                    self.point(x, y),
                    self.point(x, y, depth),
                    self.point(u, v, depth),
                ],
                mat,
            )

    def ledge(self, m, l, r, lo, hi, inside, outside, mat, front=None):
        if front is None:
            self.face(m, l, r, lo, hi, mat, outside)
        else:
            m.face(
                [
                    self.point(l, lo, outside),
                    self.point(r, lo, outside),
                    self.point(r, hi, outside),
                    self.point(l, hi, outside),
                ],
                front,
                [(0, 0), (1, 0), (1, 1), (0, 1)],
            )
        for t, ds in ((hi, (outside, inside)), (lo, (inside, outside))):
            m.face(
                [
                    self.point(l, t, ds[0]),
                    self.point(r, t, ds[0]),
                    self.point(r, t, ds[1]),
                    self.point(l, t, ds[1]),
                ],
                mat,
            )
        for u, ds in ((l, (outside, inside)), (r, (inside, outside))):
            m.face(
                [
                    self.point(u, lo, ds[0]),
                    self.point(u, hi, ds[0]),
                    self.point(u, hi, ds[1]),
                    self.point(u, lo, ds[1]),
                ],
                mat,
            )


def _range(mesh, prefix):
    return next((a, b) for n, a, b in mesh.parts if n.startswith(prefix))


def _remove_faces(mesh, doomed):
    # Keep all old vertex group ranges and remap explicit UVs to the surviving faces.
    faces = []
    mats = []
    uvs = {}
    for i, f in enumerate(mesh.f):
        if i in doomed:
            continue
        if i in mesh.face_uvs:
            uvs[len(faces)] = mesh.face_uvs[i]
        faces.append(f)
        mats.append(mesh.m[i])
    used = {v for f in faces for v in f}
    prefix = [0]
    verts = []
    for i, v in enumerate(mesh.v):
        if i in used:
            verts.append(v)
        prefix.append(len(verts))
    mesh.v = verts
    mesh.f = [tuple(prefix[v] for v in f) for f in faces]
    mesh.parts = [
        (label, prefix[a], prefix[b])
        for label, a, b in mesh.parts
        if prefix[a] < prefix[b]
    ]
    mesh.m, mesh.face_uvs = mats, uvs


def _glazing(m, w, l, r, b, t, mat, detail):
    # The border, mullions and panes partition a single recessed plane.
    reveal, frame, glass = mat['reveal'], mat['frame'], mat['glass']
    d = -0.135
    w.cross_section(m, l, r, b, t, d, reveal)
    edge = 0.055
    w.face(m, l, r, b, b + edge, frame, d)
    w.face(m, l, r, t - edge, t, frame, d)
    w.face(m, l, l + edge, b + edge, t - edge, frame, d)
    w.face(m, r - edge, r, b + edge, t - edge, frame, d)
    count = (3 if r - l > 1.85 else 2) if detail or r - l > 1.1 else 1
    width = (r - l - 2 * edge) / count
    for j in range(count):
        x = l + edge + j * width
        if j:
            w.face(m, x - 0.026, x + 0.026, b + edge, t - edge, frame, d)
        w.face(
            m,
            x + (0.026 if j else 0),
            x + width - (0.026 if j + 1 < count else 0),
            b + edge,
            t - edge,
            glass,
            d,
        )


def _panel_course(m, w, base, top, openings, wall, mat, detail):
    x = 0.0
    for cx, width, lo, hi in openings:
        l, r = cx - width / 2, cx + width / 2
        w.face(m, x, l, base, top, wall)
        w.face(m, l, r, base, lo, wall)
        w.face(m, l, r, hi, top, wall)
        _glazing(m, w, l, r, lo, hi, mat, detail)
        x = r
    w.face(m, x, w.width, base, top, wall)


def _ring_walls(ring, z, hole=False):
    pts = ring[:-1]
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1]))
    if (area > 0) == hole:
        pts = pts[::-1]
    return [_Wall(a, b, z) for a, b in zip(pts, pts[1:] + pts[:1])]
