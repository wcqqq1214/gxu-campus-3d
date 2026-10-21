"""Run with Blender's Python: preserve authored UVs through nested batching."""
import sys
import unittest
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from geometry import Mesh, MATERIALS, material


class MeshUVTests(unittest.TestCase):
    def setUp(self):
        self.mat = material('uv-regression', (.5, .5, .5))

    def tearDown(self):
        for obj in list(bpy.data.objects):
            if obj.name.startswith('uv-regression'):
                mesh = obj.data
                bpy.data.objects.remove(obj, do_unlink=True)
                bpy.data.meshes.remove(mesh)
        bpy.data.materials.remove(MATERIALS.pop())

    def test_nested_batch_keeps_corner_associations_and_default_projection(self):
        face = [(4, 8, 0), (6, 8, 0), (6, 9, 0), (4, 9, 0)]
        authored = [(.1, .2), (.6, .2), (.6, .45), (.1, .45)]
        detail = Mesh()
        detail.face(face, self.mat, authored)
        building = Mesh()
        building.face(face, self.mat)
        building.extend(detail)
        chunk = Mesh()
        chunk.face(face, self.mat)
        chunk.extend(building)
        obj = chunk.object('uv-regression-batch', bpy.context.scene.collection)
        uv = obj.data.uv_layers.active.data
        for index, expected in enumerate(([tuple(v / 4 for v in p[:2]) for p in face],) * 2 + (authored,)):
            for loop, pair in zip(obj.data.polygons[index].loop_indices, expected):
                for actual, wanted in zip(uv[loop].uv, pair):
                    self.assertAlmostEqual(actual, wanted, places=6)

    def test_invalid_corner_count_leaves_mesh_unchanged(self):
        mesh = Mesh()
        with self.assertRaises(ValueError):
            mesh.face([(0, 0, 0), (1, 0, 0), (0, 1, 0)], self.mat, [(0, 0)])
        self.assertEqual((mesh.v, mesh.f, mesh.m, mesh.face_uvs), ([], [], [], {}))


if __name__ == '__main__':
    unittest.main(argv=[__file__])
