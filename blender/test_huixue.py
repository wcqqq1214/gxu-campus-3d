"""Guard the observed open galleries and the two-flight entrance in both LODs."""
import json
import math
from pathlib import Path
import sys
import unittest

from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'blender'))
from huixue import huixue


class HuixueTests(unittest.TestCase):
    def test_gallery_voids_and_stair_landing_survive_both_lods(self):
        record = next(r for r in json.loads((ROOT / 'public/data/landmarks.json').read_text())
                      if r['id'] == 'huixue')
        colors = {name: i for i, name in enumerate(
            ('stone', 'white', 'glass', 'dark', 'slate', 'wood', 'metal', 'red', 'path', 'green', 'huixueRoof'))}
        xmin, ymin, xmax, ymax = record['bounds']
        cx, cy = (xmin+xmax)/2, (ymin+ymax)/2
        ground = record['elevation']
        # Independent acceptance probes in world coordinates: the entrance
        # faces east, a wing bay stays open, and the middle stair landing is flat.
        for detail in (False, True):
            with self.subTest(detail=detail):
                mesh = huixue(record, None, ground, colors, detail)
                self.assertTrue(all(math.isfinite(c) for v in mesh.v for c in v))
                bvh = BVHTree.FromPolygons([Vector(v) for v in mesh.v], mesh.f)
                entry = bvh.ray_cast(Vector((xmax+2, cy, ground+6)), Vector((-1, 0, 0)), 20)[0]
                self.assertIsNotNone(entry)
                self.assertGreater(entry.x, xmax-10)
                # A front gallery bay must not become an opaque glass facade.
                bay = bvh.ray_cast(Vector((xmax+2, cy+26, ground+9)), Vector((-1, 0, 0)), 10)[0]
                self.assertIsNone(bay)
                heights = []
                for east in (xmax+1.5, xmax+2.2):
                    hit = bvh.ray_cast(Vector((east, cy, ground+5)), Vector((0, 0, -1)), 6)[0]
                    self.assertIsNotNone(hit)
                    heights.append(hit.z)
                self.assertAlmostEqual(heights[0], heights[1], places=3)
                self.assertAlmostEqual(heights[0], ground+1.5, places=3)
                # The consultant's low-angle front photo shows a steep upper
                # entry pitch above the main front eave, not one shallow cap.
                entry_roof = bvh.ray_cast(Vector((-190, cy, ground+30)),
                                           Vector((0, 0, -1)), 10)[0]
                self.assertIsNotNone(entry_roof)
                self.assertGreater(entry_roof.z-ground, 23)
                self.assertLess(entry_roof.z-ground, 24.3)
                # At this observed side bay, glass on the lower floor must be
                # separated from the next floor by an opaque stone spandrel.
                for height, material in [(5.5, 'glass'), (7.2, 'stone')]:
                    hit = bvh.ray_cast(Vector((-220.8, -465, ground+height)),
                                       Vector((0, -1, 0)), 20)
                    self.assertIsNotNone(hit[0])
                    self.assertEqual(mesh.m[hit[2]], colors[material])
                # Mid-flight probes on both external side stairs: placing the
                # flight on the column axis would hit a pier instead of a tread.
                for north in (-469.99, -551.46):
                    hit = bvh.ray_cast(Vector((-249.5, north, ground+6)),
                                       Vector((0, 0, -1)), 7)[0]
                    self.assertIsNotNone(hit)
                    self.assertGreater(hit.z-ground, 1.2)
                    self.assertLess(hit.z-ground, 1.9)
                    overhead = bvh.ray_cast(hit+Vector((0, 0, 1.8)),
                                            Vector((0, 0, 1)), 8)[0]
                    self.assertIsNone(overhead)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]])
