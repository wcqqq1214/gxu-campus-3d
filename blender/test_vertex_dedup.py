"""Base export may share identical vertices, but must retain UV/hard seams."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from io_scene_gltf2.io.exp.binary_data import BinaryData

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vertex_dedup import deduplicate_primitive_vertices


class VertexDedupTests(unittest.TestCase):
    def test_preserves_face_corners_and_shared_source_accessors(self):
        positions = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0],
                              [0, 0, 0], [0, 0, 0], [0, 0, 0]], dtype='<f4')
        normals = np.array([[0, 0, 1]] * 6, dtype='<f4')
        normals[4] = [0, 1, 0]  # Same position, different hard-edge normal.
        uvs = np.array([[0, 0], [1, 0], [0, 1], [1, 1], [0, 0], [0, 0]], dtype='<f4')
        indices = np.array([0, 1, 2, 3, 1, 2, 4, 1, 2, 5, 1, 2], dtype='<u2')

        def accessor(values, component_type=5126):
            return SimpleNamespace(buffer_view=BinaryData(values.tobytes()),
                                   count=len(values), byte_offset=None, sparse=None,
                                   component_type=component_type, min=None, max=None)

        attributes = {name: accessor(values) for name, values in
                      [('POSITION', positions), ('NORMAL', normals), ('TEXCOORD_0', uvs)]}
        index = accessor(indices, 5123)
        primitive = SimpleNamespace(mode=4, targets=None, indices=index, attributes=attributes)
        original_bytes = {name: a.buffer_view.data for name, a in attributes.items()}
        deduplicate_primitive_vertices(primitive)

        self.assertEqual(primitive.attributes['POSITION'].count, 5)
        mapped = np.frombuffer(primitive.indices.buffer_view.data, dtype='<u2')
        for name, source in [('POSITION', positions), ('NORMAL', normals), ('TEXCOORD_0', uvs)]:
            decoded = np.frombuffer(primitive.attributes[name].buffer_view.data,
                                    dtype='<f4').reshape(-1, source.shape[1])
            np.testing.assert_array_equal(decoded[mapped], source[indices])
            self.assertEqual(attributes[name].buffer_view.data, original_bytes[name])
            self.assertEqual(attributes[name].count, 6)
        self.assertEqual(index.buffer_view.data, indices.tobytes())
        self.assertIsNot(primitive.indices, index)


if __name__ == '__main__':
    unittest.main(argv=[__file__])
