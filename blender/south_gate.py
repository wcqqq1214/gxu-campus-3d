"""Current three-bay south gate: multiple 2018–2026 photo references.

Dimensions and unseen rear ornament are estimates. No geometry from the obsolete
freestanding-column gate is reused. Blender axes: east X, north Y, up Z.
"""

import json
import math
from functools import lru_cache
from pathlib import Path

import bpy

from geometry import Mesh


def prism(m, outline, y, depth, mat):
    """Extrude an X/Z silhouette, preserving the open space below the arch."""
    area = sum(
        a[0] * b[1] - b[0] * a[1] for a, b in zip(outline, outline[1:] + outline[:1])
    )
    if area < 0:
        outline = list(reversed(outline))
    front = [(x, y - depth / 2, z) for x, z in outline]
    back = [(x, y + depth / 2, z) for x, z in outline]
    m.face(front, mat)
    m.face(back[::-1], mat)
    for i in range(len(outline)):
        j = (i + 1) % len(outline)
        m.face([front[i], back[i], back[j], front[j]], mat)


def cornice(m, x, y, z, width, depth, height, mat):
    """A shallow sloped stone moulding, rather than a stack of square boxes."""
    bevel = min(0.09, height * 0.28)
    levels = [
        (-height / 2, width - 0.18, depth - 0.18),
        (-height / 2 + bevel, width, depth),
        (height / 2 - bevel * 0.5, width, depth),
        (height / 2, width - 0.06, depth - 0.06),
    ]
    rings = [
        [
            (x + sx * w / 2, y + sy * d / 2, z + h)
            for sx, sy in [(-1, -1), (1, -1), (1, 1), (-1, 1)]
        ]
        for h, w, d in levels
    ]
    m.face(rings[0][::-1], mat)
    m.face(rings[-1], mat)
    for a, b in zip(rings, rings[1:]):
        for i in range(4):
            j = (i + 1) % 4
            m.face([a[i], a[j], b[j], b[i]], mat)


def arch_band(m, cx, y, cz, radius, side, width, depth, mat, segments):
    """Flat stone archivolt following a quarter-circle, with a solid return."""
    outer = []
    inner = []
    for i in range(segments + 1):
        angle = i * math.pi / (2 * segments)
        outer.append(
            (
                cx + side * (radius + width) * math.cos(angle),
                cz + (radius + width) * math.sin(angle),
            )
        )
        inner.append(
            (cx + side * radius * math.cos(angle), cz + radius * math.sin(angle))
        )
    # Individual quads keep the curved strip planar and avoid concave n-gons.
    for i in range(segments):
        outline = [inner[i], outer[i], outer[i + 1], inner[i + 1]]
        if side < 0:
            outline.reverse()
        prism(m, outline, y, depth, mat)


def inscription(text, x, y, z, width, height, mat, detail):
    """Self-contained raised glyph meshes; bundled OFL font, no runtime font fetch."""
    path = str(Path(__file__).parent / 'fonts/MaShanZheng-Regular.ttf')
    font = bpy.data.fonts.get('MaShanZheng-Regular') or bpy.data.fonts.load(path)
    font.name = 'MaShanZheng-Regular'
    curve = bpy.data.curves.new('校名字形临时', 'FONT')
    curve.body = text
    curve.font = font
    curve.size = 1
    curve.extrude = 0.012
    curve.resolution_u = 8 if detail else 3
    curve.bevel_depth = 0.002 if detail else 0
    curve.bevel_resolution = 1
    obj = bpy.data.objects.new('校名字形临时', curve)
    bpy.context.scene.collection.objects.link(obj)
    deps = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(deps)
    mesh = evaluated.to_mesh()
    a = min(v.co.x for v in mesh.vertices)
    b = max(v.co.x for v in mesh.vertices)
    c = min(v.co.y for v in mesh.vertices)
    d = max(v.co.y for v in mesh.vertices)
    scale = min(width / (b - a), height / (d - c))
    m = Mesh()
    for face in mesh.polygons:
        # Text XY becomes the south-facing XZ plane, with extrusion toward south.
        m.face(
            [
                (
                    x + (mesh.vertices[i].co.x - (a + b) / 2) * scale,
                    y - mesh.vertices[i].co.z * scale,
                    z + (mesh.vertices[i].co.y - (c + d) / 2) * scale,
                )
                for i in face.vertices
            ],
            mat,
        )
    evaluated.to_mesh_clear()
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.curves.remove(curve)
    return m


@lru_cache(maxsize=1)
def wordmark_glyphs():
    return json.loads((Path(__file__).parent / 'fonts/gxu-wordmark.json').read_text())[
        'glyphs'
    ]


def gate_wordmark(x, y, z, width, height, mat):
    """Official handwritten outlines, spaced as four solid south-facing letters.

    The same silhouette is used for both LODs. Each stroke has front, back and
    side faces, including the holes; no image texture or font is loaded at runtime.
    """
    m = Mesh()
    glyphs = wordmark_glyphs()
    sizes = [1.0, 0.86, 0.9, 0.98]
    depth = 0.045
    glyph_widths = [
        max(p[0] for o in g['outlines'] for r in o['rings'] for p in r)
        - min(p[0] for o in g['outlines'] for r in o['rings'] for p in r)
        for g in glyphs
    ]
    step = (
        width - height * (glyph_widths[0] * sizes[0] + glyph_widths[-1] * sizes[-1]) / 2
    ) / 3
    for i, (glyph, size) in enumerate(zip(glyphs, sizes)):
        cx = x + (i - 1.5) * step
        scale = height * size
        for outline in glyph['outlines']:
            rings = [
                [(cx + a * scale, z + b * scale) for a, b in ring]
                for ring in outline['rings']
            ]
            flat = [p for ring in rings for p in ring]
            for start in range(0, len(outline['triangles']), 3):
                triangle = [flat[k] for k in outline['triangles'][start : start + 3]]
                m.face([(a, y - depth, b) for a, b in triangle], mat)
                m.face([(a, y, b) for a, b in reversed(triangle)], mat)
            for ring in rings:
                for a, b in zip(ring, ring[1:] + ring[:1]):
                    m.face(
                        [
                            (a[0], y, a[1]),
                            (b[0], y, b[1]),
                            (b[0], y - depth, b[1]),
                            (a[0], y - depth, a[1]),
                        ],
                        mat,
                    )
    return m


def pavilion(m, x, y, z, scale, C, detail):
    stone = C['gateStone']
    trim = C['gateTrim']
    s = scale
    for h, w, d in [(0.10, 1.55, 1.55), (0.27, 1.32, 1.32), (0.43, 1.08, 1.08)]:
        m.box(x, y, z + h * s, w * s, d * s, 0.18 * s, stone)
    for dx in [-0.40, 0.40]:
        for dy in [-0.40, 0.40]:
            m.box(
                x + dx * s, y + dy * s, z + 1.0 * s, 0.19 * s, 0.19 * s, 1.0 * s, stone
            )
    for sy in [-1, 1]:
        m.box(x, y + sy * 0.40 * s, z + 1.53 * s, 1.0 * s, 0.20 * s, 0.19 * s, trim)
    for sx in [-1, 1]:
        m.box(x + sx * 0.40 * s, y, z + 1.53 * s, 0.20 * s, 1.0 * s, 0.19 * s, trim)
    # Four arched openings, clearly visible in the 2022 oblique photograph.
    for rotation in range(4):
        face = Mesh()
        r = 0.305 * s
        spring = z + 1.13 * s
        segments = 12 if detail else 6
        for side in [-1, 1]:
            arc = [
                (
                    x + side * r * math.cos(i * math.pi / (2 * segments)),
                    spring + r * math.sin(i * math.pi / (2 * segments)),
                )
                for i in range(segments + 1)
            ]
            outline = [(x + side * r, z + 1.45 * s)] + arc
            if side < 0:
                outline.reverse()
            prism(face, outline, y - 0.40 * s, 0.20 * s, stone)
        face.rotate_z(x, y, rotation * math.pi / 2)
        m.extend(face)
    cornice(m, x, y, z + 1.62 * s, 1.32 * s, 1.32 * s, 0.17 * s, trim)
    # Square pyramidal caps, with a closed underside and a narrow eave.
    base = [
        (x + dx * 0.66 * s, y + dy * 0.66 * s, z + 1.71 * s)
        for dx, dy in [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    ]
    peak = (x, y, z + 2.19 * s)
    m.face(base[::-1], stone)
    for a, b in zip(base, base[1:] + base[:1]):
        m.face([a, b, peak], stone)


def soffit(m, x, y, z, C, detail):
    """Three recessed ceiling fields and bronze-drum lamps, 2018 upward photo.

    Raised frames below the beam leave its underside as the coffer back plane.
    Lamp engraving is a geometric approximation; dimensions are not surveyed.
    """
    for cx in [-9.2, 0, 9.2]:
        for drop, inset in [(0.10, 0), (0.23, 0.13), (0.34, 0.27)]:
            w = 9.2 - 2 * inset
            d = 3.35 - 2 * inset
            # Miter the four corners: overlapping boxes create coplanar black seams.
            outer = [
                (x + cx + a * w / 2, y + b * d / 2)
                for a, b in [(-1, -1), (1, -1), (1, 1), (-1, 1)]
            ]
            inner = [
                (x + cx + a * (w / 2 - 0.11), y + b * (d / 2 - 0.11))
                for a, b in [(-1, -1), (1, -1), (1, 1), (-1, 1)]
            ]
            for i in range(4):
                j = (i + 1) % 4
                for h in [-0.06, 0.06]:
                    ring = [
                        (*p, z - drop + h)
                        for p in [outer[i], outer[j], inner[j], inner[i]]
                    ]
                    m.face(ring if h > 0 else ring[::-1], C['gateTrim'])
                for ring in [outer, inner[::-1]]:
                    a, b = ring[i], ring[j]
                    m.face(
                        [
                            (*a, z - drop - 0.06),
                            (*b, z - drop - 0.06),
                            (*b, z - drop + 0.06),
                            (*a, z - drop + 0.06),
                        ],
                        C['gateTrim'],
                    )
        r = 0.68 if cx == 0 else 0.45
        h = 0.64 if cx == 0 else 0.50
        n = 32 if detail else 16
        zz = z - 0.40
        # Suspended neck, flared shoulders, translucent-looking warm drum body.
        m.cylinder(x + cx, y, zz - 0.09, r * 0.23, 0.30, C['wood'], n)
        m.cylinder(
            x + cx, y, zz - 0.24, r * 0.58, 0.20, C['gateTrim'], n, topr=r * 0.30
        )
        body = zz - 0.36 - h / 2
        m.cylinder(x + cx, y, body, r, h, C['gateTrim'], n)
        for dz in [-h / 2, -h / 2 + 0.06, h / 2 - 0.06, h / 2]:
            m.cylinder(x + cx, y, body + dz, r * 1.025, 0.035, C['wood'], n)
        for j in range(12):
            a = j * math.tau / 12
            dx, dy = r * math.cos(a), r * math.sin(a)
            m.line(
                (x + cx + dx, y + dy, body - h / 2),
                (x + cx + dx, y + dy, body + h / 2),
                0.014,
                C['wood'],
                4,
            )
        # Concentric underside rings and a restrained radial motif.
        for radius in [r * 0.68, r * 0.26]:
            for j in range(n):
                a = j * math.tau / n
                b = (j + 1) * math.tau / n
                m.line(
                    (
                        x + cx + radius * math.cos(a),
                        y + radius * math.sin(a),
                        body - h / 2 - 0.025,
                    ),
                    (
                        x + cx + radius * math.cos(b),
                        y + radius * math.sin(b),
                        body - h / 2 - 0.025,
                    ),
                    0.016,
                    C['wood'],
                    4,
                )
        for j in range(12):
            a = j * math.tau / 12
            m.line(
                (
                    x + cx + r * 0.28 * math.cos(a),
                    y + r * 0.28 * math.sin(a),
                    body - h / 2 - 0.025,
                ),
                (
                    x + cx + r * 0.60 * math.cos(a),
                    y + r * 0.60 * math.sin(a),
                    body - h / 2 - 0.025,
                ),
                0.014,
                C['wood'],
                4,
            )


def relief_ribbon(m, points, y, width, depth, mat, closed=False):
    """Shallow bevelled stone ribbon, with joined corners instead of round wire."""
    rings = []
    n = len(points)
    for i, (x, z) in enumerate(points):
        a = points[(i - 1) % n] if closed or i else points[0]
        b = points[(i + 1) % n] if closed or i < n - 1 else points[-1]
        dx = b[0] - a[0]
        dz = b[1] - a[1]
        length = math.hypot(dx, dz)
        nx, nz = -dz / length, dx / length
        rings.append(
            [
                (x + nx * w, y - h, z + nz * w)
                for w, h in [
                    (-width / 2, 0),
                    (-width * 0.28, depth),
                    (width * 0.28, depth),
                    (width / 2, 0),
                ]
            ]
        )
    pairs = list(zip(rings, rings[1:]))
    if closed:
        pairs.append((rings[-1], rings[0]))
    else:
        m.face(rings[0][::-1], mat)
        m.face(rings[-1], mat)
    for a, b in pairs:
        for i in range(4):
            j = (i + 1) % 4
            m.face([a[i], b[i], b[j], a[j]], mat)


def rosette(m, x, y, z, C, detail):
    """Four small curled leaves; a geometric reading of the photographed carving."""
    for petal in range(4):
        angle = petal * math.pi / 2
        co, si = math.cos(angle), math.sin(angle)
        points = []
        steps = 14 if detail else 8
        for i in range(steps + 1):
            t = i / steps
            r = 0.13 * (1 - t) + 0.018
            a = -math.pi / 2 + t * math.pi * 1.65
            u = 0.15 + r * math.cos(a)
            v = r * math.sin(a)
            points.append((x + 1.1 * (u * co - v * si), z + 1.1 * (u * si + v * co)))
        relief_ribbon(m, points, y, 0.066, 0.065, C['gateTrim'])
    m.ellipsoid(x, y - 0.025, z, 0.045, 0.04, 0.045, C['gateTrim'], 8, 4)


def panel(m, x, y, z, width, height, C, detail):
    stone = C['gateStone']
    trim = C['gateTrim']
    m.box(x, y, z, width + 0.25, 0.10, height + 0.25, trim)
    m.box(x, y - 0.07, z, width, 0.06, height, C['gateRecess'])
    # Complete the four-sided inset frame in both LODs.
    for dx in [-1, 1]:
        m.box(
            x + dx * (width / 2 + 0.065), y - 0.1, z, 0.08, 0.12, height + 0.20, stone
        )
    for dz in [-1, 1]:
        m.box(
            x, y - 0.1, z + dz * (height / 2 + 0.065), width + 0.21, 0.12, 0.08, stone
        )
    if not detail:
        return
    # Flat bevelled diamonds read as carved stone, retaining the photographed
    # diagonal rhythm without presenting the approximation as a carving scan.
    rows = int(height / 0.43)
    step = (height - 0.18) / rows
    for row in range(rows):
        zz = z - height / 2 + 0.09 + (row + 0.5) * step
        for col in [-1, 0, 1]:
            xx = x + col * width * 0.29
            rx = width * 0.125
            rz = step * 0.38
            p = [(xx - rx, zz), (xx, zz + rz), (xx + rx, zz), (xx, zz - rz)]
            relief_ribbon(m, p, y - 0.10, 0.075, 0.045, stone, closed=True)


def south_gate(x, y, z, C, detail=True, footprint_width=66.65, footprint_depth=5.3):
    m = Mesh()
    stone = C['gateStone']
    trim = C['gateTrim']
    joint = C['gateJoint']
    # Four rectangular piers; centre opening is wider and higher than the side bays.
    for i, px in enumerate([-31, -16, 16, 31]):
        high = abs(px) == 16
        pw = 4.2 if high else 3.4
        ph = 16.0 if high else 11.4
        part = Mesh()
        xx = x + px
        part.box(xx, y, z + 0.23, pw + 1.2, 5.3, 0.46, trim)
        part.box(xx, y, z + 0.58, pw + 0.7, 4.7, 0.26, stone)
        part.box(xx, y, z + 1.15, pw + 0.35, 4.4, 0.88, stone)
        # Narrow recessed joints between actual stone courses.
        n = 6 if high else 4
        hh = (ph - 1.6) / n
        for row in range(n):
            part.box(xx, y, z + 1.6 + (row + 0.5) * hh, pw, 4.0, hh - 0.035, stone)
        for zz, ww, dd, hh in [
            (ph - 3.0, pw + 0.5, 4.5, 0.30),
            (ph - 0.30, pw + 1.0, 4.9, 0.40),
            (ph + 0.03, pw + 1.25, 5.1, 0.24),
        ]:
            cornice(part, xx, y, z + zz, ww, dd, hh, trim)
        if high:
            # Rear repeats the structural panel; its exact ornament is inferred.
            front = Mesh()
            panel(front, xx, y - 2.03, z + 6.4, 1.15, 7.3, C, detail)
            part.extend(front)
            rear = Mesh()
            panel(rear, xx, y - 2.03, z + 6.4, 1.15, 7.3, C, detail)
            rear.rotate_z(xx, y, math.pi)
            part.extend(rear)
        elif detail:
            for sy in [-1, 1]:
                for dx in [-0.65, 0.65]:
                    part.box(xx + dx, y + sy * 2.03, z + 4.9, 0.08, 0.08, 5.9, joint)
                part.box(xx, y + sy * 2.03, z + 7.85, 1.35, 0.08, 0.08, joint)
        # User-confirmed equal front/rear pair. Perspective is not a size ratio.
        lantern_ranges = []
        for sy in [-1, 1]:
            size = 1.18 if high else 0.94
            py = y + sy * 1.20
            lantern = Mesh()
            pavilion(lantern, xx, py, z + ph + 0.20, size, C, detail)
            # Keep the small square pavilions proportional when fitting gate depth.
            ratio = (footprint_width / 66.65) / (footprint_depth / 5.3)
            lantern.v = [(a, py + (b - py) * ratio, c) for a, b, c in lantern.v]
            start = len(part.v)
            part.extend(lantern)
            lantern_ranges.append(
                (f'小亭-{i + 1:02}-' + ('前' if sy < 0 else '后'), start, len(part.v))
            )
        offset = len(m.v)
        m.add_part(f'门柱-{i + 1:02} · 石材分缝与顶部小亭', part)
        m.parts.extend((name, offset + a, offset + b) for name, a, b in lantern_ranges)

    # Three genuinely open portals, with quadrant corner brackets and layered cornices.
    for name, cx, span, underside, top in [
        ('中央门跨', 0, 27.8, 11.3, 15.85),
        ('西侧门跨', -23.7, 11.24, 7.7, 11.23),
        ('东侧门跨', 23.7, 11.24, 7.7, 11.23),
    ]:
        part = Mesh()
        xx = x + cx
        radius = 2.25 if cx == 0 else 1.45
        part.box(xx, y, z + (underside + top) / 2, span, 3.35, top - underside, stone)
        for height, width, depth in [
            (underside + 0.10, 0.15, 3.65),
            (underside + 1.55, 0.32, 3.85),
            (top, 0.36, 3.95),
        ]:
            cornice(part, xx, y, z + height, span + 0.18, depth, width, trim)
        for side in [-1, 1]:
            edge = xx + side * span / 2
            center = edge - side * radius
            spring = z + underside - radius
            arc = [
                (
                    center + side * radius * math.cos(t * math.pi / 2),
                    spring + radius * math.sin(t * math.pi / 2),
                )
                for t in [
                    j / (28 if detail else 10)
                    for j in range((28 if detail else 10) + 1)
                ]
            ]
            prism(part, [(edge, z + underside)] + arc, y, 3.35, stone)
            for sy in [-1, 1]:
                segments = 24 if detail else 10
                arch_band(
                    part,
                    center,
                    y + sy * 1.73,
                    spring,
                    radius,
                    side,
                    0.19,
                    0.15,
                    trim,
                    segments,
                )
                arch_band(
                    part,
                    center,
                    y + sy * 1.70,
                    spring,
                    radius + 0.25,
                    side,
                    0.10,
                    0.10,
                    stone,
                    segments,
                )
        if detail:
            for sy in [-1, 1]:
                # Recessed herringbone frieze, bounded by continuous stone fillets.
                part.box(
                    xx,
                    y + sy * 1.68,
                    z + underside + 1.84,
                    span,
                    0.035,
                    0.37,
                    C['gateRecess'],
                )
                for zz in [underside + 1.63, underside + 2.05]:
                    part.box(xx, y + sy * 1.73, z + zz, span, 0.12, 0.07, trim)
                for j in range(int(span / 0.32)):
                    xx0 = xx - span / 2 + 0.04 + j * 0.32
                    for direction in [-1, 1]:
                        part.line(
                            (xx0, y + sy * 1.73, z + underside + 1.84),
                            (
                                xx0 + 0.23,
                                y + sy * 1.73,
                                z + underside + 1.84 + direction * 0.15,
                            ),
                            0.023,
                            trim,
                            4,
                        )
        m.add_part(name + ' · 弧形承托与叠檐', part)

    ceiling = Mesh()
    soffit(ceiling, x, y, z + 11.3, C, detail)
    m.add_part('中央门洞分格吊顶与三盏铜鼓形灯', ceiling)

    plaque = Mesh()
    plaque.box(x, y, z + 14.64, 14.6, 3.9, 3.20, trim)
    for sy in [-1, 1]:
        plaque.box(x, y + sy * 2.00, z + 14.66, 13.80, 0.12, 2.72, C['gateRecess'])
        plaque.box(x, y + sy * 2.08, z + 14.66, 13.53, 0.12, 2.47, stone)
    plaque.box(x, y, z + 16.28, 14.95, 4.18, 0.24, trim)
    prism(
        plaque,
        [(x - 3.5, z + 16.40), (x + 3.5, z + 16.40), (x, z + 16.92)],
        y,
        3.6,
        stone,
    )
    m.add_part('中央校名匾额 · 山花与嵌框', plaque)
    # Trace the official seal's wordmark, retaining the individual brush silhouettes.
    letters = gate_wordmark(x, y - 2.135, z + 14.65, 10.4, 2.05, C['gateRed'])
    m.add_part('南向红色立体校名 · 官方题字轮廓', letters)
    # Four-lobed rosettes either side of the plaque, kept as raised stone geometry.
    ornaments = Mesh()
    front = Mesh()
    for side in [-1, 1]:
        for i in range(4):
            rosette(front, x + side * (8.5 + i * 1.45), y - 1.68, z + 14.50, C, detail)
    ornaments.extend(front)
    front.rotate_z(x, y, math.pi)
    ornaments.extend(front)
    m.add_part('梁面四瓣石雕纹样', ornaments)
    # Fit the actual mapped gate footprint. Vertical scale follows width (no exaggeration).
    sx = footprint_width / 66.65
    sy = footprint_depth / 5.3
    # Mapped road surface is draped 0.40 m above the DEM; retain visible plinths.
    m.v = [
        (x + (a - x) * sx, y + (b - y) * sy, z + 0.45 + (c - z) * sx) for a, b, c in m.v
    ]
    # Forecourt uses actual world metres; do not stretch pots/slabs with the gate.
    from south_gate_site import forecourt

    site = forecourt(x, y, C, detail)
    start = len(m.v)
    m.extend(site)
    m.parts.extend((name, start + a, start + b) for name, a, b in site.parts)
    return m
