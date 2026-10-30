# nf-claw Architecture

nf-claw derives its parameter documentation and general input validation from each pipeline's own `nextflow_schema.json` and, where present, its input schema (`assets/schema_input.json`). Curated handoff rules and documented compatibility adjustments supplement those schemas. The pinned upstream pipeline remains the authority for its analysis and complete runtime validation.

---

## Navigation

[System Overview](#system-overview) • [1. pipelines/ Library](#1-pipelines--the-library-content) • [2. runner/ Engine](#2-runner--the-runtime-engine-nfclaw) • [3. handoffs/ Rules](#3-handoffs--chaining-rules) • [4. librarian/ Maintenance](#4-librarian--maintenance--code-generation)

---

## System Overview

The repository is structured into four distinct, decoupled functional zones:

```
                        ┌─────────────────────────────────┐
                        │           nf-claw Core          │
                        └─────────────────────────────────┘
                                         │
        ┌─────────────────────┬──────────┴──────────┬─────────────────────┐
        ▼                     ▼                     ▼                     ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│   pipelines/  │     │   handoffs/   │     │    runner/    │     │   librarian/  │
│  (Submodules  │     │   (Chaining   │     │  (CLI, Engine │     │  (Drift Gate, │
│   & Skills)   │     │     Rules)    │     │   & Runtime)  │     │  Generators)  │
└───────────────┘     └───────────────┘     └───────────────┘     └───────────────┘
```

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

The runner executes pipelines, validates inputs before launch, enforces runtime isolation, records provenance, and manages multi-stage pipeline chains. `nfclaw mcp` (`runner/mcp_server.py`, `runner/mcp_tools.py`, `runner/jobs.py`) serves the same commands to MCP clients, running runs and chains as detached jobs ([mcp.md](mcp.md)).

### 2.1 Schema Preflight & Fast-Fail Parameter Validation
`nfclaw run --check` lists completed, deferred and unsupported checks; real runs record the detailed
`validation_scope` in their manifest. The [preflight scope guide](preflight.md) documents the schema
subset and the generation support matrix, including differences between handwritten and generated
tables and JSON/YAML inputs.

Before invoking Nextflow, `nfclaw run` executes fast, deterministic preflight checks (`runner/preflight.py`, `runner/schema.py`, `runner/parameters.py`, `runner/inputs.py`):
- **Syntactic Validation:** Rejects unknown flags, typos, and syntax errors prior to Nextflow process initialization.
- **Type & Range Checking:** Validates scalar types, boolean flags, numeric bounds, and enum choices.
- **Samplesheet Generation (`runner/sheetgen.py`):** When `--input` names data files (a directory, a glob, or files given with `--input` once each) where the pipeline takes a samplesheet, the first stage of the run uses the pinned input contract, including declared alternative formats and exact-schema source annotations in `runner/input_roles.json`. Typed columns take files matching their patterns, FastQ mates pair by `_R1`/`_R2` names, or by `_1`/`_2` when their read names identify one molecule, sample names come unaltered from file names, and values no file determines come from `--sheet-set` or schema defaults. Gaps and ambiguities are refused; source-audited stale HGTseq and Nanoseq contracts require explicit sheets. The result then passes the same preflight as a hand-written sheet; it is staged beside `params.json`, named on the command line so a moved bundle replays its own copy, recorded with the configs, and its data files are recorded as inputs.
- **Samplesheet Preflight:** Verifies samplesheet existence, column headers, required fields, and path formats.
- **Path Resolution:** Resolves the `--input` samplesheet path against the caller's working directory. Local data paths inside a samplesheet must already be absolute; relative entries are rejected.
- **Type Coercion Safeguards:** Translates `--input false` to an unset `input` parameter in `params.json` for pipelines that support running without a samplesheet (e.g. sarek), preventing nf-schema type validation crashes.
- **Pipeline Code Integrity:** Refuses a pinned `upstream/` that is not at the commit its `skill.md` documents, and any tree (pin, release cache or `dev` commit) with local edits to tracked files, so provenance never names code that did not run.
- **Resource Ceiling Floor:** Refuses `--limit-*` when the run's engine predates Nextflow 24.04.0 or cannot be identified; older engines ignore `process.resourceLimits` silently.
- **Reproducibility Advisories:** `runner/reproducibility.py` scans pinned task scripts before launch to detect known sources of run-to-run variability (such as dada2 `assignTaxonomy` tie-breaking or unseeded QIIME2 rarefaction) and announces prelaunch advisories unless those steps are explicitly skipped. It also announces pinned workflow code that reorders, in place, a list Nextflow hands to several processes at once (createtaxdb 3.1.0's sourmash step) when that step runs.
- **Diagnostics:** Emits clean, actionable diagnostics with `ErrorCode` and suggested fixes. The pinned pipeline's runtime validation remains authoritative for conditional and complex constraints; releases use different validation plugins.

#### What is left to Nextflow and the pinned release
Every pinned release checks itself at launch, before any task runs. Nextflow enforces the manifest's `nextflowVersion`, and every pinned release uses the strict `!>=` form. The release's validation code checks every parameter and samplesheet against its schemas: nf-schema, nf-validation in older releases, or the `NfcoreSchema` library of the oldest template. nfclaw does not repeat a check whose result Nextflow or the release produces just as early:
- **Engine version:** a launch does not probe for it. When Nextflow refuses an older engine, nfclaw's error names the `--nxf-ver` to pass, and `skill.md` states the declared engine. `--check` warns about it, because `nextflow config` does not enforce it.
- **Java:** nfclaw looks for it where the Nextflow launcher does (`NXF_JAVA_HOME`, `JAVA_HOME`, then `PATH`). The launcher checks the version.
- **Profiles, config syntax, conditional and nested schema constraints, remote files:** Nextflow and the plugin judge them at launch.
- **Analysis results:** each release's nf-test snapshot is what nf-core's CI checks. nf-claw's demo validation compares its runs with that snapshot instead of re-deriving the tools' output.

nfclaw keeps its own schema checks where they act before Nextflow could:
- `--check`, a chain's `--check` and the MCP `run_pipeline(check=true)` never start Nextflow.
- A chain validates every stage before the first one launches. Otherwise a later stage's own validation would run only after the stages before it have finished.
- Unknown parameters are refused. nf-schema only warns about them by default, because institutional profiles may set extra parameters, so a mistyped flag would run with its default.
- Declared local samplesheet paths must be absolute and identifiers shell-safe. A real run hashes its discovered local dependencies before launching Nextflow from `--outdir`; `--check` inspects paths without establishing every data file's byte readability. Implicit, transitive and remote dependencies retain the limits in [preflight scope](preflight.md).

### 2.2 Run Execution & Sibling Directory Locking
- **Launch Isolation:** Nextflow is launched from `--outdir`, isolating its `.nextflow/` history and session databases. Task work files default to the shared `<repo>/work/` directory; `NXF_WORK` selects another location and is resolved against the caller's working directory before launch.
- **Sibling File Locking:** On POSIX systems, `runner/locking.py` acquires an exclusive, non-blocking sibling flock (`.{outdir.name}.nfclaw.lock`) before creating or modifying `--outdir`. Overlapping or concurrent runs into the same directory fail fast with `ErrorCode.ENVIRONMENT`, preventing corrupted session states or interleaved logs.
- **Docker Daemon Preflight:** For runs selecting the Docker profile, `runner/preflight.py` probes daemon responsiveness (`docker info`) with a configurable timeout (`NFCLAW_DOCKER_TIMEOUT`, default 60 seconds; bounded by `--timeout`), preventing premature aborts on busy CI or cloud runners.
- **Check Safety:** `--check` stages parameters in temporary directories and never writes into
  `--outdir`. Resolving a requested pipeline version may fetch tags or populate its version cache.

### 2.3 Process Lifecycle & Signal Trapping
- `runner/execution.py` traps `SIGTERM`, `SIGHUP`, and `SIGINT` (Ctrl-C).
- On receiving a stop signal, nfclaw signals Nextflow's process group, captures its final output,
  and attempts to record the termination outcome and provenance before exiting.
- Shutdown grace defaults to 10 seconds and is configurable with `NFCLAW_SHUTDOWN_GRACE`.
  Runs have no overall deadline unless `--timeout SECONDS` is supplied; see [timeouts](timeouts.md).
- A task container belongs to the engine, not to the process group: before each signal nfclaw
  notes the `nxf-…` containers the group's `docker run`/`podman run` clients started, and once the
  group is gone force-removes those still present, recording it in the run log
  (`replay_guard.task_containers`; a replay's supervisor does the same).
- On Linux, `PR_SET_PDEATHSIG` signals the direct Nextflow child if nfclaw dies abruptly. It does
  not by itself guarantee cleanup of detached processes or remote tasks.

### 2.4 Structured Logging & Status Inspection
- **`<outdir>/provenance/logs/run.log`**: Authoritative execution log containing nfclaw launch metadata (command, PID, host, advisories), followed by Nextflow's console stream.
- **Outcome Line:** The log terminates with a machine-verifiable trailer line:  
  `==> nfclaw run finished <timestamp>: <outcome>`
- **Stream Separation:** `stdout.txt` and `stderr.txt` are maintained alongside `run.log`.
- **`nfclaw status <outdir>`**: Reads `run.log` and, for an unfinished run on the same host,
  checks the recorded process identity. Reports `success`, `running`, `failed`, `terminated`, or
  `stopped without an outcome`. Remote unfinished runs cannot be inspected locally, and a log
  that exists but cannot be read is reported as `unknown` with the reason (exit status 1).
- **Completion caveats:** A pipeline can exit 0 without some samples or tasks. `runner/runlog.py`
  quotes what it reported (nf-core's "…, but with errored process(es)", rnaseq's skipped samples)
  and Nextflow's count of ignored task failures; `nfclaw run` prints them, `nfclaw status` reports
  `success — with caveats …`, and the manifest records them as `completion_caveats`.

### 2.5 Provenance Bundles & Dependency Hashing
Executions attempt to record a provenance bundle in `<outdir>/provenance/`, including failed runs. Individual records are replaced atomically and the manifest is published last. Recording errors prevent a successful outcome; the replay guard refuses an incomplete bundle.

| Manifest / File | Description & Verification Function |
|---|---|
| `logs/run.log` | The whole launch in order, ending with its outcome line (§2.4); `stdout.txt` and `stderr.txt` beside it keep Nextflow's raw streams. |
| `run_manifest.json` | Captures pipeline name, version, commit, command, recording time, outcome, observed engine, operating system, the nfclaw that wrote the bundle (`nfclaw`: package version and checkout commit, as `nfclaw --version` prints them), and active `NXF_*` variables (with sensitive values redacted). Host/process identity is recorded in `logs/run.log`. `pipeline_archive`, `bundled_configs`, `container_pins` and `execution_environment.issues` show the evidence actually captured. |
| `params.json` | Resolved wrapper parameters passed to Nextflow, including the pinned `trace_report_suffix` where the upstream schema supports it and the nf-core/configs commit (`custom_config_version`) when automatic pinning applies. The upstream pipeline can record further defaults or profile values itself, and other independently timestamped metadata can still change filenames. |
| `commands.sh`, `replay_guard.py`, `environment_record.py` | The replay script and its two zero-dependency helpers (§2.6). |
| `inputs.sha256` | Prelaunch digests of declared local input files, schema path parameters, existing absolute local files supplied to parameters without a path format, and local data paths inside CSV/TSV or flat JSON/YAML records, including auxiliary tables. |
| `outputs.sha256` | Snapshot of published result files, excluding provenance and Nextflow state. |
| `pipeline.sha256` | Prelaunch digest snapshot of tracked pipeline source files. |
| `pipeline-source.tar.gz` | Deterministic archive of exactly those source files (fixed owner, time and mode, sorted, untimestamped gzip). A replay runs the recorded checkout while it holds exactly this source, otherwise it extracts and checks the archive and runs that copy (`<target>/provenance/pipeline-source.json` records which). |
| `configs/` | Copies of external `-c` configuration files, recorded in the manifest's `bundled_configs`. A replay passes the copies; a config that uses `includeConfig` replays from its original path. |
| `environment.json` | Available execution evidence: process/container records, image identities (Docker/Podman registry digest, image ID and platform, or Singularity/Apptainer file SHA-256), Nextflow build, container engine version, plugins, Java runtime and remote-input hashes recovered from logs. Missing evidence is recorded as unresolved entries or `issues`. Its digest is in the manifest (`environment_record`), with a summary under `execution_environment`. |
| `containers.config` | Optional Nextflow config pinning eligible Docker/Podman processes (fully qualified `withName`) to recorded registry digests. `commands.sh` passes it last when present. File-image engines, unresolved or multiple images, mixed containerless tasks and ephemeral Wave references do not receive these pins. |
| `configs.sha256` | Digests of the resolved params file, generated configs and explicit external Nextflow configuration files passed via `-c`. |
| `inputs.inventory.json` / `configs.inventory.json` | Prelaunch dependency namespaces, empty directories, entry types and link identities, checked alongside file bytes. |
| `outputs.inventory.json` | Published output namespace used by replay verification and handoff checks. |
| `resource_limits.config` | Generated resource ceiling configuration when `--limit-*` flags are used. |
| `nf_schema_compat.config` / `fastqrepair_compat.config` | Conditional plugin adjustments and recorded task corrections. |

Checksum manifests escape filenames using GNU conventions, preserving backslashes and Unicode
separators without losing file identities.

Missing local path parameters without an upstream `exists: true` constraint are delegated to Nextflow: they may be output/cache destinations. They produce a warning and an `unverified_local_paths` manifest entry rather than a false input checksum. Required missing inputs are refused. Remote data recovered from Nextflow's staging logs is hashed after the run and compared after a replay; files tasks download themselves, profile-only references, a user config's own `includeConfig` targets, Conda environments and data referenced by non-tabular input formats are not comprehensively frozen. Supported validation-only table URLs are fetched again after the run, up to 100 MiB; that hash describes the refetched bytes, not an immutable copy of what validation originally read. Unavailable identities remain unresolved.

`runner/institutional.py` pins the release's default nf-core/configs branch when its schema declares `custom_config_version` and its config uses the recognized nf-core URL. Explicit `custom_config_version` or `custom_config_base` values and a nonempty `NXF_OFFLINE` bypass automatic resolution. A resumed run reuses its prior recorded commit when applicable. Successful resolution is passed in `params.json` and recorded under `institutional_configs`; failure emits an advisory and retains the release default. This does not resolve arbitrary config includes.

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

Before success, declared local inputs, configurations and tracked source are checked
against their launch snapshots. Changed or unreadable dependencies fail the run and
are reported in the manifest's `dependency_stability` record. These checkpoint checks
also run with `--no-provenance`; transient changes restored between checkpoints and
remote or indirectly configured dependencies remain outside their scope.

Archive operations prepare replacements before moving the run, retain ordinary relative links,
rebase links through outdir aliases and external publications, and roll back recoverable failures
and cancellation. A verified result inventory is rebased with its publication links, preserving
the archive's file checksums and logical namespace.

### 2.6 Replay & Replay Guard
- **`provenance/commands.sh`**: Standalone reproduction script that re-runs the recorded execution — same pinned code, local inputs, parameters, configs and observed engine — into a fresh output directory (default `<outdir>.replay`). Replaying in place is rejected to avoid output collisions with existing published artifacts. Outputs are reproduced only as far as the pipeline's tools are deterministic: a multithreaded or unseeded stochastic step can produce different results from identical inputs (measured for ampliseq 3.0.0 in [known-issues](known-issues.md#pipeline-specific-run-notes)). Compare replays with `nfclaw verify` and a format-aware inspection of changed files.
- **Self-contained replay:** `commands.sh` runs the recorded checkout while its git revision and tracked bytes still match `pipeline.sha256` (keeping `${projectDir}`-derived paths), otherwise extracts `pipeline-source.tar.gz` into `<target>/provenance/pipeline` (each file checked) and runs that. It passes replayable config copies and, when present, `containers.config` for eligible process pins. Extracting changes `${projectDir}`; absolute paths already stored in params are not rewritten. Local input data and configs using `includeConfig` retain their external dependencies.
- **`provenance/environment_record.py`**: A zero-dependency script that records the execution environment (`runner/environment_record.py`, copied into the bundle). After a replay's Nextflow succeeds, `commands.sh` runs it to write `<target>/provenance/environment.json` and `environment_check.json`; a different image digest, plugin set, container engine or staged remote file fails the replay after Nextflow, and undecidable entries are reported as unverified.
- **`provenance/replay_guard.py`**: A zero-dependency script executed by `commands.sh` prior to launching Nextflow. Verifies that local inputs, referenced samplesheets, configs (bundled copies where recorded), the archived pipeline source (or, for bundles that predate the archive, the checkout's git commit and tracked bytes) and the recorded `environment.json` / `containers.config` match the digests in the bundle. If anything has drifted or disappeared, replay halts immediately.
- **Dynamic Relocation:** `commands.sh` discovers its current bundle directory and rebases
  bundle-owned params, configs, config copies, pins and source archive. External input data retain their recorded paths.

The archive is verified before and after execution. When the replay uses the original
checkout, its revision and tracked bytes are also rechecked at completion. The extracted
working tree is checked on creation and rehashed against the source manifest after execution.
Replay targets receive logs and source/environment records; the original bundle remains
the replay entry point and the reference for dependency and output checks.

### 2.7 Verification Engine (`nfclaw verify`)
- `runner/verify.py` compares replayed output files against the original run by path.
- **Structural Equivalence:** Separates file inventory from byte equality. Pairs timestamped
  metadata paths in `pipeline_info/` while preserving file multiplicity and reporting byte changes.
  Also compares directory inventories; a historical file-only manifest cannot certify structure.
- **Random Library Name Pairing:** For tools like `kraken2-build --add-to-library` in createtaxdb that generate random temporary filenames (e.g. `XXXXXXXXXX.fna`, `.fna.masked`, `prelim_map_XXXXXXXXXX.txt`), `runner/verify.py` pairs exactly these names one to one within their directory, lists them under `renamed`, and compares their bytes without reporting false inventory discrepancies.
- **Strict Mode (`--strict`):** Requires byte-for-byte identity for every paired result, including metadata, and agreement of recorded link identities. When both `environment.json` records are readable JSON objects, the environment comparison must also report `identical`; `differs` and `unverified` fail strict mode. Otherwise the report says `not recorded by both runs` and no environment condition is enforced.
- **Environment Comparison:** Compares the container engine name, loaded plugin list, comparable images for processes present in both records, and the recorded remote-input URLs and hashes. Java runtime changes and processes present on only one side are notes. Nextflow build, container engine version, host platform and task counts are recorded but not equality gates. Default verification reports these findings without changing its structural exit criterion; standalone replay fails detected mismatches, but permits `unverified` results.
- **Recording Scope:** An `identical` verdict covers the evidence compared. Inspect `issues`, `unverified` and `notes` as well; missing task or staging records are not comprehensively detected, and the verdict does not certify that every execution dependency was captured.
- **Scientific Scope:** Inventory agreement alone establishes no analytical agreement. Matching
  bytes demonstrate agreement of the observed artifacts, not biological accuracy or universal reproducibility.

### 2.8 Scientific Output Assessment (`nfclaw assess`)
- `runner/scientific.py`, `runner/scientific_hts.py`, and `runner/scientific_h5ad.py` evaluate run outputs against explicit declarative contracts (`runner/output_contracts/*.json`).
- **Format Parsers & Comparative Evaluation:**
  - `table`: exact unique header, unique row-key column(s), finite decimal rational arithmetic comparisons, sample columns or expected sample membership, and documented column exclusions (`ignore_columns`).
  - `fasta`: unique identifiers, exact case-preserved sequences/descriptions, sequence counts, lengths, and N50 summary.
  - `bam`: 0-based half-open coordinates, alignments, unmapped/duplicate reads, flags, CIGAR, positions, mate fields, quality, tags, read-group sample labels, and canonical header digest comparisons.
  - `vcf`: 1-based closed coordinates, HTSlib-decoded variants, INFO/FORMAT fields, genotype phase, sample columns, and GATK strand count encodings (`INFO/AS_SB_TABLE`).
  - `h5ad_matrix`: dense/CSR/CSC matrix comparison by cell/gene identity with integer/nonnegative invariants.
- **Assessment Modes:**
  - Single-run assessment: checks that output artifacts exist, match expected schemas, record bounds, and meet coordinate requirements.
  - Comparative assessment (`--against ORIGINAL`): parses candidate and verified original files, requiring that original outputs match their recorded `provenance/outputs.sha256` before serving as truth, and applies exact rational tolerances.
- **Actionable Reporting:** Returns JSON detailing evaluation verdicts, parsed record counts, tolerance reasons, and unassessed file tallies; exits nonzero on any unmet expectation. See [`docs/scientific-output-contracts.md`](scientific-output-contracts.md).

### 2.9 Dynamic Version Selection & Dev Tracking
- `nfclaw run <name> --pipeline-version X.Y.Z`: Materializes the requested release tag as a git worktree in `pipelines/<name>/.versions/<tag>/`. Skill documentation is generated dynamically on demand.
- `nfclaw run <name> --pipeline-version dev`: Resolves nf-core's `dev` branch to its current remote head commit and materializes an immutable worktree in `.versions/dev-<commit12>/`. Caches heads locally for offline fallback.

### 2.10 Chaining Engine (`runner/chain.py`)
- Runs multi-pipeline workflows sequentially, passing outputs from stage $k$ to inputs of stage $k+1$.
- **Chain Locking:** Locks `<outdir>/chain/.lock` against concurrent chain execution.
- **Preflight Configuration Probe:** Runs `nextflow config` under each stage's engine before
  launching stage 1. Parser failures, unavailable engines and inconclusive probes stop the chain.
- **Handoff Output Verification:** Validates upstream output bytes and complete recorded namespaces before constructing downstream inputs; inherited local references also require producer input evidence.
- **Lineage Verification:** `nfclaw chain status` checks recorded stage identities, live stage
  outputs, and handoff files/references against upstream and downstream checksum inventories.
  This checks the recorded links; it does not independently revalidate every original input,
  configuration or algorithm, or authenticate a bundle against deliberate rewriting.
  `--quick` reports execution state without hashing data and explicitly leaves lineage unchecked.

---

## 3. `handoffs/` — Chaining Rules

Chaining rules live in `handoffs/<upstream>/<downstream>.json`. They describe how to transform an upstream stage's outputs into a downstream stage's parameter inputs:
- **Declarative Mappings:** Source types include `samplesheet`, `build`, `file`, and `upstream_param`.
- **Transformations:** Row- and column-level adaptations including `rename`, `set`, `add_empty`, `drop_rows_not_allowed`, `allowed_values`, and `require_values`.
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

### Complete environment verification

`nfclaw verify REPLAY --against ORIGINAL --require-environment` requires complete matching recorded
environment evidence even if output structure alone agrees. It refuses missing records, unknown
engine builds/runtimes/platforms/container engine versions, absent process or image identities,
containerless tasks, missing plugin/remote inventories, recording issues and refetched validation
inputs. Engine build/runtime, host platform and process inventories must agree as well as the
container/plugin/remote comparisons. Combine it with `--strict` to also require output byte identity.
This checks declared recorded evidence; it does not discover undeclared task downloads or prove
continuous input immutability. The legacy default and `--strict` retain their existing behavior.
