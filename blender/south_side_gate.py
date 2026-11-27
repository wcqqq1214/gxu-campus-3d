"""South-side gate from the labelled campus-interior photograph and OSM.

Coordinates are local east, north and up in metres. Relative component sizes
and the hidden surfaces are estimates. The 2025 works notice does not locate
the new pedestrian gates or establish a footprint for a separate guard booth.
"""

import math

import bpy
from mathutils import Vector

import geometry
from geometry import Mesh

# Road-surface samples in the source .blend, relative to campus_gate's
# vertical datum. Each row holds northing, west edge, centre and east edge.
# The shoulders continue the edge levels out to their modelled perimeter.
ROAD_SECTIONS = (
    (-1.90, 0.079, 0.123, 0.185),
    (0.00, 0.140, 0.169, 0.221),
    (3.20, 0.248, 0.271, 0.293),
    (7.50, 0.447, 0.444, 0.453),
)


def road_surface(x, y):
    left = x < 0
    column = 1 if left else 2
    across = max(0, 1 + x / 3.62) if left else min(1, x / 3.82)
    for lower, upper in zip(ROAD_SECTIONS, ROAD_SECTIONS[1:]):
        if y <= upper[0] or upper == ROAD_SECTIONS[-1]:
            a = lower[column] + across * (lower[column + 1] - lower[column])
            b = upper[column] + across * (upper[column + 1] - upper[column])
            return a + (b - a) * (y - lower[0]) / (upper[0] - lower[0])


def ensure_materials(C):
    for name, rgb, rough, metal in [
        ('southSideAsphalt', (0.14, 0.16, 0.16), 0.96, 0),
        ('southSideConcrete', (0.43, 0.45, 0.43), 0.93, 0),
        ('southSideIsland', (0.32, 0.33, 0.30), 0.94, 0),
        ('southSideStone', (0.43, 0.42, 0.37), 0.90, 0),
        ('southSideWallStone', (0.26, 0.27, 0.25), 0.96, 0),
        ('southSideSandstone', (0.48, 0.42, 0.34), 0.95, 0),
        ('southSideMortar', (0.18, 0.19, 0.17), 0.98, 0),
        ('southSideMetal', (0.38, 0.43, 0.44), 0.43, 0.48),
        ('southSideGuardrail', (0.30, 0.34, 0.35), 0.50, 0.65),
        ('southSideBlack', (0.025, 0.032, 0.034), 0.72, 0.18),
        ('southSideBlue', (0.018, 0.11, 0.32), 0.62, 0.08),
        ('southSideYellow', (0.78, 0.42, 0.035), 0.68, 0.08),
        ('southSideWhite', (0.79, 0.81, 0.77), 0.72, 0),
        ('southSideRed', (0.55, 0.045, 0.03), 0.67, 0),
        ('southSideGlass', (0.055, 0.12, 0.14), 0.28, 0.25),
        ('southSidePaint', (0.82, 0.83, 0.76), 0.90, 0),
    ]:
        if name not in C:
            existing = bpy.data.materials.get(name)
            if existing:
                C[name] = len(geometry.MATERIALS)
                geometry.MATERIALS.append(existing)
            else:
                C[name] = geometry.material(name, rgb, rough, metal)
        mat = geometry.MATERIALS[C[name]]
        mat.diffuse_color = (*rgb, 1)
        bs = mat.node_tree.nodes.get('Principled BSDF')
        bs.inputs['Base Color'].default_value = (*rgb, 1)
        bs.inputs['Roughness'].default_value = rough
        bs.inputs['Metallic'].default_value = metal


def graded_slab(m, x0, x1, y0, y1, mat, thickness=0.16, lift=0):
    """Split long slabs at the slope breaks before fitting the gate to the road."""
    stops = [y0, *(row[0] for row in ROAD_SECTIONS if y0 < row[0] < y1), y1]
    bottom = lift - thickness
    for a, b in zip(stops, stops[1:]):
        loop = [(x0, a), (x1, a), (x1, b), (x0, b)]
        m.face([(x, y, lift) for x, y in loop], mat)
        m.face([(x, y, bottom) for x, y in reversed(loop)], mat)
        for i in range(4):
            if (i == 0 and a != y0) or (i == 2 and b != y1):
                continue
            x, y = loop[i]
            u, v = loop[(i + 1) % 4]
            m.face([(x, y, bottom), (u, v, bottom), (u, v, lift), (x, y, lift)], mat)


def rounded_slab(m, x0, x1, y0, y1, radius, mat, thickness, lift):
    """Rounded closed slab whose top and bottom follow the same local grade."""
    corners = [
        (x1 - radius, y0 + radius, -90),
        (x1 - radius, y1 - radius, 0),
        (x0 + radius, y1 - radius, 90),
        (x0 + radius, y0 + radius, 180),
    ]
    outline = []
    for cx, cy, start in corners:
        for i in range(5):
            angle = math.radians(start + i * 90 / 4)
            outline.append(
                (cx + radius * math.cos(angle), cy + radius * math.sin(angle))
            )
    m.face([(x, y, lift) for x, y in outline], mat)
    m.face([(x, y, lift - thickness) for x, y in reversed(outline)], mat)
    for (x, y), (a, b) in zip(outline, outline[1:] + outline[:1]):
        m.face(
            [
                (x, y, lift - thickness),
                (a, b, lift - thickness),
                (a, b, lift),
                (x, y, lift),
            ],
            mat,
        )


def barrier_segment(m, a, b, mat, width, depth):
    """Rectangular aluminium barrier section, not a round ornamental tube."""
    av, bv = Vector(a), Vector(b)
    axis = (bv - av).normalized()
    across = Vector((0, 1, 0)) * (depth / 2)
    normal = Vector((0, 1, 0)).cross(axis).normalized() * (width / 2)
    pts = [
        tuple(point + u * normal + v * across)
        for point in [av, bv]
        for u, v in [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    ]
    for face in [
        (3, 2, 1, 0),
        (0, 1, 5, 4),
        (1, 2, 6, 5),
        (2, 3, 7, 6),
        (3, 0, 4, 7),
        (4, 5, 6, 7),
    ]:
        m.face([pts[i] for i in face], mat)


def ground_and_parking(m, C, detail):
    p = Mesh()
    # The mapped asphalt carriageway remains structural. Side aprons and the
    # photographed flush road hardware use slight lifts to prevent z-fighting.
    graded_slab(
        p, 3.82, 7.45, -1.90, 7.50, C['southSideAsphalt'], thickness=0.56, lift=0.015
    )
    graded_slab(
        p, -6.25, -3.62, -1.90, 7.50, C['southSideConcrete'], thickness=0.56, lift=0.015
    )
    # The parked cars face across the road. Only the in-frame ends of the
    # bays are represented; the parking lot's full depth is unknown.
    for y in [1.95, 4.55, 7.15]:
        graded_slab(
            p, 4.02, 7.45, y - 0.045, y + 0.045, C['southSidePaint'], 0.004, 0.020
        )
    graded_slab(p, 3.93, 4.02, 1.91, 7.20, C['southSidePaint'], 0.004, 0.020)
    # Visible road hardware supplies scale without altering the underlying road.
    x, y = 1.85, 6.3
    sides = 32 if detail else 16
    p.cylinder(x, y, 0.001, 0.34, 0.028, C['southSideBlack'], sides)
    p.cylinder(x, y, 0.015, 0.29, 0.008, C['southSideMetal'], sides)
    if detail:
        for offset in [-0.12, 0, 0.12]:
            half = math.sqrt(0.25**2 - offset**2)
            p.line(
                (x - half, y + offset, 0.021),
                (x + half, y + offset, 0.021),
                0.006,
                C['southSideBlack'],
                5,
            )
    y = -1.65
    graded_slab(p, -3.48, -0.70, y - 0.11, y + 0.11, C['southSideBlack'], 0.035, 0.016)
    for yy in [y - 0.10, y + 0.10]:
        graded_slab(
            p, -3.48, -0.70, yy - 0.015, yy + 0.015, C['southSideMetal'], 0.006, 0.022
        )
    if detail:
        for i in range(16):
            x = -3.40 + i * 2.62 / 15
            p.box(x, y, 0.020, 0.035, 0.18, 0.008, C['southSideMetal'])
    m.add_part('01_侧向铺装停车线雨水篦子与井盖_位置估算', p)


def lowered_arm(m, C, detail):
    # Interior view: east is image-left. The single yellow cabinet and lowered
    # arm therefore sit on +X; the blue notice and slim reader sit on -X.
    y = -0.55
    a = (0.55, y, 1.03)
    b = (3.55, y, 1.03)
    barrier_segment(m, a, b, C['southSideWhite'], 0.105, 0.065)
    for i in range(5 if detail else 3):
        t0 = i / (5 if detail else 3) + 0.055
        t1 = min(t0 + 0.09, 0.98)
        p0 = tuple(a[k] + (b[k] - a[k]) * t0 for k in range(3))
        p1 = tuple(a[k] + (b[k] - a[k]) * t1 for k in range(3))
        barrier_segment(m, p0, p1, C['southSideRed'], 0.112, 0.071)


def checkpoint(m, C, detail):
    p = Mesh()
    rounded_slab(p, -0.53, 0.57, -1.42, 1.30, 0.24, C['southSideIsland'], 0.20, 0.15)
    if detail:
        for i in range(7):
            y = -1.12 + i * 0.36
            p.box(
                0.535,
                y,
                0.085,
                0.045,
                0.25,
                0.15,
                C['southSideYellow'],
            )
    x, y = 0.40, -0.70
    z = 0.15
    p.box(x, y, z + 0.49, 0.38, 0.48, 0.98, C['southSideYellow'])
    p.box(x, y, z + 1.02, 0.40, 0.50, 0.10, C['southSideBlack'])
    for face in [-1, 1]:
        p.box(
            x,
            y + face * 0.246,
            z + 0.78,
            0.27,
            0.018,
            0.25,
            C['southSideGlass'],
        )
    lowered_arm(p, C, detail)
    # A slim reader is visible beside the sign; it is not a second barrier cabinet.
    p.box(-0.46, -0.54, 0.58, 0.12, 0.18, 0.86, C['southSideMetal'])
    p.box(-0.46, -0.636, 0.85, 0.085, 0.018, 0.18, C['southSideGlass'])
    m.add_part('02_中央岛台与单机箱落杆道闸_比例估算', p)
    p = Mesh()
    y = 0.48
    z = 0.15
    for x in [-0.385, -0.015]:
        p.box(x, y, z + 0.70, 0.04, 0.055, 1.40, C['southSideMetal'])
    p.box(-0.20, y, z + 1.10, 0.46, 0.09, 1.32, C['southSideBlue'])
    if detail:
        # The interior face shows stacked blue sections. Model the white
        # section dividers only; the photographed lettering is unresolved.
        front = y + 0.051
        for x in [-0.421, 0.021]:
            p.box(x, front, z + 1.10, 0.018, 0.012, 1.30, C['southSideMetal'])
        for h in [0.455, 1.745]:
            p.box(-0.20, front, z + h, 0.44, 0.012, 0.018, C['southSideMetal'])
        for h in [0.68, 1.00, 1.50]:
            p.box(-0.20, front, z + h, 0.40, 0.012, 0.011, C['southSideWhite'])
    m.add_part('03_窄高蓝色告示牌_文字不可辨', p)


def no_parking_sign(m, x, y, C, detail):
    """Single signed face and plain metal back, oblique to the road."""
    sign = Mesh()
    n = 32 if detail else 16
    # Construct in the XZ plane facing +Y. Winding matters for front lighting.
    rim = [
        (0.24 * math.cos(t * math.tau / n), 0.24 * math.sin(t * math.tau / n))
        for t in range(n)
    ]
    sign.face([(u, -0.026, v) for u, v in rim], C['southSideMetal'])
    for (u, v), (w, z) in zip(rim, rim[1:] + rim[:1]):
        sign.face(
            [(u, -0.026, v), (u, 0.026, v), (w, 0.026, z), (w, -0.026, z)],
            C['southSideMetal'],
        )
        sign.face(
            [
                (w, 0.026, z),
                (u, 0.026, v),
                (u * 0.8, 0.026, v * 0.8),
                (w * 0.8, 0.026, z * 0.8),
            ],
            C['southSideRed'],
        )
    sign.face([(u * 0.8, 0.026, v * 0.8) for u, v in reversed(rim)], C['southSideBlue'])
    sign.face(
        [
            (-0.15, 0.030, -0.123),
            (0.123, 0.030, 0.15),
            (0.15, 0.030, 0.123),
            (-0.123, 0.030, -0.15),
        ],
        C['southSideRed'],
    )
    sign.rotate_z(0, 0, math.radians(-48))
    sign.v = [(x + u, y + v, 2.48 + h) for u, v, h in sign.v]
    m.extend(sign)
    m.box(x, y, 2.22, 0.04, 0.04, 0.48, C['southSideMetal'])


def iron_scroll(m, x, y, z, sign, C):
    """Restrained spiral ornament visible on the central iron gate leaf."""
    points = []
    for i in range(19):
        t = i / 18
        angle = sign * (0.15 + t * 1.65 * math.tau)
        radius = 0.23 * (1 - 0.78 * t)
        yy = y + radius * math.cos(angle)
        points.append((x, yy, z + radius * math.sin(angle)))
    for a, b in zip(points, points[1:]):
        m.line(a, b, 0.014, C['southSideBlack'], 5)


def enclosure(m, C, detail):
    p = Mesh()
    x = -5.60
    y0, y1 = -0.8, 3.2
    for y in (y0, y1):
        p.box(x, y, 0.10, 0.68, 0.68, 0.20, C['southSideStone'])
        p.box(x, y, 1.01, 0.50, 0.50, 1.68, C['southSideMortar'])
        rows = 6 if detail else 1
        for i in range(rows):
            h = 1.64 / rows
            mat = 'southSideSandstone' if i % 3 == 1 else 'southSideStone'
            p.box(x, y, 0.20 + (i + 0.5) * h, 0.54, 0.54, h - 0.016, C[mat])
        p.box(x, y, 1.90, 0.64, 0.64, 0.12, C['southSideStone'])
        p.roof(x, y, 1.96, 0.66, 0.66, 0.11, C['southSideSandstone'])

    # Photograph: one arched iron leaf between stone piers; a masonry sill
    # continues on the near (north) side, below the neighbouring facade.
    start, end = y0 + 0.26, y1 - 0.26

    def top(y):
        t = (y - start) / (end - start)
        return 1.48 + 0.34 * 4 * t * (1 - t)

    segments = 12 if detail else 6
    for i in range(segments):
        a = start + (end - start) * i / segments
        b = start + (end - start) * (i + 1) / segments
        p.line((x, a, top(a)), (x, b, top(b)), 0.032, C['southSideBlack'], 8)
    for h in (0.12, 0.29, 1.32):
        p.line((x, start, h), (x, end, h), 0.023, C['southSideBlack'], 6)
    count = 16 if detail else 9
    for i in range(count):
        y = start + (end - start) * (i + 0.5) / count
        bottom, head = 0.12, top(y)
        p.box(
            x, y, (bottom + head) / 2, 0.033, 0.033, head - bottom, C['southSideBlack']
        )
    if detail:
        for i, direction in enumerate([1, -1, 1, -1]):
            iron_scroll(p, x, start + (i + 0.5) * (end - start) / 4, 1.43, direction, C)

    start, end = y1 + 0.27, 7.50
    graded_slab(p, x - 0.16, x + 0.16, start, end, C['southSideWallStone'], 0.48, 0.48)
    if detail:
        for row in range(2):
            a = start
            while a < end - 0.02:
                width = 0.42 if row and a == start else 0.85
                b = min(end, a + width)
                mat = (
                    'southSideStone'
                    if (row + round((a - start) / width)) % 3
                    else 'southSideSandstone'
                )
                graded_slab(
                    p,
                    x + 0.156,
                    x + 0.18,
                    a + 0.008,
                    b - 0.008,
                    C[mat],
                    0.22,
                    0.24 + row * 0.24,
                )
                a = b
    graded_slab(p, x - 0.19, x + 0.20, start, end, C['southSideStone'], 0.065, 0.545)
    no_parking_sign(p, x, y1, C, detail)
    m.add_part('04_双石柱浅拱铁门与路缘石墙_长度估算', p)


def roadside_rails(m, C, detail):
    p = Mesh()
    # Both the single parking tube and the portable rails recede along the
    # street in the photo, from the camera (north) towards the gate (south).
    x = 3.68
    for y in [1.84, 4.56, 7.28]:
        p.box(x, y, 0.11, 0.055, 0.055, 0.22, C['southSideGuardrail'])
        p.box(x, y, 0.028, 0.14, 0.14, 0.056, C['southSideConcrete'])
    p.line(
        (x, 1.84, 0.24),
        (x, 7.28, 0.24),
        0.045,
        C['southSideGuardrail'],
        12 if detail else 8,
    )
    x = -5.10
    for y0, y1 in [(3.64, 5.16), (6.05, 7.45)]:
        for y in (y0, y1):
            z = 0.015
            p.cylinder(x, y, z + 0.035, 0.14, 0.07, C['southSideBlack'], 8)
            p.box(x, y, z + 0.53, 0.055, 0.055, 0.98, C['southSideWhite'])
        for h in [0.16, 0.93]:
            graded_slab(p, x - 0.024, x + 0.024, y0, y1, C['southSideWhite'], 0.048, h)
        bars = 9 if detail else 5
        for i in range(bars):
            y = y0 + (y1 - y0) * (i + 1) / (bars + 1)
            p.box(x, y, 0.53, 0.024, 0.024, 0.76, C['southSideWhite'])
    m.add_part('05_顺校道白色活动栏与低位停车护栏_比例估算', p)


def south_side_gate(C, detail=True):
    ensure_materials(C)
    m = Mesh()
    ground_and_parking(m, C, detail)
    checkpoint(m, C, detail)
    enclosure(m, C, detail)
    roadside_rails(m, C, detail)
    m.v = [(x, y, h + road_surface(x, y)) for x, y, h in m.v]
    return m
