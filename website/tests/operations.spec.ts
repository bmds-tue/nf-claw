import { test, expect, type Page } from '@playwright/test';

/** Open a pipeline page once React has hydrated it: before that, a click reaches server-rendered
 *  markup with no handlers. The page records the visit in an effect, which runs only after. */
async function openHydrated(page: Page, name: string) {
  await page.goto(`/pipelines/${name}/`);
  await page.waitForFunction(n => window.localStorage.getItem('nfclaw:recent-pipelines')?.includes(`"${n}"`), name);
}

for (const pipeline of ['createtaxdb', 'funcscan']) {
  test(`${pipeline} shows its recorded workflow correction beside run guidance`, async ({ page }) => {
    await page.goto(`/pipelines/${pipeline}/`);
    await expect(page.getByRole('heading', { name: 'Runtime corrections', exact: true })).toBeVisible();
    await expect(page.getByText(/NFCLAW_SOURCE_CACHE/)).toBeVisible();
    await expect(page.getByRole('link', { name: 'Recorded source corrections' })).toBeVisible();
  });
}

test('funcscan shows the prepared DRAMP reference route beside its run guidance', async ({ page }) => {
  await page.goto('/pipelines/funcscan/');
  await expect(page.getByRole('heading', { name: 'Reference database', exact: true })).toBeVisible();
  await expect(page.getByText(/nfclaw prepare-dramp/)).toBeVisible();
  await expect(page.getByRole('link', { name: 'DRAMP reference preparation' })).toBeVisible();
});

test('proteinfold shows its authoritative demo caveat beside the command', async ({ page }) => {
  await page.goto('/pipelines/proteinfold/');
  await expect(page.locator('#run')).toContainText(/placeholder|computes nothing/i);
});

for (const path of ['/docs/agents/', '/']) {
  test(`${path} shows its content without JavaScript`, async ({ browser }) => {
    // Entrance animations start from opacity 0, which only a script can lift.
    const context = await browser.newContext({ javaScriptEnabled: false });
    try {
      const page = await context.newPage();
      await page.goto(path);
      const content = page.locator('main h1, main h1 ~ p, main a[href="/docs/"]');
      expect(await content.count()).toBeGreaterThan(path === '/' ? 2 : 0);
      for (const element of await content.all()) {
        await expect(element).toBeVisible();
        const opacity = await element.evaluate((node) => {
          let opacity = 1;
          for (let at: Element | null = node; at; at = at.parentElement)
            opacity *= Number(getComputedStyle(at).opacity);
          return opacity;
        });
        expect(opacity).toBe(1);
      }
    } finally { await context.close(); }
  });
}

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
    await expect(page.getByRole('dialog', { name: 'Navigation menu' })).toBeVisible();
    await expect(page.locator('main')).toHaveAttribute('inert', '');
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

test('holding the search shortcut opens once and a new press closes it', async ({ page }) => {
  await page.goto('/pipelines/');
  await page.getByRole('button', { name: /^Search (⌘K|Ctrl K)$/ }).click();
  const input = page.locator('input[role="combobox"]');
  await expect(input).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(input).toHaveCount(0);
  await page.keyboard.down('Control');
  try {
    await page.keyboard.down('k');
    await expect(input).toBeFocused();
    await page.keyboard.down('k');
    await expect(input).toBeFocused();
    await page.keyboard.up('k');
    await page.keyboard.down('k');
    await expect(input).toHaveCount(0);
  } finally {
    await page.keyboard.up('k');
    await page.keyboard.up('Control');
  }
});

test('a second shortcut press right after the palette takes focus closes it', async ({ page }) => {
  // Opening goes through a custom event, so React defers its effects to a later task while the
  // input takes focus during the commit. A press in between met a listener that still saw the
  // palette closed, and it stayed open (the holding test above failed this way under load).
  await page.goto('/pipelines/');
  await page.getByRole('button', { name: /^Search (⌘K|Ctrl K)$/ }).click();
  const input = page.locator('input[role="combobox"]');
  await expect(input).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(input).toHaveCount(0);
  await page.evaluate(() => {
    const press = () => window.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'k', ctrlKey: true, bubbles: true }));
    document.addEventListener('focusin', (e) => {
      if ((e.target as Element).matches('input[role="combobox"]')) queueMicrotask(press);
    }, { once: true });
    press();
  });
  await expect(input).toHaveCount(0);
});

test('the search palette finds a documentation section and opens it at its heading', async ({ page }) => {
  // Titles alone could not find what a guide says: a query lists the sections whose headings match.
  await page.goto('/pipelines/');
  await page.getByRole('button', { name: /^Search (⌘K|Ctrl K)$/ }).click();
  const input = page.locator('input[role="combobox"]');
  await expect(input).toBeFocused();
  await expect(page.getByText('In the docs', { exact: false })).toHaveCount(0);   // none unasked
  await input.fill('dependency stability during');
  const option = page.getByRole('option', { name: /Dependency stability during execution/ });
  await expect(option).toBeVisible();
  await expect(option).toContainText('Replaying and verifying runs');
  await option.click();
  await expect(page).toHaveURL(/\/docs\/replay\/#dependency-stability-during-execution$/);
  await expect(page.locator('#dependency-stability-during-execution')).toBeInViewport();
});

test('a document has a table of contents at phone width too', async ({ page }) => {
  // The sticky "On this page" column exists only from the xl breakpoint; narrower screens had none.
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/docs/replay/');
  const toc = page.locator('details', { has: page.locator('summary', { hasText: 'On this page' }) });
  await expect(toc).toBeVisible();
  await toc.locator('summary').click();
  const link = toc.getByRole('link', { name: 'Local inputs and resume' });
  await expect(link).toBeVisible();
  await link.click();
  await expect(page).toHaveURL(/\/docs\/replay\/#local-inputs-and-resume$/);
  await expect(page.locator('#local-inputs-and-resume')).toBeInViewport();
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

for (const width of [1280, 390]) {
  test(`skills arrows follow the focused row at width ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 });
    await page.goto('/#skills');
    const input = page.locator('#skills input').first();
    const index = page.waitForResponse(response => response.url().endsWith('/search/params.json'));
    await input.focus();
    await (await index).finished();
    await input.fill('rna');
    const rows = page.locator('#skills [data-skill]:visible');
    await expect(rows.first()).toHaveAttribute('data-skill', /^rna/);
    await expect(rows.nth(1)).toBeVisible();
    await rows.first().focus();
    await expect(rows.first()).toBeFocused();
    await page.keyboard.press('ArrowDown');
    await expect(rows.nth(1)).toBeFocused();
    await page.keyboard.press('Home');
    await expect(rows.first()).toBeFocused();
    await input.focus();
    await input.press('Escape');
    await expect(input).toHaveValue('');
  });
}

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

test('the status tiles report the auto-update and drift-check workflows themselves', async ({ page }) => {
  const fs = await import('node:fs');
  const workflow = (file: string) => fs.readFileSync(`../.github/workflows/${file}`, 'utf8');
  expect(workflow('auto-update.yml')).toMatch(/cron: "0 6 \* \* \*"/);
  expect(workflow('drift-check.yml')).toMatch(/^on:\n {2}pull_request:/m);
  await page.goto('/');
  const tiles = page.locator('#activity .glass-hover');
  await expect(tiles.filter({ hasText: 'Auto-update' })).toContainText('Daily at 06:00 UTC');
  await expect(tiles.filter({ hasText: 'Auto-update' })).toContainText('auto-update workflow');
  await expect(tiles.filter({ hasText: 'Drift gate' })).toContainText('Enforced on every PR');
});

test('the security policy is published with the guides that point to it', async ({ page }) => {
  await page.goto('/docs/contributing/');
  const link = page.locator('main article').getByRole('link', { name: 'SECURITY.md' });
  await expect(link).toHaveAttribute('href', /\/docs\/security\/$/);
  await link.click();
  await expect(page).toHaveURL(/\/docs\/security\/$/);
  await expect(page.locator('main h1').first()).toHaveText('Security policy');
});

test('a copy the browser refuses is reported as failed, never as copied', async ({ page }) => {
  const errors: Error[] = [];
  page.on('pageerror', error => errors.push(error));
  // The Clipboard API refuses, so the control falls back to execCommand, whose outcome the
  // test sets per click: refused (false), unsupported (throws), then accepted (true).
  await page.addInitScript(() => {
    const state = window as unknown as { copyOutcome: boolean | 'throw' };
    state.copyOutcome = false;
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: () => Promise.reject(new DOMException('Write permission denied.', 'NotAllowedError')) },
    });
    document.execCommand = () => {
      if (state.copyOutcome === 'throw') throw new Error('copy is not supported');
      return state.copyOutcome;
    };
  });
  await openHydrated(page, 'bacmodel');
  const command = page.locator('#run .group').first();
  const button = command.getByRole('button');
  for (const outcome of [false, 'throw'] as const) {
    await page.evaluate(value => {
      (window as unknown as { copyOutcome: boolean | 'throw' }).copyOutcome = value;
    }, outcome);
    await expect(button).toHaveText('Copy');
    await button.click();
    await expect(button).toHaveText('Copy failed');
    await expect(button).toHaveAttribute('aria-label', 'Copy failed');
    await expect(button).toBeFocused();
  }
  await page.evaluate(() => { (window as unknown as { copyOutcome: boolean }).copyOutcome = true; });
  await expect(button).toHaveText('Copy');
  await button.click();
  await expect(button).toHaveText('Copied');
  expect(errors).toEqual([]);
});

test('parameter rows keep description links out of their toggle buttons', async ({ page }) => {
  await openHydrated(page, 'bacmodel');
  // A link inside a button is invalid markup, and following it toggled the row as well.
  await expect(page.locator('#parameters p a').first()).toBeVisible();
  await expect(page.locator('#parameters button a, #parameters button button')).toHaveCount(0);
  // The description still toggles its row, except where it is a link.
  const plain = page.locator('#parameters button[aria-expanded] + p:not(:has(a))').first();
  const plainToggle = plain.locator('xpath=preceding-sibling::button[1]');
  await expect(plainToggle).toHaveAttribute('aria-expanded', 'false');
  await plain.click();
  await expect(plainToggle).toHaveAttribute('aria-expanded', 'true');
  await plainToggle.click();
  await expect(plainToggle).toHaveAttribute('aria-expanded', 'false');
  const linked = page.locator('#parameters button[aria-expanded] + p:has(a)').first();
  const linkedToggle = linked.locator('xpath=preceding-sibling::button[1]');
  await linkedToggle.click();
  await expect(linkedToggle).toHaveAttribute('aria-expanded', 'true');
  await page.evaluate(() => document.addEventListener('click', event => {
    if ((event.target as Element).closest('a')) event.preventDefault(); // stay on the page
  }, true));
  await linked.locator('a').first().click();
  await expect(linkedToggle).toHaveAttribute('aria-expanded', 'true');
});

test('the skills list is a listbox beside its detail and disclosures above it', async ({ page }) => {
  await page.goto('/');
  const listbox = page.locator('#skills [role="listbox"]');
  await expect(listbox).toHaveCount(1);
  await expect(listbox.locator('[data-skill]:not([role="option"])')).toHaveCount(0);
  await expect(listbox.locator('button:not([role="option"]), a')).toHaveCount(0);
  // On a small screen each skill opens under its row, so the rows are disclosure buttons instead.
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(listbox).toHaveCount(0);
  const row = page.locator('#skills [data-skill]').first();
  await expect(row).toHaveAttribute('aria-expanded', 'false');
  await expect(row).not.toHaveAttribute('role', 'option');
  await row.click();
  await expect(row).toHaveAttribute('aria-expanded', 'true');
  await expect(page.locator('#skills h3:visible', { hasText: 'Parameter groups' })).toHaveCount(1);
  await page.setViewportSize({ width: 1440, height: 900 });
  await expect(listbox).toHaveCount(1);
});

test('a heading link shows itself when the keyboard reaches it', async ({ page }) => {
  await page.goto('/docs/agents/');
  const link = page.locator('main h2 a[aria-label="Link to this section"]').first();
  await link.focus();
  expect(await link.evaluate(node => node.matches(':focus-visible'))).toBe(true);
  await expect.poll(() => link.evaluate(node => getComputedStyle(node).opacity)).toBe('1');
});

test('tables wider than a phone can be scrolled from the keyboard', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/pipelines/bacmodel/');
  const table = page.getByRole('region', { name: 'Samplesheet columns' });
  await expect(table).toHaveAttribute('tabindex', '0');
  expect(await table.evaluate(node => node.scrollWidth > node.clientWidth)).toBe(true);
  await table.focus();
  await page.keyboard.press('ArrowRight');
  await expect.poll(() => table.evaluate(node => node.scrollLeft)).toBeGreaterThan(0);
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
