"""A shoreline must stay on land, retain its anchors and respect existing routes."""
import copy, unittest
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
from shore_data import derive_shore, revision, effective_surfaces

class ShoreDataTests(unittest.TestCase):
    def example(self,reverse=False):
        vertices=[[0,0],[0,50],[50,50],[50,0]]
        if reverse:vertices.reverse()
        water={'id':'lake','kind':'water','vertices':vertices,'insideCampus':True,'waterLevel':2}
        config={'id':'bank','waterId':'lake','shorelineRevision':revision(vertices),'edgeIndices':[1],'freeboard':.55,'capWidth':.4,'landWidth':6,'endFeather':5,'meshStep':.75,'safetyMargin':.6,'safetyFeather':.75,'sourceRefs':['photo'],'evidence':{k:'Documented or estimated' for k in ['location','form','dimensions','details']}}
        return config,water

    def test_reversed_ring_keeps_the_same_land_band(self):
        shapes=[]
        for reverse in [False,True]:
            config,water=self.example(reverse);original=copy.deepcopy(water)
            record,area,cap=derive_shore(config,[water],[],box(-20,59,70,62),{'photo'})
            self.assertEqual(water,original);self.assertLess(area.intersection(Polygon(water['vertices'])).area,1e-8)
            self.assertAlmostEqual(record['coreLength'],50);self.assertAlmostEqual(cap.area,20)
            self.assertGreater(area.area,300);shapes.append(area)
            triangles=[Polygon(p) for p in record['gradingMasks']]
            self.assertAlmostEqual(sum(t.area for t in triangles),area.area,places=6)
            self.assertLess(unary_union(triangles).symmetric_difference(area).area,1e-7)
        self.assertLess(shapes[0].symmetric_difference(shapes[1]).area,1e-7)

    def test_nearby_road_clips_only_land_and_cap_conflict_fails(self):
        config,water=self.example();road=box(20,53,30,60)
        record,area,cap=derive_shore(config,[water],[],road,{'photo'})
        self.assertLess(area.intersection(road.buffer(.6)).area,1e-8)
        self.assertTrue(record['safetyPolygons']);self.assertAlmostEqual(cap.area,20)
        with self.assertRaisesRegex(ValueError,'cap conflicts'):
            derive_shore(config,[water],[],box(20,50.5,30,60),{'photo'})

    def test_stale_or_invalid_source_parameters_are_rejected(self):
        config,water=self.example()
        for field,value in [('shorelineRevision','stale'),('sourceRefs',['unknown']),('freeboard',float('nan')),('edgeIndices',[1,3]),('capWidth',True),('endFeather',60)]:
            c=copy.deepcopy(config);c[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):derive_shore(c,[water],[],Polygon(),{'photo'})

    def test_effective_surface_precedence_and_original_slots(self):
        surfaces=[{'id':'old','kind':'roads','vertices':[[0,0]]},{'id':'kept','kind':'roads','vertices':[[1,1]]},{'id':'hidden','kind':'water','suppressed':True}];original=copy.deepcopy(surfaces)
        effective=effective_surfaces(surfaces,[{'1':{'vertices':[[2,2]]}},{'1':{'vertices':[[3,3]]}}],{'old'})
        self.assertEqual(effective,[{'id':'kept','kind':'roads','vertices':[[3,3]]}]);self.assertEqual(surfaces,original)

if __name__=='__main__':unittest.main()
