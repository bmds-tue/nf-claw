---
name: scrnaseq
pipeline: nf-core/scrnaseq
version: 4.2.0
commit: 3fc17b4f971a89e47c88337de71d0e777ffad8cc
description: Pipeline for processing 10x Genomics single cell rnaseq data
summary: nf-core/scrnaseq is a bioinformatics best-practice analysis pipeline for processing 10x Genomics single-cell RNA-seq data.
has_samplesheet: true
input: samplesheet (sample, fastq_1, fastq_2, fastq_barcode, expected_cells, seq_center, sample_type, feature_type)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["FastQC", "MultiQC", "Simpleaf", "Alevin-fry", "Alevin", "Salmon", "Kallisto/Bustools", "StarSolo"]
---
# scrnaseq

nf-core/scrnaseq is a bioinformatics best-practice analysis pipeline for processing 10x Genomics single-cell RNA-seq data.

## Run it
```bash
git submodule update --init pipelines/scrnaseq/upstream   # first time only
nfclaw run scrnaseq --input samplesheet.csv --outdir results -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/scrnaseq/upstream -profile docker --input samplesheet.csv --outdir results
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions scrnaseq` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show scrnaseq --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show scrnaseq --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `sample` | string | yes |  | matches ^\S+$ |
| `fastq_1` | string (file path) | yes |  | matches ^([\S\s]*\/)?[^\s\/]+\.f(ast)?q\.gz$ |
| `fastq_2` | string (file path) | yes |  | matches ^([\S\s]*\/)?[^\s\/]+\.f(ast)?q\.gz$ |
| `fastq_barcode` | string | no |  |  |
| `expected_cells` | integer | no |  |  |
| `seq_center` | string | no |  |  |
| `sample_type` | string | no | `atac`, `gex` |  |
| `feature_type` | string | no | `gex`, `vdj`, `ab`, `crispr`, `cmo` |  |

`--input` must match `^\S+\.csv$`.

The samplesheet is a CSV with this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
sample,fastq_1,fastq_2
```

Any of the optional columns above may be appended to the header when your data needs them: `fastq_barcode`, `expected_cells`, `seq_center`, `sample_type`, `feature_type`.

**From data files.** `--input` may also be the data files — a directory (searched recursively), a quoted glob, or files (`--input` once per file) — from which nfclaw writes this samplesheet: `sample` from file names; `fastq_1`/`fastq_2` from FastQ files (mates paired by `_R1`/`_R2`, or by `_1`/`_2` when their read names show they are mates). Set other columns with `--sheet-set COLUMN=VALUE`. Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file path) |  |  | matches ^\S+\.csv$ | Path to comma-separated file containing information about the samples in the experiment. |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## Mandatory arguments
The schema groups these under **Mandatory arguments** — the pipeline authors' own label. They are absent from the `required` list above only because each carries a default, so nf-schema will not stop a run that omits them — but the pipeline itself can reject the default at runtime. Set them deliberately.

| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--aligner` | string | simpleaf | `kallisto`, `star`, `simpleaf`, `cellranger`, `cellrangerarc`, `cellrangermulti` |  | Name of the tool to use for scRNA (pseudo-) alignment. |
| `--barcode-whitelist` | string (file path) |  |  |  | If not using the 10X Genomics platform, a custom barcode whitelist can be used with `--barcode_whitelist`. |
| `--protocol` | string | auto |  |  | The protocol that was used to generate the single cell data, e.g. 10x Genomics v2 Chemistry. Can be 'auto' (cellranger only), '10XV1', '10XV2', '10XV3', '10XV4', or any other protocol string that will get directly passed the respective aligner. |

## Reference genome
No reference genome is set by default: supply your own reference. The schema declares AWS iGenomes at `s3://ngi-igenomes/igenomes/`; selecting `--genome <id>` uses the paths in the pipeline's reference configuration. Access to that remote source is required. To supply your own reference, use e.g. `--fasta`; the `reference_genome_options` group in [reference.md](reference.md) lists every reference option. Set `--igenomes-ignore true` to disable the lookup entirely. Confirm the selected reference's paths and source in the pinned `upstream/nextflow.config` and `upstream/conf/` before running.

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, default, allowed values and constraints — organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Cellranger Multi options** (`cellranger_multi_options`) — 10 parameters
- **Cellranger Options** (`cellranger_options`) — 2 parameters
- **Cellranger ARC Options** (`cellrangerarc_options`) — 3 parameters
- **Generic options** (`generic_options`) — 15 parameters
- **Input/output options** (`input_output_options`) — 4 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **Kallisto/BUS Options** (`kallisto_bus_options`) — 4 parameters
- **Mandatory arguments** (`mandatory_arguments`) — 3 parameters
- **Reference genome options** (`reference_genome_options`) — 9 parameters
- **Simpleaf Options** (`simpleaf_options`) — 4 parameters
- **Skip Tools** (`skip_tools`) — 5 parameters
- **STARSolo Options** (`starsolo_options`) — 4 parameters

## Resources
A real (non-`--demo`) run requests the resources the pipeline's `conf/base.config` asks for, which are sized for a server — a single step can request far more memory than a workstation has, and Nextflow retries a failed step with more still. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run scrnaseq --input samplesheet.csv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=25.10.4'`.

To run the engine this release targets — worth doing if a newer Nextflow emits config-parser warnings the release never saw:
```bash
nfclaw run scrnaseq ... --nxf-ver 25.10.4
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `--skip-multiqc true` disables that report. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/scrnaseq/blob/4.2.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: FastQC, MultiQC, Simpleaf, Alevin-fry, Alevin, Salmon, Kallisto/Bustools, StarSolo.

Full list with references: https://github.com/nf-core/scrnaseq/blob/4.2.0/CITATIONS.md

## Demo
```bash
nfclaw run scrnaseq --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

## Full reference
Every parameter — name, type, required, hidden, allowed values, constraints, default and description — is in [reference.md](reference.md). Use it as the source of truth; do not guess flags. Nextflow's nf-schema validates every parameter against this schema at runtime, so an unknown or invalid value fails fast. Upstream usage: https://github.com/nf-core/scrnaseq/blob/4.2.0/docs/usage.md

<!-- Generated from nf-core/scrnaseq@3fc17b4f971a89e47c88337de71d0e777ffad8cc. Do not edit by hand. -->
