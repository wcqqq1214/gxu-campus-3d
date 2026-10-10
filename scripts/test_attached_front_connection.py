"""External portico steps connect at their true outer solid, in any direction."""
import copy
import hashlib
import json
import math
import unittest
from pathlib import Path

from shapely.geometry import Polygon
from building_overrides import footprint_revision
from front_connection_data import derive_front_connection
from shore_data import effective_surfaces


def revision(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class AttachedFrontConnectionTests(unittest.TestCase):
    def fixture(self):
        root = Path(__file__).resolve().parents[1]
        read = lambda name: json.loads((root/'public/data'/f'{name}.json').read_text())
        buildings = read('buildings')
        building = next(b for b in buildings if b['id'] == 'relation/11564703')
        infra, surround, roads = (read(n) for n in ('infrastructure', 'surroundings', 'campus-roads'))
        surface = next(s for s in effective_surfaces(read('surfaces'),
            [infra['surfaceOverrides'], surround['surfaceOverrides'], roads['surfaceOverrides']],
            set(infra['replaceSurfaceIds'])) if s['id'] == 'way/759170262')
        config = dict(id='forestry-test', type='front-connection', buildingId=building['id'],
            footprintRevision=footprint_revision(building), entranceId='south-portico',
            surfaceId=surface['id'], surfaceRevision=revision(surface), roadSearchDistance=[5, 8],
            meshStep=2, groundClearance=.12, joinOverlap=.2, roadContactDepth=1,
            roadContactSideMargin=.5, sourceRefs=['osm'], evidence={'presence': 'fixture'})
        return config, buildings, surface

    def test_actual_portico_meets_road_and_preserves_step_base(self):
        config, buildings, surface = self.fixture()
        original = copy.deepcopy((buildings, surface))
        site, area, _ = derive_front_connection(config, buildings, surface, {'osm'})
        self.assertEqual((buildings, surface), original)
        self.assertAlmostEqual(site['startY'], 4.105)
        self.assertEqual(site['halfWidth'], 4.5)
        self.assertEqual(site['stairBaseHeight'], .24)
        self.assertEqual(site['material'], 'path')
        self.assertAlmostEqual(area.area, 57.173724867, places=6)
        self.assertGreater(area.boundary.intersection(Polygon(surface['vertices']).boundary.buffer(1e-6)).length, 9)
        # The stored exclusion footprint is nominal, while actual tread boxes
        # extend a further 5 mm. Verify the connector has that exact separation.
        self.assertAlmostEqual(area.distance(Polygon(site['entry']['attachedPortico']['footprint'])), .005, places=7)

    def test_incomplete_stairs_arbitrary_width_and_missing_road_rejected(self):
        config, buildings, surface = self.fixture()
        for key in ['steps', 'tread', 'stepBaseHeight', 'depth']:
            bad = copy.deepcopy(buildings)
            b = next(b for b in bad if b['id'] == config['buildingId'])
            del b['form']['entrances'][0]['attachedPortico'][key]
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'explicit stairs'):
                derive_front_connection(config, bad, surface, {'osm'})
        with self.assertRaisesRegex(ValueError, 'width must match'):
            derive_front_connection({**config, 'pathWidth': 4}, buildings, surface, {'osm'})
        with self.assertRaisesRegex(ValueError, 'Road is missing'):
            derive_front_connection({**config, 'roadSearchDistance': [1, 3]}, buildings, surface, {'osm'})

    def test_rotation_preserves_full_width_approach(self):
        config, buildings, surface = self.fixture()
        building = next(b for b in buildings if b['id'] == config['buildingId'])
        area = derive_front_connection(config, [building], surface, {'osm'})[1]
        rotate = lambda p: [-p[1], p[0]]
        building['polygons'] = [[[rotate(p) for p in ring] for ring in poly] for poly in building['polygons']]
        building['center'] = rotate(building['center'])
        for entry in building['form']['entrances']:
            entry['center'] = rotate(entry['center'])
            entry['bearing'] = (entry['bearing']-90) % 360
            p = entry['attachedPortico']
            p['footprint'] = [rotate(v) for v in p['footprint']]
            p['columns'] = [rotate(v) for v in p['columns']]
        surface['vertices'] = [rotate(p) for p in surface['vertices']]
        config.update(footprintRevision=footprint_revision(building), surfaceRevision=revision(surface))
        rotated = derive_front_connection(config, [building], surface, {'osm'})[1]
        self.assertAlmostEqual(rotated.area, area.area, places=6)

    def test_obstacle_and_bridge_still_rejected(self):
        config, buildings, surface = self.fixture()
        area = derive_front_connection(config, buildings, surface, {'osm'})[1]
        obstacle = {'id': 'obstacle', 'polygons': [[list(area.representative_point().buffer(.3).exterior.coords)]]}
        with self.assertRaisesRegex(ValueError, 'crosses a building'):
            derive_front_connection(config, buildings+[obstacle], surface, {'osm'})
        surface['tags']['bridge'] = 'yes'
        config['surfaceRevision'] = revision(surface)
        with self.assertRaisesRegex(ValueError, 'at-grade'):
            derive_front_connection(config, buildings, surface, {'osm'})
