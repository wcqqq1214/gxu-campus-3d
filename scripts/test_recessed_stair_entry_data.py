import copy,json,unittest
from shapely.geometry import Point,LineString
from building_overrides import ROOT,load_catalogue,resolve_building,source_catalogue

class RecessedStairEntryTests(unittest.TestCase):
    def setUp(self):
        self.b=next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']=='relation/11564999')
        self.raw=copy.deepcopy(load_catalogue()[self.b['id']]);self.sources={s['id'] for s in source_catalogue()}
    def resolve(self):return resolve_building(self.b,self.raw,self.sources)
    def test_rear_door_flights_canopy_and_original_rings(self):
        b=self.resolve();e=b['form']['entrances'][0];p=e['recessedStairEntry']
        self.assertEqual(b['polygons'],self.b['polygons']);self.assertEqual(len(b['form']['entrances']),1)
        self.assertTrue(e['primary']);self.assertGreater(p['recess'],16);self.assertLess(p['recess'],17)
        self.assertGreater(p['innerStart'],7);self.assertEqual(len(p['columns']),4)
        self.assertLess(p['toe'],0);self.assertGreater(p['doorLandingHeight'],p['platformHeight'])
        self.assertLess(LineString(self.b['polygons'][0][3][3:5]).distance(Point(p['rearCenter'])),1e-7)
    def test_projecting_approach_clears_effective_road_and_cuts_old_flat_floor(self):
        from shapely.geometry import Polygon
        from shapely.ops import unary_union
        from audit_entry_road_context import conflicts_for_entry,effective_road_surfaces
        b=self.resolve();e=b['form']['entrances'][0];p=e['recessedStairEntry']
        surfaces=json.loads((ROOT/'public/data/surfaces.json').read_text())
        self.assertEqual({v['roadId'] for v in conflicts_for_entry(b['id'],e,surfaces)},{'way/842784663'})
        self.assertEqual(conflicts_for_entry(b['id'],e,effective_road_surfaces()),[])
        floor=unary_union([Polygon(r[0],r[1:]) for r in p['frameFloor']['polygons']])
        self.assertLess(floor.intersection(Polygon(p['footprint'])).area,1e-7)
        self.assertGreater(p['innerStart']-p['outerEnd'],1.2)
    def test_rejects_ungrounded_or_invalid_approach_profile(self):
        for value in [[],[.1]*12,[True]*13,[float('nan')]*13,[10]*13,[-.1]*13]:
            r=copy.deepcopy(self.raw);r['entrances'][0]['recessedStairEntry']['apronFrontHeights']=value
            with self.assertRaises(ValueError):resolve_building(self.b,r,self.sources)
    def test_rejects_bad_risers_and_unbuildable_rises(self):
        for key,values in [('outerRisers',[True,0,33,2]),('innerRisers',[1,2,99]),('tread',[0,.6,float('nan')])]:
            for value in values:
                with self.subTest(key=key,value=value):
                    r=copy.deepcopy(self.raw);r['entrances'][0]['recessedStairEntry'][key]=value
                    with self.assertRaises(ValueError):resolve_building(self.b,r,self.sources)
    def test_rejects_invalid_rear_wall_and_missing_frame(self):
        for key,value in [('rearRing',0),('rearEdge',1),('framePart','missing'),('rearLandingDepth',20),('platformWidth',40)]:
            with self.subTest(key=key):
                r=copy.deepcopy(self.raw);r['entrances'][0]['recessedStairEntry'][key]=value
                with self.assertRaises(ValueError):resolve_building(self.b,r,self.sources)
    def test_rejects_canopy_blocking_route_or_overhead_lattice(self):
        for key,value in [('columnInset',2),('topHeight',22),('topHeight',8),('depth',10),('width',30),('thickness',-1)]:
            with self.subTest(key=key,value=value):
                r=copy.deepcopy(self.raw);r['entrances'][0]['recessedStairEntry']['canopy'][key]=value
                with self.assertRaises(ValueError):resolve_building(self.b,r,self.sources)
    def test_rejects_combined_entrance_generators(self):
        for key,value in [('recess',5),('steps',3),('landingHeight',.5)]:
            with self.subTest(key=key):
                r=copy.deepcopy(self.raw);r['entrances'][0][key]=value
                with self.assertRaises(ValueError):resolve_building(self.b,r,self.sources)

    def test_hall_is_cut_in_crossbar_and_preserves_upper_footprint(self):
        from shapely.geometry import Polygon
        from shapely.ops import unary_union
        b=self.resolve();p=b['form']['entrances'][0]['recessedStairEntry'];h=p['hall']
        part=next(v for v in b['form']['parts'] if v['id']==h['part'])
        shape=lambda ps:unary_union([Polygon(v[0],v[1:]) for v in ps])
        removed=shape(part['polygons']).difference(shape(h['wallGeometry']['polygons']))
        self.assertAlmostEqual(removed.area,h['width']*h['depth'],delta=.05)
        self.assertLess(h['depth'],7)
        for key,value in [('part','east-open-frame'),('depth',9),('width',30),('clearHeight',2),('galleryWidth',4)]:
            r=copy.deepcopy(self.raw);r['entrances'][0]['recessedStairEntry']['hall'][key]=value
            with self.assertRaises(ValueError):resolve_building(self.b,r,self.sources)

    def test_landscape_rejects_blocked_landings_and_bad_ground_mesh(self):
        for field,key,value in [('lowerFlight','toe',-6),('lowerFlight','risers',2),('court','back',-4),('court','floorHeight',5)]:
            r=copy.deepcopy(self.raw);r['entrances'][0]['recessedStairEntry']['landscape'][field][key]=value
            with self.subTest(field=field,key=key),self.assertRaises(ValueError):resolve_building(self.b,r,self.sources)
        r=copy.deepcopy(self.raw);r['entrances'][0]['recessedStairEntry']['landscape']['groundPatches'][0]['triangles']=[]
        with self.assertRaisesRegex(ValueError,'topology'):resolve_building(self.b,r,self.sources)

    def test_court_turning_landing_cannot_be_shorter_than_stair_width(self):
        r=copy.deepcopy(self.raw)
        r['entrances'][0]['recessedStairEntry']['landscape']['court']['risers']=18
        with self.assertRaisesRegex(ValueError,'at least as deep as its stair width'):
            resolve_building(self.b,r,self.sources)

if __name__=='__main__':unittest.main()
