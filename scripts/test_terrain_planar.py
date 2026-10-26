"""Negative controls for the independent terrain acceptance checker."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from check_terrain_planar import check, read, read_decoded


class TerrainCoverageTest(unittest.TestCase):
    def pair(self, *, reversed_face=False, height=0, uv_shift=0, hole=False):
        vertices = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], dtype=float)
        faces = np.array([[0, 1, 2], [0, 2, 3]])
        uv = vertices[faces, :2]/4
        normals = np.tile([0., 0., 1.], (2, 3, 1))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'mesh.npz'
            np.savez(path, vertices=vertices, triangles=faces, uvs=uv, normals=normals, materials=np.zeros(2))
            before = read(path)
            vertices[:, 2] += height
            uv += uv_shift
            if reversed_face:
                faces = faces[:, ::-1]
                uv = uv[:, ::-1]
            count = 1 if hole else 2
            np.savez(path, vertices=vertices, triangles=faces[:count], uvs=uv[:count], normals=normals[:count], materials=np.zeros(count))
            return before, read(path)

    def test_identical_and_bounded_height(self):
        a, b = self.pair()
        self.assertTrue(check(a, b)['passed'])
        a, b = self.pair(height=.0001)
        self.assertTrue(check(a, b)['passed'])

    def test_height_change_rejected(self):
        a, b = self.pair(height=.01)
        self.assertFalse(check(a, b)['passed'])

    def test_missing_coverage_rejected(self):
        a, b = self.pair(hole=True)
        self.assertFalse(check(a, b)['passed'])

    def test_reversed_surface_rejected(self):
        a, b = self.pair(reversed_face=True)
        self.assertFalse(check(b, a)['passed'])

    def test_uv_change_rejected(self):
        a, b = self.pair(uv_shift=.1)
        self.assertFalse(check(a, b)['passed'])


class DecodedTerrainCoverageTest(unittest.TestCase):
    def fixture(self, *, vertical=False):
        vertices = [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]]
        if vertical:
            vertices = [[x, 0, y] for x, y, _ in vertices]
        return dict(vertices=vertices, triangles=[[0, 1, 2], [0, 2, 3]],
                    uvs=[[0, 0], [.25, 0], [.25, .25], [0, .25]],
                    normals=[[0, -1, 0] if vertical else [0, 0, 1] for _ in vertices],
                    material={'name': 'terrain'}, modelSHA256='fixture')

    def read_pair(self, before, after):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory)/name for name in ('before.json', 'after.json')]
            for path, data in zip(paths, (before, after)):
                path.write_text(json.dumps(data))
            return tuple(read_decoded(path) for path in paths)

    def test_identical_and_cyclic_faces_keep_horizontal_and_vertical_surfaces(self):
        for vertical in (False, True):
            before = self.fixture(vertical=vertical)
            for cyclic in (False, True):
                after = copy.deepcopy(before)
                if cyclic:
                    after['triangles'] = [face[1:]+face[:1] for face in after['triangles']]
                a, b = self.read_pair(before, after)
                for source, target in ((a, b), (b, a)):
                    with self.subTest(vertical=vertical, cyclic=cyclic):
                        result = check(source, target)
                        self.assertTrue(result['passed'])
                        self.assertEqual(result['changedFaces'], 0)

    def test_bounded_uv_and_normal_rounding_passes_in_both_directions(self):
        before = self.fixture()
        after = copy.deepcopy(before)
        after['uvs'] = [[u+5e-10, v] for u, v in after['uvs']]
        after['normals'] = [[.0005, 0, (1-.0005**2)**.5] for _ in after['normals']]
        a, b = self.read_pair(before, after)
        for source, target in ((a, b), (b, a)):
            self.assertTrue(check(source, target)['passed'])

    def test_uv_and_normal_changes_are_rejected_in_both_directions(self):
        before = self.fixture()
        for attribute in ('uvs', 'normals'):
            after = copy.deepcopy(before)
            after[attribute] = ([[u+.1, v] for u, v in before['uvs']] if attribute == 'uvs'
                                else [[0, 1, 0] for _ in before['normals']])
            a, b = self.read_pair(before, after)
            for direction, (source, target) in enumerate(((a, b), (b, a))):
                with self.subTest(attribute=attribute, direction=direction):
                    self.assertFalse(check(source, target)['passed'])

    def test_duplicate_geometry_cannot_hide_a_missing_uv_surface(self):
        before = self.fixture()
        before['vertices'] *= 2
        before['normals'] *= 2
        before['triangles'] += [[i+4 for i in face] for face in before['triangles']]
        before['uvs'] += [[u+.5, v] for u, v in before['uvs']]
        after = copy.deepcopy(before)
        after['uvs'][4:] = copy.deepcopy(after['uvs'][:4])
        a, b = self.read_pair(before, after)
        self.assertFalse(check(a, b)['passed'])


if __name__ == '__main__':
    unittest.main()
