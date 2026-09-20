import copy
import unittest
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from facade_panels_data import validate_panels, resolve_round_window_walls
from building_overrides import resolve_facades


class RoundWindowWallTests(unittest.TestCase):
    def panel(self):
        return dict(id='round',type='round-window-wall',**{'from':.1,'to':.9},bottom=4,top=19,columns=1,rows=1,frameWidth=.07,depth=.1,openings=[dict(t=.65,height=h,radius=.55) for h in [5,8,11,14,17]])

    def test_triangulated_wall_has_real_disjoint_holes(self):
        p=self.panel();before=copy.deepcopy(p);validate_panels([p],10,20,6)
        g=resolve_round_window_walls([p],10)['round'];rings=g['rings'];xy=[v for ring in rings for v in ring]
        faces=[Polygon([xy[j] for j in g['triangles'][i:i+3]]) for i in range(0,len(g['triangles']),3)]
        wall=Polygon(rings[0],rings[1:]);union=unary_union(faces)
        self.assertLess(union.symmetric_difference(wall).area,1e-9)
        self.assertLess(abs(sum(f.area for f in faces)-wall.area),1e-9)
        for h in [5,8,11,14,17]:self.assertFalse(union.covers(Point(5.2,h-4)))
        self.assertEqual(p,before)

    def test_rejects_outside_overlapping_nonfinite_and_unbounded_openings(self):
        invalid=[[],[{}],[dict(t=True,height=6,radius=.5)],[dict(t=.5,height=float('nan'),radius=.5)],
                 [dict(t=.5,height=5,radius=3)],[dict(t=0,height=5,radius=.5)],
                 [dict(t=.5,height=4.5,radius=.5)],[dict(t=.5,height=19,radius=.5)],
                 [dict(t=.5,height=5,radius=.5)]*2,[dict(t=.5,height=5,radius=.5)]*17,
                 [dict(t=.5,height=5,radius=.5,unknown=1)]]
        for openings in invalid:
            p=self.panel();p['openings']=openings
            with self.subTest(openings=openings),self.assertRaises(ValueError):validate_panels([p],10,20,6)
        p=self.panel();p['columns']=2
        with self.assertRaises(ValueError):validate_panels([p],10,20,6)

    def test_resolution_attaches_geometry_without_mutating_input_and_leaves_old_panels_alone(self):
        b={'id':'fixture','polygons':[[[[0,0],[10,0],[10,10],[0,10],[0,0]]]]}
        form={'parts':[],'height':20,'levels':6,'roof':{'type':'flat','rise':0}}
        rule=dict(polygon=0,ring=0,edge=0,balconies=False,panels=[self.panel()]);before=copy.deepcopy(rule)
        f=next(f for f in resolve_facades(b,form,[rule]) if f['rule'])
        self.assertIn('round',f['roundWindowWalls']);self.assertEqual(rule,before)
        p=self.panel();p.pop('openings');p['type']='glazing';rule['panels']=[p]
        self.assertEqual(resolve_round_window_walls([p],10),{})
        f=next(f for f in resolve_facades(b,form,[rule]) if f['rule'])
        self.assertNotIn('roundWindowWalls',f)
