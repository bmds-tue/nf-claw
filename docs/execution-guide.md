# Execution, input integrity and monitoring

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
   Prints `success`, `running`, or how it ended with the error (exit codes: `0` success, `3` running, `1` failed). Logs: see [Where a run is logged](execution-guide.md#where-a-run-is-logged--and-how-to-check-one).

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

## Requirements (agent environment)

- **Git**
- **Python 3.11+** (install nfclaw with `pip install -e .`)
- **Nextflow** (Java 17+)
- **Docker** or **Singularity/Apptainer**

> [!IMPORTANT]
> **Use a space-free path on macOS and Linux:** Many bioinformatics tools and Nextflow's work directory mishandle spaces in paths; on macOS also avoid iCloud paths.

---

## Reference genomes

Some releases resolve a reference **remotely by default** — sarek defaults `--genome` to `GATK.GRCh38`, looked up in AWS iGenomes at `s3://ngi-igenomes/igenomes/` — so a run that passes no reference of its own reads from S3 and fails on a host without access to that bucket. Each `skill.md` states which case its pipeline is in under "Reference genome". Pass your own reference (`--fasta`, …) for a self-contained run, or `--igenomes-ignore true` to disable the lookup.

---

## Warnings are not failures

A run or replay can print benign upstream warnings: Nextflow reporting the `validation.*` config scope as unrecognised (its linter does not see plugin-contributed scopes — upstream nf-schema issue), a pinned release setting a parameter its own plugin removed (scrnaseq's `validationSchemaIgnoreParams` — `nfclaw run` neutralises this one at the config layer via nf-schema's `validation.ignoreParams` and prints an advisory recording that it did, leaving the pinned tree untouched), or a `test` profile that deliberately sets conflicting references (rnaseq's `--gtf` with `--gff`). They are catalogued with their real cause in [`docs/known-issues.md`](known-issues.md) under "Warnings a run prints that are not faults". Check there before reporting one. `nfclaw run` also announces measured run-to-run variability before launch (e.g. dada2 `assignTaxonomy` tie-breaking or unseeded QIIME2 rarefaction) when task scripts contain them, so differences across runs or replays are anticipated rather than treated as faults. Replay runs the recorded analysis into a fresh directory, removes `-resume`, and pins the observed engine version; warning text can vary with plugin resolution and cached configuration even when scientific outputs agree. nf-claw keeps the pinned pipeline source unmodified.

---

## Run-time errors

Spaces in a path break many tools, so `nfclaw run` checks the repo path, the Nextflow work directory and `--outdir` **before** launching and **fails fast** naming the offending path (pass `--allow-spaces` to override) — a deterministic check, not a guess. For other failures (IPv6 host, no-network database downloads, a too-new Nextflow config parser, known upstream-pipeline bugs) the error quotes Nextflow's own report and names the run log, `.nextflow.log` and the failing task's files by absolute path (see [Where a run is logged](execution-guide.md#where-a-run-is-logged--and-how-to-check-one)); the symptom→fix map is in [`docs/known-issues.md`](known-issues.md).

Use [result acceptance](result-acceptance.md) to reject selected completion caveats and [structured diagnostics/status](structured-results.md) for automation.
