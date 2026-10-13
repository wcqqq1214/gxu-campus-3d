/** Fixed-pose S0 comparison. Start two previews with the same built frontend. */
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { openPanelTab } from './browser-check-helpers.mjs';

const baseline = process.env.BASELINE_URL;
const candidate = process.env.REFINEMENT_URL;
const output = process.env.PERFORMANCE_REPORT;
if (!baseline || !candidate || !output)
  throw Error('Set BASELINE_URL, REFINEMENT_URL and PERFORMANCE_REPORT');
try {
  await fs.access(output);
  throw Error('Report already exists; choose a new output path');
} catch (e) {
  if (e.code !== 'ENOENT') throw e;
}
await fs.mkdir(path.dirname(output), { recursive: true });
const { chromium } = await import(
  process.env.PLAYWRIGHT_MODULE || 'playwright'
);
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.CHROMIUM_PATH,
});
const page = await browser.newPage({
  viewport: { width: 1280, height: 720 },
  deviceScaleFactor: 2,
});
const rows = [],
  errors = [],
  hashes = { s0: {}, candidate: {} },
  pending = [];
let label = 's0';
page.on('pageerror', (e) => errors.push(String(e)));
page.on('console', (m) => {
  if (m.type() === 'error') errors.push(m.text());
});
page.on('response', (r) => {
  if (r.status() >= 400) errors.push(`${r.status()} ${r.url()}`);
});
page.on('requestfinished', async (request) => {
  const r = await request.response();
  if (!r || !r.url().startsWith('http')) return;
  const pathname = new URL(r.url()).pathname;
  if (
    !/\.(?:js|glb)$/.test(pathname) &&
    !pathname.endsWith('/data/models.json')
  )
    return;
  const role = label;
  pending.push(
    r
      .body()
      .then((bytes) => {
        const sha = createHash('sha256').update(bytes).digest('hex');
        assert.ok(
          !hashes[role][pathname] || hashes[role][pathname] === sha,
          `Asset changed during measurement: ${pathname}`,
        );
        hashes[role][pathname] = sha;
      })
      .catch((e) => errors.push(`${r.url()}: ${e}`)),
  );
});
const metric = async () =>
  JSON.parse(await page.locator('.debug-metrics').textContent());
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
}
const pose =
  'place=library&camera=293.48561877743737,210.12037099347816,933.8260354765424,204.77115631103516,23.81999981403351,490.2537231445313&span=149.3774821192244&light=day';
const median = (values) => {
  const v = [...values].sort((a, b) => a - b);
  return (v[Math.floor((v.length - 1) / 2)] + v[Math.floor(v.length / 2)]) / 2;
};
const angle = (m) => {
  const c = m.benchmark.camera;
  return Math.atan2(c.position[0] - c.target[0], c.position[2] - c.target[2]);
};
const angularDistance = (a, b) =>
  Math.abs(Math.atan2(Math.sin(a - b), Math.cos(a - b)));
let failure = null,
  summary = null;
try {
  for (const tier of ['精细', '流畅'])
    for (let repeat = 1; repeat <= 3; repeat++)
      for (const [name, base] of [
        ['s0', baseline],
        ['candidate', candidate],
      ]) {
        label = name;
        const url = new URL(base);
        url.search =
          '?lang=zh&debug&benchmark=fixed-orbit&capture=' + Date.now();
        url.hash = pose;
        await page.goto(url.href);
        await settle();
        await openPanelTab(page, '光影');
        const quality = page.locator('.quality-disclosure');
        if (!(await quality.evaluate((e) => e.open)))
          await quality.locator('summary').click();
        await page.getByRole('radio', { name: tier, exact: true }).click();
        await page.getByRole('button', { name: /^返回\s*图书馆$/ }).click();
        await settle();
        await page.waitForFunction(
          (t) => {
            const m = JSON.parse(
              document.querySelector('.debug-metrics').textContent,
            );
            return (
              m.quality === t &&
              m.queuedDetails === 0 &&
              m.postprocessing === (t === '精细' ? 'ready' : 'off')
            );
          },
          tier,
          { timeout: 90000 },
        );
        await Promise.all(pending);
        assert.deepEqual(errors, []);
        const initial = await metric();
        assert.equal(initial.benchmark.orbiting, false);
        assert.equal(initial.benchmark.sampleIndex, 0);
        assert.ok(
          Math.abs(initial.benchmark.camera.position[0] - 293.48561877743737) <
            1e-4,
        );
        if (rows.length)
          assert.deepEqual(initial.benchmark, rows[0].initial.benchmark);
        const samples = [];
        const started = Date.now();
        await page.getByRole('button', { name: '环绕', exact: true }).click();
        while (samples.length < 21) {
          assert.ok(Date.now() - started < 45000, 'Sampling stalled');
          await page.waitForTimeout(60);
          const m = await metric();
          if (
            !m.benchmark.orbiting ||
            m.benchmark.sampleIndex <= samples.length
          )
            continue;
          assert.equal(
            m.benchmark.sampleIndex,
            samples.length + 1,
            'Missing metric window',
          );
          assert.equal(m.quality, tier);
          assert.equal(m.automaticQualityLevel, 1);
          assert.equal(m.queuedDetails, 0);
          assert.equal(m.postprocessing, tier === '精细' ? 'ready' : 'off');
          assert.equal(m.pixelRatio, tier === '精细' ? 1.75 : 1.125);
          assert.deepEqual(m.benchmark.frame, initial.benchmark.frame);
          assert.deepEqual(m.benchmark.viewport, [1280, 720]);
          assert.deepEqual(
            m.benchmark.camera.target,
            initial.benchmark.camera.target,
          );
          assert.ok(
            Math.abs(m.benchmark.camera.span - initial.benchmark.camera.span) <
              1e-9,
            'Camera span changed',
          );
          const lateness =
            m.benchmark.elapsedMs - m.benchmark.sampleIndex * 1500;
          assert.ok(
            lateness >= 0 && lateness < 200,
            `Late metric window: ${lateness}ms`,
          );
          assert.ok(
            angularDistance(
              angle(m),
              angle(initial) + m.benchmark.elapsedMs * 0.00013,
            ) < 1e-7,
            'Orbit deviated from wall-clock route',
          );
          samples.push(m);
        }
        const row = {
          label,
          tier,
          repeat,
          initial,
          samples,
          durationMs: Date.now() - started,
          median: Object.fromEntries(
            ['fps', 'triangles', 'drawCalls'].map((k) => [
              k,
              median(samples.slice(2).map((s) => s[k])),
            ]),
          ),
        };
        rows.push(row);
        await fs.writeFile(
          output + '.partial.json',
          JSON.stringify({ rows, hashes, errors }, null, 2) + '\n',
        );
        console.log(label, tier, repeat, row.median);
        await Promise.all(pending);
      }
  let maxPhase = 0;
  for (let i = 0; i < rows.length; i += 2)
    for (let j = 0; j < 21; j++)
      maxPhase = Math.max(
        maxPhase,
        angularDistance(
          angle(rows[i].samples[j]),
          angle(rows[i + 1].samples[j]),
        ),
      );
  assert.ok(maxPhase < 0.03, `Paired orbit phase mismatch: ${maxPhase}`);
  for (const [name, sha] of Object.entries(hashes.candidate).filter(([name]) =>
    name.endsWith('.js'),
  ))
    assert.equal(hashes.s0[name], sha, `Different frontend: ${name}`);
  const tiers = {};
  for (const tier of ['精细', '流畅']) {
    const values = Object.fromEntries(
      ['s0', 'candidate'].map((role) => [
        role,
        Object.fromEntries(
          ['fps', 'triangles', 'drawCalls'].map((k) => [
            k,
            median(
              rows
                .filter((r) => r.label === role && r.tier === tier)
                .map((r) => r.median[k]),
            ),
          ]),
        ),
      ]),
    );
    const delta = Object.fromEntries(
      ['fps', 'triangles', 'drawCalls'].map((k) => [
        k,
        (values.candidate[k] / values.s0[k] - 1) * 100,
      ]),
    );
    tiers[tier] = {
      ...values,
      deltaPercent: delta,
      passed:
        delta.fps >= -10 && delta.triangles <= 15 && delta.drawCalls <= 15,
    };
  }
  summary = { maxPairedPhaseDifference: maxPhase, tiers };
  assert.ok(
    Object.values(tiers).every((t) => t.passed),
    'Performance budget exceeded',
  );
} catch (e) {
  failure = String(e);
} finally {
  await Promise.all(pending);
  await browser.close();
  await fs.writeFile(
    output,
    JSON.stringify(
      {
        passed: !failure && !errors.length,
        failure,
        scope:
          '12 alternating S0/candidate rounds, three per manual tier. Fixed shared camera and frontend; 21 timed publications, discard first two; median per round then median of three. Enforce sample indices, elapsed-time camera path, <=200ms sample lateness, <0.03rad paired phase, identical viewport/profile and zero queued details. No FPS-based exclusions. No exclusive-device, cold-cache or physical-mobile claim.',
        summary,
        rows,
        hashes,
        errors,
      },
      null,
      2,
    ) + '\n',
  );
}
if (failure || errors.length) throw Error(failure || errors.join('\n'));
console.log(JSON.stringify(summary, null, 2));
