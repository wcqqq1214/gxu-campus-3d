"""Street-side walks must stay on their own level where Bocui Road descends."""

import json
import sys
import unittest
from pathlib import Path

from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'blender'))
from geometry import Mesh
from infrastructure import residence_fence_panel
from west_dorm_garden import WALK_WIDTH, approach, front_section, front_walk


def surface(mesh):
    return BVHTree.FromPolygons(mesh.v, mesh.f)


class ResidenceGrades(unittest.TestCase):
    def test_west_five_approach_meets_upper_walk(self):
        b = next(
            row
            for row in json.loads((ROOT / 'public/data/buildings.json').read_text())
            if row['id'] == 'way/759158608'
        )
        colors = {'path': 0, 'stone': 1, 'grass': 2}
        entry = Mesh()
        approach(entry, b, b['elevation'], colors, 5)
        apron, sidewalk = surface(entry), surface(front_walk(colors))
        for offset in (-0.9, 0, 0.9):
            x = b['form']['entrances'][0]['center'][0] + offset
            inner_edge = front_section(x)[0] + WALK_WIDTH
            a = apron.ray_cast((x, inner_edge + 0.03, 15), (0, 0, -1))[0]
            c = sidewalk.ray_cast((x, inner_edge - 0.10, 15), (0, 0, -1))[0]
            self.assertIsNotNone(a)
            self.assertIsNotNone(c)
            self.assertLess(abs(a.z - c.z), 0.04)
            self.assertIsNone(apron.ray_cast((x, -582, 15), (0, 0, -1))[0])
        # The independently streamed crossing owns its original walking surface.
        self.assertIsNone(sidewalk.ray_cast((42, -584.2, 15), (0, 0, -1))[0])

    def test_fence_follows_both_ends_of_a_sloping_road_bay(self):
        colors = dict.fromkeys(
            (
                'wallStone',
                'curb',
                'pavingRed',
                'grass',
                'fenceIron',
                'dormStoneWarm',
                'dormStonePale',
            ),
            0,
        )
        for detail in (False, True):
            mesh = Mesh()
            residence_fence_panel(
                mesh,
                (92, -485, 3),
                (95, -485, 3.3),
                (7.7, 7.7),
                ((1, 0), (1, 0)),
                colors,
                detail,
            )
            fence = surface(mesh)
            for x, expected in ((92.5, 5.04), (94.5, 5.24)):
                rail = fence.ray_cast((x, -477.3, 8), (0, 0, -1))[0]
                self.assertIsNotNone(rail)
                self.assertAlmostEqual(rail.z, expected + 0.045, delta=0.015)
            # Nothing should project from the enclosure over the walking lane.
            self.assertIsNone(fence.ray_cast((93, -479, 8), (0, 0, -1))[0])


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]])
