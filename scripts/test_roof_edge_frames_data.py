import math
import unittest
from shapely.geometry import Polygon
from building_overrides import footprint_revision, resolve_building
from roof_edge_frames_data import resolve_roof_edge_frames


class RoofEdgeFrameTests(unittest.TestCase):
    def fixture(self):
        b = dict(id='way/frame', name='fixture', category='academic', landmark=None,
                 tags={'building':'university'}, polygons=[[[[0,0],[40,0],[40,20],[0,20],[0,0]]]])
        c = dict(id='frame', part='body', polygon=0, edge=0, **{'from':.05,'to':.95},
                 inset=.8, rise=3.3, beamHeight=.4, beamDepth=.5, postCount=7, postWidth=.45, postDepth=.4)
        return b, c

    def resolve(self, b, configs, volumes=None):
        record = dict(roofEdgeFrames=configs, footprintRevision=footprint_revision(b),
                      evidence={'roofEdgeFrames':dict(status='estimated', sourceRefs=[], note='fixture')})
        if volumes:
            record['roofVolumes'] = volumes
            record['evidence']['roofVolumes'] = dict(status='estimated', sourceRefs=[], note='fixture')
        return resolve_building(b, record)

    def test_rotation_winding_and_repeated_resolution(self):
        b, c = self.fixture(); r = self.resolve(b, [c]); f = r['form']['roofEdgeFrames'][0]
        self.assertEqual(r, self.resolve(r, [c]))
        self.assertNotIn('roofEdgeFrames', resolve_building(r)['form'])
        self.assertEqual(len(f['posts']), 7)
        self.assertAlmostEqual(f['posts'][0][0], 2)
        self.assertAlmostEqual(f['posts'][-1][0], 38)
        b['polygons'][0][0].reverse()
        rev = self.resolve(b, [{**c,'edge':3}])['form']['roofEdgeFrames'][0]
        self.assertLess(Polygon(f['footprint']).symmetric_difference(Polygon(rev['footprint'])).area, 1e-8)
        b, c = self.fixture(); angle = .67
        b['polygons'][0][0] = [[x*math.cos(angle)-y*math.sin(angle), x*math.sin(angle)+y*math.cos(angle)]
                              for x, y in b['polygons'][0][0]]
        rotated = self.resolve(b,[c])['form']['roofEdgeFrames'][0]
        self.assertAlmostEqual(Polygon(rotated['footprint']).area, Polygon(f['footprint']).area)

    def test_invalid_dimensions_and_identifiers(self):
        b, c = self.fixture()
        for key, value in [('id',''),('part',False),('part','missing'),('polygon',True),('edge',4),
                           ('postCount',True),('postCount',2.5),('postCount',41),('rise',float('nan')),
                           ('beamDepth',True),('beamHeight',3),('beamDepth',.3),('from',1),
                           ('to',.051),('postWidth',0),('extra',1)]:
            with self.subTest(key=key,value=value), self.assertRaises(ValueError):
                self.resolve(b,[{**c,key:value}])
        for config in ([],{},[c,c],[c]*9):
            with self.subTest(config=config), self.assertRaises(ValueError):self.resolve(b,config)

    def test_support_edges_courtyard_and_other_features(self):
        b,c = self.fixture()
        with self.assertRaisesRegex(ValueError,'clearance'):self.resolve(b,[{**c,'from':0}])
        b['polygons'][0].append([[8,.4],[10,.4],[10,1.2],[8,1.2],[8,.4]])
        with self.assertRaisesRegex(ValueError,'courtyards'):self.resolve(b,[c])
        b,c = self.fixture(); form = self.resolve(b,[c])['form']
        for feature in ('stairTower','roofDome','roofEave','roofCrown','gableScreen'):
            with self.subTest(feature=feature), self.assertRaises(ValueError):
                resolve_roof_edge_frames(b,{**form,feature:{}},[c])
        for patch in ({'openBelow':{}},{'roof':{'type':'hipped'}},{'roof':{'type':'flat','inset':1}}):
            part = dict(id='body',height=10,roof={'type':'flat'},polygons=b['polygons'])
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                resolve_roof_edge_frames(b,{**form,'parts':[{**part,**patch}]},[c])

    def test_cap_height_and_glazing_collisions(self):
        b,c = self.fixture()
        volume = dict(id='pavilion',part='body',polygon=0,edge=0,**{'from':.4,'to':.6},
                      inset=1.1,depth=4,rise=6,cap={'overhang':.5,'height':.4})
        self.resolve(b,[c],[volume])  # Cap is above the beam, despite plan overlap.
        with self.assertRaisesRegex(ValueError,'intersects'):
            self.resolve(b,[c],[{**volume,'rise':3}])
        with self.assertRaisesRegex(ValueError,'intersects'):
            self.resolve(b,[c,{**c,'id':'second'}])
        glazing = dict(faces={'outer':3},sill=1,height=2,margin=.3,frameWidth=.1,projection=.12)
        with self.assertRaisesRegex(ValueError,'intersects'):
            self.resolve(b,[c],[{**volume,'glazing':glazing}])
        self.resolve(b,[c],[{**volume,'glazing':{**glazing,'sill':3.6}}])


if __name__ == '__main__':unittest.main()
