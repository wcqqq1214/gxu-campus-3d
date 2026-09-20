import copy,math,unittest
from shapely.geometry import Polygon,LineString
from building_overrides import resolve_building,footprint_revision


class GableScreenTests(unittest.TestCase):
    def fixture(self):
        b=dict(id='way/gable',name='fixture',category='academic',landmark=None,tags={'building':'university'},
               polygons=[[[[0,0],[0,20],[-20,20],[-20,0],[0,0]]]])
        c=dict(part='body',polygon=0,edge=0,thickness=.3,shoulderRise=.8,peakRise=3.6,peakT=.5,
               window=dict(centerT=.5,width=1.8,height=1.8,bottom=.6,frameWidth=.09))
        return b,c

    def resolve(self,b,c):
        return resolve_building(b,dict(gableScreen=c,footprintRevision=footprint_revision(b),
            evidence={'gableScreen':dict(status='estimated',sourceRefs=[],note='fixture')}))

    def test_real_hole_idempotence_and_parapet_replacement(self):
        b,c=self.fixture();original=copy.deepcopy(b);r=self.resolve(b,c);g=r['form']['gableScreen']
        self.assertEqual(b,original);self.assertEqual(r,self.resolve(r,c));self.assertNotIn('gableScreen',resolve_building(r)['form'])
        face=Polygon(g['wallGeometry']['polygons'][0][0],g['wallGeometry']['polygons'][0][1:])
        self.assertEqual(len(face.interiors),1)
        self.assertAlmostEqual(face.area+Polygon(g['opening']).area,Polygon(g['outline']).area)
        for edge in g['retainedParapetEdges']:self.assertLess(LineString(edge).intersection(Polygon(g['footprint'])).length,1e-6)
        self.assertEqual(r['form']['roof']['type'],'flat')

    def test_rotation_and_reversed_winding_preserve_support(self):
        b,c=self.fixture();area=Polygon(self.resolve(b,c)['form']['gableScreen']['footprint']).area
        for reverse in (False,True):
            rotated=copy.deepcopy(b);angle=.57
            ring=[[x*math.cos(angle)-y*math.sin(angle),x*math.sin(angle)+y*math.cos(angle)] for x,y in b['polygons'][0][0]]
            if reverse:ring.reverse()
            rotated['polygons']=[[ring]];g=self.resolve(rotated,{**c,'edge':3 if reverse else 0})['form']['gableScreen']
            self.assertAlmostEqual(Polygon(g['footprint']).area,area)
            self.assertTrue(Polygon(ring).buffer(1e-7).covers(Polygon(g['footprint'])))

    def test_invalid_profile_window_anchor_and_courtyard_rejected(self):
        b,c=self.fixture()
        for key,value in [('polygon',-1),('edge',True),('edge',100),('part','missing'),('thickness',float('nan')),('peakT',1),('peakRise',.9),('unknown',1)]:
            with self.subTest(key=key),self.assertRaises(ValueError):self.resolve(b,{**c,key:value})
        for key,value in [('width',4),('height',True),('bottom',2),('centerT',0),('frameWidth',.4)]:
            with self.subTest(key=key),self.assertRaises(ValueError):self.resolve(b,{**c,'window':{**c['window'],key:value}})
        b['polygons'][0].append([[-.1,5],[-.2,5],[-.2,6],[-.1,6],[-.1,5]])
        with self.assertRaisesRegex(ValueError,'support|courtyard'):self.resolve(b,c)


if __name__=='__main__':unittest.main()
