"""Analytic crossfall, rotated-frame, boundary and failure fixtures."""
import math,sys,unittest
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parent),str(Path(__file__).resolve().parents[1]/'scripts')]
from geometry import Mesh
from road_landing_geometry import build_landing, world, weight
from mathutils import Vector
from mathutils.bvhtree import BVHTree

class LandingTests(unittest.TestCase):
    def fixture(self,angle=0):
        r=dict(id='fixture',origin=[30,-40],normal=[-math.sin(angle),math.cos(angle)],tangent=[math.cos(angle),math.sin(angle)],halfWidth=2,sideFeather=1,depthStations=[.2,.65,1.25,4.5],meshStep=1,targetElevation=5,minimumTerrainClearance=.12)
        points=[world(r,x,y) for x,y in [(-5,0),(5,0),(5,5),(-5,5)]]
        r['surface']={'vertices':points,'triangles':[0,1,2,0,2,3]}
        road=Mesh();ground=Mesh()
        for ids in [(0,1,2),(0,2,3)]:
            road.face([(*points[i],5+[-.2,.2,.2,-.2][i]) for i in ids],0)
            ground.face([(*points[i],4) for i in ids],0)
        return r,road,ground
    def height(self,mesh,point):
        tree=BVHTree.FromPolygons(mesh.v,mesh.f)
        hit=tree.ray_cast(Vector((*point,10)),Vector((0,0,-1)),20)[0]
        self.assertIsNotNone(hit)
        return hit.z
    def check_grade(self,angle):
        r,road,ground=self.fixture(angle);after,report=build_landing(r,road,ground,0)
        for x in [-1.9,0,1.9]:self.assertAlmostEqual(self.height(after,world(r,x,.935)),5,places=5)
        for x,y in [(-4,2),(4,2),(0,.05),(0,4.8),(-3,2),(3,2),(1,.2),(1,4.5)]:
            self.assertAlmostEqual(self.height(after,world(r,x,y)),self.height(road,world(r,x,y)),places=5)
        self.assertGreater(report['minimumSampledTerrainClearance'],.7)
        # Adjacent points across the clipping boundary approach the same height.
        for x in [-3,3]:self.assertLess(abs(self.height(after,world(r,x-.001,2))-self.height(after,world(r,x+.001,2))),.001)
    def test_crossfall(self):self.check_grade(0)
    def test_rotated(self):self.check_grade(.47)
    def test_outside_road_rejected(self):
        r,road,g=self.fixture();r['depthStations'][-1]=6
        with self.assertRaisesRegex(ValueError,'leaves mapped'):build_landing(r,road,g,0)
    def test_overlapping_road_rejected(self):
        r,road,g=self.fixture();road.extend(road)
        with self.assertRaisesRegex(ValueError,'overlapping'):build_landing(r,road,g,0)
    def test_burial_rejected(self):
        r,road,g=self.fixture();r['targetElevation']=3
        with self.assertRaisesRegex(ValueError,'intrusion'):build_landing(r,road,g,0)

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LandingTests))
    if not result.wasSuccessful():raise SystemExit(1)
