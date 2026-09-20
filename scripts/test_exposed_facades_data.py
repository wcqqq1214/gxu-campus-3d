"""Part-local anchors must not decorate hidden walls or change the footprint."""
import copy
import unittest

from building_overrides import footprint_revision, resolve_building


class ExposedFacadeTests(unittest.TestCase):
    def fixture(self):
        b = dict(id='way/test', name='test', category='academic', landmark=None,
                 tags={'building': 'university'}, polygons=[[[[0,0],[30,0],[30,20],[0,20],[0,0]]]])
        parts = [dict(id='high', polygons=[[[[0,0],[15,0],[15,20],[0,20],[0,0]]]], height=16.5, levels=5),
                 dict(id='low', polygons=[[[[15,0],[30,0],[30,20],[15,20],[15,0]]]], height=6.6, levels=2)]
        rules = [dict(part='high', adjacentPart='low', polygon=0, ring=0, edge=1,
                      rule=dict(balconies=False, openCorridor=dict(depth=1, firstLevel=4, lastLevel=4,
                                                                 railHeight=.9, endInset=.4)))]
        record = dict(parts=parts, exposedFacadeRules=rules)
        return b, record

    def resolve(self, b, values):
        r = dict(values, footprintRevision=footprint_revision(b), evidence={
            k: dict(status='estimated', sourceRefs=[], note='fixture') for k in values})
        return resolve_building(b, r)

    def test_valid_internal_edge_and_idempotence(self):
        b, r = self.fixture(); resolved = self.resolve(b, r)
        f = resolved['form']['facades'][-1]
        self.assertEqual(f['normal'], [1, 0])
        self.assertAlmostEqual(f['minimumHeight'], 7.4)
        self.assertEqual(f['start'], [15, 0]); self.assertEqual(f['end'], [15, 20])
        self.assertIsNone(f['edge']); self.assertEqual(f['partAnchor']['edge'], 1)
        self.assertEqual(resolved['polygons'], b['polygons'])
        self.assertEqual(resolved, self.resolve(resolved, r))
        self.assertNotIn('facades', resolve_building(resolved)['form'])

    def test_reject_missing_parts_external_anchor_and_duplicates(self):
        b, r = self.fixture()
        for key, value in [('part', 'absent'), ('adjacentPart', 'high'), ('edge', 0),
                           ('edge', True), ('edge', 8), ('ring', 1), ('extra', 0)]:
            bad = copy.deepcopy(r); bad['exposedFacadeRules'][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.resolve(b, bad)
        bad = copy.deepcopy(r); bad['exposedFacadeRules'] *= 2
        with self.assertRaisesRegex(ValueError, 'Duplicate'): self.resolve(b, bad)
        bad = copy.deepcopy(r); del bad['parts']
        with self.assertRaises(ValueError): self.resolve(b, bad)

    def test_reject_hidden_details_and_recess_outside_support(self):
        b, r = self.fixture()
        for update in [dict(firstLevel=2), dict(depth=16), dict(endInset=11)]:
            bad = copy.deepcopy(r); bad['exposedFacadeRules'][0]['rule']['openCorridor'].update(update)
            with self.subTest(update=update), self.assertRaises(ValueError): self.resolve(b, bad)
        for extra in [dict(windowBands=dict(**{'from':.05,'to':.95}, firstLevel=1, lastLevel=1,
                          heightRatio=.5, depth=.4, thickness=.2, windows=[{'from':.1,'to':.9,'panes':3}])),
                      dict(panels=[dict(id='hidden', type='glazing', **{'from':.1,'to':.9}, bottom=4, top=6,
                                        columns=2, rows=2, frameWidth=.06, depth=.1)]),
                      dict(balconies=True), dict(spacing=4)]:
            bad = copy.deepcopy(r); bad['exposedFacadeRules'][0]['rule'].update(extra)
            with self.subTest(extra=extra), self.assertRaises(ValueError): self.resolve(b, bad)
        bad = copy.deepcopy(r)
        bad['facadeRules'] = [dict(polygon=0, ring=0, edge=0, part='high', balconies=False,
            openCorridor=dict(depth=1, firstLevel=4, lastLevel=4, railHeight=.9, endInset=.4))]
        with self.assertRaisesRegex(ValueError, 'overlaps another facade recess'):
            self.resolve(b, bad)

    def test_reject_partial_shared_edge(self):
        b, r = self.fixture()
        # Equal coverage, but the selected edge borders two independently
        # identified low parts; a single adjacentPart may not claim both.
        r['parts'][1]['polygons'] = [[[[15,0],[30,0],[30,10],[15,10],[15,0]]]]
        r['parts'].append(dict(id='other', polygons=[[[[15,10],[30,10],[30,20],[15,20],[15,10]]]], height=6.6, levels=2))
        with self.assertRaisesRegex(ValueError, 'complete internal'): self.resolve(b, r)


if __name__ == '__main__': unittest.main()
