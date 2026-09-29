// Compare saved pre-change and current production builds, including layer switches.
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
const { chromium } = await import(
  process.env.PLAYWRIGHT_MODULE || 'playwright'
);
const phase = process.argv[2];
assert(phase && /^[a-z0-9-]+$/.test(phase));
const reportPath = `docs/model-checks/refinement/${phase}-visual.json`;
await assert.rejects(fs.access(reportPath), { code: 'ENOENT' });
const sports = JSON.parse(await fs.readFile('public/data/sports.json', 'utf8'));
const includeCourts = process.argv.includes('--courts');
if (includeCourts) {
  const data = JSON.parse(
    await fs.readFile('public/data/basketball.json', 'utf8'),
  );
  for (const bank of ['basketball-bank-897194442', 'basketball-bank-east']) {
    const courts = data.courts.filter((c) => c.bank === bank);
    assert(courts.length);
    sports.push({
      id: bank,
      center: [0, 1].map(
        (i) => courts.reduce((s, c) => s + c.center[i], 0) / courts.length,
      ),
      elevation: courts[0].elevation,
    });
  }
}
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.CHROMIUM_PATH,
});
const report = {
  completed: false,
  errors: [],
  states: [],
  method:
    'Saved before production frontend (BEFORE_FRONTEND_ROOT route fulfillment or BEFORE_URL); current production frontend; same unchanged assets, camera and viewport. Desktop mobile-size simulation.',
};
try {
  for (const variant of ['before', 'after']) {
    const context = await browser.newContext({
      viewport: { width: 1280, height: 720 },
      deviceScaleFactor: 1,
    });
    if (variant === 'before' && process.env.BEFORE_FRONTEND_ROOT) {
      const saved = path.resolve(process.env.BEFORE_FRONTEND_ROOT);
      await context.route('http://127.0.0.1:4300/**', async (route) => {
        let pathname = new URL(route.request().url()).pathname.replace(
          /^\/gxu-campus-3d(?=\/|$)/,
          '',
        );
        if (pathname.endsWith('/')) pathname += 'index.html';
        const file = path.resolve(saved, '.' + pathname);
        assert(file.startsWith(saved + path.sep));
        const types = {
          '.html': 'text/html',
          '.js': 'text/javascript',
          '.css': 'text/css',
          '.json': 'application/json',
          '.geojson': 'application/json',
          '.wasm': 'application/wasm',
        };
        await route.fulfill({
          body: await fs.readFile(file),
          contentType: types[path.extname(file)] || 'application/octet-stream',
        });
      });
    }
    const page = await context.newPage();
    page.on('pageerror', (e) => report.errors.push(String(e)));
    page.on('console', (m) => {
      if (m.type() === 'error') report.errors.push(m.text());
    });
    page.on('response', (r) => {
      if (r.status() >= 400) report.errors.push(`${r.status()} ${r.url()}`);
    });
    const base =
      variant === 'before'
        ? process.env.BEFORE_FRONTEND_ROOT
          ? 'http://127.0.0.1:4300/gxu-campus-3d/'
          : process.env.BEFORE_URL || 'http://127.0.0.1:4312/gxu-campus-3d/'
        : process.env.REFINEMENT_URL || 'http://127.0.0.1:4300/gxu-campus-3d/';
    async function settle() {
      await page.waitForFunction(
        () => {
          const t = document.querySelector('.debug-metrics')?.textContent;
          if (!t) return false;
          const m = JSON.parse(t);
          return m.readyMs > 0 && m.queuedDetails === 0;
        },
        undefined,
        { timeout: 90000 },
      );
      await page.waitForTimeout(2000);
    }
    for (const [id, light, mobile] of [
      ['west-track', 'day', false],
      ['east-track', 'day', false],
      ['west-track', 'night', false],
      ['west-track', 'day', true],
      ...(includeCourts
        ? [
            ['basketball-bank-897194442', 'day', false],
            ['basketball-bank-east', 'day', false],
            ['basketball-bank-east', 'night', false],
            ['basketball-bank-east', 'day', true],
          ]
        : []),
    ]) {
      const s = sports.find((s) => s.id === id),
        [x, y] = s.center;
      const position = [x + (mobile ? 60 : 140), 210, -y + 210];
      const target = [x, s.elevation, -y],
        span = mobile ? 130 : 145;
      await page.setViewportSize(
        mobile ? { width: 390, height: 844 } : { width: 1280, height: 720 },
      );
      const hash = new URLSearchParams({
        light,
        camera: [...position, ...target].join(','),
        span,
      });
      await page.goto(
        `${base}?debug&batch-check=${id}-${light}-${mobile}#${hash}`,
      );
      await settle();
      await page.getByRole('tab', { name: '图层', exact: true }).click();
      for (const name of ['林木植被', '地点名称']) {
        const control = page.getByRole('switch', {
          name: new RegExp(`^${name}`),
        });
        if ((await control.getAttribute('aria-checked')) === 'true')
          await control.click();
      }
      await page.getByRole('tab', { name: '探索', exact: true }).click();
      await settle();
      const folder = `docs/screenshots/refinement/${phase}/${variant}`;
      await fs.mkdir(folder, { recursive: true });
      const file = path.join(
        folder,
        `${id}-${light}${mobile ? '-mobile' : ''}.png`,
      );
      const metrics = JSON.parse(
        await page.locator('.debug-metrics').textContent(),
      );
      await page.screenshot({
        path: file,
        style: '.debug-metrics{visibility:hidden!important}',
      });
      const state = {
        variant,
        file,
        id,
        light,
        mobile,
        position,
        target,
        span,
        metrics,
      };
      if (id === 'west-track' && light === 'day' && !mobile) {
        await page.getByRole('tab', { name: '图层', exact: true }).click();
        const control = page.getByRole('switch', { name: /^运动场地/ });
        assert.equal(await control.getAttribute('aria-checked'), 'true');
        await control.click();
        await settle();
        state.sportsOff = JSON.parse(
          await page.locator('.debug-metrics').textContent(),
        );
        await control.click();
        await settle();
        state.sportsRestored = JSON.parse(
          await page.locator('.debug-metrics').textContent(),
        );
        assert(state.sportsOff.triangles < metrics.triangles);
        assert.equal(state.sportsRestored.triangles, metrics.triangles);
      }
      report.states.push(state);
      await fs.writeFile(reportPath, JSON.stringify(report, null, 2) + '\n');
      console.log(file);
    }
    await context.close();
  }
  assert.deepEqual(report.errors, []);
  report.completed = true;
} finally {
  await fs.writeFile(reportPath, JSON.stringify(report, null, 2) + '\n');
  await browser.close();
}
