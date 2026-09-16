import copy
import json
import unittest
from pathlib import Path
from shapely.geometry import Point, Polygon
from courtyard_data import derive_courtyard, apply_courtyards
from building_overrides import source_catalogue
from vegetation_exclusions import ground_masks, filter_ground


class CourtyardTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        self.buildings = json.loads((root/'public/data/buildings.json').read_text())
        self.config = next(s for s in json.loads((root/'data/site-overrides.json').read_text())['sites'] if s['id']=='arts-east-courtyard')
        self.sources = {s['id'] for s in source_catalogue(root)}

    def derive(self, config=None, buildings=None):
        return derive_courtyard(config or self.config, buildings or self.buildings, self.sources)

    def test_current_court_preserves_buildings_and_open_tree_pits(self):
        site, paving, _ = self.derive()
        self.assertEqual(len(paving.interiors), 2)
        self.assertEqual(site, self.derive()[0])
        for b in self.buildings:
            for p in b['polygons']:
                self.assertLess(paving.intersection(Polygon(p[0], p[1:])).area, 1e-7)
        self.assertTrue(paving.covers(Polygon(site['openAreaPolygon'])))
        for t in site['treeCandidates']:
            self.assertFalse(paving.covers(Point(t[:2])))

    def test_stale_neighbours_and_intruding_crowns_fail(self):
        for field, value in [('footprintRevision','bad'), ('contextRevisions',{}),
                             ('boundaryVertices',[0,1,2,3]), ('surfaceOffset',float('nan')),
                             ('sourceRefs',['missing'])]:
            config = copy.deepcopy(self.config); config[field] = value
            with self.assertRaises(ValueError, msg=field): self.derive(config)
        config = copy.deepcopy(self.config); config['trees'][0]['local']=[10,10]
        with self.assertRaisesRegex(ValueError,'crown'): self.derive(config)
        config = copy.deepcopy(self.config); config['trees'][1]['local']=config['trees'][0]['local']
        with self.assertRaises(ValueError): self.derive(config)

    def test_connection_closes_only_the_gap_and_joins_both_edges(self):
        site, combined, _ = self.derive()
        c = site['stairConnection']; patch = Polygon(c['polygon'])
        court = Polygon(site['pavingPolygon'], site['pavingHoles'])
        stair = next(b for b in self.buildings if b['id'] == c['buildingId'])
        target = Polygon(stair['polygons'][0][0])
        self.assertAlmostEqual(court.distance(target), c['gapMeters'])
        self.assertGreater(patch.boundary.intersection(court.boundary.buffer(1e-7)).length, 2.399)
        self.assertGreater(patch.boundary.intersection(target.boundary.buffer(1e-7)).length, 2.3)
        self.assertLess(patch.intersection(court).area, 1e-7)
        self.assertLess(patch.intersection(target).area, 1e-7)
        self.assertAlmostEqual(combined.area, court.area+patch.area)
        self.assertGreater(patch.area, 1.5)
        self.assertLess(patch.area, 3)
        without = copy.deepcopy(self.config); without.pop('stairConnection')
        self.assertEqual(self.derive(without)[0]['pavingMesh'], site['pavingMesh'])

    def test_invalid_connection_or_an_obstacle_cannot_create_paving(self):
        for key, value in [('width', float('nan')), ('width', 10), ('buildingId', 'missing'),
                           ('footprintRevision', 'stale'), ('evidence', '')]:
            config = copy.deepcopy(self.config); config['stairConnection'][key] = value
            with self.assertRaises(ValueError, msg=key): self.derive(config)
        site, _, _ = self.derive(); patch = Polygon(site['stairConnection']['polygon'])
        obstacle = patch.representative_point().buffer(.01)
        buildings = copy.deepcopy(self.buildings)
        buildings.append({'id':'test-obstacle', 'polygons':[[list(obstacle.exterior.coords)]]})
        with self.assertRaisesRegex(ValueError, 'crosses a mapped building'):
            self.derive(buildings=buildings)

    def test_replacement_is_idempotent_and_preserves_outside_tree_attributes(self):
        site, _, _ = self.derive()
        original = [[381.4,-122.5,10,0,2.990891], [0,0,12,1,8.4],
                    [*site['treeCandidates'][0],3.1]]
        before = copy.deepcopy(original)
        trees, records = apply_courtyards(original,[site])
        self.assertEqual(trees,[original[1],original[2],site['treeCandidates'][1]])
        self.assertEqual(records[0]['replacedPriorRows'],2)
        self.assertEqual(apply_courtyards(trees,[site])[0],trees)
        self.assertEqual(original,before)

    def test_final_ground_filter_retains_pit_tree_but_excludes_activity_centre(self):
        site, _, _ = self.derive()
        data = {'surfaces':[], 'infrastructure':{'surfaceOverrides':{},'replaceSurfaceIds':[]},
                'surroundings':{'surfaceOverrides':{},'layers':[]},
                'campus-roads':{'surfaceOverrides':{},'layers':[]},
                'sites':{'surfaceOverrides':{},'sites':[site]}, 'buildings':[], 'sports':[],
                'pavings':{'pavings':[]}, 'shores':{'shores':[]}}
        masks,_=ground_masks(data)
        centre=Polygon(site['openAreaPolygon']).centroid
        connection = Polygon(site['stairConnection']['polygon']).representative_point()
        trees=[*site['treeCandidates'],[centre.x,centre.y,9,0], [connection.x,connection.y,9,0]]
        kept,removed=filter_ground(trees,masks)
        self.assertEqual(kept,site['treeCandidates'])
        self.assertEqual(len(removed),2)


if __name__=='__main__': unittest.main()
