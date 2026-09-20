"""Run the current civil-college geometry checks on one unchanged asset set.

This validates the implemented estimates. Architectural source review, unknowns,
browser views and performance are separate requirements of whole-building review.
"""
import hashlib
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
PREFIX = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--report-prefix=')), 's2-civil-whole')
OUT = ROOT / 'docs/model-checks/refinement'
FILES = ['blender/gxu-campus.blend', 'public/models/base.glb',
         'public/models/chunk-n2-n3.glb', 'public/data/buildings.json',
         'public/data/sites.json', 'public/data/pavings.json', 'public/data/models.json']


def fingerprints():
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in FILES}


# Historical probes are narrowed only where a later dedicated check supersedes
# them. Both old retained geometry and its replacement are included in this suite.
CASES = [
    ('entry', ['--portal-only']),
    ('annex', ['--decorated-step', '--terrace-added', '--rear-massing-added', '--seventh-recess-added']),
    ('facade', ['--retained-only', '--seventh-recess-added']),
    ('recess', []),
    ('seventh', []),
    ('step', ['--seventh-recess-added']),
    ('return', ['--crown-added', '--side-wall-added', '--portal-return-added']),
    ('crown', ['--side-wall-added']),
    ('sidewall', ['--portal-return-added', '--rear-massing-added']),
    ('portal_return', []),
    ('stairs', []),
    ('annex_terrace', ['--gable-screen-added']),
    ('gable', []),
    ('rear', []),
    ('north_gallery', []),
    ('round_windows', []),
    ('north_wing', []),
    ('wing_ends', []),
    ('wing_wrap', []),
    ('forecourt_road', []),
    ('garden', []),
]
checks = [(f'blender/validate_civil_{name}.py', name.replace('_', '-'), args)
          for name, args in CASES]
checks += [('blender/validate_side_connection.py', name,
            [f'--site-id={site}', '--baseline=work/refinement-s2-civil-garden-before'])
           for name, site in [('main-connection', 'civil-main-front-connection'),
                              ('annex-connection', 'civil-annex-stair-connection')]]

report_path = OUT / f'{PREFIX}-geometry-suite.json'
assert not report_path.exists(), 'Do not overwrite an existing suite result'
before = fingerprints()
report = dict(passed=False, scope=__doc__.strip(), fingerprints=before, checks=[])
try:
    for script, name, flags in checks:
        check_prefix = f'{PREFIX}-{name}'
        target = OUT / f'{check_prefix}-geometry.json'
        assert not target.exists(), f'Do not overwrite {target}'
        sys.argv = ['blender', '--', f'--report-prefix={check_prefix}', *flags]
        print(f'WHOLE CHECK START: {name}', flush=True)
        runpy.run_path(str(ROOT / script), run_name='__main__')
        result = json.loads(target.read_text())
        report['checks'].append(dict(script=script, flags=flags, report=str(target.relative_to(ROOT)), passed=result['passed']))
        assert result['passed'], name
        assert fingerprints() == before, 'Validation changed input assets'
        print(f'WHOLE CHECK PASS: {name}', flush=True)
    report['passed'] = True
except Exception as error:
    report['failure'] = str(error)
    raise
finally:
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('Civil whole geometry suite:', report['passed'], flush=True)
