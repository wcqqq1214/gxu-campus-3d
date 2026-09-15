import copy,json,unittest
from pathlib import Path
from mapped_canopy_data import resolve_mapped_canopy_context,check_prepared_mapped_canopies
from canopy_connection_data import derive_canopy_connection
from building_overrides import load_catalogue,resolve_building,source_catalogue

ROOT=Path(__file__).resolve().parents[1]
class MappedCanopyTests(unittest.TestCase):
    def fixture(self):
        read=lambda n:json.loads((ROOT/'public/data'/f'{n}.json').read_text())
        bs=read('buildings');b=next(b for b in bs if b['id']=='way/759165563')
        e=b['form']['entrances'][0];roof=next(b for b in bs if b['id']==e['mappedCanopy']['buildingId'])
        c=next(s for s in json.loads((ROOT/'data/site-overrides.json').read_text())['sites'] if s.get('type')=='canopy-connection')
        return bs,b,e,roof,c,read('campus-roads')

    def test_actual_entry_has_three_clear_routes_and_shared_platform(self):
        bs,b,e,roof,c,roads=self.fixture();resolve_mapped_canopy_context(bs,check_only=True);check_prepared_mapped_canopies(bs)
        self.assertEqual(len(e['shelter']['passages']),3)
        self.assertEqual(e['shelter']['floorHeight'],roof['form']['parts'][0]['openBelow']['floorHeight'])
        self.assertTrue(250<e['bearing']<270)
        before=copy.deepcopy(bs);record,area,_=derive_canopy_connection(c,bs,roads,set(c['sourceRefs']))
        self.assertEqual(bs,before);self.assertTrue(80<area.area<95)
        from shapely.geometry import Polygon
        boundary=Polygon(roof['polygons'][0][0]).boundary
        self.assertGreater(area.boundary.intersection(boundary.buffer(1e-6)).length,11.7)

    def test_stale_canopy_and_moved_entry_fail(self):
        for change in ['revision','part','entry','derived']:
            bs,b,e,roof,c,roads=self.fixture()
            if change=='revision':e['mappedCanopy']['footprintRevision']='bad'
            if change=='part':roof['form']['parts'][0]['openBelow']['floorHeight']+=.1
            if change=='entry':e['center'][0]+=1
            if change=='derived':e['shelter']['floorHeight']+=.1
            with self.subTest(change=change),self.assertRaises(ValueError):check_prepared_mapped_canopies(bs)
            with self.subTest(change=change),self.assertRaises(ValueError):resolve_mapped_canopy_context(bs,check_only=True)

    def test_obstructed_or_too_tall_entry_fails(self):
        for change in ['column','height','position']:
            bs,b,e,roof,c,roads=self.fixture()
            if change=='height':e['mappedCanopy']['doorHeight']=3.2
            if change=='position':e['center'][0]+=20
            if change=='column':
                path=e['shelter']['passages'][1]
                roof['form']['parts'][0]['openBelow']['columns'][0]['center']=[(a+b)/2 for a,b in zip(*path)]
            with self.subTest(change=change),self.assertRaises(ValueError):resolve_mapped_canopy_context(bs)

    def test_conflicting_automatic_platform_fails(self):
        bs,b,e,roof,c,roads=self.fixture();r=copy.deepcopy(load_catalogue()[b['id']]);r['entrances'][0]['landingHeight']=.4
        with self.assertRaisesRegex(ValueError,'duplicate'):resolve_building(b,r,{s['id'] for s in source_catalogue()})

    def test_bad_road_and_crossing_footprints_fail(self):
        bs,b,e,roof,c,roads=self.fixture()
        for k,v in [('canopyEdge',0),('roadId','missing'),('footprintRevision','bad'),('roadSearchDistance',[1,2]),('meshStep',True)]:
            with self.subTest(k=k),self.assertRaises(ValueError):derive_canopy_connection({**c,k:v},bs,roads,set(c['sourceRefs']))
        _,area,_=derive_canopy_connection(c,bs,roads,set(c['sourceRefs']));obstacle={'id':'obstacle','polygons':[[list(area.representative_point().buffer(.5).exterior.coords)]]}
        with self.assertRaisesRegex(ValueError,'crosses a mapped building'):derive_canopy_connection(c,bs+[obstacle],roads,set(c['sourceRefs']))
