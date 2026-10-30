# Exhaustive repository audit, 2026-10-30

Audited: `6576243` (the [2026-10-29 deep audit](2026-10-29-deep-audit.md), B01–B16, on the
[2026-10-28 audit](2026-10-28-repository-audit.md), A01–A27). Applied on `main` at `1d637b6` (both
merged, plus the Actions and website dependency updates #225 and #220). Server: `denbi_instance`, Python
3.12.3, Nextflow 26.04.3, Docker 29.1.3, every pipeline submodule initialised. Local: macOS, Python
3.13, Node 22.

The two audits before this one read every module, fuzzed the parsers and crawled the website. This
one went after what neither could see from the code alone:

- **What a stopped run leaves on a real container engine.** A stop is tested with fake processes
  in the suite; here a real Nextflow, a real Docker daemon and task containers whose PID 1 ignores
  SIGTERM (the usual case: bash as PID 1) were stopped through nfclaw's own supervisor, and the
  engine's container list compared before and after (C01).
- **Every pipeline's preparation.** `nfclaw run <name> --demo --check` for all 95 pins, with the
  advisories each printed collected and classified.
- **Cost, measured rather than assumed.** SHA-256 throughput on the server's CPU, against the three
  hashing passes every run makes (C03), and the bytes of agent guidance loaded into every session
  (C05).
- **Platform contracts.** Each place that needs POSIX locking, compared with what it does without
  it (C04).
- **Static analysis beyond the configured gates:** pyright, an extended ruff rule set, vulture,
  zizmor, actionlint, and shellcheck on the scripts and on a real generated `commands.sh`.

Each finding was reproduced before it was fixed; each fix has a test that fails without it.
Three findings duplicated the deep audit, which was opened while this one ran: four workflow
checkouts that persisted credentials (its B06), Dependabot proposing same-day releases (B07) and
the acceptance-gate test that needs the host's GNU `timeout` (B14). This change keeps its fixes and
adds none of its own for them.

## Checklist

| ID | Kind | Finding | Disposition |
|---|---|---|---|
| C01 | Defect | A stopped run left its Docker/Podman task containers behind. On SIGTERM each task wrapper runs `docker stop`, which waits 10 s for a container's PID 1 that ignores SIGTERM, and nfclaw's shutdown grace is also 10 s: the wrappers were killed first, so their own `docker rm` never ran. With the default grace every container stayed behind exited, forever; with a 3 s grace both were still running after nfclaw reported the run stopped (evidence below). The same held for a replay's supervisor, chain stages and MCP `cancel_job`. | Before each signal, nfclaw notes the `nxf-…` containers the run's own process group started (the `docker run`/`podman run` clients' `--name`, read from `/proc`, or `ps` elsewhere); once the group is gone, it force-removes those still present, concurrently, and records it in the run log. Containers of other runs are never touched. The replay supervisor does the same and logs it. With `docker.sudo`, removal runs `sudo -n`, so it cannot hang on a password prompt. |
| C02 | Missing feature | `nfclaw status` and `nfclaw chain status` printed prose only, and the MCP `run_status` reduced every non-success to "not successful". An agent had to parse the report to tell `failed (exit status 1)` from `timed out after 3600 s` or a stop. | `--json` on both prints one object (version 1): state, kind, outcome, times, pids, logs, caveats, recorded error, last output and the report, with the same exit codes. A missing chain record gives `{"error": …}`. `run_status` returns the record as `run`. |
| C03 | Performance | Every run hashes its declared inputs twice (before launch and after) and its outputs once, one file at a time. SHA-256 managed 314 MB/s on one core of the server; 3.2 GB of cached files took 10.2 s. | Input snapshots, output snapshots (and with them `verify`, chain status and handoffs) hash up to eight distinct files at once (`replay_guard.hash_files`): the same 3.2 GB in 1.3 s (7.7×). Digests, deduplication of aliases and the first error in order are unchanged. |
| C04 | Defect | On a Python without `fcntl` (native Windows), `nfclaw run` silently skipped its `--outdir` writer lock and `nfclaw chain run` its chain lock, so two runs could write one directory, while MCP jobs and source corrections already refused there. Nextflow itself runs only on POSIX systems. | Both refuse before writing anything, with an environment error naming WSL 2. `--check` is unchanged. AGENTS.md and compatibility.md state the requirement. |
| C05 | Documentation (cost) | `AGENTS.md`, which `CLAUDE.md` imports and the MCP server serves, so every agent session loads it, had grown from 9.4 KB (2026-10-05) to 44.8 KB (about 11 000 tokens), in a library that describes itself as token-minimal. Most of the growth was guarantee detail: filename rules, bundle contents, replay checks, resume of changed inputs. | AGENTS.md is 23.7 KB. It keeps every operating instruction and states each rule in one line. The detail moved, word for word, to [replay.md](../replay.md) (new), [preflight.md](../preflight.md#inputs-refused-before-launch), [chaining.md](../chaining.md) and [source-corrections.md](../source-corrections.md); README and llms.txt link the new guide. |
| C06 | Missing component | No changelog. The only release notes were the GitHub draft for 1.0.0 (2026-10-22), and 24 pull requests have changed user-visible behaviour since. | [`CHANGELOG.md`](../../CHANGELOG.md) starts at the draft, lists this change, #218 and #219, and the merged pull requests since; CONTRIBUTING asks for an entry per user-visible change; the site and llms.txt link it. |
| C07 | Missing feature | The website's search palette found documents by title only (the 2026-10-26 audit's O12), and a document's table of contents existed only from the `xl` breakpoint (1280 px): tablets and phones had none (O11). | The palette also lists the ## and ### sections whose headings match a query (at most twelve, none until something is typed) and opens the page at that heading. Below `xl` a document opens with the same headings in a folded "On this page" (`<details>`, so it works without JavaScript too). Browser tests search for a section of the replay guide and land on it, and follow the folded contents at phone width. |
| C08 | Defect (latent) | `version.package_version` named `PackageNotFoundError` in an `except` clause whose import was inside the `try`: had the import failed, the handler itself would have raised `NameError` (pyright). | The import precedes the `try`. |
| C09 | Defect | `nfclaw verify` failed every replay of a resumed run. Found by this audit's own server run: rnaseq stopped mid-run (C01's check), resumed into the same `--outdir`, then replayed. The original's `pipeline_info/` held both launches' report, timeline, trace, DAG and params file; the replay, one launch, had one of each, so six files were "missing" and the two `params_<time>.json` against one were deliberately left unpaired. | When the original's recorded command resumed, launch-stamped run metadata older than the newest of its kind is listed as `earlier attempts` and not compared: launches into one `--outdir` run one after another under its lock, so the newest is the recorded launch's. Results are never set apart, and without a recorded resume two such files for one still fail. Re-verified on the same server data: 0 missing, 0 extra, 5 earlier attempts, environment identical. |

## Evidence

Server `denbi_instance`, in a separate clone (`/mnt/volume/claude-audit-20261030`), every submodule
initialised, `--nxf-env NXF_JVM_ARGS=-Djava.net.preferIPv6Addresses=true` as this IPv6-only host
needs. The host was shared with two other sessions' test suites and pipelines throughout (load
average 15–23 at times), which is why Docker operations below take seconds.

| Gate | Result |
|---|---|
| `pytest` (complete suite, server, final head) | 3502 run, 0 failed, 0 errors, 1 skipped (the declared `rnasplice is no longer pinned at the audited commit` fixture) |
| `pytest` (complete suite, macOS, Python 3.13, no submodules) | 3448 run, 0 failed, 0 errors, 227 skipped (pinned sources the clone lacks) |
| `ruff check .`, actionlint, shellcheck | clean |
| Website: `npm audit`, typecheck, export, served `llms.txt` | 0 vulnerabilities; typecheck and export pass (the new `replay` and `changelog` pages included); `llms.txt` identical |
| Website Playwright (operational and accessibility) | 154 passed on the server at the final head and 154 locally. One earlier server run lost one page load to `net::ERR_NETWORK_CHANGED` (Docker network churn from other work on the host, as the deep audit records); that test passed when rerun |
| `nfclaw run <name> --demo --check`, all 95 pipelines | 95 of 95 succeeded |

Real executions with the changed code:

- **C01 reproduction** ([record](evidence/2026-10-30-task-container-cleanup.json)): a two-task
  workflow whose containers' PID 1 ignores SIGTERM, stopped through `runner.execution`. Before the
  fix: with the default grace both containers stayed behind exited, never removed; with a 3 s grace
  both were still running after the supervisor exited. After: none left in any state, with 3 s and
  10 s grace.
- **rnaseq 3.27.0 demo stopped by SIGTERM** while tasks ran: `nfclaw: removed 4 task container(s)
  the stopped run left behind`, none left; `nfclaw status --json` gave `ended` / `terminated by
  SIGTERM` / exit 1. `--resume` succeeded (226 tasks run, 8 cached). The `commands.sh` replay
  succeeded, and `nfclaw verify` reported the same files and directories with an identical execution
  environment once C09 was fixed (before it: 6 missing, 1 extra, from the stopped attempt's run
  metadata).
- **fetchngs 1.13.0 → rnaseq chain** stopped by SIGTERM during stage 2: no task container left;
  the chain log ended `terminated by SIGTERM (stage 02-rnaseq)`; `--resume` completed both stages;
  `nfclaw chain status --json` exited 0 with `success`, lineage `verified`, no problems.
- **MCP**, through the official SDK: a detached rnaseq job cancelled with `cancel_job` while two
  task containers ran ended `cancelled` with no container left, and `run_status` returned the
  parsed record (`ended`, `terminated by SIGTERM`, exit 1).
- **demo 1.2.0**: run, `commands.sh` replay and `nfclaw verify` passed;
  `--require-environment` refused, by design, because its test profile reads a remote samplesheet.
- **C03 benchmark**: eight 400 MB files, page-cached, hashed with the repository's chunked
  SHA-256: 10.2 s one at a time, 3.1 s with four threads, 1.3 s with eight.

## Examined without a defect

- `nfclaw run <name> --demo --check` for all 95 pipelines: every preparation succeeded. The
  advisories they printed were classified: the institutional-config pin (every pipeline), recorded
  corrections and fixtures (bactmap, createtaxdb, funcscan, fastqrepair, hgtseq, tumourevo,
  bamtofastq), stub-run and variability notices (proteinfold, ampliseq), nf-core-utils' positional
  argument warning (three releases) and one release that requires Nextflow 26.04.4, which `--check`
  names. None is a fault.
- `nfclaw verify --require-environment` refuses the demo pipeline's replay because its test
  profile reads a remote samplesheet whose refetched bytes cannot establish what was consumed: the
  documented behaviour.
- pyright's 135 findings were reviewed: apart from C08, they come from dynamically shaped JSON
  records, narrowing it cannot follow, and the MCP server's deferred results. vulture's candidates
  are MCP tools dispatched by name and a checksum helper the tests use. The extended ruff findings
  are continued prose and deliberate broad handlers on cleanup paths.
- actionlint and shellcheck are clean on every workflow and script; shellcheck's two notes on a
  generated `commands.sh` are a function called from a trap and a deliberately single-quoted
  script. zizmor's medium findings are the deep audit's B06 and B07.

## Left to the maintainers

- Publishing 1.0.0. Its draft notes are out of date: 95 pipelines rather than 94, and CI covers
  Python 3.11–3.15 rather than 3.11–3.13.
- The rest of the 2026-10-26 audit's optional items are product decisions this change does not
  make: DAG chains (O01), further handoff rules (O02), a single replay package for a chain (O03),
  CLI job management (O04, beyond C02's `--json`), custom pipeline sources (O05), offline
  bundles (O06), distribution beyond an editable checkout (O07, beyond C06's changelog), browser run
  configuration (O08) and `SKILL.md` export (O10). O09 is C04's policy, O11 and O12 are C07; O13
  and O15 were already in place (canonical and social metadata; no pagination claim remains).
- C01 covers the local Docker and Podman executors. Scheduler jobs (Slurm, cloud batch) and host
  crashes still need the executor's own reconciliation.
