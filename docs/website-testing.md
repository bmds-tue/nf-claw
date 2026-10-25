# Website search and browser verification

The production static export is the browser test target. The suite runs Chromium
at desktop and mobile sizes under the configured `/nf-claw` project base path.
It covers search shortcuts, keyboard navigation, focus restoration and trapping,
full-text remedies and section links, URL filters with reload/back/forward,
parameter searches, documentation navigation and mobile navigation. Axe checks
the navigation and search dialog for relevant WCAG accessibility violations.
Tests also fail on JavaScript exceptions and failed local requests, retaining
screenshots, traces and an HTML report on failure. These checks do not constitute
an audit of every page or assistive-technology/browser combination.

```bash
npm --prefix website ci
cd website
npx playwright install chromium --only-shell
npm run typecheck
npm run build:test
npm run test:browser
```

Linux hosts may need Playwright's browser system dependencies; CI installs them
with `playwright install --with-deps chromium --only-shell`. Browser binaries can
use an isolated `PLAYWRIGHT_BROWSERS_PATH`. Test reports and traces are ignored by
Git and retained as CI artifacts. `scripts/serve-export.mjs` serves only the built
files on loopback, preserving the project base path; it does not run Next.js in
development mode.

Documentation search builds `search/docs.json` from root guides and `docs/*.md`.
It indexes headings and body content, including error text in fenced code blocks,
and uses the renderer's heading IDs for section links. The command palette loads
the index on its first opening. Search results include a bounded contextual
snippet. Queries are literal text, never HTML or executable regular expressions;
result text is rendered through React's escaping. Matching limits query length,
tokens and returned sections. Existing pipeline and parameter searches retain
their separate indexes. Domain changes create history entries; editing a text
filter updates the current entry, and back/forward restores the URL's filter state.
