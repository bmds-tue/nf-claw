# nf-claw — nf-core pipelines for agents

This repo is a library of nf-core pipelines. Each lives in `pipelines/<name>/`:
`upstream/` (the pinned pipeline code, a git submodule) and `skill.md` (how to run it).

This guide is what an agent needs to find, run, follow, replay and chain a pipeline. The
guarantees behind each step, and their limits, are in focused guides it links to:
[inputs and preflight](docs/preflight.md), [replay and verification](docs/replay.md),
[chaining](docs/chaining.md), [timeouts](docs/timeouts.md), [MCP](docs/mcp.md) and
[known issues](docs/known-issues.md).

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

1. **Find it:** `nfclaw list <keywords>` ranks the pipelines matching a request, or grep `catalog.json` (or `catalog.md`) for a keyword — do NOT read it whole.
2. **Read `pipelines/<name>/skill.md`:** the exact command, inputs, and required parameters for the pinned version.
3. **Run:**
   ```bash
   nfclaw run <name> --input samplesheet.csv --outdir results -profile docker
   ```
   *(Direct upstream command: `nextflow run pipelines/<name>/upstream -profile docker ...` — the submodule is already pinned to the release, so no `-r`. This bypasses nfclaw's preflight, provenance and runtime corrections; use nfclaw for releases that need those corrections.)*
4. **Check status (foreground or background):**
   ```bash
   nfclaw status results          # add --json for one machine-readable object
   ```
   Prints `success`, `running`, or how it ended with the error (exit codes: `0` success, `3` running, `1` failed). Logs: see [Where a run is logged](#where-a-run-is-logged--and-how-to-check-one).

> [!NOTE]
> `nfclaw run` executes the pipeline for real — there is no preview/dry-run default. To see the exact `nextflow` command that *would* run without launching it, add `--check` (it validates inputs and parameters, prints the command — prefixed with the `NXF_*` variables `--nxf-ver`/`--nxf-env` set for it, e.g. `NXF_VER=25.10.4 nextflow run …` — and exits; it writes nothing into `--outdir`, so you can still use that directory for the real run). Add `--demo` to run the pinned release's bundled test profile end to end. A run has no overall time limit unless you pass `--timeout SECONDS`.

- **Options:** Docker is the default profile; `-profile` / `--profile` accepts comma-separated
  profiles. `--params-file PATH` loads JSON (or YAML with the `yaml` extra); explicit CLI values
  override file values. Pipeline flags accept hyphens or underscores (raw Nextflow needs their
  exact schema spelling). `--no-provenance` skips the replay bundle and checksum records but keeps
  the parameter file and run logs.
- **What `--check` covers:** inputs, parameters and environment requirements; it can initialize
  submodules, fetch a requested version and probe Nextflow. Its `preflight` lines say which checks
  ran, which are deferred to launch and which are unsupported; conditional and complex schema
  constraints remain for the pinned release's own validation ([scope](docs/preflight.md)).
- **References:** supply the references the selected analysis needs, even when its schema does not
  mark them required; each skill's reference section explains the options.
- **Output directory:** outside the repository or ignored by Git (`results/` is ignored), and one
  per run. A second run into an `--outdir` that is in use fails fast (an exclusive lock beside it).
  Keep data, pipeline code and configuration outside the output tree: nfclaw refuses any overlap
  between what a run reads and where it writes before writing anything.

### Inputs

- **Absolute paths inside a samplesheet.** Nextflow resolves them against its launch directory,
  which `nfclaw run` sets to `--outdir`, so a relative one cannot mean what it says — `nfclaw run`
  rejects it. `--input` itself may be relative (nfclaw makes it absolute), and it is not always a
  samplesheet: the pipeline's schema decides — a directory or tarball (rangeland), an SDRF file or
  PRIDE accession (mhcquant), or `--input false` where a pipeline documents running without one
  (sarek). The `Inputs` section of `skill.md` says which.
- **No samplesheet yet? Pass the data files.** Where `--input` is a samplesheet, it may instead
  name a directory (searched recursively), a quoted glob, or files (`--input` once per file), and
  `nfclaw run` generates the sheet first:
  `nfclaw run rnaseq --input /data/fastq --sheet-set strandedness=auto --outdir results`.
  Sample names come from file names (never altered); FastQ mates pair by `_R1`/`_R2` (by `_1`/`_2`
  only when their first read names show they are mates); lanes fill a `lane` column. Values no file
  determines come from `--sheet-set COLUMN=VALUE` (repeatable; a constant or a `{sample}`/`{lane}`
  template; an empty value leaves a column empty, which is also how to choose between read-column
  groups) or the schema's defaults — the `Inputs` section of
  `skill.md` lists which. Missing values, ambiguous matches, orphan mates and duplicates are refused;
  unmatched files are ignored with an advisory, so read the warnings. Add `--check` to see the sheet
  first. It is staged as `<outdir>/provenance/samplesheet.csv` and replayed as recorded. A chain
  stage takes the same `input` plus a `"sheet_set"` object. Details and the per-pipeline support
  matrix: [generation boundaries](docs/preflight.md#generation-boundaries).
- **Safe filenames and sample IDs.** Task scripts put staged file names and sample identifiers into
  shell commands, so nfclaw refuses input file names with whitespace, shell operators, wildcards or
  a leading `-`/`~`, and sample/patient/genome identifiers that do not start with a letter, digit or
  underscore or that hold anything but letters, digits, combining marks, `.`, `_` and `-`. Use a
  safely named copy or an explicit safe alias: nfclaw never renames a scientific sample. The full
  rules: [inputs refused before launch](docs/preflight.md#inputs-refused-before-launch).
- **Recorded runtime corrections.** A few exact releases (fastqrepair 1.1.1; Bactmap, Createtaxdb
  and Funcscan) run with recorded corrections that leave the pinned source untouched; the run says
  so and records them ([source corrections](docs/source-corrections.md)).

---

## Where a run is logged — and how to check one

Every `nfclaw run` records itself at a fixed place — there is no need to redirect its output, and nothing to look up. To know how a run stands, ask nfclaw:

```bash
nfclaw status <outdir>
nfclaw status <outdir> --json     # state, outcome, times, pids, logs, caveats, error, last output
```

Prints `status: success`, `running (…)`, the outcome it ended with (`failed (exit status N)`, `timed out after N s`, `interrupted`, `terminated by SIGTERM`, `refused before launch`), or `stopped without an outcome` (nfclaw itself was killed with SIGKILL, ran out of memory, its disk filled up, or the machine restarted); then the log, and the recorded error or the run's last output. A log that exists but cannot be read is `unknown`. Exit code: 0 success, 3 running, 1 anything else. It works for replays and chains too.

**Success is not completeness.** A pipeline can exit 0 without some of its samples or tasks. When its completion summary says so (nf-core's "…, but with errored process(es)", rnaseq's skipped samples and failed strandedness checks), when Nextflow ignored failed tasks, or when a profile or `--config` runs every task as a stub (`stubRun = true`, as proteinfold's `test` profile does — so its `--demo` computes nothing), `nfclaw status` reports `status: success — with caveats the pipeline reported about its results` and quotes them; `nfclaw run` prints them as warnings and records them in `provenance/run_manifest.json` (`completion_caveats`). Read them before using the results.

- **`<outdir>/provenance/logs/run.log`** — the whole launch in order: nfclaw's header (command, launch directory, Nextflow log path, host and pids, advisories), everything Nextflow printed (each line prefixed with `| `), and on failure nfclaw's error. Its **last line**, written once nfclaw is done, is `==> nfclaw run finished <time>: <outcome>`. `--resume` appends, so a failed attempt is never overwritten. No run log means nfclaw never launched there — run the command in the foreground to see why.
- **`<outdir>/.nextflow.log`** — Nextflow's own detailed log. Nextflow runs from `--outdir`, so its console hint "Check '.nextflow.log'" means this file, not one in your working directory.
- **`stdout.txt` / `stderr.txt` beside `run.log`** — Nextflow's two raw streams. Engines through 26.04 print error reports on stdout; from 26.10, console logs go to stderr ([migration notes](https://docs.seqera.io/nextflow/migrations/26-10#breaking-changes)). Inspect both when diagnosing a failure.

**Jobs started through MCP** can also be managed from the shell, using the same host, user and
`NFCLAW_STATE_DIR`: `nfclaw jobs list`, `nfclaw jobs status <job-id>` and
`nfclaw jobs cancel <job-id>`. Add `--json` for a versioned object. Job status exits 0 for success,
3 while running, and 1 for failed, cancelled, lost or unknown jobs. Cancellation acknowledges the
request without waiting; inspect status to confirm shutdown. [Commands and JSON fields](docs/mcp.md#manage-jobs-from-the-shell).

Start a long run in the background with `nohup nfclaw run ... &` and stop it with `kill <nfclaw pid>` (the `pid:` line of the run log): nfclaw then shuts Nextflow and its tasks down, removes the task containers they left behind, writes the bundle and closes the log, as on Ctrl-C. On Linux, a Nextflow whose nfclaw is killed outright (SIGKILL) is sent SIGTERM; scheduler jobs and other detached work still rely on the executor's own cleanup.

When a run fails, nfclaw's error quotes what Nextflow reported — plus the `Caused by:` chain from `.nextflow.log` when the console hides the reason — and names the run log, `.nextflow.log` and the failing task's `.command.err` by absolute path. Fix the cause, then re-run the same command with `--resume`. The symptom→fix map is in [`docs/known-issues.md`](docs/known-issues.md).

---

## Replaying and verifying a run

`<outdir>/provenance/commands.sh` re-runs the recorded command into a **fresh** directory (default `<outdir>.replay`, or pass one: `./commands.sh /path/to/fresh-dir`); it refuses a target that already holds files, because an nf-core pipeline cannot re-publish over a previous run's files. A replay re-executes the pipeline — a reproduction, not a `--resume` — after its guard checks that the recorded pipeline source, local input bytes (including samplesheet data paths), parameters and configs are unchanged; it refuses rather than producing silently divergent results. It logs itself to `<target>/provenance/logs/run.log` (`nfclaw status <target>` reads it; `kill <replay pid>` stops it), and after Nextflow succeeds compares its execution environment (image digests, plugins, container engine, remote inputs) with the recording. Keep the original bundle.

```bash
nfclaw verify results.replay --against results            # structure; pairs launch-stamped files
nfclaw verify results.replay --against results --strict   # also byte identity; environment if both recorded one
nfclaw verify results.replay --against results --require-environment   # complete environment evidence
nfclaw assess results.replay --contract runner/output_contracts/tumourevo-1.0.0-demo.json
```

`verify` compares files and directories by path and reports `identical` / `changed` / `missing` / `extra`; changed bytes may be metadata or different science, so inspect them format-aware. `assess` checks sample coverage and parsed scientific content against an explicit [output contract](docs/scientific-output-contracts.md); two exact-pin demo contracts are supplied. What the bundle carries, what the guard checks, how `--resume` treats changed local inputs, and what each verification mode can and cannot establish: [replay and verification](docs/replay.md).

Trust `skill.md` / `reference.md` over your own memory — they are generated from the pinned commit. To set any parameter beyond the essentials, look it up in `pipelines/<name>/reference.md` (the complete list, with allowed values and value constraints) — do not invent a flag or value. `nfclaw run` rejects unknown flags, invalid allowed values and unambiguous scalar/shape errors before it starts; `nf-schema` remains authoritative for the complete schema at runtime. Numeric values keep their exact decimal value on their way to Nextflow. Only read `upstream/` for deep dives.

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
It validates every stage and handoff and checks that every stage's config parses with its target engine, leaving `--outdir` untouched — then run the same without `--check`.

- **Which pipeline can follow which:** `nfclaw chain edges [name]`, or the `## Chaining` section of a `skill.md`; without a rule there is no chain (or give the stage an inline `"handoff"`).
- **Stage parameters:** a stage's `params` are its own flags (look them up in its `reference.md`); explicit stage `input` and `params` override mapped handoff values. `demo: true` adds that release's `test` profile.
- **Run options:** `profile`, `nxf_ver`, `nxf_env`, `config` and `limits` go on the chain or on a stage (releases of different ages can need different engines). A stage's `nxf_env` merges over the chain's; its `config` and `limits` replace them. `--timeout SECONDS` sets one deadline for the whole chain.
- **Logs and state:** each stage is an ordinary run in `<outdir>/NN-<stage>/`. The chain logs to `<outdir>/chain/logs/chain.log`, whose **last line** is `==> nfclaw chain finished <time>: <outcome>`; `kill <pid>` stops it cleanly.
- **Resuming:** `nfclaw chain run [spec.json] --outdir /abs/chain --resume` skips succeeded stages and resumes the failed one (which you may edit in the spec) with Nextflow's cache. `"retries": N` relaunches a stage after a pipeline failure (never after a validation error).
- **Lineage check:** `nfclaw chain status <outdir>` (add `--json` for one object) verifies by SHA-256 which run's outputs became which run's inputs, and exits 0 succeeded, 3 running, 1 otherwise; `--quick` skips the hashing. Handoff verification, sample isolation, secrets in `nxf_env` and failure modes: [`docs/chaining.md`](docs/chaining.md).

---

## Using nf-claw through MCP

`nfclaw mcp` serves this library to MCP clients (Claude Code, Codex, Antigravity, Hermes, …) on stdio; setup per client is in [`docs/mcp.md`](docs/mcp.md). Each tool runs the `nfclaw` command it names, so everything in this guide applies unchanged:

- **Find and read:** `list_pipelines(query)`, then `show_pipeline(pipeline)` for its `skill.md`, or `show_pipeline(pipeline, document="reference", grep="…")` for any other parameter. `read_doc(guide="known-issues", search="…")` returns only the sections about an error or warning.
- **Run:** `run_pipeline(pipeline, outdir, input, params={…}, check=true)` validates and prints the command; without `check` it starts a detached job and returns its `job_id`. Pipeline parameters go in `params` under their schema names; nfclaw's own options (`profile`, `resume`, `nxf_env`, `limit_cpus`, …) are separate arguments.
- **Follow:** `get_job(job_id, wait_seconds=N)` reports `running` (`preparing` / `launched`), `succeeded`, `failed`, `cancelled` or `lost`, with `nfclaw status`'s report and the latest output. A job survives the client and the server: any later session reads it back (`list_jobs`). `run_status(outdir)` reports any run directory, with the parsed `nfclaw status --json` record.
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

### Unreleased development code (`dev`)

`--pipeline-version dev` runs the `dev` branch (the `nextflow run nf-core/<name> -r dev` equivalent), where the changes that are not in any release yet live:
```bash
nfclaw run fetchngs --pipeline-version dev --input ids.csv --outdir /path/to/out -profile docker
```
`dev` moves, so each run resolves it to the branch's current head commit, materializes that commit under `pipelines/<name>/.versions/dev-<commit12>/`, prints a warning naming it, and records it for replay. Read its docs first (`nfclaw show <name> --pipeline-version dev`): params can differ from the release. `nfclaw versions <name>` lists `dev` with its head commit; offline, nfclaw falls back to the last `dev` head it fetched and says so; `--resume` warns when `dev` moved since the run it continues. Prefer a release for results you need to reproduce from a version number.

---

## Tuning the Nextflow engine / environment

`nfclaw run` inherits your shell environment and passes it through to Nextflow. Two run flags make the engine and its runtime explicit and reproducible (both are recorded in `<outdir>/provenance/`):

- **`--nxf-ver X.Y.Z`** — pin the Nextflow engine for this run (sets `NXF_VER`). Use it when a newer Nextflow breaks an older pipeline release, or to reproduce a prior run exactly. Nextflow itself refuses an engine older than the release's declared `nextflowVersion` (see `skill.md`); nfclaw's error then names the `--nxf-ver` to pass, and `--check` warns about it instead.
- **`--nxf-env KEY=VALUE`** — set an `NXF_*` variable for this run (repeatable). Common fixes:
  - IPv6-only host where the JVM can't reach GitHub for remote configs:
    `--nxf-env NXF_JVM_ARGS=-Djava.net.preferIPv6Addresses=true`
  - skip remote config fetches entirely:
    `--nxf-env NXF_OFFLINE=true`
- **`--config PATH` (or `-c`, repeatable)** — pass an extra Nextflow config straight through (`-c`), e.g. a docker host-network config (`docker { runOptions = "--network host" }`) or custom resources.

Each run launches Nextflow from its `--outdir`, so its `.nextflow/` history is isolated and `--resume` resumes that run (use a distinct `--outdir` per pipeline). Task work files default to the shared `<repo>/work/` directory; set `--nxf-env NXF_WORK=/path/to/work` to choose another, and keep the work files that `--resume` and result symlinks need.

---

## Running on a machine smaller than the pipeline assumes

nf-core commonly sizes processes from labels in the pipeline's `conf/base.config`, tuned for a server: one step can request far more memory than a workstation has (`Process requirement exceeds available memory`), and retry rules can increase requests. Many bundled `test` profiles set small ceilings; real runs often need an explicit one. Set one:
```bash
nfclaw run <name> ... --limit-cpus 4 --limit-memory 15.GB
```
`--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes.

These become Nextflow's `process.resourceLimits`, applied to every process and every retry (written to `<outdir>/provenance/resource_limits.config` and replayed by `commands.sh`). `resourceLimits` needs Nextflow 24.04.0 or newer: older engines accept it silently and apply no ceiling, so `nfclaw run` refuses `--limit-*` when the run would use one or its engine version cannot be identified (pin a supported engine with `--nxf-ver`, or use the release's own `--max-*` parameters where it declares them). Do not chase this with `withName:` overrides: those size only selected processes.

If a pipeline's `upstream/` is empty, initialise it first:
```bash
git submodule update --init pipelines/<name>/upstream
```
`nfclaw run` refuses a pinned `upstream/` that is not at the commit its `skill.md` documents (e.g. after a `git pull` without a submodule update) or that has local edits to tracked files: restore it with `git submodule update --force pipelines/<name>/upstream`, or pass `--pipeline-version` to run another release deliberately.

---

## Requirements (agent environment)

- **Linux or macOS** (on Windows, run nfclaw inside WSL 2)
- **Git**
- **Python 3.11+** (install nfclaw with `pip install -e .`)
- **Nextflow** (Java 17+)
- **Docker** or **Singularity/Apptainer**

> [!IMPORTANT]
> **Use a space-free path on macOS and Linux:** Many bioinformatics tools and Nextflow's work directory mishandle spaces in paths; on macOS also avoid iCloud paths. `nfclaw run` checks the repo path, the work directory and `--outdir` before launching and fails fast naming the offending path (`--allow-spaces` overrides it).

---

## Reference genomes

Some releases resolve a reference **remotely by default** — sarek defaults `--genome` to `GATK.GRCh38`, looked up in AWS iGenomes at `s3://ngi-igenomes/igenomes/` — so a run that passes no reference of its own reads from S3 and fails on a host without access to that bucket. Each `skill.md` states which case its pipeline is in under "Reference genome". Pass your own reference (`--fasta`, …) for a self-contained run, or `--igenomes-ignore true` to disable the lookup.

---

## Warnings are not failures

A run or replay can print benign upstream warnings: Nextflow reporting the `validation.*` config scope as unrecognised (its linter does not see plugin-contributed scopes), a pinned release setting a parameter its own plugin removed (scrnaseq's `validationSchemaIgnoreParams`, which `nfclaw run` neutralises at the config layer and announces), or a `test` profile that deliberately sets conflicting references (rnaseq's `--gtf` with `--gff`). They are catalogued with their real cause in [`docs/known-issues.md`](docs/known-issues.md) under "Warnings a run prints that are not faults"; check there before reporting one. `nfclaw run` also announces measured run-to-run variability before launch (e.g. dada2 `assignTaxonomy` tie-breaking or unseeded QIIME2 rarefaction), so differences across runs or replays are anticipated rather than treated as faults. nf-claw keeps the pinned pipeline source unmodified.
