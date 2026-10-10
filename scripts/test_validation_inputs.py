"""Comparison commands must not silently use missing historical model inputs."""

from contextlib import redirect_stderr
import io
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'blender'))
from validation_inputs import baseline_root


class BaselineInputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'blender').mkdir()
        (self.root / 'blender/gxu-campus.blend').write_bytes(b'baseline')

    def test_accepts_blender_arguments_and_existing_option_alias(self):
        for args in [[f'--baseline={self.root}'], ['--baseline-root', str(self.root)]]:
            with self.subTest(args=args):
                result = baseline_root(['blender', '--background', '--',
                                        '--report-prefix=check', *args])
                self.assertEqual(result, self.root.resolve())

    def test_requires_explicit_baseline(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            baseline_root(['blender', '--', '--report-prefix=check'])
        self.assertEqual(error.exception.code, 2)

    def test_rejects_incomplete_baseline_before_opening_models(self):
        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit):
            baseline_root(['blender', '--', f'--baseline-root={self.root}'],
                          files=('blender/gxu-campus.blend', 'public/models/base.glb'))
        self.assertIn('public/models/base.glb', stderr.getvalue())

    def test_suite_can_choose_distinct_road_and_connection_inputs(self):
        other = self.root / 'connection'
        (other / 'blender').mkdir(parents=True)
        (other / 'blender/gxu-campus.blend').write_bytes(b'connection baseline')
        args = ['blender', '--', f'--road-baseline-root={self.root}',
                f'--connection-baseline-root={other}']
        self.assertEqual(baseline_root(args, flags=('--road-baseline-root',)), self.root.resolve())
        self.assertEqual(baseline_root(args, flags=('--connection-baseline-root',)), other.resolve())


if __name__ == '__main__':
    unittest.main()
