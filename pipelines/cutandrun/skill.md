---
name: cutandrun
pipeline: nf-core/cutandrun
version: 3.2.2
commit: 6e1125d4fee4ea7c8b70ed836bb0e92a89e3305f
description: Analysis pipeline for CUT&RUN and CUT&TAG experiments that includes sequencing QC, spike-in normalisation, IgG control normalisation, peak calling and downstream peak analysis.
summary: nf-core/cutandrun is a best-practice bioinformatic analysis pipeline for CUT&RUN, CUT&Tag, and TIPseq experimental protocols that were developed to study protein-DNA interactions and epigenomic profiling.
has_samplesheet: true
input: samplesheet (group, replicate, fastq_1, fastq_2, control)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["FastQC", "MultiQC", "bedtools", "samtools", "bowtie2", "deeptools", "seacr", "macs2", "picard"]
---
# cutandrun

nf-core/cutandrun is a best-practice bioinformatic analysis pipeline for CUT&RUN, CUT&Tag, and TIPseq experimental protocols that were developed to study protein-DNA interactions and epigenomic profiling.

## Run it
```bash
git submodule update --init pipelines/cutandrun/upstream   # first time only
nfclaw run cutandrun --input samplesheet.csv --outdir results -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/cutandrun/upstream -profile docker --input samplesheet.csv --outdir results
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions cutandrun` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show cutandrun --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show cutandrun --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `group` | string | yes |  | matches ^\S+$ |
| `replicate` | integer | yes |  | matches ^[0-9]*$ |
| `fastq_1` | string | yes |  | matches ^\S+\.f(ast)?q\.gz$ |
| `fastq_2` | string | yes |  | matches ^\S+\.f(ast)?q\.gz$ |
| `control` | string | yes |  | matches ^\S+$ |

`--input` must match `^\S+\.csv$`.

The samplesheet is a CSV with this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
group,replicate,fastq_1,fastq_2,control
```

**From data files.** `--input` may also be the data files — a directory (searched recursively), a quoted glob, or files (`--input` once per file) — from which nfclaw writes this samplesheet: `fastq_1`/`fastq_2` from FastQ files (mates paired by `_R1`/`_R2`, or by `_1`/`_2` when their read names show they are mates). Set the required columns no file determines with `--sheet-set COLUMN=VALUE` (a constant or a `{sample}`/`{lane}` template): `group` (matching ^\S+$); `replicate` (matching ^[0-9]*$); `control` (matching ^\S+$). Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file path) |  |  | matches ^\S+\.csv$ | Path to comma-separated file containing information about the samples in the experiment. |
| `--outdir` | string (directory path) | ./results |  |  | The output directory where the results will be saved. You have to use absolute paths to store on Cloud infrastructure. |

## Reference genome
No reference genome is set by default: supply your own reference. A genome name alone does not specify where reference files come from. Confirm the selected reference's paths and source in the pinned `upstream/nextflow.config` and `upstream/conf/` before running. To supply your own reference, use e.g. `--fasta`; the `reference_data_options` group in [reference.md](reference.md) lists every reference option. Set `--igenomes-ignore true` to disable the lookup entirely.

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, required, hidden, allowed values, constraints, default and description. Use it as the source of truth; do not guess flags. It uses nfclaw's hyphenated flags; raw Nextflow requires the exact schema spelling (usually underscores). nfclaw checks explicit parameters before launch; the pinned pipeline's validation handles conditional and complex constraints at runtime. It is organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Flow switching options** (`flow_switching_options`) — 16 parameters
- **Generic options** (`generic_options`) — 16 parameters
- **Input/output options** (`input_output_options`) — 11 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **Max job request options** (`max_job_request_options`) — 3 parameters
- **Pipeline Options** (`pipeline_options`) — 25 parameters
- **Reference data options** (`reference_data_options`) — 10 parameters
- **Reporting Options** (`reporting_options`) — 11 parameters
- **Trimming Options** (`trimming_options`) — 5 parameters

Upstream usage: https://github.com/nf-core/cutandrun/blob/3.2.2/docs/usage.md

## Resources
Resource requests follow the pipeline's configs and selected profiles. nf-core's resource labels often assume a server — a single step can request far more memory than a workstation has, and retry rules can increase requests. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run cutandrun --input samplesheet.csv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=23.04.0'`.

To pin this release's declared minimum engine — useful when a newer Nextflow has incompatible config parsing:
```bash
nfclaw run cutandrun ... --nxf-ver 23.04.0
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

Nextflow 23.04.0 predates `process.resourceLimits` (24.04.0), so `--limit-*` cannot be combined with this pin — nfclaw refuses it rather than run without the ceiling; cap resources with the release's own `--max-cpus`, `--max-memory`, `--max-time` instead.

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `--skip-multiqc true` disables that report. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/cutandrun/blob/3.2.2/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: FastQC, MultiQC, bedtools, samtools, bowtie2, deeptools, seacr, macs2, picard.

Full list with references: https://github.com/nf-core/cutandrun/blob/3.2.2/CITATIONS.md

## Demo
```bash
nfclaw run cutandrun --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

<!-- Generated from nf-core/cutandrun@6e1125d4fee4ea7c8b70ed836bb0e92a89e3305f. Do not edit by hand. -->
