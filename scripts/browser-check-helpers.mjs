/* Shared UI navigation and recording for the standalone visual checks. */
import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));

export async function openPanelTab(page, name, { legacy = false } = {}) {
  const expand = page.getByRole('button', { name: '展开面板', exact: true });
  if (await expand.isVisible()) await expand.click();
  const back = page.getByRole('button', { name: '返回地点列表', exact: true });
  if (await back.isVisible()) await back.click();
  else if (legacy) {
    const oldBack = page.getByTitle('返回精选地标', { exact: true });
    if (await oldBack.isVisible()) await oldBack.click();
  }
  let tab = page.getByRole('tab', { name, exact: true });
  // Only the saved-before frontend comparison opts into historical labels.
  if (legacy && !(await tab.count())) {
    const oldName = { 地点: '探索', 光影: '环境' }[name] ?? name;
    tab = page.getByRole('tab', { name: oldName, exact: true });
  }
  await tab.click();
}

export async function setLayerEnabled(
  page,
  name,
  enabled,
  { legacy = false } = {},
) {
  let control = page.getByRole('switch', { name: new RegExp(`^${name}`) });
  if (legacy && name === '树木' && !(await control.count()))
    control = page.getByRole('switch', { name: /^林木植被/ });
  if ((await control.getAttribute('aria-checked')) !== String(enabled))
    await control.click();
  if ((await control.getAttribute('aria-checked')) !== String(enabled))
    throw new Error(`Layer failed: ${name}`);
}

export async function runLayerCheck({ cameraFile, cameraId, selected }, check) {
  const phase = process.argv[2];
  if (!phase || !/^[a-z0-9-]+$/.test(phase))
    throw new Error('Supply a recording phase');
  const base =
    process.env.REFINEMENT_URL || 'http://127.0.0.1:4300/gxu-campus-3d/';
  const output = path.join(
    root,
    'docs/model-checks/refinement',
    `${phase}-interaction.json`,
  );
  try {
    await fs.access(output);
    throw new Error(`Recording already exists: ${output}`);
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }
  const input = path.resolve(
    root,
    process.env.REFINEMENT_CAMERAS || cameraFile,
  );
  const cameras = JSON.parse(
    await fs.readFile(input, 'utf8').catch((error) => {
      throw new Error(
        `Cannot read cameras at ${input}; set REFINEMENT_CAMERAS to a preserved camera list`,
        { cause: error },
      );
    }),
  );
  const camera = cameras.find((c) => c.id === cameraId);
  if (!camera) throw new Error(`Camera ${cameraId} is missing from ${input}`);
  const folder = path.join(root, 'docs/screenshots/refinement', phase);
  await fs.mkdir(folder, { recursive: true });
  await fs.mkdir(path.dirname(output), { recursive: true });
  const { chromium } = await import(
    process.env.PLAYWRIGHT_MODULE || 'playwright'
  );
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROMIUM_PATH,
  });
  const report = {
    capturedAt: new Date().toISOString(),
    camera,
    states: [],
    errors: [],
    completed: false,
  };
  let page;
  try {
    const response = await fetch(`${base}data/models.json`);
    if (!response.ok)
      throw new Error(`Manifest request failed: ${response.status}`);
    report.manifestSha256 = createHash('sha256')
      .update(await response.text())
      .digest('hex');
    page = await browser.newPage({
      viewport: { width: 1280, height: 720 },
      deviceScaleFactor: 1,
    });
    page.on('pageerror', (e) => report.errors.push(String(e)));
    page.on('console', (m) => {
      if (m.type() === 'error') report.errors.push(m.text());
    });
    page.on('response', (r) => {
      if (r.status() >= 400) report.errors.push(`${r.status()} ${r.url()}`);
    });
    async function settle() {
      await page.waitForFunction(
        () => {
          const text = document.querySelector('.debug-metrics')?.textContent;
          if (!text) return false;
          const m = JSON.parse(text);
          return m.readyMs > 0 && m.queuedDetails === 0;
        },
        undefined,
        { timeout: 90000 },
      );
      await page.waitForTimeout(2000);
    }
    async function visit(name, near, light = 'day') {
      const hash = new URLSearchParams({
        camera: [...camera.position, ...camera.target].join(','),
        span: camera.span,
        light,
      });
      const place = selected ?? camera.selected;
      if (near && place) hash.set('place', place);
      await page.goto(`${base}?debug&site=${name}#${hash}`);
      await settle();
    }
    async function layer(name, enabled) {
      await setLayerEnabled(page, name, enabled);
      await settle();
    }
    async function capture(name) {
      await page.screenshot({
        path: path.join(folder, `${name}.png`),
        style: '.debug-metrics { visibility: hidden !important; }',
      });
      const state = {
        name,
        url: page.url(),
        metrics: JSON.parse(await page.locator('.debug-metrics').textContent()),
      };
      report.states.push(state);
      console.log(`Captured ${phase}/${name}`);
      return state.metrics;
    }
    await check({
      visit,
      layers: () => openPanelTab(page, '图层'),
      layer,
      capture,
    });
    if (report.errors.length) throw new Error(JSON.stringify(report.errors));
    report.completed = true;
  } catch (error) {
    report.failure = String(error);
    if (page) await page.screenshot({ path: path.join(folder, 'failure.png') });
    throw error;
  } finally {
    try {
      await fs.writeFile(output, JSON.stringify(report, null, 2) + '\n');
    } finally {
      await browser.close();
    }
  }
}
