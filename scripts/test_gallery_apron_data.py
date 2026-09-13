"""A gallery apron clears only its own open floor, never another building."""
import copy,unittest
from shapely.geometry import Polygon
from building_overrides import footprint_revision
from gallery_apron_data import derive_gallery_apron
class GalleryApronTests(unittest.TestCase):
 def fixture(self):
  f=dict(polygon=0,ring=0,edge=0,part='body',start=[0,0],end=[30,0],normal=[0,-1],rule={'openCorridor':{'firstLevel':0,'depth':1.8,'endInset':.3,'piers':{'bays':8,'width':.42,'depth':.5}}})
  b=dict(id='test',center=[15,5],polygons=[[[[0,0],[30,0],[30,10],[0,10],[0,0]]]],form={'facades':[f]})
  c=dict(id='gallery',type='gallery-apron',buildingId='test',footprintRevision=footprint_revision(b),facade={'polygon':0,'ring':0,'edge':0,'part':'body'},apronDepth=1,gradingFeather=2,groundClearance=.12,meshStep=.5,sourceRefs=['photo'],evidence={'presence':'Sourced open gallery'})
  return b,c
 def test_gallery_floor_mask_and_external_apron_have_distinct_extents(self):
  b,c=self.fixture();s,area,grading=derive_gallery_apron(c,[b],{'photo'})
  self.assertAlmostEqual(area.area,29.4);self.assertEqual(s['gradingStartY'],-1.8)
  body=Polygon(b['polygons'][0][0]);self.assertLess(area.intersection(body).area,1e-8);self.assertGreater(grading.intersection(body).area,29.4*1.8)
 def test_gallery_rejects_stale_closed_or_conflicting_anchors(self):
  b,c=self.fixture()
  for key,val in [('edge',False),('part','missing'),('ring',1)]:
   bad=copy.deepcopy(c);bad['facade'][key]=val
   with self.subTest(key=key),self.assertRaises(ValueError):derive_gallery_apron(bad,[b],{'photo'})
  b['form']['facades'][0]['rule']['openCorridor']['firstLevel']=1
  with self.assertRaises(ValueError):derive_gallery_apron(c,[b],{'photo'})
  b,c=self.fixture();other=dict(id='other',polygons=[[[[0,-2],[1,-2],[1,-1],[0,-1],[0,-2]]]])
  with self.assertRaises(ValueError):derive_gallery_apron(c,[b,other],{'photo'})
if __name__=='__main__':unittest.main()
