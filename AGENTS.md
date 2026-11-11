# nf-claw agent guide

This repository is a library of nf-core pipelines. Each one lives in `pipelines/<name>/`:
`upstream/` holds the pinned pipeline code (a git submodule) and `skill.md` says how to run it.

This guide is what an agent needs to find, run, follow, replay and chain a pipeline. The guarantees
behind each step, and their limits, are in the guides it links to:
[inputs and preflight](docs/preflight.md), [replay and verification](docs/replay.md),
[chaining](docs/chaining.md), [timeouts](docs/timeouts.md), [MCP](docs/mcp.md) and
[known issues](docs/known-issues.md).

---

## Setup (first time)

Install once, from the repository root, so the `nfclaw` command is on `PATH`:
```bash
pip install -e .
```
Use Python 3.11+ and a virtualenv on a path without spaces (on macOS, not in iCloud). For the
maintenance tests, install `pip install -e ".[dev,yaml]"`, which adds pytest and YAML support.

**Without installing:** run `python3 -m runner <cmd>` from the repository root wherever this guide
shows `nfclaw <cmd>`.

---

## To run a pipeline

1. **Find it:** `nfclaw list <keywords>` ranks the pipelines that match a request. Or grep
   `catalog.json` (or `catalog.md`) for a keyword; do NOT read it whole.
2. **Read `pipelines/<name>/skill.md`:** the exact command, inputs and required parameters of the
   pinned release.
3. **Run:**
   ```bash
   nfclaw run <name> --input samplesheet.csv --outdir results -profile docker
   ```
   The direct upstream command is `nextflow run pipelines/<name>/upstream -profile docker ...`, with
   no `-r` because the submodule is already pinned to the release. It skips nfclaw's preflight,
   provenance and runtime corrections, so use nfclaw for releases that need those corrections.
4. **Check status, in the foreground or the background:**
   ```bash
   nfclaw status results          # add --json for one machine-readable object
   ```
   It prints `success`, `running`, or how the run ended, with the error. Exit codes: `0` success,
   `3` running, `1` failed. For the logs, see [where a run is logged](#where-a-run-is-logged-and-how-to-check-it).

> [!NOTE]
> `nfclaw run` runs the pipeline for real: there is no preview/dry-run default. To see the exact
> `nextflow` command without launching it, add `--check`. It validates inputs and parameters, prints
> the command (preceded by the `NXF_*` variables that `--nxf-ver` and `--nxf-env` set, e.g.
> `NXF_VER=25.10.4 nextflow run …`) and exits. It writes nothing into `--outdir`, so you can use that
> directory for the real run. Add `--demo` to run the release's bundled test profile end to end. A
> run has no overall time limit unless you pass `--timeout SECONDS`.

- **Options:** Docker is the default profile; `-profile` (or `--profile`) takes comma-separated
  profiles. `--params-file PATH` loads JSON (or YAML, with the `yaml` extra), and values given on the
  command line override the file. Pipeline flags accept hyphens or underscores (raw Nextflow needs
  the exact spelling from the schema). `--no-provenance` skips the replay bundle and checksum records
  but keeps the parameter file and the run logs; without those records a later `--resume` cannot
  reuse cached tasks and recomputes them all ([why](docs/replay.md#local-inputs-and-resume)).
- **What `--check` covers:** inputs, parameters and the environment (Git, Nextflow, Java, the
  profile's container engine and, for Docker, a daemon that answers), and whether the run's engine
  can parse the release's configuration (`nextflow config`). A release that Nextflow 26.04+'s strict
  parser rejects is refused, with the fix. `--check` may initialise submodules, fetch a requested
  version and download a pinned engine. Its `preflight` lines say which checks ran, which are left
  to launch and which are not supported; conditional and complex schema constraints are left to the
  release's own validation ([scope](docs/preflight.md)).
- **References:** pass the references the chosen analysis needs, even when the schema does not mark
  them required. Each skill's reference section lists the options.
- **Output directory:** outside the repository or ignored by Git (`results/` is ignored), and a new
  one per run. A second run into an `--outdir` that is in use fails at once (a lock file sits beside
  it). Keep data, pipeline code and configuration outside the output directory: nfclaw refuses any
  overlap between what a run reads and where it writes, before writing anything.

### Inputs

- **Paths inside a samplesheet must be absolute.** Nextflow resolves them against its launch
  directory, which `nfclaw run` sets to `--outdir`, so a relative path would not mean what it says,
  and `nfclaw run` rejects it. `--input` itself may be relative (nfclaw makes it absolute). It is
  not always a samplesheet; the schema decides. It can be a directory or tarball (rangeland), an
  SDRF file or PRIDE accession (mhcquant), or `--input false` where a pipeline documents running
  without one (sarek). The `Inputs` section of `skill.md` says which.
- **No samplesheet yet? Pass the data files.** Where `--input` is a samplesheet, it may instead name
  a directory (searched recursively), a quoted glob, or files (`--input` once per file), and
  `nfclaw run` writes the sheet first:
  `nfclaw run rnaseq --input /data/fastq --sheet-set strandedness=auto --outdir results`.
  Sample names are the file names, never changed. FastQ mates pair by `_R1`/`_R2`, or by `_1`/`_2`
  only when their first read names show they are mates; lanes fill a `lane` column. Values that no
  file determines come from `--sheet-set COLUMN=VALUE` or from the schema's defaults; the `Inputs`
  section of `skill.md` lists them. `--sheet-set` can be repeated and takes a constant or a
  `{sample}`/`{lane}` template; an empty value leaves a column empty, which is also how to choose
  between groups of read columns. Missing values, ambiguous matches, unpaired mates and duplicates
  are refused. Files that match nothing are ignored with an advisory, so read the warnings. Add
  `--check` to see the sheet first. It is staged as `<outdir>/provenance/samplesheet.csv` and
  replayed as recorded. In a chain, a stage takes the same `input` plus a `"sheet_set"` object. The
  rules and the list of supported pipelines: [generation boundaries](docs/preflight.md#generation-boundaries).
- **Safe file names and sample IDs.** Task scripts put staged file names and sample identifiers into
  shell commands. nfclaw therefore refuses input file names with whitespace, shell operators,
  wildcards or a leading `-` or `~`. It also refuses sample, patient and genome identifiers that do
  not start with a letter, digit or underscore, or that contain anything other than letters, digits,
  combining marks, `.`, `_` and `-`. Use a safely named copy or a safe alias; nfclaw never renames a
  sample. The full rules: [inputs refused before launch](docs/preflight.md#inputs-refused-before-launch).
- **Recorded runtime corrections.** A few exact releases (fastqrepair 1.1.1, Bactmap, Createtaxdb and
  Funcscan) run with recorded corrections that leave the pinned source untouched. The run says so and
  records them ([source corrections](docs/source-corrections.md)).

---

## Where a run is logged and how to check it

Every `nfclaw run` logs itself to a fixed place, so there is no need to redirect its output. To find
out how a run stands, ask nfclaw:

```bash
nfclaw status <outdir>
nfclaw status <outdir> --json     # state, outcome, times, pids, logs, caveats, provenance gaps, error, last output
```

It prints `status: success`, `running (…)`, or the outcome the run ended with (`failed (exit status N)`,
`timed out after N s`, `interrupted`, `terminated by SIGTERM`, `refused before launch`). If nfclaw
itself was killed with SIGKILL, ran out of memory, filled the disk or the machine restarted, it
prints `stopped without an outcome`; `--resume` then continues from the finished tasks. After the
status come the log's location and the recorded error or the run's last output. A log that exists
but cannot be read is `unknown`. Exit codes: 0 success, 3 running, 1 anything else. It also works
for replays and chains.

**Success is not completeness.** A pipeline can exit 0 without some of its samples or tasks. When
its completion summary says so (nf-core's "…, but with errored process(es)", rnaseq's skipped
samples and failed strandedness checks), when Nextflow ignored failed tasks, or when a profile or
`--config` runs every task as a stub (`stubRun = true`, as proteinfold's `test` profile does, so its
`--demo` computes nothing), `nfclaw status` reports
`status: success — with caveats the pipeline reported about its results` and quotes them.
`nfclaw run` prints them as warnings and records them in `provenance/run_manifest.json`
(`completion_caveats`). Read them before using the results.

A successful run may also have gaps in what it recorded for replay: an image without a digest, a task
with no container, no task records. The results are unaffected, but a replay can check less.
`nfclaw status` lists these under `provenance gaps` (`provenance_gaps` with `--json`), and
`nfclaw chain status` beside each stage.

- **`<outdir>/provenance/logs/run.log`:** the whole launch in order. nfclaw's header (command, launch
  directory, Nextflow log path, host and pids, advisories), everything Nextflow printed (each line
  prefixed with `| `), gaps in the recorded environment (`provenance: …`) and, on failure, nfclaw's
  error. Its **last line**, written once nfclaw is done, is
  `==> nfclaw run finished <time>: <outcome>`. `--resume` appends to it, so a failed attempt is never
  overwritten. No run log means nfclaw never launched there: run the command in the foreground to see
  why.
- **`<outdir>/.nextflow.log`:** Nextflow's own detailed log. Nextflow runs from `--outdir`, so its
  hint "Check '.nextflow.log'" means this file, not one in your working directory.
- **`stdout.txt` and `stderr.txt` beside `run.log`:** Nextflow's two raw streams. Engines up to
  26.04 print error reports on stdout; from 26.10 the console log goes to stderr
  ([migration notes](https://docs.seqera.io/nextflow/migrations/26-10#breaking-changes)). Look at
  both when diagnosing a failure.

**Jobs started through MCP** can also be managed from a shell on the same host, as the same user and
with the same `NFCLAW_STATE_DIR`: `nfclaw jobs list`, `nfclaw jobs status <job-id>` and
`nfclaw jobs cancel <job-id>`. Add `--json` for a versioned object. Job status exits 0 for success,
3 while running, and 1 for failed, cancelled, lost or unknown jobs. Cancelling returns without
waiting; check the status to confirm the job stopped.
[Commands and JSON fields](docs/mcp.md#manage-jobs-from-the-shell).

To run in the background, start `nohup nfclaw run ... &`, and stop it with `kill <nfclaw pid>` (the
`pid:` line of the run log). nfclaw then shuts Nextflow and its tasks down, removes the task
containers they left behind, writes the bundle and closes the log, as on Ctrl-C. On Linux, if
nfclaw is killed outright (SIGKILL), its Nextflow receives SIGTERM; scheduler jobs and other
detached work still depend on the executor's own cleanup.

When a run fails, nfclaw's error quotes what Nextflow reported, adds the `Caused by:` chain from
`.nextflow.log` when the console hides the reason, and gives the absolute paths of the run log,
`.nextflow.log` and the failing task's `.command.err`. Fix the cause and run the same command again
with `--resume`. [`docs/known-issues.md`](docs/known-issues.md) maps symptoms to fixes.

---

## Replaying and verifying a run

`<outdir>/provenance/commands.sh` re-runs the recorded command into a **fresh** directory
(`<outdir>.replay` by default, or `./commands.sh /path/to/fresh-dir`). It refuses a target that
already holds files, because an nf-core pipeline cannot publish over a previous run's files. A
replay runs the pipeline again; it is a reproduction, not a `--resume`. Before it starts, its guard
checks that the recorded pipeline source, local input bytes (samplesheet data paths included),
parameters and configs are unchanged, and refuses rather than produce results that silently differ.
It logs to `<target>/provenance/logs/run.log` (`nfclaw status <target>` reads it;
`kill <replay pid>` stops it). After Nextflow succeeds, it compares its execution environment
(image digests, plugins, container engine, remote inputs) with the recording. Keep the original
bundle.

```bash
nfclaw verify results.replay --against results            # structure; pairs launch-stamped files
nfclaw verify results.replay --against results --strict   # also identical bytes, and environment if both recorded one
nfclaw verify results.replay --against results --require-environment   # complete environment evidence
nfclaw assess results.replay --contract runner/output_contracts/tumourevo-1.0.0-demo.json
```

`verify` compares files and directories by path and reports them as `identical`, `changed`,
`missing` or `extra`. Changed bytes may be metadata or a different result, so inspect them with tools
that understand the format. `assess` checks sample coverage and the parsed scientific content against
an explicit [output contract](docs/scientific-output-contracts.md); two contracts for exact demo pins
are supplied. What the bundle holds, what the guard checks, how `--resume` treats changed local
inputs, and what each verification mode can and cannot show: [replay and verification](docs/replay.md).

Trust `skill.md` and `reference.md` over your own memory: they are generated from the pinned commit.
To set a parameter beyond the essentials, look it up in `pipelines/<name>/reference.md`, which lists
every parameter with its allowed values and constraints. Do not invent a flag or a value.
`nfclaw run` rejects unknown flags, values outside the allowed set and clear type or shape errors
before it starts; `nf-schema` stays authoritative for the complete schema at run time. Numbers reach
Nextflow with their exact decimal value. Read `upstream/` only for deep dives.

---

## To chain pipelines (A, then B, then C)

A chain runs several pipelines in sequence. Each stage starts only after the previous one
**succeeded**, and its inputs are prepared from that stage's outputs (for fetchngs → rnaseq,
fetchngs's samplesheet becomes rnaseq's `--input`). Write a spec in JSON and run it:
```json
{
  "nxf_env": {"NXF_JVM_ARGS": "-Djava.net.preferIPv6Addresses=true"},
  "stages": [
    {"pipeline": "fetchngs", "input": "/abs/ids.csv", "retries": 2},
    {"pipeline": "rnaseq", "params": {"genome": "GRCh38"}}
  ]
}
```

Check it first:
```bash
nfclaw chain run spec.json --outdir /abs/chain --check
```
This validates every stage and handoff and checks that each stage's config parses with its engine,
leaving `--outdir` untouched. Then run the same command without `--check`.

- **Which pipeline can follow which:** `nfclaw chain edges [name]`, or the `## Chaining` section of a
  `skill.md`. Without a rule there is no chain, unless you give the stage an inline `"handoff"`.
- **Stage parameters:** a stage's `params` are its own flags (look them up in its `reference.md`).
  An explicit stage `input` or `params` value overrides the value a handoff would supply.
  `demo: true` adds that release's `test` profile.
- **Run options:** `profile`, `nxf_ver`, `nxf_env`, `config` and `limits` can be set on the chain or
  on a stage, since releases of different ages can need different engines. A stage's `nxf_env` is
  merged over the chain's; its `config` and `limits` replace the chain's. `--timeout SECONDS` sets
  one deadline for the whole chain.
- **Logs and state:** each stage is an ordinary run in `<outdir>/NN-<stage>/`. The chain logs to
  `<outdir>/chain/logs/chain.log`, whose **last line** is
  `==> nfclaw chain finished <time>: <outcome>`; `kill <pid>` stops it cleanly.
- **Resuming:** `nfclaw chain run [spec.json] --outdir /abs/chain --resume` skips the stages that
  succeeded and resumes the failed one (which you may change in the spec) with Nextflow's cache.
  `"retries": N` relaunches a stage after a pipeline failure, never after a validation error.
- **Lineage:** `nfclaw chain status <outdir>` (add `--json` for one object) checks by SHA-256 which
  run's outputs became which run's inputs. It exits 0 when the chain succeeded, 3 while it runs and 1
  otherwise; `--quick` skips the hashing. Handoff checks, sample isolation, secrets in `nxf_env` and
  failure handling: [`docs/chaining.md`](docs/chaining.md).

---

## Using nf-claw through MCP

`nfclaw mcp` serves this library to MCP clients (Claude Code, Codex, Antigravity, Hermes and others)
on stdio; [`docs/mcp.md`](docs/mcp.md) explains the setup for each client. Each tool runs the
`nfclaw` command it names, so everything in this guide applies unchanged:

- **Find and read:** `list_pipelines(query)`, then `show_pipeline(pipeline)` for its `skill.md`, or
  `show_pipeline(pipeline, document="reference", grep="…")` for any other parameter.
  `read_doc(guide="known-issues", search="…")` returns only the sections about an error or warning.
- **Run:** `run_pipeline(pipeline, outdir, input, params={…}, check=true)` validates and prints the
  command; without `check` it starts a detached job and returns its `job_id`. Pipeline parameters go
  in `params` under their schema names; nfclaw's own options (`profile`, `resume`, `nxf_env`,
  `limit_cpus`, …) are separate arguments.
- **Follow:** `get_job(job_id, wait_seconds=N)` reports `running` (`preparing` or `launched`),
  `succeeded`, `failed`, `cancelled` or `lost`, with `nfclaw status`'s report and the latest output.
  A job outlives the client and the server: any later session can read it back (`list_jobs`).
  `run_status(outdir)` reports on any run directory, with the parsed `nfclaw status --json` record.
- **Chain:** `run_chain(spec, outdir)` runs `nfclaw chain run` on a spec given as JSON;
  `run_status(outdir, chain=true)` checks the lineage.
- **Stop:** `cancel_job(job_id)` stops a job as `kill <nfclaw pid>` does; continue later with
  `resume=true`.

Use absolute paths and a new `outdir` per run, as on the command line.

---

## To run a specific (non-latest) version

By default a run uses the release pinned in this repository. Updates are checked before they are
adopted, so a newer upstream release may not be pinned yet. To run another published release:

1. **List releases:** `nfclaw versions <name>` (the pinned release is marked).
2. **Read that version's docs:** `nfclaw show <name> --pipeline-version X.Y.Z` fetches the tag,
   checks it out under `pipelines/<name>/.versions/X.Y.Z/` (ignored by Git) and prints the
   `skill.md` generated from that release's schema, with a `reference.md` beside it. Parameters,
   flags and validation all come from X.Y.Z.
3. **Run it:**
   ```bash
   nfclaw run <name> --pipeline-version X.Y.Z --input samplesheet.csv --outdir results -profile docker
   ```

Only real release tags are accepted: `X.Y.Z`, or `X.Y` for older nf-core releases such as fetchngs
`1.9`, with or without a leading `v`, plus `dev` (below). An unknown version fails at once and lists
the available ones. Provenance records the exact version that ran.

### Unreleased development code (`dev`)

`--pipeline-version dev` runs the `dev` branch (like `nextflow run nf-core/<name> -r dev`), which holds
changes not yet in any release:
```bash
nfclaw run fetchngs --pipeline-version dev --input ids.csv --outdir /path/to/out -profile docker
```
`dev` moves, so each run resolves it to the branch's current commit, checks that commit out under
`pipelines/<name>/.versions/dev-<commit12>/`, prints a warning naming it, and records it for replay.
Read its docs first (`nfclaw show <name> --pipeline-version dev`), because its parameters can differ
from the release. `nfclaw versions <name>` lists `dev` with its current commit. Offline, nfclaw uses
the last `dev` commit it fetched and says so, and `--resume` warns when `dev` has moved since the
run it continues. Prefer a release for results you need to reproduce from a version number.

---

## Choosing the Nextflow engine and environment

`nfclaw run` passes your shell environment on to Nextflow. Two flags make the engine and its
environment explicit and reproducible; both are recorded in `<outdir>/provenance/`:

- **`--nxf-ver X.Y.Z`** pins the Nextflow version for this run (it sets `NXF_VER`). Use it when a
  newer Nextflow breaks an older release, or to reproduce an earlier run exactly. Nextflow refuses
  an engine older than the release's declared `nextflowVersion` (see `skill.md`); nfclaw's error then
  names the `--nxf-ver` to pass, and `--check` warns about it instead.
- **`--nxf-env KEY=VALUE`** sets an `NXF_*` variable for this run (repeatable). Common uses:
  - on an IPv6-only host where the JVM cannot reach GitHub for remote configs:
    `--nxf-env NXF_JVM_ARGS=-Djava.net.preferIPv6Addresses=true`
  - to skip remote config fetches entirely: `--nxf-env NXF_OFFLINE=true`
- **`--config PATH`** (or `-c`, repeatable) passes an extra Nextflow config through as `-c`, for
  example a Docker host-network config (`docker { runOptions = "--network host" }`) or custom
  resources.

Each run launches Nextflow from its `--outdir`, so its `.nextflow/` history belongs to that run and
`--resume` resumes it (use a separate `--outdir` per pipeline). Task work files go to the shared
`<repo>/work/` directory by default; set `--nxf-env NXF_WORK=/path/to/work` to choose another, and
keep the work files that `--resume` and result symlinks need.

---

## Running on a machine smaller than the pipeline assumes

nf-core usually sizes processes with labels from the pipeline's `conf/base.config`, which assume a
server. One step can request far more memory than a workstation has
(`Process requirement exceeds available memory`), and retry rules can raise requests further. Many
bundled `test` profiles set small ceilings, but real runs often need one. Set it with:
```bash
nfclaw run <name> ... --limit-cpus 4 --limit-memory 15.GB
```
`--limit-time DURATION` also caps how long any one task may run. A task that needs longer is stopped,
and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the
analysis takes.

These become Nextflow's `process.resourceLimits`, applied to every process and every retry. They are
written to `<outdir>/provenance/resource_limits.config` and replayed by `commands.sh`.
`resourceLimits` needs Nextflow 24.04.0 or newer: older engines accept it but apply no ceiling. So
`nfclaw run` refuses `--limit-*` when the run would use an older engine or the engine version cannot
be identified; pin a newer engine with `--nxf-ver`, or use the release's own `--max-*` parameters
where it has them. Do not work around this with `withName:` overrides, which size only the processes
they name.

If a pipeline's `upstream/` is empty, initialise it first:
```bash
git submodule update --init pipelines/<name>/upstream
```
`nfclaw run` refuses a pinned `upstream/` that is not at the commit its `skill.md` documents (for
example after a `git pull` without a submodule update) or that has local edits to tracked files.
Restore it with `git submodule update --force pipelines/<name>/upstream`, or pass `--pipeline-version`
to run another release on purpose.

---

## Requirements

- **Linux or macOS** (on Windows, run nfclaw inside WSL 2)
- **Git**
- **Python 3.11+** (install nfclaw with `pip install -e .`)
- **Nextflow** (Java 17+)
- **Docker** or **Singularity/Apptainer**

> [!IMPORTANT]
> **Use paths without spaces.** Many bioinformatics tools and Nextflow's work directory mishandle
> spaces in paths; on macOS, also avoid iCloud folders. `nfclaw run` checks the repository path, the
> work directory and `--outdir` before launch and fails with the offending path (`--allow-spaces`
> overrides this).

---

## Reference genomes

Some releases fetch a reference **remotely by default**. sarek, for example, defaults `--genome` to
`GATK.GRCh38`, which it looks up in AWS iGenomes at `s3://ngi-igenomes/igenomes/`, so a run that
passes no reference of its own reads from S3 and fails on a host without access to that bucket. Each
`skill.md` says which case its pipeline is in, under "Reference genome". Pass your own reference
(`--fasta`, …) for a self-contained run, or `--igenomes-ignore true` to turn the lookup off.

---

## Warnings are not failures

A run or replay can print harmless upstream warnings. Examples: Nextflow reporting the `validation.*`
config scope as unrecognised (its linter does not see scopes that plugins add); a release setting a
parameter its own plugin removed (scrnaseq's `validationSchemaIgnoreParams`, which `nfclaw run`
neutralises in the config and announces); or a `test` profile that sets conflicting references on
purpose (rnaseq's `--gtf` with `--gff`). [`docs/known-issues.md`](docs/known-issues.md) lists them with
their real cause under "Warnings a run prints that are not faults"; check there before reporting one.
`nfclaw run` also announces measured run-to-run variation before launch (for example dada2
`assignTaxonomy` tie-breaking or unseeded QIIME2 rarefaction), so differences between runs or
replays are expected rather than treated as faults. nf-claw never modifies the pinned pipeline
source.
