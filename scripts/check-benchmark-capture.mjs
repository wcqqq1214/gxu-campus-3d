/** Browser fixture for delayed reads, duplicate updates, and real source gaps. */
import assert from 'node:assert/strict';
import { beginBenchmarkCapture } from './benchmark-capture.mjs';
const { chromium } = await import(
  process.env.PLAYWRIGHT_MODULE || 'playwright'
);
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.CHROMIUM_PATH,
});
try {
  const page = await browser.newPage();
  await page.setContent('<pre class="debug-metrics"></pre>');
  const capture = await page.evaluateHandle(beginBenchmarkCapture);
  // Publish in separate browser tasks without making any automation reads.
  await page.evaluate(async () => {
    const node = document.querySelector('.debug-metrics');
    for (const sampleIndex of [1, 2, 3, 4, 5]) {
      node.textContent = JSON.stringify({
        benchmark: { orbiting: true, sampleIndex },
        fps: 60 - sampleIndex,
      });
      await new Promise((resolve) => setTimeout(resolve, 30));
    }
  });
  const legacyLatest = JSON.parse(
    await page.locator('.debug-metrics').textContent(),
  );
  assert.equal(legacyLatest.benchmark.sampleIndex, 5);
  const all = await capture.evaluate((state) => state.samples.splice(0));
  assert.deepEqual(
    all.map((m) => m.benchmark.sampleIndex),
    [1, 2, 3, 4, 5],
  );
  assert.deepEqual(
    all.map((m) => m.fps),
    [59, 58, 57, 56, 55],
  );
  // A duplicate publication must not overwrite the original timed sample.
  // A genuine missing index must remain absent so the existing gate rejects it.
  await page.evaluate(async () => {
    const node = document.querySelector('.debug-metrics');
    for (const sampleIndex of [5, 7]) {
      node.textContent = JSON.stringify({
        benchmark: { orbiting: true, sampleIndex },
        fps: 1,
      });
      await new Promise((resolve) => setTimeout(resolve, 30));
    }
  });
  const gap = await capture.evaluate((state) => state.samples.splice(0));
  assert.deepEqual(
    gap.map((m) => m.benchmark.sampleIndex),
    [7],
  );
  assert.throws(() => assert.equal(gap[0].benchmark.sampleIndex, 6));
  await capture.evaluate((state) => state.observer.disconnect());
  await capture.dispose();
  await page.setContent('<div>No metrics</div>');
  await assert.rejects(
    page.evaluateHandle(beginBenchmarkCapture),
    /Missing benchmark metrics/,
  );
  console.log(
    'Benchmark capture passed: delayed reads retain all publications, duplicates preserve timed values, genuine gaps remain failures, missing element rejects.',
  );
} finally {
  await browser.close();
}
