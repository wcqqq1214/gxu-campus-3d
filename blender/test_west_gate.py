"""Evidence-backed gate masses, bounds and traversable lanes in both LODs."""
import json,sys,unittest
from pathlib import Path
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from campus_gates import west_gate,campus_gate

class WestGateGeometry(unittest.TestCase):
    def test_video_masses_and_open_lanes(self):
        C={k:i for i,k in enumerate(['white','glass','metal','dark','gateTrim','gateRed','path','paleRoof','wood'])}
        l=next(l for l in json.loads((ROOT/'public/data/landmarks.json').read_text()) if l['id']=='west-gate')
        for detail in (False,True):
            with self.subTest(detail=detail):
                m=west_gate(C,detail);tree=BVHTree.FromPolygons(m.v,m.f)
                # North canopy and south name wall must both exist in the far asset.
                roof=tree.ray_cast((-7.0,.3,15),(0,0,-1))[0]
                wall=tree.ray_cast((10.0,-1.55,15),(0,0,-1))[0]
                self.assertIsNotNone(roof);self.assertIsNotNone(wall)
                self.assertGreater(roof.z,5);self.assertGreater(wall.z,6)
                self.assertLess(max(z for x,y,z in m.v),7)
                for x in (-2,0,2,5.4,6.8):
                    self.assertIsNone(tree.ray_cast((x,-8,1.2),(0,1,0),16)[0])
                # No cross-road lintel may re-close the central open entrance.
                self.assertIsNone(tree.ray_cast((0,0,15),(0,0,-1))[0])
                world=campus_gate(l,l['elevation'],C,detail)
                a,b,c,d=l['bounds']
                self.assertTrue(all(a-.001<=x<=c+.001 and b-.001<=y<=d+.001 for x,y,z in world.v))
                self.assertLessEqual(max(z for x,y,z in world.v),l['elevation']+l['height'])

if __name__=='__main__':unittest.main(argv=[sys.argv[0]])
