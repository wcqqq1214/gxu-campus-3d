import { readdir } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const directory = path.join(root, 'blender');
const tests = (await readdir(directory, { withFileTypes: true }))
  .filter((entry) => entry.isFile() && /^test_.*\.py$/.test(entry.name))
  .map((entry) => entry.name)
  .sort();
if (!tests.length) throw new Error('未找到 Blender 几何回归入口');

for (const test of tests) {
  console.log(`\nBlender 几何回归：${test}`);
  const result = spawnSync(
    process.env.BLENDER_BIN || 'blender',
    [
      '--background',
      '--factory-startup',
      '--disable-autoexec',
      '--python-exit-code',
      '1',
      '--python',
      path.join(directory, test),
    ],
    { cwd: root, stdio: 'inherit' },
  );
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}
console.log(`\n通过 ${tests.length} 份 Blender 几何回归脚本`);
