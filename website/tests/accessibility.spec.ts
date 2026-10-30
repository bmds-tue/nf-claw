import { test, expect, type Page } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

// axe-core on every page of the static export, as built. Pages are generated from the repository's
// own documents, so a heading level or table written in one of them reaches the site unreviewed;
// sampling a few pages missed exactly that.
const AXE = fs.readFileSync(createRequire(import.meta.url).resolve('axe-core/axe.min.js'), 'utf8');
const OUT = fileURLToPath(new URL('../out', import.meta.url));

function pages(dir = OUT): string[] {
  const found: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name !== '_next') found.push(...pages(full));
    } else if (entry.name.endsWith('.html')) {
      const rel = path.relative(OUT, full).split(path.sep).join('/');
      found.push('/' + (rel.endsWith('index.html') ? rel.slice(0, -'index.html'.length) : rel));
    }
  }
  return found.sort();
}

type Axe = {
  run: (context: Document, options: object) => Promise<{
    violations: { id: string; impact: string; help: string; nodes: { target: string[] }[] }[];
  }>;
};

/** Wait until no element's opacity is still changing: a fade that reduced motion leaves in place
 *  (an opacity change is not motion) must not be measured half-way. */
async function settle(page: Page) {
  let previous = '';
  let unchanged = 0;
  for (let sample = 0; sample < 50; sample++) {
    const current = await page.evaluate(() => Array.from(document.querySelectorAll('body *'),
      (element) => getComputedStyle(element).opacity).join());
    unchanged = current === previous ? unchanged + 1 : 0;
    if (unchanged === 2) return;
    previous = current;
    await page.waitForTimeout(150);
  }
  throw new Error('opacity still changing after 7.5 s');
}

/** Each violation as one line: the rule, its impact, and the first elements that break it. */
async function violations(page: Page): Promise<string[]> {
  await settle(page);
  await page.addScriptTag({ content: AXE });
  return page.evaluate(async () => {
    const axe = (window as unknown as { axe: Axe }).axe;
    const { violations } = await axe.run(document, { resultTypes: ['violations'] });
    return violations.map((v) => `${v.id} (${v.impact}): ${v.help} — `
      + v.nodes.slice(0, 3).map((n) => n.target.join(' ')).join(', '));
  });
}

// Entrance animations end where they start under reduced motion, so nothing is checked mid-fade.
test.use({ reducedMotion: 'reduce' });

const all = fs.existsSync(OUT) ? pages() : [];

test('the static export is there to check', () => {
  expect(all.length).toBeGreaterThan(100);
});

for (const url of all) {
  test(`${url} has no axe violation`, async ({ page }) => {
    // A script error or a request the page could not load leaves it half-rendered (or on Next's
    // error page), which axe would report as something else: name it instead.
    const broken: string[] = [];
    page.on('pageerror', (error) => broken.push(`page error: ${error.message}`));
    page.on('requestfailed', (request) => broken.push(
      `request failed: ${request.url()} (${request.failure()?.errorText})`));
    await page.goto(url);
    await page.waitForLoadState('networkidle');
    expect(broken).toEqual([]);
    expect(await violations(page)).toEqual([]);
  });
}

// Layouts that change at phone width, one page of each kind.
for (const url of ['/', '/pipelines/', '/pipelines/rnaseq/', '/docs/', '/docs/chaining/', '/404/']) {
  test(`${url} has no axe violation at phone width`, async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(url);
    await page.waitForLoadState('networkidle');
    expect(await violations(page)).toEqual([]);
  });
}

test('the open search palette has no axe violation', async ({ page }) => {
  await page.goto('/pipelines/');
  await page.getByRole('button', { name: /^Search (⌘K|Ctrl K)$/ }).click();
  await expect(page.locator('input[role="combobox"]')).toBeFocused();
  await page.keyboard.type('rna');
  expect(await violations(page)).toEqual([]);
});

test('a pipeline page with every parameter expanded has no axe violation', async ({ page }) => {
  await page.goto('/pipelines/bacmodel/');
  await page.waitForFunction(() => window.localStorage.getItem('nfclaw:recent-pipelines')?.includes('"bacmodel"'));
  for (const row of await page.locator('#parameters button[aria-expanded]').all()) {
    if (await row.getAttribute('aria-expanded') === 'false') await row.click();
  }
  await expect(page.locator('#parameters button[aria-expanded="false"]')).toHaveCount(0);
  expect(await violations(page)).toEqual([]);
});

test('an expanded parameter appears at once under reduced motion', async ({ page }) => {
  // The rows grew and faded in over 280 ms whatever the reader's motion setting, unlike the rest of
  // the site; axe then measured the contrast of a half-faded row on a slower host.
  await page.goto('/pipelines/bacmodel/');
  await page.waitForFunction(() => window.localStorage.getItem('nfclaw:recent-pipelines')?.includes('"bacmodel"'));
  const opacity = await page.evaluate(async () => {
    const toggle = document.querySelector<HTMLButtonElement>('#parameters button[aria-expanded="false"]')!;
    toggle.click();
    for (let frame = 0; frame < 3; frame++) await new Promise(requestAnimationFrame);
    const panel = toggle.closest('.group\\/row')?.querySelector(':scope > .overflow-hidden');
    return panel ? Number(getComputedStyle(panel).opacity) : -1;
  });
  expect(opacity).toBe(1);
});
