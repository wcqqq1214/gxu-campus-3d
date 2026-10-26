"""An editable object transform must be applied before comparing generator coordinates."""
import sys
import unittest
from pathlib import Path
import bpy
from mathutils import Matrix, Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_generic import component_vertices


class EditableCoordinatesTests(unittest.TestCase):
    def test_translated_rotated_source_matches_baked_world_coordinates(self):
        mesh = bpy.data.meshes.new('regression')
        mesh.from_pydata([(0, 0, 0), (2, 0, 1), (0, 3, 0)], [], [(0, 1, 2)])
        obj = bpy.data.objects.new('regression', mesh)
        bpy.context.scene.collection.objects.link(obj)
        self.addCleanup(lambda: bpy.data.objects.remove(obj, do_unlink=True))
        group = obj.vertex_groups.new(name='body'); group.add([0, 1, 2], 1, 'REPLACE')
        obj.matrix_world = Matrix.Translation((10, -7, -8.25)) @ Matrix.Rotation(.5, 4, 'Z')
        expected = [obj.matrix_world @ Vector(p) for p in [(0, 0, 0), (2, 0, 1), (0, 3, 0)]]
        actual = component_vertices(obj, group)
        self.assertTrue(all((a-b).length < 1e-6 for a,b in zip(actual,expected)))
        self.assertGreater((actual[0]-mesh.vertices[0].co).length, 8)
        obj.location.z += .2
        bpy.context.view_layer.update()
        self.assertGreater((component_vertices(obj,group)[0]-expected[0]).length, .19)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]])
