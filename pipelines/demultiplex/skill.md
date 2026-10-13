---
name: demultiplex
pipeline: nf-core/demultiplex
version: 1.8.0
commit: daade37c4a75a4c1709ccf12434deb3424141319
description: Demultiplexing pipeline for Illumina sequencing data
summary: nf-core/demultiplex is a bioinformatics pipeline used to demultiplex the raw data produced by next generation sequencing machines. The following platforms are supported:
has_samplesheet: true
input: samplesheet (id, samplesheet, lane, flowcell, per_flowcell_manifest)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["fastp", "Falco", "MultiQC", "CheckQC", "samshee"]
feeds: ["atacseq", "methylseq", "rnaseq", "sarek", "seqinspector", "taxprofiler"]
---
# demultiplex

nf-core/demultiplex is a bioinformatics pipeline used to demultiplex the raw data produced by next generation sequencing machines. The following platforms are supported:

## Run it
```bash
git submodule update --init pipelines/demultiplex/upstream   # first time only
nfclaw run demultiplex --input samplesheet.csv --outdir results -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/demultiplex/upstream -profile docker --input samplesheet.csv --outdir results
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions demultiplex` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show demultiplex --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show demultiplex --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `id` | string | yes |  | matches ^\S+$ |
| `samplesheet` | string (file path) | yes |  | matches ^\S+\.csv$ |
| `lane` | integer | no |  | ≥ 1; ≤ 8 |
| `flowcell` | string (file or directory path) | yes |  |  |
| `per_flowcell_manifest` | string (file path) | no |  |  |

`--input` must match `^\S+\.csv$`.

The samplesheet is a CSV with this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
id,samplesheet,flowcell
```

Any of the optional columns above may be appended to the header when your data needs them: `lane`, `per_flowcell_manifest`.

**From data files.** `--input` may also be the data files — a directory (searched recursively), a quoted glob, or files (`--input` once per file) — from which nfclaw writes this samplesheet: `id` from file names; `samplesheet` from files matching their patterns, by sample name. Set the required columns no file determines with `--sheet-set COLUMN=VALUE` (a constant or a `{sample}`/`{lane}` template): `flowcell` (string). Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--demultiplexer` | string | bclconvert | `bases2fastq`, `bcl2fastq`, `bclconvert`, `fqtk`, `sgdemux`, `mkfastq`, `mgikit` |  | Demultiplexer to use. |

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, default, allowed values and constraints — organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **CheckQC options** (`checkqc_options`) — 1 parameter
- **Demultiplexing options** (`demultiplex_options`) — 1 parameter
- **Downstream CSV options** (`downstream_csv_options`) — 1 parameter
- **Generic options** (`generic_options`) — 16 parameters
- **Input/output options** (`input_output_options`) — 10 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **Workflow options** (`workflow_options`) — 9 parameters

## Resources
Resource requests follow the pipeline's configs and selected profiles. nf-core's resource labels often assume a server — a single step can request far more memory than a workstation has, and retry rules can increase requests. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run demultiplex --input samplesheet.csv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=25.10.4'`.

To pin this release's declared minimum engine — useful when a newer Nextflow has incompatible config parsing:
```bash
nfclaw run demultiplex ... --nxf-ver 25.10.4
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/demultiplex/blob/1.8.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Chaining
Run demultiplex as one stage of a chain: `nfclaw chain run spec.json --outdir DIR` starts each stage only after the one before it succeeded, and prepares its inputs from that stage's outputs. The rules live in `handoffs/` (format and spec in [docs/chaining.md](../../docs/chaining.md)); list them with `nfclaw chain edges demultiplex`.

Feeds into:
- `atacseq` — demultiplex writes samplesheet/atacseq_samplesheet.csv (every sample as replicate 1) for its demultiplexed FastQ files; a single-end run's sheet lacks the fastq_2 column, which atacseq's own sheet check requires, so it is added empty.
- `methylseq` — demultiplex writes samplesheet/methylseq_samplesheet.csv for its demultiplexed FastQ files.
- `rnaseq` — demultiplex writes samplesheet/rnaseq_samplesheet.csv for its demultiplexed FastQ files (strandedness from its --strandedness, default auto).
- `sarek` — demultiplex writes samplesheet/sarek_samplesheet.csv with an empty patient; each sample is made its own patient (set it per sample yourself if several samples share one); sarek reads paired-end FastQ only, so every row needs a fastq_2. No status or sex column is written: sarek treats every sample as normal tissue (status 0, sex NA) and runs germline analyses only; a tumour/normal design needs its own sarek samplesheet (a handoff's set gives every row the same value).
- `seqinspector` — demultiplex writes samplesheet/seqinspector_samplesheet.csv for its demultiplexed FastQ files.
- `taxprofiler` — demultiplex writes samplesheet/taxprofiler_samplesheet.csv without run_accession or instrument_platform; each sample becomes its own run, sequenced on ILLUMINA (bcl2fastq/bclconvert data — use an inline handoff for other platforms).

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: fastp, Falco, MultiQC, CheckQC, samshee.

Full list with references: https://github.com/nf-core/demultiplex/blob/1.8.0/CITATIONS.md

## Demo
```bash
nfclaw run demultiplex --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

## Full reference
Every parameter — name, type, required, hidden, allowed values, constraints, default and description — is in [reference.md](reference.md). Use it as the source of truth; do not guess flags. nfclaw checks explicit parameters before launch; the pinned pipeline's validation handles conditional and complex constraints at runtime. The reference uses nfclaw's hyphenated flags; raw Nextflow requires the exact schema spelling (usually underscores). Upstream usage: https://github.com/nf-core/demultiplex/blob/1.8.0/docs/usage.md

<!-- Generated from nf-core/demultiplex@daade37c4a75a4c1709ccf12434deb3424141319. Do not edit by hand. -->
