---
name: stableexpression
pipeline: nf-core/stableexpression
version: 1.1.0
commit: c4cbf82471391990cae257c0212be86f6b4fb18b
description: This pipeline is dedicated to identifying the most stable genes within a single or multiple expression dataset(s). This is particularly useful for identifying the most suitable RT-qPCR reference genes for a specific species.
summary: nf-core/stableexpression is a bioinformatics pipeline that aims to identify the most stable genes in one or more expression datasets. These datasets can be downloaded from public databases such as EBI Expression Atlas and NCBI GEO Datasets, or provided directly by the user. Both RNA-seq and microarray count datasets can be used. The pipeline is ideally suited to determining the most suitable RT-qPCR reference genes for a given species.
has_samplesheet: false
input: parameters (no samplesheet)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["EBI Expression Atlas", "NCBI GEO", "g:Profiler", "Scikit-learn", "Normfinder", "GeNorm", "MultiQC"]
---
# stableexpression

nf-core/stableexpression is a bioinformatics pipeline that aims to identify the most stable genes in one or more expression datasets. These datasets can be downloaded from public databases such as EBI Expression Atlas and NCBI GEO Datasets, or provided directly by the user. Both RNA-seq and microarray count datasets can be used. The pipeline is ideally suited to determining the most suitable RT-qPCR reference genes for a given species.

## Run it
```bash
git submodule update --init pipelines/stableexpression/upstream   # first time only
nfclaw run stableexpression --outdir results -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/stableexpression/upstream -profile docker --outdir results
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions stableexpression` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show stableexpression --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show stableexpression --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
This pipeline does not use a samplesheet; configure inputs via parameters.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--outdir` | string (directory path) |  |  |  | Output directory |

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, required, hidden, allowed values, constraints, default and description. Use it as the source of truth; do not guess flags. It uses nfclaw's hyphenated flags; raw Nextflow requires the exact schema spelling (usually underscores). nfclaw checks explicit parameters before launch; the pinned pipeline's validation handles conditional and complex constraints at runtime. It is organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Generic options** (`generic_options`) — 15 parameters
- **ID mapping options** (`idmapping_options`) — 7 parameters
- **Input/output options** (`input_output_options`) — 11 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **Missing value imputation options** (`missing_value_imputation_options`) — 1 parameter
- **Normalisation options** (`normalisation_options`) — 5 parameters
- **Public data options** (`public_data_options`) — 6 parameters
- **Sample filtering options** (`sample_filtering_options`) — 3 parameters
- **Scalability options** (`scalability_options`) — 2 parameters
- **Stability scoring options** (`stability_scoring_options`) — 4 parameters

Upstream usage: https://github.com/nf-core/stableexpression/blob/1.1.0/docs/usage.md

## Resources
Resource requests follow the pipeline's configs and selected profiles. nf-core's resource labels often assume a server — a single step can request far more memory than a workstation has, and retry rules can increase requests. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run stableexpression --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=26.04.4'`.

To pin this release's declared minimum engine — useful when a newer Nextflow has incompatible config parsing:
```bash
nfclaw run stableexpression ... --nxf-ver 26.04.4
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/stableexpression/blob/1.1.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: EBI Expression Atlas, NCBI GEO, g:Profiler, Scikit-learn, Normfinder, GeNorm, MultiQC.

Full list with references: https://github.com/nf-core/stableexpression/blob/1.1.0/CITATIONS.md

## Demo
```bash
nfclaw run stableexpression --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

<!-- Generated from nf-core/stableexpression@c4cbf82471391990cae257c0212be86f6b4fb18b. Do not edit by hand. -->
