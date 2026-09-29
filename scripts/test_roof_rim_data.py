import copy
import unittest
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from building_overrides import resolve_parts


class RoofRimTests(unittest.TestCase):
    def fixture(self, profiled=False):
        polygons = [[[[0,0],[12,0],[12,8],[0,8],[0,0]]]]
        roof = dict(type='flat', rise=0, rim=dict(edges=[[0,0],[0,1],[0,2],[0,3]], width=.3, height=.4))
        if profiled:
            roof.update(type='profiled', rise=2, mesh=dict(vertices=[[0,0,0],[12,0,0],[12,8,2],[0,8,2]], triangles=[0,1,2,0,2,3]))
        part = dict(id='test', polygons=polygons, height=10, levels=3, roof=roof)
        return dict(polygons=polygons, height=10), part

    def resolve(self, building, part):
        return resolve_parts(building, [part], dict(type='flat', rise=0))[0]['roof']['rimGeometry']

    def test_continuous_inset_ring_tracks_surface_with_outward_walls(self):
        for profiled in (False, True):
            b, p = self.fixture(profiled); before = copy.deepcopy(p)
            result = self.resolve(b, p)
            tops = [Polygon([v[:2] for v in face]) for face in result['tops']]
            shape = unary_union(tops)
            self.assertAlmostEqual(shape.area, 96-11.4*7.4)
            self.assertAlmostEqual(sum(t.area for t in tops), shape.area)
            self.assertEqual(len(shape.interiors), 1)
            for face in result['tops']:
                a,c,d = face
                self.assertGreater((c[0]-a[0])*(d[1]-a[1])-(c[1]-a[1])*(d[0]-a[0]), 1e-9)
                for x,y,z in face:self.assertAlmostEqual(z, .4+(y/4 if profiled else 0))
            for face in result['walls']:
                a,c = face[:2]; x,y = (a[0]+c[0])/2,(a[1]+c[1])/2
                nx,ny = c[1]-a[1],a[0]-c[0]
                self.assertFalse(shape.contains(Point(x+nx*.001,y+ny*.001)))
                self.assertTrue(shape.contains(Point(x-nx*.001,y-ny*.001)))
            self.assertEqual(before, p)

    def test_selected_edges_leave_unselected_side_open_and_courtyard_untouched(self):
        b,p = self.fixture(True);p['roof']['rim']['edges']=[[0,0],[0,1],[0,3]]
        r=self.resolve(b,p);self.assertAlmostEqual(r['areaMeters2'],8.22)
        shape=unary_union([Polygon([v[:2] for v in f]) for f in r['tops']])
        self.assertFalse(shape.contains(Point(6,7.9)))
        b,p=self.fixture();hole=[[4,3],[4,5],[8,5],[8,3],[4,3]]
        p['polygons'][0].append(hole)
        r=self.resolve(b,p)
        self.assertAlmostEqual(unary_union([Polygon([v[:2] for v in f]) for f in r['tops']]).intersection(Polygon(hole)).area,0)

    def test_rejects_bad_dimensions_anchors_and_unsupported_roofs(self):
        for key,value in [('width',True),('width',float('nan')),('height',0),('height',2),('edges',[]),('edges',[[0,0],[0,0]]),('edges',[[0,99]]),('edges',[[True,0]])]:
            b,p=self.fixture();p['roof']['rim'][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):self.resolve(b,p)
        b,p=self.fixture();p['roof'].update(type='hipped',rise=2)
        with self.assertRaisesRegex(ValueError,'continuous'):self.resolve(b,p)
