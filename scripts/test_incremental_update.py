"""Regress retained published resources and failure-before-publication behavior."""
import copy
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'blender'))
from incremental_glb import splice_nodes, validate_retained, node_signatures, pack
from preserve_glb_geometry import unpack, mesh_nodes_by_name
from incremental_update import publish, snapshot, staged_update, validate_candidate, copy_inputs


class PublishedNodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = (ROOT / 'public/models/base.glb').read_bytes()

    def changed_candidate(self):
        doc, binary = unpack(self.original)
        # A new exporter can reorder primitives, change their count and update
        # shared materials. None of that may affect unselected published nodes.
        for node in doc['nodes']:
            node['translation'] = [1, 2, 3]
            node['extras']['regression'] = True
        road = mesh_nodes_by_name(doc)['roads']
        primitives = doc['meshes'][road['mesh']]['primitives']
        primitives.reverse()
        primitives.pop()
        for material in doc['materials']:
            material['doubleSided'] = not material.get('doubleSided', False)
        return pack(doc, binary)

    def test_existing_assets_retain_full_resource_closure(self):
        candidate = self.changed_candidate()
        with self.assertRaisesRegex(ValueError, 'Unrelated base nodes'):
            validate_retained(self.original, candidate, {'roads'})
        result = splice_nodes(self.original, candidate, {'roads'})
        old = node_signatures(self.original)
        actual = node_signatures(result)
        self.assertEqual(validate_retained(self.original, result, {'roads'}), len(old) - 1)
        self.assertEqual(actual['roads'], node_signatures(candidate)['roads'])
        self.assertNotEqual(actual['roads'], old['roads'])
        for name in old.keys() - {'roads'}:
            self.assertEqual(actual[name], old[name], name)
        budget = json.loads((ROOT / 'data/initial-model-budget.json').read_text())
        self.assertLessEqual(len(result) + (ROOT / 'public/models/trees.glb').stat().st_size, budget['hardLimitBytes'])

    def test_selected_addition_and_removal_do_not_leak_other_new_nodes(self):
        doc, binary = unpack(self.original)
        road = mesh_nodes_by_name(doc)['roads']
        road['name'] = 'new-road'
        extra = copy.deepcopy(road); extra['name'] = 'unrelated-new-node'
        doc['nodes'].append(extra)
        doc['scenes'][0]['nodes'].append(len(doc['nodes']) - 1)
        candidate = pack(doc, binary)
        result = splice_nodes(self.original, candidate, {'roads', 'new-road'})
        names = node_signatures(result)
        self.assertIn('new-road', names)
        self.assertNotIn('roads', names)
        self.assertNotIn('unrelated-new-node', names)
        validate_retained(self.original, result, {'roads', 'new-road'})

    def test_corrupted_retained_texture_is_detected(self):
        doc, binary = unpack(self.original)
        binary = bytearray(binary)
        view = doc['bufferViews'][doc['images'][0]['bufferView']]
        binary[view.get('byteOffset', 0)] ^= 1
        with self.assertRaisesRegex(ValueError, 'Unrelated base nodes'):
            validate_retained(self.original, pack(doc, binary), {'roads'})


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'formal'
        self.candidate = Path(self.temp.name) / 'candidate'
        for root in (self.root, self.candidate):
            for name, value in {'blender/gxu-campus.blend':b'blend', 'public/models/base.glb':b'base',
                                'public/data/models.json':b'manifest'}.items():
                p = root / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(value)
            (root / 'work').mkdir()
        self.before = snapshot(self.root)
        (self.candidate / 'public/models/base.glb').write_bytes(b'new base')
        (self.candidate / 'public/data/models.json').write_bytes(b'new manifest')

    def test_candidate_inside_public_is_rejected_before_copy(self):
        with self.assertRaisesRegex(ValueError, 'inside a copied input'):
            copy_inputs(self.root, self.root / 'public/candidate')
        self.assertEqual(snapshot(self.root), self.before)

    def test_success_publishes_the_validated_set(self):
        changed = publish(self.root, self.candidate, self.before)
        self.assertEqual(set(changed), {'public/models/base.glb', 'public/data/models.json'})
        self.assertEqual(snapshot(self.root), snapshot(self.candidate))

    def test_budget_failure_keeps_formal_assets(self):
        limit = json.loads((ROOT / 'data/initial-model-budget.json').read_text())['hardLimitBytes']
        (self.candidate / 'public/models/base.glb').write_bytes(b'x' * (limit + 1))
        (self.candidate / 'public/models/trees.glb').write_bytes(b'')
        with self.assertRaisesRegex(RuntimeError, 'Initial model budget exceeded'):
            validate_candidate(self.root, self.candidate, 'blender', 'roads')
        self.assertEqual(snapshot(self.root), self.before)

    def test_concurrent_edit_is_not_overwritten(self):
        (self.root / 'public/models/base.glb').write_bytes(b'user edit')
        now = snapshot(self.root)
        with self.assertRaisesRegex(RuntimeError, 'changed while building'):
            publish(self.root, self.candidate, self.before)
        self.assertEqual(snapshot(self.root), now)

    def test_replacement_failure_rolls_back_prior_files(self):
        import os
        original = os.replace
        calls = []
        def fail_second(source, target):
            if 'prepared' in Path(source).parts:
                calls.append(target)
                if len(calls) == 2:
                    raise OSError('injected disk failure')
            return original(source, target)
        with patch('incremental_update.os.replace', side_effect=fail_second):
            with self.assertRaisesRegex(OSError, 'disk failure'):
                publish(self.root, self.candidate, self.before)
        self.assertEqual(snapshot(self.root), self.before)

    def test_build_or_validation_failure_never_publishes(self):
        for phase in ('build', 'geometry'):
            with self.subTest(phase=phase), patch.dict(sys.modules, {'bpy':types.SimpleNamespace(app=types.SimpleNamespace(binary_path='blender'))}), \
                 patch('incremental_update.sys.argv', ['update_roads.py']), \
                 patch('incremental_update.copy_inputs'), \
                 patch('incremental_update.run_checked', side_effect=RuntimeError('build failed') if phase == 'build' else None), \
                 patch('incremental_update.validate_candidate', side_effect=RuntimeError('geometry failed')), \
                 patch('incremental_update.publish') as promote:
                with self.assertRaisesRegex(RuntimeError, phase + ' failed'):
                    staged_update(self.root, self.root / 'blender/update_roads.py')
                promote.assert_not_called()
                self.assertEqual(snapshot(self.root), self.before)


if __name__ == '__main__':
    unittest.main()
