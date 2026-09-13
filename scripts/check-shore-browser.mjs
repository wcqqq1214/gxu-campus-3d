/* Shore visual checks through production UI: retained layers and night. */
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = fileURLToPath(new URL('../', import.meta.url));
const phase = process.argv[2];
if (!phase || !/^[a-z0-9-]+$/.test(phase)) throw new Error('Supply a recording phase');
const base = process.env.REFINEMENT_URL || 'http://127.0.0.1:4300/gxu-campus-3d/';
const output = path.join(root, 'docs/model-checks/refinement', `${phase}-interaction.json`);
try {
  await fs.access(output);
  throw new Error('Recording already exists');
} catch (error) {
  if (error.code !== 'ENOENT') throw error;
}
const folder = path.join(root, 'docs/screenshots/refinement', phase);
await fs.mkdir(folder, { recursive: true });
const cameras = JSON.parse(await fs.readFile(path.join(root, 'docs/model-checks/refinement/s4-shore-cameras.json')));
const camera = cameras.find((c) => c.id === 'jinghu-auditorium-bank');
const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_PATH });
const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
const report = { capturedAt: new Date().toISOString(), camera, states: [], errors: [], completed: false };
page.on('pageerror', (e) => report.errors.push(String(e)));
page.on('console', (m) => { if (m.type() === 'error') report.errors.push(m.text()); });
page.on('response', (r) => { if (r.status() >= 400) report.errors.push(`${r.status()} ${r.url()}`); });
const metrics = async () => JSON.parse(await page.locator('.debug-metrics').textContent());
async function settle() {
  await page.waitForFunction(() => {
    const text = document.querySelector('.debug-metrics')?.textContent;
    if (!text) return false;
    const m = JSON.parse(text);
    return m.readyMs > 0 && m.queuedDetails === 0;
  }, undefined, { timeout: 90000 });
  await page.waitForTimeout(2000);
}
async function visit(name, near, light = 'day') {
  const hash = new URLSearchParams({ camera: [...camera.position, ...camera.target].join(','), span: camera.span, light });
  if (near) hash.set('place', 'auditorium');
  await page.goto(`${base}?debug&site=${name}#${hash}`);
  await settle();
}
async function layers() {
  const back = page.getByTitle('返回精选地标', { exact: true });
  if (await back.count()) await back.click();
  await page.getByRole('tab', { name: '图层', exact: true }).click();
}
async function layer(name, enabled) {
  // The enclosing label contributes its description to the accessible name.
  const control = page.getByRole('switch', { name: new RegExp(`^${name}`) });
  if ((await control.getAttribute('aria-checked')) !== String(enabled)) await control.click();
  if ((await control.getAttribute('aria-checked')) !== String(enabled)) throw new Error(`Layer failed: ${name}`);
  await settle();
}
async function capture(name) {
  await page.screenshot({ path: path.join(folder, `${name}.png`), style: '.debug-metrics { visibility: hidden !important; }' });
  const state = { name, url: page.url(), metrics: await metrics() };
  report.states.push(state);
  console.log(`Captured ${phase}/${name}`);
  return state.metrics;
}
try {
  await visit('near', true);
  await layers();
  await layer('地点名称', false);
  const near = await capture('near-labels-off');
  await layer('湖塘水面', false);
  const noWater = await capture('water-off');
  if (noWater.triangles >= near.triangles) throw new Error('Water layer did not remove geometry');
  await layer('湖塘水面', true);
  await capture('water-restored');
  await layer('道路与桥梁', false);
  const hidden = await capture('roads-off');
  if (hidden.triangles >= near.triangles) throw new Error('Road layer did not remove geometry');
  await layer('道路与桥梁', true);
  await layer('校园建筑', false);
  await capture('paving-with-buildings-off');
  await layer('校园建筑', true);
  const restored = await capture('layers-restored');
  await layer('林木植被', false);
  const noTrees = await capture('vegetation-off');
  if (noTrees.triangles >= restored.triangles) throw new Error('Vegetation layer did not remove geometry');
  await layer('林木植被', true);
  const treesRestored = await capture('vegetation-restored');
  if (treesRestored.triangles <= noTrees.triangles) throw new Error('Vegetation instances were not restored');
  await visit('night', true, 'night');
  await layers();
  await layer('地点名称', false);
  await capture('night-labels-off');
  if (report.errors.length) throw new Error(JSON.stringify(report.errors));
  report.completed = true;
} catch (error) {
  report.failure = String(error);
  await page.screenshot({ path: path.join(folder, 'failure.png') });
  throw error;
} finally {
  await fs.writeFile(output, JSON.stringify(report, null, 2) + '\n');
  await browser.close();
}
