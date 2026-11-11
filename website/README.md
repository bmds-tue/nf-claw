# nf-claw website

The static website at [bmds-tue.github.io/nf-claw](https://bmds-tue.github.io/nf-claw/). It is built
from the repository: pipeline metadata, versions, skills, parameters and documentation are read at
build time, and no page is maintained by hand.

## Stack

- Next.js 16 (App Router, React Server Components) and TypeScript
- Tailwind CSS 4, with colours taken from the logo
- Framer Motion for animation
- react-markdown for the documentation pages

Shared UI components are in `src/components/ui`.

## Where the content comes from

The data layer in `src/lib/data` reads these files at build time:

| Source | Used for |
|---|---|
| `catalog.json` | The pipeline list. |
| `pipelines/<name>/skill.md` (front matter and body) | Run commands, samplesheet, required parameters, outputs. |
| `pipelines/<name>/reference.md` | The parameter explorer (every group and parameter). |
| `sources.tsv`, `.gitmodules` | Upstream URLs and update policy. |
| `pipelines/<name>/upstream/` (submodule) | The pinned release's date and its number of nf-core modules. |
| `.github/workflows/*.yml` | The automation panel. |
| `README.md`, `docs/*.md`, `CONTRIBUTING.md` and the other root guides | The documentation pages. The README's first paragraph is also the home page's lead. |
| local `git log` and `git tag` | The update history and the release timeline. |

Adding a pipeline, releasing or editing a guide changes the site on its next build. The layout does
not depend on the number of pipelines: the home page's domain chart gives each research domain a
wedge sized by its pipeline count and tightens its rings until every pipeline fits, and the
explorers page, group and search their content instead of rendering everything at once.

## Using the site

- `⌘K`, `Ctrl K` or `/` opens a search over every pipeline, document, documentation section and
  home page section. With an empty query it lists the pipelines this browser opened most recently.
- "How it works" shows an agent's three steps with real repository content: the `catalog.md` lines
  a grep returns, an excerpt of a `skill.md`, and its run and demo commands
  (`src/lib/data/quickstart.ts`).
- The header marks the section being read (by scrolling on the home page, by route elsewhere) and
  shows reading progress. Pipeline pages have an "on this page" bar, documents a table of contents,
  and both link to the previous and next page.
- Filters are kept in the URL, so they can be shared: `/pipelines/?domain=Epigenomics&q=chip`. A
  search in the skills explorer opens the pipeline's parameter list with the same query
  (`/pipelines/rnaseq/?q=aligner#parameters`).
- Research domains (`src/lib/derive.ts`) are matched from each pipeline's name and description, so
  there is no per-pipeline list to maintain; pipelines that match no domain are under "Other".

## Develop

Use the current patch release of Node.js 24 LTS, as CI and deployment do. Node.js 20 is
[end-of-life](https://nodejs.org/en/about/eol) and receives no security fixes.

Build from a Git checkout of the repository. Initialise the pinned submodules
(`git submodule update --init`) for release dates and module counts, and keep the full Git history
for the activity timeline.

```bash
cd website
npm ci
npm run dev        # http://localhost:3000
```

## Build

The site is exported as static files (`output: "export"`) into `out/`; no server is needed.

```bash
npm run build          # writes ./out
npx serve out          # preview the static files
```

`npm run typecheck` checks the TypeScript without building. There is no `npm start`: `next start`
cannot serve a static export, so preview `out/` instead.

## Test

```bash
npx playwright install chromium   # once
npm run build && npm run test:browser
```

The browser tests serve `out/` and drive it in Chromium:

| Spec | What it checks |
|---|---|
| `tests/operations.spec.ts` | How the built pages behave. |
| `tests/accessibility.spec.ts` | axe-core on every exported page, on the layouts that change at phone width, on the open search and on a fully expanded parameter list; any violation fails. |
| `tests/links.spec.ts` | Which link targets rendered text may use, and how repository links resolve. |
| `tests/format.spec.ts` | The wording of workflow schedules and of the release timeline's months. |
| `tests/audit-regressions.spec.ts` | Regressions found by the repository audits. |

CI also runs the site's Markdown parser tests over every generated `skill.md` from the repository
root (`pytest tests/test_website_parsing.py`); a skipped test fails the job.

The Tailwind 4 build targets Safari 16.4+, Chrome 111+ and Firefox 128+ (Tailwind's
[browser requirements](https://tailwindcss.com/docs/upgrade-guide#browser-requirements)).

To host the site under a sub-path, set the base path at build time:

```bash
NEXT_PUBLIC_BASE_PATH=/nf-claw NEXT_PUBLIC_SITE_URL=https://<user>.github.io npm run build
```

## Deployment

1. **GitHub Pages.** `.github/workflows/deploy-pages.yml` builds the site on every push to `main` and
   publishes it to Pages. It checks out the pinned submodules and the full Git history, so the data
   layer can read release dates, module counts, tags and the commit log, and it takes the base path
   and origin from the Pages configuration. The maintenance bots (`auto-update`,
   `discover-pipelines`) update `main` with `GITHUB_TOKEN`, which triggers no push workflow, so they
   start the deployment themselves after publishing. Deployment uses the workflow's `GITHUB_TOKEN`
   and Pages OIDC permissions; no personal access token is needed.
2. **Live GitHub data (optional).** If `GITHUB_TOKEN` or `GH_TOKEN` is set at build time,
   `src/lib/data/github.ts` adds recent Actions runs to the activity section through the REST API.
   Without a token, the site shows the local Git history and the workflow definitions. Release
   information always comes from the local pins and Git tags. The token is read only at build time
   and never reaches the browser. The Actions data is a snapshot from the build; the site does not
   poll GitHub and changes only when it is deployed again.

Set `NFCLAW_REPO_ROOT` to build the website from outside the repository.

## Design tokens

Defined in `tailwind.config.ts` and `src/app/globals.css`, with colours taken from the logo (a white
line-art T-rex and a green apple on black):

- `ink`: near-black surfaces with slight elevation steps
- `claw`: apple green, the primary colour
- `cream`: a warm secondary colour (the apple's bite)
- `fog`: text. Body text uses the default, muted and dim steps; the darker `faint` step is only for
  decoration.
- Domain colours: eight categorical colours checked against the dark surface (a lightness band,
  contrast of at least 3:1, and neighbours that stay distinct under protan and deutan simulation, in
  wedge order). Reordering them changes which colours sit next to each other, so check them again
  before changing `CATEGORIES`.
- Cards use a translucent `glass` style with a highlight that follows the pointer. Focus rings are
  visible for keyboard users, and animation respects reduced-motion settings.
