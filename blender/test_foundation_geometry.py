"""Actual mesh regression tests for bounded grading and service-road trimming."""
import sys
import unittest
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from geometry import Mesh
from site_geometry import mesh_triangles
from foundation_geometry import build_foundations


def square(x0,y0,x1,y1):
    return [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]


def mesh(ring,z):
    m=Mesh();m.face([(x,y,z(x,y) if callable(z) else z) for x,y in ring],0);return m


def height(m,x,y):
    tree=BVHTree.FromPolygons(m.v,[ids for ids,_ in mesh_triangles(m)],all_triangles=True)
    hit=tree.ray_cast(Vector((x,y,100)),Vector((0,0,-1)),200)[0]
    return None if hit is None else hit.z


class FoundationRepairTests(unittest.TestCase):
    def setUp(self):
        core=square(-1,-1,1,1);outer=square(-3,-3,3,3)
        self.record={'id':'fixture','datum':0,'groundOffset':0,'bounds':[-3,-3,3,3],
            'roadTrimBounds':[-1,-1,1,1],'corePolygons':[[core+[core[0]]]],
            'gradingPolygons':[[outer+[outer[0]]]],'coreMasks':[core],
            'transitionMasks':[square(-3,-3,3,-1),square(-3,1,3,3),square(-3,-1,-1,1),square(1,-1,3,1)],
            'roadTrimMasks':[core]}

    def repair(self,terrain,roads=None):
        return build_foundations({'foundations':[self.record]},terrain,roads or Mesh())[:2]

    def test_high_coarse_plane_clears_floor_and_retains_outside_slope(self):
        old=mesh(square(-5,-5,5,5),lambda x,y:4+x/10)
        ground,_=self.repair(old)
        for xy in [(0,0),(.9,.9),(-.9,-.9)]:
            self.assertAlmostEqual(height(ground,*xy),0,places=4)
        for xy in [(4,0),(-4,0),(0,4),(0,-4),(3,0),(-3,0)]:
            self.assertAlmostEqual(height(ground,*xy),height(old,*xy),places=4)
        self.assertGreater(height(ground,2,0),0)
        self.assertLess(height(ground,2,0),height(old,2,0))

    def test_road_is_removed_inside_mask_and_original_plane_retained_outside(self):
        road=mesh(square(-5,-.3,5,.3),lambda x,y:1+x/20)
        _,clipped=self.repair(mesh(square(-5,-5,5,5),0),road)
        self.assertIsNone(height(clipped,0,0))
        for x in (-4,-1.1,1.1,4):
            self.assertAlmostEqual(height(clipped,x,0),height(road,x,0),places=4)

    def test_low_ground_is_not_raised(self):
        old=mesh(square(-5,-5,5,5),-2)
        ground,_=self.repair(old)
        self.assertAlmostEqual(height(ground,0,0),-2)

    def test_protected_hole_preserves_ground_and_road_support(self):
        # A road-sized interior hole keeps its original ground support.
        core=square(-2,-.5,-1,.5);hole=square(0,-1,1,1)
        self.record['coreMasks']=[core]
        self.record['corePolygons']=[[core+[core[0]]]]
        self.record['gradingPolygons'][0].append(hole+[hole[0]])
        self.record['transitionMasks']=[square(-3,-3,3,-1),square(-3,1,3,3),
            square(-3,-1,-2,1),square(-2,.5,0,1),square(-2,-1,0,-.5),
            square(-1,-.5,0,.5),square(1,-1,3,1)]
        ground,_=self.repair(mesh(square(-5,-5,5,5),3))
        self.assertAlmostEqual(height(ground,.5,0),3,places=4)
        self.assertAlmostEqual(height(ground,-1.5,0),0,places=4)


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FoundationRepairTests))
    if not result.wasSuccessful():raise AssertionError('Foundation repair tests failed')
