import fs from 'node:fs/promises';
import path from 'node:path';

/** Shared diagnostics for the existing standalone browser regressions. */
export async function browserCheck(name, engine = 'chromium') {
  const output = path.resolve(
    process.env.BROWSER_REPORT_DIR ||
      `work/browser-checks/${name}-${Date.now()}`,
  );
  await fs.mkdir(output, { recursive: true });
  const playwright = await import(
    process.env.PLAYWRIGHT_MODULE || 'playwright'
  );
  const browser = await playwright[engine].launch({
    channel: engine === 'chromium' ? 'chromium' : undefined,
    executablePath: process.env.BROWSER_PATH || process.env.CHROMIUM_PATH,
    args:
      engine === 'chromium' && process.env.SWIFTSHADER === '1'
        ? [
            '--use-gl=angle',
            '--use-angle=swiftshader',
            '--enable-unsafe-swiftshader',
          ]
        : [],
  });
  const pages = new Map();
  const messages = [];
  let sequence = 0;
  async function closePage(page) {
    const id = pages.get(page);
    if (id === undefined) return;
    await page
      .context()
      .tracing.stop({ path: path.join(output, `trace-${id}.zip`) });
    await page.context().close();
    pages.delete(page);
  }
  return {
    output,
    async newPage(options = {}) {
      const context = await browser.newContext(options);
      // Continuous screencast readbacks can stall this WebGL scene on software GPUs.
      // Keep DOM/network traces and capture a single screenshot on failure instead.
      await context.tracing.start({ screenshots: false, snapshots: true });
      const page = await context.newPage();
      const id = ++sequence;
      pages.set(page, id);
      page.setDefaultTimeout(60000);
      page.setDefaultNavigationTimeout(120000);
      page.on('console', (message) =>
        messages.push(`${id} console ${message.type()}: ${message.text()}`),
      );
      page.on('pageerror', (error) =>
        messages.push(`${id} pageerror: ${error.stack || error}`),
      );
      page.on('requestfailed', (request) =>
        messages.push(
          `${id} requestfailed: ${request.url()} ${request.failure()?.errorText}`,
        ),
      );
      page.on('response', (response) => {
        if (response.status() >= 400)
          messages.push(`${id} HTTP ${response.status()}: ${response.url()}`);
      });
      return page;
    },
    closePage,
    async close() {
      try {
        // Successful viewport checks close themselves; remaining pages show the failure state.
        for (const [page, id] of pages) {
          try {
            await page.screenshot({
              path: path.join(output, `remaining-${id}.png`),
              timeout: 10000,
            });
          } catch (error) {
            messages.push(`Screenshot unavailable: ${String(error)}`);
          }
          try {
            await closePage(page);
          } catch (error) {
            messages.push(`Trace unavailable: ${String(error)}`);
          }
        }
        await fs.writeFile(
          path.join(output, 'browser.log'),
          messages.join('\n') + '\n',
        );
      } finally {
        await browser.close();
      }
    },
  };
}
