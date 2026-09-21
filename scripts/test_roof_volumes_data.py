import copy
import math
import unittest
from shapely.geometry import Polygon
from building_overrides import footprint_revision, resolve_building
from roof_volumes_data import resolve_roof_volumes


class RoofVolumeTests(unittest.TestCase):
    def fixture(self):
        b=dict(id='way/roof-volume', name='fixture', category='academic', landmark=None,
               tags={'building':'university'}, polygons=[[[[0,0],[40,0],[40,20],[0,20],[0,0]]]])
        c=dict(id='raised-strip',part='body',polygon=0,edge=0,
               **{'from':.1,'to':.8},inset=4,depth=.5,rise=1.2)
        return b,c

    def resolve(self,b,config):
        return resolve_building(b,dict(roofVolumes=config,footprintRevision=footprint_revision(b),
            evidence={'roofVolumes':dict(status='estimated',sourceRefs=[],note='fixture')}))

    def test_rotation_reversed_winding_idempotence_and_removal(self):
        b,c=self.fixture();r=self.resolve(b,[c]);v=r['form']['roofVolumes'][0]
        self.assertEqual(r,self.resolve(r,[c]))
        self.assertEqual(b['polygons'],r['polygons'])
        self.assertNotIn('roofVolumes',resolve_building(r)['form'])
        area=Polygon(v['footprint']).area
        self.assertAlmostEqual(area,14)
        b['polygons'][0][0].reverse();reverse={**c,'edge':3,'from':.2,'to':.9}
        self.assertLess(Polygon(self.resolve(b,[reverse])['form']['roofVolumes'][0]['footprint']).symmetric_difference(Polygon(v['footprint'])).area,1e-8)
        b,c=self.fixture();angle=.73
        b['polygons'][0][0]=[[x*math.cos(angle)-y*math.sin(angle),x*math.sin(angle)+y*math.cos(angle)] for x,y in b['polygons'][0][0]]
        volume=self.resolve(b,[c])['form']['roofVolumes'][0]
        self.assertAlmostEqual(Polygon(volume['footprint']).area,area)
        self.assertTrue(Polygon(b['polygons'][0][0]).contains(Polygon(volume['footprint'])))

    def test_reject_invalid_identity_anchor_and_dimensions(self):
        b,c=self.fixture()
        for key,value in [('id',''),('part',False),('part','absent'),('polygon',1),('edge',4),
                          ('edge',True),('polygon',-1),('from',.9),('to',1.2),('inset',.2),
                          ('depth',0),('rise',7),('rise',True),('rise',float('inf')),('inset',float('nan')),
                          ('to',.1001),('extra',1)]:
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):self.resolve(b,[{**c,key:value}])
        for config in ([],{},[c]*13,[c,copy.deepcopy(c)]):
            with self.subTest(config=config),self.assertRaises(ValueError):self.resolve(b,config)

    def test_courtyard_and_roof_edge_clearance(self):
        b,c=self.fixture()
        with self.assertRaisesRegex(ValueError,'clearance'):self.resolve(b,[{**c,'from':.005}])
        with self.assertRaisesRegex(ValueError,'clearance'):self.resolve(b,[{**c,'inset':19.1}])
        b['polygons'][0].append([[9,3],[11,3],[11,5],[9,5],[9,3]])
        with self.assertRaisesRegex(ValueError,'courtyards'):self.resolve(b,[c])

    def test_intersecting_volumes_rejected_touching_volumes_allowed(self):
        b,c=self.fixture();second={**c,'id':'second','inset':4.2}
        with self.assertRaisesRegex(ValueError,'overlap'):self.resolve(b,[c,second])
        r=self.resolve(b,[c,{**second,'inset':4.5}])
        shapes=[Polygon(v['footprint']) for v in r['form']['roofVolumes']]
        self.assertAlmostEqual(shapes[0].intersection(shapes[1]).area,0)

    def test_support_and_conflicting_roof_features(self):
        b,c=self.fixture();form=self.resolve(b,[c])['form']
        for feature in ('stairTower','roofDome','roofEave','roofCrown','gableScreen'):
            with self.subTest(feature=feature),self.assertRaisesRegex(ValueError,'another roof'):
                resolve_roof_volumes(b,{**form,feature:{}},[c])
        part=dict(id='body',polygons=[[[[0,0],[40,0],[40,3],[0,3],[0,0]]]],height=10,roof={'type':'flat'})
        with self.assertRaisesRegex(ValueError,'clearance'):resolve_roof_volumes(b,{**form,'parts':[part]},[c])
        for patch in ({'roof':{'type':'hipped'}},{'openBelow':{}},{'roof':{'type':'flat','inset':1}}):
            with self.subTest(patch=patch),self.assertRaises(ValueError):
                resolve_roof_volumes(b,{**form,'parts':[{**part,**patch}]},[c])


if __name__=='__main__':unittest.main()
