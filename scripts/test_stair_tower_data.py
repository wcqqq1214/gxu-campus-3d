import copy,json,unittest
from pathlib import Path
from shapely.geometry import Polygon
from stair_tower_data import resolve_stair_tower_context,check_prepared_stair_towers
from building_overrides import resolve_building,load_catalogue,source_catalogue

ROOT=Path(__file__).resolve().parents[1]
class StairTowerTests(unittest.TestCase):
    def fixture(self):
        bs=json.loads((ROOT/'public/data/buildings.json').read_text());b=next(b for b in bs if b['id']=='way/880089960');host=next(b for b in bs if b['id']=='way/759165562')
        return bs,b,host
    def test_current_shape_connects_three_levels_without_changing_footprints(self):
        bs,b,h=self.fixture();old=[x['polygons'] for x in bs];resolve_stair_tower_context(bs);check_prepared_stair_towers(bs)
        self.assertEqual([x['polygons'] for x in bs],old);s=b['form']['stairTower']
        self.assertEqual(len(h['form']['stairAccessDoors']),3);self.assertAlmostEqual(s['floorHeight'],3.3)
        bridge=Polygon(s['bridgeFootprint']);wall=Polygon(h['polygons'][0][0]).boundary
        self.assertGreater(bridge.boundary.intersection(wall.buffer(1e-6)).length,2.39)
        self.assertEqual(s['hostCenter'],h['center'])
    def test_stale_host_shape_height_or_derived_geometry_is_rejected(self):
        for change in ['height','footprint','door','geometry']:
            bs,b,h=self.fixture()
            if change=='height':h['height']+=1
            if change=='footprint':h['polygons'][0][0][0][0]+=.1
            if change=='door':h['form']['stairAccessDoors'][0]['floor']+=.1
            if change=='geometry':b['form']['stairTower']['hostDistance']+=1
            with self.subTest(change=change),self.assertRaises(ValueError):check_prepared_stair_towers(bs)
    def test_obstructed_support_oversize_flights_and_missing_headroom_fail(self):
        for change in ['column','width','roof','host','riser']:
            bs,b,h=self.fixture();c=b['form']['stairTower']['config']
            if change=='column':c['columns'][0]['center']=[1.4,0]
            if change=='width':c['flightWidth']=20
            if change=='roof':b['height']=10.5
            if change=='host':c['host']['footprintRevision']='stale'
            if change=='riser':c['risersPerFlight']=True
            with self.subTest(change=change),self.assertRaises(ValueError):resolve_stair_tower_context(bs)
    def test_bridge_does_not_cross_other_building(self):
        bs,b,h=self.fixture();p=Polygon(b['form']['stairTower']['bridgeFootprint']).representative_point()
        obstacle=dict(id='obstacle',polygons=[[list(p.buffer(.4).exterior.coords)]])
        with self.assertRaisesRegex(ValueError,'crosses a mapped building'):resolve_stair_tower_context(bs+[obstacle])
    def test_raw_stair_configuration_requires_matching_archetype(self):
        bs,b,h=self.fixture();r=copy.deepcopy(load_catalogue()[b['id']]);r['archetype']='generic'
        with self.assertRaisesRegex(ValueError,'conflicts'):resolve_building(b,r,{s['id'] for s in source_catalogue()})
