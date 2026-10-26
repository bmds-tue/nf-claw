# nf-claw — nf-core pipelines for agents

This repo is a library of nf-core pipelines. Each lives in `pipelines/<name>/`:
`upstream/` (the pinned pipeline code, a git submodule) and `skill.md` (how to run it).

---

## Setup (first time)

Install once, from the repo root, so the `nfclaw` command is on PATH:
```bash
pip install -e .
```
(Use a virtualenv on a space-free path; on macOS also avoid iCloud paths).
Use Python 3.11+ for both installation and the no-install command. For maintenance
tests, install `pip install -e ".[dev,yaml]"` to include pytest and YAML support.

**No-install equivalent:** run `python3 -m runner <cmd>` from the repo root anywhere this doc shows `nfclaw <cmd>`.

---

## To run a pipeline

1. **Find it:** grep `catalog.json` (or `catalog.md`) for a keyword — do NOT read it whole.
2. **Read `pipelines/<name>/skill.md`:** the exact command, inputs, and required parameters for the pinned version.
3. **Run:**
   ```bash
   nfclaw run <name> --input samplesheet.csv --outdir results -profile docker
   ```
   *(Direct upstream command: `nextflow run pipelines/<name>/upstream -profile docker ...` — the submodule is already pinned to the release, so no `-r`. This bypasses nfclaw's preflight, provenance and runtime corrections; use nfclaw for releases that need those corrections.)*
4. **Check status (foreground or background):**
   ```bash
   nfclaw status results
   ```
   Prints `success`, `running`, or how it ended with the error (exit codes: `0` success, `3` running, `1` failed). Logs: see [Where a run is logged](#where-a-run-is-logged--and-how-to-check-one).

> [!NOTE]
> `nfclaw run` executes the pipeline for real — there is no preview/dry-run default. To see the exact `nextflow` command that *would* run without launching it, add `--check` (it validates inputs and parameters, prints the command — prefixed with the `NXF_*` variables `--nxf-ver`/`--nxf-env` set for it, e.g. `NXF_VER=25.10.4 nextflow run …` — and exits; it writes nothing into `--outdir`, so you can still use that directory for the real run). Add `--demo` to run the pinned release's bundled test profile end to end. A run has no overall time limit unless you pass `--timeout SECONDS`.

`--check` also checks environment requirements and can initialize submodules, fetch
requested versions and probe Nextflow; conditional and complex constraints remain
subject to upstream runtime validation. Docker is the default profile; `-profile` /
`--profile` accepts comma-separated profiles. `--params-file PATH` loads JSON (or
YAML with the `yaml` extra), and explicit CLI values override file values. Pipeline
flags accept hyphens or underscores; raw Nextflow requires their exact schema spelling.
Output directories must be outside the repository or ignored by Git (`results/` is
ignored). Supply the references the selected analysis needs, even when its schema
does not mark them required; each skill's reference section explains the options.
`--no-provenance` disables the replay bundle and checksum records, while retaining
the parameter file and run logs required for execution and status inspection.

> [!IMPORTANT]
> **Run Concurrency Locking:** On POSIX systems, `nfclaw run` holds an exclusive non-blocking sibling lock (`.{outdir.name}.nfclaw.lock`) around the run. Overlapping or concurrent runs into the same `--outdir` fail fast with an environment error, preventing race conditions or output corruption. Before creating that lock or any run files, explicit local dependencies and samplesheet data paths are checked against output, work, engine-state and log destinations. Keep execution writes outside consumed directories, including nested aliases and directory glob matches; keep data, pipeline code and configuration outside the output tree. Chain preflight also checks its whole output tree before writing its record. Existing output aliases and hard-linked files are inspected too: a different pathname does not establish different data. Declared work/cache trees retain their staged-read policy; input slots within output trees remain protected even when their symlinks point outside. Boundary refusals preserve input files, directory entries and existing logs.

> [!TIP]
> **Absolute Paths in Samplesheets:** Write **absolute paths inside a samplesheet**: Nextflow resolves them against its launch directory, which `nfclaw run` sets to `--outdir`, so a relative one cannot mean what it says — `nfclaw run` rejects it before launching. `--input` itself may be relative (nfclaw makes it absolute), and it is not always a samplesheet: the pipeline's schema decides — a directory or tarball (rangeland), an SDRF file or PRIDE accession (mhcquant), or `--input false` where a pipeline documents running without one (sarek — nfclaw intercepts it and leaves `input` unset in the params file, avoiding nf-schema type errors). The `Inputs` section of `skill.md` says which.

> [!TIP]
> **No samplesheet yet? Pass the data files.** Where `--input` is a samplesheet, it may instead name the data files — a directory (searched recursively, hidden entries skipped), a quoted glob, or files (`--input` once per file) — and `nfclaw run` generates the samplesheet as its first step: `nfclaw run rnaseq --input /data/fastq --sheet-set strandedness=auto --outdir results`. The pinned schema decides the columns: sample names come from file names (never altered — a name the pipeline cannot take is refused), FastQ mates pair by `_R1`/`_R2` (an advisory flags first read names that disagree), and by `_1`/`_2` only when their first read names show they are mates, Illumina lane numbers fill a `lane` column, other typed columns (BAM, FASTA, …) take files matching their patterns by sample name. Values no file determines come only from `--sheet-set COLUMN=VALUE` (repeatable; a constant or a `{sample}`/`{lane}` template; an empty value leaves a column empty, which is also how to choose between read-column groups) or the schema's defaults — the `Inputs` section of `skill.md` lists which. Missing values, ambiguous or stray files, orphan mates and duplicates are refused before anything is written. Add `--check` to see the sheet first. It is staged as `<outdir>/provenance/samplesheet.csv`, recorded with the configs (its data files as inputs), and replayed as recorded — a replay never re-scans the directory; `--resume` regenerates it and says which samples changed. A chain stage takes the same `input` plus a `"sheet_set"` object; resuming refuses a succeeded stage whose data now holds files it never analysed (removed data is fine).

> [!IMPORTANT]
> **Input filenames:** Explicit local and remote input path fields and schema-declared path parameters are checked for filenames that pinned tasks could interpret as shell syntax. Unsafe staged basenames (including literal wildcards, whitespace, shell operators and leading `-` or `~`) are refused; choose a safely named copy rather than renaming a scientific sample. Local directories and directory glob matches are inspected recursively, including empty subdirectories; unreadable entries, broken links and cycles are refused. Symlink targets and local glob matches receive the same name check. Unicode letters, digits and combining marks and literal `._-+@%=,:~` characters remain supported (with `~` only internally). Nextflow preserves percent escapes in remote basenames; nfclaw preserves them too. HTTP/FTP query suffixes are excluded from the staged name; standalone fragments remain literal filename characters. Object-store keys such as S3 retain query and fragment characters and receive the literal-name check. Parent directory names are not staged as the input basename, but LF/CR in local input paths or resolved targets are refused because Nextflow can turn them into shell lines. Samplesheet paths crossing a directory symlink with `..` must use an explicit absolute parent: Nextflow's lexical normalization may select different data. Ordinary parent traversal is supported; wildcard parents followed by `..` are refused before resolution. URI schemes must start the value, so a local colon parent remains a checksummed local dependency. The separate run-directory space check still applies, and `--allow-spaces` cannot permit LF/CR in launch, output or work paths. Local `file:` URI inputs must be written as absolute filesystem paths so the same filename and replay-dependency checks apply. Values supplied indirectly through configs/profiles, remote glob inventories and remote file contents remain subject to upstream validation.

Audited output-only directory parameters retain basename checks while excluding unrelated
existing children from input snapshots. These roles are declared in `runner/path_roles.json`
for exact clean source revisions, never inferred from names or descriptions. Whole-path
arguments in audited task scripts also validate parent folders and resolved symlink paths.
HTTP/HTTPS/FTP basenames remain literal even in schema-declared file patterns; object-store
patterns retain their upstream expansion semantics.

> [!IMPORTANT]
> **Sample identities:** Metadata identifiers (`meta.id`, patient/sample IDs, genome/database names and legacy sample/patient columns) must start with a letter, digit or underscore and contain only letters, digits, combining marks, dots, underscores or hyphens. Upstream tasks use these values in shell commands and filenames. Choose explicit safe aliases for other identifiers; nfclaw never silently renames scientific samples. This preflight applies to CSV/TSV and flat JSON/YAML records; YAML requires `pip install -e ".[yaml]"`. Local path fields in these records must be absolute, including glob patterns, and their content is included in replay dependency checks. Explicitly supplied auxiliary tables such as `--genome-sheet` and `--databases` receive their own schema validation and local-data dependency checks too. Values supplied by profiles/configs and future chain handoffs are validated by Nextflow when available. Nested input structures remain subject to the pinned nf-schema validation.

> [!IMPORTANT]
> **Recorded runtime corrections:** The exact affected fastqrepair 1.1.1 commit receives `provenance/fastqrepair_compat.config`: a splitter whose chunks wipe exactly as the whole file, exact report gathering, the missing BBMap shell continuation and distinct read/log/report publication. The complete standalone implementation and its source digest are recorded for replay; internal recipe prefixes invalidate prior task caches. The pinned source tree remains unchanged, while generated task scripts explicitly incorporate these corrections. Input with no line where a split is invisible to fastqwiper is wiped whole beside an empty placeholder chunk. Inspect actual task `.command.sh` files and retained read/report inventories; process success alone does not establish read conservation or biological accuracy.

---

## Where a run is logged — and how to check one

Every `nfclaw run` records itself at a fixed place — there is no need to redirect its output, and nothing to look up. To know how a run stands, ask nfclaw:

```bash
nfclaw status <outdir>
```

Prints `status: success`, `running (…)`, the outcome it ended with (`failed (exit status N)`, `timed out after N s`, `interrupted`, `terminated by SIGTERM`, `refused before launch`), or `stopped without an outcome` (nfclaw itself was killed with SIGKILL, ran out of memory, its disk filled up, or the machine restarted); then the log, and the recorded error or the run's last output. Exit code: 0 success, 3 running, 1 anything else. It works for replays too.

**Success is not completeness.** A pipeline can exit 0 without some of its samples or tasks. When it says so in its completion summary (nf-core's "…, but with errored process(es)", rnaseq's skipped samples and failed strandedness checks), Nextflow ignored failed tasks, or a selected profile or a `--config` runs every task as a stub that writes placeholders instead of running its tool (`stubRun = true`, as proteinfold's `test` profile does — so its `--demo` computes nothing), `nfclaw status` reports `status: success — with caveats the pipeline reported about its results` and quotes them; `nfclaw run` prints them as warnings and records them in `provenance/run_manifest.json` (`completion_caveats`), and a chain lists them per stage. Read them before using the results.

### Log Files Overview

- **`<outdir>/provenance/logs/run.log`** — The whole launch in order: nfclaw's header (command, launch directory, Nextflow log path, host and pids, advisories), everything Nextflow printed, and on failure nfclaw's error. Child-output lines are prefixed with `| ` so printed text cannot forge nfclaw's status markers; `nfclaw status` removes that prefix when displaying the output, and `stdout.txt` / `stderr.txt` preserve the raw run streams. Once nfclaw is done — the provenance bundle included — its **last line** is:
  ```
  ==> nfclaw run finished <time>: <outcome>
  ```
  `--resume` appends, so a failed attempt is never overwritten by the retry; a relaunch nfclaw refuses before starting (invalid parameters, a non-empty `--outdir` without `--resume`) is appended too, except when an unsafe input/output overlap requires leaving the input tree and its log untouched. Otherwise the last line is the latest attempt's. A refused first attempt leaves a fresh `--outdir` untouched: no run log means nfclaw never launched there — run the command in the foreground to see why.
- **`<outdir>/.nextflow.log`** — Nextflow's own detailed log. Nextflow runs from `--outdir`, so its console hint "Check '.nextflow.log'" means this file, not one in your working directory.
- **`stdout.txt` / `stderr.txt` beside `run.log`** — Nextflow's two streams kept apart. Engines through 26.04 print console error reports on stdout, with launcher notices and some validation details on stderr. From Nextflow 26.10, console logs go to stderr instead ([migration notes](https://docs.seqera.io/nextflow/migrations/26-10#breaking-changes)). nfclaw captures both; inspect both streams when diagnosing a failure.

Start a long run in the background with `nohup nfclaw run ... &` and stop it with `kill <nfclaw pid>` (the `pid:` line of the run log): nfclaw then shuts Nextflow and its tasks down, writes the bundle and closes the log, as on Ctrl-C. On Linux, parent-death signaling stops the direct Nextflow child if nfclaw is killed abruptly; detached tasks and containers still require the executor's cleanup and are not covered by that signal alone.

When a run fails, nfclaw's error quotes what Nextflow reported on stdout and stderr — plus the `Caused by:` chain from `.nextflow.log` when the console alone hides the reason (e.g. "Unable to parse config file" ← "Network is unreachable") — and names these files by absolute path, along with the failing task's `.command.err` (its `.command.log` and `.command.sh` sit beside it). `--check` launches nothing and writes no log.

---

## Replaying a run

`<outdir>/provenance/commands.sh` re-runs the recorded command. It reproduces the run into a **fresh** directory (default `<outdir>.replay`, or pass one: `./commands.sh /path/to/fresh-dir`) and refuses a target that already holds files. That is deliberate: an nf-core pipeline publishes into `--outdir` and cannot re-publish over a previous run's files, so replaying in place fails immediately on `pipeline_info/execution_trace_*.txt` (and on sarek's `manifest_*.bco.json`). A replay re-executes the pipeline — it is a reproduction, not a `--resume` — and the result can be compared against the original bundle's `outputs.sha256`. It logs itself the same way, to `<target>/provenance/logs/run.log`, ending with its outcome: `nfclaw status <target>` reads it, and `kill <replay pid>` stops Nextflow with it.

Before launching Nextflow, `commands.sh` runs `provenance/replay_guard.py` against the original bundle. The guard checks the recorded pipeline revision and tracked source bytes (`pipeline.sha256`), declared local input content including data paths referenced in samplesheets (`inputs.sha256`), and parameters and configuration (`configs.sha256`). The `inputs.inventory.json` and `configs.inventory.json` records also preserve directory entries (including empty directories), entry types and symlink identities. Changed or missing dependencies and incomplete bundles are refused, rather than producing silently divergent scientific results. Replay targets inside a recorded input directory are refused before creating their locks or logs. New replay bundles acquire the same output-directory writer lock as `nfclaw run`, so overlapping runs and replays cannot write into that directory concurrently.

**What the bundle carries:** new bundles archive tracked pipeline source and copy replayable external configs; they do not embed scientific input data, container images or plugins. Replay still needs Python, Bash, Nextflow and its compatible Java runtime, the selected execution tools, and access to recorded external data and software. Inspect the manifest for recording gaps; configs using `includeConfig` retain the original-path requirement below.
- **Pipeline source:** `pipeline-source.tar.gz`, a deterministic archive of exactly the tracked files `pipeline.sha256` records. A replay runs the recorded checkout while it still holds that exact revision and source bytes, so paths that embed the pipeline directory (nf-core's `${projectDir}/assets/...` defaults) keep their values. Otherwise it extracts the archive into `<target>/provenance/pipeline`, checking every file, and runs that copy, so a bundle still replays after the checkout has moved to another release, been edited or been deleted. `<target>/provenance/pipeline-source.json` says which ran. The archive is checked again after Nextflow finishes, as is the original checkout when that was used. The extracted working tree is checked on creation but is not separately rehashed after execution. Archive fallback changes `${projectDir}`; absolute paths already stored in params are not rewritten.
- **Configuration:** the params file, generated configs and a copy of each external `--config` file (`configs/`). A config that uses `includeConfig` resolves relative includes against its own directory, so it replays from its original path. For recognized nf-core/configs includes, the release's default branch is resolved before launch and passed as `custom_config_version`, recorded in `params.json` and the manifest (`institutional_configs`). Explicit `custom_config_version` or `custom_config_base` values, a nonempty `NXF_OFFLINE`, or an unrecognized include bypass automatic pinning; a resumed run reuses its prior commit when applicable. A failed lookup is announced and leaves the release default.
- **Execution environment:** `environment.json`, read after the run from Nextflow's own records (`nextflow log`, `.nextflow.log`): available container identities by registry digest and local image ID (Docker, Podman) or image-file SHA-256 (Singularity, Apptainer), the engine version, the plugins and Java runtime Nextflow loaded, and remote inputs recovered from its staging and validation logs. Staged local copies are hashed after execution; supported validation-only HTTP/HTTPS/FTP URLs are fetched again, up to 100 MiB, so those hashes describe the refetched bytes rather than proving what validation originally consumed. `containers.config` is generated only for eligible Docker/Podman processes with one known registry digest and no containerless tasks, and `commands.sh` passes it last. Multiple or unresolved images and ephemeral Wave references have no pin; Singularity/Apptainer image files are hashed rather than pinned this way. Inspect unresolved entries and `issues` for recording gaps; recorded issues are also printed as advisories.

After Nextflow succeeds, a replay records its own `environment.json` and compares it with the recording in `<target>/provenance/environment_check.json`. Another image digest, plugin set, container engine, or remote file content or set fails the replay with `failed after Nextflow succeeded (execution environment differs from the recording)`; entries no record can decide (an image without a comparable identity, a Singularity image converted on another host) are reported as unverified and do not fail standalone replay. A differing Java runtime and processes present in only one run are notes. The comparator checks the container engine name, plugin list, images of shared processes and recorded remote URLs/hashes; Nextflow build, container engine version, host platform and task counts are not equality gates.

**Dependency stability during execution:** Before declaring success, nfclaw compares declared local input bytes and namespaces, generated/user configuration files, tracked pipeline source bytes and its Git revision with the launch snapshots. A visible change or unreadable dependency fails the run even when Nextflow exits zero. Results and launch hashes remain available for inspection; provenance records `dependency_stability`. Restoring the original bytes does not validate cached tasks from that attempt: resume archives the failed run and recomputes, and standalone replay refuses its tainted bundle. The check also applies with `--no-provenance`; that flag skips the bundle rather than the dependency checks. Standalone replay rechecks its original bundle after Nextflow finishes. These are checkpoint comparisons, not filesystem locks or immutable input copies: transient edits restored between checks, remote inputs and indirect configuration dependencies are outside their scope. Keep scientific inputs stable for the full execution.

**Local inputs and resume:** Ordinary Nextflow caching can miss file byte changes when size and timestamp are preserved, as well as recursive directory changes when root metadata is unchanged. Before a real `--resume`, nfclaw compares the prelaunch directory namespace and the SHA-256 of every explicitly declared local input file, including samplesheet data paths, with the previous bundle. An unchanged namespace and content retain normal caching; a changed namespace, changed file content, or an unavailable inventory preserves the complete previous run in a sibling `<outdir>.previous-<id>` archive, announces its path, and recomputes all tasks in a fresh Nextflow cache session. Prior logs remain in the archive and are copied forward so the current run log still appends. Previous publications cannot contaminate the fresh result inventory. Archiving refuses active engine database locks and dependencies that overlap the run directory. This safeguard also applies when the new launch disables provenance. Without a valid earlier input snapshot, local-input runs start fresh because unchanged data cannot be established. It covers explicitly declared local inputs, not remote or indirectly configured inputs.

Invoke `commands.sh` by an absolute or relative path. A moved bundle replays its own params, configs, config copies, pin config and source archive; external input data must still exist at their recorded paths and pass their checksum checks, as must a config that uses `includeConfig`.

Trust `skill.md` / `reference.md` over your own memory — they are generated from the pinned commit. To set any parameter beyond the essentials, look it up in `pipelines/<name>/reference.md` (the complete list, with allowed values and value constraints) — do not invent a flag or value. `nfclaw run` rejects unknown flags, invalid allowed values and unambiguous scalar/shape errors before it starts; `nf-schema` remains authoritative for the complete schema (especially conditionals and complex constraints) at runtime. Only read `upstream/` for deep dives.

Numeric values supplied through CLI flags, JSON/YAML parameter files and chain specs retain their decimal value when nfclaw writes the parameters Nextflow reads. Decimal notation and scientific notation do not round large integers or underflow small nonzero values to zero. Schema enum/boundary comparisons and numeric CSV/TSV column checks use the emitted decimal value. JSON/YAML nested numeric parameters and recorded chain specs retain it too. Integer values beyond Nextflow's signed 64-bit JSON parser range use decimal notation to prevent wraparound. NaN and infinity remain refused. Nextflow, nf-schema and each scientific tool still determine their own supported ranges and arithmetic precision.

---

## To chain pipelines (A, then B, then C)

Several pipelines in sequence — each stage starts only after the previous one **succeeded**, and its inputs are prepared from that stage's outputs (fetchngs → rnaseq: fetchngs's samplesheet becomes rnaseq's `--input`). Write a spec (JSON) and run it:
```json
{
  "nxf_env": {"NXF_JVM_ARGS": "-Djava.net.preferIPv6Addresses=true"},
  "stages": [
    {"pipeline": "fetchngs", "input": "/abs/ids.csv", "retries": 2},
    {"pipeline": "rnaseq", "params": {"genome": "GRCh38"}}
  ]
}
```

Preflight check first:
```bash
nfclaw chain run spec.json --outdir /abs/chain --check
```
It validates every stage, every handoff, and verifies that every stage's config parses with its target engine (`nextflow config`), leaving `--outdir` untouched — then run the same without `--check`. Unavailable engines and timed-out configuration probes block the chain before any stage launches.

Which pipeline can follow which: `nfclaw chain edges [name]`, or the `## Chaining` section of a `skill.md`; without a rule there is no chain (or give the stage an inline `"handoff"`).

- **Stage parameters:** A stage's `params` are its own flags (look them up in its `reference.md`). Explicit stage `input` and `params` values override mapped handoff values with an advisory; unused sources are not materialized, though the rule must still pass static checks. Values in `params_file` have lower priority and do not suppress mapped sources. `demo: true` adds that release's `test` profile.
- **Engine tuning:** Run options (`profile`, `nxf_ver`, `nxf_env`, `config`, `limits`) go on the chain or on a stage: releases of different ages can need different engines (`"nxf_ver": "25.10.4"` on an older one).
- **Option inheritance:** Stage `nxf_env` merges over chain-level values; stage `config` and `limits` replace the entire inherited list/object. Include shared configs explicitly when overriding. `--timeout SECONDS` opts into one shared deadline for preparation, stages, retries and completion checks; cleanup/failure recording may finish beyond it. Each config probe defaults to 300 seconds (`NFCLAW_CONFIG_TIMEOUT`); all analyses remain unlimited without `--timeout`. [Timeouts and long analyses](docs/timeouts.md) documents configurable margins and whole-controller background execution. `nfclaw chain status OUTDIR --quick` avoids data hashing and explicitly leaves lineage unchecked; normal chain status retains full verification.
- **Chain locking:** Concurrent chain processes targeting the same `--outdir` are blocked by an exclusive POSIX flock on `<outdir>/chain/.lock`.
- **Logs and state:** Each stage is an ordinary run in `<outdir>/NN-<stage>/`, with its own run log and provenance. The chain logs to `<outdir>/chain/logs/chain.log`; its **last line** is `==> nfclaw chain finished <time>: <outcome>` — poll it with `tail -n 1` for a background chain (`nohup nfclaw chain run ... &`); `kill <pid>` stops it cleanly. Per-stage state: `<outdir>/chain/state.json`.
- **Verification and safety:** Before feeding stage outputs into a downstream stage, the handoff engine verifies upstream file bytes against `outputs.sha256` and the complete published namespace against `outputs.inventory.json`, including empty directories, entry types and link identities. Local reference handoffs also require the producer's input namespace and byte records. Directory handoffs record their complete boundary inventory, and chain status compares it with the downstream prelaunch inventory after the schema-defined root canonicalization. A whole-run-directory handoff preserves every entry, including execution records; published results remain anchored to their original manifest, while the complete directory is recorded separately at the handoff boundary. Metagenomic assembly handoffs (fetchngs → mag, detaxizer → mag) isolate individual samples (`group: {sample}`) to avoid accidental multi-sample co-assembly pooling.
- **Resuming:** A failed chain continues with `nfclaw chain run [spec.json] --outdir /abs/chain --resume`: succeeded stages are skipped (and frozen), the failed one — which you may edit in the spec — resumes with Nextflow's cache. `"retries": N` relaunches a stage automatically after a pipeline failure (never after a validation error).
- **Lineage check:** `nfclaw chain status <outdir>` reconstructs the chain and verifies every link by SHA-256 (which run's outputs became which run's inputs); like `nfclaw status` (which also reads a chain's `--outdir`) it exits 0 succeeded, 3 still running, 1 otherwise — a chain whose nfclaw was killed outright is reported "stopped without an outcome". Spec, rules and failure modes: [`docs/chaining.md`](docs/chaining.md).

---

## Using nf-claw through MCP

`nfclaw mcp` serves this library to MCP clients (Claude Code, Codex, Antigravity, Hermes, …) on stdio; setup per client is in [`docs/mcp.md`](docs/mcp.md). Each tool runs the `nfclaw` command it names, so everything in this guide applies unchanged:

- **Find and read:** `list_pipelines(query)`, then `show_pipeline(pipeline)` for its `skill.md`, or `show_pipeline(pipeline, document="reference", grep="…")` for any other parameter.
- **Run:** `run_pipeline(pipeline, outdir, input, params={…}, check=true)` validates and prints the command; without `check` it starts a detached job and returns its `job_id`. Pipeline parameters go in `params` under their schema names; nfclaw's own options (`profile`, `resume`, `nxf_env`, `limit_cpus`, …) are separate arguments.
- **Follow:** `get_job(job_id, wait_seconds=N)` reports `running` (`preparing` / `launched`), `succeeded`, `failed`, `cancelled` or `lost`, with `nfclaw status`'s report and the latest output. A job survives the client and the server: any later session reads it back (`list_jobs`).
- **Chain:** `run_chain(spec, outdir)` runs `nfclaw chain run` on the spec given as JSON; `run_status(outdir, chain=true)` verifies the lineage.
- **Stop:** `cancel_job(job_id)` stops it as `kill <nfclaw pid>` does; continue later with `resume=true`.

Use absolute paths and a new `outdir` per run, exactly as on the command line.

---

## To run a specific (non-latest) version

The default is the repository's pinned release. Updates are checked before adoption, so a newer upstream release may not yet be pinned. To run another published release instead:

1. **List releases:** `nfclaw versions <name>` (the pinned latest is flagged).
2. **Read that version's docs:** `nfclaw show <name> --pipeline-version X.Y.Z` — it fetches the tag, materializes it under `pipelines/<name>/.versions/X.Y.Z/` (git-ignored), and prints the `skill.md` generated from *that* release's schema (a `reference.md` is written alongside it). The params, flags and validation all come from X.Y.Z, not from latest.
3. **Run it:**
   ```bash
   nfclaw run <name> --pipeline-version X.Y.Z --input samplesheet.csv --outdir results -profile docker
   ```

Only real release tags are accepted (`X.Y.Z`, or the `X.Y` of older nf-core releases such as fetchngs `1.9`; with or without a leading `v`) — plus `dev`, below; an unknown version fails fast and lists what is available. Provenance records the exact version that ran.

---

## To run unreleased development code (`dev`)

Every nf-core pipeline develops on a `dev` branch and releases from it, so `dev` holds the changes that are not in any release yet. To run it (the `nextflow run nf-core/<name> -r dev` equivalent):
```bash
nfclaw run <name> --pipeline-version dev --input samplesheet.csv --outdir results -profile docker
```
Every other flag works as for a release, e.g.:
```bash
nfclaw run fetchngs --pipeline-version dev --input ids.csv --outdir /path/to/out -profile binac2 --nxf-ver 25.10.4
```

- **Commit anchoring:** `dev` moves, so each run resolves it to the branch's **current head commit** and materializes that commit under `pipelines/<name>/.versions/dev-<commit12>/` (git-ignored, one immutable tree per commit, so a replay or a concurrent run never sees the code change). The run prints a warning naming the commit; provenance records `version: dev` plus that exact commit, and `commands.sh` replays it.
- **Documentation:** Read its docs first — params can differ from the release: `nfclaw show <name> --pipeline-version dev` prints the `skill.md` generated from that commit (`reference.md` is written beside it).
- **Listing:** `nfclaw versions <name>` lists `dev` (with its head commit) after the releases.
- **Offline behavior:** Offline, nfclaw falls back to the last `dev` head it fetched and says so; a pipeline with no `dev` branch fails fast. `--resume` warns when `dev` moved since the run it continues (Nextflow then re-runs only the tasks the change touched).

Prefer a release for results you need to reproduce from a version number; use `dev` for fixes or features that are not released yet.

---

## Tuning the Nextflow engine / environment

`nfclaw run` inherits your shell environment and passes it through to Nextflow. Two run flags make the engine and its runtime explicit and reproducible (both are recorded in `<outdir>/provenance/`):

- **`--nxf-ver X.Y.Z`** — pin the Nextflow engine for this run (sets `NXF_VER`). Use it when a newer Nextflow breaks an older pipeline release (e.g. a config-parser change in a new Nextflow major), or to reproduce a prior run exactly. Nextflow itself refuses an engine older than the release's declared `nextflowVersion` (see `skill.md`); nfclaw's error then names the `--nxf-ver` to pass.
- **`--nxf-env KEY=VALUE`** — set an `NXF_*` variable for this run (repeatable). Common fixes:
  - IPv6-only host where the JVM can't reach GitHub for remote configs:
    `--nxf-env NXF_JVM_ARGS=-Djava.net.preferIPv6Addresses=true`
  - skip remote config fetches entirely:
    `--nxf-env NXF_OFFLINE=true`
- **`--config PATH` (or `-c`, repeatable)** — pass an extra Nextflow config straight through (`-c`), e.g. a docker host-network config (`docker { runOptions = "--network host" }`) or custom resources.

---

## Running on a machine smaller than the pipeline assumes

nf-core commonly sizes processes from labels in the pipeline's `conf/base.config`, tuned for a server: one step can request far more memory than a workstation has (`Process requirement exceeds available memory`), and retry rules can increase requests. Many bundled `test` profiles set small ceilings; real runs often need an explicit one. Set one:
```bash
nfclaw run <name> ... --limit-cpus 4 --limit-memory 15.GB
```
`--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes.

These become Nextflow's `process.resourceLimits` — the ceiling nf-core documents — applied to every process and every retry, so one flag covers whatever the pipeline asks for next. `resourceLimits` needs Nextflow 24.04.0 or newer: older engines accept it silently and apply no ceiling, so `nfclaw run` refuses `--limit-*` when the run would use one or its engine version cannot be identified (pin a supported concrete engine with `--nxf-ver`, or use the release's own `--max-*` parameters where it declares them). Do not chase this with `withName:` overrides: those size only selected processes. A constant override also applies to that process's retries, but expressions using `task.attempt` can grow and every other process still needs coverage. The generated config is written to `<outdir>/provenance/resource_limits.config` and replayed by `commands.sh`.

Any other environment (proxies, `JAVA_HOME`, …) is inherited from your shell unchanged. Each run launches Nextflow from its `--outdir`, so its `.nextflow/` history is isolated and `--resume` resumes that run (use a distinct `--outdir` per pipeline).

Task work files default to the shared `<repo>/work/` directory. Set
`--nxf-env NXF_WORK=/path/to/work` to choose another location; relative values resolve
against the caller's working directory. Preserve the work files needed for resume
and any result symlinks that point into them.

If a pipeline's `upstream/` is empty, initialise it first:
```bash
git submodule update --init pipelines/<name>/upstream
```
`nfclaw run` refuses a pinned `upstream/` that is not at the commit its `skill.md` documents (e.g. after a `git pull` without a submodule update, which would otherwise run the old release under the new release's docs) or that has local edits to tracked files: restore it with `git submodule update --force pipelines/<name>/upstream`, or pass `--pipeline-version` to run another release deliberately.

---

## Requirements (agent environment)

- **Git**
- **Python 3.11+** (install nfclaw with `pip install -e .`)
- **Nextflow** (Java 17+)
- **Docker** or **Singularity/Apptainer**

> [!IMPORTANT]
> **Use a space-free path on macOS and Linux:** Many bioinformatics tools and Nextflow's work directory mishandle spaces in paths; on macOS also avoid iCloud paths.

---

## Checking a replay

```bash
nfclaw verify <replay-outdir> --against <original-outdir>
```

Hashes the replay's live files and compares them **by path** with the original recorded `outputs.sha256` (or live originals when no manifest exists). It reports `identical` / `changed` / `missing` / `extra` for files, missing/extra directories, and changed link identities from `outputs.inventory.json`. Missing or extra files or directories fail the structural check. The nf-core run-metadata files the template names from its launch clock (`pipeline_info/params_<time>.json`, the execution report/timeline/trace/DAG of releases without `trace_report_suffix`, and the nf-co2footprint plugin's `co2footprint_{report,summary,trace}_<time>` files) are paired one to one, listed under `renamed` as `original -> replay`, and compared by bytes; any other dated path keeps its exact identity. A historical file-only manifest cannot certify its original directory structure; verification reports that gap and exits unsuccessfully. Without any historical checksum manifest, both live directory trees can still be compared. Changed bytes may reflect metadata or different scientific results; inspect them using a format-aware comparison. File structure alone establishes no analytical agreement. When both execution-environment records (`provenance/environment.json`) can be read as JSON objects, it also reports the comparison of container images, plugins, the container engine name and remote inputs (`environment: identical`, `differs` with the mismatches, or `unverified`). Add `--strict` to require identical file bytes, recorded link identities and an `identical` environment comparison when available. If either environment record is missing, unreadable or not a JSON object, verification reports `not recorded by both runs` and strict mode enforces only the output checks; it cannot establish environment agreement. Links into independently generated task work directories can differ; inspect those changes explicitly.

Replay requires Python 3 and checks the recorded local data, configurations, parameters and archived pipeline source before launching. A changed dependency or incomplete bundle is refused. It pins the observed Nextflow version and, where recorded and eligible, container image digests and the nf-core/configs commit, then compares the recorded environment evidence. Retain the original bundle: standalone replay writes logs and source/environment records into the target, rather than generating another complete replay bundle. Files a task downloads by itself, Conda environments and a config's own `includeConfig` targets are not frozen.

---

## Reference genomes

Some releases resolve a reference **remotely by default** — sarek defaults `--genome` to `GATK.GRCh38`, looked up in AWS iGenomes at `s3://ngi-igenomes/igenomes/` — so a run that passes no reference of its own reads from S3 and fails on a host without access to that bucket. Each `skill.md` states which case its pipeline is in under "Reference genome". Pass your own reference (`--fasta`, …) for a self-contained run, or `--igenomes-ignore true` to disable the lookup.

---

## Warnings are not failures

A run or replay can print benign upstream warnings: Nextflow reporting the `validation.*` config scope as unrecognised (its linter does not see plugin-contributed scopes — upstream nf-schema issue), a pinned release setting a parameter its own plugin removed (scrnaseq's `validationSchemaIgnoreParams` — `nfclaw run` neutralises this one at the config layer via nf-schema's `validation.ignoreParams` and prints an advisory recording that it did, leaving the pinned tree untouched), or a `test` profile that deliberately sets conflicting references (rnaseq's `--gtf` with `--gff`). They are catalogued with their real cause in [`docs/known-issues.md`](docs/known-issues.md) under "Warnings a run prints that are not faults". Check there before reporting one. `nfclaw run` also announces measured run-to-run variability before launch (e.g. dada2 `assignTaxonomy` tie-breaking or unseeded QIIME2 rarefaction) when task scripts contain them, so differences across runs or replays are anticipated rather than treated as faults. Replay runs the recorded analysis into a fresh directory, removes `-resume`, and pins the observed engine version; warning text can vary with plugin resolution and cached configuration even when scientific outputs agree. nf-claw keeps the pinned pipeline source unmodified.

---

## Run-time errors

Spaces in a path break many tools, so `nfclaw run` checks the repo path, the Nextflow work directory and `--outdir` **before** launching and **fails fast** naming the offending path (pass `--allow-spaces` to override) — a deterministic check, not a guess. For other failures (IPv6 host, no-network database downloads, a too-new Nextflow config parser, known upstream-pipeline bugs) the error quotes Nextflow's own report and names the run log, `.nextflow.log` and the failing task's files by absolute path (see [Where a run is logged](#where-a-run-is-logged--and-how-to-check-one)); the symptom→fix map is in [`docs/known-issues.md`](docs/known-issues.md).
