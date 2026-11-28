"""Run scripts/test_*.py in parallel across isolated worker processes."""

import argparse
import concurrent.futures
import io
import os
import sys
import time
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
HEAVY_FIRST = (
    'test_vegetation_reservations',
    'test_public_data_export',
    'test_vegetation_exclusions',
    'test_recessed_entry_site_data',
    'test_building_overrides',
    'test_mapped_canopy_data',
    'test_incremental_publication',
)


def _run_module(args):
    module_name, verbose = args
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    started = time.perf_counter()
    stream = io.StringIO()
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(module_name)
    result = unittest.TextTestRunner(stream=stream, verbosity=2 if verbose else 1).run(
        suite
    )
    elapsed = time.perf_counter() - started
    return (
        module_name,
        result.testsRun,
        result.wasSuccessful(),
        elapsed,
        stream.getvalue(),
    )


def _discover_modules(filters):
    available = {p.stem: p for p in SCRIPTS_DIR.glob('test_*.py')}
    if filters:
        selected = []
        for raw in filters:
            name = Path(raw).stem if raw.endswith('.py') else raw
            if name not in available:
                raise SystemExit(f'未找到测试模块：{raw}')
            if name not in selected:
                selected.append(name)
        return selected
    rank = {name: i for i, name in enumerate(HEAVY_FIRST)}
    return sorted(
        available,
        key=lambda name: (
            rank.get(name, len(HEAVY_FIRST)),
            -available[name].stat().st_size,
        ),
    )


def _worker_count(total):
    raw = os.environ.get('TEST_DATA_WORKERS')
    if raw is not None:
        try:
            count = int(raw)
        except ValueError as error:
            raise SystemExit(f'无效的 TEST_DATA_WORKERS：{raw}') from error
        if count < 1:
            raise SystemExit(f'TEST_DATA_WORKERS 必须 >= 1：{raw}')
        return min(count, total)
    return min(os.cpu_count() or 1, 8, total)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog='其他 unittest discover 参数使用标准库执行。',
        allow_abbrev=False,
    )
    parser.add_argument('modules', nargs='*', help='可选的测试模块名过滤')
    parser.add_argument(
        '-v', '--verbose', action='store_true', help='列出各用例结果及逐模块耗时'
    )
    parser.add_argument(
        '-k', action='append', default=[], help='按用例名子串或通配符过滤，可重复'
    )
    parser.add_argument(
        '-s',
        '--start-directory',
        '-p',
        '--pattern',
        '-t',
        '--top-level-directory',
        dest='discovery_options',
        action='append',
        help=argparse.SUPPRESS,
    )
    args = sys.argv[1:]
    parsed, extra = parser.parse_known_intermixed_args(args)
    if parsed.k or parsed.discovery_options or extra:
        if parsed.modules and not parsed.discovery_options:
            # Named modules use the standard runner too when combined with its options.
            options = ['-v'] if parsed.verbose else []
            for pattern in parsed.k:
                options.extend(('-k', pattern))
            options.extend(extra)
            options.extend(_discover_modules(parsed.modules))
        else:
            options = ['discover', '-s', str(SCRIPTS_DIR), '-p', 'test_*.py', *args]
        unittest.main(module=None, argv=[sys.argv[0], *options])
        return

    modules = _discover_modules(parsed.modules)
    if not modules:
        raise SystemExit('未找到任何 scripts/test_*.py 测试模块')

    workers = _worker_count(len(modules))
    started = time.perf_counter()
    tasks = [(name, parsed.verbose) for name in modules]
    if workers == 1:
        outcomes = [_run_module(task) for task in tasks]
    else:
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
            outcomes = list(pool.map(_run_module, tasks))

    total_tests = 0
    failed = []
    for name, count, ok, elapsed, output in outcomes:
        total_tests += count
        if parsed.verbose:
            status = 'OK' if ok else 'FAIL'
            print(f'{name}: {count} tests in {elapsed:.2f}s [{status}]')
            if ok:
                print(output, end='')
        if not ok:
            failed.append((name, output))

    wall = time.perf_counter() - started
    if failed:
        for name, output in failed:
            print(f'\n=== {name} ===\n{output}', file=sys.stderr)
        raise SystemExit(
            f'数据测试失败：{len(failed)}/{len(modules)} 个模块未通过（共 {total_tests} 用例，{wall:.2f}s）'
        )
    print(
        f'通过 {len(modules)} 个模块 / {total_tests} 个用例（{workers} 进程，{wall:.2f}s）'
    )


if __name__ == '__main__':
    main()
