"""Factory-startup regressions for real foundation meshes, without a .blend.

Both production simplification modes exercise Blender triangulation, BMesh and
BVH ray casts. The civil fixture retains the original non-planar terrain quad
that exposed a roughly 6.7 mm change outside the grading boundary (e72301b).
"""
import json
import math
from pathlib import Path
import sys
import unittest

from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from foundation_geometry import build_foundations, clipped_mesh, masks_for
from geometry import Mesh
from site_geometry import mesh_triangles


def square(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def plane(ring, level, material=6):
    result = Mesh()
    result.face([(x, y, level(x, y) if callable(level) else level)
                 for x, y in ring], material)
    return result


class Surface:
    """Sample the complete output mesh using Blender's actual quad diagonal."""
    def __init__(self, mesh):
        self.mesh = mesh
        self.triangles = mesh_triangles(mesh)
        self.tree = BVHTree.FromPolygons(
            mesh.v, [ids for ids, _ in self.triangles], all_triangles=True)

    def hit(self, x, y):
        return self.tree.ray_cast(Vector((x, y, 150)), Vector((0, 0, -1)), 300)

    def height(self, x, y):
        position = self.hit(x, y)[0]
        return None if position is None else position.z

    def material(self, x, y):
        index = self.hit(x, y)[2]
        return None if index is None else self.mesh.m[self.triangles[index][1]]


class FoundationGeometryCases:
    """One behavior contract, exercised with default and welded simplification."""
    simplification = None

    def setUp(self):
        core = square(-1, -1, 1, 1)
        outer = square(-3, -3, 3, 3)
        self.record = {
            'id': 'fixture', 'datum': 0, 'groundOffset': 0,
            'bounds': [-3, -3, 3, 3], 'roadTrimBounds': [-1, -1, 1, 1],
            'corePolygons': [[core + [core[0]]]],
            'gradingPolygons': [[outer + [outer[0]]]], 'coreMasks': [core],
            'transitionMasks': [square(-3, -3, 3, -1), square(-3, 1, 3, 3),
                                square(-3, -1, -1, 1), square(1, -1, 3, 1)],
            'roadTrimMasks': [core],
        }
        if self.simplification:
            self.record['meshSimplification'] = dict(self.simplification)

    def repair(self, terrain, roads=None):
        return build_foundations(
            {'foundations': [self.record]}, terrain,
            Mesh() if roads is None else roads)

    def assert_height(self, surface, x, y, expected, tolerance=1e-4):
        actual = surface.height(x, y)
        self.assertIsNotNone(actual, ('missing surface', x, y))
        self.assertAlmostEqual(actual, expected, delta=tolerance,
                               msg=str((x, y, actual, expected)))

    def assert_mesh(self, mesh, expected_area, materials, area_tolerance=1e-4):
        """Check every triangle and the aggregate projected coverage area."""
        self.assertEqual(len(mesh.f), len(mesh.m))
        self.assertEqual(set(mesh.m), materials)
        area = 0
        for ids, _ in mesh_triangles(mesh):
            a, b, c = (Vector(mesh.v[index]) for index in ids)
            self.assertTrue(all(math.isfinite(value) for p in (a, b, c) for value in p))
            signed_area = (b - a).cross(c - a).z / 2
            self.assertGreater(signed_area, 1e-9, ('degenerate/reversed face', ids))
            area += signed_area
        self.assertAlmostEqual(area, expected_area, delta=area_tolerance)

    def test_high_plane_clears_core_and_retains_complete_outside_slope(self):
        original = plane(square(-5, -5, 5, 5), lambda x, y: 4 + x / 10)
        before = Surface(original)
        ground, _, reports = self.repair(original)
        self.assert_mesh(ground, 100, {6})
        after = Surface(ground)
        for x in (-.9, 0, .9):
            for y in (-.9, 0, .9):
                self.assert_height(after, x, y, 0)
        # The unchanged exterior is a known plane, independent of grading math.
        for x in (-4.5, -3, -2, 0, 2, 3, 4.5):
            for y in (-4.5, -3, -2, 0, 2, 3, 4.5):
                if abs(x) >= 3 or abs(y) >= 3:
                    self.assert_height(after, x, y, 4 + x / 10)
        # The finite mesh approximates the grade between its vertices. Probe
        # inside each apron near the core without requiring an analytic field.
        for x, y in ((1.5, 0), (-1.5, 0), (0, 1.5), (0, -1.5)):
            self.assertGreater(after.height(x, y), 0)
            self.assertLess(after.height(x, y), before.height(x, y))
        self.assertGreater(reports[0]['terrain']['affectedTriangles'], 0)
        self.assertGreater(reports[0]['terrain']['maximumLoweringMeters'], 3)

    def test_core_uses_datum_plus_ground_offset(self):
        self.record.update(datum=-1.25, groundOffset=.25)
        ground, _, _ = self.repair(plane(square(-5, -5, 5, 5), 3))
        self.assert_mesh(ground, 100, {6})
        after = Surface(ground)
        for x, y in ((0, 0), (-.9, -.9), (.9, .9)):
            self.assert_height(after, x, y, -1)
        self.assert_height(after, 4, 0, 3)

    def test_road_trim_removes_core_and_preserves_outside_plane_and_material(self):
        road = plane(square(-5, -.3, 5, .3), lambda x, y: 1 + x / 20, material=3)
        _, clipped, reports = self.repair(plane(square(-5, -5, 5, 5), 0), road)
        self.assert_mesh(clipped, 4.8, {3})
        after = Surface(clipped)
        for x in (-.9, 0, .9):
            for y in (-.25, 0, .25):
                self.assertIsNone(after.height(x, y), ('road still inside core', x, y))
        for x in (-4, -1.001, 1.001, 4):
            for y in (-.25, 0, .25):
                self.assert_height(after, x, y, 1 + x / 20)
                self.assertEqual(after.material(x, y), 3)
        self.assertGreater(reports[0]['roads']['affectedTriangles'], 0)

    def test_low_ground_is_never_raised(self):
        ground, _, reports = self.repair(plane(square(-5, -5, 5, 5), -2))
        self.assert_mesh(ground, 100, {6})
        after = Surface(ground)
        for x in (-4, -3, -.9, 0, .9, 3, 4):
            for y in (-4, -3, -.9, 0, .9, 3, 4):
                self.assert_height(after, x, y, -2)
        self.assertEqual(reports[0]['terrain']['maximumLoweringMeters'], 0)

    def test_protected_hole_keeps_ground_and_road_support_at_each_edge(self):
        core = square(-2, -.5, -1, .5)
        hole = square(0, -1, 1, 1)
        self.record.update(coreMasks=[core], corePolygons=[[core + [core[0]]]],
                           roadTrimMasks=[core], roadTrimBounds=[-2, -.5, -1, .5])
        self.record['gradingPolygons'][0].append(hole + [hole[0]])
        self.record['transitionMasks'] = [
            square(-3, -3, 3, -1), square(-3, 1, 3, 3), square(-3, -1, -2, 1),
            square(-2, .5, 0, 1), square(-2, -1, 0, -.5),
            square(-1, -.5, 0, .5), square(1, -1, 3, 1),
        ]
        road = plane(square(.1, -.8, .9, .8), 3, material=3)
        ground, retained, _ = self.repair(plane(square(-5, -5, 5, 5), 3), road)
        self.assert_mesh(ground, 100, {6})
        after = Surface(ground)
        for x, y in ((.5, 0), (0, 0), (1, 0), (.5, -1), (.5, 1)):
            self.assert_height(after, x, y, 3)
        self.assert_height(after, -1.5, 0, 0)
        self.assertEqual((retained.v, retained.f, retained.m), (road.v, road.f, road.m))
        self.assert_height(Surface(retained), .5, 0, 3)

    def test_shared_xy_boundary_keeps_both_original_surface_elevations(self):
        core = square(1, -1, 2, 1)
        outer = square(0, -3, 3, 3)
        self.record.update(
            bounds=[0, -3, 3, 3], coreMasks=[core],
            corePolygons=[[core + [core[0]]]], gradingPolygons=[[outer + [outer[0]]]],
            transitionMasks=[square(0, -3, 3, -1), square(0, 1, 3, 3),
                             square(0, -1, 1, 1), square(2, -1, 3, 1)])
        original = plane(square(-4, -4, 0, 4), 1, material=6)
        original.face([(x, y, 3) for x, y in square(0, -4, 4, 4)], 7)
        ground, _, _ = self.repair(original)
        self.assert_mesh(ground, 64, {6, 7})
        after = Surface(ground)
        for x, y in ((-.001, 0), (-.01, 0), (-.1, 1), (-1, -1)):
            self.assert_height(after, x, y, 1)
            self.assertEqual(after.material(x, y), 6)
        # At one XY, the lower and upper surfaces must each retain their Z.
        for material, level in ((6, 1), (7, 3)):
            boundary = [ground.v[k] for face, mat in zip(ground.f, ground.m)
                        if mat == material for k in face if abs(ground.v[k][0]) < 1e-5]
            self.assertTrue(boundary)
            for point in boundary:
                self.assertAlmostEqual(point[2], level, delta=1e-4)
        self.assert_height(after, 1.5, 0, 0)

    def test_civil_nonplanar_quad_preserves_exact_boundary_and_retained_side(self):
        fixture = json.loads((Path(__file__).parent / 'fixtures' /
                              'civil-foundation-boundary.json').read_text())
        self.record = fixture['record']
        if self.simplification:
            self.record['meshSimplification'] = dict(self.simplification)
        original = Mesh()
        original.v = fixture['vertices']
        original.f = fixture['faces']
        original.m = fixture['materials']
        before = Surface(original)
        ground, _, _ = self.repair(original)
        after = Surface(ground)
        x, y = fixture['probe']
        for dx in (0, -.001, -.01, -.1):
            # Above -10 proves rays hit the production quad, not the fixture's
            # separate -100 m support face; every cast includes both faces.
            expected = before.height(x + dx, y)
            self.assertGreater(expected, -10)
            self.assert_height(after, x + dx, y, expected)
            self.assertEqual(after.material(x + dx, y), 10)
        self.assert_mesh(ground, 40000 +
                         (fixture['vertices'][1][0] - fixture['vertices'][0][0]) *
                         (fixture['vertices'][3][1] - fixture['vertices'][0][1]),
                         # BMesh stores campus coordinates as float32; the
                         # separate height regression keeps its 0.1 mm limit.
                         {0, 10}, area_tolerance=.005)


class FoundationClipGeometryTests(unittest.TestCase):
    def test_mask_miss_preserves_original_road_quad_and_material(self):
        # This direct clipping behavior has no simplification setting, so it
        # runs once rather than duplicating it under both BMesh modes.
        original = plane(square(0, 0, 1, 1), 2, material=3)
        result, report = clipped_mesh(
            original, masks_for([square(2, 2, 3, 3)]), [-1, -1, 4, 4])
        self.assertEqual((result.v, result.f, result.m),
                         (original.v, original.f, original.m))
        self.assertEqual(report['affectedTriangles'], 0)


class FoundationGeometryTests(FoundationGeometryCases, unittest.TestCase):
    pass


class WeldedFoundationGeometryTests(FoundationGeometryCases, unittest.TestCase):
    simplification = {'normalTolerance': 1e-4, 'weldDistance': 1e-4}


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise AssertionError('Foundation geometry regressions failed')
