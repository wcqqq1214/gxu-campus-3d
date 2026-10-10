"""Source UV preservation and rejection of unsupported ground mappings."""
import sys
import unittest
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from geometry import Mesh
from repair_foundation_candidate import replace_terrain, source_mesh


class CandidateTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        data = bpy.data.meshes.new('terrain')
        data.from_pydata([(0, 0, 1), (4, 0, 1), (4, 4, 1), (0, 4, 1),
                          (10, 0, 1), (14, 0, 1), (10, 4, 1)], [], [(0, 1, 2, 3), (4, 5, 6)])
        data.materials.append(bpy.data.materials.new('ground'))
        uv = data.uv_layers.new(name='ground')
        for face in data.polygons:
            for k in face.loop_indices:
                p = data.vertices[data.loops[k].vertex_index].co
                uv.data[k].uv = (p.x / 4, p.y / 4)
        # A distant custom mapping must survive without being reprojected.
        for k in data.polygons[1].loop_indices:
            uv.data[k].uv = (7, 9)
        self.obj = bpy.data.objects.new('terrain', data)
        bpy.context.scene.collection.objects.link(self.obj)

    def repaired(self):
        result = source_mesh(self.obj)
        result.v.append((2, 2, 0))
        result.f = [(0, 1, 7), (1, 2, 7), (2, 3, 7), (3, 0, 7), (4, 5, 6)]
        result.m = [0] * 5
        return result

    def test_lowered_patch_keeps_projection_and_distant_uvs(self):
        report = replace_terrain(self.obj, self.repaired())
        self.assertEqual(report['unchangedFacesWithExactUVs'], 1)
        for face in self.obj.data.polygons:
            for k in face.loop_indices:
                p = self.obj.data.vertices[self.obj.data.loops[k].vertex_index].co
                expected = (7, 9) if face.index == 4 else (p.x / 4, p.y / 4)
                self.assertEqual(tuple(self.obj.data.uv_layers.active.data[k].uv), expected)

    def test_changed_nonplanar_uv_mapping_is_rejected(self):
        old = self.obj.data
        old.uv_layers.active.data[0].uv = (3, 5)
        with self.assertRaisesRegex(ValueError, 'XY/4'):
            replace_terrain(self.obj, self.repaired())
        self.assertIs(self.obj.data, old)

    def test_transformed_source_is_rejected(self):
        self.obj.location.x = 10
        bpy.context.view_layer.update()
        with self.assertRaisesRegex(ValueError, 'untransformed'):
            source_mesh(self.obj)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CandidateTests)
    if not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful():
        raise AssertionError('Foundation candidate tests failed')
