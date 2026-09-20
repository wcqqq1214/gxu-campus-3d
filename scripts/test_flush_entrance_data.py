import copy,json,unittest
from pathlib import Path
from shapely.geometry import LineString,Polygon
from building_overrides import load_catalogue,resolve_building,source_catalogue
from flush_entrance_data import validate_flush_entrance,validate_flush_canopy_footprint
from front_connection_data import derive_front_connection
from shore_data import effective_surfaces

ROOT=Path(__file__).resolve().parents[1]

class FlushEntranceTests(unittest.TestCase):
    def test_glazed_portal_canopy_rejects_bad_dimensions_and_local_roof_collision(self):
        _,r,_=self.fixture();p=copy.deepcopy(r['entrances'][0]['flushEntrance'])
        p['canopy']={'width':17,'depth':2,'thickness':.6}
        validate_flush_entrance(p,16.2,13.2)
        for key,value in [('width',16),('depth',True),('depth',float('nan')),('depth',5),('thickness',0)]:
            bad=copy.deepcopy(p);bad['canopy'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_flush_entrance(bad,16.2,13.2)
        with self.assertRaisesRegex(ValueError,'wall height'):
            validate_flush_entrance(p,16.2,p['glazingHeight']+.7)

    def test_glazed_portal_canopy_cannot_wrap_a_corner_or_overlap_neighbor_wing(self):
        b={'polygons':[[[[-10,-10],[10,-10],[10,10],[-10,10],[-10,-10]]]]}
        e={'center':[10,0],'bearing':90,'t':.5,'flushEntrance':{'canopy':{'width':14,'depth':2,'thickness':.6}}}
        validate_flush_canopy_footprint(b,e,20)
        for bearing,center in [(0,[0,10]),(180,[0,-10]),(270,[-10,0])]:
            validate_flush_canopy_footprint(b,{**e,'bearing':bearing,'center':center},20)
        with self.assertRaisesRegex(ValueError,'beyond its facade'):
            validate_flush_canopy_footprint(b,{**e,'t':.1},20)
        b['polygons'].append([[[11,-4],[13,-4],[13,4],[11,4],[11,-4]]])
        with self.assertRaisesRegex(ValueError,'overlaps another'):
            validate_flush_canopy_footprint(b,e,20)

    def test_canopy_and_upper_glazing_must_not_intersect(self):
        b,r,refs=self.fixture();r=copy.deepcopy(r)
        p=r['entrances'][0]['flushEntrance'];p['canopy']={'width':16.2,'depth':2,'thickness':.6}
        r['facadeRules'][0]['panels'][0]['bottom']=p['glazingHeight']+.3
        with self.assertRaisesRegex(ValueError,'overlap the flush'):resolve_building(b,r,refs)

    def fixture(self):
        read=lambda n:json.loads((ROOT/'public/data'/f'{n}.json').read_text())
        buildings=read('buildings');b=next(b for b in buildings if b['id']=='way/671978896')
        return b,load_catalogue()[b['id']],{s['id'] for s in source_catalogue()}

    def test_impossible_doors_glazing_and_combined_canopies_are_rejected(self):
        b,r,refs=self.fixture();p=r['entrances'][0]['flushEntrance']
        for key,value in [('bays',2),('bays',True),('glazingHeight',14),('doorWidth',8),
                          ('floorHeight',float('nan')),('splitHeight',2),('pierDepth',2),('frameWidth',True)]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                validate_flush_entrance({**p,key:value},16.2,13.2)
        bad=copy.deepcopy(r);bad['entrances'][0]['landingHeight']=.3
        with self.assertRaisesRegex(ValueError,'cannot add'):resolve_building(b,bad,refs)

    def test_portal_uses_actual_part_height_and_rejects_overlaid_panels(self):
        b,r,refs=self.fixture();bad=copy.deepcopy(r)
        bad['parts'][0]['height']=5;bad['parts'][0]['levels']=2
        bad['height']=9.9;bad['evidence']['height']=dict(status='estimated',sourceRefs=['osm'],note='test low core')
        with self.assertRaisesRegex(ValueError,'exceeds its wall'):resolve_building(b,bad,refs)
        bad=copy.deepcopy(r);bad['facadeRules'][0]['panels'][0]['bottom']=5
        with self.assertRaisesRegex(ValueError,'overlap the flush'):resolve_building(b,bad,refs)

    def test_solid_sign_wall_cannot_be_a_lattice(self):
        b,r,refs=self.fixture();bad=copy.deepcopy(r)
        panel=next(p for p in bad['facadeRules'][0]['panels'] if p['type']=='solid');panel['rows']=2
        with self.assertRaisesRegex(ValueError,'Solid panels'):resolve_building(b,bad,refs)

    def test_flush_connection_attaches_to_door_and_road_without_stairs(self):
        read=lambda n:json.loads((ROOT/'public/data'/f'{n}.json').read_text())
        c=next(c for c in json.loads((ROOT/'data/site-overrides.json').read_text())['sites'] if c['id']=='office-north-front-connection')
        i,s,r=read('infrastructure'),read('surroundings'),read('campus-roads')
        surface=next(x for x in effective_surfaces(read('surfaces'),[i['surfaceOverrides'],s['surfaceOverrides'],r['surfaceOverrides']],set(i['replaceSurfaceIds'])) if x['id']==c['surfaceId'])
        buildings=read('buildings');record,area,_=derive_front_connection(c,buildings,surface,set(c['sourceRefs']))
        self.assertNotIn('stairFlight',record['entry']);self.assertAlmostEqual(record['startY'],0)
        self.assertGreater(area.boundary.intersection(Polygon(surface['vertices']).boundary.buffer(1e-6)).length,4.39)
        building=next(b for b in buildings if b['id']==c['buildingId'])
        self.assertGreater(area.boundary.intersection(Polygon(building['polygons'][0][0]).boundary.buffer(1e-6)).length,4.39)
        for width in (True,1,6,30,float('nan')):
            with self.subTest(width=width),self.assertRaises(ValueError):derive_front_connection({**c,'pathWidth':width},buildings,surface,set(c['sourceRefs']))
