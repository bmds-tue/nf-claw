---
name: scnanoseq
pipeline: nf-core/scnanoseq
version: 1.3.0
commit: 83d55ea87eb625a3564d40124fb1fa54c4c63f9e
description: Single-cell/nuclei pipeline for data derived from Oxford Nanopore
summary: nf-core/scnanoseq is a bioinformatics best-practice analysis pipeline for 10X Genomics single-cell/nuclei RNA-seq data derived from Oxford Nanopore Q20+ chemistry (R10.4 flow cells (>Q20)). Due to the expectation of >Q20 quality, the input data for the pipeline does not depend on Illumina paired data. Please note scnanoseq can also process Oxford data with older chemistry, but we encourage usage of the Q20+ chemistry when possible.
has_samplesheet: true
input: samplesheet (sample, fastq, cell_count)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["BLAZE", "FastQC", "IsoQuant", "Minimap2", "MultiQC", "NanoComp", "Chopper", "NanoPlot", "oarfish", "pigz", "SAMtools", "ToulligQC", "UMI-tools", "Picard", "UCSC tools", "R", "ggplot2", "optparse", "Seurat", "Biopython", "NumPy", "Pandas", "Pysam"]
---
# scnanoseq

nf-core/scnanoseq is a bioinformatics best-practice analysis pipeline for 10X Genomics single-cell/nuclei RNA-seq data derived from Oxford Nanopore Q20+ chemistry (R10.4 flow cells (>Q20)). Due to the expectation of >Q20 quality, the input data for the pipeline does not depend on Illumina paired data. Please note scnanoseq can also process Oxford data with older chemistry, but we encourage usage of the Q20+ chemistry when possible.

## Run it
```bash
git submodule update --init pipelines/scnanoseq/upstream   # first time only
nfclaw run scnanoseq --input samplesheet.csv --outdir results --gtf <gtf> --barcode-format <barcode_format> --quantifier <quantifier> -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/scnanoseq/upstream -profile docker --input samplesheet.csv --outdir results --gtf <gtf> --barcode_format <barcode_format> --quantifier <quantifier>
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions scnanoseq` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show scnanoseq --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show scnanoseq --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `sample` | string | yes |  | matches ^\S+$ |
| `fastq` | string (file path) | yes |  | matches ^([\S\s]*\/)?[^\s\/]+\.f(ast)?q\.gz$ |
| `cell_count` | integer | yes |  |  |

`--input` must match `^\S+\.csv$`.

The samplesheet is a CSV with this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
sample,fastq,cell_count
```

**From data files.** `--input` may also be the data files — a directory (searched recursively), a quoted glob, or files (`--input` once per file) — from which nfclaw writes this samplesheet: `sample` from file names; `fastq` from FastQ files (single-end). Set the required columns no file determines with `--sheet-set COLUMN=VALUE` (a constant or a `{sample}`/`{lane}` template): `cell_count` (integer). Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file path) |  |  | matches ^\S+\.csv$ | Path to comma-separated file containing information about the samples in the experiment. |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--gtf` | string (file path) |  |  | matches ^\S+\.gtf(\.gz\|\.zip)?$ | Path to GTF file. |
| `--barcode-format` | string |  | `10X_3v3`, `10X_3v4`, `10X_5v2`, `10X_5v3` |  | Specify the format for the barcode+umi. This parameter also defines a default barcode whitelist for the pipeline to use for barcode calling, this can be overridden with the 'whitelist' parameter. |
| `--dedup-tool` | string | umitools | `umitools`, `picard` |  | Specify which tool to be used for deduplication (Options: picard, umitools) |
| `--quantifier` | string |  |  | matches ^(oarfish\|isoquant)(,(oarfish\|isoquant))*$ | Provide a comma-delimited options of quantifiers for the pipeline to use. Available tools: isoquant, oarfish |

## Reference genome
No reference genome is set by default: supply your own reference. The iGenomes lookup is disabled by default (`--igenomes-ignore true`). Configure your reference explicitly (the `reference_genome_options` group in [reference.md](reference.md) lists the reference options). Confirm the selected reference's paths and source in the pinned `upstream/nextflow.config` and `upstream/conf/` before running.

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, default, allowed values and constraints — organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Analysis options** (`analysis_options`) — 2 parameters
- **Cell barcode options** (`cell_barcode_options`) — 4 parameters
- **Fastq options** (`fastq_options`) — 1 parameter
- **Generic options** (`generic_options`) — 16 parameters
- **Input/output options** (`input_output_options`) — 4 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **Mapping** (`mapping`) — 4 parameters
- **Process skipping options** (`process_skipping_options`) — 11 parameters
- **Read trimming options** (`read_trimming_options`) — 3 parameters
- **Reference genome options** (`reference_genome_options`) — 7 parameters

## Resources
Resource requests follow the pipeline's configs and selected profiles. nf-core's resource labels often assume a server — a single step can request far more memory than a workstation has, and retry rules can increase requests. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run scnanoseq --input samplesheet.csv --outdir results --gtf <gtf> --barcode-format <barcode_format> --quantifier <quantifier> -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=25.04.2'`.

To pin this release's declared minimum engine — useful when a newer Nextflow has incompatible config parsing:
```bash
nfclaw run scnanoseq ... --nxf-ver 25.04.2
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `--skip-multiqc true` disables that report. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/scnanoseq/blob/1.3.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: BLAZE, FastQC, IsoQuant, Minimap2, MultiQC, NanoComp, Chopper, NanoPlot, oarfish, pigz, SAMtools, ToulligQC, UMI-tools, Picard, UCSC tools, R, ggplot2, optparse, Seurat, Biopython, NumPy, Pandas, Pysam.

Full list with references: https://github.com/nf-core/scnanoseq/blob/1.3.0/CITATIONS.md

## Demo
```bash
nfclaw run scnanoseq --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

## Full reference
Every parameter — name, type, required, hidden, allowed values, constraints, default and description — is in [reference.md](reference.md). Use it as the source of truth; do not guess flags. nfclaw checks explicit parameters before launch; the pinned pipeline's validation handles conditional and complex constraints at runtime. The reference uses nfclaw's hyphenated flags; raw Nextflow requires the exact schema spelling (usually underscores). Upstream usage: https://github.com/nf-core/scnanoseq/blob/1.3.0/docs/usage.md

<!-- Generated from nf-core/scnanoseq@83d55ea87eb625a3564d40124fb1fa54c4c63f9e. Do not edit by hand. -->
