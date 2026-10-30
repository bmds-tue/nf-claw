---
name: bacass
pipeline: nf-core/bacass
version: 2.6.1
commit: 5ed7c2dd9a05d2434d8ba39ace1116368a4ba570
description: Simple bacterial assembly and annotation
summary: nf-core/bacass is a bioinformatics best-practice analysis pipeline for simple bacterial assembly and annotation. The pipeline is able to assemble short reads, long reads, or a mixture of short and long reads (hybrid assembly).
has_samplesheet: true
input: samplesheet (ID, R1, R2, LongFastQ, Fast5, GenomeSize)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["FastQC", "FastP", "Porechop", "NanoPlot", "ToulligQC", "pycoQC", "Unicycler", "MEGAHIT", "Miniasm", "Canu", "Flye", "Raven", "Autocycler", "QUAST", "Prokka", "DFAST", "Liftoff", "Medaka", "Nanopolish", "SAMtools", "Kraken2", "Rasusa", "MultiQC"]
---
# bacass

nf-core/bacass is a bioinformatics best-practice analysis pipeline for simple bacterial assembly and annotation. The pipeline is able to assemble short reads, long reads, or a mixture of short and long reads (hybrid assembly).

## Run it
```bash
git submodule update --init pipelines/bacass/upstream   # first time only
nfclaw run bacass --input samplesheet.csv --outdir results -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/bacass/upstream -profile docker --input samplesheet.csv --outdir results
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions bacass` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show bacass --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show bacass --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `ID` | string | yes |  | matches `^\S+$` |
| `R1` | ['string', 'null'] or string | no |  |  |
| `R2` | ['string', 'null'] or string | no |  |  |
| `LongFastQ` | ['string', 'null'] or string | no |  |  |
| `Fast5` | ['string', 'null'] or string | no |  |  |
| `GenomeSize` | ['string', 'null'] or string | no |  |  |

The samplesheet is a CSV with this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
ID
```

Any of the optional columns above may be appended to the header when your data needs them: `R1`, `R2`, `LongFastQ`, `Fast5`, `GenomeSize`.

**From data files.** `--input` may also be the data files — a directory (searched recursively), a quoted glob, or files (`--input` once per file) — from which nfclaw writes this samplesheet once you choose the read columns: the samplesheet takes reads in several column groups (R1 + R2; LongFastQ) and file names cannot tell which yours belong in; leave the groups you do not use empty, e.g. --sheet-set LongFastQ=. Set the required columns no file determines with `--sheet-set COLUMN=VALUE`. Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file path) |  |  |  | Path to tab-separated sample sheet |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, required, hidden, allowed values, constraints, default and description. Use it as the source of truth; do not guess flags. It uses nfclaw's hyphenated flags; raw Nextflow requires the exact schema spelling (usually underscores). nfclaw checks explicit parameters before launch; the pinned pipeline's validation handles conditional and complex constraints at runtime. It is organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Annotation** (`annotation`) — 8 parameters
- **Assembly parameters** (`assembly_parameters`) — 12 parameters
- **Assembly Polishing** (`assembly_polishing`) — 1 parameter
- **BUSCO options** (`busco_options`) — 5 parameters
- **Contamination Screening** (`contamination_screening`) — 4 parameters
- **Generic options** (`generic_options`) — 17 parameters
- **Input/output options** (`input_output_options`) — 3 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **QC and Trim** (`qc_and_trim`) — 13 parameters
- **Skipping Options** (`skipping_options`) — 7 parameters

Upstream usage: https://github.com/nf-core/bacass/blob/2.6.1/docs/usage.md

## Resources
Resource requests follow the pipeline's configs and selected profiles. nf-core's resource labels often assume a server — a single step can request far more memory than a workstation has, and retry rules can increase requests. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run bacass --input samplesheet.csv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=25.04.0'`.

To pin this release's declared minimum engine — useful when a newer Nextflow has incompatible config parsing:
```bash
nfclaw run bacass ... --nxf-ver 25.04.0
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `--skip-multiqc true` disables that report. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/bacass/blob/2.6.1/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: FastQC, FastP, Porechop, NanoPlot, ToulligQC, pycoQC, Unicycler, MEGAHIT, Miniasm, Canu, Flye, Raven, Autocycler, QUAST, Prokka, DFAST, Liftoff, Medaka, Nanopolish, SAMtools, Kraken2, Rasusa, MultiQC.

Full list with references: https://github.com/nf-core/bacass/blob/2.6.1/CITATIONS.md

## Demo
```bash
nfclaw run bacass --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

<!-- Generated from nf-core/bacass@5ed7c2dd9a05d2434d8ba39ace1116368a4ba570. Do not edit by hand. -->
