"""Packing regressions: references, metadata boundaries and lossless JPEGs."""
import io
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'blender'))
from preserve_glb_geometry import compact_buffer_views, unpack


def fixture(path, payloads, **fields):
    binary = bytearray()
    views = []
    for payload in payloads:
        binary.extend(b'\0' * (-len(binary) % 4))
        views.append({'buffer': 0, 'byteOffset': len(binary), 'byteLength': len(payload)})
        binary.extend(payload)
    binary.extend(b'\0' * (-len(binary) % 4))
    doc = {'asset': {'version': '2.0'}, 'buffers': [{'byteLength': len(binary)}],
           'bufferViews': views, **fields}
    header = json.dumps(doc).encode()
    header += b' ' * (-len(header) % 4)
    path.write_bytes(struct.pack('<4sII', b'glTF', 2, 28 + len(header) + len(binary))
                     + struct.pack('<I4s', len(header), b'JSON') + header
                     + struct.pack('<I4s', len(binary), b'BIN\0') + binary)


def payload(doc, binary, index):
    view = doc['bufferViews'][index]
    start = view.get('byteOffset', 0)
    return binary[start:start + view['byteLength']]


class LosslessPackingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'fixture.glb'

    def test_duplicates_and_nested_references_preserve_slices(self):
        fixture(self.path, [b'unused', b'abcdefgh', b'abcdefgh'],
                accessors=[{'bufferView': 1, 'byteOffset': 2}],
                meshes=[{'primitives': [{'extensions': {'KHR_draco_mesh_compression':
                         {'bufferView': 2, 'attributes': {'POSITION': 0}}}}]}])
        compact_buffer_views(self.path)
        doc, binary = unpack(self.path.read_bytes())
        self.assertEqual(len(doc['bufferViews']), 1)
        self.assertEqual(doc['accessors'], [{'bufferView': 0, 'byteOffset': 2}])
        self.assertEqual(payload(doc, binary, 0)[2:], b'cdefgh')
        self.assertEqual(doc['meshes'][0]['primitives'][0]['extensions']
                         ['KHR_draco_mesh_compression']['bufferView'], 0)
        before = self.path.read_bytes()
        compact_buffer_views(self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_metadata_differences_prevent_sharing(self):
        views = [{'buffer': 0, 'byteOffset': index * 8, 'byteLength': 8, **extra}
                 for index, extra in enumerate([{}, {'target': 34962}, {'byteStride': 8},
                                                {'extras': {'meaning': 'distinct'}}])]
        fixture(self.path, [b'abcdefgh'] * 4, bufferViews=views,
                accessors=[{'bufferView': index} for index in range(4)])
        compact_buffer_views(self.path)
        self.assertEqual(len(unpack(self.path.read_bytes())[0]['bufferViews']), 4)

    def test_failure_preserves_original_file(self):
        fixture(self.path, [b'bad jpeg'], images=[{'bufferView': 0, 'mimeType': 'image/jpeg'}])
        before = self.path.read_bytes()
        with patch('preserve_glb_geometry.shutil.which', return_value='/fake/jpegtran'), \
             patch('preserve_glb_geometry.subprocess.run', side_effect=subprocess.CalledProcessError(1, 'jpegtran')):
            with self.assertRaises(subprocess.CalledProcessError):
                compact_buffer_views(self.path, optimize_jpegs=True)
        self.assertEqual(before, self.path.read_bytes())

    def test_missing_encoder_preserves_file(self):
        fixture(self.path, [b'jpeg'], images=[{'bufferView': 0, 'mimeType': 'image/jpeg'}])
        before = self.path.read_bytes()
        with patch('preserve_glb_geometry.shutil.which', return_value=None):
            with self.assertRaisesRegex(RuntimeError, 'jpegtran'):
                compact_buffer_views(self.path, optimize_jpegs=True)
        self.assertEqual(before, self.path.read_bytes())

    def test_mixed_usage_does_not_rewrite_geometry(self):
        fixture(self.path, [b'shared'], images=[{'bufferView': 0, 'mimeType': 'image/jpeg'}],
                accessors=[{'bufferView': 0}])
        with patch('preserve_glb_geometry.subprocess.run') as run:
            compact_buffer_views(self.path, optimize_jpegs=True)
            run.assert_not_called()
        doc, binary = unpack(self.path.read_bytes())
        self.assertEqual(payload(doc, binary, 0), b'shared')

    @unittest.skipUnless(shutil.which('jpegtran'), 'jpegtran is a model-build dependency')
    def test_jpeg_pixels_quantization_and_markers_preserved(self):
        from PIL import Image
        for mode in ['RGB', 'L']:
            with self.subTest(mode=mode):
                buffer = io.BytesIO()
                image = Image.new(mode, (32, 32))
                image.putdata([(i % 251, (i * 3) % 253, (i * 7) % 255) if mode == 'RGB'
                               else i % 251 for i in range(1024)])
                exif = Image.Exif(); exif[270] = 'Preserve description'
                image.save(buffer, 'JPEG', quality=85, exif=exif, icc_profile=b'test-icc-marker')
                original = buffer.getvalue()
                fixture(self.path, [original], images=[{'bufferView': 0, 'mimeType': 'image/jpeg'}])
                compact_buffer_views(self.path, optimize_jpegs=True)
                doc, binary = unpack(self.path.read_bytes())
                optimized = payload(doc, binary, 0)
                a, b = Image.open(io.BytesIO(original)), Image.open(io.BytesIO(optimized))
                self.assertLess(len(optimized), len(original))
                self.assertEqual(a.tobytes(), b.tobytes())
                self.assertEqual(a.quantization, b.quantization)
                self.assertEqual(a.info.get('exif'), b.info.get('exif'))
                self.assertEqual(a.info.get('icc_profile'), b.info.get('icc_profile'))
                before = self.path.read_bytes()
                compact_buffer_views(self.path, optimize_jpegs=True)
                self.assertEqual(before, self.path.read_bytes())


if __name__ == '__main__':
    unittest.main()
