"""Exercise the ground audit with real mesh intersections, including service roads."""
import sys
import unittest
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inspect_foundation_clearance import measure, sample_parts


class FoundationAuditTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.material = bpy.data.materials.new('audit-fixture')
        self.building = {'elevation': 0, 'form': {'parts': [
            {'id': 'closed', 'height': 4, 'polygons': [[[[0, 0], [4, 0], [4, 4], [0, 4], [0, 0]]]]},
            {'id': 'portico', 'height': 4, 'openBelow': {'floorHeight': 1},
             'polygons': [[[[4, 0], [6, 0], [6, 4], [4, 4], [4, 0]]]]},
        ]}}
        self.points = sample_parts(self.building, 1)

    def mesh(self, name, layer, points):
        data = bpy.data.meshes.new(name)
        data.from_pydata(points, [], [(0, 1, 2), (0, 2, 3)])
        data.materials.append(self.material)
        obj = bpy.data.objects.new(name, data)
        bpy.context.scene.collection.objects.link(obj)
        obj['layer'] = layer
        return obj

    def ground(self, high=0):
        return self.mesh('terrain', 'terrain', [(-2, -2, 0), (6, -2, high), (6, 6, high), (-2, 6, 0)])

    def road(self, x=10, z=1.25):
        return self.mesh('ordinary-service-road', 'roads', [(x, 1, z), (x+2, 1, z), (x+2, 3, z), (x, 3, z)])

    def result(self):
        bpy.context.view_layer.update()
        return measure(self.building, self.points, .3, 'fixture')[0]

    def test_clear_ground_passes_and_open_portico_is_not_a_closed_floor(self):
        self.ground()
        self.road(x=4)
        result = self.result()
        self.assertTrue(result['passed'])
        self.assertEqual({p[0] for p in self.points}, {'closed'})

    def test_high_external_grid_corners_expose_interior_terrain_burial(self):
        self.ground(high=4)
        self.road()
        result = self.result()
        self.assertFalse(result['passed'])
        self.assertGreater(result['parts'][0]['maximumTerrainAboveDatum'], 2)
        self.assertGreater(result['parts'][0]['terrainIntrusionSamples'], 0)

    def test_ordinary_service_road_is_detected_without_infrastructure_id(self):
        self.ground()
        self.road(x=1)
        result = self.result()
        self.assertFalse(result['passed'])
        part = result['parts'][0]
        self.assertEqual(part['terrainIntrusionSamples'], 0)
        self.assertGreater(part['roadIntrusionSamples'], 0)
        self.assertEqual(part['worstRoadSamples'][0]['roadHit']['object'], 'ordinary-service-road')

    def test_courtyard_hole_is_not_sampled_as_closed_ground_floor(self):
        self.building['form']['parts'][0]['polygons'][0].append([[1, 1], [1, 3], [3, 3], [3, 1], [1, 1]])
        points = sample_parts(self.building, 1)
        self.assertFalse(any(1 < x < 3 and 1 < y < 3 for _, x, y, _ in points))
        self.assertGreater(len(points), 0)

    def test_road_above_roof_does_not_hide_a_lower_intrusive_road(self):
        self.ground()
        self.road(x=1, z=6)
        self.assertTrue(self.result()['passed'])
        self.road(x=1, z=1)
        result = self.result()
        self.assertFalse(result['passed'])
        self.assertAlmostEqual(result['parts'][0]['worstRoadSamples'][0]['roadAboveDatum'], 1)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(FoundationAuditTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise AssertionError('Foundation audit fixture failed')
