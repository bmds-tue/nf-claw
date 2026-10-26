import { test, expect } from '@playwright/test';

test('proteinfold shows its authoritative demo caveat beside the command', async ({ page }) => {
  await page.goto('/pipelines/proteinfold/');
  await expect(page.locator('#run')).toContainText(/placeholder|computes nothing/i);
});

test('core documentation is visible without JavaScript', async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  try {
    const page = await context.newPage();
    await page.goto('/docs/agents/');
    const heading = page.locator('main h1').first();
    await expect(heading).toBeVisible();
    const opacity = await heading.evaluate((element) => {
      let opacity = 1;
      for (let node: Element | null = element; node; node = node.parentElement)
        opacity *= Number(getComputedStyle(node).opacity);
      return opacity;
    });
    expect(opacity).toBe(1);
  } finally { await context.close(); }
});

test('mobile navigation contains keyboard focus and restores it on Escape', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/pipelines/');
  const toggle = page.getByRole('button', { name: 'Open menu' });
  await toggle.click();
  await expect(page.locator('#mobile-menu')).toBeVisible();
  await expect(page.locator('main')).toHaveAttribute('inert', '');
  for (let i = 0; i < 20; i++) {
    await page.keyboard.press('Tab');
    expect(await page.evaluate(() => Boolean(document.activeElement?.closest('header')))).toBe(true);
  }
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button', { name: 'Open menu' })).toBeFocused();
  await expect(page.locator('main')).not.toHaveAttribute('inert', '');
});

test('parameter search recovers from an initial network failure', async ({ page }) => {
  let requests = 0;
  await page.route('**/search/params.json', async route => {
    requests++;
    if (requests === 1) await route.fulfill({ status: 503, body: 'temporarily unavailable' });
    else await route.continue();
  });
  await page.goto('/#skills');
  const search = page.locator('#skills input[type="search"], #skills input').first();
  await search.fill('carveme-mediadb');
  await expect(page.locator('#skills')).toContainText('parameter search unavailable');
  await page.getByRole('button', { name: 'Retry parameter search' }).click();
  await expect(page.locator('#skills')).not.toContainText('parameter search unavailable');
  await expect(page.locator('#skills')).toContainText('carveme-mediadb');
  expect(requests).toBeGreaterThanOrEqual(2);
});

test('bacmodel example link points to its pinned upstream source', async ({ page }) => {
  await page.goto('/pipelines/bacmodel/');
  await page.getByRole('button', { name: /carveme-mediadb/ }).first().click();
  const link = page.getByRole('link', { name: 'example file' });
  await expect(link).toHaveAttribute('href', /github\.com\/nf-core\/bacmodel\/blob\/[0-9a-f]{40}\/assets\/medium_carveme_mediadb_example\.tsv$/);
});

test('copied parameter values preserve spaces and leading dashes through the shell', async ({ page }) => {
  const { spawnSync } = await import('node:child_process');
  await page.context().grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.goto('/pipelines/bacmodel/');
  await page.getByRole('button', { name: /gapseq-doall-args/ }).first().click();
  await page.getByRole('button', { name: /^Copy: --gapseq-doall-args/ }).last().click();
  const snippet = await page.evaluate(() => navigator.clipboard.readText());
  const parsed = spawnSync('bash', ['-c',
    `python3 -c 'import json,sys; print(json.dumps(sys.argv[1:]))' ${snippet}`], { encoding: 'utf8' });
  expect(parsed.status).toBe(0);
  expect(JSON.parse(parsed.stdout)).toEqual(['--gapseq-doall-args=-b 200 -A diamond']);
});
