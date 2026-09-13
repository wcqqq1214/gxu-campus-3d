"""Containment in closed, orientable triangle components.

Weld duplicated face vertices on a micrometre coordinate grid, but never cap an
open mesh. Reconstruct consistent winding per shell; input face normals are not
trusted. Open/non-manifold components remain available as surface witnesses and
are reported separately, not silently treated as occupied bounding boxes.
"""
import math
from collections import defaultdict
from itertools import product

CELL_METERS = 16


def cell(point):
    return tuple(math.floor(value/CELL_METERS) for value in point)


def cells(box):
    low, high = cell(box[0]), cell(box[1])
    return product(*(range(a, b+1) for a, b in zip(low, high)))


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def subtract(a, b):
    return tuple(x-y for x, y in zip(a, b))


def contains_bounds(box, point):
    return all(box[0][axis] <= point[axis] <= box[1][axis] for axis in range(3))


class ClosedShell:
    def __init__(self, vertices, triangles):
        self.triangles = [tuple(vertices[i] for i in tri) for tri in triangles]
        points = [p for tri in self.triangles for p in tri]
        self.bounds = tuple(tuple(fn(p[k] for p in points) for k in range(3)) for fn in (min, max))

    def contains(self, point):
        if not contains_bounds(self.bounds, point):
            return False
        angles = []
        for triangle in self.triangles:
            a, b, c = [subtract(v, point) for v in triangle]
            la, lb, lc = [math.sqrt(dot(v, v)) for v in (a, b, c)]
            if min(la, lb, lc) == 0:
                return True
            numerator = dot(a, cross(b, c))
            denominator = la*lb*lc + dot(a, b)*lc + dot(b, c)*la + dot(c, a)*lb
            angles.append(2*math.atan2(numerator, denominator))
        # A closed consistent shell subtends ±4π inside and zero outside.
        # Boundary contact is also handled by the caller's surface overlap pass.
        return abs(math.fsum(angles)) > 2*math.pi


class MeshVolumes:
    def __init__(self, vertices, triangles):
        welded, mapping, lookup = [], [], {}
        for vertex in vertices:
            point = tuple(round(float(v), 6) for v in vertex)
            if not all(math.isfinite(v) for v in point):
                raise ValueError('Containment requires finite mesh coordinates')
            if point not in lookup:
                lookup[point] = len(welded)
                welded.append(point)
            mapping.append(lookup[point])
        faces, seen = [], set()
        for triangle in triangles:
            face = tuple(mapping[i] for i in triangle)
            if len(face) != 3:
                raise ValueError('Containment requires triangulated meshes')
            key = tuple(sorted(face))
            if len(set(face)) != 3 or key in seen:
                continue
            a, b, c = [welded[i] for i in face]
            normal = cross(subtract(b, a), subtract(c, a))
            if dot(normal, normal) == 0:
                continue
            seen.add(key)
            faces.append(face)
        edge_faces = defaultdict(list)
        face_edges = []
        for i, face in enumerate(faces):
            edges = []
            for a, b in zip(face, face[1:]+face[:1]):
                edge = tuple(sorted((a, b)))
                direction = 1 if (a, b) == edge else -1
                edge_faces[edge].append((i, direction))
                edges.append((edge, direction))
            face_edges.append(edges)
        self.shells, self.representatives = [], []
        self.open_components = 0
        visited = set()
        for first in range(len(faces)):
            if first in visited:
                continue
            pending = [first]
            signs = {first: 1}
            visited.add(first)
            closed = True
            while pending:
                current = pending.pop()
                for edge, direction in face_edges[current]:
                    neighbors = edge_faces[edge]
                    if len(neighbors) != 2:
                        closed = False
                    for other, other_direction in neighbors:
                        if other == current:
                            continue
                        expected = -signs[current]*direction*other_direction
                        if other in signs:
                            if signs[other] != expected:
                                closed = False
                        else:
                            signs[other] = expected
                            visited.add(other)
                            pending.append(other)
            self.representatives.append(welded[faces[first][0]])
            if closed:
                oriented = [faces[i] if sign == 1 else faces[i][::-1] for i, sign in signs.items()]
                self.shells.append(ClosedShell(welded, oriented))
            else:
                self.open_components += 1
        self._shell_cells, self._point_cells = defaultdict(list), defaultdict(list)
        self._large_shells = []
        for shell in self.shells:
            low, high = cell(shell.bounds[0]), cell(shell.bounds[1])
            if math.prod(b-a+1 for a, b in zip(low, high)) > 4096:
                self._large_shells.append(shell)
            else:
                for key in cells(shell.bounds):
                    self._shell_cells[key].append(shell)
        for point in self.representatives:
            self._point_cells[cell(point)].append(point)

    def representatives_in_bounds(self, box):
        for key in cells(box):
            for point in self._point_cells.get(key, ()):
                if contains_bounds(box, point):
                    yield point

    def witness_inside(self, points):
        for point in points:
            nearby = self._shell_cells.get(cell(point), ())
            if any(shell.contains(point) for shell in nearby) or any(shell.contains(point) for shell in self._large_shells):
                return tuple(point)
        return None
