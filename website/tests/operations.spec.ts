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

for (const trigger of ['button', 'shortcut']) {
  test(`mobile menu hands focus to search opened by ${trigger}`, async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/pipelines/');
    await page.getByRole('button', { name: 'Open menu' }).click();
    if (trigger === 'button') await page.getByRole('button', { name: 'Search', exact: true }).click();
    else await page.keyboard.press('Control+k');
    const input = page.locator('input[role="combobox"]');
    await expect(input).toBeFocused();
    await input.fill('rnaseq');
    await expect(input).toHaveValue('rnaseq');
    await expect(page.getByRole('dialog', { name: 'Navigation menu' })).toHaveCount(0);
    await page.keyboard.press('Escape');
    await expect(page.locator('main')).not.toHaveAttribute('inert', '');
  });
}

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

test('exported local links and fragments resolve to real artifacts', async ({ page }) => {
  const fs = await import('node:fs');
  const path = await import('node:path');
  const root = path.resolve('out');
  const files: string[] = [];
  function walk(dir: string) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const file = path.join(dir, entry.name);
      if (entry.isDirectory()) walk(file);
      else if (entry.name.endsWith('.html')) files.push(file);
    }
  }
  walk(root);
  const pages = new Map<string, { links: string[]; ids: string[] }>();
  for (const file of files) {
    const parsed = await page.evaluate(html => {
      const doc = new DOMParser().parseFromString(html, 'text/html');
      return { links: Array.from(doc.querySelectorAll('a[href]'), a => a.getAttribute('href')!),
               ids: Array.from(doc.querySelectorAll('[id]'), e => e.id) };
    }, fs.readFileSync(file, 'utf8'));
    pages.set(file, parsed);
  }
  const broken: string[] = [];
  let checked = 0;
  for (const [file, content] of pages) {
    const relative = path.relative(root, file).split(path.sep).join('/');
    const base = 'http://export.test/' + relative.replace(/index\.html$/, '');
    for (const href of content.links) {
      const url = new URL(href, base);
      if (url.origin !== 'http://export.test') continue;
      checked++;
      let target = path.join(root, decodeURIComponent(url.pathname));
      if (fs.existsSync(target) && fs.statSync(target).isDirectory()) target = path.join(target, 'index.html');
      if (!fs.existsSync(target)) { broken.push(`${relative}: ${href} (missing file)`); continue; }
      const fragment = decodeURIComponent(url.hash.slice(1));
      if (fragment && pages.has(target) && !pages.get(target)!.ids.includes(fragment))
        broken.push(`${relative}: ${href} (missing fragment)`);
    }
  }
  expect(checked).toBeGreaterThan(1000);
  expect(broken).toEqual([]);
});
