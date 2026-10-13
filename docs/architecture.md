# nf-claw Architecture

nf-claw derives its parameter documentation and general input validation from each pipeline's own `nextflow_schema.json` and, where present, its input schema (`assets/schema_input.json`). Curated handoff rules and documented compatibility adjustments supplement those schemas. The pinned upstream pipeline remains the authority for its analysis and complete runtime validation.

---

### Navigation

[System Overview](#system-overview) • [1. pipelines/ Library](#1-pipelines--the-library-content) • [2. runner/ Engine](#2-runner--the-runtime-engine-nfclaw) • [3. handoffs/ Rules](#3-handoffs--chaining-rules) • [4. librarian/ Maintenance](#4-librarian--maintenance--code-generation)

---

## System Overview

The repository is structured into four distinct, decoupled functional zones:

```
                          ┌────────────────────────────────────────┐
                          │             nf-claw Core               │
                          └────────────────────────────────────────┘
                                              │
             ┌──────────────────┬─────────────┴────────────┬──────────────────┐
             ▼                  ▼                          ▼                  ▼
       ┌──────────────┐   ┌──────────────┐          ┌──────────────┐   ┌────────────────┐
       │  pipelines/  │   │   handoffs/  │          │   runner/    │   │   librarian/   │
       │ (Submodules  │   │  (Chaining   │          │ (CLI, Engine │   │ (Drift Gate,   │
       │  & Skills)   │   │    Rules)    │          │  & Runtime)  │   │  Generators)   │
       └──────────────┘   └──────────────┘          └──────────────┘   └────────────────┘
```

| Architectural Zone | Primary Responsibility | Key Files & Directories |
|---|---|---|
| **`pipelines/`** | Pinned upstream code, agent skills, and parameter reference manuals. | `pipelines/<name>/upstream/`, `skill.md`, `reference.md` |
| **`runner/`** | The `nfclaw` CLI runtime: preflight validation, process isolation, locking, and provenance. | `runner/cli.py`, `runner/schema.py`, `runner/execution.py`, `runner/chain.py` |
| **`handoffs/`** | Declarative mapping specifications connecting sequential pipeline stages. | `handoffs/<upstream>/<downstream>.json` |
| **`librarian/`** | Maintenance generators, submodule release trackers, and schema drift checkers. | `librarian/check_drift.py`, `write_skill.py`, `update_pipelines.py` |

---

## 1. `pipelines/` — The Library Content

Each pipeline lives in `pipelines/<name>/`:

| Artifact | Type | Role & Guarantee |
|---|---|---|
| **`upstream/`** | Git submodule | Pinned to the commit resolved from an nf-core release tag. Upstream code unmodified. |
| **`skill.md`** | Agent definition | Concise agent instructions generated deterministically from `nextflow_schema.json`. Includes identity, description, tool inventory (from `CITATIONS.md`), run commands, allowed parameters, parameter groups from the upstream schema, and chaining relationships. |
| **`reference.md`** | Complete catalog | Comprehensive parameter manual documenting every parameter, type, required/hidden status, regex constraints, and defaults. |
| **`.versions/`** | Git worktrees *(git-ignored)* | Commit-anchored worktrees materialized on demand when executing other releases or unreleased `dev` branch heads. |

The drift gate regenerates `skill.md` and `reference.md` from the pinned schemas and checks them against the committed files. This detects stale generated context; it does not prove that an upstream schema describes every behavior of its analysis code correctly.

---

## 2. `runner/` — The Runtime Engine (`nfclaw`)

The runner executes pipelines, validates inputs before launch, enforces runtime isolation, records provenance, and manages multi-stage pipeline chains.

### 2.1 Schema Preflight & Fast-Fail Parameter Validation
Before invoking Nextflow, `nfclaw run` executes fast, deterministic preflight checks (`runner/preflight.py`, `runner/schema.py`, `runner/parameters.py`, `runner/inputs.py`):
- **Syntactic Validation:** Rejects unknown flags, typos, and syntax errors prior to Nextflow process initialization.
- **Type & Range Checking:** Validates scalar types, boolean flags, numeric bounds, and enum choices.
- **Samplesheet Generation (`runner/sheetgen.py`):** When `--input` names data files (a directory, a glob, or files given with `--input` once each) where the pipeline takes a samplesheet, the first stage of the run writes that samplesheet from the pinned `schema_input.json` alone: typed columns take files matching their patterns, FastQ mates pair by `_R1`/`_R2` names, or by `_1`/`_2` when their read names identify one molecule, sample names come unaltered from file names, and values no file determines come from `--sheet-set` or schema defaults. Gaps and ambiguities are refused. The result then passes the same preflight as a hand-written sheet; it is staged beside `params.json`, named on the command line so a moved bundle replays its own copy, recorded with the configs, and its data files are recorded as inputs.
- **Samplesheet Preflight:** Verifies samplesheet existence, column headers, required fields, and path formats.
- **Path Resolution:** Resolves the `--input` samplesheet path against the caller's working directory. Local data paths inside a samplesheet must already be absolute; relative entries are rejected.
- **Type Coercion Safeguards:** Translates `--input false` to an unset `input` parameter in `params.json` for pipelines that support running without a samplesheet (e.g. sarek), preventing nf-schema type validation crashes.
- **Pipeline Code Integrity:** Refuses a pinned `upstream/` that is not at the commit its `skill.md` documents, and any tree (pin, release cache or `dev` commit) with local edits to tracked files, so provenance never names code that did not run.
- **Resource Ceiling Floor:** Refuses `--limit-*` when the run's engine predates Nextflow 24.04.0 or cannot be identified; older engines ignore `process.resourceLimits` silently.
- **Diagnostics:** Emits clean, actionable diagnostics with `ErrorCode` and suggested fixes. The pinned pipeline's runtime validation remains authoritative for conditional and complex constraints; releases use different validation plugins.

### 2.2 Run Execution & Sibling Directory Locking
- **Launch Isolation:** Nextflow is executed with its working directory pointed inside `--outdir`, isolating `.nextflow/` state, session databases, and caches to that run.
- **Sibling File Locking:** On POSIX systems, `runner/locking.py` acquires an exclusive, non-blocking sibling flock (`.{outdir.name}.nfclaw.lock`) before creating or modifying `--outdir`. Overlapping or concurrent runs into the same directory fail fast with `ErrorCode.ENVIRONMENT`, preventing corrupted session states or interleaved logs.
- **Check Safety:** `--check` stages parameters in temporary directories and never writes into
  `--outdir`. Resolving a requested pipeline version may fetch tags or populate its version cache.

### 2.3 Process Lifecycle & Signal Trapping
- `runner/execution.py` traps `SIGTERM`, `SIGHUP`, and `SIGINT` (Ctrl-C).
- On receiving a stop signal, nfclaw signals Nextflow's process group, captures its final output,
  and attempts to record the termination outcome and provenance before exiting.
- On Linux, `PR_SET_PDEATHSIG` signals the direct Nextflow child if nfclaw dies abruptly. It does
  not by itself guarantee cleanup of detached processes, remote tasks, or containers.

### 2.4 Structured Logging & Status Inspection
- **`<outdir>/provenance/logs/run.log`**: Authoritative execution log containing nfclaw launch metadata (command, PID, host, advisories), followed by Nextflow's console stream.
- **Outcome Line:** The log terminates with a machine-verifiable trailer line:  
  `==> nfclaw run finished <timestamp>: <outcome>`
- **Stream Separation:** `stdout.txt` and `stderr.txt` are maintained alongside `run.log`.
- **`nfclaw status <outdir>`**: Reads `run.log` and, for an unfinished run on the same host,
  checks the recorded process identity. Reports `success`, `running`, `failed`, `terminated`, or
  `stopped without an outcome`. Remote unfinished runs cannot be inspected locally.
- **Completion caveats:** A pipeline can exit 0 without some samples or tasks. `runner/runlog.py`
  quotes what it reported (nf-core's "…, but with errored process(es)", rnaseq's skipped samples)
  and Nextflow's count of ignored task failures; `nfclaw run` prints them, `nfclaw status` reports
  `success — with caveats …`, and the manifest records them as `completion_caveats`.

### 2.5 Provenance Bundles & Dependency Hashing
Executions attempt to record a provenance bundle in `<outdir>/provenance/`, including failed runs. Individual records are replaced atomically and the manifest is published last. Recording errors prevent a successful outcome; the replay guard refuses an incomplete bundle.

| Manifest / File | Description & Verification Function |
|---|---|
| `run_manifest.json` | Captures pipeline name, version, commit, command, recording time, outcome, observed engine, operating system, and active `NXF_*` variables (with sensitive values redacted). Host/process identity is recorded in `logs/run.log`. |
| `inputs.sha256` | Prelaunch digests of declared local input files, schema path parameters, existing absolute local files supplied to parameters without a path format, and local data paths inside CSV/TSV or flat JSON/YAML records, including auxiliary tables. |
| `outputs.sha256` | Snapshot of published result files, excluding provenance and Nextflow state. |
| `pipeline.sha256` | Prelaunch digest snapshot of tracked pipeline source files. |
| `configs.sha256` | Digests of the resolved params file, generated configs and explicit external Nextflow configuration files passed via `-c`. |
| `inputs.inventory.json` / `configs.inventory.json` | Prelaunch dependency namespaces, empty directories, entry types and link identities, checked alongside file bytes. |
| `outputs.inventory.json` | Published output namespace used by replay verification and handoff checks. |
| `resource_limits.config` | Generated resource ceiling configuration when `--limit-*` flags are used. |
| `nf_schema_compat.config` / `fastqrepair_compat.config` | Conditional plugin adjustments and recorded task corrections. |
| `trace_report_suffix` | A pinned parameter in `params.json` when supported by the upstream schema; other independently timestamped metadata can still change filenames. |

Missing local path parameters without an upstream `exists: true` constraint are delegated to Nextflow: they may be output/cache destinations. They produce a warning and an `unverified_local_paths` manifest entry rather than a false input checksum. Required missing inputs are refused. Remote data, profile-only references, indirect configuration includes, container digests and data referenced by non-tabular input formats are not comprehensively frozen.

`runner/path_roles.json` records output-only directory roles proven from exact upstream commits.
The generic consumer requires the expected pipeline identity, an unchanged directory schema and
a clean matching source checkout. These destinations keep their filename checks and parameter
checksums, while unrelated existing children are excluded from input inspection and snapshots.
Unlisted paths, changed releases and reused `storeDir` caches retain their input guards. Audited
whole-path shell arguments also check parent folders and resolved symlink paths.

Before `--resume`, declared local inputs are compared with the prior byte and namespace
snapshots. Unchanged inputs retain caching; changed data or an unavailable inventory
archives the complete prior run in `<outdir>.previous-<id>` and starts a fresh cache
session. Prior logs are copied forward. This also applies with `--no-provenance`.

Archive operations prepare replacements before moving the run, retain ordinary relative links,
rebase links through outdir aliases and external publications, and roll back recoverable failures
and cancellation. A verified result inventory is rebased with its publication links, preserving
the archive's file checksums and logical namespace.

### 2.6 Replay & Replay Guard
- **`provenance/commands.sh`**: Standalone reproduction script that re-runs the recorded execution — same pinned code, local inputs, parameters, configs and observed engine — into a fresh output directory (default `<outdir>.replay`). Replaying in place is rejected to avoid output collisions with existing published artifacts. Outputs are reproduced only as far as the pipeline's tools are deterministic: a multithreaded or unseeded stochastic step can produce different results from identical inputs (measured for ampliseq 3.0.0 in [known-issues](known-issues.md#pipeline-specific-run-notes)). Compare replays with `nfclaw verify` and a format-aware inspection of changed files.
- **`provenance/replay_guard.py`**: A zero-dependency script executed by `commands.sh` prior to launching Nextflow. Verifies that local inputs, referenced samplesheets, external configs, and pipeline git commits match the hashes in `provenance/*.sha256`. If inputs have drifted or disappeared, replay halts immediately.
- **Dynamic Relocation:** `commands.sh` discovers its current bundle directory and rebases
  bundle-owned params/config arguments. External dependencies retain their recorded paths.

### 2.7 Verification Engine (`nfclaw verify`)
- `runner/verify.py` compares replayed output files against the original run by path.
- **Structural Equivalence:** Separates file inventory from byte equality. Pairs timestamped
  metadata paths in `pipeline_info/` while preserving file multiplicity and reporting byte changes.
  Also compares directory inventories; a historical file-only manifest cannot certify structure.
- **Strict Mode (`--strict`):** Requires byte-for-byte identity for every paired result, including metadata, and agreement of recorded link identities.
- **Scientific Scope:** Inventory agreement alone establishes no analytical agreement. Matching
  bytes demonstrate agreement of the observed artifacts, not biological accuracy or universal reproducibility.

### 2.8 Dynamic Version Selection & Dev Tracking
- `nfclaw run <name> --pipeline-version X.Y.Z`: Materializes the requested release tag as a git worktree in `pipelines/<name>/.versions/<tag>/`. Skill documentation is generated dynamically on demand.
- `nfclaw run <name> --pipeline-version dev`: Resolves nf-core's `dev` branch to its current remote head commit and materializes an immutable worktree in `.versions/dev-<commit12>/`. Caches heads locally for offline fallback.

### 2.9 Chaining Engine (`runner/chain.py`)
- Runs multi-pipeline workflows sequentially, passing outputs from stage $k$ to inputs of stage $k+1$.
- **Chain Locking:** Locks `<outdir>/chain/.lock` against concurrent chain execution.
- **Preflight Configuration Probe:** Runs `nextflow config` under each stage's engine before
  launching stage 1. Parser failures, unavailable engines and inconclusive probes stop the chain.
- **Handoff Output Verification:** Validates upstream output bytes and complete recorded namespaces before constructing downstream inputs; inherited local references also require producer input evidence.
- **Lineage Verification:** `nfclaw chain status` checks recorded stage identities, live stage
  outputs, and handoff files/references against upstream and downstream checksum inventories.
  This checks the recorded links; it does not independently revalidate every original input,
  configuration or algorithm, or authenticate a bundle against deliberate rewriting.

---

## 3. `handoffs/` — Chaining Rules

Chaining rules live in `handoffs/<upstream>/<downstream>.json`. They describe how to transform an upstream stage's outputs into a downstream stage's parameter inputs:
- **Declarative Mappings:** Source types include `samplesheet`, `build`, `file`, and `upstream_param`.
- **Transformations:** Row- and column-level adaptations including `rename`, `set`, `add_empty`, `drop_rows_not_allowed`, and `require_values`.
- **Metagenomic Safety:** Rules for assembly pipelines (e.g. `mag`) explicitly isolate individual samples (`group: {sample}`) to avoid unintended multi-sample co-assembly pooling.
- **Drift Gate Static Validation:** The drift gate statically validates every handoff rule against the pinned schemas of both participating pipelines.

---

## 4. `librarian/` — Maintenance & Code Generation

Invoked via `make`, the librarian automates generation and release tracking for the curated library:

| Librarian Tool | Invocations | Purpose |
|---|---|---|
| `write_skill.py` | `make build` | Generates `skill.md` and `reference.md` from `nextflow_schema.json` and `assets/schema_input.json`. |
| `write_catalog.py` | `make build` | Compiles `catalog.json` and `catalog.md` across all tracked pipelines. |
| `check_drift.py` | `make check` | Enforces bidirectional synchronization across `sources.tsv`, `.gitmodules`, disk directories, skills, references, and handoff rules. |
| `update_pipelines.py` | `make update` | Scans upstream remotes for newly published release tags and bumps submodules. |
| `discover_pipelines.py` | Workflow | Discovers newly published DSL2 nf-core pipelines and scaffolds initial submodules. |
