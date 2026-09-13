import copy,unittest
from shapely.geometry import box,Point,LineString
from paving_data import derive_paving,context_revision
from shore_data import revision
class PavingDataTests(unittest.TestCase):
    def fixture(self):
        s={'id':'way/1','kind':'roads','insideCampus':True,'tags':{'highway':'pedestrian'},'vertices':[[0,0],[10,0],[10,6],[0,6]],'triangles':[0,1,2,0,2,3]}
        c={'id':'example','surfaceId':s['id'],'surfaceRevision':revision(s['vertices']),'joinEdges':[3],'joinFeather':3,'meshStep':2,'contactDepth':1,'contactSideMargin':.5,'joinOverlap':.15,'burial':.06,'sourceRefs':['osm'],'evidence':dict.fromkeys(['location','surface','dimensions','excludedDetails'],'documented')}
        return c,s,box(-2,-1,0,7)
    def test_footprint_retained_and_real_road_opening_has_no_side_wall(self):
        c,s,n=self.fixture();before=copy.deepcopy(s);r=derive_paving(c,s,n,{'osm'})
        self.assertEqual(s,before);self.assertEqual(r['vertices'],s['vertices']);self.assertEqual(r['areaMeters2'],60)
        self.assertTrue(all(LineString(line).distance(Point(0,3))>1 for line in r['freeEdges']))
        self.assertEqual(r['joins'][0]['inward'],[1.,0.])
    def test_reversed_ring_retains_same_inward_contact(self):
        c,s,n=self.fixture();s['vertices'].reverse();c['surfaceRevision']=revision(s['vertices']);r=derive_paving(c,s,n,{'osm'})
        self.assertEqual(r['joins'][0]['inward'],[1.,-0.])
    def test_stale_invalid_unconnected_or_unknown_inputs_rejected(self):
        c,s,n=self.fixture()
        for key,value in [('surfaceRevision','stale'),('meshStep',float('nan')),('joinFeather',True),('joinEdges',[0]),('sourceRefs',['unknown'])]:
            bad=copy.deepcopy(c);bad[key]=value
            with self.assertRaises(ValueError):derive_paving(bad,s,n,{'osm'})
        bad=copy.deepcopy(s);bad['tags']['bridge']='yes'
        with self.assertRaises(ValueError):derive_paving(c,bad,n,{'osm'})
    def test_context_changes_with_final_road_overlay(self):
        self.assertNotEqual(context_revision([],{}, {},{'layers':[]},{}),context_revision([],{}, {},{'layers':[1]},{}))
if __name__=='__main__':unittest.main()
