"""Deterministic near and far tree templates, shared by full and vegetation-only builds."""

import math
import random

import bmesh

from geometry import Mesh


def areca_palm(C, detail):
    """Slender ringed trunk, a green crownshaft and pinnate, arching fronds."""
    mesh = Mesh()
    sides = 12 if detail else 7
    mesh.cylinder(0, 0, 0.44, 0.17, 0.88, C['palmLimewash'], sides, topr=0.14)
    mesh.cylinder(0, 0, 3.39, 0.14, 5.02, C['palmStem'], sides, topr=0.115)
    mesh.cylinder(0, 0, 6.35, 0.13, 0.9, C['leaf2'], sides, topr=0.11)
    if detail:
        for i in range(12):
            z = 1.1 + i * 0.41
            radius = 0.142 - (z - 0.88) * 0.005
            mesh.cylinder(0, 0, z, radius, 0.024, C['bark'], sides)
    # Outer mature fronds hang below the crownshaft; newer fronds stand higher.
    for i in range(11):
        angle = i * 2.39996
        ux, uy = math.cos(angle), math.sin(angle)
        tier = i % 3
        reach = (2.55, 2.25, 1.45)[tier]
        rise = (1.25, 2.05, 2.5)[tier]
        drop = (2.15, 1.8, 1.30)[tier]
        material = C[('leaf', 'leaf2', 'leaf3')[tier]]

        def point(t, side=0, sag=0):
            r = reach * t
            z = 6.76 + rise * t - drop * t * t
            return (ux * r - uy * side, uy * r + ux * side, z - sag)

        sections = 15 if detail else 7
        for j in range(sections):
            t, end = j / sections, (j + 1) / sections
            if detail:
                mesh.line(point(t), point(end), 0.018 * (1 - 0.7 * t), material, 4)
                if j == 0:
                    continue
                # Each leaf tapers from a narrow base, with a slight fold and drooping tip.
                length = 0.15 + 0.58 * math.sin(math.pi * t) ** 0.7
                for sign in (-1, 1):
                    base = point(t)
                    tip = point(t + 0.7 * length / reach, sign * length, 0.48 * length)
                    mid = t + 0.24 * length / reach
                    spread = sign * length * 0.47
                    mesh.face(
                        [
                            base,
                            point(mid - 0.024, spread, 0.12 * length),
                            tip,
                            point(mid + 0.024, spread, 0.16 * length),
                        ][::-sign],
                        material,
                    )
            else:
                # Joined, folded blades retain an unbroken silhouette in the far model.
                def edge(u, sign):
                    width = 0.38 * math.sin(math.pi * u)
                    return point(u, sign * width, width * 0.42)

                for sign in (-1, 1):
                    blade = [point(t), edge(t, sign), edge(end, sign), point(end)]
                    if j == 0:
                        blade.pop(1)
                    elif j == sections - 1:
                        blade.pop(2)
                    mesh.face(blade[::-sign], material)
    return mesh


def tree_templates(C, collection, detail):
    if detail:
        templates = []
        for typ in range(3):
            m = Mesh()
            m.cylinder(0, 0, 2.5, 0.24, 5, C['bark'], 8, topr=0.12)
            if typ < 2:
                rng = random.Random(200 + typ)
                for i in range(8 if typ == 0 else 5):
                    angle = i * math.tau / 8
                    r = 1.7 if i else 0
                    m.ellipsoid(
                        math.cos(angle) * r,
                        math.sin(angle) * r,
                        5 + rng.uniform(-0.8, 1.6),
                        2.0,
                        1.8,
                        2.0 if typ == 0 else 3.2,
                        C[['leaf', 'leaf2', 'leaf3'][i % 3]],
                        12,
                        8,
                    )
            else:
                # Continuous arching rachis and paired leaflets replace disconnected triangles.
                for i in range(10):
                    a = i * math.tau / 10
                    ux, uy = math.cos(a), math.sin(a)
                    vx, vy = -uy, ux

                    def stem(t):
                        return (
                            ux * t * 4.1,
                            uy * t * 4.1,
                            6.2 + math.sin(t * math.pi) * 1.0 - t * 1.6,
                        )

                    for j in range(9):
                        t = j / 9
                        t1 = (j + 1) / 9
                        p0 = stem(t)
                        p1 = stem(t1)
                        m.line(p0, p1, 0.028, C['leaf'], 4)
                        for side in [-1, 1]:
                            spread = 0.63 * math.sin((t + 0.10) * math.pi) * side
                            tip = (
                                p0[0] + ux * 0.36 + vx * spread,
                                p0[1] + uy * 0.36 + vy * spread,
                                p0[2] - 0.18 - abs(spread) * 0.15,
                            )
                            m.face([p0, tip, p1], C['leaf2'] if j % 3 else C['leaf3'])
            template = m.object(f'Tree-template-{typ}', collection, {'template': typ})
            if typ < 2:
                bm = bmesh.new()
                bm.from_mesh(template.data)
                bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.0001)
                bm.to_mesh(template.data)
                bm.free()
                for poly in template.data.polygons:
                    poly.use_smooth = True
                template.data.update()
            templates.append(template)
    else:
        templates = []
        for typ in range(3):
            m = Mesh()
            m.cylinder(0, 0, 2.5, 0.24, 5, C['bark'], 8, topr=0.12)
            if typ < 2:
                rng = random.Random(200 + typ)
                for i in range(8 if typ == 0 else 5):
                    angle = i * math.tau / 8
                    r = 1.7 if i else 0
                    m.ellipsoid(
                        math.cos(angle) * r,
                        math.sin(angle) * r,
                        5 + rng.uniform(-0.8, 1.6),
                        2.0,
                        1.8,
                        2.0 if typ == 0 else 3.2,
                        C[['leaf', 'leaf2', 'leaf3'][i % 3]],
                        8,
                        5,
                    )
            else:
                for i in range(10):
                    a = i * math.tau / 10
                    for j in range(5):
                        r = j * 0.8
                        r1 = (j + 1) * 0.8
                        z0 = 6 + math.sin(j / 5 * math.pi) * 1.3 - j * 0.26
                        z1 = 6 + math.sin((j + 1) / 5 * math.pi) * 1.3 - (j + 1) * 0.26
                        m.face(
                            [
                                (
                                    math.cos(a) * r - math.sin(a) * 0.5,
                                    math.sin(a) * r + math.cos(a) * 0.5,
                                    z0,
                                ),
                                (math.cos(a) * r1, math.sin(a) * r1, z1),
                                (
                                    math.cos(a) * r + math.sin(a) * 0.5,
                                    math.sin(a) * r - math.cos(a) * 0.5,
                                    z0,
                                ),
                            ],
                            C['leaf2'],
                        )
            templates.append(
                m.object(f'Tree-far-template-{typ}', collection, {'template': typ})
            )
    palm = areca_palm(C, detail)
    prefix = 'Tree-template' if detail else 'Tree-far-template'
    templates.append(palm.object(f'{prefix}-3', collection, {'template': 3}))
    return templates
