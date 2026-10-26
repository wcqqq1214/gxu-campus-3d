/* Set I18N_BROWSER=webkit and BROWSER_PATH for WebKit; Chromium is the default. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const playwright = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const engine = process.env.I18N_BROWSER || 'chromium';
const base = process.env.I18N_URL || 'http://127.0.0.1:4310/';
const output = new URL('../outputs/i18n-browser/', import.meta.url);
await fs.mkdir(output, { recursive: true });
const browser = await playwright[engine].launch({
  executablePath: process.env.BROWSER_PATH || process.env.CHROMIUM_PATH,
});
const errors = [];
const results = [];
const waitForSceneReady = (page) =>
  page.waitForFunction(
    () => document.querySelector('.tour-start')?.disabled === false,
    undefined,
    { timeout: 120000 },
  );
const languageTrigger = (page) =>
  page.getByRole('button', { name: '语言 / Language', exact: true });
async function setLanguage(page, locale) {
  await languageTrigger(page).click();
  const option = page.getByRole('menuitemradio', {
    name: locale === 'en' ? 'English' : '中文',
    exact: true,
  });
  await option.click();
  await page.waitForFunction(
    (lang) => document.documentElement.lang === lang,
    locale === 'en' ? 'en' : 'zh-CN',
  );
  await languageTrigger(page).click();
  assert.equal(await option.getAttribute('aria-checked'), 'true');
  await page.keyboard.press('Escape');
}
try {
  for (const width of [1280, 390, 320]) {
    const page = await browser.newPage({
      viewport: { width, height: 844 },
      deviceScaleFactor: 1,
    });
    page.setDefaultTimeout(60000);
    console.log(`Checking ${width}px`);
    page.on('pageerror', (e) => errors.push(String(e)));
    await page.goto(base + '?debug');
    await page.waitForFunction(
      () => {
        const metrics = document.querySelector('.debug-metrics')?.textContent;
        return metrics && JSON.parse(metrics).readyMs > 0;
      },
      undefined,
      { timeout: 120000 },
    );
    await page.evaluate(() => {
      window.i18nCanvas = document.querySelector('.scene-host canvas');
    });
    const checkHeader = () =>
      page.evaluate(() => {
        const control = document.querySelector(
          'button[aria-label="语言 / Language"]',
        );
        const rect = control.getBoundingClientRect();
        const header = document.querySelector('.masthead');
        return {
          x: rect.x,
          y: rect.y,
          width: rect.width,
          fits: header.scrollWidth <= header.clientWidth + 1,
          buttonsFit: [...header.querySelectorAll('button')].every((el) => {
            const bounds = el.getBoundingClientRect();
            return bounds.left >= 0 && bounds.right <= innerWidth;
          }),
        };
      });
    const chineseHeader = await checkHeader();
    assert.ok(chineseHeader.fits && chineseHeader.buttonsFit);
    await setLanguage(page, 'en');
    assert.deepEqual(await checkHeader(), chineseHeader);
    assert.equal(await page.title(), 'Guangxi University Campus Map');
    const search = page.getByRole('searchbox', {
      name: 'Search campus places',
    });
    await search.fill('计电');
    await page.locator('.place-row[data-place-id="computer"]').click();
    await page
      .getByRole('heading', {
        name: 'School of Computer, Electronics and Information',
        exact: true,
      })
      .waitFor();
    await page.waitForTimeout(1600); // Let the existing focus animation finish before checking preservation.
    const before = await page.locator('.debug-metrics').textContent();
    await setLanguage(page, 'zh');
    await page
      .getByRole('heading', { name: '计算机与电子信息学院', exact: true })
      .waitFor();
    await setLanguage(page, 'en');
    assert.ok(
      await page.evaluate(
        () =>
          window.i18nCanvas === document.querySelector('.scene-host canvas'),
      ),
    );
    assert.equal(
      JSON.parse(await page.locator('.debug-metrics').textContent()).readyMs,
      JSON.parse(before).readyMs,
    );
    const layout = await page.evaluate(() => {
      const heading = document.querySelector('.detail-heading h2');
      const panel = document.querySelector('.panel-dock');
      const header = document.querySelector('.masthead');
      const title = heading.getBoundingClientRect();
      const bounds = panel.getBoundingClientRect();
      return {
        pageOverflow: document.documentElement.scrollWidth > innerWidth,
        titleFits:
          heading.scrollWidth <= heading.clientWidth + 1 &&
          title.right <= bounds.right,
        panelFits: bounds.right <= innerWidth && bounds.left >= 0,
        headerFits: header.scrollWidth <= header.clientWidth + 1,
      };
    });
    assert.ok(
      !layout.pageOverflow &&
        layout.titleFits &&
        layout.panelFits &&
        layout.headerFits,
      JSON.stringify({ width, layout }),
    );
    await page.screenshot({
      style: '.debug-metrics { visibility: hidden !important; }',
      path: new URL(`en-detail-${width}.png`, output).pathname,
    });
    // Translation must include dialogs rendered through a portal.
    await page
      .getByRole('group', { name: 'Views of this place', exact: true })
      .waitFor();
    await page.locator('.detail-actions button').click();
    await page.getByRole('heading', { name: 'Share', exact: true }).waitFor();
    assert.ok(
      !/\p{Script=Han}/u.test(await page.getByRole('dialog').innerText()),
    );
    if (width === 320) {
      const downloadReady = page.waitForEvent('download');
      await page
        .getByRole('button', { name: 'Download image', exact: true })
        .click();
      const download = await downloadReady;
      assert.equal(
        download.suggestedFilename(),
        'Guangxi-University-Campus.png',
      );
      await download.saveAs(new URL('en-export-320.png', output).pathname);
    } else {
      await page.getByRole('button', { name: 'Close', exact: true }).click();
    }

    await page
      .getByRole('button', { name: 'Back to places', exact: true })
      .click();
    await search.fill('No. 6');
    assert.equal(await page.locator('.place-row').count(), 1);
    assert.equal(
      await page.locator('.place-row').getAttribute('data-place-id'),
      'teaching-six',
    );
    await search.fill('');
    await search.blur();
    await page.getByRole('tab', { name: 'Layers', exact: true }).click();
    await page
      .getByRole('switch', { name: 'Place labels', exact: true })
      .waitFor();
    await page.getByRole('tab', { name: 'Lighting', exact: true }).click();
    await page.getByRole('button', { name: 'Night', exact: true }).click();
    await page.screenshot({
      style: '.debug-metrics { visibility: hidden !important; }',
      path: new URL(`en-lighting-${width}.png`, output).pathname,
    });
    await page.goto(base + '?debug'); // No lang parameter: restore the saved preference.
    await page.waitForFunction(() => document.documentElement.lang === 'en');
    await page
      .getByRole('searchbox', { name: 'Search campus places' })
      .waitFor();
    // Language restores before model decoding finishes. Let this document finish
    // initializing before navigating again: WebKit rejects blob loads in a departing document.
    await waitForSceneReady(page);
    // Explicit share language overrides the stored preference, without changing the place hash.
    await page.goto(base + '?lang=zh#place=library');
    await page.waitForFunction(() => document.documentElement.lang === 'zh-CN');
    await languageTrigger(page).waitFor();
    await waitForSceneReady(page);
    results.push({ width, ...layout, passed: true });
    await page.close();
  }
  const page = await browser.newPage();
  await page.addInitScript(() => {
    Object.defineProperty(window, 'localStorage', {
      get() {
        throw new DOMException('Blocked', 'SecurityError');
      },
    });
  });
  await page.addInitScript(() => {
    const getContext = Object.getOwnPropertyDescriptor(
      HTMLCanvasElement.prototype,
      'getContext',
    ).value;
    HTMLCanvasElement.prototype.getContext = function (kind, ...args) {
      return kind.startsWith('webgl')
        ? null
        : Reflect.apply(getContext, this, [kind, ...args]);
    };
  });
  await page.goto(base + '?lang=en');
  await page.getByRole('alert').filter({ hasText: 'WebGL 2' }).waitFor();
  await setLanguage(page, 'zh');
  await page.getByRole('alert').filter({ hasText: '此浏览器' }).waitFor();
  results.push({ storageUnavailable: true, webglFallbackTranslated: true });
  assert.deepEqual(errors, []);
  console.log(JSON.stringify(results, null, 2));
} finally {
  await fs.writeFile(
    new URL('results.json', output),
    JSON.stringify({ results, errors }, null, 2),
  );
  await browser.close();
}
