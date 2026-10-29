# Repository audit, 2026-10-28

Audited: `9fd2a4c` (main, #216). Applied and verified on `58e8e15` (main after #217, which fixed
A15 independently). Server: `denbi_instance`, Python 3.12.3, Nextflow 26.04.3, Docker, every
pipeline submodule initialised. Local: macOS, Python 3.13.

Scope: every module of the runner (`runner/`, including the MCP server and jobs), the librarian,
the maintenance scripts, every handoff rule (each one's claims about published files checked
against the pinned upstream code and its nf-test snapshots), every website page, component and
data module, the workflows and the agent documentation, read in full. The built website was also
checked with axe-core 4.10.2 at desktop and phone widths. Each finding below was reproduced before
it was fixed, and each fix carries a regression test that fails on the baseline, except where
noted: A23 needs a checkout without submodules (in this audit's local clone all 95 releases are
undated, so the baseline counts 0), and A24's test checks the tiles against the real workflows,
which the baseline also happened to read correctly. The baseline suite and the website gates
(typecheck, production build, `npm audit`, 13 Playwright tests) passed before any change.

## Checklist

| ID | Kind | Finding | Disposition |
|---|---|---|---|
| A01 | Defect | `nfclaw status` and `nfclaw chain status` ended in a `PermissionError` traceback for a log that exists but cannot be read (another user's run). | `runlog.read_state` reports such a log as `unreadable` with the reason; `status` prints `status: unknown — … cannot be read` and exits 1; `chain status` reports the chain as unknown and exits 1. |
| A02 | Defect | A run-log `pid:` header beyond the platform's range (`OverflowError` from `os.kill`) or written with non-ASCII digits (`str.isdigit` accepts `²`, `int()` refuses it) made `nfclaw status` raise. | Header pids are parsed as 1–10 ASCII digits within the pid range; `_is_process` treats an out-of-range pid as no process. A report never prints `pid None`. |
| A03 | Defect | On Python 3.11–3.13, `Path.exists`/`is_file`/`is_dir` raise `PermissionError` under a directory that cannot be searched. `nfclaw run --input /root/x.csv`, `--input /root/dir` and `--outdir /root/out` ended in tracebacks (reproduced on the server). | The CLI reports an inaccessible path as an `[environment]` refusal naming the path, records the refusal in an existing run log, and `status`/`run` probe their log without `Path.is_file`. A write-boundary check that cannot inspect a path still refuses, now with permission advice instead of the overlap advice. |
| A04 | Defect | The chain's final `state.json` write could raise before `log.finish()`, leaving the chain log without its last line: `nfclaw status` then reported a finished chain as stopped without an outcome. | The last line is always written. A success whose state cannot be recorded becomes `failed (the chain state could not be recorded)`; a failure already under way keeps its own error beside the note. |
| A05 | Defect | The job supervisor caught only `OSError`/`ValueError` while freezing a job's status: anything else killed it before it recorded the exit code, and a finished job read as `lost`. | Any exception there is recorded as `status_error`; the exit code is always written. `get_job` shows `status_error` when the frozen report is absent. |
| A06 | Defect | `jobs.load` accepted any positive integer pid, so `cancel_job` could raise `OverflowError` on a damaged record. | Supervisor and child pids must lie within the pid range; damaged records are isolated as other malformed records are. |
| A07 | Defect | The staged-directory digest followed directory symlinks without cycle detection (hashing until the OS refused the path) and `os.walk` silently skipped unlistable subdirectories, recording a digest of part of the directory. | Cycles and unlistable directories leave the remote input `unresolved` with the reason. Digests of ordinary directories are byte-identical to the previous implementation. |
| A08 | Defect | The container-event watcher was never reaped after `SIGKILL`, leaving a zombie per run when the engine ignored `SIGTERM`. | It is waited for after the kill. |
| A09 | Defect | The nf-core/configs lookup ignored `NFCLAW_GIT_TIMEOUT`, which `docs/timeouts.md` documents for remote Git discovery. | It honours the setting (default 30 s, unchanged). |
| A10 | Defect | `scripts/check_nftest_snapshot.py` read each candidate result (and its decompressed `.gz`) into memory whole, counted `.nextflow/` and `.nextflow.log*` files as published results, and raised tracebacks on a malformed snapshot or missing run directory. | Files are hashed in chunks and at most once; Nextflow state is excluded; malformed input exits 2 with an error. |
| A11 | Missing feature | No `nfclaw --version`; the package version alone cannot identify the code because it does not change between commits. | `nfclaw --version` prints the package version and the checkout commit (`runner/version.py`); the MCP server reports the same package version. |
| A12 | Provenance gap | `run_manifest.json` recorded the pipeline's revision but not which nfclaw validated, launched and recorded the run. | The manifest records `nfclaw: {version, commit}`. |
| A13 | Missing feature | The CLI could not search the library; only the MCP `list_pipelines` ranked pipelines by keyword. | `nfclaw list <keywords>` ranks exactly as `list_pipelines` does (shared `discovery.search`); `nfclaw list` alone is unchanged. No match exits 1. |
| A14 | Usability | `nfclaw --help` described three of ten commands; `nfclaw run --help` left `name`, `--outdir`, `--profile`, `--params-file`, `--pipeline-version`, `--check`, `--demo`, `--resume` and `--no-provenance` undescribed and did not say how pipeline parameters are passed. | Every command, chain sub-command and `run` option is described; `run --help` explains pipeline parameters. A test keeps every `run` option described. |
| A15 | Defect | The search palette opens through a custom DOM event, so React defers the effect that re-subscribes its ⌘K/Ctrl+K listener to a later task, while the input takes focus (`autoFocus`) during the commit. A second press in between reached the listener that still saw the palette closed, and the palette stayed open. This is why `holding the search shortcut opens once and a new press closes it` failed once on the server. | Fixed on main in #217 (`a801e94`, found independently): the listener reads the open state from a ref that a layout effect keeps current. This change keeps that fix and adds a browser test that presses the shortcut again in exactly that window; it fails 5/5 on the `9fd2a4c` component and passes on main's. |
| A16 | Defect | `python -m librarian.write_skill NAME` with an unknown or path-like name ended in a `FileNotFoundError` traceback, and a path-like name reached outside `pipelines/`. | The name must be a library pipeline; otherwise the generator exits 1 with `pipeline_not_found`. |
| A17 | Documentation | Agent guidance did not mention keyword search, `--version`, the unreadable-log status, the manifest's nfclaw identity or `status_error`. | AGENTS.md, README.md, llms.txt, docs/architecture.md and docs/mcp.md updated. |
| A18 | Test defect | `test_lookup_obeys_active_budget_and_stops_download_helpers` gave a fake `git` 0.5 s to start its helper before the deadline stopped it, then required that helper's pid: on a busy host the shell had not started yet and the test failed (seen once locally). | The test waits for the helper to exist before the deadline meets it, as the version-probe test already does. With a shell that takes 1 s to start, the original test fails and the corrected one passes. |
| A19 | Defect | Handoffs dropped samples without a word. bamtofastq converts single-end samples beside paired ones in one run (its own `no_bai` nf-test: `test`, `test2` paired, `test3` single-end) and publishes them as `reads/<sample>_other.fq.gz`; `bamtofastq → rnaseq` built rows from the paired files only, so rnaseq never saw `test3`. Its description also named the single-end files wrongly (`<sample>.merged.fastq.gz`). detaxizer writes samples without a second short-read file to `mag-se.csv` beside `mag-pe.csv`; `detaxizer → mag` handed over `mag-pe.csv` alone. | Two rule options: a `build` source's `exhaustive` glob names files that must all reach a row, and a `samplesheet` source's `refuse_rows_in` names sheets whose rows it cannot take. Either fails the handoff (even an optional one), naming the files or samples. Both rules use them and say what single-end runs need; `docs/chaining.md` and the generated `skill.md` files say the same. The other 17 rules hand over outputs that cover the whole run; every rule's paths match the pinned code and its nf-test snapshots. |
| A20 | Defect | Website copy controls showed "Copied" when the Clipboard API refused and the `execCommand` fallback failed too, and a fallback that threw became an unhandled promise rejection. | The control reports "Copy failed" (label, `aria-label`, title) unless a copy succeeded, and returns focus to itself after the fallback's hidden selection. |
| A21 | Defect | The home page rendered its `<h1>`, lead, calls to action, stats, principles and steps at `opacity: 0` in the static HTML; only a script lifted it, so without JavaScript (or when a script chunk failed to load) the page showed almost nothing. | A `<noscript>` style shows entrance-animated content as it ends up; with scripts the animations are unchanged. The no-JavaScript test covers the home page as well as the docs. |
| A22 | Accessibility | axe-core on the built site: a parameter row's toggle `<button>` contained the description's links (`nested-interactive`; following a link also toggled the row); the skills listbox held its "Show all" button and, on small screens, each skill's whole detail (`aria-required-children`), whose headings skipped a level; the samplesheet and comparison tables scrolled sideways with no keyboard access; heading anchor links stayed invisible when focused. | The toggle holds the summary line and the description sits beside it (a click on it still toggles, except on a link or a text selection); the skills rows are a listbox where the detail is beside them and disclosure buttons where it opens under them; the tables are focusable labelled regions; anchors show on focus. axe-core then reports no violation on the home (desktop, phone, skill opened, palette open), pipeline index, pipeline (desktop, phone, every parameter expanded), docs index, two docs and 404 pages. |
| A23 | Defect | The release timeline counted only dated releases as "pinned releases" and every undated one as a "library tag"; release dates come from the submodules, so a checkout without them showed "0 pinned releases". | Releases are counted by kind; only the year span needs dates. |
| A24 | Robustness | The status tiles took the first scheduled workflow by name as the auto-update (correct only because `auto-update` sorts before `CodeQL`) and printed "Enforced on every PR" for any workflow named like drift, without checking that it runs on pull requests ("Configured" when there was none). | The auto-update tile reads `auto-update.yml`; the drift tile states what the drift workflow's triggers support, or "Not configured". |
| A25 | Missing component | No security policy: nothing said how to report a vulnerability privately or what is in scope. | `SECURITY.md` (GitHub private vulnerability reporting, scope, where fixes land), linked from CONTRIBUTING, llms.txt and the website's documentation hub. |
| A26 | Missing component | Nothing kept the SHA-pinned Actions or the website's npm dependencies current between advisories. | `.github/dependabot.yml`: weekly grouped updates for every workflow and composite action and for `website/`; pipelines stay on their validated maintenance route. A test keeps every directory that holds workflows or actions covered. Also removed: an unused `y` prop of the website's `Reveal`. |
| A27 | Defect | `list_pipelines` ranked one query word in a pipeline's name above pipelines matching the whole query, and `nfclaw list` (A13) shares its ranking: the final server run showed `nfclaw list variant calling`, the documented example, putting `callingcards` ahead of every pipeline whose description names variant calling. | Rows holding more of the query's words rank first; the field weights and the exact-name bonus order rows holding as many. Single-word queries rank as before. |

## Evidence

Server `denbi_instance` (Python 3.12.3, every submodule initialised, website dependencies
installed). The baseline column is a clean checkout of `58e8e15`; the other is the same checkout
with this change applied (its diff has SHA-256 `45a409ab3c05…`, recorded before and after the
run; this record's evidence section is the only later change). Reports are kept on the server in
`~/volume/nfclaw-goal-evidence/` (`base58-*`, `final-*`; the patch as `audit-rebased.patch`). The
same gates passed on `9fd2a4c` before main moved (`v3/`).

| Gate | Baseline `58e8e15` | With this change |
|---|---|---|
| `pytest` (complete suite, JUnit) | 3407 run, 0 failed, 0 errors, 1 skipped | 3475 run, 0 failed, 0 errors, 1 skipped |
| `ruff check .` | — | clean |
| `python -m librarian.check_drift` | — | no drift |
| Website `npm audit`, typecheck, export, served `llms.txt` | 122 pages | 0 vulnerabilities; 123 pages (the security policy added); `llms.txt` identical |
| Website Playwright | 13 tests | 22 tests, three consecutive runs, all passing |

The one skip in both is a declared `… is no longer pinned at the audited commit` fixture. The new
handoff tests ran against the real pinned schemas; with the baseline handoff code and rules
restored, the bamtofastq → rnaseq and detaxizer → mag tests fail (`DID NOT RAISE`): the mixed
runs were handed over with samples missing.

Real runs with the changed code (`--nxf-env NXF_JVM_ARGS=-Djava.net.preferIPv6Addresses=true`, which
this host needs and which nfclaw's own failure message names when it is missing):

- `nfclaw --version`: `nfclaw 1.0.0 (commit 58e8e15797b6)`. `nfclaw list variant calling` ranks
  `variantbenchmarking` and `rnavar` first (A27).
- `nfclaw run demo --demo -profile docker`: success; the manifest records `nfclaw` 1.0.0 at
  `58e8e15`; the release's own nf-test snapshot matches (87/87 paths, 20/20 checksums).
- `provenance/commands.sh` replay: success; `nfclaw verify` reports the same files and directories
  (none missing or extra, one launch-time file paired by role) and an identical execution
  environment; the byte-different files are MultiQC reports/plots and Nextflow's dated execution
  reports, and the replay also matches the nf-test snapshot (20/20).
- `--resume` of the finished run: success. `nfclaw status` on an unreadable log: `status: unknown`,
  exit 1. `--input /root/x/sheet.csv` and `--outdir /root/out`: refusals naming the path and the
  permission, exit 1.
- Local (macOS, Python 3.13, no submodules): on `9fd2a4c`, 3410 run with exactly the baseline's 26
  failures, all from the host `python3` 3.9 described below; on `58e8e15`, the affected modules
  pass (536 tests). The website gates, the Playwright suite (22) and an axe-core check of the built
  pages pass.

## Examined without a defect

- Local baseline failures (26) were all the macOS host's `python3` 3.9 being picked up by
  `scripts/nextflow_accept.sh` and `scripts/publish_validated_update.sh`; CI and the server use a
  supported interpreter, where the same tests pass.
- The MCP protocol layer (batches, cancellation, deferred waits), replay guard, provenance writer,
  handoff engine, scientific contracts, DRAMP preparation, source corrections, resume archiving,
  samplesheet validation and parameter coercion: no reproducible defect.
- Website: dependencies audit clean; typecheck and static export (122 pages) pass; the served
  `llms.txt` matches the repository's. The other global listeners (the navigation menu) change
  state from React's own click handlers, whose effects run in the same commit, so they have no
  window like A15's.
- Handoffs, besides A19: `{placeholder}` patterns capture sample names that end like a read
  suffix correctly (`S_1_1.merged.fastq.gz` is sample `S_1`); the remaining rules' sheets
  (fetchngs, demultiplex, createtaxdb, detaxizer for taxprofiler) hold every sample of the run;
  rnaseq's ordered count-matrix list and its paired gene lengths choose one producer step. A glob
  skips an entry it cannot stat, so a deliberately unsearchable directory inside an outdir could
  hide a second match; outdirs are written by the run's own user, so this was left as is.
- Website, besides A20–A24: the data layer (catalog, skill/reference parsers, workflows, git
  history, timeline, link resolution), the constellation layout, the command palette, the doc
  pages and the pipeline page read correctly. Intermittent local Playwright failures during this
  audit came from the Mac sleeping mid-run (power log) and from six parallel browsers
  overflowing the test server's listen backlog; the configured suite runs one worker.
- Generators and maintenance tools (`write_skill`, `write_catalog`, `check_drift`,
  `update_pipelines`, `discover_pipelines`, the snapshot and pytest-evidence checkers): apart from
  A10 and A16, inputs are repository-controlled and checked by the drift and maintenance gates.

## Left to the maintainers

- Committing this change and opening its pull request.
