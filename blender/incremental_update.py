"""Stage and validate legacy incremental workers before publishing any assets."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def snapshot(root):
    paths = [root / 'blender/gxu-campus.blend']
    paths += sorted((root / 'public').rglob('*'))
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths if p.is_file()}


def copy_inputs(root, candidate):
    if any(candidate.resolve().is_relative_to((root / name).resolve())
           for name in ('data', 'public', 'scripts', 'lib', 'blender', 'node_modules')):
        raise ValueError('Candidate cannot be inside a copied input directory')
    candidate.mkdir(parents=True, exist_ok=False)
    for name in ('data', 'public', 'scripts', 'lib'):
        shutil.copytree(root / name, candidate / name, ignore=shutil.ignore_patterns('__pycache__'))
    (candidate / 'blender').mkdir()
    for path in (root / 'blender').glob('*.py'):
        shutil.copy2(path, candidate / 'blender' / path.name)
    for name in ('textures', 'fonts', 'fixtures'):
        shutil.copytree(root / 'blender' / name, candidate / 'blender' / name)
    shutil.copy2(root / 'blender/gxu-campus.blend', candidate / 'blender/gxu-campus.blend')
    (candidate / 'docs/model-checks/refinement').mkdir(parents=True)
    (candidate / 'work').mkdir()
    (candidate / 'node_modules').symlink_to((root / 'node_modules').resolve(), target_is_directory=True)
    shutil.copy2(root / 'package.json', candidate / 'package.json')


def run_checked(command, candidate, name):
    log = candidate / 'work' / (name + '.log')
    print(f'Incremental check: {name} ({log})', flush=True)
    with log.open('w') as stream:
        result = subprocess.run(command, cwd=candidate, stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f'{name} failed; formal assets retained. See {log}')


def validate_candidate(root, candidate, blender, kind):
    from initial_model_budget import check_initial_model_budget
    total = sum((candidate / 'public/models' / n).stat().st_size for n in ('base.glb', 'trees.glb'))
    check_initial_model_budget(total)
    checks = [
        ('source-retention', 'validate_incremental_source.py', [f'--baseline-root={root}', f'--update-kind={kind}']),
        ('edges', 'validate_civil_edges.py', []),
        ('grade', 'validate_civil_grade.py', [f'--baseline-root={root}']),
        ('materials', 'validate_materials_entry.py', []),
        ('generic', 'validate_generic.py', ['--report-prefix=incremental-generic']),
    ]
    for name, script, args in checks:
        run_checked([blender, '-b', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1',
                     '--python', str(candidate / 'blender' / script), '--',
                     f'--check-root={candidate}', f'--report={candidate}/work/{name}.json', *args], candidate, name)
    run_checked([os.environ.get('NODE_BIN', 'node'), '--experimental-strip-types', '--test',
                 'scripts/test-campus.mjs', 'scripts/test-basketball.mjs'], candidate, 'assets')


def publish(root, candidate, before):
    """Reject concurrent edits; prepare all replacements and roll back ordinary I/O failures."""
    if snapshot(root) != before:
        raise RuntimeError('Formal assets changed while building; candidate retained, nothing published')
    after = snapshot(candidate)
    removed = set(before) - set(after)
    if removed:
        raise ValueError(f'Incremental update unexpectedly deleted files: {sorted(removed)}')
    changed = [name for name, digest in after.items() if before.get(name) != digest]
    with tempfile.TemporaryDirectory(prefix='gxu-publish-', dir=root / 'work') as directory:
        backup = Path(directory) / 'backup'; prepared = Path(directory) / 'prepared'
        for name in changed:
            target = root / name
            if target.exists():
                saved = backup / name; saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, saved)
            ready = prepared / name; ready.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(candidate / name, ready)
        installed = []
        try:
            for name in changed:
                target = root / name; target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(prepared / name, target); installed.append(name)
        except BaseException:
            for name in reversed(installed):
                saved = backup / name
                if saved.exists():
                    os.replace(saved, root / name)
                else:
                    (root / name).unlink()
            raise
    return changed


def staged_update(root, script):
    import bpy
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path, help='Keep a validated candidate without publishing')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    root = root.resolve()
    (root / 'work').mkdir(exist_ok=True)
    if args.output_root:
        candidate = args.output_root.resolve()
        if candidate == root or candidate in root.parents:
            raise ValueError('Candidate must be a new independent directory')
    else:
        directory = Path(tempfile.mkdtemp(prefix='incremental-', dir=root / 'work'))
        candidate = directory / 'candidate'
    before = snapshot(root)
    copy_inputs(root, candidate)
    worker = candidate / 'blender' / Path(script).name
    expression = f"import runpy; runpy.run_path({str(worker)!r}, init_globals={{'_INCREMENTAL_CANDIDATE': True}}, run_name='__main__')"
    run_checked([bpy.app.binary_path, '-b', '--factory-startup', '--disable-autoexec',
                 '--python-exit-code', '1', '--python-expr', expression], candidate, 'update')
    validate_candidate(root, candidate, bpy.app.binary_path, Path(script).stem.removeprefix('update_'))
    if snapshot(root) != before:
        raise RuntimeError('Formal assets changed during candidate validation; nothing published')
    changed = [] if args.output_root else publish(root, candidate, before)
    report = {'passed': True, 'candidate': str(candidate), 'published': changed,
              'initialBytes': sum((candidate / 'public/models' / n).stat().st_size for n in ('base.glb', 'trees.glb'))}
    (candidate / 'work/incremental-result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)
