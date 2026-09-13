"""Sideways entrance connections must meet the selected mapped footway."""
import copy,hashlib,json,unittest
from pathlib import Path
from shapely.geometry import Polygon,LineString
from side_connection_data import derive_side_connection
from shore_data import effective_surfaces

def revision(value):return hashlib.sha256(json.dumps(value,separators=(',',':'),sort_keys=True).encode()).hexdigest()

class SideConnectionTests(unittest.TestCase):
    def fixture(self):
        root=Path(__file__).resolve().parents[1];read=lambda n:json.loads((root/'public/data'/f'{n}.json').read_text())
        config=next(s for s in json.loads((root/'data/site-overrides.json').read_text())['sites'] if s.get('type')=='side-connection')
        buildings=read('buildings');infra=read('infrastructure');sur=read('surroundings');roads=read('campus-roads')
        effective=effective_surfaces(read('surfaces'),[infra['surfaceOverrides'],sur['surfaceOverrides'],roads['surfaceOverrides']],set(infra['replaceSurfaceIds']))
        surface=next(s for s in effective if s['id']==config['surfaceId'])
        return config,buildings,surface,set(config['sourceRefs'])

    def test_actual_connection_meets_both_edges_without_changing_input(self):
        c,b,s,refs=self.fixture();old=copy.deepcopy((b,s));r,area,_=derive_side_connection(c,b,s,refs)
        self.assertEqual((b,s),old);self.assertAlmostEqual(area.area,103.737,places=2)
        self.assertTrue(area.is_valid)
        self.assertGreater(area.boundary.intersection(Polygon(s['vertices']).boundary.buffer(1e-6)).length,3.59)
        p=r['entry']['attachedPortico'];self.assertLess(area.intersection(Polygon(p['footprint'])).area,1e-7)
        self.assertGreater(area.boundary.intersection(Polygon(p['footprint']).boundary.buffer(1e-6)).length,6.39)

    def test_rotated_building_and_footway_keep_the_same_connection(self):
        c,buildings,s,refs=self.fixture();b=next(b for b in buildings if b['id']==c['buildingId'])
        original=derive_side_connection(c,[b],s,refs)[1]
        rot=lambda p:[-p[1],p[0]]
        b['polygons']=[[[rot(p) for p in ring] for ring in poly] for poly in b['polygons']];b['center']=rot(b['center'])
        for e in b['form']['entrances']:
            e['center']=rot(e['center']);e['bearing']=(e['bearing']-90)%360
            if 'attachedPortico' in e:
                for field in ['columns','footprint']:e['attachedPortico'][field]=[rot(p) for p in e['attachedPortico'][field]]
            if 'stairFlight' in e:e['stairFlight']['footprint']=[rot(p) for p in e['stairFlight']['footprint']]
        s['vertices']=[rot(p) for p in s['vertices']]
        c['surfaceRevision']=revision(s);c['footprintRevision']=hashlib.sha256(json.dumps(b['polygons'],separators=(',',':')).encode()).hexdigest()
        rotated=derive_side_connection(c,[b],s,refs)[1];self.assertAlmostEqual(rotated.area,original.area,places=6)

    def test_stale_missing_and_blocked_connection_fails(self):
        c,b,s,refs=self.fixture()
        for k,v in [('surfaceRevision','stale'),('footprintRevision','stale'),('entranceId','missing'),('sourceRefs',['unknown']),('leadDistance',.5),('pathWidth',True),('roadSearchDistance',[1,5])]:
            bad={**c,k:v}
            with self.subTest(k=k),self.assertRaises(ValueError):derive_side_connection(bad,b,s,refs)
        r,area,_=derive_side_connection(c,b,s,refs);p=area.representative_point();obstacle={'id':'obstacle','polygons':[[[[p.x-.2,p.y-.2],[p.x+.2,p.y-.2],[p.x+.2,p.y+.2],[p.x-.2,p.y+.2],[p.x-.2,p.y-.2]]]]}
        with self.assertRaisesRegex(ValueError,'crosses a building'):derive_side_connection(c,b+[obstacle],s,refs)

    def test_grade_separated_footway_cannot_be_used(self):
        c,b,s,refs=self.fixture();s['tags']['bridge']='yes';c['surfaceRevision']=revision(s)
        with self.assertRaisesRegex(ValueError,'at-grade footway'):derive_side_connection(c,b,s,refs)
