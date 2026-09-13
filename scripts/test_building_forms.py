"""Architectural invariants: floor counts, roof coverage and rotation symmetry."""
import copy
import hashlib
import json
import math
import unittest
from pathlib import Path
from shapely.geometry import Polygon
from shapely.ops import unary_union
from building_forms import resolve_form, roof_geometry, fallback_entrances

ROOT = Path(__file__).resolve().parents[1]


class BuildingFormTests(unittest.TestCase):
    def test_refinement_preserves_every_existing_footprint(self):
        baseline = json.loads((ROOT/'docs/model-checks/refinement/footprint-baseline.json').read_text())['footprints']
        buildings = json.loads((ROOT/'public/data/buildings.json').read_text())
        self.assertEqual(set(baseline), {b['id'] for b in buildings})
        for b in buildings:
            digest = hashlib.sha256(json.dumps(b['polygons'],separators=(',',':')).encode()).hexdigest()
            self.assertEqual(digest, baseline[b['id']], b['id'])

    def building(self, polygons=None):
        return {'id': 'way/test', 'name': '测试教学楼', 'category': 'academic',
                'height': 30, 'levels': 7, 'tags': {'building:levels': '7'},
                'polygons': polygons or [[[[0,0],[30,0],[30,10],[0,10],[0,0]]]]}

    def test_levels_do_not_get_rederived_from_height(self):
        b = self.building()
        self.assertEqual(resolve_form(b)['levels'], 7)
        self.assertNotEqual(resolve_form(b)['levels'], round(b['height']/3.3))
        for value in (0, -2, float('nan'), float('inf'), True, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                resolve_form({**b, 'levels': value})

    def test_dining_use_does_not_select_residential_facade(self):
        b = self.building(); b.update(name='南苑第二餐厅', category='living')
        self.assertEqual(resolve_form(b)['archetype'], 'canteen')
        b.update(name='学生宿舍', tags={'building':'dormitory'})
        self.assertEqual(resolve_form(b)['archetype'], 'dormitory')
        self.assertEqual(resolve_form(b)['roof']['type'], 'flat')

    def check_coverage(self, polygons, roof):
        target = unary_union([Polygon(p[0], p[1:]) for p in polygons])
        projected = []
        for i in range(0, len(roof['triangles']), 3):
            points = [roof['vertices'][k] for k in roof['triangles'][i:i+3]]
            self.assertTrue(all(math.isfinite(v) for p in points for v in p))
            poly = Polygon([p[:2] for p in points])
            if poly.area > 1e-8: projected.append(poly)
        actual = unary_union(projected)
        self.assertLess(actual.symmetric_difference(target).area, 1e-5)
        self.assertLess(abs(sum(p.area for p in projected)-target.area), 1e-5)
        self.assertGreater(max(p[2] for p in roof['vertices']), 0)

    def test_hipped_roof_keeps_concavities_and_inner_court_open(self):
        examples = [self.building()['polygons'],
            [[[[0,0],[30,0],[30,10],[10,10],[10,30],[0,30],[0,0]]]],
            [[[[0,0],[30,0],[30,30],[0,30],[0,0]], [[8,8],[8,22],[22,22],[22,8],[8,8]]]]]
        for polys in examples:
            with self.subTest(polygons=polys):
                self.check_coverage(polys, roof_geometry(polys, 'hipped', 2.3))
        fifth = next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']=='way/759129515')
        self.check_coverage(fifth['polygons'], roof_geometry(fifth['polygons'], 'hipped', 2.3))

    def test_rotating_rectangle_rotates_roof_and_entrance(self):
        b = self.building(); original = copy.deepcopy(b)
        angle = math.radians(31)
        def rotate(p): return [p[0]*math.cos(angle)-p[1]*math.sin(angle), p[0]*math.sin(angle)+p[1]*math.cos(angle)]
        b['polygons'] = [[[[*rotate(p)] for p in ring] for ring in poly] for poly in b['polygons']]
        a = roof_geometry(original['polygons'], 'hipped', 2.3)
        c = roof_geometry(b['polygons'], 'hipped', 2.3)
        self.check_coverage(b['polygons'], c)
        expected = sorted((round(rotate(p)[0],5),round(rotate(p)[1],5),round(p[2],5)) for p in a['vertices'])
        actual = sorted(tuple(round(v,5) for v in p) for p in c['vertices'])
        self.assertEqual(expected, actual)
        e = fallback_entrances(original['polygons'])[0]
        f = fallback_entrances(b['polygons'])[0]
        # Either equal-length opposite longest side is a valid *estimated*
        # fallback. In both cases its outward normal must point outside.
        poly = Polygon(b['polygons'][0][0]); bearing = math.radians(f['bearing'])
        from shapely.geometry import Point
        p = Point(f['center'][0]+math.sin(bearing),f['center'][1]+math.cos(bearing))
        self.assertFalse(poly.covers(p))
        self.assertEqual(e['status'], f['status'])


if __name__ == '__main__':
    unittest.main()
