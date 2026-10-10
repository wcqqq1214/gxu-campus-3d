/* Dev-server UI regressions. Set PLAYWRIGHT_MODULE / CHROMIUM_PATH if needed. */
import assert from 'node:assert/strict';
const { chromium } = await import(
  process.env.PLAYWRIGHT_MODULE || 'playwright'
);
const browser = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH,
});
const results = [];
const errors = [];
try {
  for (const width of [1280, 390]) {
    const page = await browser.newPage({ viewport: { width, height: 844 } });
    page.on('pageerror', (error) => errors.push(String(error)));
    // Exercise the fallback dialog without depending on host clipboard permissions.
    await page.addInitScript(() => {
      Object.defineProperty(navigator.clipboard, 'writeText', {
        value: async () => {
          throw new DOMException('Clipboard unavailable', 'NotAllowedError');
        },
      });
    });
    await page.goto(process.env.MENU_TEST_URL || 'http://127.0.0.1:3000/');
    await page.waitForFunction(
      () => document.querySelector('.place-row')?.disabled === false,
      undefined,
      { timeout: 90000 },
    );
    const passed = (name) => {
      results.push(`${width}: ${name}`);
      console.log(`PASS ${results.at(-1)}`);
    };
    const chooseGate = () =>
      page.locator('.place-row[data-place-id="south-gate"]').click();
    const back = () =>
      page.getByRole('button', { name: '返回地点列表', exact: true }).click();
    const search = page.getByRole('searchbox', { name: '搜索校园地点' });
    await chooseGate();
    assert.equal(
      await page.getByRole('group', { name: '地点观察视角' }).isVisible(),
      true,
      'Landmark views must be available in the compact detail panel',
    );
    await page.getByRole('button', { name: '环绕', exact: true }).click();
    await back();
    await page
      .getByRole('button', { name: '返回 南大门', exact: true })
      .click();
    assert.equal(
      await page.getByRole('button', { name: '暂停环绕', exact: true }).count(),
      0,
      'Returning to the list must pause orbit',
    );
    passed('返回列表暂停环绕');
    await page.locator('.tour-start').click();
    await back();
    assert.equal(
      await page.locator('.tour-start span').textContent(),
      '继续游览',
      'Returning to the list must pause the tour',
    );
    const station = await page.locator('.tour-copy small').textContent();
    await page.waitForTimeout(8800);
    assert.equal(
      await page.locator('.tour-copy small').textContent(),
      station,
      'Paused tour must not advance',
    );
    passed('返回列表暂停自动游览且不再切站');
    await page.locator('.tour-start').click();
    await page.getByRole('button', { name: '收起面板', exact: true }).click();
    assert.match(await page.locator('.tour-compact').textContent(), /暂停游览/);
    await page.locator('.tour-compact').click();
    assert.match(await page.locator('.tour-compact').textContent(), /继续游览/);
    await page.locator('.tour-compact').click();
    await page.getByRole('button', { name: '展开面板', exact: true }).click();
    await search.focus();
    assert.equal(
      await page.locator('.tour-start span').textContent(),
      '继续游览',
    );
    passed('收起面板可暂停继续，搜索暂停游览');
    await page.getByRole('button', { name: '结束游览', exact: true }).click();
    await search.fill('六教');
    assert.equal(await page.locator('.place-row').count(), 1);
    assert.equal(
      await page.locator('.place-row').getAttribute('data-place-id'),
      'teaching-six',
    );
    assert.equal(await page.locator('.place-group h3').count(), 0);
    await page.locator('.place-row').click();
    await back();
    assert.equal(await search.inputValue(), '六教');
    await page.waitForFunction(
      () =>
        document.activeElement?.getAttribute('data-place-id') ===
        'teaching-six',
    );
    await page.getByTitle('清除搜索', { exact: true }).click();
    assert.equal(await page.locator('.place-row').count(), 20);
    assert.equal(
      await search.evaluate((el) => document.activeElement === el),
      true,
    );
    assert.deepEqual(
      await page
        .locator('.place-group')
        .evaluateAll((groups) =>
          groups.map((group) => group.getAttribute('aria-label')),
        ),
      ['教学', '文体', '校门', '路桥', '生活'],
    );
    await search.fill('不存在的校园地点');
    assert.equal(await page.locator('.place-row').count(), 0);
    await page.getByRole('button', { name: '清空搜索', exact: true }).click();
    assert.equal(await search.inputValue(), '');
    assert.equal(await page.locator('.place-row').count(), 20);
    assert.equal(
      await search.evaluate((el) => document.activeElement === el),
      true,
    );
    passed('别名搜索平铺、分类分组恢复、返回焦点和空结果重置');
    await page.getByRole('tab', { name: '光影', exact: true }).click();
    await page.getByRole('button', { name: '夜景', exact: true }).click();
    await page.getByRole('tab', { name: '图层', exact: true }).click();
    const labels = page.getByRole('switch', { name: '地点名称', exact: true });
    await labels.click();
    assert.equal(await labels.getAttribute('aria-checked'), 'false');
    await page.getByRole('tab', { name: '地点', exact: true }).click();
    await page.getByRole('tab', { name: '光影', exact: true }).click();
    assert.equal(
      await page
        .getByRole('button', { name: '夜景', exact: true })
        .getAttribute('aria-pressed'),
      'true',
    );
    await page.getByRole('tab', { name: '图层', exact: true }).click();
    assert.equal(await labels.getAttribute('aria-checked'), 'false');
    await labels.click();
    passed('切换菜单保留光照和图层状态');
    if (width < 760) {
      await page.getByRole('button', { name: '更多工具', exact: true }).click();
      await page
        .getByRole('dialog')
        .getByRole('button', { name: '分享', exact: true })
        .click();
    } else {
      await page.getByRole('button', { name: '分享', exact: true }).click();
    }
    await page
      .getByRole('dialog', { name: '分享校园', exact: true })
      .getByRole('button', { name: '复制视角链接', exact: true })
      .click();
    const share = page.getByRole('dialog', { name: '分享这个校园视角' });
    await share.waitFor();
    const input = share.getByRole('textbox', { name: '校园视角链接' });
    const link = new URL(await input.inputValue());
    assert.equal(new URLSearchParams(link.hash.slice(1)).get('light'), 'night');
    assert.equal(
      new URLSearchParams(link.hash.slice(1)).get('place'),
      'teaching-six',
    );
    await input.focus();
    assert.equal(
      await input.evaluate((el) => el.selectionEnd - el.selectionStart),
      (await input.inputValue()).length,
    );
    await page.keyboard.press('Escape');
    await share.waitFor({ state: 'hidden' });
    await page.waitForTimeout(200);
    assert.equal(
      await page.evaluate(() => document.activeElement?.tagName),
      'BUTTON',
    );
    passed('剪贴板受限时可复制分享链接并恢复焦点');
    await page.close();
  }
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ passed: results.length, errors }, null, 2));
} finally {
  await browser.close();
}
