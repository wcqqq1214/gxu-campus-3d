/* Fixed-camera visual records and sustained, repeatable UI-driven measurements.
 * Provide Playwright via PLAYWRIGHT_MODULE and Chromium via CHROMIUM_PATH.
 * Usage: node scripts/check-refinement-browser.mjs baseline [--captures-only]
 */
import * as fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
const { chromium } = await import(
  process.env.PLAYWRIGHT_MODULE || 'playwright'
);
const root = fileURLToPath(new URL('../', import.meta.url));
const phase = process.argv[2];
if (!phase || !/^[a-z0-9-]+$/.test(phase))
  throw new Error('Supply a recording phase');
const base =
  process.env.REFINEMENT_URL || 'http://127.0.0.1:4300/gxu-campus-3d/';
const reports = path.join(root, 'docs/model-checks/refinement');
const screenshots = path.join(root, 'docs/screenshots/refinement', phase);
const read = async (name) =>
  JSON.parse(await fs.readFile(path.join(root, name), 'utf8'));
const median = (values) =>
  [...values].sort((a, b) => a - b)[Math.floor(values.length / 2)];
const metrics = async (page) =>
  JSON.parse(await page.locator('.debug-metrics').textContent());
async function settled(page) {
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
  await page.waitForTimeout(1800);
}
async function quality(page, name) {
  if (await page.getByTitle('返回精选地标', { exact: true }).count())
    await page.getByTitle('返回精选地标', { exact: true }).click();
  await page.getByRole('tab', { name: '环境', exact: true }).click();
  await page.getByRole('radio', { name: new RegExp(`^${name}`) }).click();
  const back = page.getByRole('button', { name: /返回 图书馆/ });
  if (await back.count()) await back.click();
  else await page.getByRole('tab', { name: '探索', exact: true }).click();
  await settled(page);
}
async function main() {
  const output = path.join(reports, `${phase}-browser.json`);
  try {
    await fs.access(output);
    throw new Error(`Recording already exists: ${output}`);
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }
  await fs.mkdir(screenshots, { recursive: true });
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROMIUM_PATH,
  });
  const report = {
    phase,
    capturedAt: new Date().toISOString(),
    browser: browser.version(),
    environment: {
      platform: os.platform(),
      release: os.release(),
      cpu: os.cpus()[0].model,
      headless: true,
      deviceScaleFactor: 1,
      viewport: { width: 1280, height: 720 },
    },
    assetManifest: await (await fetch(`${base}data/models.json`)).json(),
    method:
      'Local production preview; UI controls; existing DOM debug metrics; mobile is desktop viewport simulation. Screenshots hide only the debug metrics overlay.',
    captures: [],
    lodCycles: [],
    performance: [],
    errors: [],
  };
  try {
    const context = await browser.newContext({
      viewport: report.environment.viewport,
      deviceScaleFactor: 1,
    });
    const page = await context.newPage();
    const observe = (target) => {
      target.on('pageerror', (error) => report.errors.push(String(error)));
      target.on('console', (message) => {
        if (message.type() === 'error') report.errors.push(message.text());
      });
      target.on('response', (response) => {
        if (response.status() >= 400)
          report.errors.push(`${response.status()} ${response.url()}`);
      });
    };
    observe(page);
    const cameras = await read(
      process.env.REFINEMENT_CAMERAS ||
        'docs/model-checks/refinement/cameras.json',
    );
    // Capture each camera in a fresh load and explicitly select the fine tier.
    for (const camera of cameras) {
      const hash = new URLSearchParams({
        light: camera.light,
        camera: [...camera.position, ...camera.target].join(','),
        span: camera.span,
      });
      if (camera.selected) hash.set('place', camera.selected);
      // Fragment-only navigation does not remount the scene.
      const url = `${base}?debug&refinement=${camera.id}#${hash}`;
      await page.goto(url);
      await settled(page);
      await quality(page, '精细');
      const file = `${camera.id}.png`;
      await page.screenshot({
        path: path.join(screenshots, file),
        style: '.debug-metrics { visibility: hidden !important; }',
      });
      report.captures.push({
        file,
        url,
        camera,
        viewport: page.viewportSize(),
        metrics: await metrics(page),
      });
      console.log(`Captured ${phase}/${file}`);
    }
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(
      `${base}?debug&refinement=mobile#place=library&view=rear-entrance&light=day`,
    );
    await settled(page);
    await page.screenshot({
      path: path.join(screenshots, 'library-mobile.png'),
      style: '.debug-metrics { visibility: hidden !important; }',
    });
    report.captures.push({
      file: 'library-mobile.png',
      url: page.url(),
      viewport: page.viewportSize(),
      metrics: await metrics(page),
    });
    await page.setViewportSize(report.environment.viewport);
    if (!process.argv.includes('--captures-only')) {
      await page.goto(
        `${base}?debug&refinement=lod#place=library&view=rear-entrance&light=day`,
      );
      await settled(page);
      await quality(page, '精细');
      for (let repeat = 1; repeat <= 3; repeat++) {
        await page
          .getByRole('button', { name: '北门近景', exact: true })
          .click();
        await settled(page);
        await page.waitForFunction(
          () => {
            const m = JSON.parse(
              document.querySelector('.debug-metrics').textContent,
            );
            return m.loadedDetails.some((id) => id.startsWith('chunk-'));
          },
          undefined,
          { timeout: 20000 },
        );
        const near = await metrics(page);
        if (!near.loadedDetails.some((id) => id.startsWith('chunk-')))
          throw new Error('Near camera did not load ordinary building chunks');
        await page.getByTitle('返回全景', { exact: true }).click();
        await settled(page);
        // Metrics refresh after camera tween and resource reconciliation.
        await page.waitForFunction(
          () => {
            const m = JSON.parse(
              document.querySelector('.debug-metrics').textContent,
            );
            return (
              !m.loadedDetails.some((id) => id.startsWith('chunk-')) &&
              m.queuedDetails === 0
            );
          },
          undefined,
          { timeout: 20000 },
        );
        const far = await metrics(page);
        if (far.loadedDetails.some((id) => id.startsWith('chunk-')))
          throw new Error('Overview did not unload ordinary building chunks');
        report.lodCycles.push({ repeat, near, far });
        await page.getByRole('tab', { name: '探索', exact: true }).click();
        await page.locator('button[data-place-id="library"]').click();
        await settled(page);
      }
      for (const tier of ['精细', '流畅']) {
        // A new browser context starts without HTTP cache for each tier.
        const perfContext = await browser.newContext({
          viewport: report.environment.viewport,
          deviceScaleFactor: 1,
        });
        const perf = await perfContext.newPage();
        observe(perf);
        await perf.goto(`${base}?debug#place=library&view=back&light=day`);
        await settled(perf);
        const coldStart = await metrics(perf);
        await quality(perf, tier);
        for (let repeat = 1; repeat <= 3; repeat++) {
          await perf.getByRole('button', { name: '北侧', exact: true }).click();
          await settled(perf);
          await perf
            .getByRole('button', { name: '环绕观察', exact: true })
            .click();
          const samples = [];
          const started = Date.now();
          while (Date.now() - started < 30000) {
            await perf.waitForTimeout(1600);
            samples.push(await metrics(perf));
          }
          await perf
            .getByRole('button', { name: '暂停环绕', exact: true })
            .click();
          const finished = Date.now();
          const row = {
            tier,
            repeat,
            startedAt: new Date(started).toISOString(),
            finishedAt: new Date(finished).toISOString(),
            durationMs: finished - started,
            coldStart,
            samples,
            medianFPS: median(samples.map((s) => s.fps)),
            medianTriangles: median(samples.map((s) => s.triangles)),
            medianDrawCalls: median(samples.map((s) => s.drawCalls)),
          };
          report.performance.push(row);
          await fs.writeFile(output, JSON.stringify(report, null, 2) + '\n');
          console.log(
            `${phase}: ${tier} ${repeat}/3, median ${row.medianFPS} FPS`,
          );
        }
        await perfContext.close();
      }
    }
    report.completed = true;
  } catch (error) {
    report.failure = String(error);
    throw error;
  } finally {
    await fs.writeFile(output, JSON.stringify(report, null, 2) + '\n');
    await browser.close();
  }
  if (report.errors.length) throw new Error(JSON.stringify(report.errors));
}
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
