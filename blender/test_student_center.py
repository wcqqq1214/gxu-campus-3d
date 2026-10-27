"""Run in Blender: mapped tower void and one-storey terrace must survive both LODs."""
import json
import sys
import unittest
from pathlib import Path
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'blender'))
from landmarks import landmark


class StudentCenterGeometry(unittest.TestCase):
    def test_terrace_tower_void_and_main_roof(self):
        l=next(x for x in json.loads((ROOT/'public/data/landmarks.json').read_text()) if x['id']=='student-center')
        b=next(x for x in json.loads((ROOT/'public/data/buildings.json').read_text()) if x['id']==l['osmId'])
        c={k:i for i,k in enumerate(['stone','white','glass','dark','slate','wood','metal','path','paleRoof','libraryInk','red','studentRailGlass'])}
        for detail in (False,True):
            with self.subTest(detail=detail):
                mesh=landmark(l,b,0,c,detail)
                tree=BVHTree.FromPolygons(mesh.v,mesh.f)
                hit=tree.ray_cast((230,42,50),(0,0,-1))[0]
                self.assertIsNotNone(hit)
                self.assertAlmostEqual(hit.z,4.4,places=3)
                self.assertIsNone(tree.ray_cast((239.9,50.1,50),(0,0,-1))[0],
                                  'Do not cap the mapped water-tower void')
                hit=tree.ray_cast((265,30,50),(0,0,-1))[0]
                self.assertIsNotNone(hit)
                self.assertAlmostEqual(hit.z,22,places=3)
                hit=tree.ray_cast((265,24.3,5.6),(0,0,1))[0]
                self.assertIsNotNone(hit,'Projecting balcony requires a visible soffit')
                self.assertAlmostEqual(hit.z,7.96,places=3)
                self.assertTrue(all(v[2]>=0 for v in mesh.v))
                # The removed guessed rectangular porch used to protrude south
                # at the midpoint of the whole footprint, away from the main wall.
                self.assertIsNone(tree.ray_cast((274.6,1.6,10),(0,0,-1))[0])


result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(StudentCenterGeometry))
if not result.wasSuccessful():raise SystemExit(1)
