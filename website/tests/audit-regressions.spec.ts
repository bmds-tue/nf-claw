import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import { gotoHydrated } from './hydration';

// Also run this file against a project-site export, with the same build-time base path.
const base = process.env.NEXT_PUBLIC_BASE_PATH || '';

test('pipeline filters follow same-route links and browser history', async ({ page }) => {
  await gotoHydrated(page, `${base}/pipelines/?q=rnaseq`);
  const search = page.getByRole('textbox', { name: 'Search pipelines', exact: true });
  await expect(search).toHaveValue('rnaseq');
  await page.locator('footer').getByRole('link', { name: /^Epigenomics/ }).click();
  await expect(page).toHaveURL(/\/pipelines\/\?domain=Epigenomics$/);
  await expect(search).toHaveValue('');
  await expect(page.getByRole('button', { name: /^Epigenomics/ })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('main article')).not.toHaveCount(0);
  // Exiting cards can remain mounted briefly while the filter animation finishes.
  await expect(page.locator('main article').filter({ hasNotText: 'Epigenomics' })).toHaveCount(0);
  await search.fill('chip');
  await expect(page).toHaveURL(/domain=Epigenomics&q=chip$/);
  await page.goBack();
  await expect(search).toHaveValue('rnaseq');
  await expect(page.getByRole('button', { name: /^All\s*\d/ })).toHaveAttribute('aria-pressed', 'true');
  await page.goForward();
  await expect(search).toHaveValue('chip');
  await expect(page.getByRole('button', { name: /^Epigenomics/ })).toHaveAttribute('aria-pressed', 'true');
  // A link without either filter must clear both, rather than retain old component state.
  await page.locator('footer').getByRole('link', { name: 'All pipelines', exact: true }).click();
  await expect(search).toHaveValue('');
  await expect(page.getByRole('button', { name: /^All\s*\d/ })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('main article')).toHaveCount(JSON.parse(fs.readFileSync('../catalog.json', 'utf8')).length);
  // Editing filters keeps unrelated URL data and an in-page target, including a base path.
  await page.evaluate(() => history.pushState(null, '', '?keep=1#main'));
  await search.fill('rnaseq');
  await expect(page).toHaveURL(new RegExp(`${base}/pipelines/\\?keep=1&q=rnaseq#main$`));
});

test('scrnaseq retains generated mandatory guidance without changing schema requiredness', async ({ page }) => {
  const skill = fs.readFileSync('../pipelines/scrnaseq/skill.md', 'utf8');
  expect(skill).toContain('## Mandatory arguments');
  await page.goto(`${base}/pipelines/scrnaseq/`);
  const guidance = page.locator('#run .glass').filter({ has: page.getByRole('heading', { name: 'Mandatory arguments', exact: true }) });
  await expect(guidance).toContainText('Set them deliberately.');
  await expect(guidance).toContainText('--protocol');
  await expect(guidance).toContainText('cellranger only');
  await expect(page.locator('#required').getByText('--protocol', { exact: true })).toHaveCount(0);
});

test('homepage statistics show their actual values without JavaScript', async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  try {
    const page = await context.newPage();
    await page.goto(`${base}/`);
    const counters = page.locator('main a span[aria-hidden].tabular-nums');
    await expect(counters).toHaveCount(4);
    for (const counter of await counters.all()) {
      await expect(counter).toHaveText(await counter.locator('xpath=following-sibling::span').textContent() || '');
    }
  } finally { await context.close(); }
});
