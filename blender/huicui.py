"""Huicui north hotel wing and shared journalism envelope; photo-scaled, not surveyed."""

import math

from dining_interiors import interior_finish
from geometry import Mesh
from huicui_front import dining_windows, finishes, hotel_lobby, lobby_side_glazing
from huicui_stair import east_stair_entry


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
    finishes(C)
    e = b['architecture']
    m = Mesh()
    wall = C['huicuiWall']
    trim = C['huicuiTrim']
    glass = C['huiDiningGlass']
    frame = C['huicuiFrame']
    x0, y0, x1, yn = e['bounds']
    height = b['height']
    back = yn - e['arcadeDepth']
    for i, p in enumerate(e['parts']):
        part = Mesh()
        part.extrude(
            p['polygons'],
            p['triangles'],
            z + (p['base'] if i else -0.6),
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
                [
                    (flat[k][0], flat[k][1], z + e['arcadeClearHeight'])
                    for k in reversed(tri[i : i + 3])
                ],
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
    for zz in [10.83, 14.21]:
        for i in range(20):
            pane(north, -38.23 + i * 3.98, yn, zz, 2.35, 2.65, normal=-1, divisions=3)
    for zz in [19.08, 22.85]:
        for i in range(57):
            x = -34.95 + i * 1.33
            pane(north, x, yn, zz, 0.86, 2.18, normal=-1, divisions=1)
    dining_windows(north, yn, z, C, detail)
    for zz, depth, h in [
        (8.15, 0.7, 0.42),
        (12.73, 0.62, 0.2),
        (16.70, 1.25, 0.40),
        (24.52, 1.15, 0.42),
        (30.99, 0.26, 0.17),
    ]:
        north.box((x0 + x1) / 2, yn + 0.20, z + zz, x1 - x0 + 0.7, depth, h, trim)
    # Slender continuous stone fins over the closely spaced fifth/sixth-floor windows.
    for i in range(58):
        north.box(-35.61 + i * 1.33, yn + 0.26, z + 20.58, 0.19, 0.60, 7.50, trim)
    for x in (-40.9, -38.5):
        north.cylinder(x, yn - 0.26, z + 20.62, 0.35, 7.81, trim, 16 if detail else 8)
    if detail:
        for h in (17.05, 17.40, 17.77):
            north.box(-38.9, yn, z + h, 5.20, 0.07, 0.05, frame)
    m.add_part('北立面 · 方窗、密集窄窗、石材顶层与分层挑檐', north)

    arcade = Mesh()
    for x in [-38, -30.4, -22.8, -15.2, 15.2, 22.8, 30.4, 38]:
        arcade.cylinder(x, yn - 0.50, z + 4.365, 0.48, 7.57, trim, 16 if detail else 8)
        arcade.cylinder(x, yn - 0.50, z + 0.60, 0.58, 0.25, trim, 16 if detail else 8)
    # Dark glazing is behind the recessed external colonnade, never across its front.
    for i in range(20):
        x = -38 + i * 4
        if abs(x) > 12:
            pane(arcade, x, back + 0.04, 4.11, 3.72, 6.91, normal=-1, divisions=2)
    lobby_side_glazing(arcade, yn, z, C, detail)
    arcade.box(0, (back + yn) / 2, z - 0.60, x1 - x0, yn - back, 2.0, trim)
    arcade.box(0, (back + yn) / 2, z + 0.49, x1 - x0, yn - back, 0.18, C['path'])
    m.add_part('北侧落地玻璃与八根通高圆柱', arcade)

    entry = hotel_lobby(yn, z, C, detail)
    m.add_part('荟萃楼北门 · 双柱铝板雨棚、滑动玻璃门与两级踏步', entry)

    south_arcade = e.get('southArcade')
    if south_arcade:
        south = Mesh()
        soffit = e['arcadeClearHeight']
        for poly, tri in zip(south_arcade['polygons'], south_arcade['triangles']):
            flat = [v for ring in poly for v in ring[:-1]]
            for i in range(0, len(tri), 3):
                south.face(
                    [
                        (flat[k][0], flat[k][1], z + soffit)
                        for k in reversed(tri[i : i + 3])
                    ],
                    trim,
                )
        pitch = (x1 - x0) / 14
        for i in range(14):
            x = x0 + (i + 0.5) * pitch
            south.cylinder(
                x, y0 + 0.7, z + soffit / 2, 0.43, soffit, trim, 16 if detail else 8
            )
            pane(south, x, y0 + 3.1, 3.6, pitch - 0.55, 6.25, divisions=3)
        upper_pitch = (x1 - x0) / 42
        for i in range(42):
            x = x0 + (i + 0.5) * upper_pitch
            for zz in (19.08, 22.85):
                pane(south, x, y0, zz, 0.95, 2.25, divisions=1)
            south.box(x - upper_pitch / 2, y0 - 0.20, z + 20.58, 0.18, 0.45, 7.55, trim)
        m.add_part('新闻学院南翼 · 架空圆柱廊与双层窄窗', south)

    east_entry = e.get('eastStairEntry')
    if east_entry:
        m.add_part(
            '新闻教学区东端入口首跑',
            east_stair_entry(east_entry, z, e['arcadeClearHeight'], C, detail, pane),
        )

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
            roof.box(mx, my, z + height - 0.43, length, 0.32, 0.76, trim, angle)
            roof.box(mx, my, z + height - 0.055, length + 0.1, 0.56, 0.12, trim, angle)
            if my > yn - 0.6 and ri == 0:
                continue
            n = max(1, round(length / 4.2))
            for zz in [2.9, 6.05, 10.83, 14.21, 19.08, 22.85, 27.03]:
                if (
                    south_arcade
                    and ri == 0
                    and my < y0 + 0.3
                    and (zz < 8.15 or 16.7 < zz < 24.55)
                ):
                    continue
                for i in range(n):
                    t = (i + 0.5) / n
                    x = a[0] + t * dx
                    y = a[1] + t * dy
                    # Do not cap the side ends of the north colonnade with glazing.
                    if zz < 8.15 and (
                        y > back - 0.5 or (south_arcade and y < y0 + 3.1)
                    ):
                        continue
                    if (
                        east_entry
                        and ri == 0
                        and zz < e['arcadeClearHeight']
                        and x > x1 - 0.2
                        and east_entry['south'] - 1.3 < y < east_entry['north'] + 1.3
                    ):
                        continue
                    if 16.7 < zz < 24.55 and x < -36.1 and y > yn - 4.5:
                        continue
                    pane(other, x, y, zz, min(2.3, length / n * 0.64), 1.9, angle, sign)
            for zz in [8.15, 16.70, 24.55]:
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
    if detail:
        # Preserve the backing surfaces and depth behind the seventh-floor windows.
        room = Mesh()
        stone = interior_finish(C, 'banquetWall', (0.70, 0.63, 0.50), 0.81)
        room.box(0, 0, -0.04, 6.8, 6.8, 0.08, stone)
        room.box(0, 3.26, 1.61, 6.8, 0.16, 3.22, stone)
        room.box(3.34, 0, 1.61, 0.12, 6.6, 3.22, stone)
        room.v = [(x, y + yn - 8, zz + z + 24.58) for x, y, zz in room.v]
        m.add_part('七楼窗后楼板与墙面', room)
    m.rotate_z(0, 0, e['angle'])
    ox, oy = e['origin']
    m.v = [(x + ox, y + oy, zz) for x, y, zz in m.v]
    return m
