"""Check skewed junction cuts against independent GIS differences and real scope."""
import json
import unittest
from pathlib import Path

from shapely.geometry import Polygon, Point, shape
from shapely.ops import transform, unary_union

from prepare_geodata import project
from road_display_cleanup import load_cuts, subtract

ROOT = Path(__file__).resolve().parents[1]


class RoadDisplayCleanupTests(unittest.TestCase):
    def test_sloping_surface_and_uvs_match_independent_difference(self):
        xy = [(-4, -3), (8, -3), (8, 9), (-4, 9)]
        surface = [(x, y, 2*x + 3*y + 7, x/4, y/4) for x, y in xy]
        mask = [(-2, 1), (5, -1), (9, 6), (1, 8)]
        fragments = subtract(surface, mask)
        expected = Polygon(xy).difference(Polygon(mask))
        actual = unary_union([Polygon([p[:2] for p in f]) for f in fragments])
        self.assertLess(actual.symmetric_difference(expected).area, 1e-8)
        for poly in fragments:
            self.assertGreater(Polygon([p[:2] for p in poly]).area, 1e-8)
            for x, y, z, u, v in poly:
                self.assertAlmostEqual(z, 2*x + 3*y + 7)
                self.assertAlmostEqual(u, x/4)
                self.assertAlmostEqual(v, y/4)
            self.assertEqual(subtract(poly, mask), [poly])

    def test_touching_and_disjoint_faces_remain_exact(self):
        poly = [(0, 0, 3), (2, 0, 4), (0, 2, 5)]
        for mask in [[(2, 0), (4, 0), (4, 4), (2, 4)],
                     [(4, 4), (6, 4), (6, 6), (4, 6)]]:
            self.assertEqual(subtract(poly, mask), [poly])

    def test_real_masks_leave_campus_gates_and_junction_centres(self):
        geo = json.loads((ROOT/'public/data/geography.geojson').read_text())
        campus = unary_union([transform(project, shape(f['geometry']))
                              for f in geo['features']
                              if f['id'] == 'campus' or f['properties'].get('kind') == 'campus-supplement'])
        cuts = load_cuts()
        mask = unary_union([Polygon(c['polygon']) for c in cuts])
        self.assertLess(mask.intersection(campus).area, 1e-8)
        # Junction centres and every mapped campus destination remain clear.
        anchors = json.loads((ROOT/'data/road-display-cleanup.json').read_text())['retainedProbes']
        for point in anchors:
            self.assertGreater(mask.distance(Point(point)), 1)
        landmarks = json.loads((ROOT/'public/data/landmarks.json').read_text())
        for landmark in landmarks:
            self.assertGreater(mask.distance(Point(landmark['center'])), 10)
        # Explicit former tail witnesses must fall inside their intended masks.
        for cut in cuts:
            self.assertTrue(Polygon(cut['polygon']).contains(Point(cut['removedProbe'])), cut['id'])

    def test_incremental_cut_selection_is_explicit(self):
        cuts = load_cuts(ids=['xiuxiang-west', 'daxue-east', 'xiuling-west-first-east'])
        self.assertEqual([c['id'] for c in cuts],
                         ['xiuxiang-west', 'daxue-east', 'xiuling-west-first-east'])
        with self.assertRaises(ValueError):
            load_cuts(ids=['misspelled-cut'])


if __name__ == '__main__':
    unittest.main()
