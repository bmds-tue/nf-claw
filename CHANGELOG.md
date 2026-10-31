# Changelog

User-visible changes to nf-claw, newest first. nf-claw has no tagged release yet; the draft release
notes for 1.0.0 (2026-10-22) describe the library as it stood then, and this file starts there.
Pipeline releases the maintenance workflows pin, bump or add are recorded in `sources.tsv`, the
generated `skill.md` files and the git history, not here. Audit records, with the evidence behind
each change, are in [`docs/audit/`](docs/audit/).

## Unreleased

### Added

- `nfclaw status --json` and `nfclaw chain status --json` print one machine-readable object (state,
  outcome, times, pids, logs, caveats, recorded error, last output, and the human report) with the
  same exit codes; the MCP `run_status` tool returns it as `run`.
- [`docs/replay.md`](docs/replay.md): what a provenance bundle carries, the replay guard, dependency
  stability, resume of changed local inputs, and what `nfclaw verify` and `nfclaw assess`
  establish.
- The website's search palette finds documentation sections by their headings, not only documents
  by title, and opens the page at the section; below the widest layout, a document opens with a
  folded table of contents.
- `nfclaw --version`, `nfclaw list <keywords>`, run manifests that record which nfclaw ran them, and
  a security policy (`SECURITY.md`) (#218).
- An accessibility check of every website page in the browser tests (#219).
- MCP `read_doc(guide, search)`: an nf-claw guide, or only its sections that hold every word
  searched. Agents checking a warning against `known-issues` (about 120 KB) get its section
  (under 1 KB); the server's instructions now say so.

### Changed

- `AGENTS.md`, which every agent session loads, is half its size (45 KB → 24 KB): it keeps every
  operating instruction and links the guarantees behind them to focused guides.
- Inputs and outputs are hashed several files at once (up to eight threads): one core hashed
  314 MB/s on the validation server, eight threads 7.7× faster on cached data.
- `nfclaw run` and `nfclaw chain run` refuse a Python without POSIX file locks (native Windows)
  instead of running without their writer locks; use WSL 2 there.
- Generated parameter tables write patterns, defaults and allowed values as code spans, so they
  render as the values nf-schema enforces (#219).
- Each CI test lane runs the complete suite on all of its runner's cores (`pytest -n auto
  --dist worksteal`, pytest-xdist in the `dev` extra) and still reports every case; the suite ran
  one test at a time for 16–34 minutes a lane. On the validation server, four workers took 9
  minutes instead of 29.
- A new push to a pull request cancels that pull request's previous, now superseded CI run; it
  had stayed queued for hours behind the macOS runners. Runs for main, schedules, dispatches and
  the maintenance gate are never cancelled.

### Fixed

- A stopped run (Ctrl-C, `kill`, `--timeout`, MCP `cancel_job`) and a stopped replay remove the
  Docker/Podman task containers their processes started. Task wrappers killed while `docker stop`
  waited on a container's PID 1 had left every container behind, exited, and with a shorter shutdown
  grace still running.
- `nfclaw verify` no longer fails every replay of a resumed run: the run metadata that a stopped or
  failed earlier attempt left in the original's `pipeline_info/` is listed as `earlier attempts`
  instead of as missing results.
- `nfclaw verify` pairs the random names `kraken2-build` gives library files when they contain `_`
  (createtaxdb's Kraken2 and Bracken databases): such a replay had been reported as missing them
  (#226).
- The createtaxdb, bamtofastq and funcscan demos stage their sample sheets from immutable
  test-datasets commits, recorded in provenance, instead of the moving branches their test profiles
  validate, so `nfclaw verify --require-environment` accepts their replays (#226).
- On the website, a tap on the menu or on Search right after a page loaded was undone or reached
  no listener, and did nothing (#221).
- Handoffs no longer drop samples silently (bamtofastq → rnaseq single-end files, detaxizer → mag
  single-end sheets), and resuming a chain stage keeps its unchanged handoff and Nextflow cache
  (#218, #219).
- The daily pipeline update gives each changed pipeline's bundled analysis 90 minutes instead of
  30. ampliseq 3.1.0's test, still running at 30 minutes, had failed the update since
  2026-10-29 and held back every other release with it (variantbenchmarking 1.6.0). A release
  that cannot pass the gate can be set to the `hold` policy in `sources.tsv` so that the others
  publish ([maintenance.md](docs/maintenance.md)).
- The acceptance gate and the maintenance publisher run their Python helpers on `$PYTHON` (default
  `python3`, as in the Makefile) and refuse an interpreter older than 3.11 with a message naming
  it. On macOS, whose `python3` is 3.9, every preview had failed with an `ImportError` reported as
  a rejected pipeline. Without GNU `timeout` or `gtimeout`, the gate bounds each preview with the
  bundled `scripts/run_with_timeout.py` instead of refusing to run.
- A params file path given to `parameters.merge` that does not exist is an error, not an empty
  set of parameters (`nfclaw run` already refused it).
- `nfclaw mcp` answers a message nested too deeply to parse instead of stopping (#219).
- `nfclaw chain edges <name>` refuses a pipeline the library lacks (exit 1) instead of printing
  nothing, which read as "no handoff exists"; for a pipeline without rules it says so.
- `nfclaw chain status --json` gives a missing chain the same keys as a found one, with `error` a
  list as in `nfclaw status --json`.
- On Linux, Nextflow is launched without Python code between fork and exec (`preexec_fn`), which
  can deadlock a parent running threads, as nfclaw's container watch does: a single-threaded
  launcher requests the parent-death signal and execs Nextflow in place.
- Stopping a run or replay whose process group has already ended no longer searches or signals
  that group's number, which another process group may hold by then.
- `CITATION.cff` no longer gives 1.0.0 a release date (2026-06-15) that no release had.
- Robustness of `nfclaw status` with unreadable logs and damaged records, the job supervisor and
  the container watcher (#218).

### Since the 1.0.0 draft notes

- #217 Post-merge fixes: palette race, kraken2 verify pairing, sarek 3.11.0 re-audit, docker probe
  limit.
- #216 Audit remediation: verified defect fixes, scientific output contracts (`nfclaw assess`),
  `verify --require-environment`, structured MCP parameters, `replay_run` and `read_artifact`,
  gated maintenance publication.
- #215 Stop repeating checks that Nextflow and nf-core already make.
- #213 fastqrepair: run the recorded corrections under the legacy config parser.
- #212 Remove duplicated files, code and documentation.
- #209, #211 MCP verified end to end in Claude Code, Codex and Antigravity; Antigravity loads every
  tool up front.
- #205 Report runs stubbed by a `--config`; stub-run seqsubmit's test without ENA.
- #203 Review of the whole codebase: three bug fixes, dead code removed, 100-column lint.
- #202 Next.js 15.5.28 for the website (GHSA-2464-fhr4-w9xw, GHSA-p3m5-59mp-jv5r).
- #200, #206, #207 Maintenance publication without organization PR permissions.
- #195 Name the release a failed chain stage ran; correct engine and network notes.
- Pipelines added or validated since: bacmodel, plasmodiumdrugres, provenancereport,
  stableexpression, magmap 1.3.1, rnasplice 2.0.0, rnastructurome 1.1.0, genomeassembler 2.0.1
  (#197, #198, #204, #208, #214).
