import copy
import json
import math
import tempfile
import unittest
from pathlib import Path
from shapely.geometry import box

from building_overrides import footprint_revision
from low_planting_data import derive_plantings
from low_planting_contract import context_value, digest


class LowPlantingTests(unittest.TestCase):
    def setUp(self):
        self.building = {'id':'way/1', 'polygons':[[[[0,0],[2,0],[2,2],[0,2],[0,0]]]],
                         'center':[1,1], 'architecture':{'origin':[10,20], 'angle':math.pi/2}}
        self.item = {'id':'test', 'type':'hedge', 'buildingId':'way/1',
                     'footprintRevision':footprint_revision(self.building),
                     'localLine':[[3,3],[13,3]], 'widthMeters':1, 'heightMeters':.7,
                     'sourceRefs':['photo'], 'evidence':{k:'Estimated with reference' for k in ('placement','dimensions','species','openSpace')}}

    def derive(self, item=None, exclusions=None, zones=None):
        return derive_plantings({'schemaVersion':1,'plantings':[item or self.item]},
                               [self.building], {'photo'}, box(-100,-100,100,100), exclusions or [], zones or [])

    def test_frame_and_dimensions(self):
        before = copy.deepcopy(self.item)
        result = self.derive()[0]
        self.assertAlmostEqual(result['line'][0][0], 7)
        self.assertAlmostEqual(result['line'][0][1], 23)
        self.assertAlmostEqual(result['line'][1][1], 33)
        self.assertAlmostEqual(result['areaMeters2'], 10)
        self.assertEqual(self.derive(), self.derive())
        self.assertEqual(self.item, before)

    def test_entire_footprint_and_open_spaces_are_reserved(self):
        # This sliver touches only the side, leaving the centreline clear.
        sliver = ('walk', box(7.4,25,8,26))
        with self.assertRaisesRegex(ValueError, 'reserved space'):
            self.derive(exclusions=[sliver])
        with self.assertRaisesRegex(ValueError, 'reserved space'):
            self.derive(zones=[sliver])
        self.assertEqual(len(self.derive(exclusions=[('walk',box(8,25,9,26))])), 1)

    def test_bad_sources_anchors_dimensions_and_duplicates(self):
        changes = [{'footprintRevision':'stale'}, {'sourceRefs':['unknown']},
                   {'heightMeters':float('nan')}, {'heightMeters':True}, {'widthMeters':0},
                   {'type':'tree'}, {'localLine':[[1,2],[1,2]]},
                   {'localLine':[[1,2],[float('inf'),2]]}, {'evidence':{}}, {'extra':1}]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.derive({**self.item, **change})
        with self.assertRaises(ValueError):
            derive_plantings({'schemaVersion':1,'plantings':[self.item,self.item]},
                            [self.building], {'photo'}, box(-100,-100,100,100), [], [])

    def test_context_catches_entrance_changes_but_ignores_export_metadata(self):
        root = Path(__file__).resolve().parents[1]
        from low_planting_contract import CONTEXT_FILES
        data = {n:json.loads((root/'public/data'/f'{n}.json').read_text()) for n in CONTEXT_FILES}
        config = json.loads((root/'data/low-planting.json').read_text())
        first = digest(context_value(root, config, data))
        data['buildings'][0]['chunk'] = 'export-only'
        self.assertEqual(first, digest(context_value(root, config, data)))
        library = next(b for b in data['buildings'] if b['landmark']=='library')
        library['architecture']['northEntry']['width'] += 1
        self.assertNotEqual(first, digest(context_value(root, config, data)))


if __name__ == '__main__': unittest.main()
