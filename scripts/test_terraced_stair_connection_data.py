"""A stair apron joins the lower toe without creating an entrance identity."""
import copy,json,hashlib,unittest,math
from pathlib import Path
from shapely.geometry import Polygon
from front_connection_data import derive_front_connection
from shore_data import effective_surfaces
from building_overrides import footprint_revision

class TerracedStairConnectionTests(unittest.TestCase):
    def fixture(self):
        root=Path(__file__).resolve().parents[1];read=lambda n:json.loads((root/'public/data'/f'{n}.json').read_text())
        c=next(c for c in json.loads((root/'data/site-overrides.json').read_text())['sites'] if c['id']=='civil-annex-stair-connection')
        i,s,r=read('infrastructure'),read('surroundings'),read('campus-roads')
        surface=next(x for x in effective_surfaces(read('surfaces'),[i['surfaceOverrides'],s['surfaceOverrides'],r['surfaceOverrides']],set(i['replaceSurfaceIds'])) if x['id']==c['surfaceId'])
        return c,read('buildings'),surface,set(c['sourceRefs'])

    def test_full_toe_boundary_without_a_new_door_and_rotation(self):
        c,bs,s,refs=self.fixture();before=copy.deepcopy((bs,s))
        record,area,_=derive_front_connection(c,bs,s,refs)
        self.assertEqual((bs,s),before);self.assertNotIn('entranceId',record)
        self.assertEqual(set(record['entry']),{'terracedStairs'})
        stairs=record['entry']['terracedStairs']
        self.assertAlmostEqual(record['startY'],stairs['front'])
        self.assertGreater(area.boundary.intersection(Polygon(stairs['footprint']).boundary.buffer(1e-6)).length,11.99)
        self.assertGreater(area.boundary.intersection(Polygon(s['vertices']).boundary.buffer(1e-6)).length,11.99)
        b=next(b for b in bs if b['id']==c['buildingId']);rot=lambda p:[-p[1],p[0]]
        b['polygons']=[[[rot(p) for p in ring] for ring in poly] for poly in b['polygons']];b['center']=rot(b['center'])
        b['form']['entrances']=[];b['form']['facades']=[]
        stairs=b['form']['terracedStairs']
        for key in ['center','tangent','normal']:stairs[key]=rot(stairs[key])
        stairs['footprint']=[rot(p) for p in stairs['footprint']]
        s['vertices']=[rot(p) for p in s['vertices']];c['footprintRevision']=footprint_revision(b)
        c['surfaceRevision']=hashlib.sha256(json.dumps(s,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        self.assertAlmostEqual(derive_front_connection(c,[b],s,refs)[1].area,area.area,places=6)

    def test_missing_anchor_width_override_and_obstructing_stairs_rejected(self):
        c,bs,s,refs=self.fixture()
        for key,value in [('entranceId','fake-door'),('pathWidth',2),('surfaceRevision','stale')]:
            with self.subTest(key=key),self.assertRaises(ValueError):derive_front_connection({**c,key:value},bs,s,refs)
        b=next(b for b in bs if b['id']==c['buildingId']);saved=b['form'].pop('terracedStairs')
        with self.assertRaisesRegex(ValueError,'requires resolved'):derive_front_connection(c,bs,s,refs)
        b['form']['terracedStairs']=saved
        record,area,_=derive_front_connection(c,bs,s,refs);obstacle=area.representative_point().buffer(.5)
        other={'id':'obstructing-stair','polygons':[],'form':{'terracedStairs':{'footprint':list(obstacle.exterior.coords)}}}
        with self.assertRaisesRegex(ValueError,'overlaps terraced'):derive_front_connection(c,bs+[other],s,refs)
