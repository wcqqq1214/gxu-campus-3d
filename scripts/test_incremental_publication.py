"""Publication faults and real competing processes must not lose existing assets."""
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'blender'))
from incremental_update import publish, snapshot


CHILD = r'''
import fcntl,json,os,shutil,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from incremental_update import publish
root,candidate,baseline=map(Path,sys.argv[2:5]);mode=sys.argv[5]
original_copy,original_replace,original_lock=shutil.copy2,os.replace,fcntl.flock
paused=False

def copy(source,target,*args,**kwargs):
    global paused
    result=original_copy(source,target,*args,**kwargs)
    if mode=='copy' and not paused and Path(source).is_relative_to(candidate):
        paused=True;print('COPY',flush=True);sys.stdin.readline()
    return result

def replace(source,target):
    global paused
    source,target=Path(source),Path(target)
    if mode in ('rollback','rollbackfail') and 'prepared' in source.parts and target==root/'public/models/base.glb':
        raise OSError('injected install failure')
    if mode in ('rollback','rollbackfail') and not paused and 'restore' in source.parts:
        paused=True;print(mode.upper(),flush=True);sys.stdin.readline()
        if mode=='rollbackfail':raise PermissionError('injected restore failure')
    return original_replace(source,target)

def lock(fd,operation):
    if operation==fcntl.LOCK_EX:print('LOCK_ATTEMPT',flush=True)
    return original_lock(fd,operation)

shutil.copy2=copy;os.replace=replace;fcntl.flock=lock
try:
    publish(root,candidate,json.loads(baseline.read_text()))
    print('SUCCESS',flush=True)
except Exception as error:
    print('ERROR '+str(error),flush=True)
'''


SIGNAL_CHILD = r'''
import os, signal, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from incremental_update import publish, snapshot
root, candidate = map(Path, sys.argv[2:4])
interrupt_target, timing, fail_restore = sys.argv[4:7]
original_replace = os.replace
signal.signal(signal.SIGINT, signal.default_int_handler)

def replace(source, target):
    source, target = Path(source), Path(target)
    interrupt = 'prepared' in source.parts and target == root / interrupt_target
    if interrupt and timing == 'before':
        os.kill(os.getpid(), signal.SIGINT)
    if fail_restore == 'yes' and 'restore' in source.parts and target == root / interrupt_target:
        raise PermissionError('injected restore failure')
    result = original_replace(source, target)
    if interrupt and timing == 'after':
        # The rename has completed, but the caller has not resumed bookkeeping.
        os.kill(os.getpid(), signal.SIGINT)
    return result

os.replace = replace
try:
    publish(root, candidate, snapshot(root))
except KeyboardInterrupt:
    print('INTERRUPTED', flush=True)
except RuntimeError as error:
    print(str(error), flush=True)
else:
    raise AssertionError('SIGINT was not delivered')
'''


class PublicationFaultTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.root, self.candidate = self.directory/'formal', self.directory/'candidate'
        self.names = ['blender/gxu-campus.blend', 'public/data/models.json', 'public/models/base.glb']
        for base, prefix in ((self.root, b'old '), (self.candidate, b'new ')):
            for name in self.names:
                path=base/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(prefix+name.encode())
            (base/'work').mkdir()
        self.before = snapshot(self.root)

    def transactions(self):
        return list((self.root/'work').glob('gxu-publish-*'))

    def interrupt_publication(self, target, timing='after', fail_restore=False):
        result = subprocess.run(
            [sys.executable, '-c', SIGNAL_CHILD, str(ROOT / 'blender'),
             str(self.root), str(self.candidate), target, timing, 'yes' if fail_restore else 'no'],
            capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_sigint_after_successful_replace_restores_every_attempted_file(self):
        for name in self.names:
            with self.subTest(interrupted=name):
                self.assertIn('INTERRUPTED', self.interrupt_publication(name))
                self.assertEqual(snapshot(self.root), self.before)
                self.assertEqual(self.transactions(), [])
        # A real publisher must be able to acquire the released lock and proceed.
        retry = self.start(self.candidate, 'plain')
        output, error = retry.communicate(timeout=10)
        self.assertEqual(retry.returncode, 0, error)
        self.assertIn(b'SUCCESS', output)
        self.assertEqual(snapshot(self.root), snapshot(self.candidate))

    def test_sigint_before_replace_preserves_unmodified_target(self):
        self.assertIn('INTERRUPTED', self.interrupt_publication(self.names[1], timing='before'))
        self.assertEqual(snapshot(self.root), self.before)
        self.assertEqual(self.transactions(), [])

    def test_sigint_after_new_file_install_removes_it_during_rollback(self):
        name = 'public/data/added.json'
        (self.candidate / name).write_bytes(b'new file')
        self.assertIn('INTERRUPTED', self.interrupt_publication(name))
        self.assertFalse((self.root / name).exists())
        self.assertEqual(snapshot(self.root), self.before)
        self.assertEqual(self.transactions(), [])

    def test_sigint_with_failed_restore_retains_backups_and_restores_other_files(self):
        name = self.names[1]
        self.assertIn('Recovery backups retained', self.interrupt_publication(name, fail_restore=True))
        self.assertEqual((self.root / self.names[0]).read_bytes(), b'old ' + self.names[0].encode())
        self.assertEqual((self.root / name).read_bytes(), b'new ' + name.encode())
        transaction, = self.transactions()
        record = json.loads((transaction / 'recovery.json').read_text())
        self.assertEqual(record['state'], 'rollback_incomplete')
        self.assertIn(name, record['rollbackErrors'])
        for original in self.names:
            self.assertEqual((transaction / 'backup' / original).read_bytes(), b'old ' + original.encode())
        with self.assertRaisesRegex(RuntimeError, 'recovery'):
            publish(self.root, self.candidate, snapshot(self.root))

    def test_rollback_verifies_all_restored_files_before_deleting_backups(self):
        original = os.replace
        edited = self.names[1]
        def replace(source, target):
            source, target = Path(source), Path(target)
            if 'prepared' in source.parts and target == self.root / self.names[-1]:
                raise OSError('install failed')
            result = original(source, target)
            if 'restore' in source.parts and target == self.root / self.names[0]:
                # The manifest was restored earlier, then another writer changed it.
                (self.root / edited).write_bytes(b'concurrent edit')
            return result
        with patch('incremental_update.os.replace', side_effect=replace):
            with self.assertRaisesRegex(RuntimeError, 'Recovery'):
                publish(self.root, self.candidate, self.before)
        self.assertEqual((self.root / edited).read_bytes(), b'concurrent edit')
        transaction, = self.transactions()
        record = json.loads((transaction / 'recovery.json').read_text())
        self.assertIn(edited, record['rollbackErrors'])
        self.assertEqual((transaction / 'backup' / edited).read_bytes(), b'old ' + edited.encode())

    def test_failed_restore_keeps_backups_and_attempts_remaining_files(self):
        original=os.replace;attempted=[]
        def fail(source,target):
            source,target=Path(source),Path(target)
            if 'prepared' in source.parts and target==self.root/'public/models/base.glb':
                raise OSError('install failed')
            if 'restore' in source.parts or 'backup' in source.parts:
                attempted.append(str(target.relative_to(self.root)))
                if target==self.root/'public/data/models.json':raise PermissionError('restore denied')
            return original(source,target)
        with patch('incremental_update.os.replace',side_effect=fail):
            with self.assertRaisesRegex(RuntimeError,'Recovery'):
                publish(self.root,self.candidate,self.before)
        self.assertIn('blender/gxu-campus.blend',attempted)
        self.assertEqual((self.root/self.names[0]).read_bytes(),b'old '+self.names[0].encode())
        transaction,=self.transactions()
        record=json.loads((transaction/'recovery.json').read_text())
        self.assertEqual(record['state'],'rollback_incomplete')
        self.assertIn('public/data/models.json',record['rollbackErrors'])
        for name in self.names:
            self.assertEqual((transaction/'backup'/name).read_bytes(),b'old '+name.encode())
        # A later update must not silently adopt the partially restored state.
        with self.assertRaisesRegex(RuntimeError,'recovery'):
            publish(self.root,self.candidate,snapshot(self.root))

    def test_external_edit_during_preparation_aborts_before_install(self):
        original=shutil.copy2;edited=[]
        def copy(source,target,*args,**kwargs):
            result=original(source,target,*args,**kwargs)
            if Path(source).is_relative_to(self.candidate) and not edited:
                (self.root/'public/models/base.glb').write_bytes(b'user edit');edited.append(True)
            return result
        with patch('incremental_update.shutil.copy2',side_effect=copy):
            with self.assertRaisesRegex(RuntimeError,'changed'):
                publish(self.root,self.candidate,self.before)
        self.assertEqual((self.root/'public/models/base.glb').read_bytes(),b'user edit')
        for name in self.names[:2]:
            self.assertEqual((self.root/name).read_bytes(),b'old '+name.encode())
        self.assertEqual(self.transactions(),[])

    def test_external_edit_between_replacements_is_preserved(self):
        original=os.replace;edited=[]
        def replace(source,target):
            result=original(source,target)
            if 'prepared' in Path(source).parts and not edited:
                (self.root/'public/models/base.glb').write_bytes(b'user edit');edited.append(True)
            return result
        with patch('incremental_update.os.replace',side_effect=replace):
            with self.assertRaisesRegex(RuntimeError,'changed'):
                publish(self.root,self.candidate,self.before)
        self.assertEqual((self.root/'public/models/base.glb').read_bytes(),b'user edit')
        for name in self.names[:2]:
            self.assertEqual((self.root/name).read_bytes(),b'old '+name.encode())

    def test_rollback_does_not_overwrite_an_edit_to_an_installed_file(self):
        original=os.replace
        def replace(source,target):
            if 'prepared' in Path(source).parts and Path(target)==self.root/'public/models/base.glb':
                (self.root/'blender/gxu-campus.blend').write_bytes(b'user edit after install')
                raise OSError('install failed')
            return original(source,target)
        with patch('incremental_update.os.replace',side_effect=replace):
            with self.assertRaisesRegex(RuntimeError,'Recovery'):
                publish(self.root,self.candidate,self.before)
        self.assertEqual((self.root/'blender/gxu-campus.blend').read_bytes(),b'user edit after install')
        transaction,=self.transactions()
        self.assertEqual((transaction/'backup/blender/gxu-campus.blend').read_bytes(),b'old blender/gxu-campus.blend')

    def test_failed_removal_of_new_file_does_not_stop_other_restores(self):
        added = 'public/data/added.json'
        (self.candidate / added).write_bytes(b'new file')
        original_replace, original_unlink = os.replace, Path.unlink
        def replace(source, target):
            if 'prepared' in Path(source).parts and Path(target) == self.root / self.names[-1]:
                raise OSError('install failed')
            return original_replace(source, target)
        def unlink(path, *args, **kwargs):
            if path == self.root / added:
                raise PermissionError('remove denied')
            return original_unlink(path, *args, **kwargs)
        with patch('incremental_update.os.replace', side_effect=replace), patch.object(Path, 'unlink', unlink):
            with self.assertRaisesRegex(RuntimeError, 'Recovery'):
                publish(self.root, self.candidate, self.before)
        for name in self.names:
            self.assertEqual((self.root / name).read_bytes(), b'old ' + name.encode())
        transaction, = self.transactions()
        record = json.loads((transaction / 'recovery.json').read_text())
        self.assertIsNone(record['files'][added]['before'])
        self.assertIn(added, record['rollbackErrors'])

    def test_recovery_record_failure_keeps_original_record_and_backups(self):
        original = os.replace
        journals = []
        def replace(source, target):
            source, target = Path(source), Path(target)
            if target.name == 'recovery.json':
                journals.append(target)
                if len(journals) == 2:
                    raise OSError('journal failed')
            if 'restore' in source.parts or ('prepared' in source.parts and target == self.root / self.names[-1]):
                raise OSError('disk failure')
            return original(source, target)
        with patch('incremental_update.os.replace', side_effect=replace):
            with self.assertRaisesRegex(RuntimeError, 'recovery record update failed'):
                publish(self.root, self.candidate, self.before)
        transaction, = self.transactions()
        record = json.loads((transaction / 'recovery.json').read_text())
        self.assertEqual(record['state'], 'publishing')
        for name in self.names:
            self.assertEqual((transaction / 'backup' / name).read_bytes(), b'old ' + name.encode())
        with self.assertRaisesRegex(RuntimeError, 'recovery'):
            publish(self.root, self.candidate, snapshot(self.root))

    def test_candidate_change_during_preparation_is_rejected(self):
        original = shutil.copy2
        def copy(source, target, *args, **kwargs):
            if Path(source) == self.candidate / self.names[0]:
                Path(source).write_bytes(b'not the validated candidate')
            return original(source, target, *args, **kwargs)
        with patch('incremental_update.shutil.copy2', side_effect=copy):
            with self.assertRaisesRegex(RuntimeError, 'Candidate changed'):
                publish(self.root, self.candidate, self.before)
        self.assertEqual(snapshot(self.root), self.before)
        self.assertEqual(self.transactions(), [])

    def test_external_edit_to_unrelated_file_at_last_replace_is_detected(self):
        name = 'public/unrelated.txt'
        for base in (self.root, self.candidate):
            (base / name).write_bytes(b'unrelated')
        before = snapshot(self.root)
        original = os.replace
        def replace(source, target):
            result = original(source, target)
            if 'prepared' in Path(source).parts and Path(target) == self.root / self.names[-1]:
                (self.root / name).write_bytes(b'user edit')
            return result
        with patch('incremental_update.os.replace', side_effect=replace):
            with self.assertRaisesRegex(RuntimeError, 'changed during publication'):
                publish(self.root, self.candidate, before)
        self.assertEqual((self.root / name).read_bytes(), b'user edit')
        for name in self.names:
            self.assertEqual((self.root / name).read_bytes(), b'old ' + name.encode())
        self.assertEqual(self.transactions(), [])

    def start(self,candidate,mode):
        baseline=self.directory/'before.json';baseline.write_text(json.dumps(self.before))
        process=subprocess.Popen([sys.executable,'-c',CHILD,str(ROOT/'blender'),str(self.root),str(candidate),str(baseline),mode],
                                 stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0)
        def cleanup():
            if process.poll() is None:process.kill()
            process.communicate()
        self.addCleanup(cleanup)
        return process

    def line(self,process):
        # Unbuffered pipes avoid hiding the next event in TextIOWrapper's read-ahead buffer.
        line = bytearray()
        while not line.endswith(b'\n'):
            self.assertTrue(select.select([process.stdout],[],[],10)[0],'child did not reach synchronization point')
            value = process.stdout.read(1)
            self.assertTrue(value, 'child exited before synchronization point')
            line.extend(value)
        return line.decode().strip()

    def compete(self,mode):
        other=self.directory/'other';shutil.copytree(self.candidate,other)
        for name in self.names:(other/name).write_bytes(b'second '+name.encode())
        first=self.start(self.candidate,mode)
        self.assertEqual(self.line(first),'LOCK_ATTEMPT')
        self.assertEqual(self.line(first),mode.upper())
        second=self.start(other,'plain')
        self.assertEqual(self.line(second),'LOCK_ATTEMPT')
        self.assertFalse(select.select([second.stdout],[],[],.2)[0],'second publisher entered a locked transaction')
        first_out,first_err=first.communicate(b'release\n',timeout=10)
        second_out,second_err=second.communicate(timeout=10)
        self.assertEqual(first.returncode,0,first_err);self.assertEqual(second.returncode,0,second_err)
        return other,first_out.decode(),second_out.decode()

    def test_two_publishers_serialize_then_reject_stale_baseline(self):
        _,first,second=self.compete('copy')
        self.assertIn('SUCCESS',first)
        self.assertIn('changed while building',second)
        self.assertEqual(snapshot(self.root),snapshot(self.candidate))
        self.assertEqual(self.transactions(),[])

    def test_lock_covers_rollback_and_is_released_after_failure(self):
        other,first,second=self.compete('rollback')
        self.assertIn('install failure',first)
        self.assertIn('SUCCESS',second)
        self.assertEqual(snapshot(self.root),snapshot(other))
        self.assertEqual(self.transactions(),[])

    def test_waiting_publisher_rejects_incomplete_recovery(self):
        _, first, second = self.compete('rollbackfail')
        self.assertIn('Recovery backups retained', first)
        self.assertIn('Unresolved publication recovery', second)
        self.assertEqual(len(self.transactions()), 1)


if __name__=='__main__':unittest.main()
