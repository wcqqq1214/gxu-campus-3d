"""Run all (or selected) Blender geometry regressions in a single Blender process."""

import sys
import unittest
from pathlib import Path

import bpy

BLENDER_DIR = Path(__file__).resolve().parent
if str(BLENDER_DIR) not in sys.path:
    sys.path.insert(0, str(BLENDER_DIR))


class IsolatedResult(unittest.TextTestResult):
    """Reset Blender scene and shared material cache before every test case."""

    def startTest(self, test):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        geometry = sys.modules.get('geometry')
        if geometry is not None and hasattr(geometry, 'MATERIALS'):
            geometry.MATERIALS.clear()
        super().startTest(test)


def _load_suite(filters):
    loader = unittest.TestLoader()
    if not filters:
        return loader.discover(str(BLENDER_DIR), pattern='test_*.py')
    suite = unittest.TestSuite()
    for raw in filters:
        name = Path(raw).stem if raw.endswith('.py') else raw
        suite.addTests(loader.loadTestsFromName(name))
    return suite


def main():
    argv = sys.argv[sys.argv.index('--') + 1 :] if '--' in sys.argv else []
    suite = _load_suite(argv)
    if suite.countTestCases() == 0:
        raise SystemExit('未找到任何 Blender 几何回归用例')
    runner = unittest.TextTestRunner(verbosity=2, resultclass=IsolatedResult)
    result = runner.run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)


if __name__ == '__main__':
    main()
