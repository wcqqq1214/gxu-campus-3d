import copy
import unittest
from building_overrides import resolve_facades


class ProfiledCorridorTests(unittest.TestCase):
    def fixture(self):
        b={'id':'fixture','polygons':[[[[0,0],[30,0],[30,20],[0,20],[0,0]],
                                      [[5,5],[25,5],[25,15],[5,15],[5,5]]]]}
        form={'parts':[],'height':26.4,'levels':8,'roof':{'type':'flat','rise':0}}
        rule={'polygon':0,'ring':1,'edge':0,'balconies':False,'openCorridor':{
            'depth':1.6,'firstLevel':1,'railHeight':.95,'endInset':.4,
            'frontProfile':[[0,0],[.2,0],[.3,.4],[.7,.4],[.8,0],[1,0]]}}
        return b,form,rule

    def test_courtyard_recess_points_into_building_without_mutating_input(self):
        b,form,rule=self.fixture();before=copy.deepcopy((b,form,rule))
        facade=next(f for f in resolve_facades(b,form,[rule]) if f['rule'])
        self.assertEqual(facade['normal'],[0,1])
        self.assertEqual((b,form,rule),before)
        b['polygons'][0][1].reverse();rule['edge']=3
        facade=next(f for f in resolve_facades(b,form,[rule]) if f['rule'])
        self.assertEqual(facade['normal'],[0,1])

    def test_profile_rejects_outward_excursions_crossings_and_missing_end_returns(self):
        for profile in [[[0,0],[.5,-.1],[1,0]],[[0,0],[.5,1.1],[1,0]],
                        [[0,0],[.7,.2],[.6,.4],[1,0]],[[0,.1],[.5,.3],[1,0]],
                        [[0,0],[.5,float('nan')],[1,0]],[[0,0],[True,.2],[1,0]],
                        [[0,0],[.001,.2],[1,0]]]:
            b,form,rule=self.fixture();rule['openCorridor']['frontProfile']=profile
            with self.subTest(profile=profile),self.assertRaises(ValueError):resolve_facades(b,form,[rule])

    def test_rejects_unsupported_profile_supports_and_recess_outside_host(self):
        for patch in [{'firstLevel':0,'piers':{'bays':4,'width':.3,'depth':1}},
                      {'lastLevel':5},{'balusters':{'spacing':.3,'width':.1}},
                      {'depth':6}]:
            b,form,rule=self.fixture();rule['openCorridor'].update(patch)
            with self.subTest(patch=patch),self.assertRaises(ValueError):resolve_facades(b,form,[rule])
