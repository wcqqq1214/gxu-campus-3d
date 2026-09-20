import copy,math,unittest
from shapely.geometry import Polygon,LineString
from building_overrides import resolve_building,footprint_revision

class FlushReturnTests(unittest.TestCase):
 def fixture(self):
  b=dict(id='way/return',name='fixture',category='academic',landmark=None,tags={},polygons=[[[[0,0],[20,0],[20,20],[0,20],[0,0]]]])
  p=dict(floorHeight=.1,glazingHeight=7.2,splitHeight=3.6,bays=3,pierWidth=.65,pierDepth=.3,doorWidth=3.2,doorHeight=2.7,frameWidth=.09,canopy=dict(width=18,depth=2,thickness=.6),returnGlazing=dict(side='start',depth=3.8,bays=2,pierWidth=.4,pierDepth=.3,beamHeight=.45,canopyProjection=1.4))
  e=dict(id='main',polygon=0,ring=0,edge=0,t=.5,width=16,primary=True,flushEntrance=p)
  return b,dict(entrances=[e],evidence={'entrances':dict(status='estimated',sourceRefs=[],note='fixture')})
 def resolve(self,b,r):return resolve_building(b,{**r,'footprintRevision':footprint_revision(b)})
 def test_rotated_corner_connected_canopy_and_idempotence(self):
  for side in ('start','end'):
   b,r=self.fixture();r['entrances'][0]['flushEntrance']['returnGlazing']['side']=side
   for angle in (0,.43):
    q=copy.deepcopy(b);q['polygons']=[[[[x*math.cos(angle)-y*math.sin(angle),x*math.sin(angle)+y*math.cos(angle)] for x,y in b['polygons'][0][0]]]]
    out=self.resolve(q,r);self.assertEqual(out,self.resolve(out,r));self.assertEqual(out['polygons'],q['polygons'])
    p=out['form']['entrances'][0]['flushEntrance'];c=p['returnGlazing'];shape=Polygon(c['canopyGeometry']['polygons'][0][0]);body=Polygon(q['polygons'][0][0])
    self.assertLess(shape.intersection(body).area,1e-6)
    self.assertAlmostEqual(LineString(c['frontJoint']).length,2)
    self.assertGreater(shape.boundary.intersection(LineString(c['frontJoint']).buffer(1e-7)).length,1.99)
    self.assertEqual(len(out['form']['entrances']),1)
 def test_invalid_dimensions_missing_canopy_and_overlapping_wing(self):
  b,r=self.fixture()
  for key,value in [('side','other'),('depth',20),('bays',True),('bays',4),('pierWidth',.1),('pierDepth',2),('beamHeight',float('nan')),('canopyProjection',True),('extra',1)]:
   bad=copy.deepcopy(r);bad['entrances'][0]['flushEntrance']['returnGlazing'][key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):self.resolve(b,bad)
  bad=copy.deepcopy(r);bad['entrances'][0]['flushEntrance'].pop('canopy')
  with self.assertRaisesRegex(ValueError,'front canopy'):self.resolve(b,bad)
  b['polygons'].append([[[-1.2,1],[-.5,1],[-.5,2],[-1.2,2],[-1.2,1]]])
  with self.assertRaisesRegex(ValueError,'overlaps another wing'):self.resolve(b,r)
 def test_conflicting_low_panels_rejected_upper_glass_allowed(self):
  b,r=self.fixture();r['facadeRules']=[dict(polygon=0,ring=0,edge=3,balconies=False,panels=[dict(id='side',type='glazing',**{'from':.82,'to':.99},bottom=6,top=10,columns=2,rows=2,frameWidth=.07,depth=.1)])]
  r['evidence']['facadeRules']=dict(status='estimated',sourceRefs=[],note='fixture')
  with self.assertRaisesRegex(ValueError,'overlap the portal return'):self.resolve(b,r)
  r['facadeRules'][0]['panels'][0]['bottom']=7.8
  self.resolve(b,r)

if __name__=='__main__':unittest.main()
