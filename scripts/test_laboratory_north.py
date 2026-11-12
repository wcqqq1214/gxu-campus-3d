"""Historical north neighbours must remain distinct from the former guesthouse."""

import json
import unittest
from pathlib import Path

from building_overrides import resolve_building, source_catalogue
from public_data_fields import without_documentation

ROOT = Path(__file__).resolve().parents[1]
TARGETS = {'way/759090364', 'way/842784665'}


def assert_close(case, actual, expected, path='value'):
    """Compare nested data, tolerating cross-platform libm float noise."""
    if isinstance(expected, dict):
        case.assertEqual(actual.keys(), expected.keys(), path)
        for key in expected:
            assert_close(case, actual[key], expected[key], f'{path}.{key}')
    elif isinstance(expected, list):
        case.assertEqual(len(actual), len(expected), path)
        for i, (a, e) in enumerate(zip(actual, expected)):
            assert_close(case, a, e, f'{path}[{i}]')
    elif isinstance(expected, float):
        case.assertAlmostEqual(actual, expected, delta=1e-9, msg=path)
    else:
        case.assertEqual(actual, expected, path)


class LaboratoryNorthTests(unittest.TestCase):
    def test_published_neighbours_use_attributed_three_storeys(self):
        buildings = json.loads((ROOT / 'public/data/buildings.json').read_text())
        catalogue = json.loads((ROOT / 'data/building-overrides.json').read_text())[
            'buildings'
        ]
        sources = {s['id'] for s in source_catalogue(ROOT)}
        geo = {
            f['id']: f['properties']
            for f in json.loads((ROOT / 'public/data/geography.geojson').read_text())[
                'features'
            ]
        }
        selected = [b for b in buildings if b['id'] in TARGETS]
        self.assertEqual({b['id'] for b in selected}, TARGETS)
        laboratory = next(b for b in buildings if b.get('landmark') == 'laboratory')
        for b in selected:
            with self.subTest(id=b['id']):
                resolved = resolve_building(b, catalogue[b['id']], sources)
                assert_close(self, b, without_documentation(resolved))
                self.assertEqual(b['levels'], 3)
                self.assertAlmostEqual(b['height'], 9.9)
                self.assertGreater(b['center'][1], laboratory['center'][1])
                self.assertEqual(
                    resolved['calibration']['evidence']['height']['status'], 'estimated'
                )
                self.assertEqual(
                    set(catalogue[b['id']]['evidence']['levels']['sourceRefs']),
                    {'gxuDonationProjects', 'gxuCivilDemolitionScope2022'},
                )
                for key in (
                    'height',
                    'levels',
                    'archetype',
                    'sourceRefs',
                    'calibration',
                ):
                    self.assertEqual(geo[b['id']][key], b[key])
                self.assertEqual(b['form']['height'], b['height'])
                self.assertEqual(b['form']['roof']['type'], 'flat')
        self.assertLess(min(b['center'][0] for b in selected), laboratory['center'][0])
        self.assertGreater(
            max(b['center'][0] for b in selected), laboratory['center'][0]
        )
