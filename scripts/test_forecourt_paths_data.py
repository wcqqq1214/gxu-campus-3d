import copy
import json
import unittest
from pathlib import Path
from shapely.geometry import Point, Polygon
from forecourt_paths_data import derive_forecourt_paths
from shore_data import effective_surfaces
from surroundings_data import surface_shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]


class ForecourtPathsTests(unittest.TestCase):
    def setUp(self):
        read = lambda n: json.loads((ROOT/'public/data'/f'{n}.json').read_text())
        self.buildings = read('buildings')
        infra, surround, roads = [read(n) for n in ('infrastructure', 'surroundings', 'campus-roads')]
        self.surface = next(s for s in effective_surfaces(read('surfaces'),
            [infra['surfaceOverrides'], surround['surfaceOverrides'], roads['surfaceOverrides']],
            set(infra['replaceSurfaceIds'])) if s['id'] == 'way/842784664')
        self.paving = next(p for p in json.loads((ROOT/'data/paving-overrides.json').read_text())['pavings'] if p['surfaceId'] == self.surface['id'])
        self.config = next(s for s in json.loads((ROOT/'data/site-overrides.json').read_text())['sites'] if s['id'] == 'civil-forecourt-garden')

    def derive(self, config=None, paving=None, buildings=None):
        return derive_forecourt_paths(config or self.config, buildings or self.buildings,
                                      self.surface, paving or self.paving, set(self.config['sourceRefs']))

    def test_ring_contacts_lawn_and_trunks(self):
        site, area, grading = self.derive()
        self.assertTrue(area.equals(grading))
        self.assertEqual(len(area.interiors), 1)
        self.assertGreater(site['contactLengthMeters'], 2.4)
        for xy in [(-491, -856.5), (-477, -856.5), (-484, -852), (-484, -861), (-496, -856.5), (-478, -847)]:
            self.assertTrue(area.covers(Point(xy)), xy)
        for xy in [(-484, -856.5), (-488, -856.5), (-491.2, -853.2), (-488.2, -864.5)]:
            self.assertFalse(area.buffer(.4).covers(Point(xy)), xy)
        vertices = site['pavingMesh']['vertices']; indices = site['pavingMesh']['triangles']
        triangles = [Polygon([vertices[j] for j in indices[i:i+3]]) for i in range(0, len(indices), 3)]
        self.assertAlmostEqual(sum(t.area for t in triangles), area.area, places=6)
        lawn = Polygon(area.interiors[0])
        self.assertLess(sum(t.intersection(lawn).area for t in triangles), 1e-7)
        seams=unary_union([Polygon(p[0],p[1:]) for p in site['seamPolygons']])
        self.assertLess(seams.difference(surface_shape(self.surface)).area,1e-7)
        for poly in site['seamPolygons']:
            for ring in poly:
                self.assertLessEqual(max(area.distance(Point(p)) for p in ring),.120001)
        self.assertGreater(seams.area,.25)

    def test_stale_or_incompatible_context(self):
        for field, value in [('footprintRevision', 'stale'), ('surfaceRevision', 'stale'), ('sourceRefs', ['missing']), ('surfaceOffset', .16)]:
            config = copy.deepcopy(self.config); config[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.derive(config)
        paving = copy.deepcopy(self.paving); paving['groundedService']['offset'] = .15
        with self.assertRaises(ValueError): self.derive(paving=paving)
        paving = copy.deepcopy(self.paving); paving['joinFeather'] = 30
        with self.assertRaises(ValueError): self.derive(paving=paving)

    def test_unconnected_or_out_of_bounds_layout(self):
        for fields in [dict(branches=[[[-491,-856.5],[-494,-856.5]]]),
                       dict(branches=[[[-479,-848],[-477,-842]]]),
                       dict(center=[-460,-856]), dict(radii=[1,1]),
                       dict(pathWidth=float('nan')), dict(boundary=[[0,0],[10,0],[10,10],[0,10]])]:
            config = copy.deepcopy(self.config); config.update(fields)
            with self.subTest(fields=fields), self.assertRaises(ValueError): self.derive(config)

    def test_building_obstacle_is_rejected(self):
        obstacle = {'id':'fixture-obstacle', 'polygons':[[[[-485,-852.5],[-483,-852.5],[-483,-851.5],[-485,-851.5],[-485,-852.5]]]]}
        with self.assertRaises(ValueError): self.derive(buildings=self.buildings+[obstacle])


if __name__ == '__main__': unittest.main()
