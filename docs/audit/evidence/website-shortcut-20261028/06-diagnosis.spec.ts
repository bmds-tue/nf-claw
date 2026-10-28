import { test, expect } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    const events: unknown[] = [];
    (window as any).__auditEvents = events;
    const snapshot = (event: string, data: object = {}) => events.push({
      time: performance.now(), event, url: location.href,
      menu: Boolean(document.querySelector('header[role="dialog"]')),
      input: Boolean(document.querySelector('input[role="combobox"]')),
      inert: document.querySelector('main')?.hasAttribute('inert'),
      focus: document.activeElement?.outerHTML.slice(0, 160), ...data,
    });
    const add = window.addEventListener.bind(window);
    window.addEventListener = function(type: string, ...args: any[]) {
      if (type === 'keydown' || type === 'nfclaw:open-palette') snapshot('listener-installed', {type});
      return (add as any)(type, ...args);
    } as typeof window.addEventListener;
    add('keydown', e => { snapshot('keydown', {key:e.key, repeat:e.repeat, ctrl:e.ctrlKey}); queueMicrotask(() => snapshot('keydown-after', {prevented:e.defaultPrevented})); }, true);
    add('nfclaw:open-palette', () => snapshot('open-event'), true);
    add('error', e => snapshot('error', {message:e.message}));
    add('DOMContentLoaded', () => {
      let previous='';
      new MutationObserver(() => {
        const next=[Boolean(document.querySelector('header[role="dialog"]')),Boolean(document.querySelector('input[role="combobox"]')),document.querySelector('main')?.hasAttribute('inert')].join();
        if (next !== previous) { previous=next; snapshot('state-change'); }
      }).observe(document.documentElement, {subtree:true, childList:true, attributes:true, attributeFilter:['role','inert']});
    });
  });
});
test.afterEach(async ({page}, info) => {
  await info.attach('event-record', {body:JSON.stringify(await page.evaluate(() => (window as any).__auditEvents),null,2),contentType:'application/json'});
});
for (const mode of ['original', 'menu-precondition']) {
  test(`shortcut ${mode}`, async ({page}) => {
    await page.setViewportSize({width:390,height:844});
    await page.goto('/pipelines/');
    await page.getByRole('button',{name:'Open menu'}).click();
    if (mode === 'menu-precondition') {
      await expect(page.getByRole('dialog',{name:'Navigation menu'})).toBeVisible();
      await expect(page.locator('main')).toHaveAttribute('inert','');
    }
    await page.keyboard.press('Control+k');
    await expect(page.locator('input[role="combobox"]')).toBeFocused();
    await expect(page.getByRole('dialog',{name:'Navigation menu'})).toHaveCount(0);
  });
}
test('holding shortcut does not close search', async ({page}) => {
  await page.goto('/pipelines/');
  // A working button proves hydration and the global handler are ready.
  await page.getByRole('button',{name:'Search (⌘K)'}).click();
  await expect(page.locator('input[role="combobox"]')).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(page.locator('input[role="combobox"]')).toHaveCount(0);
  await page.keyboard.down('Control');
  try {
    await page.keyboard.down('k');
    await expect(page.locator('input[role="combobox"]')).toBeFocused();
    await page.keyboard.down('k');
    await expect(page.locator('input[role="combobox"]')).toBeFocused();
  } finally { await page.keyboard.up('k'); await page.keyboard.up('Control'); }
});
