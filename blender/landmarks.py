"""Distinct architectural studies, using the reference catalogue and OSM footprints."""

from campus_gates import campus_gate
from geometry import Mesh
from huicui import huicui
from huixue import huixue
from international_residence import international_residence
from laboratory import laboratory
from library import library
from south_gate import south_gate
from student_center import student_center
from teaching_six import teaching_six
from teaching_ten import teaching_ten
from time_gate import time_gate

DEDICATED_LANDMARKS = {
    'huixue': huixue,
    'laboratory': laboratory,
    'student-center': student_center,
    'library': library,
    'international-residence': international_residence,
    'teaching-six': teaching_six,
    'teaching-ten': teaching_ten,
}


def facade(m, x, y, z, w, d, h, wall, glass, trim, floors=6, spacing=4, band=False):
    m.box(x, y, z + h / 2, w, d, h, wall)
    for sy in [-1, 1]:
        for f in range(floors):
            zz = z + (f + 0.55) * h / floors
            if band:
                m.box(
                    x,
                    y + sy * (d / 2 + 0.08),
                    zz,
                    w - 2,
                    0.12,
                    h / floors * 0.61,
                    glass,
                )
            else:
                count = max(1, int(w / spacing))
                for i in range(count):
                    m.box(
                        x - w / 2 + (i + 0.5) * w / count,
                        y + sy * (d / 2 + 0.08),
                        zz,
                        w / count * 0.56,
                        0.14,
                        h / floors * 0.55,
                        glass,
                    )
            m.box(
                x,
                y + sy * (d / 2 + 0.20),
                z + (f + 1) * h / floors,
                w + 0.5,
                0.38,
                0.2,
                trim,
            )
    for sx in [-1, 1]:
        for f in range(floors):
            count = max(1, int(d / spacing))
            for i in range(count):
                m.box(
                    x + sx * (w / 2 + 0.08),
                    y - d / 2 + (i + 0.5) * d / count,
                    z + (f + 0.55) * h / floors,
                    0.14,
                    d / count * 0.52,
                    h / floors * 0.55,
                    glass,
                )
    m.box(x, y, z + h + 0.3, w + 1.5, d + 1.5, 0.6, trim)


def steps(m, x, y, z, width, depth, height, mat, n=12):
    for i in range(n):
        m.box(
            x,
            y + depth * i / n / 2,
            z + height * (i + 0.5) / n,
            width,
            depth * (1 - i / n),
            height / n,
            mat,
        )


def landmark(l, b, z, C, detail=True):
    k = l['id']
    if k in DEDICATED_LANDMARKS:
        return DEDICATED_LANDMARKS[k](l, b, z, C, detail)
    if k == 'huicui':
        return huicui(b, z, C, detail)
    if l.get('placeKind') == 'sculpture':
        return time_gate(l, z, C, detail)
    if l.get('placeKind') == 'gate':
        return campus_gate(l, z, C, detail)
    m = Mesh()
    x, y = l['center']
    xmin, ymin, xmax, ymax = l['bounds']
    w = xmax - xmin
    d = ymax - ymin
    x = (xmin + xmax) / 2
    y = (ymin + ymax) / 2
    h = l['height']
    stone, white, glass, dark, _roof, wood = (
        C['stone'],
        C['white'],
        C['glass'],
        C['dark'],
        C['slate'],
        C['wood'],
    )
    if k == 'south-gate':
        return south_gate(x, y, z, C, detail, footprint_width=w, footprint_depth=d)
    elif k == 'auditorium':
        m.box(x, y, z + 5.4, w * 0.9, d * 0.93, 10.8, white)
        m.roof(x, y, z + 10.8, w * 0.98, d, 3, C['paleRoof'])
        front = y - d * 0.49
        m.box(x, front, z + 11.3, w, 6, 0.8, stone)
        m.face(
            [
                (x - w * 0.38, front - 3, z + 11.7),
                (x + w * 0.38, front - 3, z + 11.7),
                (x, front - 3, z + 15),
            ],
            white,
        )
        m.line(
            (x - w * 0.41, front - 3, z + 11.7), (x, front - 3, z + 15.3), 0.20, stone
        )
        m.line(
            (x, front - 3, z + 15.3), (x + w * 0.41, front - 3, z + 11.7), 0.20, stone
        )
        for i in range(6):
            xx = x + (i - 2.5) * w * 0.13
            m.cylinder(xx, front - 2, z + 6, 0.56, 10, white, 20)
            m.cylinder(xx, front - 2, z + 10.8, 0.82, 0.5, stone, 20)
            m.cylinder(xx, front - 2, z + 1, 0.8, 0.4, stone, 20)
            m.box(xx, front + 0.08, z + 2, 2, 0.15, 2.5, wood)
            for f in [1, 2]:
                m.box(xx, front + 0.08, z + 2 + f * 3, 1.8, 0.15, 2.2, glass)
        for sx in [-1, 1]:
            for j in range(8):
                for f in range(3):
                    m.box(
                        x + sx * w * 0.455,
                        y - d * 0.39 + j * d * 0.106,
                        z + 1.8 + 3 * f,
                        0.15,
                        1.7,
                        2,
                        glass,
                    )
                m.box(
                    x + sx * w * 0.465,
                    y - d * 0.43 + j * d * 0.12,
                    z + 5.5,
                    0.4,
                    0.5,
                    10,
                    stone,
                )
        steps(m, x, front - 6, z, w * 0.94, 9, 1.2, stone)
    elif k == 'stadium':
        # Official 2021 video, 00:07 and 00:12: broad shallow roof, vertical piers, horizontal louvers.
        # The mapped footprint has a narrow north wing. Using the full bounding
        # rectangle filled that concavity and pushed the east annex into Nongyuan Road.
        ring = b['polygons'][0][0][:-1]
        winding = sum(
            a[0] * c[1] - c[0] * a[1] for a, c in zip(ring, ring[1:] + ring[:1])
        )
        reflex = []
        for i, p in enumerate(ring):
            a = ring[i - 1]
            c = ring[(i + 1) % len(ring)]
            cross = (p[0] - a[0]) * (c[1] - p[1]) - (p[1] - a[1]) * (c[0] - p[0])
            if cross * winding < 0:
                reflex.append(p)
        notch = max(reflex, key=lambda p: p[0])
        split = notch[1]
        north = [p for p in ring if p[1] > split + 1]
        wing_left = min(p[0] for p in north)
        wing_right = max(p[0] for p in north)
        mainw = w * 0.9
        maind = (split - ymin) * 0.93
        hh = h * 0.83
        xx = x
        y = (ymin + split) / 2
        facade(m, xx, y, z, mainw, maind, hh, stone, glass, white, 2, 5, True)
        m.roof(xx, y, z + hh + 1.4, mainw + 8, maind + 8, 1.9, C['paleRoof'])
        for sy in [-1, 1]:
            front = y + sy * (maind / 2 + 0.3)
            for i in range(9):
                m.box(
                    xx + (i - 4) * mainw * 0.108,
                    front,
                    z + hh * 0.47,
                    1.8,
                    2.0,
                    hh * 0.94,
                    stone,
                )
            for j in range(5):
                m.box(
                    xx,
                    front + sy * 0.8,
                    z + hh * 0.66 + j * 0.85,
                    mainw - 5,
                    0.35,
                    0.22,
                    C['metal'],
                )
            m.box(xx, front, z + hh + 1.1, mainw + 8, 4, 1.1, dark)
        facade(
            m,
            (wing_left + wing_right) / 2,
            (split + ymax) / 2,
            z,
            (wing_right - wing_left) * 0.93,
            (ymax - split) * 0.96,
            h * 0.48,
            stone,
            glass,
            white,
            2,
            4,
            True,
        )
        for row in range(5):
            for col in range(6):
                sx = xx + (col - 2.5) * mainw * 0.115
                sy = y + (row - 2) * maind * 0.14
                m.box(sx, sy, z + hh + 3.1, 2.3, 2.3, 0.7, white)
        steps(m, xx, ymin - 3, z, mainw * 0.65, 8, 1.2, stone)
    elif k == 'teaching-two':
        facade(m, x, y, z, w, d, h, C['pink'], glass, white, 7, 3.8)
        m.box(x, ymin - 1.6, z + h * 0.50, 9, 3, h, stone)
        m.box(x, ymin - 3, z + 4.5, 15, 7, 0.5, white)
        for sx in [-1, 1]:
            m.box(x + sx * (w * 0.4), y, z + h + 1, 6, d * 0.8, 2.2, stone)
        steps(m, x, ymin - 4, z, 14, 6, 0.8, stone)
    elif k == 'computer':
        facade(m, x, y, z, w, d, h, white, glass, stone, 10, 3.6)
        m.box(x + w * 0.44, y, z + h / 2, w * 0.18, d + 1, h, C['pink'])
        m.box(x - w * 0.05, ymin - 0.8, z + h * 0.52, w * 0.14, 0.35, h * 0.91, glass)
        for i in range(8):
            m.box(
                x - w * 0.4 + i * w * 0.05,
                ymin - 0.8,
                z + h * 0.48,
                0.9,
                1.0,
                h * 0.79,
                stone,
            )
        m.box(x, y, z + h + 1.8, w + 5, d + 3, 0.55, white)
        m.box(x + w * 0.18, ymin - 0.6, z + h / 2, w * 0.15, 1.4, h + 2, stone)
        m.box(x - w * 0.35, ymax - d * 0.2, z + h + 1, w * 0.26, d * 0.28, 3, stone)
        m.box(x, ymin - 2, z + 4.6, 12, 7, 0.55, white)
        for sx in [-1, 1]:
            m.cylinder(x + sx * 4.5, ymin - 4, z + 2.2, 0.4, 4.4, stone)
        steps(m, x, ymin - 4, z, 12, 6, 0.7, stone)
    return m
