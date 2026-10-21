"""Opt-in integration regression using the current published assets and editable source."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'blender'))
from incremental_update import snapshot
from incremental_glb import validate_retained
from preserve_glb_geometry import unpack, mesh_nodes_by_name

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-root', type=Path, required=True, help='New directory for both validated candidates')
args = parser.parse_args()
output = args.output_root.resolve()
output.mkdir(parents=True, exist_ok=False)
before = snapshot(ROOT)
old = (ROOT / 'public/models/base.glb').read_bytes()
results = {}
for kind in ('roads', 'basketball'):
    candidate = output / kind
    with (output / (kind + '.log')).open('w') as log:
        result = subprocess.run([os.environ.get('BLENDER_BIN', 'blender'), '-b', '--factory-startup',
            '--disable-autoexec', '--python-exit-code', '1', '--python', str(ROOT / f'blender/update_{kind}.py'),
            '--', f'--output-root={candidate}'], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    if snapshot(ROOT) != before:
        raise RuntimeError('Integration test modified published assets')
    if result.returncode:
        raise RuntimeError(f'{kind} failed: {output / (kind + ".log")}')
    updated = (candidate / 'public/models/base.glb').read_bytes()
    names = set(mesh_nodes_by_name(unpack(old)[0])) | set(mesh_nodes_by_name(unpack(updated)[0]))
    selected = {'roads', 'terrain', 'green'} | {n for n in names if n.startswith(('site-', 'shore-', 'paving-', 'vegetation-low-'))}
    if kind == 'roads':
        selected |= {n for n in names if n.startswith('infra-approach-')}
        selected |= {'landmark-' + b['id'] for b in json.loads((ROOT / 'public/data/infrastructure.json').read_text())['bridges']}
    else:
        selected |= {'sports'} | {n for n in names if n.startswith('basketball-bank-')}
    retained = validate_retained(old, updated, selected)
    report = json.loads((candidate / 'work/incremental-result.json').read_text())
    assert report['passed'] and report['published'] == []
    results[kind] = {'retainedNodes':retained, 'initialBytes':report['initialBytes']}
    (output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    print(kind, results[kind], flush=True)
