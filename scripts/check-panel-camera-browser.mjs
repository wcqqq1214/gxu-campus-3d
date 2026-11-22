/* Run against the dev server; probes are injected into its response, never shipped. */
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import ts from 'typescript';
import { browserCheck } from './browser-check.mjs';
const baselineText = process.env.PANEL_SCENE_REV
  ? execFileSync(
      'git',
      ['show', `${process.env.PANEL_SCENE_REV}:lib/campus/scene.ts`],
      { encoding: 'utf8' },
    )
  : null;
// The baseline swaps only createScene and keeps the current module imports, so
// it supports revisions after createScene was split into lib/campus/scene-*.ts.
if (baselineText && !baselineText.includes("from './scene-details'"))
  throw new Error(
    `PANEL_SCENE_REV=${process.env.PANEL_SCENE_REV} 早于场景模块拆分，不支持作为基准`,
  );
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
const viewports = new Map([
  ['desktop', { width: 1280, height: 800 }],
  ['mobile', { width: 390, height: 844 }],
]);
const selected = process.env.PANEL_VIEWPORT;
if (selected !== undefined && !viewports.has(selected))
  throw new Error(
    `无效的 PANEL_VIEWPORT：${selected}（支持 desktop 或 mobile）`,
  );
const browser = await browserCheck('camera');
try {
  for (const viewport of selected
    ? [viewports.get(selected)]
    : viewports.values()) {
    let stage;
    let operation;
    let started;
    function begin(label) {
      stage = `${viewport.width}: ${label}`;
      started = performance.now();
      operation = '开始';
      console.log(`开始 ${stage}`);
    }
    function action(label) {
      operation = label;
      console.log(`${stage} ${operation}`);
    }
    function passed() {
      results.push(stage);
      console.log(
        `PASS ${stage} (${Math.round(performance.now() - started)} ms)`,
      );
    }
    begin('全景保持相机与投影');
    const page = await browser.newPage({ viewport });
    page.on('console', (message) => {
      const text = message.text();
      if (text.startsWith('[camera]'))
        console.log(
          `${stage} ${operation} (${Math.round(performance.now() - started)} ms) ${text}`,
        );
    });
    page.on('pageerror', (error) => errors.push(String(error)));
    await page.route('**/lib/campus/scene.ts*', async (route) => {
      const response = await route.fetch();
      let source = await response.text();
      if (baselineSource)
        source =
          source.slice(0, source.indexOf('export function createScene')) +
          baselineSource;
      const sceneModule = ts.createSourceFile(
        'scene.js',
        source,
        ts.ScriptTarget.Latest,
        true,
        ts.ScriptKind.JS,
      );
      const createScene = sceneModule.statements.find(
        (statement) =>
          ts.isFunctionDeclaration(statement) &&
          statement.name?.text === 'createScene',
      );
      const controllerReturn = createScene?.body?.statements.find(
        (statement) =>
          ts.isReturnStatement(statement) &&
          statement.expression &&
          ts.isObjectLiteralExpression(statement.expression) &&
          ['focus', 'landmarkView', 'getSnapshot'].every((name) =>
            statement.expression.properties.some(
              (property) => property.name?.getText(sceneModule) === name,
            ),
          ),
      );
      assert.ok(
        controllerReturn,
        'Dev createScene must return its scene controller',
      );
      // A tween can finish after controls.update() and leave a pose that the next
      // update still needs to clamp. Count actual settled updates, not wall time.
      const probe = `let panelSettledUpdates = 0;
      let nextPanelReport = 0;
      const panelUpdateControls = controls.update.bind(controls);
      controls.update = (...args) => {
        const moving = panelUpdateControls(...args);
        panelSettledUpdates = tween || (moving && !orbiting)
          ? 0 : panelSettledUpdates + 1;
        const now = performance.now();
        if (now >= nextPanelReport) {
          console.debug('[camera]', JSON.stringify({
            queuedDetails: details.queued, tweenActive: Boolean(tween),
            settledUpdates: panelSettledUpdates
          }));
          nextPanelReport = now + 15000;
        }
        return moving;
      };
      globalThis.__panelCameraProbe = () => ({
        position: camera.position.toArray(), target: controls.target.toArray(),
        projection: camera.projectionMatrix.toArray(), span: getSnapshot().span,
        queuedDetails: details.queued, orbiting, tweenStart: tween?.start ?? null,
        frame: {...frame}, width: host.clientWidth, height: host.clientHeight,
        framedWidth, framedHeight, settledUpdates: panelSettledUpdates
      });\n`;
      await route.fulfill({
        response,
        body:
          source.slice(0, controllerReturn.getStart(sceneModule)) +
          probe +
          source.slice(controllerReturn.getStart(sceneModule)),
      });
    });
    await page.goto(
      `${process.env.PANEL_TEST_URL || 'http://127.0.0.1:3000/'}?debug`,
    );
    const settle = async () => {
      action('等待场景稳定');
      await page.waitForTimeout(1600);
      await page.waitForFunction(
        () => {
          const metrics = document.querySelector('.debug-metrics')?.textContent;
          if (!metrics || !globalThis.__panelCameraProbe) return false;
          const m = JSON.parse(metrics);
          const scene = globalThis.__panelCameraProbe();
          return (
            m.readyMs > 0 &&
            scene.queuedDetails === 0 &&
            scene.tweenStart === null &&
            scene.settledUpdates >= 2
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
    const toggleCycle = async (controls) => {
      await settle();
      const before = await snapshot();
      for (const name of ['收起面板', '展开面板']) {
        action(name);
        await page.getByRole('button', { name, exact: true }).click();
        await page.waitForTimeout(650);
        unchanged(before, await snapshot(), `${stage}/${name}`);
        if (controls)
          assert.deepEqual(
            await page
              .getByRole('group', {
                name: '地点观察视角',
                exact: true,
                includeHidden: true,
              })
              .getByRole('button', { includeHidden: true })
              .allTextContents(),
            controls,
            `手机详情${name}后须保留同一组视角控件`,
          );
      }
    };
    await toggleCycle();
    passed();
    begin(
      viewport.width < 760
        ? '手机详情收起展开保留视角控件、相机与投影'
        : '地标自动取景保持相机与投影',
    );
    await page
      .locator('.panel-dock')
      .getByRole('button', { name: '01 南大门', exact: true })
      .click();
    const controls =
      viewport.width < 760
        ? await page
            .getByRole('group', { name: '地点观察视角', exact: true })
            .getByRole('button')
            .allTextContents()
        : undefined;
    if (controls) assert.ok(controls.length > 0);
    await toggleCycle(controls);
    passed();
    begin('俯视保持相机与投影');
    const beforeView = await snapshot();
    await page
      .getByRole('group', { name: '地点观察视角', exact: true })
      .getByRole('button', { name: '俯视', exact: true })
      .click();
    await toggleCycle();
    assert.notDeepEqual(
      beforeView.position,
      (await snapshot()).position,
      'Explicit view switch must still move the camera',
    );
    passed();
    begin('手动平移缩放保持相机与投影');
    await page.locator('canvas').focus();
    await page.keyboard.press('-');
    await settle();
    await page.locator('canvas').focus();
    await page.keyboard.press('ArrowLeft');
    await toggleCycle();
    passed();
    begin('环绕不重启、不改变距离');
    await page.getByRole('button', { name: '环绕', exact: true }).click();
    await settle();
    const beforeOrbit = await snapshot();
    for (const name of ['收起面板', '展开面板']) {
      action(name);
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
    passed();
    begin('分享链接恢复后保持相机与投影');
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
    await toggleCycle();
    passed();
    begin('窗口缩放后仍保持构图');
    await page
      .locator('.masthead')
      .getByRole('button', { name: '回到全景', exact: true })
      .click();
    await settle();
    const beforeResize = await snapshot();
    const resizedViewport = {
      width: viewport.width + 120,
      height: viewport.height - 80,
    };
    action('等待窗口重新构图');
    await page.setViewportSize(resizedViewport);
    // Software rendering can delay resize events and ResizeObserver beyond the
    // animation wait. Wait for layout and composition, not for the assertion itself.
    await page.waitForFunction(
      ({ width, height }) => {
        const scene = globalThis.__panelCameraProbe();
        return (
          scene.width === width &&
          scene.height === height &&
          scene.framedWidth === width &&
          scene.framedHeight === height
        );
      },
      resizedViewport,
      { timeout: 90000 },
    );
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
    await toggleCycle();
    assert.equal(await page.locator('vite-error-overlay').count(), 0);
    passed();
    begin('保存追踪并关闭页面');
    await browser.closePage(page);
    console.log(
      `完成 ${stage} (${Math.round(performance.now() - started)} ms)`,
    );
  }
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ passed: results.length, errors }, null, 2));
} finally {
  console.log('开始浏览器收尾');
  const closing = performance.now();
  await browser.close();
  console.log(`完成浏览器收尾 (${Math.round(performance.now() - closing)} ms)`);
}
