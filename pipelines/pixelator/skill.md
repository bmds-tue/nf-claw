---
name: pixelator
pipeline: nf-core/pixelator
version: 5.0.3
commit: d7376a8bca8b262b858ed440b6dd49c1853911e8
description: Pipeline for analysis of Proximity Network Assay data
summary: nf-core/pixelator is a bioinformatics best-practice analysis pipeline for analysis of data from the Proximity Network (PNA) assay. It takes a samplesheet as input and will process your data using pixelator to produce a PXL file containing single-cell protein abundance and protein interactomics data.
has_samplesheet: true
input: samplesheet (pool, hash_index, sample, sample_alias, condition, design, panel, panel_file, fastq_1, fastq_2)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled)
tools: ["pixelator", "cutadapt", "fastp"]
---
# pixelator

nf-core/pixelator is a bioinformatics best-practice analysis pipeline for analysis of data from the Proximity Network (PNA) assay. It takes a samplesheet as input and will process your data using pixelator to produce a PXL file containing single-cell protein abundance and protein interactomics data.

## Run it
```bash
git submodule update --init pipelines/pixelator/upstream   # first time only
nfclaw run pixelator --input samplesheet.csv --outdir results --technology <technology> -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/pixelator/upstream -profile docker --input samplesheet.csv --outdir results --technology <technology>
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions pixelator` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show pixelator --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show pixelator --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `pool` | string | no |  | matches `^\S+$` |
| `hash_index` | integer | no |  |  |
| `sample` | string | yes |  | matches `^\S+$` |
| `sample_alias` | string | yes |  |  |
| `condition` | string | yes |  |  |
| `design` | string | yes |  | matches `^\S+$` |
| `panel` | string | no |  | matches `^\S+$` |
| `panel_file` | string | no |  | matches `^$\|^\S+\.(csv\|tsv\|ya?ml)$` |
| `fastq_1` | string | yes |  | matches `^\S+\.f(ast)?q\.gz$` |
| `fastq_2` | string | no |  | matches `^\S+\.f(ast)?q\.gz$` |

`--input` must match `^\S+\.(csv|tsv|yml|yaml)$`.

For tabular CSV/TSV input, use this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
sample,sample_alias,condition,design,fastq_1
```

Any of the optional columns above may be appended to the header when your data needs them: `pool`, `hash_index`, `panel`, `panel_file`, `fastq_2`.

**From data files.** `--input` may also be the data files — a directory (searched recursively), a quoted glob, or files (`--input` once per file) — from which nfclaw writes this samplesheet: `sample` from file names; `fastq_1`/`fastq_2` from FastQ files (mates paired by `_R1`/`_R2`, or by `_1`/`_2` when their read names show they are mates); `panel_file` from files matching their patterns, by sample name. Set the required columns no file determines with `--sheet-set COLUMN=VALUE` (a constant or a `{sample}`/`{lane}` template): `sample_alias` (string); `condition` (string); `design` (matching ^\S+$). Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file path) |  |  | matches `^\S+\.(csv\|tsv\|yml\|yaml)$` | Path to comma-separated file containing information about the samples in the experiment. |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--technology` | string |  | `proxiome-v1`, `proxiome-v2`, `hashed_samples`, `nonhashed_samples` |  | The technology used to process the samples |

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, required, hidden, allowed values, constraints, default and description. Use it as the source of truth; do not guess flags. It uses nfclaw's hyphenated flags; raw Nextflow requires the exact schema spelling (usually underscores). nfclaw checks explicit parameters before launch; the pinned pipeline's validation handles conditional and complex constraints at runtime. It is organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Experiment Summary options** (`experiment_summary_options`) — 1 parameter
- **Generic options** (`generic_options`) — 12 parameters
- **Global options** (`global_config_options`) — 5 parameters
- **Input/output options** (`input_output_options`) — 4 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **Amplicon options** (`pna_amplicon_options`) — 9 parameters
- **Analysis options** (`pna_analysis_options`) — 7 parameters
- **Collapse options** (`pna_collapse_options`) — 3 parameters
- **Demux options** (`pna_demux_options`) — 7 parameters
- **Denoise options** (`pna_denoise_options`) — 9 parameters
- **Graph options** (`pna_graph_options`) — 13 parameters
- **Layout options** (`pna_layout_options`) — 5 parameters
- **Sample calling options** (`pna_sample_calling_options`) — 4 parameters

Upstream usage: https://github.com/nf-core/pixelator/blob/5.0.3/docs/usage.md

## Resources
Resource requests follow the pipeline's configs and selected profiles. nf-core's resource labels often assume a server — a single step can request far more memory than a workstation has, and retry rules can increase requests. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run pixelator --input samplesheet.csv --outdir results --technology <technology> -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=25.10.4'`.

To pin this release's declared minimum engine — useful when a newer Nextflow has incompatible config parsing:
```bash
nfclaw run pixelator ... --nxf-ver 25.10.4
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/pixelator/blob/5.0.3/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: pixelator, cutadapt, fastp.

Full list with references: https://github.com/nf-core/pixelator/blob/5.0.3/CITATIONS.md

## Demo
```bash
nfclaw run pixelator --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

<!-- Generated from nf-core/pixelator@d7376a8bca8b262b858ed440b6dd49c1853911e8. Do not edit by hand. -->
