/* Check short-screen dialogs in Chromium or WebKit, including the close target. */
import assert from 'node:assert/strict';
const playwright = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const engine = process.env.I18N_BROWSER || 'chromium';
const browser = await playwright[engine].launch({
  executablePath: process.env.BROWSER_PATH || process.env.CHROMIUM_PATH,
});
try {
  const page = await browser.newPage({
    viewport: { width: 320, height: 480 },
    isMobile: true,
    hasTouch: true,
  });
  await page.goto(
    (process.env.I18N_URL || 'http://127.0.0.1:4310/') + '?lang=en',
  );
  await page.waitForFunction(() => document.documentElement.lang === 'en');
  for (const [width, height] of [
    [320, 480],
    [320, 568],
    [667, 375],
    [844, 390],
  ]) {
    await page.setViewportSize({ width, height });
    for (const locale of ['en', 'zh']) {
      if (
        (await page.locator('.language-switch').getAttribute('data-locale')) !==
        locale
      )
        await page.locator('.language-switch').click();
      await page.locator('.about-button').click();
      await page.getByRole('dialog').waitFor();
      await page.waitForTimeout(250); // Let the popup's opening scale animation finish.
      const layout = await page.getByRole('dialog').evaluate((dialog) => {
        const close = dialog.querySelector('[data-slot="dialog-close"]');
        const body = dialog.querySelector('.about-scroll');
        const rect = dialog.getBoundingClientRect();
        const target = close.getBoundingClientRect();
        body.scrollTop = body.scrollHeight;
        const last = body.lastElementChild.getBoundingClientRect();
        const scroll = body.getBoundingClientRect();
        return {
          fits:
            rect.top >= 0 &&
            rect.bottom <= innerHeight &&
            rect.left >= 0 &&
            rect.right <= innerWidth,
          closeFits: target.top >= 0 && target.bottom <= innerHeight,
          closeHittable: close.contains(
            document.elementFromPoint(
              target.x + target.width / 2,
              target.y + target.height / 2,
            ),
          ),
          bodyScrollable: body.scrollHeight > body.clientHeight,
          lastContentVisible: last.bottom <= scroll.bottom + 1,
        };
      });
      assert.ok(
        Object.values(layout).every(Boolean),
        JSON.stringify({ engine, width, height, locale, ...layout }),
      );
      await page
        .getByRole('button', {
          name: locale === 'en' ? 'Close' : '关闭',
          exact: true,
        })
        .click();
      await page.getByRole('dialog').waitFor({ state: 'hidden' });
      console.log(`PASS ${engine} ${width}x${height} ${locale}`);
    }
  }
} finally {
  await browser.close();
}
