"""Verify the west-gate wing, pedestrian opening and name wall in both LODs."""

import json
import sys
import unittest
from pathlib import Path

from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'blender'))
from campus_gates import campus_gate


class WestGateGeometry(unittest.TestCase):
    def test_street_sections_and_catalogue_bounds(self):
        landmark = next(
            item
            for item in json.loads((ROOT / 'public/data/landmarks.json').read_text())
            if item['id'] == 'west-gate'
        )
        ground = landmark['elevation']
        for detail in (False, True):
            with self.subTest(detail=detail):
                gate = campus_gate(landmark, ground, {}, detail)
                tree = BVHTree.FromPolygons(gate.v, gate.f)
                # World-space sections from the accepted Luban Road street views.
                for label, x, y, lo, hi in [
                    ('white gate wing', -814.4, -225.73, 5.0, 5.8),
                    ('sloping name wall', -819.7, -243.73, 6.0, 6.9),
                ]:
                    hit = tree.ray_cast((x, y, ground + 10), (0, 0, -1))[0]
                    self.assertIsNotNone(hit, label)
                    self.assertTrue(lo < hit.z - ground < hi, label)
                # The gatehouse has a walk-through opening beside its glazed wall.
                for y, blocked in [(-225.73, False), (-227.73, True)]:
                    hit = tree.ray_cast((-816.4, y, ground + 1.8), (1, 0, 0), 4)[0]
                    self.assertEqual(hit is not None, blocked, y)

                cx, cy = landmark['center']
                x0, y0, x1, y1 = landmark['siteBoundsOffset']
                self.assertTrue(
                    all(
                        x0 - 0.001 <= x - cx <= x1 + 0.001
                        and y0 - 0.001 <= y - cy <= y1 + 0.001
                        for x, y, z in gate.v
                    ),
                    'scene framing omits west-gate geometry',
                )
                self.assertLessEqual(
                    max(z for x, y, z in gate.v), ground + landmark['height']
                )


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]])
