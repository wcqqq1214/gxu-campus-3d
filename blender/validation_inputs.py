"""Explicit, checked baseline inputs for Blender comparison commands."""

import argparse
from pathlib import Path


def baseline_root(argv, *, flags=('--baseline-root', '--baseline'),
                  files=('blender/gxu-campus.blend',)):
    """Read a baseline after Blender's ``--`` separator, before opening models."""
    args = argv[argv.index('--') + 1:] if '--' in argv else argv[1:]
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(*flags, dest='baseline', type=Path, required=True)
    options, _ = parser.parse_known_args(args)
    root = options.baseline.expanduser().resolve()
    missing = [name for name in files if not (root / name).is_file()]
    if missing:
        parser.error(f'Baseline {root} is missing: {", ".join(missing)}. '
                     'Provide a preserved baseline; current assets are not a substitute.')
    return root
