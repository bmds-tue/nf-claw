# nf-claw website

A **living digital interface** for the nf-claw repository — futuristic, dark, and
fully data-driven. Nothing about pipelines, versions, skills, parameters or docs is
hardcoded: every value on the site is read from the repository at build time.

## Stack

- **Next.js 15** (App Router, React Server Components) · **TypeScript**
- **Tailwind CSS 4** (custom design system derived from the brand logo)
- **Framer Motion** (scroll storytelling, micro-interactions)
- **react-markdown** (documentation hub)

Shared UI components live in `src/components/ui`.

## The repository is the CMS

The data layer (`src/lib/data`) is the single source of truth and reads, at build time:

| Source in the repo | Powers |
|---|---|
| `catalog.json` | the pipeline list |
| `pipelines/<name>/skill.md` (frontmatter + body) | run commands, samplesheet, required params, outputs |
| `pipelines/<name>/reference.md` | the full parameter explorer (every group + parameter) |
| `sources.tsv`, `.gitmodules` | upstream URLs and version policy |
| `pipelines/<name>/upstream/` (submodule) | pinned release date + nf-core module count |
| `.github/workflows/*.yml` | the CI/CD / automation panel |
| `README.md`, `docs/*.md`, `CONTRIBUTING.md`, … | the documentation hub |
| local `git log` / `git tag` | the update history + release timeline |

**Add a pipeline, push a release, edit a doc → the site reflects it on the next build.**
No page is maintained by hand. The design scales from 5 to 500 pipelines: the constellation
gives each research domain a wedge sized to its pipeline count and tightens its rings until
every node fits, and the explorers page, group and search rather than render everything.

## Navigating it

- **⌘K / Ctrl K or `/`** opens a command palette over every pipeline, doc and home section; with
  an empty query it offers the pipelines this browser opened last.
- **How it works** types out the agent's three steps with real repository content — the
  `catalog.md` lines a grep returns, an excerpt of a `skill.md`, its run and demo commands
  (`src/lib/data/quickstart.ts`).
- The header marks the section being read (scroll-spy on the home page, the route elsewhere)
  and shows reading progress; pipeline pages add a sticky "on this page" bar, docs a
  table of contents, and both have previous/next links.
- Filters are shareable: `/pipelines/?domain=Epigenomics&q=chip`, and a skills search hands
  its query to the pipeline's parameter explorer (`/pipelines/rnaseq/?q=aligner#parameters`).
- Research domains (`src/lib/derive.ts`) are matched from each pipeline's name and
  description — no per-pipeline list to maintain; anything unmatched lands in "Other".

## Develop

Use the current patch release of Node.js 24 LTS, matching CI and deployment builds.
[Node.js 20 is end-of-life](https://nodejs.org/en/about/eol) and receives no security fixes.

```bash
cd website
npm ci
npm run dev        # http://localhost:3000
```

## Build

The site is exported as a fully static bundle (`output: "export"`) into `out/` — no
server runtime is required.

```bash
npm run build          # writes ./out
npx serve out          # preview the static bundle
```

The Tailwind 4 build targets Safari 16.4+, Chrome 111+ and Firefox 128+; see the
[official browser requirements](https://tailwindcss.com/docs/upgrade-guide#browser-requirements).

For project-site hosting under a sub-path, set the base path at build time:

```bash
NEXT_PUBLIC_BASE_PATH=/nf-claw NEXT_PUBLIC_SITE_URL=https://<user>.github.io npm run build
```

## Deployment

1. **GitHub Pages (default).** `.github/workflows/deploy-pages.yml` builds the static
   bundle on every push to `main` and publishes it to Pages. It checks out the pinned
   submodules and full git history so the data layer can read release dates, module
   counts, tags and the commit log, and it derives the base path/origin from the Pages
   configuration. Every push to `main` rebuilds the site from the current repository state.
   A bot merge (`auto-update`, `discover-pipelines`) is made with `GITHUB_TOKEN` and triggers
   no push workflow, so those jobs dispatch the deploy after merging. No tokens required.
2. **Live GitHub augmentation (optional).** If a `GITHUB_TOKEN` (or `GH_TOKEN`) is present
   at build time, `src/lib/data/github.ts` augments the Activity section with live Actions
   runs and Releases via the REST API. Without it, the site falls back to local git tags
   and workflow definitions. The token is only ever read at build time and is never shipped
   to the client.

Override the data root with `NFCLAW_REPO_ROOT` if the website is built outside the repo.

## Design system

Defined in `tailwind.config.ts` and `src/app/globals.css`, derived from the logo
(white line-art T-rex + green apple on black):

- **Surfaces** — a near-black `ink` scale with subtle elevation
- **Primary** — apple-green `claw` scale
- **Secondary** — warm `cream` (the apple's bite)
- **Text** — `fog` scale; even the dimmest step clears WCAG AA (4.5:1) on every surface
- **Domains** — eight categorical colors validated for the dark surface (lightness band,
  ≥ 3:1 contrast, adjacent pairs distinct under protan/deutan simulation, in wedge order);
  reordering them re-pairs neighbours, so re-validate before changing `CATEGORIES`
- Consistent spacing, `glass` cards with a pointer spotlight, ambient glows, film grain,
  keyboard focus rings, and reduced-motion support throughout
