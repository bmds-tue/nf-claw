# Cleanup audit, 2026-10-30

Audited: `bcc40d5`, `main` after the [exhaustive audit](2026-10-30-exhaustive-audit.md) (#227,
C01–C09) and the website's Next 16 update (#223). This audit began on `6576243` (the [deep
audit](2026-10-29-deep-audit.md), B01–B16) while those were open, was carried onto `main`, and was
published on `67f2975` (#228, the native gate's budget; #224, `@types/node`; #226, pinned demo
sheets; #221, D10's fix; #229, a review's hardening; #233, the gate helpers' interpreter; #236,
changelog; #222, `lucide-react`); its findings are numbered D01–D10 so they cannot be confused with
the other record of the same day. Server: `denbi_instance`, Python 3.12.3, Nextflow 26.04.3, Docker,
every pipeline submodule initialised. Local: macOS, Python 3.13.

The audits before this one looked for defects. This one looked for what a cleanup removes or
consolidates (unused, test-only, duplicated, deprecated or stale code, data, files and
documentation) and used tools aimed at each:

- **Unused code.** `vulture` and a reference count of every top-level function, class, method and
  constant of `runner`, `librarian` and `scripts`, separating production callers from test callers;
  every defaulted parameter checked against every call site; `knip` on the website (files, exports,
  dependencies).
- **Duplicated code.** pylint's similarity checker over the production modules (5 lines or more)
  and the tests (8 or more); the workflows compared job by job.
- **Dependencies.** `deptry` for the Python package; `knip` for the website; the runtime of every
  pinned GitHub Action, and the warnings and failures of the last CI and maintenance runs.
- **Files and data.** Every test fixture, script, handoff rule, image and audit evidence file traced
  to what reads it; every entry of the role, contract and acceptance-exception tables checked
  against the library and its pins.
- **Stale text.** Every code name in a comment or docstring of the production code, and every
  repository path and relative link in the hand-written documentation, resolved.

Each defect was reproduced (D01 and D02 on a real run's directory on the server, D10 in the
browser there), and D01's and D02's tests fail without their fixes. The
cleanups keep every message and behaviour and are covered by the existing tests.

## Checklist

| ID | Kind | Finding | Disposition |
|---|---|---|---|
| D01 | Defect | A `--resume` that archives the previous run builds the new run directory with `mkdtemp` and renames it into place, so it was always `0700`. On the server, a demo run resumed with one sample removed was left `0700` beside its `0775` archive, and another account could no longer list it; the deep audit's chain resume shows the same (`02-rnaseq` `drwx------`). Every resumed run's results became private to the user who resumed it. | The new directory takes the permissions of the run it replaces. A test resumes a `0751` run and requires `0751`; it got `0700` before. |
| D02 | Defect | Every provenance bundle file was written through `tempfile` and so was `0600`, except `commands.sh` (`0755`, a test requires it executable for all) and the files written beside them without `tempfile`, such as `params.json` (`0664`): 16 of the 18 files of a real demo run's bundle on the server. Another account (`nobody`) got `Permission denied` opening `replay_guard.py`, the first thing `commands.sh` runs, and the manifest, although the run directory around them was `0775`. | Bundle files are created as any new file is (`0666` less the umask), like the rest of the run directory; the pipeline archive too (`replay_guard`, which must stay standard-library only, does the same inline). Files nfclaw keeps private on purpose (chain records, job and DRAMP files) keep their explicit modes. The run log's seek index, which #229 added while this audit ran with the same `tempfile` pattern, is created the same way: `replay_guard`'s two writers share one helper, and a test requires the index as readable as the log (it got `0600` for `0644`). A test writes a bundle under umask `022` and requires `0644` for every file but `commands.sh`; it got `0600` before. |
| D03 | Duplication | Four modules replaced a file atomically, each its own way: `provenance` (a unique temporary file, removed on failure), `chain` (a fixed `.tmp` name, left behind on failure), `jobs` (a per-process name, left behind) and `sheetgen` (a fixed name, left behind). `librarian.discover_pipelines` imported the private `provenance._atomic_bytes`. | One module, `runner.atomic`: a unique temporary created exclusively, removed on any failure, an explicit mode set before the rename (a private file is never readable on the way). Every caller uses it, including the updater's rollback that #229 added. Tests cover the default and explicit modes, failure and a taken temporary name. |
| D04 | Duplication | `chain._lock` repeated `locking.output_writer`'s lock: open, non-blocking `flock`, the busy refusal, the environment error, the release (pylint, 3 blocks); since #227 each also refused a Python without `fcntl` on its own. | `locking.exclusive` holds the lock and that refusal for both; each keeps its own file, mode, directory and messages. |
| D05 | Unused code | `provenance.output_checksums` had no production caller: 14 test call sites used it to check what `outputs.snapshot` records. `schema.Column.is_path` was only read by two tests, and its docstring described a rule the runner does not apply (production decides by `path_format()`, which also covers globs). `discover_pipelines.fetch_catalog` took a `url` no caller passed, beside a comment saying the URL is fixed. | The checksum helper moved to the tests (`tests/result_checksums.py`); `is_path` is removed and its tests assert `path_format()`; `fetch_catalog` reads the fixed nf-core URL. |
| D06 | Test gap | Since the rnasplice 2.0.0 bump, the role audit of its 1.0.4 schema (still applied when 1.0.4 is run with `--pipeline-version`) was never checked: the test skipped any audit whose commit is no longer the pin. It was the suite's only skip on a complete checkout. | The test reads the audited schema and sources from the submodule's history and checks them as before; it skips only where that history is absent. rnasplice also left the list of pinned schemas whose read columns are legacy: 2.0.0 declares them `file-path`. |
| D07 | Documentation | CONTRIBUTING asked contributors to check `tests/pytest` and `drift-check/drift`; pull requests also run the website and Nextflow-integration jobs, CodeQL, and path-triggered native validations. The maintenance policy's link to the artifact-ID download contract still named download-artifact v6 after #225 pinned v8.0.2. | CONTRIBUTING names every check a pull request runs and when; the link follows the pin. |
| D08 | Unused code (website) | `knip`: the data layer re-exported `allParameters`, `getTags` and the `Quickstart` type, which nothing imports from it (types are imported from their own module), and six module-internal helpers were exported. | Removed from the barrel and unexported. `splitRow` stays exported: `tests/test_website_parsing.py` loads `markdown.ts` and calls it, which `knip` cannot see. |
| D09 | Duplication (workflows) | `auto-update.yml` and `discover-pipelines.yml` repeated their `validate`, `native`, `drift` and `publish` jobs, about 95 lines each, identical but for the candidate's kind. A change to the gate or the publisher had to be made twice, in the two workflows that hold a write token. | One reusable workflow, `maintenance-gate.yml`, holds them; each bot passes its frozen candidate and kind. Every gate job stays read-only, and only the publisher uses the write permissions the callers grant. The tests follow each bot's publish step into the shared workflow. A workflow test that repeated the every-workflow checkout check for two of them is removed. |
| D10 | Defect (website) | A click on the search button just as a page hydrated could be lost. The button works as soon as React hydrates it, but the palette registered its listener in a passive effect, which React runs after that; an open asked for in between went to nobody. The palette's "navigation closes it" effect also ran on the first render, so it would have undone such an open. Under load on the server, the browser test that opens the palette and checks it with axe failed 31 of 360 runs and failed both complete browser runs; a probe showed the open event sent and the palette never rendered. | #221, merged while this audit ran, made the same change, found independently: the palette listens from the commit (a layout effect) and closes only when the path changes. It also waits for hydration in the browser checks, so this change left both to it. Applied here for the measurement, the change brought the same 360 runs at the same load to none failed. A click before the page has hydrated at all still does nothing, as on any page (below). |

## Evidence

Server `denbi_instance` (Python 3.12.3, Node 22, Nextflow 26.04.3, Docker, every submodule
initialised, the `dev`, `yaml` and `scientific` extras and the website dependencies installed). The
baseline is a clean checkout of `bcc40d5`, and the change a clean checkout of its first two commits
on it (`784342e`), run side by side. After the move onto `4d09382`, every gate ran again on the
change's code commits there, which by then included D08's last re-export and D10's change (since
left to #221). #226, merged after that, changes none of the files this change does. This record and
the changelog were written afterwards; no gate reads them. Reports are kept on the server in
`~/volume/nfclaw-c3-evidence/` (`m-base-*`, `m-change-*`, `r-*`, `e2e-m-*`, `palette-*`).

| Gate | Baseline `bcc40d5` | Change on `bcc40d5` | Change on `4d09382` |
|---|---|---|---|
| `pytest` (complete suite, JUnit) | 3498 passed, 4 skipped | 3507 passed, none skipped | 3507 passed, none skipped |
| `ruff check .` | clean | clean | clean |
| `python -m librarian.check_drift` | no drift | no drift | no drift |
| Website `npm audit`, typecheck, export, served `llms.txt` | — | 0 vulnerabilities; pass; identical | 0 vulnerabilities; pass; identical |
| `knip` on the website | — | only what is kept on purpose (below) | the same |
| `actionlint` on every workflow | — | clean | clean |

One of the baseline's skips is D06's; with the change, that test checks the rnasplice 1.0.4
audit from the submodule's history and passes. The other three are the website parser tests,
which need the website dependencies that the baseline checkout did not install; with them
installed, the change's runs executed them. No run printed a warning. The new tests for D01 and
D02 were also run against the unchanged code of `bcc40d5` and failed there (`0700` for `0751`;
`0600` for `0644`).

The browser suite (131 accessibility and 24 operational checks in Chromium) ran on a port of its
own, since other sessions ran theirs on the same server. Without D10's change it failed twice: the
palette check both times, and two and three page loads that the server's Docker network churn
aborted (`net::ERR_NETWORK_CHANGED`, which the deep audit also met). D10 was found that way: the
palette check alone, 3 × 120 runs on 20 workers, failed 31 times. With D10's change the same 360
runs passed, and the complete suite passed twice (155 of 155). On `4d09382` it passed 154 and 150 of
155: every failure was such an aborted page load, and the palette check passed both times. Under a
heavier load still (50 to 65, with 20 to 24 workers), the palette check failed again, 39 times in
360. A probe showed those clicks landing before the page had hydrated at all: the button still
showed its server-rendered `⌘K` label and dispatched nothing. No page can answer a click before its
script runs, and every browser check that clicks right after loading a page is exposed to it at such
a load; GitHub's runners did not come near it. #221 made those checks wait for hydration: on `main`
with it (`78d9cdb`), the complete suite passed twice (157 of 157) and the palette check 600 of 600
runs on 20 and 24 workers, at a load that rose to 43.

After the move onto `ca0d6e5` (#221, #229) and the two adaptations to #229, every gate ran once more
there: 3607 passed, none skipped; `ruff`, drift, the website's dependency audit, typecheck, export
and `llms.txt` as above; and the demo runs below gave the change's column again, with the run log's
seek index `664` beside its `664` log. #233, #236 and #222, merged after that, share only the
changelog, `compatibility.md` and `test_maintenance_publish.py` with this change, and merge with it
cleanly.

Real runs (`--nxf-env NXF_JVM_ARGS=-Djava.net.preferIPv6Addresses=true`, umask `0002`): nf-core/demo
1.2.0 on two local paired-end samples, then `--resume` with one sample removed, which archives the
first run; between them, the `nobody` account reads the bundle as a replay does first.

| | Baseline `bcc40d5` | With this change |
|---|---|---|
| Both runs | success | success |
| Bundle files after the first run | 16 `600`, 1 `664`, `commands.sh` `755` | 17 `664`, `commands.sh` `755` |
| `nobody`: `python3 provenance/replay_guard.py provenance` | `Permission denied` (exit 2) | bundle verified (exit 0) |
| `nobody`: read `run_manifest.json` | `Permission denied` | read |
| Run directory after the archiving resume (its archive) | `700` (`775`) | `775` (`775`) |
| `nobody`: list the resumed run | `Permission denied` | listed |

The `bamtofastq → rnaseq` chain of [validation.md](../validation.md), on the changed code: both
stages succeeded and `nfclaw chain status` verified the lineage (with rnaseq's strandedness caveat
for this test data). The chain record kept its private modes (`chain/` `700`, `state.json` `600`,
`.lock` `644`), the stage directories are `775`, 36 of the 38 files of the two bundles are `664` and
the two `commands.sh` `755`, and no temporary file was left behind.

GitHub: the daily update, dispatched from this change's branch before the move
([41081762848](https://github.com/bmds-tue/nf-claw/actions/runs/41081762848)), ran D09's shared gate
on a real candidate (the ampliseq 3.1.0, variantbenchmarking and bacmodel bumps). `gate / drift`,
`gate / native / execute` for all three pipelines, `gate / validate / website`,
`nextflow-integration` and seven of the ten pytest lanes passed. The last three macOS lanes were
still queued behind about forty macOS jobs of other pull requests three hours later, and the run
was cancelled to free the maintenance concurrency group for the next run on `main`, so its
publisher, which defers on a branch, did not run. The publisher's script is unchanged, and
`tests/test_maintenance_publish.py` runs it as each bot's call of the shared workflow defines it.

Local (macOS, Python 3.13, no submodules): 3227 passed, 226 skipped (pinned sources this clone
lacks), none failed; on `ca0d6e5`, 3314 passed, 239 skipped, none failed.

## Examined without a change

- **Production code reached only by tests:** besides D05, none. The `_tool_*` methods are the MCP
  tools, dispatched by name; their unused `ctx` keeps one signature for every tool. The unused
  `timeout_seconds` arguments are read by `budget.bounded`, and `remove_task_containers`'s
  `timeout` (#227) names the bound it reports.
- **Duplication:** besides D04 and D09, no block of five or more lines repeats in the production
  modules, and none of eight or more in the tests. The other locks differ in kind: the submodule
  lock waits within a budget, the source-correction lock checks its file's identity, the replay
  lock is held across `exec` by the standalone guard.
- **Dependencies:** no unused or missing Python dependency (`pytest`, `mcp` and `ruff` are test
  tools); every npm dependency is used (`axe-core` is loaded by path in the accessibility spec,
  and `postcss-load-config`, which `knip` calls unlisted, is only the JSDoc type of
  `postcss.config.mjs`). The twelve exported website types that only their own module uses are the
  parameter and result types of exported functions and interfaces, kept so callers can name them.
  The artifact actions' Node.js 20 deprecation, which put a warning on 26 jobs of the last CI run
  on `6576243`, was fixed on `main` by #225 with the pins this audit had chosen; every pinned action
  now targets Node.js 24.
- **Files:** every fixture, script, handoff rule and image is read by something; 166 of the 168
  audit evidence files of the earlier records are linked from them, and the other two are the
  scripts that exported that evidence.
- **Data tables:** every input-role, path-role and parameter-role audit, output contract and
  acceptance exception names a library pipeline; the five exceptions match the current pins; the
  one audit of a superseded pin is D06's, kept for the release it describes.
- **Comments and documentation:** every code name in a production comment or docstring exists (the
  five that do not are upstream column and parameter names); every repository path and relative
  link in the hand-written documentation resolves (the rest name files of upstream pipelines).
- **Compatibility code:** the "legacy" branches read chain records, handoff records and MCP
  clients from earlier versions, which still exist.
- **Static checks:** the extended ruff families (simplification, performance, unused arguments,
  commented-out code) found style preferences only; `shellcheck` at style level is clean on every
  script.
- **The native gate's budget:** this audit also found every daily update failing from
  2026-10-29 (runs [40868830529](https://github.com/bmds-tue/nf-claw/actions/runs/40868830529) and
  [41050436747](https://github.com/bmds-tue/nf-claw/actions/runs/41050436747)): the gate runs each
  bumped pipeline's demo at 2 CPUs and 6 GB, and ampliseq 3.1.0's had completed 100 of its 102
  tasks when the 30-minute budget stopped it. #228 raised the budget to 90 minutes while this
  audit ran, and this change keeps it. In the run of the daily update from this change's branch
  (below), with a 60-minute budget at the time, that demo completed in 33 minutes.
- **Website palette:** six shades of the brand scale are unused; a colour scale is kept whole.
