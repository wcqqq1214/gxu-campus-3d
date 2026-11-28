import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const runner = path.join(root, 'blender/run_geometry_tests.py');
const filters = process.argv.slice(2);

const result = spawnSync(
  process.env.BLENDER_BIN || 'blender',
  [
    '--background',
    '--factory-startup',
    '--disable-autoexec',
    '--python-exit-code',
    '1',
    '--python',
    runner,
    ...(filters.length ? ['--', ...filters] : []),
  ],
  { cwd: root, stdio: 'inherit' },
);

if (result.error) throw result.error;
if (result.status !== 0) process.exit(result.status ?? 1);
