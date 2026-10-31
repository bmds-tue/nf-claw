---
name: bacmodel
pipeline: nf-core/bacmodel
version: 1.0.1
commit: 8a9ad093d0431b4f69fa829513248c7863f37d7f
description: Systems-based bacterial functional modeling pipeline
summary: nf-core/bacmodel is a bioinformatics pipeline for comprehensive functional annotation and metabolic modeling of bacterial genomes. The pipeline takes bacterial genome assemblies (FASTA format) and performs the following steps:
has_samplesheet: true
input: samplesheet (sample, fasta, medium_gapseq, medium_gapseq_csv, medium_carveme, medium_carveme_tsv)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled)
tools: ["Prokka", "Bakta", "MacSyFinder", "TRAITAR", "CarveMe", "gapseq", "MEMOTE"]
---
# bacmodel

nf-core/bacmodel is a bioinformatics pipeline for comprehensive functional annotation and metabolic modeling of bacterial genomes. The pipeline takes bacterial genome assemblies (FASTA format) and performs the following steps:

## Run it
```bash
git submodule update --init pipelines/bacmodel/upstream   # first time only
nfclaw run bacmodel --input samplesheet.csv --outdir results -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/bacmodel/upstream -profile docker --input samplesheet.csv --outdir results
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions bacmodel` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show bacmodel --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show bacmodel --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `sample` | string | yes |  | matches `^\S+$` |
| `fasta` | string (file path) | yes |  | matches `^\S+\.(f(ast)?a\|fna)(\.gz)?$` |
| `medium_gapseq` | string | no | , `ALLmed`, `FT`, `LBmed`, `LBmed_glucose_suppl`, `M9_serine_galacturonate`, `M9_vit_aa`, `MM_anaerobic_Acetate`, `MM_anaerobic_Acetate_H2`, `MM_anaerobic_CO2_H2`, `MM_glu-thm`, `MM_glu`, `TSBmed`, `autotrophic`, `dsmz_1611_YCFA`, `gut`, `meerwasser` |  |
| `medium_gapseq_csv` | string | no |  | matches `^(\S+\.csv)?$` |
| `medium_carveme` | string | no |  | matches `^[^\s/]*$` |
| `medium_carveme_tsv` | string | no |  | matches `^(\S+\.tsv)?$` |

`--input` must match `^\S+\.(csv|tsv)$`.

For tabular CSV/TSV input, use this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
sample,fasta
```

Any of the optional columns above may be appended to the header when your data needs them: `medium_gapseq`, `medium_gapseq_csv`, `medium_carveme`, `medium_carveme_tsv`.

**From data files.** `--input` may also be the data files — a directory (searched recursively), a quoted glob, or files (`--input` once per file) — from which nfclaw writes this samplesheet: `sample` from file names; `fasta`, `medium_gapseq_csv`, `medium_carveme_tsv` from files matching their patterns, by sample name. Set other columns with `--sheet-set COLUMN=VALUE`. Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file path) |  |  | matches `^\S+\.(csv\|tsv)$` | Path to comma-separated or tab-separated file containing information about the samples in the experiment. |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, required, hidden, allowed values, constraints, default and description. Use it as the source of truth; do not guess flags. It uses nfclaw's hyphenated flags; raw Nextflow requires the exact schema spelling (usually underscores). nfclaw checks explicit parameters before launch; the pinned pipeline's validation handles conditional and complex constraints at runtime. It is organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Analysis options** (`analysis_options`) — 16 parameters
- **Annotation options** (`annotation_options`) — 4 parameters
- **Database options** (`database_options`) — 1 parameter
- **Deprecated options** (`deprecated_options`) — 5 parameters
- **Generic options** (`generic_options`) — 11 parameters
- **Input/output options** (`input_output_options`) — 3 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters

Upstream usage: https://github.com/nf-core/bacmodel/blob/1.0.1/docs/usage.md

## Resources
Resource requests follow the pipeline's configs and selected profiles. nf-core's resource labels often assume a server — a single step can request far more memory than a workstation has, and retry rules can increase requests. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run bacmodel --input samplesheet.csv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=25.10.4'`.

To pin this release's declared minimum engine — useful when a newer Nextflow has incompatible config parsing:
```bash
nfclaw run bacmodel ... --nxf-ver 25.10.4
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/bacmodel/blob/1.0.1/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: Prokka, Bakta, MacSyFinder, TRAITAR, CarveMe, gapseq, MEMOTE.

Full list with references: https://github.com/nf-core/bacmodel/blob/1.0.1/CITATIONS.md

## Demo
```bash
nfclaw run bacmodel --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

<!-- Generated from nf-core/bacmodel@8a9ad093d0431b4f69fa829513248c7863f37d7f. Do not edit by hand. -->
