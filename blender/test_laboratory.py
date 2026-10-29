"""Probe circulation, column support and stepped silhouette in both LODs."""
import json
import math
from pathlib import Path
import sys
import unittest
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'blender'))
from laboratory import laboratory


class LaboratoryTests(unittest.TestCase):
    def test_through_passage_stairs_and_column_support(self):
        l = next(v for v in json.loads((ROOT/'public/data/landmarks.json').read_text())
                 if v['id'] == 'laboratory')
        z = l['elevation']
        for detail in (False, True):
            with self.subTest(detail=detail):
                m = laboratory(l, None, z, {'stone':0,'white':1,'glass':2}, detail)
                self.assertTrue(all(math.isfinite(c) for v in m.v for c in v))
                tree = BVHTree.FromPolygons([Vector(v) for v in m.v], m.f)
                # Centre must be physically clear along the entire campus axis.
                self.assertIsNone(tree.ray_cast(Vector((-377.65,-950,z+9)),
                                               Vector((0,1,0)),90)[0])
                roof = tree.ray_cast(Vector((-377.65,-907.6,z+9)),
                                     Vector((0,0,1)),30)[0]
                self.assertIsNotNone(roof)
                self.assertGreater(roof.z-z, 20)
                self.assertLess(roof.z-z, 25)
                # A floor must connect the stairs to the through-opening.
                for yy in (-930.5,-929.5,-928.5,-925,-900):
                    hit = tree.ray_cast(Vector((-377.65,yy,z+2)),Vector((0,0,-1)),2.1)[0]
                    self.assertIsNotNone(hit, yy)
                    self.assertAlmostEqual(hit.z-z,1.8,places=3)
                # Round columns sit on a solid podium, including the outer bay.
                for xx in (-417.78,-393.53,-361.76,-337.51):
                    hit = tree.ray_cast(Vector((xx,-929.96,z+1.7)),Vector((0,0,-1)),1.8)[0]
                    self.assertIsNotNone(hit)
                tops=[]
                for xx in (-377.65,-428,-441):
                    hit=tree.ray_cast(Vector((xx,-907.6,z+60)),Vector((0,0,-1)),65)[0]
                    self.assertIsNotNone(hit)
                    tops.append(hit.z)
                self.assertGreater(tops[0],tops[1]+4)
                self.assertGreater(tops[1],tops[2]+3)
                self.assertLess(abs(tops[0]-z-l['height']),1)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]])
