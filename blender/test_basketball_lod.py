"""Geometry contracts for court LODs: simplify hardware, retain the court."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from basketball import court_model


class CourtLODTests(unittest.TestCase):
    def test_only_net_and_ring_change_at_distance(self):
        names = ['courtGreen', 'courtKey', 'sportWhite', 'courtMetal', 'courtFrame',
                 'courtGlass', 'courtOrange', 'goalNet']
        colors = {name: i for i, name in enumerate(names)}
        court = dict(elevation=1.2, rotation=.3, center=[17, -29])
        near, far = [court_model(court, colors, detail) for detail in [True, False]]
        def faces(mesh, name):
            return [[mesh.v[i] for i in f] for f, material in zip(mesh.f, mesh.m)
                    if material == colors[name]]
        for name in names:
            if name not in ['courtOrange', 'goalNet']:
                self.assertEqual(faces(near, name), faces(far, name), name)
        self.assertTrue(faces(near, 'goalNet'))
        self.assertFalse(faces(far, 'goalNet'))
        self.assertLess(len(faces(far, 'courtOrange')), len(faces(near, 'courtOrange')) / 4)
        # Top and bottom of the 18 mm tube remain at the same world heights.
        for mesh, count in [(near, 320), (far, 64)]:
            orange = faces(mesh, 'courtOrange')
            ring = [v[2] for start in [6, count + 12]
                    for f in orange[start:start + count] for v in f]
            self.assertAlmostEqual(max(ring), 1.225 + 3.05)
            self.assertAlmostEqual(min(ring), 1.225 + 3.032)


unittest.main(argv=[sys.argv[0]])
