# nf-claw architecture

How the repository and the `nfclaw` runner are put together. nf-claw takes its parameter
documentation and its general input validation from each pipeline's own `nextflow_schema.json` and,
where there is one, its input schema (`assets/schema_input.json`). Handoff rules and documented
compatibility adjustments add to those schemas. The pinned pipeline remains the authority for its
analysis and for the complete validation it runs at launch.

---

## Navigation

[Overview](#overview) • [pipelines/](#1-pipelines-the-library) • [runner/](#2-runner-the-nfclaw-command) • [Module map](#module-map) • [Preflight](#21-preflight) • [Provenance](#25-provenance-bundles) • [Replay](#26-replay-and-the-replay-guard) • [Verification](#27-verification-nfclaw-verify) • [Assessment](#28-scientific-assessment-nfclaw-assess) • [Chains](#210-chains) • [handoffs/](#3-handoffs-chaining-rules) • [librarian/](#4-librarian-maintenance)

---

## Overview

The repository has four parts:

- `pipelines/`: the pinned pipelines (git submodules) and their generated skills;
- `runner/`: the `nfclaw` command, which validates, launches, records, replays and chains runs;
- `handoffs/`: the rules that turn one pipeline's outputs into the next one's inputs;
- `librarian/`: the maintenance code that generates the skills and catalogs and tracks releases.

Around them, `scripts/` holds the acceptance gate and the validation helpers CI runs, `.github/` the
[workflows](compatibility.md#continuous-validation), and `website/` the
[website](../website/README.md) built from all of it.

---

## 1. `pipelines/`: the library

Each pipeline lives in `pipelines/<name>/`:

| Path | What it is |
|---|---|
| `upstream/` | A git submodule at the commit of an nf-core release tag. Never edited. |
| `skill.md` | Short instructions for an agent, generated from `nextflow_schema.json`: description, tools (from `CITATIONS.md`), run commands, required parameters, the schema's parameter groups and chaining. |
| `reference.md` | Every parameter with its type, whether it is required or hidden, its pattern, allowed values and default. |
| `.versions/` | Git worktrees for other releases and `dev` commits, created on demand and ignored by Git. |

The drift gate regenerates `skill.md` and `reference.md` from the pinned schemas and compares them
with the committed files. That catches stale generated files; it does not show that a schema
describes everything the pipeline's code does.

---

## 2. `runner/`: the `nfclaw` command

The runner validates inputs before launch, runs pipelines in isolation, records provenance and runs
chains. `nfclaw mcp` (`runner/mcp_server.py`, `runner/mcp_tools.py`, `runner/jobs.py`) offers the same
commands to MCP clients and runs runs and chains as detached jobs ([mcp.md](mcp.md)).

### Module map

| Concern | Modules in `runner/` |
|---|---|
| Command line | `cli.py`, `__main__.py`, `discovery.py` (finding pipelines), `version.py`, `errors.py` |
| Preflight | `preflight.py`, `schema.py`, `parameters.py`, `inputs.py`, `samplesheet.py`, `sheetgen.py`, `input_safety.py`, `path_roles.py`, `exact_json.py`, `config_probe.py`, `engine_version.py`, `resources.py` (`--limit-*`), `settings.py`, `reproducibility.py` |
| Pipeline source | `submodule.py`, `versions.py`, `source_identity.py`, `source_corrections.py`, `fastqrepair_compat.py`, `plugin_compat.py`, `demo_defaults.py`, `institutional.py` |
| Execution | `orchestration.py`, `nextflow_command.py`, `execution.py`, `locking.py`, `probes.py`, `budget.py`, `process_identity.py`, `container_watch.py`, `runlog.py`, `outputs.py`, `atomic.py` |
| Provenance and replay | `provenance.py`, `replay_guard.py`, `environment_record.py`, `dependency_stability.py`, `resume_safety.py`, `redaction.py` |
| Verification and assessment | `verify.py`, `scientific.py`, `scientific_hts.py`, `scientific_h5ad.py` |
| Chains | `chain.py`, `handoff.py`, `consumption.py` |
| MCP and jobs | `mcp_server.py`, `mcp_tools.py`, `jobs.py`, `job_reports.py`, `foreground.py` |
| Reference preparation | `dramp.py` (`nfclaw prepare-dramp`) |

`replay_guard.py`, `environment_record.py` and `source_identity.py` are also copied into each
provenance bundle, so a replay's checks need neither nfclaw nor any Python package
([what a replay still needs](replay.md#what-the-bundle-carries)).

### 2.1 Preflight

`nfclaw run --check` lists the checks it completed, those deferred to launch and those it does not
support; a real run records the detailed `validation_scope` in its manifest. The
[preflight guide](preflight.md) describes the supported schema subset and which pipelines the
samplesheet generator supports, including how generated and hand-written tables and JSON/YAML inputs
differ.

Before it starts Nextflow, `nfclaw run` runs these checks (`runner/preflight.py`, `runner/schema.py`,
`runner/parameters.py`, `runner/inputs.py`):

- Unknown and misspelt flags are refused.
- Scalar types, booleans, numeric bounds and allowed values are checked.
- When `--input` names data files (a directory, a glob, or files given with `--input` once each)
  where the pipeline expects a samplesheet, `runner/sheetgen.py` writes the sheet from the pinned
  input schema, including declared alternative formats and the source annotations in
  `runner/input_roles.json`. Typed columns take the files that match their patterns. FastQ mates
  pair by `_R1`/`_R2`, or by `_1`/`_2` when their read names show they come from one molecule.
  Sample names are the file names, unaltered, and values no file determines come from `--sheet-set`
  or the schema's defaults. Gaps and ambiguities are refused, and the stale HGTseq and Nanoseq
  contracts need a sheet written by hand. The generated sheet then goes through the same checks as a
  hand-written one. It is staged beside `params.json` and named on the command line (so a moved
  bundle replays its own copy), recorded with the configs, and its data files are recorded as inputs.
- A samplesheet must exist and have the expected header, required fields and path formats.
- `--input` is resolved against the caller's working directory. Local data paths inside a
  samplesheet must already be absolute; relative ones are refused.
- `--input false` becomes an unset `input` in `params.json` for pipelines that can run without a
  samplesheet (such as sarek), so nf-schema's type check does not fail on it.
- A pinned `upstream/` that is not at the commit its `skill.md` names is refused, and so is any tree
  (pin, release cache or `dev` commit) with local edits to tracked files, so provenance never names
  code that did not run.
- `--limit-*` is refused when the run's engine is older than Nextflow 24.04.0 or cannot be
  identified, because older engines ignore `process.resourceLimits` without a warning.
- `runner/reproducibility.py` scans the pinned task scripts for known sources of run-to-run
  variation (dada2 `assignTaxonomy` tie-breaking, unseeded QIIME2 rarefaction) and announces them
  before launch unless those steps are skipped. It also announces workflow code that reorders, in
  place, a list Nextflow hands to several processes at once (createtaxdb 3.1.0's sourmash step) when
  that step runs.
- With `--check` only, `runner/config_probe.py` asks the run's engine, with its `--nxf-ver`,
  `--nxf-env` and every `-c` (generated ones included), to resolve the pipeline's configuration and
  selected profiles with `nextflow config`, from a scratch directory. A release that engine cannot
  parse (an older one under Nextflow 26.04's strict parser) is refused with the engine or parser to
  use instead, and `profile_config` is reported as checked.
- Errors carry an `ErrorCode` and a suggested fix. The pinned pipeline's own validation stays
  authoritative for conditional and complex constraints; releases use different validation plugins.

#### What is left to Nextflow and the pinned release

Every pinned release checks itself at launch, before any task runs. Nextflow enforces the manifest's
`nextflowVersion`, which every pinned release states in the strict `!>=` form. The release's
validation code checks every parameter and samplesheet against its schemas: nf-schema, nf-validation
in older releases, or the `NfcoreSchema` library of the oldest template. nfclaw does not repeat a
check whose result Nextflow or the release produces just as early:

- **Engine version:** a launch does not probe for it. When Nextflow refuses an older engine, nfclaw's
  error names the `--nxf-ver` to pass, and `skill.md` states the declared engine. `--check` warns
  about it, because `nextflow config` does not enforce it.
- **Java:** nfclaw looks for it where the Nextflow launcher does (`NXF_JAVA_HOME`, `JAVA_HOME`, then
  `PATH`). The launcher checks the version.
- **Profile values, conditional and nested schema constraints, remote files:** Nextflow and the
  plugin judge them at launch; `--check` has the engine parse the configuration first.
- **Analysis results:** each release's nf-test snapshot is what nf-core's CI checks. nf-claw's demo
  validation compares its runs with that snapshot instead of re-deriving the tools' output.

nfclaw keeps its own schema checks where they act before Nextflow could:

- `--check`, a chain's `--check` and the MCP `run_pipeline(check=true)` never launch pipeline tasks:
  Nextflow runs only to report its version (`nextflow -version`) and resolve the configuration
  (`nextflow config`).
- A chain validates every stage before the first one launches. Otherwise a later stage's own
  validation would run only after the stages before it have finished.
- Unknown parameters are refused. nf-schema only warns about them by default, because institutional
  profiles may set extra parameters, so a mistyped flag would run with its default.
- Declared local samplesheet paths must be absolute and identifiers shell-safe. A real run hashes its
  local dependencies before launching Nextflow from `--outdir`; `--check` inspects paths without
  confirming that every data file can be read. Implicit, transitive and remote dependencies keep the
  limits described in the [preflight guide](preflight.md).

### 2.2 Launch and output locking

- Nextflow is launched from `--outdir`, so its `.nextflow/` history and session databases belong to
  that run. Task work files go to the shared `<repo>/work/` by default; `NXF_WORK` chooses another
  location and is resolved against the caller's working directory before launch.
- On POSIX systems, `runner/locking.py` takes an exclusive, non-blocking lock on a file beside the
  output directory (`.{outdir.name}.nfclaw.lock`) before it creates or changes `--outdir`. A second
  run into the same directory fails at once with `ErrorCode.ENVIRONMENT` instead of corrupting the
  first run's session or interleaving its logs.
- For the Docker profile, `runner/preflight.py` checks that the daemon answers `docker info`, waiting
  up to `NFCLAW_DOCKER_TIMEOUT` seconds (default 60, and never past `--timeout`) so a busy runner is
  not mistaken for a missing daemon.
- `--check` stages parameters in temporary directories and never writes into `--outdir`. Resolving a
  requested pipeline version may fetch tags or fill its version cache.

### 2.3 Stopping a run

- `runner/execution.py` traps `SIGTERM`, `SIGHUP` and `SIGINT` (Ctrl-C).
- On a stop signal, nfclaw signals Nextflow's process group, captures its last output, and tries to
  record the outcome and the provenance before it exits.
- Nextflow gets 10 seconds to shut down (`NFCLAW_SHUTDOWN_GRACE` changes this). A run has no overall
  deadline unless `--timeout SECONDS` is given; see [timeouts](timeouts.md).
- Task containers belong to the container engine, not to the process group. Before each signal,
  nfclaw notes the `nxf-…` containers that the group's `docker run`/`podman run` clients started;
  once the group is gone it force-removes those still present and says so in the run log
  (`replay_guard.task_containers`; a replay's supervisor does the same).
- On Linux, `PR_SET_PDEATHSIG` signals the direct Nextflow child if nfclaw dies abruptly. That alone
  does not clean up detached processes or remote tasks.

### 2.4 Logs and status

- `<outdir>/provenance/logs/run.log` is the authoritative log: nfclaw's launch details (command,
  pid, host, advisories), then Nextflow's console output.
- Its last line, written when nfclaw is done, is `==> nfclaw run finished <timestamp>: <outcome>`.
- `stdout.txt` and `stderr.txt` beside it keep Nextflow's two raw streams.
- `nfclaw status <outdir>` reads `run.log` and, for an unfinished run on the same host, checks the
  recorded process identity. It reports `success`, `running`, `failed`, `terminated` or
  `stopped without an outcome`. An unfinished run on another host cannot be inspected locally, and
  a log that exists but cannot be read is reported as `unknown` with the reason (exit status 1).
- A pipeline can exit 0 without some samples or tasks. `runner/runlog.py` quotes what it reported
  (nf-core's "…, but with errored process(es)", rnaseq's skipped samples) and Nextflow's count of
  ignored task failures. `nfclaw run` prints them, `nfclaw status` reports
  `success — with caveats …`, and the manifest records them as `completion_caveats`.

### 2.5 Provenance bundles

Every run, failed ones included, tries to record a provenance bundle in `<outdir>/provenance/`. Each
record is replaced atomically and the manifest is written last. A run that cannot record its bundle
does not report success, and the replay guard refuses an incomplete bundle.

| File | What it records |
|---|---|
| `logs/run.log` | The whole launch in order, ending with its outcome line ([2.4](#24-logs-and-status)); `stdout.txt` and `stderr.txt` beside it keep Nextflow's raw streams. |
| `run_manifest.json` | Pipeline name, version, commit, command, recording time, outcome, the engine observed, operating system, the nfclaw that wrote the bundle (`nfclaw`: package version and checkout commit, as `nfclaw --version` prints them), and the active `NXF_*` variables with secrets redacted. Host and process identity are in `logs/run.log`. `pipeline_archive`, `bundled_configs`, `container_pins` and `execution_environment.issues` show what evidence was actually captured. |
| `params.json` | The parameters passed to Nextflow, including the pinned `trace_report_suffix` where the schema supports it and the nf-core/configs commit (`custom_config_version`) when it is pinned automatically. The pipeline can record further defaults or profile values itself, and other timestamped metadata can still change file names. |
| `commands.sh`, `replay_guard.py`, `environment_record.py` | The replay script and its two dependency-free helpers ([2.6](#26-replay-and-the-replay-guard)). |
| `inputs.sha256` | Digests, taken before launch, of declared local input files, schema path parameters, existing absolute local files given to parameters without a path format, and local data paths inside CSV/TSV or flat JSON/YAML records, auxiliary tables included. |
| `outputs.sha256` | Digests of the published result files, without provenance and Nextflow state. |
| `pipeline.sha256` | Digests, taken before launch, of the tracked pipeline source files. |
| `pipeline-source.tar.gz` | A reproducible archive of exactly those source files (fixed owner, time and mode, sorted, gzip without a timestamp). A replay runs the recorded checkout while it still holds exactly this source; otherwise it extracts and checks the archive and runs that copy (`<target>/provenance/pipeline-source.json` says which). |
| `configs/` | Copies of the external `-c` configuration files, listed in the manifest's `bundled_configs`. A replay passes the copies; a config that uses `includeConfig` replays from its original path. |
| `environment.json` | The execution evidence available: process and container records, image identities (Docker/Podman registry digest, image ID and platform, or a Singularity/Apptainer file's SHA-256), Nextflow build, container engine version, plugins, Java runtime and the hashes of remote inputs found in the logs. Missing evidence is recorded as unresolved entries or `issues`. Its digest is in the manifest (`environment_record`), with a summary under `execution_environment`. |
| `containers.config` | When possible, a Nextflow config that pins eligible Docker/Podman processes (by fully qualified `withName`) to their recorded registry digests. `commands.sh` passes it last. File-based images, unresolved or multiple images, a mix of tasks with and without containers, and temporary Wave references get no pin. |
| `configs.sha256` | Digests of the params file, the generated configs and the external configuration files passed with `-c`. |
| `inputs.inventory.json`, `configs.inventory.json` | The dependencies' directory listings, empty directories, entry types and link identities, taken before launch and checked along with the file bytes. |
| `outputs.inventory.json` | The published outputs' directory listing, used by replay verification and handoff checks. |
| `launch-record.json` | Written before Nextflow starts and removed when the manifest is written: the pipeline source identity and the input bytes and listing of this launch, which `--resume` compares against when nfclaw vanished without writing a manifest. |
| `resource_limits.config` | The resource ceilings, when `--limit-*` is used. |
| `nf_schema_compat.config`, `fastqrepair_compat.config` | Plugin adjustments and recorded task corrections, when they apply. |

The checksum files escape file names the way GNU tools do, so backslashes and Unicode separators keep
their identity.

A missing local path parameter without an `exists: true` constraint is left to Nextflow, because it
may be an output or cache destination. It produces a warning and an `unverified_local_paths` entry in
the manifest instead of a misleading input checksum; a required input that is missing is refused.
Remote data found in Nextflow's staging logs is hashed after the run and compared after a replay.
Files that tasks download themselves, references set only by a profile, the `includeConfig` targets
of a user config, Conda environments and data referenced by non-tabular input formats are not all
frozen. Supported table URLs that are only used for validation are fetched again after the run (up
to 100 MiB); that hash describes the refetched bytes, not the bytes validation read. Identities that
cannot be established stay unresolved.

`runner/institutional.py` pins the release's default nf-core/configs branch to a commit when the
schema declares `custom_config_version` and the config uses the usual nf-core URL. An explicit
`custom_config_version` or `custom_config_base`, or a non-empty `NXF_OFFLINE`, turns this off, and a
resumed run reuses the commit it recorded. The resolved commit is passed in `params.json` and
recorded under `institutional_configs`; if resolution fails, an advisory says so and the release's
default stays. Other config includes are not resolved.

`runner/path_roles.json` lists directory parameters shown, at exact upstream commits, to be output
only. They are used only when the pipeline identity matches, the directory schema is unchanged and
the source checkout is clean and matching. Such destinations keep their file name checks and
parameter checksums, but unrelated files already inside them are left out of input inspection and
snapshots. Unlisted paths, other releases and reused `storeDir` caches keep their input checks.
Audited parameters passed whole to a shell also have their parent folders and resolved symlinks
checked.

Before `--resume`, the declared local inputs are compared with the previous run's byte and listing
snapshots (from the manifest, or from the launch record when no manifest was written). If nothing
changed, the cache is reused. If data changed or the previous listing is unavailable, the whole
previous run is archived in `<outdir>.previous-<id>` and a fresh cache session starts; the earlier
logs are copied forward. This also applies with `--no-provenance`.

Before reporting success, nfclaw checks the declared local inputs, configurations and tracked source
against their launch snapshots. A dependency that changed or cannot be read fails the run and is
reported in the manifest's `dependency_stability` record. These checks also run with
`--no-provenance`. A change that is undone between two checks, and remote or indirectly configured
dependencies, are outside their scope.

Archiving prepares the replacements before it moves the run, keeps ordinary relative links, rebases
links that go through output directory aliases and external publications, and rolls back failures
and cancellations it can recover from. A verified result inventory is rebased together with its
publication links, so the archive keeps its file checksums and its logical listing.

### 2.6 Replay and the replay guard

- `provenance/commands.sh` re-runs the recorded run (same pinned code, local inputs, parameters,
  configs and engine) into a fresh output directory, `<outdir>.replay` by default. Replaying into the
  original directory is refused, because published files would collide. A replay reproduces outputs
  only as far as the tools are deterministic: a multithreaded or unseeded step can give different
  results from identical inputs (measured for ampliseq 3.0.0, see
  [known issues](known-issues.md#pipeline-specific-run-notes)). Compare replays with `nfclaw verify`
  and inspect changed files with tools that understand their format.
- `commands.sh` runs the recorded checkout while its git revision and tracked bytes still match
  `pipeline.sha256`, which keeps paths derived from `${projectDir}`. Otherwise it extracts
  `pipeline-source.tar.gz` into `<target>/provenance/pipeline`, checking each file, and runs that
  copy. It passes the replayable config copies and, when present, `containers.config`. Extracting
  the archive changes `${projectDir}`; absolute paths already stored in the parameters are not
  rewritten. Local input data and configs that use `includeConfig` still depend on files outside the
  bundle.
- `provenance/environment_record.py` is a copy of `runner/environment_record.py` with no
  dependencies. After a replay's Nextflow succeeds, `commands.sh` runs it to write
  `<target>/provenance/environment.json` and `environment_check.json`. A different image digest,
  plugin set, container engine or staged remote file then fails the replay; entries that cannot be
  decided are reported as unverified.
- `provenance/replay_guard.py`, also dependency-free, runs before Nextflow. It checks that the local
  inputs, referenced samplesheets, configs (the bundled copies where recorded), the archived pipeline
  source (or, for bundles older than the archive, the checkout's commit and tracked bytes) and the
  recorded `environment.json` and `containers.config` still match the bundle's digests. If anything
  changed or disappeared, the replay stops.
- `commands.sh` finds the bundle directory it is in and rebases the bundle's own parameters,
  configs, config copies, pins and source archive, so a moved bundle still works. External input
  data keeps its recorded paths.

The archive is checked before and after the run. When the replay uses the original checkout, its
revision and tracked bytes are checked again at the end. An extracted source tree is checked when it
is created and hashed again against the source manifest afterwards. The replay target gets its own
logs and source and environment records; the original bundle stays the entry point and the reference
for dependency and output checks.

### 2.7 Verification (`nfclaw verify`)

- `runner/verify.py` compares the replay's output files with the original run's, by path.
- It separates the file inventory from byte equality. Timestamped metadata files in `pipeline_info/`
  are paired by name pattern, keeping their number and reporting byte changes. Directory inventories
  are compared too; an older file-only manifest cannot confirm directory structure.
- Some tools write files with random names, such as `kraken2-build --add-to-library` in createtaxdb
  (`XXXXXXXXXX.fna`, `.fna.masked`, `prelim_map_XXXXXXXXXX.txt`). `runner/verify.py` pairs exactly
  these names one to one within their directory, lists them under `renamed` and compares their
  bytes, instead of reporting them as missing and extra.
- `--strict` requires every paired file, metadata included, to be byte-identical, and the recorded
  link identities to agree. When both `environment.json` records are readable JSON objects, the
  environment comparison must also be `identical`; `differs` and `unverified` fail. Otherwise the
  report says `not recorded by both runs` and no environment condition applies.
- The environment comparison covers the container engine, the loaded plugins, the images of
  processes present in both records, and the recorded remote-input URLs and hashes. A different Java
  runtime, or processes present on only one side, are reported as notes. The Nextflow build,
  container engine version, host platform and task counts are recorded but not compared for
  equality. Without `--strict`, these findings are reported but do not change the result; a
  standalone replay fails on a detected mismatch but accepts `unverified`.
- An `identical` verdict covers only the evidence compared. Read `issues`, `unverified` and `notes`
  too: missing task or staging records are not always detected, and the verdict does not show that
  every dependency was captured.
- `--require-environment` requires complete, matching environment evidence even when the outputs
  agree. It refuses missing records, an unknown engine build, Java runtime, platform or container
  engine version, missing process or image identities, tasks without a container, missing plugin or
  remote-input inventories, recording issues and refetched validation inputs. The engine build, Java
  runtime, host platform and process inventories must agree, in addition to the container, plugin and
  remote-input comparisons. Add `--strict` to also require identical bytes. This checks the evidence
  that was recorded; it does not find downloads a task made on its own or prove that inputs never
  changed. The default and `--strict` modes are unchanged by it.
- Matching inventories say nothing about analytical agreement, and matching bytes show only that
  these files agree, not that they are biologically correct or reproducible elsewhere.

### 2.8 Scientific assessment (`nfclaw assess`)

`runner/scientific.py`, `runner/scientific_hts.py` and `runner/scientific_h5ad.py` check a run's
outputs against an explicit contract (`runner/output_contracts/*.json`). Supported formats:

- `table`: an exact, unique header; unique row keys; numeric comparison in exact decimal arithmetic;
  sample columns or expected sample membership; and declared column exclusions (`ignore_columns`).
- `fasta`: unique identifiers, exact sequences and descriptions (case kept), sequence counts,
  lengths and N50.
- `bam`: 0-based half-open coordinates, alignments, unmapped and duplicate reads, flags, CIGAR,
  positions, mate fields, qualities, tags, read-group sample labels and a canonical header digest.
- `vcf`: 1-based closed coordinates, variants decoded with HTSlib, INFO and FORMAT fields, genotype
  phase, sample columns, and GATK's strand count encoding (`INFO/AS_SB_TABLE`).
- `h5ad_matrix`: dense, CSR or CSC matrices compared by cell and gene identity, with integer and
  non-negative checks.

On its own, `nfclaw assess` checks that the declared outputs exist and meet the contract's
expectations. With `--against ORIGINAL`, it also compares them with the original run's files, which
must first match their recorded `provenance/outputs.sha256`, using the contract's exact tolerances.
It prints a JSON report (verdicts, parsed record counts, the reason for each tolerance, files not
assessed) and exits non-zero if any expectation is not met. See the
[output contract guide](scientific-output-contracts.md).

### 2.9 Other releases and `dev`

- `nfclaw run <name> --pipeline-version X.Y.Z` checks out that release tag as a git worktree in
  `pipelines/<name>/.versions/<tag>/` and generates its skill documentation on demand.
- `nfclaw run <name> --pipeline-version dev` resolves nf-core's `dev` branch to its current commit and
  checks it out in `.versions/dev-<commit12>/`. The last head fetched is kept for offline use.

### 2.10 Chains

`runner/chain.py` runs pipelines one after another, building each stage's inputs from the outputs of
the stage before.

- `<outdir>/chain/.lock` prevents two chains from running in the same directory.
- Before stage 1 starts, `nextflow config` runs under each stage's engine (`runner/config_probe.py`,
  shared with `nfclaw run --check`). A parser failure, a missing engine or an inconclusive probe
  stops the chain.
- Before it builds the next stage's inputs, the chain checks the previous stage's output bytes and
  its complete recorded listing. References inherited from an earlier stage also need that stage's
  input evidence.
- `nfclaw chain status` checks the recorded stage identities, the stage outputs as they are now, and
  the handoff files and references against the upstream and downstream checksum inventories. This
  checks the recorded links; it does not revalidate every original input, configuration or
  algorithm, and it cannot detect a bundle rewritten on purpose. `--quick` reports progress without
  hashing data and says that lineage was not checked.

---

## 3. `handoffs/`: chaining rules

A chaining rule, `handoffs/<upstream>/<downstream>.json`, describes how to turn an upstream stage's
outputs into a downstream stage's parameters:

- Sources can be `samplesheet`, `build`, `file` or `upstream_param`.
- Row and column transformations include `rename`, `set`, `add_empty`, `drop_rows_not_allowed`,
  `allowed_values` and `require_values`.
- Rules for assembly pipelines such as `mag` give every sample its own group (`group: {sample}`) so
  that samples are not co-assembled by accident.
- The drift gate checks every rule against the pinned schemas of both pipelines.

The format is specified in [chaining](chaining.md).

---

## 4. `librarian/`: maintenance

| Module | Run by | What it does |
|---|---|---|
| `write_skill.py` | `make build` | Generates `skill.md` and `reference.md` from `nextflow_schema.json` and `assets/schema_input.json`. |
| `write_catalog.py` | `make build` | Builds `catalog.json` and `catalog.md` from all pipelines. |
| `add_pipeline.py` | `make add` | Prints the `.gitmodules` entries and `git submodule add` commands for every pipeline in `sources.tsv`; changes nothing itself. |
| `check_drift.py` | `make check` | Checks that `sources.tsv`, `.gitmodules`, the `pipelines/` directories, the skills, the references and the handoff rules all agree. |
| `update_pipelines.py` | `make update` | Finds newly published release tags and bumps the submodules. |
| `discover_pipelines.py` | `discover-pipelines.yml` | Finds newly published DSL2 nf-core pipelines and adds their submodules. |
