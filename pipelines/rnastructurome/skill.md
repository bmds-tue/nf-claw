---
name: rnastructurome
pipeline: nf-core/rnastructurome
version: 1.1.0
commit: 633ab1d0d12103f9002fe6e781ae1251df2d2656
description: This pipeline analyses chemical-based high-throughput RNA structure probing data
summary: nf-core/rnastructurome is a bioinformatics pipeline for analysing chemical high-throughput RNA structure-probing data. It takes a samplesheet and FASTQ files from SHAPE or DMS experiments (read out by either the RT-stop or mutational profiling (MaP) principle) then performs quality control, trimming and alignment, quantifies per-base reactivity, and predicts RNA secondary structures. Outputs include normalised reactivity, Shannon entropy and base-pair arc tracks, 2D structure diagrams, RMDB-compatible RDAT files, and an aggregated QC report. References can be supplied locally or fetched automatically from Ensembl or NCBI, so the pipeline works across a wide range of organisms, including viruses and bacteria.
has_samplesheet: true
input: samplesheet (sample, sample_id, fastq_1, fastq_2, method, principle, chemical, RT_enzyme, organism, pH, adapter_3p, adapter_5p, umi_pattern, condition, sample_group, replicate, group)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["FastQC", "UMI-tools", "Cutadapt", "GffRead", "STAR", "Bowtie", "Bowtie2", "SAMtools", "BEDOPS", "RSeQC", "RNAFramework", "Four-base DMS analysis", "UCSC wigToBigWig", "R2DT", "ViennaRNA", "RNAalifold", "MultiQC"]
---
# rnastructurome

nf-core/rnastructurome is a bioinformatics pipeline for analysing chemical high-throughput RNA structure-probing data. It takes a samplesheet and FASTQ files from SHAPE or DMS experiments (read out by either the RT-stop or mutational profiling (MaP) principle) then performs quality control, trimming and alignment, quantifies per-base reactivity, and predicts RNA secondary structures. Outputs include normalised reactivity, Shannon entropy and base-pair arc tracks, 2D structure diagrams, RMDB-compatible RDAT files, and an aggregated QC report. References can be supplied locally or fetched automatically from Ensembl or NCBI, so the pipeline works across a wide range of organisms, including viruses and bacteria.

## Run it
```bash
git submodule update --init pipelines/rnastructurome/upstream   # first time only
nfclaw run rnastructurome --input samplesheet.csv --outdir results -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/rnastructurome/upstream -profile docker --input samplesheet.csv --outdir results
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions rnastructurome` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show rnastructurome --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show rnastructurome --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `sample` | string | yes |  | matches ^\S+$ |
| `sample_id` | string | no |  |  |
| `fastq_1` | string (file path) | yes |  | matches ^([\S\s]*\/)?[^\s\/]+\.f(ast)?q\.gz$ |
| `fastq_2` | string (file path) | no |  | matches ^([\S\s]*\/)?[^\s\/]+\.f(ast)?q\.gz$ |
| `method` | string | no |  |  |
| `principle` | string | no |  |  |
| `chemical` | string | no |  |  |
| `RT_enzyme` | string | no |  |  |
| `organism` | string | no |  |  |
| `pH` | number | no |  |  |
| `adapter_3p` | string | no |  |  |
| `adapter_5p` | string | no |  |  |
| `umi_pattern` | string | no |  |  |
| `condition` | string | yes | `treated`, `untreated`, `denatured` |  |
| `sample_group` | string | yes |  | matches ^\S+$ |
| `replicate` | string or integer | yes |  |  |
| `group` | string | no |  | matches ^\S+$ |

`--input` must match `^\S+\.csv$`.

The samplesheet is a CSV with this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
sample,fastq_1,condition,sample_group,replicate
```

Any of the optional columns above may be appended to the header when your data needs them: `sample_id`, `fastq_2`, `method`, `principle`, `chemical`, `RT_enzyme`, `organism`, `pH`, `adapter_3p`, `adapter_5p`, `umi_pattern`, `group`.

**From data files.** `--input` may also be the data files — a directory (searched recursively), a quoted glob, or files (`--input` once per file) — from which nfclaw writes this samplesheet: `sample` from file names; `fastq_1`/`fastq_2` from FastQ files (mates paired by `_R1`/`_R2`, or by `_1`/`_2` when their read names show they are mates). Set the required columns no file determines with `--sheet-set COLUMN=VALUE` (a constant or a `{sample}`/`{lane}` template): `condition` (one of treated, untreated, denatured); `sample_group` (matching ^\S+$); `replicate` (string or integer). Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file path) |  |  | matches ^\S+\.csv$ | Path to comma-separated file containing information about the samples in the experiment. |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, default, allowed values and constraints — organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Alignment options** (`alignment_options`) — 23 parameters
- **Executor options** (`executor_options`) — 3 parameters
- **Generic options** (`generic_options`) — 16 parameters
- **Input/output options** (`input_output_options`) — 4 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **Read trimming options** (`read_trimming_options`) — 10 parameters
- **Reference genome options** (`reference_genome_options`) — 7 parameters
- **RNAframework options** (`rnaframework_options`) — 111 parameters
- **Sample metadata options** (`sample_metadata_options`) — 10 parameters

## Resources
Resource requests follow the pipeline's configs and selected profiles. nf-core's resource labels often assume a server — a single step can request far more memory than a workstation has, and retry rules can increase requests. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run rnastructurome --input samplesheet.csv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=25.10.4'`.

To pin this release's declared minimum engine — useful when a newer Nextflow has incompatible config parsing:
```bash
nfclaw run rnastructurome ... --nxf-ver 25.10.4
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/rnastructurome/blob/1.1.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: FastQC, UMI-tools, Cutadapt, GffRead, STAR, Bowtie, Bowtie2, SAMtools, BEDOPS, RSeQC, RNAFramework, Four-base DMS analysis, UCSC wigToBigWig, R2DT, ViennaRNA, RNAalifold, MultiQC.

Full list with references: https://github.com/nf-core/rnastructurome/blob/1.1.0/CITATIONS.md

## Demo
```bash
nfclaw run rnastructurome --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

## Full reference
Every parameter — name, type, required, hidden, allowed values, constraints, default and description — is in [reference.md](reference.md). Use it as the source of truth; do not guess flags. nfclaw checks explicit parameters before launch; the pinned pipeline's validation handles conditional and complex constraints at runtime. The reference uses nfclaw's hyphenated flags; raw Nextflow requires the exact schema spelling (usually underscores). Upstream usage: https://github.com/nf-core/rnastructurome/blob/1.1.0/docs/usage.md

<!-- Generated from nf-core/rnastructurome@633ab1d0d12103f9002fe6e781ae1251df2d2656. Do not edit by hand. -->
