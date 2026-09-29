import copy
import unittest
from shapely.geometry import Polygon, Point
from shapely.affinity import rotate, translate
from slatted_roof_data import resolve_slatted_roof
from building_overrides import ROOT, load_catalogue, resolve_building, source_catalogue
import json


class SlattedRoofTests(unittest.TestCase):
    def setUp(self):
        self.polygons=[[[[0,0],[9,0],[9,16],[0,16],[0,0]]]]
        self.config={'edgeWidth':.8,'slatWidth':.3,'slatCount':7}
        self.columns=[{'center':[.4,.4]},{'center':[8.6,15.6]}]

    def test_openings_are_real_holes_and_fit_the_mapped_outline(self):
        roof=resolve_slatted_roof(self.polygons,self.config,self.columns)
        self.assertEqual(len(roof.interiors),8)
        self.assertLess(roof.area,Polygon(self.polygons[0][0]).area*.5)
        self.assertLess(roof.difference(Polygon(self.polygons[0][0])).area,1e-8)

    def test_rejects_invalid_counts_widths_and_closed_gaps(self):
        for key,values in [('slatCount',[True,0,1.5,25]),('edgeWidth',[False,0,-1,float('nan'),5]),('slatWidth',[float('inf'),2])]:
            for value in values:
                with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                    resolve_slatted_roof(self.polygons,{**self.config,key:value},self.columns)

    def test_rejects_holes_nonquadrilaterals_and_skewed_footprints(self):
        for polygons in [self.polygons+copy.deepcopy(self.polygons),[[self.polygons[0][0],[[2,2],[3,2],[3,3],[2,3],[2,2]]]],[[[[0,0],[9,0],[12,16],[0,16],[0,0]]]],[[[[0,0],[9,0],[4,5],[9,16],[0,16],[0,0]]]]]:
            with self.subTest(polygons=polygons),self.assertRaises(ValueError):
                resolve_slatted_roof(polygons,self.config,self.columns)

    def test_rejects_columns_ending_under_open_sky(self):
        with self.assertRaisesRegex(ValueError,'supporting beam'):
            resolve_slatted_roof(self.polygons,self.config,[{'center':[4.5,1.2]}])

    def test_solid_center_retains_only_side_openings_and_expected_area(self):
        roof=resolve_slatted_roof(self.polygons,{**self.config,'solidBays':[2,3,4,5]},self.columns)
        gap=(16-1.6-7*.3)/8
        self.assertEqual(len(roof.interiors),4)
        self.assertAlmostEqual(roof.area,9*16-4*(9-1.6)*gap)
        for i in range(8):
            center=Point(4.5,.8+i*(gap+.3)+gap/2)
            self.assertEqual(roof.covers(center),i in [2,3,4,5])

    def test_columns_can_meet_solid_bay_but_not_remaining_openings(self):
        cfg={**self.config,'solidBays':[2,3,4,5]}
        roof=resolve_slatted_roof(self.polygons,cfg,[{'center':[4.5,8]}])
        self.assertTrue(roof.covers(Point(4.5,8)))
        with self.assertRaisesRegex(ValueError,'supporting beam'):
            resolve_slatted_roof(self.polygons,cfg,[{'center':[4.5,1.2]}])

    def test_solid_bays_validate_indices_and_keep_an_opening(self):
        for solid in [None,True,{},[False],[2.0],[-1],[8],[2,2],list(range(8))]:
            with self.subTest(solid=solid),self.assertRaises(ValueError):
                resolve_slatted_roof(self.polygons,{**self.config,'solidBays':solid},self.columns)

    def test_end_bays_empty_option_and_rotated_outline(self):
        original=resolve_slatted_roof(self.polygons,self.config,self.columns)
        self.assertEqual(original.wkb,resolve_slatted_roof(self.polygons,{**self.config,'solidBays':[]},self.columns).wkb)
        cfg={**self.config,'solidBays':[0,7]}
        roof=resolve_slatted_roof(self.polygons,cfg,self.columns)
        shifted=translate(rotate(Polygon(self.polygons[0][0]),31,origin=(0,0)),50,-24)
        result=resolve_slatted_roof([[list(map(list,shifted.exterior.coords))]],cfg,[])
        expected=translate(rotate(roof,31,origin=(0,0)),50,-24)
        self.assertLess(result.symmetric_difference(expected).area,1e-8)
        self.assertEqual(len(result.interiors),6)

    def test_real_oblique_partition_preserves_all_exterior_intervals(self):
        b=next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']=='relation/11564999')
        r=resolve_building(b,load_catalogue()[b['id']],{s['id'] for s in source_catalogue()})
        frame=next(p for p in r['form']['parts'] if p['id']=='east-open-frame')
        self.assertEqual(len(frame['openBelow']['roofGeometry']['polygons'][0])-1,8)
        self.assertEqual(r['polygons'],b['polygons'])
        self.assertEqual(r['height'],48.1)
        # This oblique original east edge is split across two high sides and
        # a low lattice; GEOS partial intersections must not drop a side.
        fs=[f for f in r['form']['facades'] if (f['polygon'],f['ring'],f['edge'])==(0,0,10)]
        self.assertEqual(len(fs),3)
        self.assertEqual(sum(f['part']=='high-body' for f in fs),2)

    def test_curved_front_preserves_holes_back_edge_and_rotation(self):
        cfg={**self.config,'solidBays':[2,3,4,5],
             'frontCurve':{'from':.2,'to':.8,'inset':.8,'segments':24}}
        roof=resolve_slatted_roof(self.polygons,cfg,[])
        self.assertEqual(len(roof.interiors),4)
        self.assertFalse(roof.covers(Point(9,8)))
        self.assertTrue(roof.covers(Point(8.15,8)))
        self.assertTrue(roof.covers(Point(8.6,1)))
        self.assertFalse(roof.covers(Point(8,1)))  # Tail opening stays open.
        self.assertTrue(roof.covers(Point(0,8)))
        self.assertLess(roof.difference(Polygon(self.polygons[0][0])).area,1e-8)
        outline=translate(rotate(Polygon(self.polygons[0][0]),31,origin=(0,0)),50,-24)
        moved=resolve_slatted_roof([[list(map(list,outline.exterior.coords))]],cfg,[])
        expected=translate(rotate(roof,31,origin=(0,0)),50,-24)
        self.assertLess(moved.symmetric_difference(expected).area,1e-8)
        with self.assertRaisesRegex(ValueError,'supporting beam'):
            resolve_slatted_roof(self.polygons,cfg,[{'center':[8.6,8]}])

    def test_curved_front_rejects_invalid_dimensions_and_depth_loss(self):
        curve={'from':.2,'to':.8,'inset':.8,'segments':24}
        for update in [dict(inset=True),dict(inset=float('nan')),dict(inset=0),dict(inset=8.9),
                       {'from':-.1},{'from':.9},dict(segments=3),dict(segments=5),dict(segments=66),dict(extra=1)]:
            cfg={**self.config,'frontCurve':{**curve,**update}}
            with self.subTest(update=update),self.assertRaises(ValueError):
                resolve_slatted_roof(self.polygons,cfg,[])
        for bad in (None,{},True):
            with self.assertRaises(ValueError):
                resolve_slatted_roof(self.polygons,{**self.config,'frontCurve':bad},[])


if __name__=='__main__':unittest.main()
