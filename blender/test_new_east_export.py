"""Decode the real build/export paths without rebuilding the whole campus."""
import ast
from contextlib import nullcontext
from pathlib import Path
import re
import sys
import tempfile
import unittest

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'blender'))
from campus_gates import campus_gate
from detail_export import export_detail
from geometry import MATERIALS, Mesh, material
from incremental_glb import validate_retained


def full_build_export(directory):
    # build_campus has top-level scene mutation. Execute its actual export
    # function with small real meshes, not a copied set of export parameters.
    source = ROOT/'blender/build_campus.py'
    tree = ast.parse(source.read_text())
    function, = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'export']
    namespace = dict(bpy=bpy, Path=Path, nullcontext=nullcontext,
                     MODELS=directory, EXPORT=bpy.context.scene.collection,
                     foundations={'foundations': []}, pavings={'pavings': []},
                     near={}, buildings=[], bridge_by_id={})
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), 'exec'), namespace)
    return namespace['export']


class NewEastExportTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        MATERIALS.clear()
        self.colors = {name: material(name, (.5, .5, .5)) for name in ('stone', 'gateTrim')}
        self.record = {'id': 'new-east-gate', 'center': [535.648204, -661.452045], 'frontBearing': 180}
        self.key = 'landmark-new-east-gate'
        self.temporary = tempfile.TemporaryDirectory(prefix='gxu-gate-regression-')
        self.directory = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def gate(self, detail):
        return campus_gate(self.record, .58, self.colors, detail)

    def check_grain(self, path):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(path))
        faces = 0
        for obj in bpy.context.scene.objects:
            if obj.type != 'MESH' or obj.get('landmark') != 'new-east-gate':
                continue
            mesh = obj.data
            for face in mesh.polygons:
                mat = mesh.materials[face.material_index]
                if re.sub(r'\.\d+$', '', mat.name) != 'newEastStone':
                    continue
                self.assertTrue(any(n.type == 'TEX_IMAGE' and n.image and tuple(n.image.size) == (128, 128)
                                    for n in mat.node_tree.nodes))
                uv = mesh.uv_layers.active
                self.assertIsNotNone(uv)
                a, b = list(face.loop_indices)[:2]
                va = obj.matrix_world @ mesh.vertices[mesh.loops[a].vertex_index].co
                vb = obj.matrix_world @ mesh.vertices[mesh.loops[b].vertex_index].co
                scale = (uv.data[a].uv-uv.data[b].uv).length/(va-vb).length
                self.assertLess(abs(scale-2), .03, (path.name, face.index, scale))
                faces += 1
        self.assertGreaterEqual(faces, 36)

    def test_full_base_preserves_grain_and_other_node_payloads(self):
        export = full_build_export(self.directory)
        other = Mesh()
        other.box(600, -670, 5, 10, 20, 10, self.colors['stone'])
        export('base.glb', {'context': other})
        baseline = (self.directory/'base.glb').read_bytes()
        export('base.glb', {'context': other, self.key: self.gate(False)})
        validate_retained(baseline, (self.directory/'base.glb').read_bytes(), {self.key})
        self.check_grain(self.directory/'base.glb')

    def test_full_near_preserves_grain(self):
        full_build_export(self.directory)('new-east-gate.glb', {self.key: self.gate(True)})
        self.check_grain(self.directory/'new-east-gate.glb')

    def test_incremental_preserves_grain(self):
        obj = self.gate(True).object(self.key, bpy.context.scene.collection, {'landmark': 'new-east-gate'})
        path = self.directory/'incremental.glb'
        export_detail(obj, path)
        self.check_grain(path)


if __name__ == '__main__':
    unittest.main(argv=[__file__])
