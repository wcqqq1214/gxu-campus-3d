import math
import unittest
from shapely.geometry import Polygon
from building_overrides import resolve_building
from switchback_stairs_data import resolve_switchback_stairs, validate_stair_study_neighbors


class SwitchbackStairStudyTests(unittest.TestCase):
    def fixture(self):
        b=resolve_building(dict(id='way/stair-study',name='fixture',category='academic',landmark=None,
            tags={'building':'university','building:levels':'7'},
            polygons=[[[[0,0],[40,0],[40,20],[0,20],[0,0]]]]))
        c=dict(polygon=0,ring=0,edge=0,t=.5,flightWidth=1.4,gap=.2,landingDepth=.95,tread=.28,
               risers=10,levels=[round(i*3.3,2) for i in range(8)],slabThickness=.3,
               railHeight=1.1,railThickness=.15,firstLane=1)
        return b,c

    def test_anchor_winding_rotation_and_body_clearance(self):
        b,c=self.fixture();s=resolve_switchback_stairs(b,c)
        self.assertAlmostEqual(s['width'],3);self.assertAlmostEqual(s['depth'],4.42)
        self.assertAlmostEqual(Polygon(s['footprint']).area,13.26)
        self.assertEqual(s['normal'],[0,-1])
        b['polygons'][0][0].reverse();r=resolve_switchback_stairs(b,{**c,'edge':3})
        self.assertLess(Polygon(r['footprint']).symmetric_difference(Polygon(s['footprint'])).area,1e-7)
        b,c=self.fixture();a=.67
        b['polygons'][0][0]=[[x*math.cos(a)-y*math.sin(a),x*math.sin(a)+y*math.cos(a)] for x,y in b['polygons'][0][0]]
        r=resolve_switchback_stairs(b,c)
        self.assertAlmostEqual(Polygon(r['footprint']).area,13.26)
        self.assertLess(Polygon(r['footprint']).intersection(Polygon(b['polygons'][0][0])).area,1e-7)

    def test_invalid_dimensions_support_and_levels(self):
        b,c=self.fixture()
        for key,value in [('polygon',True),('edge',4),('ring',1),('risers',True),('risers',7),
                          ('firstLane',True),('firstLane',0),('t',.01),('tread',float('nan')),
                          ('flightWidth',1),('railThickness',.3),('gap',True),('levels',[0,0]),
                          ('levels',[0,3.3,2]),('levels',[0,float('inf')]),('levels',[0,30]),
                          ('levels',[]),('levels',[0,True]),('slabThickness',.2),('extra',1)]:
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                resolve_switchback_stairs(b,{**c,key:value})
        for form in ({**b['form'],'height':10},{**b['form'],'parts':[{}]},
                     {**b['form'],'stairTower':{}},{**b['form'],'roof':{'type':'hipped'}}):
            with self.subTest(form=form),self.assertRaises(ValueError):
                resolve_switchback_stairs({**b,'form':form},c)

    def test_neighbor_overlap_and_contact(self):
        b,c=self.fixture();s=resolve_switchback_stairs(b,c)
        neighbor=dict(id='way/neighbor',polygons=[[[[18,-6],[22,-6],[22,-4],[18,-4],[18,-6]]]])
        with self.assertRaisesRegex(ValueError,'neighbor'):validate_stair_study_neighbors(b['id'],s,[b,neighbor])
        neighbor['polygons']=[[[[18,-6],[22,-6],[22,-4.42],[18,-4.42],[18,-6]]]]
        validate_stair_study_neighbors(b['id'],s,[b,neighbor])


if __name__=='__main__':unittest.main()
