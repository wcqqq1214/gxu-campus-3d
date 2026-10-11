"""Compare browser exports against a Git revision, permitting only documented removals."""
import argparse
import json
from pathlib import Path
import subprocess

from mapped_canopy_data import check_prepared_mapped_canopies
from foundation_contract import load_foundations
from low_planting_contract import load_prepared

ROOT = Path(__file__).resolve().parents[1]
FILES = ('buildings.json', 'geography.geojson', 'sites.json', 'foundations.json', 'low-planting.json')


def expected_export(value):
    # Deliberately independent of the export implementation.
    if isinstance(value, list):
        return [expected_export(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {}
    for key, item in value.items():
        if key in {'note', 'evidence', 'presence', 'basis'} or key.endswith('Basis'):
            continue
        result[key] = expected_export(item)
    return result


def check(before_ref):
    report = {}
    for name in FILES:
        old_bytes = subprocess.check_output(['git', 'show', f'{before_ref}:public/data/{name}'], cwd=ROOT)
        new_bytes = (ROOT / 'public/data' / name).read_bytes()
        old, new = json.loads(old_bytes), json.loads(new_bytes)
        expected = old if name == 'low-planting.json' else expected_export(old)
        if name == 'buildings.json':
            actual_by_id = {b['id']:b for b in new}
            for building in expected:
                actual_entries = {e['id']:e for e in actual_by_id[building['id']].get('form', {}).get('entrances', [])}
                for entry in building.get('form', {}).get('entrances', []):
                    if 'mappedCanopy' in entry:
                        for key in ('contextRevision', 'partRevision'):
                            entry['shelter'][key] = actual_entries[entry['id']]['shelter'][key]
            check_prepared_mapped_canopies(new)
        if name in ('foundations.json', 'low-planting.json'):

            expected['contextRevision'] = new['contextRevision']
        # Serialized equality also distinguishes integer/float values and booleans.
        assert json.dumps(expected, sort_keys=True) == json.dumps(new, sort_keys=True), name
        report[name] = {'before':len(old_bytes), 'after':len(new_bytes), 'saved':len(old_bytes)-len(new_bytes)}
    load_foundations(ROOT)
    load_prepared(ROOT)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before_ref', help='Git revision before the export')
    print(json.dumps(check(parser.parse_args().before_ref), ensure_ascii=False, indent=2))
