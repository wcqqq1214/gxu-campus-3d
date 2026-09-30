import unittest
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union
from surroundings_data import triangulate
from foundation_data import convex_masks
from service_road_data import derive_service_road


class ServiceRoadPreparationTests(unittest.TestCase):
    def setUp(self):
        self.config={'surfaceId':'target','offset':.08,'burial':.06,'joinFeather':2,'joinMeshStep':1.5}
        self.surface={'id':'target','kind':'roads','tags':{'highway':'service'},**triangulate(Polygon([(0,0),(10,0),(10,2),(0,2)]))}
        self.neighbor={'id':'neighbor','kind':'roads','tags':{'highway':'service'},**triangulate(Polygon([(-2,-1),(1,-1),(1,3),(-2,3)]))}

    def derive(self):return derive_service_road(self.config,[self.surface,self.neighbor],[],Polygon(),convex_masks)

    def test_masks_cover_repair_and_retain_neighbor_overlap(self):
        r=self.derive();cover=unary_union([Polygon(p) for p in r['masks']]);cuts=unary_union([Polygon(p) for p in r['cutMasks']])
        self.assertAlmostEqual(cover.area,18)
        self.assertLess(cover.symmetric_difference(cuts).area,1e-7)
        self.assertFalse(cover.contains(Point(.5,1)))
        self.assertAlmostEqual(r['retainedOverlapArea'],2)
        self.assertGreater(len(r['contacts']),0)
        self.assertGreater(len(r['freeEdges']),0)

    def test_rejects_elevated_road_and_invalid_dimensions(self):
        self.surface['tags']['bridge']='yes'
        with self.assertRaisesRegex(ValueError,'at-grade'):self.derive()
        del self.surface['tags']['bridge'];self.config['offset']=float('nan')
        with self.assertRaisesRegex(ValueError,'dimension'):self.derive()


if __name__=='__main__':unittest.main()
