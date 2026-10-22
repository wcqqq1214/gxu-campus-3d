"""Stage and validate legacy incremental workers before publishing any assets."""
import argparse
from contextlib import contextmanager
import fcntl
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


@contextmanager
def publication_lock(root):
    """Serialize publishers and input copies; keep the lock inode across runs."""
    (root / 'work').mkdir(parents=True, exist_ok=True)
    with (root / 'work/.incremental-publish.lock').open('a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def require_recovered(root):
    pending = sorted((root / 'work').glob('gxu-publish-*/recovery.json'))
    if pending:
        raise RuntimeError(f'Unresolved publication recovery; inspect before retrying: {pending}')


def file_digest(path):
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError:
        return None


def write_recovery(directory, record):
    temporary = directory / 'recovery.tmp'
    temporary.write_text(json.dumps(record, indent=2) + '\n')
    os.replace(temporary, directory / 'recovery.json')


def publish(root, candidate, before):
    """Publish under a repository lock; retain recovery files if rollback is incomplete."""
    with publication_lock(root):
        require_recovered(root)
        return publish_locked(root, candidate, before)


def publish_locked(root, candidate, before):
    if snapshot(root) != before:
        raise RuntimeError('Formal assets changed while building; candidate retained, nothing published')
    after = snapshot(candidate)
    removed = set(before) - set(after)
    if removed:
        raise ValueError(f'Incremental update unexpectedly deleted files: {sorted(removed)}')
    changed = [name for name, digest in after.items() if before.get(name) != digest]
    directory = Path(tempfile.mkdtemp(prefix='gxu-publish-', dir=root / 'work'))
    backup = directory / 'backup'; prepared = directory / 'prepared'
    attempted = []
    retain = False
    record = {'state': 'publishing', 'root': str(root.resolve()), 'candidate': str(candidate.resolve()),
              'files': {name: {'before': before.get(name), 'after': after[name],
                               'backup': str(backup / name) if name in before else None}
                        for name in changed}}
    try:
        for name in changed:
            target = root / name
            if name in before:
                saved = backup / name; saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, saved)
                if file_digest(saved) != before[name]:
                    raise RuntimeError(f'Formal asset changed during preparation: {name}')
            ready = prepared / name; ready.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(candidate / name, ready)
            if file_digest(ready) != after[name]:
                raise RuntimeError(f'Candidate changed during preparation: {name}')
        if snapshot(root) != before:
            raise RuntimeError('Formal assets changed during preparation; nothing published')
        write_recovery(directory, record)
        # Keep a recovery record on unexpected interruption until rollback completes.
        retain = True
        try:
            for name in changed:
                target = root / name; target.parent.mkdir(parents=True, exist_ok=True)
                if file_digest(target) != before.get(name):
                    raise RuntimeError(f'Formal asset changed before replacement: {name}')
                # Record intent first: SIGINT can arrive after rename succeeds but
                # before Python resumes. Rollback reconciles either outcome by hash.
                attempted.append(name)
                os.replace(prepared / name, target)
            if snapshot(root) != after:
                raise RuntimeError('Formal assets changed during publication')
        except BaseException as error:
            failures = {}
            for name in reversed(attempted):
                try:
                    target = root / name
                    current = file_digest(target)
                    if current == before.get(name):
                        continue
                    if current != after[name]:
                        raise RuntimeError('Changed after installation; preserving external edit')
                    if name in before:
                        # Restore from a copy so every original backup survives a failed rollback.
                        ready = directory / 'restore' / name
                        ready.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(backup / name, ready)
                        if file_digest(ready) != before[name]:
                            raise RuntimeError('Backup digest mismatch')
                        if file_digest(target) != current:
                            raise RuntimeError('Changed during rollback; preserving external edit')
                        os.replace(ready, target)
                    else:
                        target.unlink()
                except BaseException as restore_error:
                    failures[name] = repr(restore_error)
            # A successful restore call is not enough: earlier restored files may
            # have changed while later files were recovering. Keep backups unless
            # every attempted target is back to its baseline (or absent if new).
            for name in attempted:
                try:
                    if file_digest(root / name) != before.get(name):
                        failures.setdefault(name, 'Rollback verification differs from baseline')
                except BaseException as verify_error:
                    failures.setdefault(name, repr(verify_error))
            if failures:
                record.update(state='rollback_incomplete', attempted=attempted,
                              publicationError=repr(error), rollbackErrors=failures)
                journal_error = ''
                try:
                    write_recovery(directory, record)
                except BaseException as recovery_error:
                    journal_error = f'; recovery record update failed: {recovery_error!r}'
                raise RuntimeError(f'Publication failed ({error!r}); rollback incomplete: {failures}. '
                                   f'Recovery backups retained at {directory}{journal_error}') from error
            retain = False
            raise
        retain = False
    finally:
        if not retain:
            shutil.rmtree(directory)
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
    with publication_lock(root):
        require_recovered(root)
        before = snapshot(root)
        copy_inputs(root, candidate)
        if snapshot(root) != before:
            raise RuntimeError('Formal assets changed while copying inputs; nothing published')
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
