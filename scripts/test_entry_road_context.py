import unittest
from audit_entry_road_context import conflicts_for_entry

class EntryRoadContextTests(unittest.TestCase):
    def setUp(self):
        self.e={'id':'entry','stairFlight':{'footprint':[[0,0],[4,0],[4,4],[0,4],[0,0]]}}
        self.road={'id':'road','kind':'roads','tags':{'highway':'service'},'vertices':[[2,-1,0],[3,-1,0],[3,5,0],[2,5,0]],'triangles':[0,1,2,0,2,3]}
    def test_vehicle_road_overlap_has_measured_area(self):
        r=conflicts_for_entry('building',self.e,[self.road]);self.assertEqual(len(r),1);self.assertAlmostEqual(r[0]['overlapAreaSquareMeters'],4)
    def test_boundary_contact_is_not_area_overlap(self):
        r={**self.road,'vertices':[[4,0,0],[5,0,0],[5,4,0],[4,4,0]]};self.assertEqual(conflicts_for_entry('b',self.e,[r]),[])
    def test_pedestrian_path_is_outside_vehicle_screen(self):
        self.assertEqual(conflicts_for_entry('b',self.e,[{**self.road,'tags':{'highway':'footway'}}]),[])
    def test_level_separation_still_requires_review(self):
        tags={'highway':'service','tunnel':'yes','layer':'-1'};r=conflicts_for_entry('b',self.e,[{**self.road,'tags':tags}]);self.assertEqual(r[0]['roadTags'],tags)
    def test_invalid_or_missing_footprint(self):
        self.assertEqual(conflicts_for_entry('b',{'id':'unknown'},[self.road]),[])
        e={'id':'invalid','stairFlight':{'footprint':[[0,0],[4,4],[0,4],[4,0],[0,0]]}}
        with self.assertRaises(ValueError):conflicts_for_entry('b',e,[self.road])

if __name__=='__main__':unittest.main()
