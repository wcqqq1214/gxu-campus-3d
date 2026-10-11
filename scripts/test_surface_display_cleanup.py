"""Check the screenshot-directed sports removals against prepared feature geometry."""
import json
import unittest
from pathlib import Path

from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

from road_display_cleanup import load_cuts

ROOT = Path(__file__).resolve().parents[1]


class SurfaceDisplayCleanupTests(unittest.TestCase):
    def test_masks_remove_only_the_three_marked_surfaces(self):
        cuts = load_cuts(filename='surface-display-cleanup.json')
        surfaces = json.loads((ROOT/'public/data/surfaces.json').read_text())
        masks = unary_union([Polygon(c['polygon']) for c in cuts])
        intended = {sid for c in cuts for sid in c['surfaceIds']}
        affected = set()
        shapes = {}
        for surface in surfaces:
            if surface['kind'] != 'sports' or not surface['vertices']:
                continue
            vertices, triangles = surface['vertices'], surface['triangles']
            shape = unary_union([Polygon([vertices[k] for k in triangles[i:i+3]])
                                 for i in range(0, len(triangles), 3)])
            shapes[surface['id']] = shape
            if shape.intersection(masks).area > 1e-6:
                affected.add(surface['id'])
                self.assertLess(shape.difference(masks).area, 1e-6)
        self.assertEqual(affected, intended)
        self.assertEqual(len(affected), 3)
        for cut in cuts:
            selected = unary_union([shapes[sid] for sid in cut['surfaceIds']])
            for point in cut['removedProbes']:
                self.assertTrue(selected.contains(Point(point)))


if __name__ == '__main__':
    unittest.main()
