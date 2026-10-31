# Full audit, 2026-10-31

Audited: `7141afe` (`main` after #245). Its findings are numbered E01–E14, after the A, B, C and D
series of the earlier records ([2026-10-28](2026-10-28-repository-audit.md),
[2026-10-29](2026-10-29-deep-audit.md), [2026-10-30 exhaustive](2026-10-30-exhaustive-audit.md),
[2026-10-30 cleanup](2026-10-30-cleanup-audit.md)). Server: `denbi_instance`, Python 3.12.3,
Nextflow 26.04.3 (build 12259), OpenJDK 17.0.20.1, Docker 29.1.3, every pipeline submodule
initialised. Local: macOS, Python 3.13.13 (and the system Python 3.9.6 for E10), Node 22.

The earlier audits read every module and fuzzed the parsers. This one read the runner, the
librarian, the scripts, the workflows and the guides again, with the static gates beside it (ruff
with an extended rule set, pyright, zizmor, actionlint, shellcheck, an internal link and anchor
check of every guide), and then tested what the code *assumes about Nextflow* against Nextflow
itself:

- **Nextflow's own parsers.** Every memory and duration spelling `--limit-memory`/`--limit-time`
  accepts was passed to `nextflow.util.MemoryUnit` and `nextflow.util.Duration` inside a workflow on
  the server, and one refused value was given to a real run as its `resourceLimits` (E01).
- **The current engine against the pins.** `nfclaw chain run --check` for all 19 handoff edges, and
  a plain `nfclaw run` of a pin the chain probe refused (E02).
- **The newest interfaces on real runs.** MCP through the official SDK client and `nfclaw jobs`
  from a shell against the same jobs (E03, E08), including a refused submission and a cancellation.

Each finding was reproduced before it was fixed; each fix has a test that fails without it.

## Checklist

| ID | Severity | Location | Finding | Disposition |
|---|---|---|---|---|
| E01 | Medium | `runner/resources.py` (`_MEMORY_RE`, `_TIME_RE`) | `--limit-memory`, `--limit-time` and a chain's `limits` accepted spellings Nextflow refuses, though the code promised that "a value nfclaw accepts is a value Nextflow can parse". Measured on 26.04.3: `1.5.TB`/`0.5.GB` ("multiple points"), `100.B` (bytes must be whole), `15.gb`/`15 gb`/`15.Gb` (the `B` must be upper case), `15 . GB`; `5.secs`, `5.mins`, `1.H`, `5.MIN`, `1.Day`, `1 . h`, `1.5.h`; and digits of other scripts (Python's `\d`). The existing test asserted `1.5.TB` and `100.B` as valid. A run whose generated `resourceLimits` held `memory: '1.5.GB'` passed `--check` and died at its first task: `Error executing process > 'HELLO' … Caused by: multiple points` — in a chain, after every stage before it. | The two patterns follow the measured grammar: one decimal point at most, a unit letter in either case before an upper-case `B`, whole bytes, Duration's own lower-case unit names, a dot separator only after a whole number, ASCII digits. Tests list the spellings Nextflow accepts and the ones it refuses, each measured. |
| E02 | Medium | `runner/execution.py` (`_failure`), `runner/chain.py` (`_probe_config`), `docs/known-issues.md` | Nextflow 26.04 made its strict syntax parser the default. A pinned release written for the legacy one (methylseq 4.2.0: `Invalid include source: conf/aws/batch/nextflow.config`, a profile file missing at its tag; atacseq 2.1.2; viralrecon 3.0.0) passes `nfclaw run --check`, which defers profile configuration, then fails at launch with the fix "re-run the same command with --resume", which cannot get past a configuration that does not compile. Chains refused the same edges up front, naming only the declared engine. | The failure now names the fix that works: the legacy parser (`--nxf-env NXF_SYNTAX_PARSER=v1`) or an engine that defaults to it (`--nxf-ver 25.10.4`), and does not offer `--resume`. It does so only when the engine's banner is 26.04 or later, the legacy parser is not already selected, and no rejected file is one of the run's own `-c` configs (Nextflow names a failing file by its basename; the caller's own config is theirs to fix). The chain probe adds the same option, and known-issues records it with methylseq. Verified: `nextflow config` parses methylseq with either remedy; with `NXF_SYNTAX_PARSER=v1` a real methylseq demo launched and completed tasks on 26.04.3; the four chain edges refused on 26.04.3 (demultiplex → atacseq/methylseq, fetchngs → atacseq/viralrecon) pass `--check` with the stage's `"nxf_env": {"NXF_SYNTAX_PARSER": "v1"}`. |
| E03 | Medium | `runner/jobs.py` (`_freeze_run_status`), `runner/job_reports.py` (`next_step`) | Every MCP or `nfclaw jobs` job whose command never opened its run log — the most common failure, a run refused before launch into a fresh `--outdir` (an invalid parameter, a missing samplesheet) — recorded `status_error: could not freeze this job's run status: FileNotFoundError: … run.log`, and `get_job`/`nfclaw jobs status` printed it beside the real refusal as if nfclaw had broken. The next step then said to read a `status_report` the job does not have. Reproduced through the MCP tools with a missing samplesheet. | A missing run log is nothing launched: nothing is frozen and no error is recorded. The next step names only the output for a job without a report. Through the official SDK client on the server, the refused job reports `status_error: null` and points at `output_tail`. |
| E04 | Low | `runner/mcp_tools.py` (`_grep`) | `show_pipeline(grep=…)` read every `#` line as a section heading, also inside a code block. Every one of the 95 `skill.md` files shows its command in a bash block with a `# raw equivalent …` comment: it could never be found, and it relabelled the lines after it. | Code fences are tracked, as `read_doc`'s section search already does. |
| E05 | Low | `librarian/update_pipelines.py`, `runner/versions.py` (`remote_tags`) | Tag names were taken after the last `/` of `git ls-remote` output, so a tag `release/9.9.9` read as the release `9.9.9`; the update bot (and `--pipeline-version`) would then fetch a `refs/tags/9.9.9` that does not exist. | Tags are read whole after `refs/tags/`; a slashed tag is not a release. |
| E06 | Low | `runner/resources.py` (`_NXF_VERSION_RE`), `runner/jobs.py` (`_ID`) | `--nxf-ver ٢٥.١٠.٤` was accepted and exported as `NXF_VER` (Python's `\d`), which the launcher cannot download; the job-id pattern had the same gap. | ASCII digits. |
| E07 | Low | `runner/jobs.py` (`state_dir`) | A relative `XDG_STATE_HOME` or `NFCLAW_STATE_DIR` meant a different job store for each working directory, so `nfclaw jobs` in another shell could not see the server's jobs; the XDG specification says to ignore a relative `XDG_STATE_HOME`. | The store is always absolute: a relative `XDG_STATE_HOME` is ignored, a relative `NFCLAW_STATE_DIR` is resolved where it is read. `docs/mcp.md` says so. |
| E08 | Low | `runner/job_reports.py` (`render`, `next_step`), `runner/cli.py` | `nfclaw jobs status` printed MCP tool names and fields to a shell user (`run_status(outdir) reads the live log`, `status_report says …`), and adapted the rest by string replacement. | Shell and MCP wording are produced by `next_step`/`render` themselves (`nfclaw status <outdir>`, `--resume`, `--check`, `nfclaw verify`); a test refuses MCP names in shell output. |
| E09 | Low | `tests/test_audit_fixes.py`, `tests/test_workflows.py` | Five tests ran `scripts/nextflow_accept.sh` with the host's bare `python3`. On a machine whose `python3` is older than 3.11 (macOS's 3.9) they failed on the gate's own interpreter check instead of what they test; `tests/test_nextflow_accept.py` already passes the test's interpreter. | They pass `PYTHON` too. |
| E10 | Low | `docs/replay.md` | "Replay requires Python 3": a bundle's guard scripts run on the replay host's `python3` and use `Path.is_relative_to` (3.9). Verified that they run on 3.9.6 (three replay tests with a logging `python3` wrapper: 24 invocations, all passed). | The guide states Python 3.9 or newer; a test parses both bundled scripts with Python 3.9's grammar. |
| E11 | Low | `runner/mcp_tools.py` | The `job_id` and `get_job` descriptions named run_pipeline and run_chain as the only job sources, omitting `replay_run`. | Named. |
| E12 | Low | `runner/mcp_server.py` | The module docstring was wrapped mid-sentence. | Rewrapped. |
| E13 | Low | `runner/nextflow_command.py` | Three blank lines between two functions and one between the next two. | Two. |
| E14 | Low | `tests/test_orchestration.py` | The three `--pipeline-version dev` tests fetch from a git remote and add a worktree inside a 10-second run budget. With this Mac loaded (a Playwright run and a site build beside the suite) one timed out in `git ls-remote` (`TimeoutExpired` after 9.96 s); alone it took 7.5 s. The budget is a hang bound there, not what the test checks. | `DEV_GIT_TIMEOUT = 300`, documented as a hang bound, as #242 did for the Nextflow integration tests. |

## Evidence

| Gate | Result |
|---|---|
| `pytest`, complete suite, server, `main` (`7141afe`) | 3785 run, 0 failed, 0 errors, 7 skipped (no h5py/pysam/website dependencies in that environment; two audited-commit fixtures whose history the depth-1 clone lacks) |
| `pytest`, complete suite, server, this change (scientific extras and website dependencies installed) | 3898 run, 0 failed, 0 errors, 2 skipped (the two audited-commit fixtures) |
| `pytest`, macOS, Python 3.13, no submodules (`main`) | 5 failures, all E09 (the host's `python3` is 3.9) |
| `pytest`, macOS, Python 3.13, no submodules (this change) | 3606 passed, 235 skipped, 1 failed: E14's timeout under load, which passed when rerun and is fixed |
| `ruff check .` (configured rules), `check_drift`, actionlint, shellcheck | clean; zizmor reports only its pedantic `self-repository` notes |
| Website: `npm audit`, typecheck, static export, served `llms.txt`, Playwright | 0 vulnerabilities; typecheck and export pass; `llms.txt` identical; 159 passed, on `main` and on this change (local) |

Real executions on the server with this change:

- **demo 1.2.0** with `--limit-cpus 2 --limit-memory "1.5 GB" --limit-time 1.h`: succeeded (the
  generated `resourceLimits` holds the three values); `commands.sh` replay succeeded; `nfclaw
  verify`: 42 identical, 34 changed (timestamped reports), 0 missing, 0 extra, 1 renamed, execution
  environment identical; `--strict` exits 1 on those report bytes and `--require-environment`
  refuses the test profile's remote samplesheet, both as documented. `--check` with `1.5.TB`,
  `100.B`, `15.gb`, `5.mins`, `1.H` or `1.5.h` refused each and left `--outdir` absent.
- **MCP, official SDK client (mcp 2.3.0) against `nfclaw mcp`**: a submission with a missing
  samplesheet failed with `status_error: null`; `limit_memory: "1.5.TB"` refused;
  `show_pipeline(grep="raw equivalent")` found the line; a real demo job succeeded and
  `nfclaw jobs status --json` returned the same view as `get_job` (apart from its wording);
  `read_artifact` truncated a preview and refused `..`; `replay_run` and `verify_replay` passed; a
  launched demo job with 6 task containers was cancelled with `cancel_job`: `cancelled`,
  `terminated by SIGTERM`, 0 containers left, and the shell's next step says `--resume`.
- **Chains**: `nfclaw chain run --check` for all 19 handoff edges — 15 passed, 4 refused up front on
  Nextflow 26.04.3's strict parser (E02), which pass with the legacy parser; none wrote into its
  `--outdir`. demultiplex → seqinspector for real: SIGTERM during stage 2 (`terminated by SIGTERM
  (stage 02-seqinspector)`, no task container left), `--resume` completed it, and `nfclaw chain
  status --json` exited 0 with lineage verified and no problems.
- **Stops**: `kill -9` of nfclaw during a demo run: Nextflow stopped 4 s later (the death signal),
  `nfclaw status` reported `stopped without an outcome`, no task container was left, and `--resume`
  succeeded with 12 cached tasks. methylseq 4.2.0 with `NXF_SYNTAX_PARSER=v1`, stopped by SIGTERM
  after its first task: `terminated by SIGTERM`, nfclaw removed the task container left behind.
- **Samplesheet generation**: `--input <directory>` holding `ctrlA_R1/_R2.fastq.gz` and Illumina
  `treatB_S3_L001_R1_001/_R2_001.fastq.gz` generated two paired rows; the run, its replay and
  `verify --require-environment` (all inputs local) passed with an identical environment.

## Examined without a defect

- CLI argument handling (`_collect_overrides`, reserved option names, the `-c…` guard), every
  `nfclaw` flag the guides name, and every pipeline parameter they name against that pipeline's
  `reference.md`.
- The MCP server's dispatch, cancellation and deferred results; `read_artifact`'s path handling.
- Scalar coercion of CLI values: `--x 1_000` or other scripts' digits become the number meant, which
  `params.json` records and the replay reuses — more lenient than Nextflow, never a different value.
- The remote URLs `environment_record.fetch_digest` refetches are limited to http(s)/ftp ones nf-schema
  read; `institutional.pin` queries a fixed repository.
- pyright's "possibly unbound" findings (control flow it cannot follow), ruff's extended rules
  (deliberate broad handlers on cleanup paths, continued prose), zizmor's `self-repository` notes.

## Round 2 (after #246)

Audited: `45df56a` (`main` after #246). The first round left three things open: `run --check` did
not parse configuration, nothing reported which pins the newest Nextflow refuses, and parts of the
tree had been examined only through the static gates. This round read the rest line by line — the
samplesheet generator, handoffs, the skill writer, the replay guard and environment record,
provenance, source corrections, the fastqrepair correction, demo defaults, the scientific
assessors, versions, run logs, every script and workflow, and the website's data layer, renderers
and links — and ran the complete suite with Python's resource warnings as errors
(`-X dev -W error::ResourceWarning -W error::pytest.PytestUnraisableExceptionWarning`), which the
ordinary run does not.

| ID | Severity | Location | Finding | Disposition |
|---|---|---|---|---|
| E17 | Medium | `runner/orchestration.py`, new `runner/config_probe.py`, `runner/cli.py` | `nfclaw run --check` (and MCP `run_pipeline(check=true)`) passed a pin that the engine it would run cannot parse — 25 of the 95 pins on Nextflow 26.04.3 — which then failed at launch (E02's remaining gap). Only a chain probed configuration. | `--check` asks the run's engine to resolve exactly what the printed command loads: the source it runs (corrected, where a release needs it), its profile and every `-c`, generated ones included, under its `NXF_*` overlay. A refusal names the declared engine and the legacy parser; nothing staged for it is left behind; `profile_config` is reported `checked`. The probe is one module shared with the chain's. |
| E18 | Medium | `.github/workflows/smoke.yml` | The smoke check ran every pin's `--check --demo` on the launcher's default engine and judged no configuration; with E17 it would have failed on the 25 pins that need their declared engine, while the newest engine's refusals were reported nowhere (the gate judges declared engines only, by design). | Each pin is checked, and gated, on the engine its `skill.md` advises; beside it the summary reports, without failing, whether the default engine accepts it without `--nxf-ver`. |
| E19 | Low | `runner/container_watch.py` (`_read`), `runner/replay_guard.py` (`run_replay_command`) | The `docker events` pipe of every run, and a replay supervisor's console pipe, were never closed (`ResourceWarning: unclosed file`, about 70 test cases under the strict run). | Each reader closes its pipe when the stream ends. A test fails without the fix. |
| E20 | Low | `runner/scientific.py` (`assess`) | `with sqlite3.connect(...)` only commits; the connection stayed open (`unclosed database`, Python 3.13). | `contextlib.closing`. A test fails without the fix. |
| E21 | Low | `website/src/components/ui/inline-markdown.tsx` | Inline Markdown linked any URL scheme. It renders parameter descriptions, upstream schema text that the update bot regenerates; React 19 neutralises `javascript:` but not, for example, `data:`. | Only relative, web and mail targets become links (the protocols react-markdown's default URL transform keeps); a spec covers the helper. |
| E15 | Low | `runner/samplesheet.py` (`value_problems`) | `integer` and `number` cells written with digit separators (`1_000`) passed the check: Python's `int()` takes them, nf-schema's Groovy casts do not, so the sheet failed at launch. | Refused before launch. |
| E16 | Low | `runner/chain.py` (`format_status`) | A chain still running on another host printed its recorded `running` with exit status 1; `nfclaw status` says "unknown here — launched on <host>". | The same wording. |
| E22 | Low | `tests/test_mcp_server.py`, `tests/test_bundle_self_contained.py`, `tests/test_nextflow_integration.py`, `tests/test_cli.py`, `tests/test_provenance.py` | Test harnesses left pipe ends, HTTP server sockets, a child's stderr and an unfinished run log open (68 of the first strict run's failures). | Closed. |
| E23 | Low | `runner/demo_defaults.py`, `scripts/maintenance_candidate.py` (`inventory`) | Four copies of one CSV writer; a gitlink condition tested twice. | One helper; one test. |

Evidence for round 2:

| Gate | Result |
|---|---|
| `pytest`, complete suite, server, this change (scientific extras installed; files byte-identical to the branch) | 3917 run, 0 failed, 0 errors, 5 skipped (the two audited-commit fixtures a depth-1 clone lacks; three website-parsing tests without the website's dependencies, which run locally) |
| `pytest`, complete suite, macOS, Python 3.13, `-X dev -W error::ResourceWarning -W error::pytest.PytestUnraisableExceptionWarning` | before the leak fixes: about 140 failures and errors (E19, E20, E22); with them: 3626 passed, 237 skipped (no submodules locally), 0 failed |
| `ruff check .`, `check_drift` (server, every submodule at its pin), actionlint and shellcheck (`smoke.yml`), internal link and anchor check | clean (the link check's two known false positives: an underscore slug and a regular expression in an earlier record) |
| Website: `npm audit`, typecheck, static export, served `llms.txt`, Playwright | 0 vulnerabilities; pass; identical; 160 passed (the new link spec included) |

- **Smoke, exactly as the workflow runs it** (its step extracted from `smoke.yml` and run on the
  server, 17 minutes): exit 0. All 95 pins pass `--check --demo`, configuration probe included, on
  their advised engine (21.10.3 to 26.04.4); none wrote its `--outdir`. On the default 26.04.3
  without `--nxf-ver`, 70 pass and 25 are refused with "cannot parse its configuration": atacseq,
  bactmap, callingcards, chipseq, circdna, crisprseq, cutandrun, denovotranscript, hgtseq, hic,
  hicar, marsseq, metaboigniter, metapep, methylseq, multiplesequencealign, nanoseq, nascent,
  pangenome, proteinfold, rangeland, readsimulator, reportho, viralintegration, viralrecon.
- **methylseq 4.2.0 `--demo --check`** on 26.04.3: refused in 5 s, quoting `Invalid include
  source: …/conf/aws/batch/nextflow.config` and naming `--nxf-ver 25.04.0` and
  `--nxf-env NXF_SYNTAX_PARSER=v1`; each remedy then passes (6–8 s) with `profile_config` checked.
- **A chain's probe reads the pinned tree; `run --check` reads the corrected one.** They differ only
  for bactmap 1.0.0, whose correction edits `conf/test.config`; `nextflow config` of the pinned tree
  gives the same verdict as the corrected run's probe on both 24.10.5 (parses) and 26.04.3 (refused
  at `nextflow.config:184`).

## Left to the maintainers

- The acceptance gate still judges each pin on its declared engine, deliberately: a release is
  accepted on the engine it was written for. Users of a newer engine get a refusal from `--check`
  (E17) or at launch (E02) that names the remedy, and the smoke summary lists those pins (E18).
- The earlier records' product items (DAG chains, more handoff rules, chain-wide replay packages,
  offline bundles, distribution beyond an editable checkout) remain product decisions.
