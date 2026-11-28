"""Publishing strips documentation without weakening stale-geometry detection."""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from export_public_data import EXPORTS, export_public_data
from foundation_contract import foundation_context, load_foundations, revision
from low_planting_contract import (
    CONTEXT_FILES,
    context_revision,
    context_value,
    digest,
    load_prepared,
)
from road_landing_contract import load_landings

ROOT = Path(__file__).resolve().parents[1]
WRITABLE = (*EXPORTS, 'low-planting.json', 'pavings.json', 'shores.json')


class PublicExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        os.symlink(ROOT / 'data', self.root / 'data')
        public_data = self.root / 'public/data'
        public_data.mkdir(parents=True)
        writable = set(WRITABLE)
        for source in (ROOT / 'public/data').iterdir():
            target = public_data / source.name
            if source.name in writable:
                shutil.copyfile(source, target)
            else:
                os.symlink(source, target)

    def read(self, name):
        return json.loads((self.root / 'public/data' / name).read_text())

    def write(self, name, value):
        (self.root / 'public/data' / name).write_text(
            json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n'
        )

    def snapshot(self):
        return {
            name: (self.root / 'public/data' / name).read_bytes()
            for name in (*EXPORTS, 'low-planting.json', 'pavings.json', 'shores.json')
        }

    def ground_contexts(self):
        sites = self.read('sites.json')
        paving = [
            self.read(name + '.json')
            for name in ('surfaces', 'infrastructure', 'surroundings', 'campus-roads')
        ] + [sites]
        shore = {
            'surfaces': paving[0],
            'infrastructure': paving[1],
            'surroundings': paving[2],
            'roads': paving[3],
            'sites': sites,
            'buildings': [
                [b['id'], b['polygons']] for b in self.read('buildings.json')
            ],
        }
        return {'pavings.json': paving, 'shores.json': shore}

    def prepare_dependent_fingerprints(self):
        foundation = self.read('foundations.json')
        foundation['contextRevision'] = revision(foundation_context(self.root))
        self.write('foundations.json', foundation)
        config = json.loads((self.root / 'data/low-planting.json').read_text())
        data = {name: self.read(name + '.json') for name in CONTEXT_FILES}
        low = self.read('low-planting.json')
        low['contextRevision'] = context_revision(
            context_value(self.root, config, data)
        )
        self.write('low-planting.json', low)

    def test_export_strips_documentation_migrates_fingerprints_and_is_idempotent(
        self,
    ):
        buildings = self.read('buildings.json')
        buildings[0]['heightBasis'] = 'test estimate'
        buildings[0]['nested'] = {'note': 'nested annotation'}
        self.write('buildings.json', buildings)
        sites = self.read('sites.json')
        sites['sites'][0]['evidence'] = {'dimensions': 'fresh preparation evidence'}
        self.write('sites.json', sites)
        for name, context in self.ground_contexts().items():
            value = self.read(name)
            value['contextRevision'] = digest(context)
            self.write(name, value)
        self.prepare_dependent_fingerprints()
        export_public_data(self.root)
        load_foundations(self.root)
        load_prepared(self.root)
        load_landings(self.root)
        self.assertNotIn('heightBasis', self.read('buildings.json')[0])
        self.assertEqual(self.read('buildings.json')[0]['nested'], {})
        self.assertNotIn('evidence', self.read('sites.json')['sites'][0])
        for name, context in self.ground_contexts().items():
            self.assertEqual(self.read(name)['contextRevision'], digest(context))
        first = self.snapshot()
        export_public_data(self.root)
        self.assertEqual(self.snapshot(), first)
        # Adding provenance back cannot invalidate geometric dependencies.
        self.write('buildings.json', buildings)
        self.write('sites.json', sites)
        load_foundations(self.root)
        load_prepared(self.root)

    def test_stale_ground_fingerprints_are_not_blessed_by_export(self):
        for name in ('pavings.json', 'shores.json'):
            with self.subTest(name=name):
                original = self.read(name)
                broken = dict(original, contextRevision='stale')
                self.write(name, broken)
                self.prepare_dependent_fingerprints()
                before = self.snapshot()
                with self.assertRaisesRegex(ValueError, name + ' context is stale'):
                    export_public_data(self.root)
                self.assertEqual(self.snapshot(), before)
                self.write(name, original)

    def test_stale_geometry_is_rejected_before_any_export_write(self):
        buildings = self.read('buildings.json')
        buildings[0]['center'][0] += 1
        self.write('buildings.json', buildings)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'Foundation context is stale'):
            export_public_data(self.root)
        self.assertEqual(before, self.snapshot())

    def test_stale_planting_is_rejected_even_with_valid_foundations(self):
        buildings = self.read('buildings.json')
        library = next(b for b in buildings if b['landmark'] == 'library')
        library['architecture']['northEntry']['width'] += 1
        self.write('buildings.json', buildings)
        foundation = self.read('foundations.json')
        foundation['contextRevision'] = revision(foundation_context(self.root))
        self.write('foundations.json', foundation)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'Low-planting context is stale'):
            export_public_data(self.root)
        self.assertEqual(before, self.snapshot())
