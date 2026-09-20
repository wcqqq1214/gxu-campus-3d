import unittest
from shapely.geometry import Polygon, LineString
from building_overrides import footprint_revision, resolve_building


class RoofCrownTests(unittest.TestCase):
    def fixture(self):
        b=dict(id='way/crown',name='fixture',category='academic',landmark=None,tags={'building':'university'},
               polygons=[[[[0,0],[0,30],[-30,30],[-30,0],[0,0]]]])
        c=dict(part='body',polygon=0,vertex=0,width=15,depth=3.8,rise=6,glassBottom=16.2,glassTop=22.3,
               frontEnd=14.8,sideEnd=3.7,columns=6,sideColumns=2,rows=4,screenRise=8.4,
               screenBottomDepth=8,screenTopDepth=6.2,screenThickness=.35)
        return b,c

    def resolve(self,b,c):
        return resolve_building(b,dict(roofCrown=c,footprintRevision=footprint_revision(b),
            evidence={'roofCrown':dict(status='estimated',sourceRefs=[],note='fixture')}))

    def test_rotation_idempotence_and_parapet_cut(self):
        b,c=self.fixture();r=self.resolve(b,c);crown=r['form']['roofCrown']
        self.assertEqual(r,self.resolve(r,c));self.assertEqual(b['polygons'],r['polygons'])
        self.assertNotIn('roofCrown',resolve_building(r)['form'])
        footprint=Polygon(crown['footprint'])
        self.assertTrue(Polygon(b['polygons'][0][0]).covers(footprint))
        for edge in crown['retainedParapetEdges']:
            self.assertLess(LineString(edge).intersection(footprint).length,1e-6)
        angle=.47
        import math
        b['polygons']=[[[[x*math.cos(angle)-y*math.sin(angle),x*math.sin(angle)+y*math.cos(angle)] for x,y in b['polygons'][0][0]]]]
        self.assertAlmostEqual(Polygon(self.resolve(b,c)['form']['roofCrown']['footprint']).area,footprint.area)

    def test_reject_bad_fields_dimensions_and_glazing(self):
        b,c=self.fixture()
        for key,value in [('vertex',100),('polygon',1),('vertex',True),('part','unknown'),('width',31),
                          ('depth',9),('rise',0),('screenRise',5),('screenTopDepth',9),('screenThickness',0),
                          ('glassBottom',1),('glassTop',24),('frontEnd',15),('sideEnd',4),('rows',True),
                          ('columns',0),('width',float('nan')),('unknown',1)]:
            with self.subTest(key=key),self.assertRaises(ValueError):self.resolve(b,{**c,key:value})

    def test_reject_courtyard_and_concave_corner(self):
        b,c=self.fixture()
        b['polygons'][0].append([[-2,2],[-2,3],[-3,3],[-3,2],[-2,2]])
        with self.assertRaisesRegex(ValueError,'support|courtyard'):self.resolve(b,c)
        b,c=self.fixture();b['polygons']=[[[[0,0],[0,30],[-30,30],[-30,10],[-10,10],[-10,0],[0,0]]]]
        c.update(vertex=4,width=5,depth=3,frontEnd=4.8,sideEnd=2.8,screenTopDepth=4,screenBottomDepth=5)
        with self.assertRaisesRegex(ValueError,'support|courtyard'):self.resolve(b,c)

    def test_side_wall_continues_roof_slope_and_requires_backing(self):
        b,c=self.fixture();c['sideWall']=dict(baseHeight=-.5,projection=.08)
        r=self.resolve(b,c)['form']['roofCrown'];sw=r['sideWall']
        self.assertAlmostEqual(sw['bottomDepth'],8+17*1.8/8.4)
        for bad in [dict(baseHeight=-1,projection=.08),dict(baseHeight=16,projection=.08),
                    dict(baseHeight=0,projection=.5),dict(baseHeight=0,projection=True),
                    dict(baseHeight=0,projection=float('nan')),dict(baseHeight=0),{}]:
            with self.subTest(bad=bad),self.assertRaises(ValueError):self.resolve(b,{**c,'sideWall':bad})
        # The roof-level screen fits; a setback below its wider foot does not.
        b['polygons']=[[[[0,0],[0,30],[-30,30],[-30,8.5],[-8.5,8.5],[-8.5,0],[0,0]]]]
        without=dict(c);without.pop('sideWall');self.resolve(b,without)
        with self.assertRaisesRegex(ValueError,'corner edge|complete solid facade'):self.resolve(b,c)


if __name__=='__main__':unittest.main()
