# Deep repository audit, 2026-10-29

Audited: `3367a5f` (the [2026-10-28 audit](2026-10-28-repository-audit.md), A01–A27, on `58e8e15`).
Server: `denbi_instance`, Python 3.12.3, Nextflow 26.04.3, Docker, every pipeline submodule
initialised. Local: macOS, Python 3.13.

The first audit read every module. This one tested what reading cannot settle, each method
aimed at a class of defect the first could miss:

- **Coverage-guided review.** The whole suite ran under branch coverage, with child processes
  traced (86% of `runner`, `librarian` and `scripts`). The paths no test reaches were reviewed
  and exercised by hand: the MCP `list_versions`, `chain_edges` and versioned `show_pipeline`
  tools against the real CLI, the chain's resume and failure recording, the job supervisor.
- **Property-based fuzzing** (Hypothesis, outside the repository's suite): the MCP protocol layer
  with random and malformed messages and batches (B01); chain specs, handoff rules, run logs and
  resource limits (3 000 cases each), which raised only nfclaw's own errors; and the exact-number
  JSON layer and CLI parameter coercion (8 000 cases), which kept every value.
- **Static analysis** beyond the configured gates: mypy, an extended ruff rule set (blind excepts,
  unused arguments, implicit string concatenation in collections), `shellcheck`, `actionlint` and
  `zizmor` on the workflows (B06, B07).
- **The whole website, not a sample.** Every one of the 118 exported pages was crawled for broken
  links and anchors, and checked with axe-core at desktop and phone widths (B04, B05, B11). Every
  constraint and default cell of the 190 generated `skill.md`/`reference.md` files was rendered
  with a CommonMark parser and compared with its value (B02), and every link in them resolved
  (B03).
- **Documentation against code and data.** Every `nfclaw` flag, MCP tool and `NFCLAW_*` variable
  the docs name exists; every release number next to a pipeline name is a tag of that pipeline
  (B10).
- **A real chain on the server**, not only its unit tests: `bamtofastq → rnaseq` as
  [validation.md](../validation.md) documents it, which exercised the A19 `exhaustive` handoff on
  real outputs (B09).

Each finding was reproduced before it was fixed, and each fix carries a test that fails without
it, except B09 and B10, which are documentation corrected from a real run and the release tags.

## Checklist

| ID | Kind | Finding | Disposition |
|---|---|---|---|
| B01 | Defect | One line of JSON nested 10 000 levels deep ended `nfclaw mcp` (Python 3.12 and 3.13 parse 5 000): the parser raises `RecursionError`, not `ValueError`, and the read loop let it escape, so every later request went unanswered. An exception while receiving any message would have done the same. | A message the parser cannot nest that deep is answered with a parse error (`-32700`), as `--params-file` already treated it. Anything a message raises before dispatch is answered with an internal error under its id (or `null` when its id is not one JSON-RPC allows), and the session continues. |
| B02 | Defect | The generated parameter tables wrote patterns and defaults as plain Markdown. Rendered (GitHub, any viewer), 979 constraint cells and 10 default cells showed a different value from the one nf-schema enforces: `\.` lost its backslash, `[a-z.]([a-z0-9._]*)` became a link, `*` pairs became emphasis. | Patterns, defaults and allowed values are written as code spans, with a longer fence for a value holding backticks. The site reads code spans back to the literal value. All 190 files regenerated; each such cell now renders to exactly its value. |
| B03 | Defect | Upstream descriptions link files relative to the pipeline's own docs; bacmodel's `../assets/medium_carveme_mediadb_example.tsv` pointed nowhere from `reference.md`. | A relative link to a file of the pinned tree becomes a permalink at the pinned commit; any other relative link keeps its label only. |
| B04 | Accessibility | Fifteen documents went from `#` straight to `### Navigation`, and `known-issues.md` opened with a level-3 section: axe `heading-order` on 15 site pages. | Those headings are level 2. |
| B05 | Accessibility | A key-value table in `validation.md` had empty header cells (axe `empty-table-header`). | Headers added. |
| B06 | Hardening | Four workflow checkouts (`smoke`, `nextflow-validate`, `drift-check`, `deploy-pages`) left `GITHUB_TOKEN` in `.git/config` for every later step, including the ones that parse upstream pipeline code. The test enforcing `persist-credentials: false` covered only the maintenance workflows. | Every checkout sets it; the test covers every workflow. None of these jobs pushes. |
| B07 | Hardening | The Dependabot configuration (A26) proposed a release the day it was published, the window in which a hijacked or broken package is usually found and withdrawn. | Version updates wait seven days (`cooldown`); security updates are not delayed. The test requires a cooldown on every entry. |
| B08 | Defect | A `refuse_rows_in` pattern (A19) that also matched the sheet being handed over refused every handoff: `pe.csv also holds 1 row(s) (A) that this handoff cannot hand over with pe.csv`. | The handed-over sheet is never among the sheets checked; `docs/chaining.md` says so. |
| B09 | Documentation (scientific) | The documented `bamtofastq → rnaseq` chain recipe overrode rnaseq's `fasta` and `gtf`, but its `demo: true` test profile also sets a yeast `transcript_fasta` and a prebuilt yeast `salmon_index` for its Salmon pseudo-alignment, which those two do not replace. Run as documented on the server, the human chr22 reads were quantified against yeast transcripts and the pseudo-alignment's SummarizedExperiment failed (`Rows or columns different among input matrices`), its matrices holding only the GFP transgene. | The recipe adds `"skip_pseudo_alignment": true` and says why; the chain then completed (see Evidence). |
| B10 | Documentation | `known-issues.md` named bamtofastq "2.1.2", which was never released. | The row names the pinned 2.2.1 and states what the 2.1.1 and 2.2.0 test profiles share, checked against their tags. |
| B11 | Accessibility | The navigation's search button was named "Search (⌘K)" while it showed "Ctrl K" off macOS: its accessible name neither contained its visible text (WCAG 2.5.3, axe `label-content-name-mismatch` on every page) nor named the shortcut those users press. | The button is named by what it shows, with the word kept for assistive technology where it is hidden, and declares `aria-keyshortcuts="Meta+K Control+K"`, the two shortcuts the palette accepts. |
| B12 | Missing component | Nothing checked the site's accessibility: A20–A24 and B04, B05, B11 were each found by hand, and every document under `docs/` becomes a page. | `website/tests/accessibility.spec.ts` runs axe-core 4.14.0 on every exported page, on the layouts that change at phone width, on the open search palette and on a fully expanded parameter list, as part of the site's browser tests in CI. It fails on the B04 heading. CONTRIBUTING and the website README describe it. |
| B13 | Defect | `--resume` compares the samplesheet it regenerates with the one the previous launch used; a previous sheet holding bytes that are not UTF-8 ended `nfclaw run --resume`, and a chain's resume check, with a `UnicodeDecodeError` traceback (found in the coverage review). | The previous sheet is read with replacement characters, as `named_paths` beside it already tolerated: the note still names the samples added and removed. |
| B14 | Test defect | `test_preview_preserves_existing_submodule_and_untracked_files` relied on the host's GNU `timeout`, which the acceptance gate requires before any preview. On a Mac without coreutils (`make test` as CONTRIBUTING asks) the accepted case failed, and the selected-release case passed without reaching the check it is about. | The test supplies the pass-through `timeout` the module's other tests use, and the selected-release case asserts the refusal it expects (`checkout differs from the pinned commit`). It passes on a host with neither `timeout` nor `gtimeout`. |
| B15 | Accessibility | Expanding a parameter row, a skill's inline detail and its detail swap, the pipeline universe's search field, view toggle, inspector and compare tray, and the hero's delayed scroll cue moved, resized or appeared however the reader's motion setting was set; the rest of the site honours `prefers-reduced-motion`. Found when the new gate (B12) measured the contrast of half-faded text on the server (a parameter row, the inspector, the orbit legend). | Under reduced motion they change at once (`duration: 0`, the pattern the skill rows already used). A browser test expands a row under reduced motion and requires it fully shown three frames later: the original showed it at 0.65 opacity. The accessibility checks wait until no element's opacity is still changing, so a fade reduced motion keeps (an opacity change is not motion) is never measured half-way, and they fail on any page error or failed request, naming it. |
| B16 | Defect | `nfclaw chain run --resume` prepared a handoff-fed stage's input again into `chain/handoffs/<stage>/attempts/<id>/`: identical bytes (`0ab483df…` in the server's bamtofastq → rnaseq run) at a new path. `--resume` counts a new input path as a changed input, so the failed attempt was archived and every task recomputed, although chaining.md ("Cached Retries") and the `run_chain` tool say the failed stage resumes from Nextflow's cache. | When the handoff prepared for the resumed attempt matches the one the failed attempt ran on (its recorded checksum, the same record with the new directory read as the old one, the same bytes in every file), the stage keeps that handoff and its paths, and the extra copy is removed; any difference still gets a new attempt directory. A chain test resumes a failed stage and requires the same samplesheet path, and a fresh one when the earlier record was altered. |

## Evidence

Server `denbi_instance` (Python 3.12.3, Node 22, every submodule initialised, the `dev`, `yaml` and
`scientific` extras installed, website dependencies installed). The baseline is a clean checkout of
`3367a5f`; the change is that checkout with this change applied as one patch (SHA-256
`f05bf90043e7…`, recorded before and after the run; this section is the only later change). Reports
are kept on the server in `~/volume/nfclaw-deep-evidence/` (`base-*`, `v4-*`; the B16 chain run in
`v3-*`; the coverage run as `cov-*`). Temporary files went to the large volume: an earlier final run filled the 19 GB root
filesystem, which other work shares, and failed with `No space left on device`.

| Gate | Baseline `3367a5f` | With this change |
|---|---|---|
| `pytest` (complete suite, JUnit) | 3474 passed, 1 skipped | 3484 passed, 1 skipped |
| `ruff check .` | — | clean |
| `python -m librarian.check_drift` | — | no drift (the 190 regenerated files included) |
| Website `npm audit`, typecheck, export, served `llms.txt` | — | 0 vulnerabilities; typecheck and export pass; `llms.txt` identical |
| Website Playwright | the new accessibility spec: 121 of 127 fail (label in name 119, heading order 16, empty table header 1, contrast 1) | 150 tests (22 operational, 128 accessibility): runs 1 and 2 all passing; runs 3 and 4 149, see below |

The one skip in both is the declared `rnasplice is no longer pinned at the audited commit` fixture.
Browser runs 3 and 4 each lost one page load, in different tests: `net::ERR_NETWORK_CHANGED` on
`127.0.0.1`, and a page that never finished hydrating. Other work on this shared host started 33 and
32 Docker containers during those runs (`docker events`); Docker attaches each to its bridge
network, and Chromium aborts loads in flight when the host's network changes. 150 further loads of
the same build there raised no page error, failed request or error page, and every local run passed
150 of 150.
Every new test was also run against the code it guards with the fix reverted, and failed there.

Real runs with the changed code (`--nxf-env NXF_JVM_ARGS=-Djava.net.preferIPv6Addresses=true`):

- `nfclaw mcp`, sent a ping, one line nested 200 000 levels deep, then a `list_pipelines` call:
  the ping is answered, the deep line gets `-32700`, and the call is answered
  (`variantbenchmarking` first for `variant calling`).
- `bamtofastq → rnaseq` as validation.md documented it: rnaseq failed in `SE_GENE_UNIFIED`
  (pseudo-alignment, matrices holding only the GFP transgene). Resumed with
  `skip_pseudo_alignment`: success, `nfclaw chain status` verified the lineage; STAR-Salmon counted
  1 313 and 1 307 reads for KCNMB3P1 in the two samples, with rnaseq's strandedness caveat. The A19
  `exhaustive` handoff took both paired samples from the real bamtofastq outputs.
- B16, the same chain on the changed code: run as documented before B09 it failed at rnaseq, then
  `--resume` with `skip_pseudo_alignment` kept the handoff its failed attempt used (no new attempt
  directory, no archive, no fresh cache session): Nextflow reused 28 cached tasks, ran the 57 the
  edited parameter affects, and `nfclaw chain status` verified the lineage.
- Coverage (baseline, without the `scientific` extra): 86% of statements and branches of `runner`,
  `librarian` and `scripts`, child processes included.
- Local (macOS, Python 3.13, no submodules): 3260 passed, 225 skipped (pinned sources this clone
  lacks), none failed; before B14 the same run failed its acceptance-gate test. Playwright: 150
  passed.

## Examined without a defect

- MCP protocol layer under 1 500 random sessions (besides B01): every request was answered, and
  ids, batches, notifications and cancellations behaved as specified.
- Parsers of outside input: chain specs, handoff rules, run logs and resource limits raised only
  `NfclawError`; the exact-number JSON layer round-tripped every generated value, and parameter
  coercion kept every integer and decimal exactly through to the parameters file Nextflow reads.
- The mypy and extended-ruff findings were reviewed one by one: the type findings come from
  dynamically shaped records and reused names, the implicit string concatenations are continued
  prose, and the unused `timeout_seconds` arguments are read by the `budget.bounded` decorator.
- The site's links and anchors (118 pages), the docs' commands, flags, MCP tools and environment
  variables, and the package data a built wheel needs.
- The shared `<repo>/work/` task directory, seen in the chain run, is the documented default.
- The other documented demo chains: no downstream test profile there supplies references the
  handoff leaves in place (differentialabundance's sets none; taxprofiler's databases are the
  ones the chains document).
- `zizmor`'s remaining 22 low findings suggest a different spelling for local action paths; the
  current `./.github/actions/…` form is the documented one.

## Left to the maintainers

- Committing this change and opening its pull request.
