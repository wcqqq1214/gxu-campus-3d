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

    def portico_fixture(self):
        b, r = self.fixture()
        r['parts'][1]['openBelow'] = dict(clearHeight=6.2, floorHeight=.24,
            columns=[dict(center=[28,y], width=.6, depth=.6, angle=0, shape='cylinder') for y in [5,15]])
        r['exposedFacadeRules'][0].update(region='under-portico', rule=dict(
            windows=False, balconies=False, panels=[dict(id='back-glass',type='glazing',
                **{'from':.05,'to':.95}, bottom=.6, top=5.8, columns=6, rows=3,
                frameWidth=.12,depth=.1)]))
        return b,r

    def test_glazing_behind_portico_preserves_floor_slab_and_footprint(self):
        b,r=self.portico_fixture(); result=self.resolve(b,r)
        face=result['form']['facades'][-1]
        self.assertEqual(face['region'],'under-portico')
        self.assertEqual(face['normal'],[1,0])
        self.assertAlmostEqual(face['minimumHeight'],.34)
        self.assertAlmostEqual(face['maximumHeight'],6.1)
        self.assertEqual(face['rule']['panels'][0]['bottom'],.6)
        self.assertEqual(result['polygons'],b['polygons'])
        self.assertEqual(result,self.resolve(result,r))
        self.assertEqual(result['form']['parts'][1]['openBelow']['floorHeight'],.24)

    def test_upper_glazing_clearance_includes_capital_projection(self):
        b,r=self.portico_fixture();opening=r['parts'][1]['openBelow']
        opening['columns'][0]['center']=[15.5,5]
        opening['columns'][0]['capital']=dict(height=.32,projection=.08,taperHeight=.07)
        self.resolve(b,r)  # Glazing ends below the capital.
        r['exposedFacadeRules'][0]['rule']['panels'][0]['top']=6.0
        with self.assertRaisesRegex(ValueError,'support column'):self.resolve(b,r)

    def test_portico_backing_wall_can_support_profiled_roof(self):
        b,r=self.portico_fixture()
        r['parts'][0]['roof']=dict(type='profiled',rise=2,mesh={
            'vertices':[[0,0,2],[15,0,0],[15,20,0],[0,20,2]],'triangles':[0,1,2,0,2,3]})
        result=self.resolve(b,r)
        self.assertEqual(result['form']['facades'][-1]['region'],'under-portico')
        self.assertEqual(result['form']['facades'][-1]['rule']['panels'][0]['top'],5.8)

    def test_stone_surround_keeps_panel_clearances_and_rejects_overlap(self):
        b,r=self.portico_fixture()
        panels=r['exposedFacadeRules'][0]['rule']['panels']
        panels[0]['to']=.45
        stone=dict(panels[0],id='pier',type='solid',finish='stone',columns=1,rows=1,
                   **{'from':.45,'to':.55})
        panels.append(stone)
        result=self.resolve(b,r)
        self.assertEqual(result['form']['facades'][-1]['rule']['panels'][1]['finish'],'stone')
        self.assertEqual(result,self.resolve(result,r))
        stone['from']=.44
        with self.assertRaisesRegex(ValueError,'panels overlap'):self.resolve(b,r)
        stone['from']=.45;stone['top']=6.3
        with self.assertRaisesRegex(ValueError,'underside'):self.resolve(b,r)
        stone['top']=5.8
        r['parts'][1]['openBelow']['columns'][0]['center']=[15.32,10]
        with self.assertRaisesRegex(ValueError,'support column'):self.resolve(b,r)

    def test_solid_finish_is_explicit_and_type_restricted(self):
        b,r=self.portico_fixture();panel=r['exposedFacadeRules'][0]['rule']['panels'][0]
        panel.update(type='solid',columns=1,rows=1)
        self.assertNotIn('finish',self.resolve(b,r)['form']['facades'][-1]['rule']['panels'][0])
        for finish in ('white','stone'):
            panel['finish']=finish;self.resolve(b,r)
        for update in [dict(finish='dark'),dict(finish=None),dict(finish='stone',type='glazing')]:
            bad=copy.deepcopy(r);bad['exposedFacadeRules'][0]['rule']['panels'][0].update(update)
            with self.subTest(update=update),self.assertRaisesRegex(ValueError,'Solid panel finish'):
                self.resolve(b,bad)

    def test_separate_clerestory_and_lower_glass_share_one_portico_wall(self):
        b,r=self.portico_fixture()
        r['parts'][0]['roof']=dict(type='profiled',rise=2,mesh={
            'vertices':[[0,0,2],[15,0,0],[15,20,0],[0,20,2]],'triangles':[0,1,2,0,2,3]})
        upper=copy.deepcopy(r['exposedFacadeRules'][0]);upper['region']='above-portico'
        upper['rule']['panels'][0].update(bottom=7,top=8.5,rows=1)
        r['exposedFacadeRules'].append(upper)
        result=self.resolve(b,r)
        self.assertEqual(result,self.resolve(result,r))
        self.assertEqual([f['region'] for f in result['form']['facades'] if 'region' in f],
                         ['under-portico','above-portico'])
        automatic=[f for f in result['form']['facades'] if f['part']=='high' and f['polygon'] is None and not f['rule']]
        self.assertEqual(automatic[0]['minimumHeight'],16.5)
        for change in [dict(bottom=6.5),dict(top=16.45)]:
            bad=copy.deepcopy(r);bad['exposedFacadeRules'][1]['rule']['panels'][0].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):self.resolve(b,bad)
        r['exposedFacadeRules'].append(copy.deepcopy(upper))
        with self.assertRaisesRegex(ValueError,'Duplicate'):self.resolve(b,r)

    def test_nonuniform_glazing_rows_keep_clear_cells_and_reject_bad_dividers(self):
        b,r=self.portico_fixture();p=r['exposedFacadeRules'][0]['rule']['panels'][0]
        p['rowFractions']=[.375,.625]
        result=self.resolve(b,r)
        self.assertEqual(result,self.resolve(result,r))
        for value in [None,[],[.5],[.625,.375],[.5,.5],[.01,.5],[True,.7],[.3,float('nan')]]:
            p['rowFractions']=value
            with self.subTest(value=value),self.assertRaises(ValueError):self.resolve(b,r)
        p.update(type='solid',columns=1,rows=1,rowFractions=[])
        with self.assertRaisesRegex(ValueError,'Glazing row fractions'):self.resolve(b,r)

    def test_glazing_behind_mixed_roof_keeps_height_and_column_constraints(self):
        b,r=self.portico_fixture()
        opening=r['parts'][1]['openBelow']
        opening['columns']=[dict(center=[29.5,y],width=.6,depth=.6,angle=0) for y in (7,12)]
        opening['slattedRoof']=dict(edgeWidth=1,slatWidth=.3,slatCount=3,solidBays=[1,2])
        result=self.resolve(b,r)
        self.assertEqual(len(result['form']['parts'][1]['openBelow']['roofGeometry']['polygons'][0])-1,2)
        self.assertAlmostEqual(result['form']['facades'][-1]['maximumHeight'],6.1)
        automatic=[f for f in result['form']['facades'] if f['part']=='high' and f['polygon'] is None and not f['rule']]
        self.assertEqual(len(automatic),1)
        self.assertEqual(automatic[0]['minimumHeight'],6.6)
        self.assertEqual(result,self.resolve(result,r))
        bad=copy.deepcopy(r);bad['parts'][1]['openBelow']['columns'][0]['center']=[15.32,7]
        with self.assertRaisesRegex(ValueError,'support column'):self.resolve(b,bad)
        bad=copy.deepcopy(r);bad['exposedFacadeRules'][0]['rule']['panels'][0]['top']=6.3
        with self.assertRaisesRegex(ValueError,'underside'):self.resolve(b,bad)
        del opening['slattedRoof']['solidBays']
        with self.assertRaisesRegex(ValueError,'open flat slab'):self.resolve(b,r)

    def test_portico_glazing_rejects_floor_slab_and_column_collisions(self):
        b,r=self.portico_fixture()
        for key,value in [('bottom',.2),('top',6.3)]:
            bad=copy.deepcopy(r);bad['exposedFacadeRules'][0]['rule']['panels'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.resolve(b,bad)
        bad=copy.deepcopy(r);bad['parts'][1]['openBelow']['columns'][0]['center']=[15.32,5]
        with self.assertRaisesRegex(ValueError,'support column'):self.resolve(b,bad)

    def test_portico_glazing_cannot_bypass_solid_wall_or_exterior_panel_rules(self):
        b,r=self.portico_fixture()
        bad=copy.deepcopy(r);del bad['parts'][1]['openBelow']
        with self.assertRaisesRegex(ValueError,'open flat slab'):self.resolve(b,bad)
        bad=copy.deepcopy(r);del bad['exposedFacadeRules'][0]['region']
        with self.assertRaisesRegex(ValueError,'higher solid'):self.resolve(b,bad)
        for update in [dict(region='anything'),dict(region=None)]:
            bad=copy.deepcopy(r);bad['exposedFacadeRules'][0].update(update)
            with self.assertRaises(ValueError):self.resolve(b,bad)
        for update in [dict(windows=True),dict(balconies=True),dict(openCorridor={})]:
            bad=copy.deepcopy(r);bad['exposedFacadeRules'][0]['rule'].update(update)
            with self.assertRaises(ValueError):self.resolve(b,bad)
        bad=copy.deepcopy(r);rule=bad.pop('exposedFacadeRules')[0]['rule']
        bad['facadeRules']=[dict(rule,polygon=0,ring=0,edge=0,part='high')]
        with self.assertRaisesRegex(ValueError,'upper solid facade'):self.resolve(b,bad)


if __name__ == '__main__': unittest.main()
