"""Export-only LOD splitting retains actual compressed data and fails closed."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'blender'))
from basketball_export import extract_bank, write_glb
from preserve_glb_geometry import unpack


class BankExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'bank.glb'
        self.doc = dict(asset={'version': '2.0'}, nodes=[{'name': 'bank', 'mesh': 0, 'extras': {'layer': 'sports'}}],
            meshes=[{'primitives': [{'material': 0, 'attributes': {'POSITION': 0}, 'indices': 1,
                'extensions': {'KHR_draco_mesh_compression': {'bufferView': 1, 'attributes': {'POSITION': 0}}}}]}],
            accessors=[{'count': 3, 'type': 'VEC3', 'componentType': 5126}, {'count': 3, 'type': 'SCALAR', 'componentType': 5123}],
            materials=[{'name': 'courtOrange', 'pbrMetallicRoughness': {'baseColorFactor': [1, .2, 0, 1]}}],
            buffers=[{'byteLength': 16}], bufferViews=[{'buffer': 0, 'byteOffset': 0, 'byteLength': 8},
                                                    {'buffer': 0, 'byteOffset': 8, 'byteLength': 8}])

    def raw(self, doc):
        original = self.path.with_name('input.glb')
        write_glb(original, doc, b'unused!!geometry')
        return original.read_bytes()

    def test_exact_payload_attributes_material_and_layer(self):
        extract_bank(self.raw(self.doc), 'bank', self.path)
        doc, binary = unpack(self.path.read_bytes())
        self.assertEqual(binary, b'geometry')
        self.assertEqual(doc['materials'], self.doc['materials'])
        p = doc['meshes'][0]['primitives'][0]
        self.assertEqual(doc['accessors'][p['attributes']['POSITION']], self.doc['accessors'][0])
        self.assertEqual(doc['accessors'][p['indices']], self.doc['accessors'][1])
        self.assertEqual(doc['nodes'], self.doc['nodes'])
        self.assertEqual(doc['scenes'], [{'nodes': [0]}])
        self.assertEqual(len(doc['bufferViews']), 1)
        previous = self.path.read_bytes()
        extract_bank(previous, 'bank', self.path)
        self.assertEqual(previous, self.path.read_bytes())

    def test_unsupported_inputs_do_not_overwrite_existing_output(self):
        changes = [lambda d: d['nodes'][0].update(translation=[1, 0, 0]),
                   lambda d: d['materials'][0].update(normalTexture={'index': 0}),
                   lambda d: d['materials'][0].update(extensions={'KHR_materials_clearcoat': {}}),
                   lambda d: d['accessors'][0].update(bufferView=0),
                   lambda d: d['meshes'][0]['primitives'][0].update(targets=[])]
        for change in changes:
            doc = copy.deepcopy(self.doc); change(doc)
            self.path.write_bytes(b'existing')
            with self.assertRaises(ValueError):
                extract_bank(self.raw(doc), 'bank', self.path)
            self.assertEqual(self.path.read_bytes(), b'existing')


if __name__ == '__main__':
    unittest.main()
