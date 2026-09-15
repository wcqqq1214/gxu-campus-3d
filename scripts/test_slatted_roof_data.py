import copy
import unittest
from shapely.geometry import Polygon
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


if __name__=='__main__':unittest.main()
