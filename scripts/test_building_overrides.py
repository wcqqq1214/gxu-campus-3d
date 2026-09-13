"""Reject unsupported calibration, preserve courts, and exercise real precedence."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from shapely.geometry import Polygon, Point, LineString, box
from shapely.ops import unary_union
from building_overrides import (ROOT, anchor, footprint_revision, load_catalogue,
    resolve_building, resolve_parts, source_catalogue, validate_ids, unique_object)


class BuildingOverrideTests(unittest.TestCase):
    def test_mixed_part_roofs_preserve_partition_and_reject_conflicts(self):
        b=self.building()
        parts=[{'id':'west','polygons':[[[[0,0],[15,0],[15,20],[0,20],[0,0]]]],'levels':5,'height':16.5,'roof':{'type':'hipped','rise':1.5}},
               {'id':'east','polygons':[[[[15,0],[30,0],[30,20],[15,20],[15,0]]]],'levels':3,'height':9.9,'roof':{'type':'flat','rise':0}}]
        r=self.resolve(b,parts=parts,roof={'type':'hipped','rise':2})
        self.assertEqual(r['polygons'],b['polygons'])
        self.assertEqual([p['roof']['type'] for p in r['form']['parts']],['hipped','flat'])
        self.assertNotIn('geometry',r['form']['parts'][1]['roof'])
        for bad in [{'type':'flat','rise':1},{'type':'hipped','rise':0},{'type':'hipped','rise':True},{'type':'hipped','rise':float('nan')},{'type':'unknown','rise':1},{'type':'flat'}]:
            changed=copy.deepcopy(parts);changed[0]['roof']=bad
            with self.subTest(roof=bad),self.assertRaises(ValueError):self.resolve(b,parts=changed)

    def test_ground_corridor_with_pitched_roof_requires_fitting_piers(self):
        corridor={'depth':1.8,'firstLevel':0,'railHeight':.9,'endInset':.3,
                  'piers':{'bays':8,'width':.42,'depth':.5},'balusters':{'spacing':.32,'width':.11}}
        rule={'polygon':0,'ring':0,'edge':0,'balconies':False,'openCorridor':corridor}
        r=self.resolve(self.building(),facadeRules=[rule],roof={'type':'hipped','rise':1.5})
        self.assertEqual(r['form']['facades'][0]['rule'],rule)
        for key,value in [('bays',True),('bays',0),('bays',25),('width',1),('depth',2)]:
            bad=copy.deepcopy(rule);bad['openCorridor']['piers'][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):self.resolve(self.building(),facadeRules=[bad])
        bad=copy.deepcopy(rule);bad['openCorridor']['balusters']['spacing']=.12
        with self.assertRaises(ValueError):self.resolve(self.building(),facadeRules=[bad])

    def panel_fixture(self):
        return {'polygon':0,'ring':0,'edge':0,'balconies':False,'panels':[
            {'id':'screen','type':'lattice','from':.4,'to':.6,'bottom':4.1,'top':6.2,
             'columns':3,'rows':4,'frameWidth':.065,'depth':.12}]}

    def test_upper_panels_preserve_footprint_and_rotate_with_facade(self):
        b=self.building();rule=self.panel_fixture()
        result=self.resolve(b,facadeRules=[rule])
        self.assertEqual(result['polygons'],b['polygons'])
        self.assertEqual(result['form']['facades'][0]['rule'],rule)
        b['polygons']=[[[[-y,x] for x,y in b['polygons'][0][0]]]]
        facade=self.resolve(b,facadeRules=[rule])['form']['facades'][0]
        self.assertEqual(facade['normal'],[1.,0.]);self.assertEqual(facade['rule'],rule)

    def test_panels_reject_invalid_bounds_counts_and_conflicting_facades(self):
        for key,value in [('from',-.1),('to',1.1),('bottom',0),('top',20),('depth',True),
                          ('depth',float('nan')),('frameWidth',.3),('columns',True),('rows',16),
                          ('type','unknown'),('id','')]:
            rule=self.panel_fixture();rule['panels'][0][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                self.resolve(self.building(),facadeRules=[rule])
        for patch in [{'windows':False},{'balconies':True},{'spacing':4},
                      {'openCorridor':{'depth':1,'firstLevel':1,'railHeight':.9,'endInset':.3}}]:
            with self.subTest(patch=patch),self.assertRaises(ValueError):
                self.resolve(self.building(),facadeRules=[{**self.panel_fixture(),**patch}])
        rule=self.panel_fixture();rule['windowBands']=self.bands_fixture()['windowBands']
        with self.assertRaisesRegex(ValueError,'overlaps'):
            self.resolve(self.building(),facadeRules=[rule])
        for same_id in (False,True):
            rule=self.panel_fixture();second=copy.deepcopy(rule['panels'][0])
            if not same_id:second['id']='another'
            rule['panels'].append(second)
            with self.assertRaises(ValueError):self.resolve(self.building(),facadeRules=[rule])

    def test_explicit_stair_flight_preserves_rotated_footprints_and_three_risers(self):
        b=self.building();original=copy.deepcopy(b['polygons'])
        entry={'id':'south','polygon':0,'ring':0,'edge':0,'t':.5,'width':7.2,'primary':True,
               'landingHeight':.45,'stairFlight':{'width':8.4,'landingDepth':1.2,'riserCount':3,'tread':.32,'baseHeight':0}}
        e=self.resolve(b,entrances=[entry])['form']['entrances'][0]
        self.assertEqual(b['polygons'],original);p=e['stairFlight']
        self.assertAlmostEqual(p['front'],1.84);self.assertAlmostEqual(Polygon(p['footprint']).area,8.4*1.84)
        self.assertLess(Polygon(p['footprint']).intersection(Polygon(original[0][0])).area,1e-8)
        b['polygons']=[[[[-y,x] for x,y in original[0][0]]]]
        rotated=self.resolve(b,entrances=[entry])['form']['entrances'][0]['stairFlight']
        self.assertAlmostEqual(Polygon(rotated['footprint']).area,Polygon(p['footprint']).area)

    def test_stair_flight_rejects_unsupported_risers_and_overhang(self):
        entry={'id':'south','polygon':0,'ring':0,'edge':0,'t':.5,'width':7.2,'primary':True,
               'landingHeight':.45,'stairFlight':{'width':8.4,'landingDepth':1.2,'riserCount':3,'tread':.32,'baseHeight':0}}
        for key,value in [('riserCount',True),('riserCount',1),('riserCount',8),('width',7),('width',100),('landingDepth',.5),('tread',.1),('baseHeight',.4),('baseHeight',float('nan'))]:
            bad=copy.deepcopy(entry);bad['stairFlight'][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):self.resolve(self.building(),entrances=[bad])
        bad=copy.deepcopy(entry);bad.pop('landingHeight')
        with self.assertRaises(ValueError):self.resolve(self.building(),entrances=[bad])

    def test_multibay_door_frame_retains_entrance_anchor_and_shared_landing(self):
        b=self.building()
        entry={'id':'south','polygon':0,'ring':0,'edge':0,'t':.5,'width':7.2,'primary':True,
               'landingHeight':.36,'doorFrame':{'bays':3,'pierWidth':.55,'pierDepth':1.2}}
        r=self.resolve(b,entrances=[entry]);e=r['form']['entrances'][0]
        self.assertEqual(r['polygons'],b['polygons'])
        self.assertEqual((e['center'],e['bearing'],e['landingHeight']),([15.,0.],180.,.36))
        self.assertEqual(e['doorFrame'],entry['doorFrame'])
        b['polygons']=[[[[-y,x] for x,y in b['polygons'][0][0]]]]
        e=self.resolve(b,entrances=[entry])['form']['entrances'][0]
        self.assertEqual((e['center'],e['bearing']),([0.,15.],90.))

    def test_multibay_door_frame_rejects_blocked_bays_and_unsupported_geometry(self):
        entry={'id':'south','polygon':0,'ring':0,'edge':0,'t':.5,'width':7.2,'primary':True,
               'landingHeight':.36,'doorFrame':{'bays':3,'pierWidth':.55,'pierDepth':1.2}}
        for key,value in [('bays',True),('bays',0),('bays',3.5),('bays',6),
                          ('pierWidth',True),('pierWidth',float('nan')),('pierWidth',.1),
                          ('pierDepth','1.2'),('pierDepth',.3),('pierDepth',2)]:
            bad=copy.deepcopy(entry);bad['doorFrame'][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                self.resolve(self.building(),entrances=[bad])
        bad=copy.deepcopy(entry);bad.pop('landingHeight')
        with self.assertRaises(ValueError):self.resolve(self.building(),entrances=[bad])
        # The clear width fits exactly, but its outer piers leave the facade.
        bad=copy.deepcopy(entry);bad['t']=7.2/2/30
        with self.assertRaises(ValueError):self.resolve(self.building(),entrances=[bad])

    def test_raised_landing_rejects_unusable_heights_and_conflicting_porticos(self):
        entry={'id':'south','polygon':0,'ring':0,'edge':0,'t':.5,'width':7.2,'primary':True,'landingHeight':.36}
        self.assertEqual(self.resolve(self.building(),entrances=[entry])['form']['entrances'][0]['landingHeight'],.36)
        for height in [True,'0.36',float('nan'),0,.19,1.21]:
            with self.subTest(height=height),self.assertRaises(ValueError):
                self.resolve(self.building(),entrances=[{**entry,'landingHeight':height}])
        with self.assertRaises(ValueError):
            self.resolve(self.building(),entrances=[{**self.attached_fixture(),'landingHeight':.36}])

    def test_oblique_partition_recovers_collinear_facade_without_overlapping_seam(self):
        b=self.building()
        ring=[[-272.93077627413,-868.0510959998603],[-206.8857344524391,-868.1290199999798],
              [-196.8630556923097,-877.7915959997881],[-269.3505153860546,-877.7025399999338],
              [-272.93077627413,-868.0510959998603]]
        b['polygons']=[[ring]];shape=Polygon(ring);parts=[]
        for name,extent,h,levels in [('west',box(-1000,-2000,-265,0),16.5,5),
                                     ('east',box(-265,-2000,0,0),13.2,4)]:
            p=shape.intersection(extent)
            parts.append({'id':name,'polygons':[[list(map(list,p.exterior.coords))]],'height':h,'levels':levels})
        # The exact overlay loses both intervals on this real-world oblique edge.
        line=LineString(ring[2:4])
        self.assertTrue(all(line.intersection(Polygon(p['polygons'][0][0])).length<.01 for p in parts))
        result=self.resolve(b,parts=parts)['form']['facades']
        segments=[LineString([f['start'],f['end']]) for f in result if f['edge']==2]
        self.assertEqual(len(segments),2)
        self.assertAlmostEqual(sum(s.length for s in segments),line.length,places=8)
        self.assertLess(segments[0].intersection(segments[1]).length,1e-8)

    def test_part_specific_glazing_uses_local_segment_and_height(self):
        b=self.building()
        parts=[{'id':'west','polygons':[[[[0,0],[12,0],[12,20],[0,20],[0,0]]]],'height':16.5,'levels':5},
               {'id':'east','polygons':[[[[12,0],[30,0],[30,20],[12,20],[12,0]]]],'height':13.2,'levels':4}]
        rule=self.bands_fixture();rule['part']='east'
        r=self.resolve(b,parts=parts,facadeRules=[rule])
        facades=[f for f in r['form']['facades'] if f['edge']==0]
        self.assertEqual([(f['part'],f['start'],f['end'],f['levels']) for f in facades],
                         [('west',[0.,0.],[12.,0.],5.),('east',[12.,0.],[30.,0.],4.)])
        self.assertEqual(facades[0]['rule'],{})
        self.assertEqual(facades[1]['rule'],rule)
        self.assertEqual(r['polygons'],b['polygons'])
        # Rotate the actual partition too: the selected 18 m segment stays selected.
        b['polygons']=[[[[-y,x] for x,y in b['polygons'][0][0]]]]
        for part in parts:
            part['polygons']=[[[[-y,x] for x,y in part['polygons'][0][0]]]]
        f=next(f for f in self.resolve(b,parts=parts,facadeRules=[rule])['form']['facades']
               if f['part']=='east' and f['edge']==0)
        self.assertEqual((f['start'],f['end'],f['normal']),([0.,12.],[0.,30.],[1.,0.]))

    def test_part_specific_facade_rejects_stale_disconnected_and_ambiguous_anchors(self):
        b=self.building()
        parts=[{'id':'west','polygons':[[[[0,0],[12,0],[12,20],[0,20],[0,0]]]],'height':16.5,'levels':5},
               {'id':'east','polygons':[[[[12,0],[30,0],[30,20],[12,20],[12,0]]]],'height':13.2,'levels':4}]
        rule=self.bands_fixture();rule['part']='east'
        for part,edge in [('missing',0),('east',3)]:
            bad={**rule,'part':part,'edge':edge}
            with self.subTest(part=part,edge=edge),self.assertRaises(ValueError):
                self.resolve(b,parts=parts,facadeRules=[bad])
        with self.assertRaises(ValueError):
            self.resolve(b,parts=parts,facadeRules=[rule,self.bands_fixture()])
        # One part touching the same original edge in two disjoint intervals
        # has no unambiguous normalized from/to coordinate.
        parts[0]['polygons']=[[[[10,0],[20,0],[20,20],[10,20],[10,0]]]]
        parts[1]['polygons']=[[[[0,0],[10,0],[10,20],[0,20],[0,0]]],
                              [[[20,0],[30,0],[30,20],[20,20],[20,0]]]]
        with self.assertRaises(ValueError):self.resolve(b,parts=parts,facadeRules=[rule])

    def bands_fixture(self):
        return {'polygon':0,'ring':0,'edge':0,'windowBands':{
            'from':.15,'to':.85,'firstLevel':1,'heightRatio':.55,'depth':.38,'thickness':.18,
            'windows':[{'from':.17,'to':.45,'panes':4},{'from':.5,'to':.58,'panes':1},
                       {'from':.63,'to':.83,'panes':3}]}}

    def test_window_bands_preserve_backing_wall_and_unreviewed_facades(self):
        b=self.building();rule=self.bands_fixture()
        r=self.resolve(b,facadeRules=[rule]);self.assertEqual(r['polygons'],b['polygons'])
        self.assertEqual(r['form']['parts'],[])
        facades=r['form']['facades'];self.assertEqual(len(facades),4)
        self.assertEqual(facades[0]['rule'],rule)
        self.assertTrue(all(not f['rule'] for f in facades[1:]))
        # Rotation changes world directions, not the calibrated window strip.
        b['polygons']=[[[[-y,x] for x,y in b['polygons'][0][0]]]]
        rotated=self.resolve(b,facadeRules=[rule])['form']['facades'][0]
        self.assertEqual(rotated['normal'],[1.,0.])
        self.assertEqual(rotated['rule'],rule)

    def test_window_bands_reject_overlap_invalid_floors_and_incompatible_forms(self):
        for key,value in [('from',-.1),('to',1.1),('depth',float('nan')),
                          ('thickness',True),('heightRatio',.99),('firstLevel',0),('firstLevel',5)]:
            rule=self.bands_fixture();rule['windowBands'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                self.resolve(self.building(),facadeRules=[rule])
        for change in ['overlap','frame','panes','outside','unordered','corridor','balconies']:
            rule=self.bands_fixture();windows=rule['windowBands']['windows']
            if change=='overlap':windows[1]['from']=.4
            if change=='frame':windows[1]['from']=.451
            if change=='panes':windows[1]['panes']=12
            if change=='outside':windows[-1]['to']=.9
            if change=='unordered':windows.reverse()
            if change=='corridor':rule['openCorridor']={}
            if change=='balconies':rule['balconies']=True
            with self.subTest(change=change),self.assertRaises(ValueError):
                self.resolve(self.building(),facadeRules=[rule])
        b,values=self.portico_fixture()
        rule=self.bands_fixture();rule['edge']=2;values['facadeRules']=[rule]
        with self.assertRaises(ValueError):self.resolve(b,**values)

    def attached_fixture(self):
        return {'id':'south','polygon':0,'ring':0,'edge':0,'t':.5,'width':4.2,'primary':True,
                'attachedPortico':{'width':9,'depth':3.2,'platformHeight':.36,
                    'clearHeight':3.4,'slabThickness':.2,'parapetHeight':1,
                    'columnWidth':.55,'columnInset':.45,'steps':3,'tread':.3,'stepBaseHeight':0}}

    def test_attached_portico_is_external_and_does_not_replace_the_footprint(self):
        b=self.building();entry=self.attached_fixture();r=self.resolve(b,entrances=[entry])
        p=r['form']['entrances'][0]['attachedPortico']
        self.assertEqual(r['polygons'],b['polygons'])
        self.assertEqual(r['form']['parts'],[])
        self.assertEqual(len(p['columns']),4)
        shape=Polygon(p['footprint']);body=Polygon(b['polygons'][0][0])
        self.assertAlmostEqual(shape.area,9*4.1)
        self.assertLess(shape.intersection(body).area,1e-8)
        self.assertAlmostEqual(shape.boundary.intersection(body.boundary.buffer(1e-8)).length,9,places=6)
        # A reversed ring must still put the portico outside, facing south.
        b['polygons'][0][0]=list(reversed(b['polygons'][0][0]));entry['edge']=3
        e=self.resolve(b,entrances=[entry])['form']['entrances'][0]
        self.assertEqual(e['bearing'],180)
        self.assertLess(Polygon(e['attachedPortico']['footprint']).intersection(body).area,1e-8)

    def test_attached_portico_rejects_blocked_openings_and_invalid_dimensions(self):
        for key,value in [('width',31),('columnWidth',4),('columnInset',.1),
                          ('clearHeight',3),('platformHeight',True),('depth',float('nan')),
                          ('parapetHeight',.1),('steps',0),('steps',True),('steps',2.5),
                          ('stepBaseHeight',-.1),('stepBaseHeight',True),('stepBaseHeight',.36)]:
            entry=self.attached_fixture();entry['attachedPortico'][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                self.resolve(self.building(),entrances=[entry])
        entry=self.attached_fixture();entry['recess']=2
        with self.assertRaises(ValueError):self.resolve(self.building(),entrances=[entry])
        # A neighbouring mapped component in front cannot be swallowed by the porch.
        b=self.building();b['polygons'].append([[[14,-4],[16,-4],[16,-2],[14,-2],[14,-4]]])
        with self.assertRaises(ValueError):self.resolve(b,entrances=[self.attached_fixture()])

    def test_flat_canopy_crosses_solid_height_parts_and_rotates_with_facade(self):
        b=self.building();entry=self.attached_fixture()
        entry['attachedPortico'].update(parapetHeight=0,slabThickness=.6)
        parts=[{'id':'west','polygons':[[[[0,0],[15,0],[15,20],[0,20],[0,0]]]],'height':16.5,'levels':5},
               {'id':'east','polygons':[[[[15,0],[30,0],[30,20],[15,20],[15,0]]]],'height':13.2,'levels':4}]
        r=self.resolve(b,parts=parts,entrances=[entry]);e=r['form']['entrances'][0]
        self.assertEqual(r['polygons'],b['polygons'])
        self.assertEqual(len(e['attachedPortico']['columns']),4)
        self.assertEqual(e['attachedPortico']['parapetHeight'],0)
        footprint=Polygon(e['attachedPortico']['footprint'])
        self.assertLess(footprint.intersection(Polygon(b['polygons'][0][0])).area,1e-8)
        b['polygons']=[[[[-y,x] for x,y in b['polygons'][0][0]]]]
        for part in parts:part['polygons']=[[[[-y,x] for x,y in part['polygons'][0][0]]]]
        e=self.resolve(b,parts=parts,entrances=[entry])['form']['entrances'][0]
        self.assertEqual(e['bearing'],90)
        self.assertGreater(Polygon(e['attachedPortico']['footprint']).centroid.x,0)

    def test_attached_canopy_respects_lower_part_and_open_storey(self):
        entry=self.attached_fixture();entry['attachedPortico'].update(parapetHeight=0,slabThickness=.6)
        parts=[{'id':'west','polygons':[[[[0,0],[15,0],[15,20],[0,20],[0,0]]]],'height':16.5,'levels':5},
               {'id':'east','polygons':[[[[15,0],[30,0],[30,20],[15,20],[15,0]]]],'height':3.8,'levels':1}]
        with self.assertRaisesRegex(ValueError,'every touched part'):
            self.resolve(self.building(),parts=parts,entrances=[entry])
        b,values=self.portico_fixture();entry['edge']=2
        with self.assertRaisesRegex(ValueError,'every touched part'):
            self.resolve(b,parts=values['parts'],entrances=[entry])

    def test_attached_canopy_rejects_invalid_optional_parapet(self):
        for value in [True,'0',-.1,float('nan'),float('inf'),.3]:
            entry=self.attached_fixture();entry['attachedPortico']['parapetHeight']=value
            with self.subTest(value=value),self.assertRaises(ValueError):
                self.resolve(self.building(),entrances=[entry])

    def portico_fixture(self):
        b=self.building()
        b['polygons']=[[[[0,0],[8,0],[8,-4],[22,-4],[22,0],[30,0],[30,20],[0,20],[0,0]]]]
        parts=[{'id':'main','polygons':[[[[0,0],[30,0],[30,20],[0,20],[0,0]]]],'height':16.5,'levels':5},
               {'id':'porch','polygons':[[[[8,-4],[22,-4],[22,0],[8,0],[8,-4]]]],'height':4,'levels':1,
                'openBelow':{'clearHeight':3.4,'floorHeight':.45,'columns':[
                    {'center':[x,-3.3],'width':.8,'depth':.8,'angle':0} for x in [8.7,11.5,18.5,21.3]]}}]
        entrances=[{'id':'south','polygon':0,'ring':0,'edge':2,'t':.5,'width':6.8,'primary':True,'recess':4}]
        return b,{'parts':parts,'entrances':entrances,'roof':{'type':'flat'}}

    def test_portico_preserves_outline_and_exposes_main_wall_above_canopy(self):
        b,values=self.portico_fixture();r=self.resolve(b,**values)
        self.assertEqual(r['polygons'],b['polygons'])
        entrance=r['form']['entrances'][0]
        self.assertEqual(entrance['center'],[15,0])
        self.assertEqual(entrance['outerCenter'],[15,-4])
        self.assertEqual(entrance['bearing'],180)
        self.assertEqual(entrance['platformHeight'],.45)
        facades=r['form']['facades']
        self.assertTrue(all(f['rule']['windows'] is False for f in facades if f['part']=='porch'))
        exposed=[f for f in facades if 'minimumHeight' in f]
        self.assertEqual(len(exposed),1)
        self.assertEqual(exposed[0]['minimumHeight'],4)
        self.assertEqual(exposed[0]['height'],16.5)
        self.assertAlmostEqual(LineString([exposed[0]['start'],exposed[0]['end']]).length,14)

    def test_portico_rejects_floating_door_blocked_route_and_invalid_supports(self):
        b,values=self.portico_fixture()
        bad=[]
        for depth in [2,5,True,float('nan')]:
            v=copy.deepcopy(values);v['entrances'][0]['recess']=depth;bad.append(v)
        for center in [[0,0],[15,-3.3],[float('nan'),-3.3]]:
            v=copy.deepcopy(values);v['parts'][1]['openBelow']['columns'][0]['center']=center;bad.append(v)
        v=copy.deepcopy(values);v['parts'][1]['openBelow']['columns'][1]=copy.deepcopy(v['parts'][1]['openBelow']['columns'][0]);bad.append(v)
        for key,height in [('clearHeight',4),('floorHeight',2),('clearHeight',True)]:
            v=copy.deepcopy(values);v['parts'][1]['openBelow'][key]=height;bad.append(v)
        v=copy.deepcopy(values);v['roof']={'type':'hipped'};bad.append(v)
        for v in bad:
            with self.subTest(v=v),self.assertRaises(ValueError):self.resolve(b,**v)

    def test_multistorey_portico_keeps_upper_windows_and_continuous_roof(self):
        b,values=self.portico_fixture()
        values['parts'][1].update(height=16.5,levels=5)
        values['entrances'][0]['steps']=2
        r=self.resolve(b,**values)
        front=[f for f in r['form']['facades'] if f['part']=='porch']
        self.assertTrue(front)
        self.assertTrue(all(f['minimumHeight']==3.4 and f['rule'].get('windows',True) for f in front))
        self.assertEqual(r['form']['entrances'][0]['steps'],2)
        seam=LineString([[8,0],[22,0]])
        for part in r['form']['parts']:
            self.assertIn('parapetEdges',part)
            self.assertTrue(all(LineString(edge).intersection(seam).length < 1e-6 for edge in part['parapetEdges']))
        # An explicit facade rule still wins on an upper storey.
        values['facadeRules']=[{'polygon':0,'ring':0,'edge':2,'windows':False}]
        r=self.resolve(b,**values)
        self.assertFalse(next(f for f in r['form']['facades'] if f['edge']==2)['rule']['windows'])
        for base in [-.1,.45,True,float('nan')]:
            values['entrances'][0]['stepBaseHeight']=base
            with self.subTest(base=base),self.assertRaises(ValueError):self.resolve(b,**values)
        values['entrances'][0]['stepBaseHeight']=.15
        self.assertEqual(self.resolve(b,**values)['form']['entrances'][0]['stepBaseHeight'],.15)
        for steps in [0,13,True,2.5,'2']:
            values['entrances'][0]['steps']=steps
            with self.subTest(steps=steps),self.assertRaises(ValueError):self.resolve(b,**values)

    def test_rotated_equal_height_seam_is_not_a_parapet(self):
        # Real animal-college seam that survived an exact Shapely difference.
        parts = [{"id": "entrance-core", "polygons": [[[[306.129169723045, -248.0206644421203], [306.1276938455245, -248.0209599998649], [292.505712838706, -250.7480045342522], [290.2044925008056, -239.2530768394513], [303.82736244240726, -236.52280488364025], [306.129169723045, -248.0206644421203]]]], "height": 23.1, "levels": 7}, {"id": "entrance-front", "polygons": [[[[306.1276938455245, -248.0209599998649], [307.0407116662392, -252.57394800007617], [293.4172547634234, -255.3012879999136], [292.50423694416656, -250.74830000009783], [306.1276938455245, -248.0209599998649]]]], "height": 23.1, "levels": 7}]
        shape=unary_union([Polygon(p['polygons'][0][0]) for p in parts])
        b=self.building();polys=[shape] if shape.geom_type=='Polygon' else list(shape.geoms)
        b['polygons']=[[[list(x) for x in p.exterior.coords]] for p in polys]
        b['height']=23.1
        resolved=resolve_parts(b,parts,{'type':'flat'})
        for part,other in [(resolved[0],resolved[1]),(resolved[1],resolved[0])]:
            neighbor=Polygon(other['polygons'][0][0]).boundary
            for edge in part['parapetEdges']:
                self.assertLess(LineString(edge).intersection(neighbor.buffer(1e-8)).length,1e-6)

    def building(self):
        return {'id':'way/test','name':'测试教学楼','category':'academic','height':16.5,
                'levels':5,'landmark':None,'tags':{'building':'university'},
                'polygons':[[[[0,0],[30,0],[30,20],[0,20],[0,0]]]]}

    def test_open_corridor_is_anchored_inside_the_existing_part(self):
        b=self.building()
        rule={'polygon':0,'ring':0,'edge':0,'openCorridor':{'depth':1.4,'firstLevel':1,'railHeight':.9,'endInset':.3}}
        r=self.resolve(b,facadeRules=[rule],roof={'type':'flat'})
        self.assertEqual(r['polygons'],b['polygons'])
        self.assertEqual(sum('openCorridor' in f['rule'] for f in r['form']['facades']),1)
        for key,value in [('depth',21),('depth',True),('firstLevel',0),('firstLevel',5),('firstLevel',1.5),('railHeight',3),('endInset',15)]:
            bad=copy.deepcopy(rule);bad['openCorridor'][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                self.resolve(b,facadeRules=[bad],roof={'type':'flat'})
        # A recess must not punch through the wall into an existing courtyard.
        b['polygons'][0].append([[10,1],[10,10],[20,10],[20,1],[10,1]])
        with self.assertRaises(ValueError):self.resolve(b,facadeRules=[rule],roof={'type':'flat'})

    def test_open_corridors_reject_intersecting_corner_recesses(self):
        rule={'polygon':0,'ring':0,'edge':0,'openCorridor':{'depth':1.4,'firstLevel':1,'railHeight':.9,'endInset':.3}}
        other=copy.deepcopy(rule);other['edge']=1
        with self.assertRaises(ValueError):self.resolve(self.building(),facadeRules=[rule,other],roof={'type':'flat'})

    def test_open_corridor_on_portico_is_rejected_instead_of_silently_dropped(self):
        for levels,height in [(1,4),(5,16.5)]:
            b,values=self.portico_fixture()
            values['parts'][1].update(levels=levels,height=height)
            values['facadeRules']=[{'polygon':0,'ring':0,'edge':2,
                'openCorridor':{'depth':1.4,'firstLevel':1,'railHeight':.9,'endInset':.3}}]
            with self.subTest(levels=levels),self.assertRaisesRegex(ValueError,'solid'):
                self.resolve(b,**values)

    def window_grid_rule(self, edge=0):
        return {'polygon':0,'ring':0,'edge':edge,'windowGrid':{
            'columns':8,'firstLevel':1,'edgeInset':.22,'widthRatio':.78,
            'heightRatio':.55,'pilasterWidth':.18,'pilasterDepth':.28,'paneRows':4}}

    def test_window_grid_preserves_multistorey_entrance_and_mapped_outline(self):
        b,values=self.portico_fixture()
        values['parts'][1].update(levels=5,height=16.5)
        values['facadeRules']=[self.window_grid_rule(2)]
        r=self.resolve(b,**values)
        f=next(f for f in r['form']['facades'] if f['edge']==2)
        self.assertEqual(f['rule']['windowGrid']['columns'],8)
        self.assertEqual(f['minimumHeight'],3.4)
        self.assertEqual(r['polygons'],b['polygons'])
        self.assertEqual(r['form']['entrances'][0]['recess'],4)

    def test_window_grid_rejects_unusable_dimensions_and_portico_conflicts(self):
        bad=[('columns',True),('columns',0),('columns',100),('firstLevel',5),
             ('firstLevel',-1),('edgeInset',16),('widthRatio',1),('heightRatio',1),
             ('pilasterWidth',2),('pilasterDepth',float('nan')),('pilasterDepth',4),
             ('heightRatio',.001),('paneRows',0)]
        for key,value in bad:
            rule=self.window_grid_rule();rule['windowGrid'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                self.resolve(self.building(),facadeRules=[rule])
        b,values=self.portico_fixture();values['facadeRules']=[self.window_grid_rule(2)]
        with self.assertRaises(ValueError):self.resolve(b,**values)
        rule=self.window_grid_rule();rule['windows']=False
        with self.assertRaises(ValueError):self.resolve(self.building(),facadeRules=[rule])

    def test_window_grid_count_cannot_repeat_across_split_facade(self):
        b=self.building()
        parts=[{'id':str(i),'polygons':[[[[x,0],[x+15,0],[x+15,20],[x,20],[x,0]]]],
                'height':16.5,'levels':5} for i,x in enumerate([0,15])]
        with self.assertRaisesRegex(ValueError,'undivided'):
            self.resolve(b,parts=parts,facadeRules=[self.window_grid_rule()])

    def record(self, b, **values):
        fields={('roof.'+k) for k in values.get('roof',{})} | (set(values)-{'roof'})
        return {'footprintRevision':footprint_revision(b),**values,
                'evidence':{key:{'status':'confirmed','sourceRefs':['test-source'],'note':'Fixture source'} for key in fields}}

    def resolve(self, b, **values):
        return resolve_building(b,self.record(b,**values),{'test-source','osm'})

    def test_invalid_osm_value_does_not_discard_the_other_valid_dimension(self):
        b=self.building();b['tags'].update({'height':'NaN','building:levels':'7'})
        r=resolve_building(b);self.assertEqual(r['levels'],7);self.assertAlmostEqual(r['height'],23.1)
        b['tags'].update({'height':'30 m','building:levels':'bad'})
        r=resolve_building(b);self.assertEqual(r['height'],30);self.assertEqual(r['levels'],5)
        for bad in [0,-1,float('inf'),True]:
            b['tags']={'height':bad,'building:levels':'4'}
            self.assertAlmostEqual(resolve_building(b)['height'],13.2)

    def test_independent_field_precedence_and_explicit_conflict(self):
        b=self.building();b['tags'].update({'height':'30','building:levels':'6'})
        r=self.resolve(b,levels=7)
        self.assertEqual((r['height'],r['levels']),(30,7))
        r=self.resolve(b,levels=7,height=28)
        self.assertEqual((r['height'],r['levels']),(28,7))
        r=self.resolve(b,levels=2)
        self.assertTrue(r['calibration']['warnings'])
        self.assertEqual(b['height'],16.5) # Caller data is never mutated.

    def test_schema_sources_duplicates_and_stale_ids_fail(self):
        b=self.building();record=self.record(b,levels=6)
        for mutate in [lambda r:r.update(typo=1),lambda r:r.update(footprintRevision='old'),
                       lambda r:r['evidence'].clear(),
                       lambda r:r['evidence']['levels'].update(sourceRefs=['unknown'])]:
            with self.subTest(mutate=mutate):
                r=copy.deepcopy(record);mutate(r)
                with self.assertRaises(ValueError):resolve_building(b,r,{'test-source'})
        with self.assertRaises(ValueError):json.loads('{"x":1,"x":2}',object_pairs_hook=unique_object)
        with self.assertRaises(ValueError):validate_ids({'way/missing':{}},[b])
        with self.assertRaises(ValueError):validate_ids({b['id']:{}},[{**b,'landmark':'library'}])
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'overrides.json';path.write_text('{"schemaVersion":2,"buildings":{}}')
            with self.assertRaises(ValueError):load_catalogue(path)

    def test_invalid_manual_numbers_never_become_geometry(self):
        for key in ['levels','height','floorHeight']:
            for value in [0,-1,float('nan'),float('inf'),True,None,'nonsense']:
                with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                    self.resolve(self.building(),**{key:value})

    def test_entrance_is_anchored_on_original_exterior_and_points_out(self):
        b=self.building();e={'id':'main','polygon':0,'ring':0,'edge':0,'t':.25,'width':4,'primary':True}
        r=self.resolve(b,entrances=[e]);door=r['form']['entrances'][0]
        self.assertEqual(door['center'],[7.5,0]);self.assertEqual(door['bearing'],180)
        for change in [{'edge':99},{'edge':-1},{'t':1.1},{'width':20},{'primary':False}]:
            with self.subTest(change=change),self.assertRaises(ValueError):self.resolve(b,entrances=[{**e,**change}])

    def test_parts_preserve_court_and_each_exterior_segment_occurs_once(self):
        b=self.building();b['polygons'][0].append([[10,5],[10,15],[20,15],[20,5],[10,5]])
        # Whole court ring remains with the lower part; taller west strip ends at x=8.
        parts=[{'id':'core','polygons':[[[[0,0],[8,0],[8,20],[0,20],[0,0]]]],'height':23.1,'levels':7},
               {'id':'wing','polygons':[[[[8,0],[30,0],[30,20],[8,20],[8,0]],b['polygons'][0][1]]],'height':16.5,'levels':5}]
        r=self.resolve(b,levels=7,parts=parts);form=r['form']
        shapes=[Polygon(p[0],p[1:]) for part in form['parts'] for p in part['polygons']]
        target=Polygon(b['polygons'][0][0],b['polygons'][0][1:])
        self.assertLess(unary_union(shapes).symmetric_difference(target).area,1e-6)
        self.assertFalse(unary_union(shapes).contains(Point(15,10)))
        self.assertAlmostEqual(sum(__import__('math').dist(f['start'],f['end']) for f in form['facades']),target.length)
        self.assertEqual({f['levels'] for f in form['facades']},{5,7})
        # All inner-ring window normals point into open courtyard space.
        for f in form['facades']:
            if f['ring']:
                point=Point(*[(f['start'][i]+f['end'][i])/2+f['normal'][i]*.1 for i in (0,1)])
                self.assertFalse(target.covers(point))
        for bad in [parts[:1],parts+[parts[0]],
                    [{**parts[0],'polygons':[[[[-1,0],[8,0],[8,20],[-1,20],[-1,0]]]]},parts[1]]]:
            with self.assertRaises(ValueError):self.resolve(b,levels=7,parts=bad)

    def test_pitched_roofs_resolve_on_parts_of_concave_footprint(self):
        b=self.building();b['polygons']=[[[[0,0],[30,0],[30,10],[10,10],[10,20],[0,20],[0,0]]]]
        parts=[{'id':'bar','polygons':[[[[0,0],[30,0],[30,10],[0,10],[0,0]]]],'height':16.5,'levels':5},
               {'id':'annex','polygons':[[[[0,10],[10,10],[10,20],[0,20],[0,10]]]],'height':9.9,'levels':3}]
        r=self.resolve(b,parts=parts,roof={'type':'gabled','rise':2})
        self.assertTrue(all(p['roof']['geometry']['triangles'] for p in r['form']['parts']))

    def test_blank_wall_rules_and_rollback_do_not_leave_stale_calibration(self):
        b=self.building();rules=[{'polygon':0,'ring':0,'edge':1,'windows':False,'balconies':False}]
        r=self.resolve(b,levels=6,facadeRules=rules)
        edge=next(f for f in r['form']['facades'] if f['edge']==1)
        self.assertFalse(edge['rule']['windows'])
        restored=resolve_building(r)
        self.assertEqual(restored['levels'],5);self.assertNotIn('calibration',restored)
        self.assertNotIn('facades',restored['form']);self.assertEqual(restored['facadeBasis'],'按建筑类型推定')

    def test_real_pilot_resolves_without_changing_original_footprints(self):
        buildings=json.loads((ROOT/'public/data/buildings.json').read_text());catalogue=load_catalogue()
        validate_ids(catalogue,buildings);sources={s['id'] for s in source_catalogue()}
        for b in buildings:
            if b['id'] in catalogue:
                r=resolve_building(b,catalogue[b['id']],sources)
                self.assertEqual(r['polygons'],b['polygons']);self.assertEqual(r['tags'],b['tags'])
                self.assertEqual(r['calibration']['evidence']['height']['status'],'estimated')
                self.assertEqual(resolve_building(r,catalogue[b['id']],sources),r)
                persisted=json.loads(json.dumps(r))
                self.assertEqual(resolve_building(persisted,catalogue[b['id']],sources),persisted)


if __name__=='__main__':unittest.main()
