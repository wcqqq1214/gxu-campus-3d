"""Resolved recessed stairs meet a mapped road using their actual outer face."""
import copy,hashlib,json,math,unittest
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
        self.assertEqual((bs,s),old);self.assertAlmostEqual(site['startY']-site['entry']['recess'],2.11);self.assertEqual(site['halfWidth'],6)
        self.assertEqual(site['entry']['stepWidth'],12);self.assertGreater(site['entry']['porticoWidth'],26)
        self.assertAlmostEqual(area.area,19.170873068189156,places=5)
        self.assertEqual(site['material'],'path');self.assertEqual(site['stairBaseHeight'],0)
        self.assertGreater(area.boundary.intersection(Polygon(s['vertices']).boundary.buffer(1e-6)).length,12)
    def test_missing_explicit_stairs_and_arbitrary_width_are_rejected(self):
        c,bs,s,refs=self.fixture()
        for key in ['steps','recess','platformHeight']:
            bad=copy.deepcopy(bs);b=next(b for b in bad if b['id']==c['buildingId']);del b['form']['entrances'][0][key]
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'explicit stairs'):derive_front_connection(c,bad,s,refs)
        bad=copy.deepcopy(bs);entry=next(b for b in bad if b['id']==c['buildingId'])['form']['entrances'][0]
        entry.pop('stepWidth');entry.pop('porticoWidth')
        with self.assertRaisesRegex(ValueError,'explicit stairs'):derive_front_connection(c,bad,s,refs)
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
        self.assertAlmostEqual(area.area,before.area,places=6);self.assertAlmostEqual(site['startY']-site['entry']['recess'],2.11)
    def test_deeper_door_preserves_world_stair_toe_and_connection(self):
        c,bs,s,refs=self.fixture();before=derive_front_connection(c,bs,s,refs)[1]
        b=next(b for b in bs if b['id']==c['buildingId']);e=b['form']['entrances'][0]
        bearing=math.radians(e['bearing']);n=[math.sin(bearing),math.cos(bearing)]
        e['recess']+=2.4;e['center']=[e['center'][k]-2.4*n[k] for k in range(2)]
        site,after,_=derive_front_connection(c,bs,s,refs)
        self.assertLess(before.symmetric_difference(after).area,1e-7)
        cs,sn=math.cos(site['angle']),math.sin(site['angle'])
        toe=[site['origin'][0]-site['startY']*sn,site['origin'][1]+site['startY']*cs]
        for k in range(2):self.assertAlmostEqual(toe[k],e['outerCenter'][k]+2.11*n[k],places=7)

    def test_default_recessed_width_and_two_step_base_are_preserved(self):
        b=dict(id='way/test',center=[0,6],polygons=[[[[-7,0],[7,0],[7,12],[-7,12],[-7,0]]]],
               form={'entrances':[dict(id='main',center=[0,4],outerCenter=[0,0],bearing=180,
               porticoId='front',recess=4,steps=2,porticoWidth=14,platformHeight=.55,stepBaseHeight=.25)]})
        surface=dict(id='way/road',kind='roads',tags={'highway':'service'},vertices=[[-20,-26],[20,-26],[20,-23],[-20,-23]],triangles=[0,1,2,0,2,3])
        c=dict(id='test',type='front-connection',buildingId=b['id'],footprintRevision=footprint_revision(b),entranceId='main',surfaceId=surface['id'],surfaceRevision=revision(surface),roadSearchDistance=[15,30],meshStep=1,groundClearance=.12,joinOverlap=.2,roadContactDepth=1,roadContactSideMargin=.5,sourceRefs=['osm'],evidence={'presence':'fixture'})
        original=copy.deepcopy(b);site,area,_=derive_front_connection(c,[b],surface,{'osm'})
        self.assertEqual(b,original);self.assertEqual(site['halfWidth'],7)
        self.assertAlmostEqual(site['startY'],4.61);self.assertEqual(site['stairBaseHeight'],.25)
        self.assertAlmostEqual(area.area,313.46)
        with self.assertRaisesRegex(ValueError,'width must match'):
            derive_front_connection({**c,'pathWidth':4},[b],surface,{'osm'})
