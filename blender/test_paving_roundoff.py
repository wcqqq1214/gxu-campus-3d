"""A sampled paving plane must not fragment sound ground for sub-mm noise."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from geometry import Mesh
from paving_geometry import clear_paving_ground

class GroundRoundoffTests(unittest.TestCase):
    def ground(self):
        m=Mesh();m.face([(0,0,0),(4,0,0),(4,4,0),(0,4,0)],0);return m
    def patch(self,z):
        m=Mesh();m.face([(1,1,z),(3,1,z),(3,3,z),(1,3,z)],0);return m
    def test_sample_noise_keeps_original_plane(self):
        ground=self.ground()
        result,report=clear_paving_ground(ground,self.patch(.0695),dict(bounds=[1,1,3,3],groundClearance=.07,roundoffTolerance=.002))
        self.assertIs(result,ground);self.assertEqual(report['loweredPieces'],0)
    def test_real_excavation_is_retained(self):
        ground=self.ground()
        result,report=clear_paving_ground(ground,self.patch(-1),dict(bounds=[1,1,3,3],groundClearance=.07,roundoffTolerance=.002))
        self.assertGreater(report['loweredPieces'],0);self.assertAlmostEqual(min(v[2] for v in result.v),-1.07,places=5)
        self.assertTrue(all(v[2]==0 for v in result.v if v[0]<1 or v[0]>3 or v[1]<1 or v[1]>3))
    def test_default_remains_strict(self):
        ground=self.ground()
        result,report=clear_paving_ground(ground,self.patch(.0695),dict(bounds=[1,1,3,3],groundClearance=.07))
        self.assertIsNot(result,ground);self.assertGreater(report['loweredPieces'],0)

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(GroundRoundoffTests)
    if not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful():raise SystemExit(1)
