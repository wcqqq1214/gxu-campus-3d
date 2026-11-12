"""Huicui north hotel wing and shared journalism envelope; photo-scaled, not surveyed."""

import math

from geometry import Mesh
from south_gate import inscription


def compact_source(obj):
    """Weld coincident source vertices while retaining face UVs and named groups."""
    import bmesh

    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    bmesh.ops.remove_doubles(mesh, verts=list(mesh.verts), dist=0.000001)
    mesh.to_mesh(obj.data)
    mesh.free()
    obj.data.update()


def huicui(b, z, C, detail=True):
    e = b['architecture']
    m = Mesh()
    wall = C['huicuiWall']
    trim = C['huicuiTrim']
    glass = C['huicuiGlass']
    frame = C['huicuiFrame']
    x0, y0, x1, yn = e['bounds']
    height = b['height']
    back = yn - e['arcadeDepth']
    for i, p in enumerate(e['parts']):
        part = Mesh()
        part.extrude(
            p['polygons'],
            p['triangles'],
            z + (6.8 if i else -0.6),
            p['height'] + (0 if i else 0.6),
            wall,
            C['paleRoof'],
        )
        m.add_part(p['name'], part)
    ceiling = Mesh()
    p = e['arcadeCeiling']
    for poly, tri in zip(p['polygons'], p['triangles']):
        flat = [v for r in poly for v in r[:-1]]
        for i in range(0, len(tri), 3):
            ceiling.face(
                [(flat[k][0], flat[k][1], z + 6.8) for k in reversed(tri[i : i + 3])],
                trim,
            )
    m.add_part('北侧通高柱廊 · 真实退进与顶板', ceiling)

    def pane(out, x, y, zz, w, h, angle=0, normal=1, divisions=2):
        # Local pane faces south by default; north-facing panes use normal=-1.
        nx, ny = math.sin(angle) * normal, -math.cos(angle) * normal
        out.box(x + nx * 0.10, y + ny * 0.10, z + zz, w, 0.06, h, glass, angle)
        if not detail:
            return
        out.box(
            x + nx * 0.03, y + ny * 0.03, z + zz, w + 0.18, 0.12, h + 0.18, trim, angle
        )
        # Bring glass in front of the solid frame backing, then add raised mullions.
        out.box(x + nx * 0.15, y + ny * 0.15, z + zz, w, 0.055, h, glass, angle)
        for u in range(divisions + 1):
            xx = (u / divisions - 0.5) * w
            out.box(
                x + xx * math.cos(angle) + nx * 0.21,
                y + xx * math.sin(angle) + ny * 0.21,
                z + zz,
                0.055,
                0.065,
                h,
                frame,
                angle,
            )
        for v in [-0.5, 0, 0.5]:
            out.box(
                x + nx * 0.21,
                y + ny * 0.21,
                z + zz + v * h,
                w,
                0.065,
                0.055,
                frame,
                angle,
            )

    north = Mesh()
    # The two lower rows, two tightly spaced upper rows and framed seventh floor
    # are distinct in the official whole-building photograph.
    for zz in [8.35, 11.45]:
        for i in range(17):
            pane(north, -35.5 + i * 4.35, yn, zz, 2.55, 2.1, normal=-1, divisions=3)
    for zz in [14.85, 18.0]:
        for i in range(47):
            pane(north, -39.0 + i * 1.64, yn, zz, 0.97, 2.4, normal=-1, divisions=1)
    for i in range(18):
        pane(north, -35.5 + i * 4.16, yn, 21.45, 2.08, 2.65, normal=-1, divisions=2)
    for zz, depth, h in [
        (6.8, 0.7, 0.42),
        (9.94, 0.62, 0.2),
        (13.02, 1.25, 0.40),
        (19.60, 1.15, 0.42),
        (23.2, 0.75, 0.38),
    ]:
        north.box((x0 + x1) / 2, yn + 0.20, z + zz, x1 - x0 + 0.7, depth, h, trim)
    # Slender continuous stone fins over the closely spaced fifth/sixth-floor windows.
    for i in range(48):
        north.box(-39.82 + i * 1.64, yn + 0.26, z + 16.45, 0.20, 0.60, 5.95, trim)
    if detail:
        for i in range(29):
            north.box(
                x0 + 1 + i * 2.91,
                yn + 0.035,
                z + 21.48,
                0.018,
                0.06,
                3.02,
                C['gateJoint'],
            )
        for zz in [20.1, 22.8]:
            north.box(0, yn + 0.035, z + zz, x1 - x0 - 0.2, 0.06, 0.018, C['gateJoint'])
    m.add_part('北立面 · 方窗、密集窄窗、石材顶层与分层挑檐', north)

    arcade = Mesh()
    for x in [-38, -30.4, -22.8, -15.2, 15.2, 22.8, 30.4, 38]:
        arcade.cylinder(x, yn - 0.50, z + 3.69, 0.43, 6.22, trim, 16 if detail else 8)
        arcade.cylinder(x, yn - 0.50, z + 0.60, 0.58, 0.25, trim, 16 if detail else 8)
    # Dark glazing is behind the recessed external colonnade, never across its front.
    for i in range(20):
        pane(arcade, -38 + i * 4, back + 0.04, 3.35, 3.55, 5.6, normal=-1, divisions=2)
    arcade.box(0, (back + yn) / 2, z - 0.60, x1 - x0, yn - back, 2.0, trim)
    arcade.box(0, (back + yn) / 2, z + 0.49, x1 - x0, yn - back, 0.18, C['path'])
    m.add_part('北侧落地玻璃与八根通高圆柱', arcade)

    entry = Mesh()
    # Twin-column, metal-clad hotel canopy visible in the historic entrance close-up.
    entry.box(0, yn + 0.65, z + 4.78, 15.2, 7.8, 0.48, frame)
    entry.box(0, yn + 0.65, z + 5.05, 15.5, 8.0, 0.09, C['metal'])
    for x in [-6.25, 6.25]:
        entry.cylinder(x, yn + 3.3, z + 2.58, 0.49, 4.1, trim, 20 if detail else 10)
        entry.cylinder(x, yn + 3.3, z + 0.62, 0.64, 0.26, trim, 20 if detail else 10)
    entry.box(0, yn + 0.03, z + 5.89, 15.2, 0.20, 1.20, C['wood'])
    if detail:
        for i in range(100):
            entry.box(
                -7.45 + i * 0.15,
                yn + 0.18,
                z + 5.89,
                0.034,
                0.075,
                1.18,
                C['huicuiWall'],
            )
        for x in [-5, -2.5, 0, 2.5, 5]:
            for yy in [yn - 1.6, yn + 1.1, yn + 3.3]:
                entry.box(x, yy, z + 4.525, 0.12, 0.12, 0.018, C['lampGlass'])
        for x in [-5, 0, 5]:
            entry.box(x, yn + 0.65, z + 4.528, 0.012, 7.6, 0.01, C['dark'])
        for yy in [yn - 1.8, yn + 0.65, yn + 3.1]:
            entry.box(0, yy, z + 4.528, 15, 0.012, 0.01, C['dark'])
    # Raised lettering faces north, readable from the lawn. Bundled font -> mesh.
    text = inscription('荟萃楼', 0, 0, z + 4.8, 2.8, 0.65, trim, detail)
    text.rotate_z(0, 0, math.pi)
    text.v = [(x - 4.3, y + yn + 4.57, zz) for x, y, zz in text.v]
    entry.extend(text)
    # The north forecourt DEM is lower than the shared building anchor. Eight
    # estimated treads meet the slope; a buried foundation avoids floating risers.
    for i in range(8):
        depth = 7.0 - i * 0.80
        top = -0.44 + i * 1.02 / 7
        entry.box(0, yn + depth / 2, z + (top - 1.6) / 2, 16.2, depth, top + 1.6, trim)
    pane(entry, 0, back + 0.07, 2.25, 5.2, 3.3, normal=-1, divisions=4)
    if detail:
        for x in [-0.35, 0.35]:
            entry.line(
                (x, back + 0.40, z + 1.55),
                (x, back + 0.40, z + 2.2),
                0.028,
                C['metal'],
                8,
            )
    m.add_part('荟萃楼北门 · 双圆柱金属雨棚、字牌、玻璃门与踏步', entry)

    other = Mesh()
    roof = Mesh()
    # Retain all courtyard edges and the mapped curved western recess. Unseen
    # elevations receive explicitly estimated detail, without invented entrances.
    for ri, ring in enumerate(e['footprint']):
        area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:]))
        sign = (1 if area > 0 else -1) * (1 if ri == 0 else -1)
        for a, b1 in zip(ring, ring[1:]):
            dx, dy = b1[0] - a[0], b1[1] - a[1]
            length = math.hypot(dx, dy)
            if length < 0.4:
                continue
            angle = math.atan2(dy, dx)
            nx, ny = dy / length * sign, -dx / length * sign
            mx, my = (a[0] + b1[0]) / 2, (a[1] + b1[1]) / 2
            roof.box(mx, my, z + height + 0.38, length, 0.32, 0.76, trim, angle)
            roof.box(mx, my, z + height + 0.81, length + 0.1, 0.56, 0.12, trim, angle)
            if my > yn - 0.6 and ri == 0:
                continue
            n = max(1, round(length / 4.2))
            for zz in [2.7, 5.25, 8.35, 11.45, 14.85, 18.0, 21.45]:
                for i in range(n):
                    t = (i + 0.5) / n
                    x = a[0] + t * dx
                    y = a[1] + t * dy
                    # Do not cap the side ends of the north colonnade with glazing.
                    if zz < 6.8 and y > back - 0.5:
                        continue
                    pane(other, x, y, zz, min(2.3, length / n * 0.64), 1.9, angle, sign)
            for zz in [6.8, 13.02, 19.6]:
                other.box(
                    mx + nx * 0.14,
                    my + ny * 0.14,
                    z + zz,
                    length,
                    0.45,
                    0.22,
                    trim,
                    angle,
                )
    m.add_part('学院侧翼、内院与西侧弧形凹口 · 估算立面', other)
    m.add_part('平屋顶 · 外缘及内院女儿墙', roof)
    m.rotate_z(0, 0, e['angle'])
    ox, oy = e['origin']
    m.v = [(x + ox, y + oy, zz) for x, y, zz in m.v]
    return m
