"""Negative controls for the independent terrain acceptance checker."""
import tempfile
import unittest
from pathlib import Path

import numpy as np

from check_terrain_planar import check, read


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


if __name__ == '__main__':
    unittest.main()
