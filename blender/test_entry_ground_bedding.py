"""Rebuild the accepted rear shoulder even on a fresh, coarse DEM."""
import json
import math
import sys
import unittest
from pathlib import Path

from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'blender'))
from geometry import Mesh, material
from entry_ground_bedding import bed_forecourt, grade_rear_road_contact


class RearShoulderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        building = next(b for b in json.loads((ROOT / 'public/data/buildings.json').read_text())
                        if b['id'] == 'relation/11564999')
        cls.entry = building['form']['entrances'][0]
        cls.elevation = building['elevation']
        angle = math.radians(cls.entry['bearing'])
        cls.nx, cls.ny = math.sin(angle), math.cos(angle)
        cls.x, cls.y = cls.entry['center']
        paving = Mesh()
        for patch in cls.entry['recessedStairEntry']['landscape']['groundPatches']:
            for i in range(0, len(patch['triangles']), 3):
                paving.face([cls.point(*patch['vertices'][k])
                             for k in patch['triangles'][i:i + 3]], 0)
        cls.paving = BVHTree.FromPolygons(paving.v, paving.f)

    @classmethod
    def point(cls, w, d, h):
        return Vector((cls.x + cls.ny * w - cls.nx * d,
                       cls.y - cls.nx * w - cls.ny * d, cls.elevation + h))

    def test_rear_shoulder_continues_paving_before_feathering(self):
        # Both triangulations start from untouched, low soil. A large DEM face
        # must not turn the rear paving edge into a ~15 cm raised plinth.
        for divisions in (1, 4):
            with self.subTest(divisions=divisions):
                ground = Mesh()
                for i in range(divisions):
                    a, b = -25 + 57 * i / divisions, -25 + 57 * (i + 1) / divisions
                    ground.face([self.point(w, d, -1) for w, d in
                                 ((a, -27), (b, -27), (b, 3), (a, 3))], 7)
                result, _ = bed_forecourt(ground, self.entry, self.elevation, 7)
                tree = BVHTree.FromPolygons(result.v, result.f)
                for w in (-20.3, -18.5, 17.3, 19.7, 23, 25):
                    top, normal, _, _ = self.paving.ray_cast(self.point(w, -.38, 20), Vector((0, 0, -1)))
                    self.assertIsNotNone(top)
                    for d in (-.22, -.05):
                        q = self.point(w, d, 20)
                        hit, _, _, _ = tree.ray_cast(q, Vector((0, 0, -1)))
                        expected = top.z - (normal.x * (q.x - top.x) + normal.y * (q.y - top.y)) / normal.z - .04
                        self.assertAlmostEqual(hit.z, expected, delta=.002)
                    # The original terrain plane remains fixed at and beyond
                    # the outer boundary; the shoulder cannot raise the site.
                    for d in (1.201, 1.5, 2):
                        hit, _, _, _ = tree.ray_cast(self.point(w, d, 20), Vector((0, 0, -1)))
                        self.assertIsNotNone(hit, (w, d))
                        self.assertAlmostEqual(hit.z, self.elevation - 1, delta=.002)
                self.assertEqual(set(result.m), {7})

    def test_rear_road_meets_paving_without_filling_missing_road(self):
        road = Mesh()
        road.face([self.point(w, d, -1) for w, d in
                   ((22, -.29), (26, -.29), (26, 2), (22, 2))], 9)
        result, _ = grade_rear_road_contact(road, self.entry, self.elevation)
        tree = BVHTree.FromPolygons(result.v, result.f)
        down = Vector((0, 0, -1))
        for w in (23, 25):
            top, normal, _, _ = self.paving.ray_cast(self.point(w, -.38, 20), down)
            q = self.point(w, -.22, 20)
            hit, road_normal, _, _ = tree.ray_cast(q, down)
            expected = top.z - (normal.x * (q.x - top.x) + normal.y * (q.y - top.y)) / normal.z - .015
            self.assertAlmostEqual(hit.z, expected, delta=.002)
            self.assertLess((normal - road_normal).length, .01)
            hit = tree.ray_cast(self.point(w, 1.501, 20), down)[0]
            self.assertAlmostEqual(hit.z, self.elevation - 1, delta=.002)
        for w, d in ((21.9, 0), (26.1, 0), (24, -.4), (24, 2.1)):
            self.assertIsNone(tree.ray_cast(self.point(w, d, 20), down)[0])
        self.assertEqual(set(result.m), {9})

    def test_fresh_site_samples_current_terrain_for_its_bedding(self):
        from recessed_entry_ground import build_recessed_entry_ground
        site=next(s for s in json.loads((ROOT/'public/data/sites.json').read_text())['sites']
                  if s.get('type')=='recessed-entry-ground')
        site.pop('buildingElevation',None)
        colors={name:material('datum-test-'+name,(.5,.5,.5))
                for name in ('grass','stone','path','green','dark','white','glass')}
        sampled=[]
        def current_height(x,y):
            sampled.append([x,y])
            return 12.345
        terrain,_,_,_=build_recessed_entry_ground(site,colors,current_height,Mesh(),Mesh())
        self.assertEqual(sampled,[site['buildingCenter']])
        tree=BVHTree.FromPolygons(terrain.v,terrain.f)
        hit=tree.ray_cast(self.point(0,-11,30),Vector((0,0,-1)))[0]
        self.assertIsNotNone(hit)
        # The accepted approach is 2.8 m above the host; soil is 4 cm below it.
        self.assertAlmostEqual(hit.z,12.345+2.8-.04,delta=.001)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RearShoulderTests)
    if not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful():
        raise SystemExit(1)
