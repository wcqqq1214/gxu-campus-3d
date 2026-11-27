"""Fit the final campus terrain to the documented wall and landing profiles."""

import json
import math
from pathlib import Path

from geometry import Mesh
from lakes_east import _cdt, _plane, _splice
from refine_roads_west import _source_uv
from refine_terrain_west import sample
from shore_geometry import bounds, overlaps, smooth
from site_geometry import mesh_triangles


def grade_records():
    return json.loads(Path(__file__).with_suffix('.json').read_text())


def grade_bounds(record):
    radius = record['feather']
    x0, y0, x1, y1 = bounds(record['line'])
    return (x0 - radius, y0 - radius, x1 + radius, y1 + radius)


class WallGrade:
    def __init__(self, record):
        self.line = record['line']
        self.core = record['core']
        self.radius = record['feather']
        self.limit = record['limit']
        self.bounds = grade_bounds(record)
        self.controls, self.edges = self.triangulation_controls()

    def profile(self, x, y):
        best = math.inf
        for (ax, ay, az), (bx, by, bz) in zip(self.line, self.line[1:]):
            dx, dy = bx - ax, by - ay
            t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
            distance = math.hypot(x - ax - t * dx, y - ay - t * dy)
            if distance < best:
                best = distance
                target = az + t * (bz - az)
        return best, target

    def triangulation_controls(self):
        # Constrain the wall line and the round ends of its influence. Heights on
        # the transition grid use the same capped smoothstep as the approved mesh.
        points, edges = [], []
        step = max(0.18, min(self.core * 0.8, self.radius * 0.28, 0.60))

        def chain(path):
            start = len(points)
            points.extend(path)
            edges.extend((i, i + 1) for i in range(start, len(points) - 1))

        for a, b in zip(self.line, self.line[1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            count = math.ceil(math.hypot(dx, dy) / step)
            chain(
                [
                    (a[0] + dx * i / count, a[1] + dy * i / count)
                    for i in range(count + 1)
                ]
            )
            angle = math.atan2(dy, dx)
            # One capsule per segment constrains the union, including elbows.
            ring = []
            for end, start in ((b, angle - math.pi / 2), (a, angle + math.pi / 2)):
                for i in range(21):
                    theta = start + i * math.pi / 20
                    ring.append(
                        (
                            end[0] + self.radius * math.cos(theta),
                            end[1] + self.radius * math.sin(theta),
                        )
                    )
            chain(ring + ring[:1])
        x0, y0, x1, y1 = self.bounds
        # Constrained grid lines also split incoming terrain edges and overlapping
        # capsule edges. A free point grid leaves long edges unsampled at elbows.
        for iy in range(math.ceil(y0 / step), math.ceil(y1 / step)):
            y = iy * step
            chain([(x0, y), (x1, y)])
        for ix in range(math.ceil(x0 / step), math.ceil(x1 / step)):
            x = ix * step
            chain([(x, y0), (x, y1)])
        return points, edges


def refit_triangle(corners, uvs, material, grades, road_tree, output):
    """Constrain one source plane, retaining its winding, material and UV seams."""
    a, b, c = corners
    det = (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])
    if abs(det) < 1e-9:
        output.face(corners, material, uvs)
        return
    points, edges = [p[:2] for p in corners], []
    for grade in grades:
        offset = len(points)
        points.extend(grade.controls)
        edges.extend((i + offset, j + offset) for i, j in grade.edges)
    xy, faces, owners = _cdt(points, edges, [(0, 1, 2)], points[0])
    texture_planes = [
        [(*p[:2], uv[axis]) for p, uv in zip(corners, uvs)] for axis in (0, 1)
    ]
    positions, texcoords = {}, {}
    for face, parent in zip(faces, owners):
        if not parent:
            continue
        order = face if det > 0 else face[::-1]
        for i in order:
            if i in positions:
                continue
            x, y = xy[i]
            z = _plane((x, y), corners)
            change = 0.0
            for grade in grades:
                distance, target = grade.profile(x, y)
                weight = smooth((grade.radius - distance) / (grade.radius - grade.core))
                change += weight * max(-grade.limit, min(grade.limit, target - z))
            if change > 0:
                road = road_tree.ray_cast((x, y, 80), (0, 0, -1), 160)[0]
                if road is not None:
                    change = min(change, max(0, road.z - z - 0.012))
            positions[i] = (x, y, z + change)
            texcoords[i] = tuple(_plane((x, y), plane) for plane in texture_planes)
        output.face(
            [positions[i] for i in order], material, [texcoords[i] for i in order]
        )


def apply_wall_grades(base):
    """Apply the eleven documented grades in Blender world metres after road grading."""
    grades = [WallGrade(record) for record in grade_records()]
    terrain = base['terrain']
    local = Mesh()
    removed = set()
    for i, face in enumerate(terrain.f):
        pts = [terrain.v[j] for j in face]
        area = bounds(pts)
        if any(overlaps(area, grade.bounds) for grade in grades):
            local.face(pts, terrain.m[i], _source_uv(terrain, i, pts, True))
            removed.add(i)

    roads = Mesh()
    for name, mesh in base.items():
        if name in ('roads', 'north-campus-roads') or name.startswith(
            ('site-', 'infra-', 'paving-')
        ):
            for face, mat in zip(mesh.f, mesh.m):
                pts = [mesh.v[j] for j in face]
                area = bounds(pts)
                if any(overlaps(area, grade.bounds) for grade in grades):
                    roads.face(pts, mat)
    road_tree = sample(roads)
    result = Mesh()
    for tri, i in mesh_triangles(local):
        corners = [local.v[j] for j in tri]
        area = bounds(corners)
        active = [g for g in grades if overlaps(area, g.bounds)]
        uvs = [local.face_uvs[i][local.f[i].index(j)] for j in tri]
        refit_triangle(corners, uvs, local.m[i], active, road_tree, result)
    _splice(terrain, removed, result)
