"""Reject stale or conflicting short aprons and preserve mapped geometry."""
import copy,json,math,unittest
from pathlib import Path
from shapely.geometry import Polygon
from entry_apron_data import derive_entry_apron
from building_overrides import footprint_revision
class EntryApronTests(unittest.TestCase):
 def fixture(self):
  b={'id':'test','center':[0,2],'polygons':[[[[-5,0],[5,0],[5,5],[-5,5],[-5,0]]]],'form':{'entrances':[{'id':'south','center':[0,0],'bearing':180,'stairFlight':{'front':1.22,'width':6.2,'baseHeight':.04}}]}}
  c=dict(id='apron',type='entry-apron',buildingId='test',footprintRevision=footprint_revision(b),entranceId='south',apronDepth=1.4,gradingFeather=2,groundClearance=.12,meshStep=.5,sourceRefs=['photo'],evidence={'presence':'Sourced entry apron'})
  return b,c
 def test_apron_matches_stair_width_and_stays_outside_building(self):
  b,c=self.fixture();original=copy.deepcopy(b)
  s,area,grading=derive_entry_apron(c,[b],{'photo'})
  self.assertAlmostEqual(area.area,6.2*1.4);self.assertLess(grading.intersection(Polygon(b['polygons'][0][0])).area,1e-8);self.assertEqual(b,original)
  b['polygons']=[[[[-y,x] for x,y in b['polygons'][0][0]]]];b['form']['entrances'][0]['bearing']=90;c['footprintRevision']=footprint_revision(b)
  _,rotated,_=derive_entry_apron(c,[b],{'photo'});self.assertAlmostEqual(area.area,rotated.area)
 def test_apron_rejects_unknown_sources_dimensions_and_neighbors(self):
  b,c=self.fixture()
  for key,val in [('meshStep',True),('apronDepth',4),('groundClearance',float('nan')),('gradingFeather',0),('entranceId','missing'),('footprintRevision','stale'),('sourceRefs',['unknown'])]:
   bad=copy.deepcopy(c);bad[key]=val
   with self.subTest(key=key),self.assertRaises(ValueError):derive_entry_apron(bad,[b],{'photo'})
  neighbor={'id':'neighbor','polygons':[[[[-1,-1],[1,-1],[1,-3],[-1,-3],[-1,-1]]]]}
  with self.assertRaises(ValueError):derive_entry_apron(c,[b,neighbor],{'photo'})
if __name__=='__main__':unittest.main()
