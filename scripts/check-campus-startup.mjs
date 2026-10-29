/** Paired cold-navigation measurements; intentionally does not equate ready with first paint. */
import fs from 'node:fs/promises';
import path from 'node:path';
const baseline = process.env.BASELINE_URL;
const candidate = process.env.REFINEMENT_URL;
const output = process.env.PERFORMANCE_REPORT;
const rounds = Number(process.env.ROUNDS ?? 5);
if (
  !baseline ||
  !candidate ||
  !output ||
  !Number.isInteger(rounds) ||
  rounds < 3
)
  throw Error(
    'Set BASELINE_URL, REFINEMENT_URL, PERFORMANCE_REPORT; ROUNDS must be >= 3',
  );
try {
  await fs.access(output);
  throw Error('Report already exists');
} catch (error) {
  if (error.code !== 'ENOENT') throw error;
}
const { chromium } = await import(
  process.env.PLAYWRIGHT_MODULE || 'playwright'
);
const software = process.env.SWIFTSHADER === '1';
const rows = [];
for (let round = 0; round < rounds; round++) {
  // Alternate which variant goes first to reduce order/temperature bias.
  const variants =
    round % 2
      ? [
          ['candidate', candidate],
          ['baseline', baseline],
        ]
      : [
          ['baseline', baseline],
          ['candidate', candidate],
        ];
  for (const [variant, address] of variants) {
    const browser = await chromium.launch({
      headless: true,
      executablePath: process.env.CHROMIUM_PATH,
      args: software
        ? [
            '--use-gl=angle',
            '--use-angle=swiftshader',
            '--enable-unsafe-swiftshader',
          ]
        : [],
    });
    try {
      const page = await browser.newPage({
        viewport: { width: 1280, height: 720 },
        deviceScaleFactor: 1,
      });
      const errors = [];
      page.on('pageerror', (error) => errors.push(String(error)));
      page.on('response', (response) => {
        if (response.status() >= 400)
          errors.push(`${response.status()} ${response.url()}`);
      });
      await page.addInitScript(() => {
        window.__startupLongTasks = [];
        new PerformanceObserver((list) =>
          window.__startupLongTasks.push(
            ...list
              .getEntries()
              .map((e) => ({ start: e.startTime, duration: e.duration })),
          ),
        ).observe({ type: 'longtask', buffered: true });
      });
      const cdp = await page.context().newCDPSession(page);
      await cdp.send('Network.enable');
      await cdp.send('Network.setCacheDisabled', { cacheDisabled: true });
      await cdp.send('Network.emulateNetworkConditions', {
        offline: false,
        latency: 60,
        downloadThroughput: 2500000,
        uploadThroughput: 2500000,
      });
      const url = new URL(address);
      url.searchParams.set('debug', '');
      await page.goto(url.href);
      await page.waitForFunction(
        () =>
          JSON.parse(
            document.querySelector('.debug-metrics')?.textContent || '{}',
          ).readyMs > 0,
        undefined,
        { timeout: 90000 },
      );
      const sample = await page.evaluate(() => {
        const metrics = JSON.parse(
          document.querySelector('.debug-metrics').textContent,
        );
        const base = performance
          .getEntriesByType('resource')
          .find((e) => new URL(e.name).pathname.endsWith('/models/base.glb'));
        const gl = document.querySelector('canvas').getContext('webgl2');
        const ext = gl.getExtension('WEBGL_debug_renderer_info');
        const longTasks = window.__startupLongTasks.filter(
          (e) => e.start < metrics.readyMs,
        );
        return {
          readyMs: metrics.readyMs,
          baseBytes: base?.encodedBodySize,
          baseDownloadEndMs: base?.responseEnd,
          postDownloadReadyMs: base ? metrics.readyMs - base.responseEnd : null,
          longestTaskMs: Math.max(0, ...longTasks.map((e) => e.duration)),
          longTasks,
          renderer: ext
            ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL)
            : gl.getParameter(gl.RENDERER),
          hardwareConcurrency: navigator.hardwareConcurrency,
          quality: metrics.quality,
        };
      });
      if (errors.length) throw Error(errors.join('\n'));
      if (!sample.baseBytes || !sample.renderer || !sample.readyMs)
        throw Error('Incomplete startup sample');
      rows.push({ round: round + 1, variant, ...sample });
      console.log(
        JSON.stringify({
          round: round + 1,
          variant,
          readyMs: sample.readyMs,
          longestTaskMs: sample.longestTaskMs,
        }),
      );
    } finally {
      await browser.close();
    }
  }
}
function distribution(values) {
  const sorted = values.toSorted((a, b) => a - b);
  const quantile = (p) => {
    const index = (sorted.length - 1) * p,
      lo = Math.floor(index),
      hi = Math.ceil(index);
    return sorted[lo] + (sorted[hi] - sorted[lo]) * (index - lo);
  };
  return {
    median: quantile(0.5),
    q1: quantile(0.25),
    q3: quantile(0.75),
    min: sorted[0],
    max: sorted.at(-1),
  };
}
const summary = {};
for (const variant of ['baseline', 'candidate']) {
  summary[variant] = Object.fromEntries(
    ['readyMs', 'postDownloadReadyMs', 'longestTaskMs', 'baseBytes'].map(
      (key) => [
        key,
        distribution(
          rows.filter((row) => row.variant === variant).map((row) => row[key]),
        ),
      ],
    ),
  );
}
await fs.mkdir(path.dirname(output), { recursive: true });
await fs.writeFile(
  output,
  JSON.stringify(
    {
      configuration: {
        baseline,
        candidate,
        rounds,
        software,
        network: '20 Mbit/s, 60 ms latency',
        viewport: '1280x720, DPR 1',
        browser: process.env.CHROMIUM_PATH ?? 'Playwright Chromium',
        isolation:
          'fresh browser process and profile per navigation; HTTP cache disabled; no CPU throttling',
      },
      summary,
      rows,
    },
    null,
    2,
  ),
  { flag: 'wx' },
);
console.log(JSON.stringify(summary, null, 2));
