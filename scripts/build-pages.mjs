import { dataVersion } from './data-version.mjs';
import { access, readFile, readdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { runtimeBuildings } from './runtime-data.mjs';
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
const version = await dataVersion(
  path.join(root, 'public/data'),
  await readFile(path.join(root, 'scripts/runtime-data.mjs')),
);
const result = spawnSync(
  process.execPath,
  [path.join(root, 'node_modules/vite/bin/vite.js'), 'build'],
  {
    cwd: root,
    stdio: 'inherit',
    env: {
      ...process.env,
      CAMPUS_BASE_PATH: basePath,
      VITE_DATA_VERSION: version,
    },
  },
);
if (result.error) throw result.error;
if (result.status !== 0) process.exit(result.status ?? 1);
const out = path.join(root, 'out');
const html = await readFile(path.join(out, 'index.html'), 'utf8');
if (!html.includes('西大') || !html.includes(`${basePath}/assets/`))
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
  ...(manifest.treesNear ? [manifest.treesNear] : []),
  ...manifest.zones,
  ...manifest.landmarks,
  ...(manifest.infrastructure ?? []),
  ...(manifest.sports ?? []),
])
  await access(path.join(out, a.url));
for (const a of [
  'data/buildings.json',
  'data/sources.json',
  'draco/draco_decoder.wasm',
  'draco/draco_wasm_wrapper.js',
  'draco/draco_decoder.js',
])
  await access(path.join(out, a));
// Runtime decoder URLs must all point to the one public copy.
const emitted = await readdir(path.join(out, 'assets'));
if (emitted.some((file) => file.startsWith('draco_')))
  throw new Error('构建中存在重复的 Draco 解码器');
// The page loads buildings.json before creating the scene. Publish only the
// fields it reads; public/data keeps the full modelling record.
const buildingsPath = path.join(out, 'data/buildings.json');
await writeFile(
  buildingsPath,
  JSON.stringify(
    runtimeBuildings(JSON.parse(await readFile(buildingsPath, 'utf8'))),
  ),
);
// Pages serves this for any unknown path, so links carry the full prefix.
await writeFile(
  path.join(out, '404.html'),
  `<!doctype html>
<html lang="zh-CN">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>页面不存在 · 广西大学 校园地图</title>
<link rel="icon" href="${basePath}/favicon.svg">
<style>body{margin:0;min-height:100vh;display:grid;place-content:center;gap:12px;text-align:center;font-family:Inter,'PingFang SC','Microsoft YaHei',sans-serif;color:#1d3b31;background:#f4f6f2}h1{margin:0;font-size:20px}a{color:#29a383;font-weight:600}@media (prefers-color-scheme:dark){body{color:#e8f0ec;background:#151a18}}</style>
<h1>页面不存在<br><span lang="en">Page not found</span></h1>
<a href="${basePath}/">返回校园地图 · <span lang="en">Back to the campus map</span></a>
</html>
`,
);
await writeFile(path.join(out, '.nojekyll'), '');
console.log(`GitHub Pages 静态包：${out}；资源前缀：${basePath || '/'}`);
