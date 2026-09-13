"""Library orientation follows located sources without changing mapped land use."""
import copy
import json
import unittest
from pathlib import Path

from shapely.affinity import rotate, translate
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union

from architecture_data import architectural_envelope


class LibraryEnvelopeTests(unittest.TestCase):
    def test_located_north_facade_and_south_extension_keep_original_court(self):
        root=Path(__file__).resolve().parents[1]
        b=next(x for x in json.loads((root/'public/data/buildings.json').read_text())
               if x['landmark']=='library')
        original=copy.deepcopy(b)
        e=architectural_envelope(b)
        self.assertEqual(b,original)
        mapped=Polygon(b['polygons'][0][0],b['polygons'][0][1:])
        local=translate(rotate(mapped,-e['angle'],origin=e['origin'],use_radians=True),
                        -e['origin'][0],-e['origin'][1])
        shapes=[unary_union([Polygon(p[0],p[1:]) for p in part['polygons']]) for part in e['parts']]
        self.assertLess(unary_union(shapes).symmetric_difference(local).area,1e-8)
        for i,a in enumerate(shapes):
            for bshape in shapes[i+1:]:self.assertLess(a.intersection(bshape).area,1e-8)
        for xy in [(0,-4),(5,-4),(0,-9),(8,-9)]:
            self.assertFalse(unary_union(shapes).covers(Point(*xy)))
        def part_at(x,y):
            return next(part for part,shape in zip(e['parts'],shapes) if shape.covers(Point(x,y)))
        south=part_at(0,-32);north=part_at(0,10)
        self.assertEqual(south['levels'],11)
        self.assertEqual(north['levels'],6)
        self.assertGreater(south['height'],north['height']+5)
        self.assertGreater(north['height'],part_at(-25,10)['height'])
        self.assertGreater(north['height'],part_at(25,10)['height'])
        self.assertIn('libraryConstruction2014',e['sourceRefs'])


if __name__=='__main__':unittest.main()
