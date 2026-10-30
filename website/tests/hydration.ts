import type { Page } from '@playwright/test';

/** Open a page and wait until React has attached to it. Before that, a click or key press reaches
 *  server-rendered markup with no handlers and is lost; from then on React handles it, replaying
 *  one that arrives while it is still hydrating. `goto` returns at the load event, and on a busy
 *  host React attached up to ~20 ms later: an "Open menu" click right after `goto` did nothing.
 *  React marks the container it hydrates (here the document) with a `__reactContainer$` key. */
export async function gotoHydrated(page: Page, path: string) {
  await page.goto(path);
  await page.waitForFunction(() => Object.keys(document).some(key => key.startsWith('__reactContainer$')));
}
