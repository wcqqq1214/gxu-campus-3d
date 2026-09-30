"""Regression fixtures for actual-triangle road grounding and retained contacts."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from geometry import Mesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from site_geometry import mesh_triangles
from service_road_geometry import build_service_road
from test_foundation_geometry import square,mesh,height


class ServiceRoadTests(unittest.TestCase):
    def setUp(self):
        self.record={'surfaceId':'fixture','offset':.08,'burial':.06,'joinFeather':2,
                     'polygons':[[square(0,-1,10,1)]],'bounds':[0,-1,10,1],'repairArea':20,'contacts':[[[0,-1],[0,1]]],
                     'freeEdges':[[[0,-1],[10,-1],[10,1],[0,1]]],
                     'coreMaskCount':8,'corePolygons':[[square(2,-1,10,1)]],
                     'masks':[square(x,-1,x+1,1) for x in [*range(2,10),0,1]]}

    def build(self,ground,roads):return build_service_road(self.record,{'road':0},ground,roads)[0]

    def test_floating_and_buried_road_follow_actual_ground_crease(self):
        ground=mesh(square(-2,-3,5,3),lambda x,y:x/10)
        ground.extend(mesh(square(5,-3,12,3),lambda x,y:.5-(x-5)/5))
        old=mesh(square(-1,-1,11,1),lambda x,y:.4-x/8)
        original=list(ground.v)
        road=self.build(ground,old)
        for x in (2.1,4.9,5,5.1,8,9.9):
            self.assertAlmostEqual(height(road,x,0)-height(ground,x,0),.08,places=4)
        self.assertEqual(ground.v,original)
        self.assertAlmostEqual(height(road,-.5,0),height(old,-.5,0),places=4)
        self.assertAlmostEqual(height(road,.00001,0),.4,places=4)

    def test_buried_target_at_join_uses_retained_neighbor_plane(self):
        old=mesh(square(0,-1,11,1),-1)
        old.extend(mesh(square(-1,-1,0,1),.4))
        road=self.build(mesh(square(-2,-3,12,3),0),old)
        self.assertAlmostEqual(height(road,.00001,0),.4,places=4)
        self.assertAlmostEqual(height(road,-.2,0),.4,places=4)
        self.assertAlmostEqual(height(road,3,0),.08,places=4)

    def test_shared_local_export_extends_existing_node_without_mutating_source(self):
        from paving_geometry import split_grounded_road_exports
        old=mesh(square(-20,-20,30,30),.4);before=list(old.v)
        record={'id':'existing','groundedService':{},'bounds':[0,0,2,2]}
        result=split_grounded_road_exports({'roads':old},[record],[{'exportWith':'existing','bounds':[0,0,20,20]}])
        self.assertEqual(set(result),{'roads','paving-existing-export'})
        self.assertEqual(old.v,before)
        self.assertAlmostEqual(height(result['paving-existing-export'],20,20),.4,places=4)
        self.assertAlmostEqual(height(result['roads'],-10,-10),.4,places=4)

    def test_neighbor_vertical_closure_is_retained(self):
        road=mesh(square(-1,-1,11,1),.4)
        closure=[(0,0,-1),(0,1,-1),(0,1,.4),(0,0,.4)]
        road.face(closure,1)
        result=self.build(mesh(square(-2,-3,12,3),0),road)
        tree=BVHTree.FromPolygons(result.v,[ids for ids,i in mesh_triangles(result) if result.m[i]==1],all_triangles=True)
        for y in (.1,.5,.9):
            for z in (-.9,0,.3):
                hit=tree.ray_cast(Vector((.2,y,z)),Vector((-1,0,0)),.4)[0]
                self.assertIsNotNone(hit)
                self.assertAlmostEqual(hit.x,0,places=5)

    def test_free_edge_has_buried_bottom_and_top_at_every_station(self):
        result=self.build(mesh(square(-2,-3,12,3),0),mesh(square(-1,-1,11,1),.4))
        tree=BVHTree.FromPolygons(result.v,[ids for ids,_ in mesh_triangles(result)],all_triangles=True)
        for x in (.2,1,3,5,9.8):
            for y,sign in ((-1,-1),(1,1)):
                for z in (-.05,.04):
                    hit=tree.ray_cast(Vector((x,y+sign*.2,z)),Vector((0,-sign,0)),.4)[0]
                    self.assertIsNotNone(hit)
                    self.assertAlmostEqual(hit.y,y,places=4)



if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ServiceRoadTests))
    if not result.wasSuccessful():raise AssertionError('Service-road fixtures failed')
