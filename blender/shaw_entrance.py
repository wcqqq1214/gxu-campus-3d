"""South podium junction of Shaw Building, read from GXU's two ground photographs."""

import math
from pathlib import Path

from mathutils import Vector
from mathutils.geometry import tessellate_polygon

from facade_bands import frame
from geometry import Mesh
from south_gate import inscription


def shaw_transoms(panel):
    fw = panel['frameWidth']
    clear = panel['top'] - panel['bottom'] - 2 * fw
    return [
        (panel['bottom'] + fw / 2, fw),
        *((panel['bottom'] + fw + t * clear, fw * 0.65) for t in panel['rowFractions']),
        (panel['top'] - fw / 2, fw),
    ]


class ShawEntrance:
    """Local coordinates run east along the west wing, with depth positive to the plaza."""

    def __init__(self, building):
        facades = {
            f['edge']: f
            for f in building['form']['facades']
            if f['part'] == 'front-podium' and not f['ring']
        }
        self.west = facades[9]
        self.fold = facades[8]
        self.origin = self.fold['end']
        self.east = self.fold['start']
        _, tangent, self.out, _, _ = frame(self.west)
        self.e = [-v for v in tangent]
        dx, dy = [self.east[i] - self.origin[i] for i in range(2)]
        self.run = dx * self.e[0] + dy * self.e[1]
        self.advance = dx * self.out[0] + dy * self.out[1]
        # The jamb in the group photo is already on the straight western run.
        self.left = -1.55
        self.back = -1.55
        self.clear_height = self.fold['height'] / self.fold['levels'] - 0.18
        # Five flat lights between the shoulder seams in the 8-degree view.
        # Preserve both mapped ends. The intermediate offsets are estimates.
        self.stations = [
            (self.run * j / 5, self.advance * (j / 5) ** 2) for j in range(6)
        ]

    def xy(self, s, d):
        return [self.origin[i] + self.e[i] * s + self.out[i] * d for i in range(2)]

    def front_depth(self, s):
        if s <= 0:
            return 0.0
        for (a, da), (b, db) in zip(self.stations, self.stations[1:]):
            if s <= b:
                return da + (db - da) * (s - a) / (b - a)
        return self.advance

    def notch_part(self, part):
        """Cut the jambs and straight rear wall into the podium, including its roof."""
        ring = part['polygons'][0][0][:-1]
        start = ring.index(self.east)
        ring = ring[start:] + ring[:start]
        assert ring[1] == self.origin
        jambs = [
            self.xy(self.run, self.back),
            self.xy(self.left, self.back),
            self.xy(self.left, 0),
        ]
        cut = [ring[0], *jambs, *ring[2:]]
        vectors = [Vector((x, y, 0)) for x, y in cut]
        triangles = []
        for i, j, k in tessellate_polygon([vectors]):
            if (vectors[j] - vectors[i]).cross(vectors[k] - vectors[i]).z < 0:
                j, k = k, j
            triangles.extend((i, j, k))
        assert len(triangles) == 3 * (len(cut) - 2)
        # Retain the adjoining wing parapets. The five-sided section has its own coping.
        return {
            **part,
            'polygons': [[cut + [cut[0]]]],
            'triangles': [triangles],
            'parapetEdges': list(zip(ring[1:], ring[2:] + ring[:1])),
        }

    def west_corridor(self):
        """Centre every original square window in the clear span between its new piers."""
        f = self.west
        old = f['rule']['openCorridor']
        remaining = math.dist(f['start'], f['end']) + self.left
        inset = old['endInset']
        bays = old['piers']['bays']
        pitch = (remaining - 2 * inset) / bays
        openings = []
        assert bays == len(old['openings'])
        for i, opening in enumerate(old['openings']):
            assert opening['width'] < pitch - old['piers']['width']
            openings.append({**opening, 't': (inset + (i + 0.5) * pitch) / remaining})
        return {
            **f,
            'start': self.xy(self.left, 0),
            'rule': {**f['rule'], 'openCorridor': {**old, 'openings': openings}},
        }

    def face_returns(self, shell, stone):
        points = [
            self.east,
            self.xy(self.run, self.back),
            self.xy(self.left, self.back),
            self.xy(self.left, 0),
        ]
        pairs = [set((tuple(a), tuple(b))) for a, b in zip(points, points[1:])]
        for i, face in enumerate(shell.f):
            if {tuple(shell.v[j][:2]) for j in face} in pairs:
                shell.m[i] = stone

    def build(self, z, colors, joint, soffit, letter_face, letter_edge):
        mesh = Mesh()
        height = self.fold['height']
        ceiling = self.clear_height
        stone = colors['shawPinkGranite']
        frame_mat = colors['shawGlazingFrame']
        north_angle = math.atan2(self.e[1], self.e[0])
        left, right, back = self.left, self.run, self.back

        def pt(s, d, h):
            return (*self.xy(s, d), z + h)

        def box(s, d, h, w, depth, thick, mat):
            mesh.box(*self.xy(s, d), z + h, w, depth, thick, mat, north_angle)

        def skin(a, b, bottom, top, mat, offset=0):
            # West-to-east and upward winds towards the south (plaza).
            mesh.face(
                [
                    pt(a, self.front_depth(a) + offset, bottom),
                    pt(b, self.front_depth(b) + offset, bottom),
                    pt(b, self.front_depth(b) + offset, top),
                    pt(a, self.front_depth(a) + offset, top),
                ],
                mat,
            )

        path = [(left, 0), *self.stations]
        for (a, da), (b, db) in zip(path, path[1:]):
            # Roof and soffit share their corner vertices with the wing deck;
            # each soffit row ends against the same straight door head at the rear.
            mesh.face(
                [
                    pt(a, da, height),
                    pt(b, db, height),
                    pt(b, back, height),
                    pt(a, back, height),
                ],
                colors['paleRoof'],
            )
            for row in range(3):
                r0, r1 = row / 3, (row + 1) / 3
                mesh.face(
                    [
                        pt(a, back + (da - back) * r0, ceiling),
                        pt(b, back + (db - back) * r0, ceiling),
                        pt(b, back + (db - back) * r1, ceiling),
                        pt(a, back + (da - back) * r1, ceiling),
                    ],
                    joint,
                )
                # Inset each panel in its own tapered bay; reveal the joint bed between panels.
                aa, bb = a + 0.009, b - 0.009
                corners = [
                    (aa, r0 + 0.004),
                    (bb, r0 + 0.004),
                    (bb, r1 - 0.004),
                    (aa, r1 - 0.004),
                ]
                mesh.face(
                    [
                        pt(s, back + (self.front_depth(s) - back) * t, ceiling - 0.014)
                        for s, t in corners
                    ],
                    soffit,
                )
            skin(a, b, ceiling, height, stone)
            if (
                b <= 0
            ):  # Existing west-wing glass, fascia and parapet cover this flat bay.
                continue
            skin(a, b, ceiling + 0.025, 3.714, joint, 0.093)
            skin(a + 0.007, b - 0.007, ceiling + 0.029, 3.712, stone, 0.121)
            skin(a, b, 3.72, 9.73, colors['shawCurtainGlass'], 0.035)
            # Use actual plane normals from the profile for light and reflection.
            for h, thick in shaw_transoms(self.west['rule']['panels'][0]):
                skin(a, b, h - thick / 2, h + thick / 2, frame_mat, 0.17)
                for up in (h - thick / 2, h + thick / 2):
                    mesh.face(
                        [
                            pt(a, da + 0.045, up),
                            pt(b, db + 0.045, up),
                            pt(b, db + 0.17, up),
                            pt(a, da + 0.17, up),
                        ],
                        frame_mat,
                    )
            skin(a, a + 0.039, 3.72, 9.73, frame_mat, 0.173)
            if b == right:
                skin(b - 0.039, b, 3.72, 9.73, frame_mat, 0.173)
            skin(a, b, height, height + 0.80, colors['white'])
            skin(a, b, height, height + 0.80, colors['white'], -0.19)
            mesh.face(
                [
                    pt(a, da, height + 0.8),
                    pt(b, db, height + 0.8),
                    pt(b, db - 0.19, height + 0.8),
                    pt(a, da - 0.19, height + 0.8),
                ],
                colors['white'],
            )
        # Door head and stair noses read as straight across in the official close-up.
        # Their true azimuth is not measured. Both are approximated along the west wing.
        mid = (left + right) / 2
        w = right - left
        floor, door_top = 0.40, 2.84
        glass_width = w - 0.57
        box(
            mid,
            back + 0.050,
            (floor + door_top) / 2,
            glass_width,
            0.087,
            door_top - floor,
            colors['shawDoorGlass'],
        )
        for s in (
            mid - glass_width / 2,
            mid - 0.97,
            mid,
            mid + 0.97,
            mid + glass_width / 2,
        ):
            box(
                s,
                back + 0.107,
                (floor + door_top) / 2,
                0.062,
                0.06,
                door_top - floor,
                frame_mat,
            )
        for h in (floor + 0.034, 2.43, door_top):
            box(mid, back + 0.105, h, glass_width + 0.060, 0.060, 0.067, frame_mat)
        for side in (-1, 1):
            box(
                mid + side * 0.13, back + 0.16, 1.44, 0.035, 0.05, 0.44, colors['metal']
            )
        # Full-depth landing joins the rear sill. The transverse stair noses
        # meet both side cheeks independently of the angle of the canopy above.
        nose = self.advance + 0.10
        box(mid, (back + nose) / 2, floor / 2, w, nose - back, floor, colors['stone'])
        for step in range(1, 4):
            rise = floor - step * 0.10
            box(
                mid,
                nose + (step - 0.5) * 0.28,
                rise / 2,
                w,
                0.28,
                rise,
                colors['stone'],
            )
        for side in (-1, 1):
            box(
                mid + side * (w / 2 + 0.11),
                nose + 0.30,
                0.25,
                0.22,
                1.12,
                0.50,
                colors['stone'],
            )
        # Keep each raised letter close to the local stone face, including
        # the letters that cross the shoulder onto the flat west section.
        for label, h, width, size in [
            ('外国语学院', 3.51, 2.75, 0.315),
            ('SCHOOL OF FOREIGN LANGUAGES', 3.276, 2.70, 0.105),
        ]:
            glyph = inscription(
                label,
                0,
                0,
                0,
                width,
                size,
                letter_face,
                False,
                font_path=Path(__file__).parent / 'fonts/GXUShawSign.ttf',
                outline=(0.006 if label.startswith('外') else 0.003, letter_edge),
                curve_resolution=3,
            )
            # The edge finish also wraps the actual extrusion. Keep a single
            # silver face finish across both inscriptions and every fascia fold.
            for i, face in enumerate(glyph.f):
                depths = [glyph.v[j][1] for j in face]
                if glyph.m[i] == letter_face and max(depths) - min(depths) > 1e-7:
                    glyph.m[i] = letter_edge
            glyph.v = [
                pt(0.65 + x, self.front_depth(0.65 + x) + 0.173 - y, h + up)
                for x, y, up in glyph.v
            ]
            mesh.extend(glyph)
        return mesh
