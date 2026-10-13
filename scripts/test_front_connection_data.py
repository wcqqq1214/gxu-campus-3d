import copy,hashlib,json,unittest
from pathlib import Path
from shapely.geometry import Polygon
from front_connection_data import derive_front_connection
from shore_data import effective_surfaces

def revision(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()

class FrontConnectionTests(unittest.TestCase):
    def fixture(self):
        r=Path(__file__).resolve().parents[1];read=lambda n:json.loads((r/'public/data'/f'{n}.json').read_text())
        c=next(s for s in json.loads((r/'data/site-overrides.json').read_text())['sites'] if s.get('type')=='front-connection')
        infra,sur,roads=read('infrastructure'),read('surroundings'),read('campus-roads')
        target=next(s for s in effective_surfaces(read('surfaces'),[infra['surfaceOverrides'],sur['surfaceOverrides'],roads['surfaceOverrides']],set(infra['replaceSurfaceIds'])) if s['id']==c['surfaceId'])
        return c,read('buildings'),target,set(c['sourceRefs'])

    def test_actual_stairs_and_road_share_full_width_boundary(self):
        c,b,s,refs=self.fixture();old=copy.deepcopy((b,s));record,area,_=derive_front_connection(c,b,s,refs)
        self.assertEqual((b,s),old);self.assertTrue(60<area.area<110)
        for boundary in [Polygon(s['vertices']).boundary,Polygon(record['entry']['stairFlight']['footprint']).boundary]:
            self.assertGreater(area.boundary.intersection(boundary.buffer(1e-6)).length,8.39)

    def test_stale_bridge_and_blocked_routes_are_rejected(self):
        c,b,s,refs=self.fixture()
        for k,v in [('surfaceRevision','bad'),('footprintRevision','bad'),('entranceId','missing'),('meshStep',True),('sourceRefs',['missing']),('roadSearchDistance',[1,3])]:
            with self.subTest(k=k),self.assertRaises(ValueError):derive_front_connection({**c,k:v},b,s,refs)
        bad=copy.deepcopy(s);bad['tags']['bridge']='yes'
        with self.assertRaisesRegex(ValueError,'at-grade'):derive_front_connection({**c,'surfaceRevision':revision(bad)},b,bad,refs)
        _,area,_=derive_front_connection(c,b,s,refs);point=area.representative_point()
        obstacle={'id':'block','polygons':[[list(point.buffer(.5).exterior.coords)]]}
        with self.assertRaisesRegex(ValueError,'crosses a building'):derive_front_connection(c,b+[obstacle],s,refs)

    def test_rotation_preserves_forward_route(self):
        c,b,s,refs=self.fixture();b=[next(x for x in b if x['id']==c['buildingId'])];area=derive_front_connection(c,b,s,refs)[1]
        rot=lambda p:[-p[1],p[0]];x=b[0];x['polygons']=[[[rot(p) for p in ring] for ring in poly] for poly in x['polygons']];x['center']=rot(x['center'])
        for e in x['form']['entrances']:
            e['center']=rot(e['center']);e['bearing']=(e['bearing']-90)%360
            for kind in ['stairFlight','attachedPortico']:
                if kind in e:e[kind]['footprint']=[rot(p) for p in e[kind]['footprint']]
        s['vertices']=[rot(p) for p in s['vertices']];c['surfaceRevision']=revision(s)
        c['footprintRevision']=hashlib.sha256(json.dumps(x['polygons'],separators=(',',':')).encode()).hexdigest()
        self.assertAlmostEqual(derive_front_connection(c,b,s,refs)[1].area,area.area,places=6)

    def test_taper_keeps_full_stair_toe_and_uses_only_selected_road_span(self):
        c,b,s,refs=self.fixture()
        full,area,_=derive_front_connection(c,b,s,refs)
        narrowed,path,_=derive_front_connection({**c,'roadSpan':[-3,2]},b,s,refs)
        self.assertLess(path.area,area.area)
        self.assertEqual(narrowed['localPolygon'][:2],full['localPolygon'][:2])
        self.assertEqual(narrowed['columns'][0][0],-3)
        self.assertEqual(narrowed['columns'][-1][0],2)
        self.assertAlmostEqual(path.intersection(Polygon(s['vertices'])).area,0,places=7)
        stairs=Polygon(narrowed['entry']['stairFlight']['footprint'])
        self.assertGreater(path.boundary.intersection(stairs.boundary.buffer(1e-6)).length,8.39)

    def test_invalid_road_spans_fail_instead_of_widening_or_offsetting_route(self):
        c,b,s,refs=self.fixture()
        for span in [None,[],[-3],[-3,2,4],[-100,2],[-2,100],[1,3],[-3,-1],[-.5,.5],[-3,True],[-3,float('nan')],[-float('inf'),2]]:
            with self.subTest(span=span),self.assertRaisesRegex(ValueError,'road span'):
                derive_front_connection({**c,'roadSpan':span},b,s,refs)
