import { access, cp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
const root = fileURLToPath(new URL('../', import.meta.url));
const repository =
  process.env.GITHUB_REPOSITORY?.split('/').at(-1) ?? 'gxu-campus-3d';
const basePath = (
  process.env.PAGES_BASE_PATH ??
  (repository.endsWith('.github.io') ? '' : `/${repository}`)
).replace(/\/$/, '');
if (
  !/^(\/[A-Za-z0-9._-]+)*$/.test(basePath) ||
  basePath.split('/').some((p) => p === '.' || p === '..')
)
  throw new Error('无效的 Pages 子路径');
const result = spawnSync(
  process.execPath,
  [path.join(root, 'node_modules/vinext/dist/cli.js'), 'build'],
  {
    cwd: root,
    stdio: 'inherit',
    env: { ...process.env, NEXT_PUBLIC_BASE_PATH: basePath },
  },
);
if (result.error) throw result.error;
if (result.status !== 0) process.exit(result.status ?? 1);
const client = path.join(root, 'dist/client'),
  out = path.join(root, 'out');
await rm(out, { recursive: true, force: true });
await mkdir(out, { recursive: true });
await cp(client, out, { recursive: true });
// Pages supplies the repository prefix; Vinext also puts route files beneath it on disk.
if (basePath) {
  await cp(path.join(client, basePath.slice(1)), out, { recursive: true });
  await rm(path.join(out, basePath.slice(1)), { recursive: true, force: true });
}
const html = await readFile(path.join(out, 'index.html'), 'utf8');
if (!html.includes('西大') || !html.includes(`${basePath}/_next/static/`))
  throw new Error('静态页面或资源前缀缺失');
for (const [, url] of html.matchAll(/(?:src|href)="([^"]+)"/g)) {
  if (!url.startsWith('/') || url.startsWith('//')) continue;
  if (!url.startsWith(`${basePath}/`)) throw new Error(`资源缺少前缀：${url}`);
  await access(path.join(out, url.slice(basePath.length + 1).split('?')[0]));
}
const manifest = JSON.parse(
  await readFile(path.join(out, 'data/models.json'), 'utf8'),
);
for (const a of [
  manifest.base,
  manifest.trees,
  ...manifest.zones,
  ...manifest.landmarks,
])
  await access(path.join(out, a.url));
for (const a of [
  'data/buildings.json',
  'data/sources.json',
  'draco/draco_decoder.wasm',
  'draco/draco_wasm_wrapper.js',
])
  await access(path.join(out, a));
await rm(path.join(out, '.vite'), { recursive: true, force: true });
await writeFile(path.join(out, '.nojekyll'), '');
console.log(`GitHub Pages 静态包：${out}；资源前缀：${basePath || '/'}`);
