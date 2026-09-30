"""Regressions for redundant vertices, attribute seams and cached accessors."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from io_scene_gltf2.io.exp.binary_data import BinaryData

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vertex_dedup import deduplicate_primitive_vertices
from export_attributes import omit_unused_uvs
import export_attributes


def accessor(values, component=5126):
    dtype = {5126: '<f4', 5123: '<u2', 5125: '<u4'}[component]
    array = np.array(values, dtype=dtype)
    return SimpleNamespace(count=len(values), component_type=component,
                           buffer_view=BinaryData(array.tobytes()), byte_offset=None,
                           sparse=None, min=None, max=None)


def fixture(component=5123):
    return SimpleNamespace(mode=4, targets=None, attributes={
        'POSITION': accessor([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]]),
        'NORMAL': accessor([[0, 0, 1]] * 5 + [[0, 1, 0]]),
        'TEXCOORD_0': accessor([[0, 0], [1, 0], [0, 1], [0, 0], [1, 1], [0, 0]]),
    }, indices=accessor([0, 1, 2, 3, 1, 2, 4, 1, 2, 5, 1, 2], component))


def corners(primitive):
    indices = np.frombuffer(primitive.indices.buffer_view.data,
                            dtype={5123: '<u2', 5125: '<u4'}[primitive.indices.component_type])
    return {name: np.frombuffer(a.buffer_view.data, dtype=np.uint8).reshape(a.count, -1)[indices].tobytes()
            for name, a in primitive.attributes.items()}


class VertexDedupTests(unittest.TestCase):
    def test_face_corners_seams_and_index_types(self):
        for component in (5123, 5125):
            with self.subTest(component=component):
                p = fixture(component)
                before = corners(p)
                p.indices.min, p.indices.max = [0], [5]
                deduplicate_primitive_vertices(p)
                self.assertEqual(p.attributes['POSITION'].count, 5)
                self.assertEqual(p.indices.count, 12)  # duplicate faces stay
                self.assertEqual(p.indices.component_type, component)
                self.assertEqual(p.indices.max, [4])
                self.assertEqual(corners(p), before)

    def test_shared_accessors_are_not_mutated(self):
        p = fixture()
        shared = SimpleNamespace(**vars(p))
        before = corners(shared)
        deduplicate_primitive_vertices(p)
        self.assertIsNot(p.attributes['POSITION'], shared.attributes['POSITION'])
        self.assertIsNot(p.indices, shared.indices)
        self.assertEqual(shared.attributes['POSITION'].count, 6)
        self.assertEqual(corners(shared), before)

    def test_unknown_attribute_participates(self):
        p = fixture()
        p.attributes['_CUSTOM'] = accessor([[i] for i in range(6)])
        attributes = p.attributes
        deduplicate_primitive_vertices(p)
        self.assertIs(p.attributes, attributes)

    def test_unsupported_geometry_is_unchanged(self):
        for field, value in [('mode', 1), ('targets', [object()]), ('indices', None)]:
            p = fixture()
            setattr(p, field, value)
            attributes = p.attributes
            deduplicate_primitive_vertices(p)
            self.assertIs(p.attributes, attributes)

    def test_invalid_indices_fail_before_mutation(self):
        p = fixture()
        p.indices = accessor([0, 1, 9], 5123)
        attributes = p.attributes
        with self.assertRaises(ValueError):
            deduplicate_primitive_vertices(p)
        self.assertIs(p.attributes, attributes)

    def test_mismatched_attribute_counts_fail(self):
        p = fixture()
        p.attributes['NORMAL'].count = 5
        with self.assertRaises(ValueError):
            deduplicate_primitive_vertices(p)

    def test_scope_restores_on_nested_failure(self):
        self.assertFalse(export_attributes._deduplicate_vertices)
        with omit_unused_uvs(deduplicate_vertices=True):
            self.assertTrue(export_attributes._deduplicate_vertices)
            with self.assertRaises(RuntimeError):
                with omit_unused_uvs():
                    self.assertFalse(export_attributes._deduplicate_vertices)
                    raise RuntimeError('cleanup probe')
            self.assertTrue(export_attributes._deduplicate_vertices)
        self.assertFalse(export_attributes._deduplicate_vertices)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]], verbosity=2)
