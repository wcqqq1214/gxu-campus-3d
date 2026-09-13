"""Entrance-to-road constraints, sources, and crown-aware local exclusions."""
import copy,json,unittest
from pathlib import Path
from shapely.geometry import Polygon,box
from site_data import derive_site,road_columns
from architecture_data import architectural_envelope


class SiteDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).resolve().parents[1]
        cls.config=json.loads((root/'data/site-overrides.json').read_text())['sites'][0]
        cls.buildings=json.loads((root/'public/data/buildings.json').read_text())
        b=next(b for b in cls.buildings if b['landmark']=='library')
        b['architecture']=architectural_envelope(b)
        cls.roads=json.loads((root/'public/data/campus-roads.json').read_text())
        cls.sources={s['id'] for s in json.loads((root/'public/data/sources.json').read_text())['sources']}

    def test_library_connects_mapped_road_without_replacing_the_building(self):
        original=copy.deepcopy(self.buildings)
        site,area,grading=derive_site(self.config,self.buildings,self.roads,self.sources)
        self.assertEqual(self.buildings,original)
        self.assertTrue(area.is_valid)
        self.assertTrue(grading.covers(area))
        self.assertAlmostEqual(site['startY'],39.15)
        self.assertAlmostEqual(site['columns'][-1][0]-site['columns'][0][0],25.2)
        self.assertTrue(all(28<y-site['startY']<28.2 for _,y in site['columns']))
        self.assertTrue(all(1e-6<b[0]-a[0]<=1.001 for a,b in zip(site['columns'],site['columns'][1:])))
        for b in self.buildings:
            for p in b['polygons']:self.assertLess(area.intersection(Polygon(p[0],p[1:])).area,1e-7)

    def test_road_boundary_bends_and_missing_connections(self):
        road=Polygon([(0,20),(4,20),(4,23),(10,25),(10,35),(0,35)])
        columns=road_columns(road,1,9,0,[15,30],1)
        self.assertAlmostEqual(columns[0][1],20)
        self.assertAlmostEqual(columns[-1][1],24+2/3)
        self.assertIn(4,[x for x,_ in columns])
        with self.assertRaisesRegex(ValueError,'Road is missing'):
            road_columns(road,1,11,0,[15,30],1)

    def test_stale_sources_and_road_references_fail(self):
        for field,value,message in [('footprintRevision','stale','stale'),('sourceRefs',['unknown'],'source'),('roadId','missing','road ID')]:
            cfg=copy.deepcopy(self.config);cfg[field]=value
            with self.assertRaisesRegex(ValueError,message):derive_site(cfg,self.buildings,self.roads,self.sources)


if __name__=='__main__':unittest.main()
