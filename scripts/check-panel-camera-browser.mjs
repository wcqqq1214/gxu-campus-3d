/* Run against the dev server; probes are injected into its response, never shipped. */
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import ts from 'typescript';
const { chromium } = await import(
  process.env.PLAYWRIGHT_MODULE || 'playwright'
);
const browser = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH,
});
const baselineText = process.env.PANEL_SCENE_REV
  ? execFileSync(
      'git',
      ['show', `${process.env.PANEL_SCENE_REV}:lib/campus/scene.ts`],
      { encoding: 'utf8' },
    )
  : null;
const baselineSource = baselineText
  ? ts.transpileModule(
      baselineText.slice(baselineText.indexOf('export function createScene')),
      {
        compilerOptions: {
          target: ts.ScriptTarget.ESNext,
          module: ts.ModuleKind.ESNext,
        },
      },
    ).outputText
  : null;
const errors = [];
const results = [];
try {
  for (const viewport of [
    { width: 1280, height: 800 },
    { width: 390, height: 844 },
  ]) {
    const page = await browser.newPage({ viewport });
    page.on('pageerror', (error) => errors.push(String(error)));
    await page.route('**/lib/campus/scene.ts*', async (route) => {
      const response = await route.fetch();
      let source = await response.text();
      if (baselineSource)
        source =
          source.slice(0, source.indexOf('export function createScene')) +
          baselineSource;
      const marker = /return\s*\{\s*focus,\s*landmarkView,/;
      assert.match(
        source,
        marker,
        'Dev scene module must expose its controller',
      );
      const probe = `globalThis.__panelCameraProbe = () => ({
        position: camera.position.toArray(), target: controls.target.toArray(),
        projection: camera.projectionMatrix.toArray(), span: getSnapshot().span,
        loading: [...loading], orbiting, tweenStart: tween?.start ?? null,
        frame: {...frame}, width: host.clientWidth, height: host.clientHeight
      });\n`;
      await route.fulfill({
        response,
        body: source.replace(marker, (text) => probe + text),
      });
    });
    await page.goto(
      `${process.env.PANEL_TEST_URL || 'http://127.0.0.1:3000/'}?debug`,
    );
    const settle = async () => {
      await page.waitForTimeout(1600);
      await page.waitForFunction(
        () => {
          const metrics = document.querySelector('.debug-metrics')?.textContent;
          if (!metrics || !globalThis.__panelCameraProbe) return false;
          const m = JSON.parse(metrics);
          return (
            m.readyMs > 0 &&
            m.queuedDetails === 0 &&
            globalThis.__panelCameraProbe().tweenStart === null &&
            !globalThis
              .__panelCameraProbe()
              .loading.some((key) => key.startsWith('landmark-'))
          );
        },
        undefined,
        { timeout: 90000 },
      );
      await page.waitForTimeout(350);
    };
    const snapshot = () => page.evaluate(() => globalThis.__panelCameraProbe());
    const unchanged = (a, b, label) => {
      for (const key of ['position', 'target', 'projection']) {
        assert.equal(a[key].length, b[key].length);
        a[key].forEach((v, i) =>
          assert.ok(
            Math.abs(v - b[key][i]) < 1e-8,
            `${label}: ${key}[${i}] changed: ${JSON.stringify({ before: a, after: b })}`,
          ),
        );
      }
      assert.ok(
        Math.abs(a.span - b.span) < 1e-8,
        `${label}: zoom span changed`,
      );
    };
    const toggleCycle = async (label) => {
      await settle();
      const before = await snapshot();
      for (const name of ['收起面板', '展开面板']) {
        await page.getByRole('button', { name, exact: true }).click();
        await page.waitForTimeout(650);
        unchanged(
          before,
          await snapshot(),
          `${viewport.width}/${label}/${name}`,
        );
      }
      results.push(`${viewport.width}: ${label}`);
      console.log(`PASS ${results.at(-1)}`);
    };
    await toggleCycle('全景保持相机与投影');
    await page
      .locator('.panel-dock')
      .getByRole('button', { name: '01 南大门', exact: true })
      .click();
    await toggleCycle('地标自动取景保持相机与投影');
    if (viewport.width < 760) {
      const before = await snapshot();
      await page.getByRole('button', { name: '更多视角', exact: true }).click();
      await page.waitForTimeout(650);
      unchanged(before, await snapshot(), '展开手机详情');
    }
    const beforeView = await snapshot();
    await page.getByRole('button', { name: '俯视', exact: true }).click();
    await toggleCycle('俯视保持相机与投影');
    assert.notDeepEqual(
      beforeView.position,
      (await snapshot()).position,
      'Explicit view switch must still move the camera',
    );
    await page.locator('canvas').focus();
    await page.keyboard.press('-');
    await settle();
    await page.locator('canvas').focus();
    await page.keyboard.press('ArrowLeft');
    await toggleCycle('手动平移缩放保持相机与投影');
    await page.getByRole('button', { name: '环绕', exact: true }).click();
    await settle();
    const beforeOrbit = await snapshot();
    for (const name of ['收起面板', '展开面板']) {
      await page.getByRole('button', { name, exact: true }).click();
      await page.waitForTimeout(650);
      const after = await snapshot();
      assert.equal(after.orbiting, true);
      assert.equal(
        after.tweenStart,
        null,
        'Panel toggle must not restart orbit framing',
      );
      after.projection.forEach((value, i) =>
        assert.ok(
          Math.abs(value - beforeOrbit.projection[i]) < 1e-8,
          'Orbit projection changed',
        ),
      );
      const radius = (s) =>
        Math.hypot(...s.position.map((v, i) => v - s.target[i]));
      assert.ok(Math.abs(radius(beforeOrbit) - radius(after)) < 1e-6);
    }
    results.push(`${viewport.width}: 环绕不重启、不改变距离`);
    console.log(`PASS ${results.at(-1)}`);
    await page.getByRole('button', { name: '暂停环绕', exact: true }).click();
    const saved = await snapshot();
    const hash = new URLSearchParams({
      place: 'south-gate',
      camera: [...saved.position, ...saved.target].join(','),
      span: String(saved.span),
    });
    await page.goto(
      `${process.env.PANEL_TEST_URL || 'http://127.0.0.1:3000/'}?debug&restore#${hash}`,
    );
    await toggleCycle('分享链接恢复后保持相机与投影');
    await page
      .getByRole('button', { name: '返回校园全景', exact: true })
      .click();
    await settle();
    const beforeResize = await snapshot();
    await page.setViewportSize({
      width: viewport.width + 120,
      height: viewport.height - 80,
    });
    await settle();
    const afterResize = await snapshot();
    assert.notDeepEqual(
      beforeResize.projection,
      afterResize.projection,
      'Window resize must update projection',
    );
    assert.ok(
      [...afterResize.position, ...afterResize.projection].every(
        Number.isFinite,
      ),
    );
    await toggleCycle('窗口缩放后仍保持构图');
    assert.equal(await page.locator('vite-error-overlay').count(), 0);
    await page.close();
  }
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ passed: results.length, errors }, null, 2));
} finally {
  await browser.close();
}
