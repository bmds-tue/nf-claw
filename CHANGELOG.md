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
  (under 1 KB); the server's instructions now say so (#234).
- `nfclaw jobs list`, `nfclaw jobs status` and `nfclaw jobs cancel` manage MCP's persisted jobs
  from a shell, with shared reports, bounded output tails and versioned `--json` responses (#238).

### Changed

- `AGENTS.md`, which every agent session loads, is half its size (45 KB → 24 KB): it keeps every
  operating instruction and links the guarantees behind them to focused guides.
- Inputs and outputs are hashed several files at once (up to eight threads): one core hashed
  314 MB/s on the validation server, eight threads 7.7× faster on cached data.
- `nfclaw run` and `nfclaw chain run` refuse a Python without POSIX file locks (native Windows)
  instead of running without their writer locks; use WSL 2 there.
- Both maintenance bots hand their frozen candidate to one shared gate and publisher
  (`maintenance-gate.yml`) instead of repeating its jobs.
- Generated parameter tables write patterns, defaults and allowed values as code spans, so they
  render as the values nf-schema enforces (#219).
- Each CI test lane runs the complete suite on all of its runner's cores (`pytest -n auto
  --dist worksteal`, pytest-xdist in the `dev` extra) and still reports every case; the suite ran
  one test at a time for 16–34 minutes a lane. On the validation server, four workers took 9
  minutes instead of 29 (#234).
- A new push to a pull request cancels that pull request's previous, now superseded CI run; it
  had stayed queued for hours behind the macOS runners. Runs for main, schedules, dispatches and
  the maintenance gate are never cancelled (#234).
- The smoke workflow checks each pin's demo on the engine its `skill.md` advises, which now also
  has that engine parse the configuration, and reports beside it — without failing — which pins
  the launcher's default (newest) Nextflow refuses when no `--nxf-ver` is given.

### Fixed

- Resolve verified current-product audit findings in process cancellation, completion caveats,
  environment attribution/deadlines, scientific validity/reference handoffs, private frozen-stage
  identity, website navigation/guidance/static counts, manifest parsing and MCP/job error handling
  (#247). Evidence and limitations: [follow-through audit](docs/audit/2026-10-31-followthrough-audit.md).

- A run whose pinned release Nextflow 26.04+'s strict parser rejects (methylseq 4.2.0, atacseq 2.1.2,
  viralrecon 3.0.0 among the pins) fails with the fix that works — the legacy parser,
  `--nxf-env NXF_SYNTAX_PARSER=v1`, or `--nxf-ver 25.10.4` — instead of "re-run the same command with
  --resume", which cannot get past a configuration that does not compile; `nfclaw chain run` names
  the legacy parser too (#246).
- `nfclaw run --check` (and MCP `run_pipeline(check=true)`) asks the run's engine to parse the
  release's configuration, as `nfclaw chain run --check` already did for each stage: a pin the
  engine rejects is refused with its remedy before anything launches, instead of passing the check
  and failing at launch; its `preflight` lines report `profile_config` as checked.
- Samplesheet `integer` and `number` cells written with digit separators (`1_000`) are refused
  before launch: the check accepted them, and nf-schema's Groovy casts then rejected the sheet at
  launch.
- `nfclaw chain status` reports a chain still running on another host as unknown here, naming that
  host, as `nfclaw status` does for a run, instead of `running` with exit status 1.
- A run closes the container-events pipe it follows, a replay its console pipe, and `nfclaw assess`
  its record database; Python reported each as an unclosed resource.
- The website renders a link in a parameter description (upstream schema text) only to a relative,
  web or mail target; any other scheme is shown as its label.
- `--limit-memory` and `--limit-time` (and a chain's `limits`) accept only spellings Nextflow parses.
  `1.5.TB`, `100.B`, `15.gb`, `5.secs`, `5.mins` or `1.H` passed the check and the run then died at
  its first task (`Caused by: multiple points`), in a chain after every earlier stage had run (#246).
- A job refused before launch into a fresh `--outdir` (an invalid parameter, a missing samplesheet)
  no longer reports "could not freeze this job's run status: FileNotFoundError" beside the real
  refusal in `get_job` and `nfclaw jobs status`; `nfclaw jobs status` names shell commands
  (`nfclaw status <outdir>`, `--resume`) instead of MCP tools and fields (#246).
- `show_pipeline(grep=…)` reads a `#` comment inside a code block as code: every `skill.md`'s
  `# raw equivalent …` line can be found, and no longer relabels the lines after it (#246).
- Release tags are read whole from `git ls-remote` by `nfclaw versions`, `--pipeline-version` and
  the update bot: a tag such as `release/9.9.9` is no longer mistaken for the release `9.9.9` (#246).
- Job records live in one absolute place: a relative `XDG_STATE_HOME` is ignored, as the XDG
  specification requires, and a relative `NFCLAW_STATE_DIR` is resolved where it is read (#246).
- [`docs/replay.md`](docs/replay.md) states the replay host's real requirement, Python 3.9 or newer
  as `python3`; a test keeps the bundled scripts within it (#246).
- A `--resume` that preserves the previous run in a sibling archive no longer leaves the new run
  directory private to the user who resumed it (`0700`): it keeps the permissions of the run it
  replaces (#235).
- Provenance bundle files are created like the rest of a run's files (`0666` less the umask)
  instead of `0600`, so the group a run's results are shared with can verify and replay it (#235).
- MCP refuses a tool or prompt call whose `arguments` is given but is not an object (`null`,
  `false`, a list) instead of running it without arguments, answers a request id that JSON-RPC
  does not allow (a boolean, an object, `NaN`) with an error, and no longer queues a `ping` behind
  long-running tool calls (#237).
- `nfclaw verify` and a replay's own environment check report an empty, damaged or incomplete
  environment record as `unverified` instead of `identical`, and compare image identities in both
  directions, so two names for one recorded image cannot hide a different image in the replay. A
  bundle from before environment records is still compared by its files. Reproductions and limits:
  the [boundary-integrity audit](docs/audit/2026-10-30-boundary-integrity-audit.md) (#237).
- A chain spec's `config` entries must be non-empty paths, and a `null` `nxf_env` keeps the
  default, as a `null` `nxf_ver`, `limits` or `config` already did (#237).
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
  bundled `scripts/run_with_timeout.py` instead of refusing to run (#233).
- A params file path given to `parameters.merge` that does not exist is an error, not an empty
  set of parameters (`nfclaw run` already refused it) (#233).
- `nfclaw mcp` answers a message nested too deeply to parse instead of stopping (#219).
- `nfclaw chain edges <name>` refuses a pipeline the library lacks (exit 1) instead of printing
  nothing, which read as "no handoff exists"; for a pipeline without rules it says so (#234).
- `nfclaw chain status --json` gives a missing chain the same keys as a found one, with `error` a
  list as in `nfclaw status --json` (#234).
- On Linux, Nextflow is launched without Python code between fork and exec (`preexec_fn`), which
  can deadlock a parent running threads, as nfclaw's container watch does: a single-threaded
  launcher requests the parent-death signal and execs Nextflow in place (#234).
- Stopping a run or replay whose process group has already ended no longer searches or signals
  that group's number, which another process group may hold by then (#234).
- `CITATION.cff` no longer gives 1.0.0 a release date (2026-06-15) that no release had (#234).
- Robustness of `nfclaw status` with unreadable logs and damaged records, the job supervisor and
  the container watcher (#218).
- A replay runs with the Nextflow settings its run recorded: `NXF_*` variables that the replaying
  shell sets but the run did not see are removed, and a recorded secret, kept only as
  `<redacted>`, must be exported again. A bundle with an incomplete pipeline identity or checksum
  record is refused (#229).
- `--pipeline-version` no longer deletes a partly materialized checkout under
  `pipelines/<name>/.versions/` to start again: it may hold local work, so nfclaw refuses and names
  the directory to move aside (#229).
- A run refused before launch redacts secret `NXF_*` values from the command and error it prints
  and logs (#229).
- A chain spec whose `nxf_env`, `nxf_ver` or `limits` value has the wrong type (a number for a
  memory value, a list for an object) is refused with an error that names the field (#229).
- `nfclaw status` finds the latest attempt in a run log from an index the log's writer keeps (in
  older logs, by searching backward from the end) instead of reading the whole log (#229).
- The pipeline updater takes the lock runs take to fetch or initialize a pipeline and, when an
  update fails or is interrupted, restores only the checkout, pin and generated files it
  changed; the drift check refuses a pin whose source or checkout does not match its record
  (#229).
- On the website, arrow keys in the skills list move from the row that has focus, not from the
  selected one (#229).

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
