import copy,unittest
import test_building_overrides as fixtures
from facade_panels_data import validate_panels
class PlatformEntryTrimTests(unittest.TestCase):
 def fixture(self):
  f=fixtures.BuildingOverrideTests();b,v=f.portico_fixture()
  for c in v['parts'][1]['openBelow']['columns']:c.update(shape='cylinder',finish='stone',base={'height':.55,'projection':.08,'capHeight':.08})
  v['entrances'][0]['recessDoor']={'frameWidth':.07,'leafCount':4,'lintelHeight':.12}
  return f,b,v
 def test_trim_keeps_anchors_and_stair_parameters(self):
  f,b,v=self.fixture();r=f.resolve(b,**v);self.assertEqual(r['polygons'],b['polygons']);e=r['form']['entrances'][0]
  self.assertEqual(e['center'],[15,0]);self.assertEqual(e['recessDoor']['leafCount'],4)
 def test_invalid_door_dimensions_and_conflicts_rejected(self):
  f,b,v=self.fixture()
  for k,values in [('frameWidth',[True,float('nan'),.2]),('leafCount',[True,1,5]),('lintelHeight',[.1,.4])]:
   for value in values:
    bad=copy.deepcopy(v);bad['entrances'][0]['recessDoor'][k]=value
    with self.subTest(k=k,value=value),self.assertRaises(ValueError):f.resolve(b,**bad)
  bad=copy.deepcopy(v);bad['entrances'][0]['width']=2.72
  with self.assertRaisesRegex(ValueError,'leaves or lintel'):f.resolve(b,**bad)
  del v['entrances'][0]['recess']
  with self.assertRaises(ValueError):f.resolve(b,**v)
 def test_base_bounds_and_route_include_cap_projection(self):
  f,b,v=self.fixture();v['parts'][1]['openBelow']['columns'][0]['center'][0]=8.45
  with self.assertRaisesRegex(ValueError,'footprint'):f.resolve(b,**v)
  f,b,v=self.fixture();v['parts'][1]['openBelow']['columns'][1]['center'][0]=13.92
  with self.assertRaisesRegex(ValueError,'central entrance route'):f.resolve(b,**v)
 def test_invalid_base_and_finish_rejected(self):
  f,b,v=self.fixture()
  for k,value in [('height',float('nan')),('projection',True),('capHeight',.2)]:
   bad=copy.deepcopy(v);bad['parts'][1]['openBelow']['columns'][0]['base'][k]=value
   with self.subTest(k=k),self.assertRaises(ValueError):f.resolve(b,**bad)
  for k,value in [('shape','box'),('finish','gold')]:
   bad=copy.deepcopy(v);bad['parts'][1]['openBelow']['columns'][0][k]=value
   with self.subTest(k=k),self.assertRaises(ValueError):f.resolve(b,**bad)
 def test_frame_finish_is_explicit_glazing_only(self):
  p=dict(id='test',type='glazing',**{'from':.1,'to':.9},bottom=3.2,top=5,columns=2,rows=1,frameWidth=.08,depth=.1)
  for finish in ['white','dark']:validate_panels([{**p,'frameFinish':finish}],10,6,2)
  for patch in [{'frameFinish':'red'},{'frameFinish':None},{'frameFinish':'dark','type':'lattice'}]:
   with self.subTest(patch=patch),self.assertRaises(ValueError):validate_panels([{**p,**patch}],10,6,2)
