"""Resolved recessed stairs meet a mapped road using their actual outer face."""
import copy,hashlib,json,unittest
from pathlib import Path
from shapely.geometry import Polygon,LineString
from front_connection_data import derive_front_connection
from shore_data import effective_surfaces
from building_overrides import footprint_revision

def revision(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
class RecessedConnectionTests(unittest.TestCase):
    def fixture(self):
        root=Path(__file__).resolve().parents[1];read=lambda name:json.loads((root/'public/data'/f'{name}.json').read_text())
        c=next(s for s in json.loads((root/'data/site-overrides.json').read_text())['sites'] if s['id']=='civil-platform-personnel-connection')
        infra,sur,roads=read('infrastructure'),read('surroundings'),read('campus-roads')
        s=next(s for s in effective_surfaces(read('surfaces'),[infra['surfaceOverrides'],sur['surfaceOverrides'],roads['surfaceOverrides']],set(infra['replaceSurfaceIds'])) if s['id']==c['surfaceId'])
        return c,read('buildings'),s,set(c['sourceRefs'])
    def test_full_stair_width_and_outer_face_are_used(self):
        c,bs,s,refs=self.fixture();old=copy.deepcopy((bs,s));site,area,_=derive_front_connection(c,bs,s,refs)
        self.assertEqual((bs,s),old);self.assertAlmostEqual(site['startY'],5.71);self.assertEqual(site['halfWidth'],6)
        self.assertEqual(site['entry']['stepWidth'],12);self.assertGreater(site['entry']['porticoWidth'],26)
        self.assertAlmostEqual(area.area,19.170873068189156,places=5)
        self.assertEqual(site['material'],'path');self.assertEqual(site['stairBaseHeight'],0)
        self.assertGreater(area.boundary.intersection(Polygon(s['vertices']).boundary.buffer(1e-6)).length,12)
    def test_missing_explicit_stairs_and_arbitrary_width_are_rejected(self):
        c,bs,s,refs=self.fixture()
        for key in ['steps','stepWidth','recess','platformHeight']:
            bad=copy.deepcopy(bs);b=next(b for b in bad if b['id']==c['buildingId']);del b['form']['entrances'][0][key]
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'explicit stairs'):derive_front_connection(c,bad,s,refs)
        with self.assertRaisesRegex(ValueError,'width must match'):derive_front_connection({**c,'pathWidth':4},bs,s,refs)
        with self.assertRaisesRegex(ValueError,'Road is missing'):derive_front_connection({**c,'roadSearchDistance':[.3,4]},bs,s,refs)
    def test_rotated_recess_and_stair_toe_remain_aligned(self):
        c,bs,s,refs=self.fixture();b=next(b for b in bs if b['id']==c['buildingId']);before=derive_front_connection(c,[b],s,refs)[1]
        rot=lambda p:[-p[1],p[0]]
        b['polygons']=[[[rot(p) for p in ring] for ring in poly] for poly in b['polygons']];b['center']=rot(b['center'])
        for e in b['form']['entrances']:
            e['center']=rot(e['center']);e['outerCenter']=rot(e['outerCenter']);e['bearing']=(e['bearing']-90)%360
        s['vertices']=[rot(p) for p in s['vertices']];c['surfaceRevision']=revision(s);c['footprintRevision']=footprint_revision(b)
        site,area,_=derive_front_connection(c,[b],s,refs)
        self.assertAlmostEqual(area.area,before.area,places=6);self.assertAlmostEqual(site['startY'],5.71)
