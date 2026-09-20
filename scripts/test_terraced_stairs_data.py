"""Reject misplaced or disconnected two-flight stairs and test rotated anchors."""
import copy
import unittest
from shapely.geometry import Polygon
from building_overrides import footprint_revision, resolve_building
from terraced_stairs_data import validate_terraced_stairs_context


class TerracedStairTests(unittest.TestCase):
    def fixture(self):
        b=dict(id='way/stairs',name='fixture',category='academic',landmark=None,
               tags={'building':'university'},polygons=[[[[0,0],[30,0],[30,20],[0,20],[0,0]]]])
        c=dict(polygon=0,ring=0,edge=0,t=.5,width=12,baseHeight=0,intermediateHeight=1.62,
               landingHeight=2.52,lowerRisers=9,upperRisers=5,tread=.32,landingDepth=1.2,
               intermediateDepth=1.6,upperWidth=4.8,upperOffset=-3.2)
        return b,c

    def resolve(self,b,c,**extra):
        values=dict(terracedStairs=c,**extra)
        return resolve_building(b,dict(values,footprintRevision=footprint_revision(b),evidence={
            k:dict(status='estimated',sourceRefs=[],note='fixture') for k in values}))

    def test_rotation_support_footprint_and_idempotence(self):
        b,c=self.fixture();r=self.resolve(b,c);s=r['form']['terracedStairs']
        self.assertEqual(s['normal'],[0,-1]);self.assertAlmostEqual(s['front'],6.64)
        self.assertEqual(r['polygons'],b['polygons']);self.assertEqual(r,self.resolve(r,c))
        self.assertAlmostEqual(Polygon(s['footprint']).intersection(Polygon(b['polygons'][0][0])).area,0)
        self.assertNotIn('terracedStairs',resolve_building(r)['form'])
        # Rotate the entire mapped outline without changing local stair data.
        b['polygons']=[[[[-y,x] for x,y in b['polygons'][0][0]]]]
        rotated=self.resolve(b,c)['form']['terracedStairs']
        self.assertEqual(rotated['normal'],[1,0])
        self.assertAlmostEqual(Polygon(rotated['footprint']).area,12*6.64)

    def test_reject_bad_anchor_dimensions_and_unusable_rises(self):
        b,c=self.fixture()
        for key,value in [('ring',1),('edge',True),('edge',4),('t',0),('width',31),
                          ('upperWidth',12),('upperOffset',5),('baseHeight',-1),
                          ('intermediateHeight',.5),('landingHeight',1),('upperRisers',True),
                          ('lowerRisers',2),('tread',.1),('landingDepth',0),('intermediateDepth',.4),
                          ('upperOffset',float('nan')),('width',True),('extra',1)]:
            with self.subTest(key=key),self.assertRaises(ValueError):self.resolve(b,{**c,key:value})

    def test_reject_low_and_split_supports(self):
        b,c=self.fixture()
        parts=[dict(id='left',polygons=[[[[0,0],[15,0],[15,20],[0,20],[0,0]]]],height=16.5,levels=5),
               dict(id='right',polygons=[[[[15,0],[30,0],[30,20],[15,20],[15,0]]]],height=16.5,levels=5)]
        with self.assertRaisesRegex(ValueError,'one solid supporting'):self.resolve(b,c,parts=parts)
        with self.assertRaisesRegex(ValueError,'one solid supporting'):self.resolve(b,c,height=4,levels=1)

    def test_reject_neighbor_and_existing_platform_collisions(self):
        b,c=self.fixture();r=self.resolve(b,c)
        neighbor=dict(id='way/other',polygons=[[[[10,-5],[20,-5],[20,-2],[10,-2],[10,-5]]]])
        with self.assertRaisesRegex(ValueError,'intersect building'):validate_terraced_stairs_context([r,neighbor])
        neighbor['polygons']=[[[[40,40],[45,40],[45,45],[40,45],[40,40]]]]
        validate_terraced_stairs_context([r,neighbor])
        for kind in ('attachedPortico','stairFlight'):
            bad=copy.deepcopy(r);bad['form']['entrances'].append({kind:{'footprint':r['form']['terracedStairs']['footprint']}})
            with self.assertRaisesRegex(ValueError,'entrance platform'):validate_terraced_stairs_context([bad])


if __name__=='__main__':unittest.main()
