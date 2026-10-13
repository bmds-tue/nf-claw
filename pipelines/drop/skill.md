---
name: drop
pipeline: nf-core/drop
version: 1.0.0
commit: 20388350d242746f8e799b28c3ae80421627b077
description: The detection of RNA Outliers Pipeline (DROP) is an integrative workflow to detect aberrant expression, aberrant splicing, and mono-allelic expression from raw sequencing files.
summary: nf-core/drop is a Nextflow rewrite of drop (Detection of RNA Outliers Pipeline), a bioinformatics pipeline that detects aberrant expression, aberrant splicing, and mono-allelic expression from RNA sequencing data. drop was originally written by Vicente Yepez, Christian Mertes, Michaela Mueller, Daniela Andrade, Leonhard Wachutka from the Gagneur lab at the Department of Informatics and School of Medicine of the Technical University of Munich (TUM) and The German Human Genome-Phenome Archive (GHGA).
has_samplesheet: true
input: samplesheet (RNA_ID, RNA_BAM_FILE, RNA_BAI_FILE, DNA_ID, DNA_VCF_FILE, DNA_TBI_FILE, DROP_GROUP, PAIRED_END, COUNT_MODE, COUNT_OVERLAPS, STRAND, HPO_TERMS, GENE_COUNTS_FILE, GENE_ANNOTATION, GENOME, SPLICE_COUNTS_DIR, SEX, TISSUE, DISEASE)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["BBmisc", "BCFTools", "BeautifulSoup4", "BiocManager", "BiocParallel", "BSgenome", "Cowplot", "Data.table", "DelayedMatrixStats", "Devtools", "Dplyr", "DT", "FRASER", "GATK", "GenomicAlignments", "GenomicFeatures", "GenomicRanges", "Ggplot2", "Ggthemes", "Hdf5r", "Htslib", "Knitr", "Lxml", "MafDB", "Magrittr", "MultiQC", "OUTRIDER", "Pheatmap", "Plotly.R", "Python", "R", "RColorBrewer", "Reshape2", "Rmarkdown", "Rsamtools", "Rtracklayer", "R utils", "R YAML", "SAMtools", "Stringr", "SummarizedExperiment", "Tar", "Tidyr", "tMAE", "Txdbmaker", "VariantAnnotation"]
---
# drop

nf-core/drop is a Nextflow rewrite of drop (Detection of RNA Outliers Pipeline), a bioinformatics pipeline that detects aberrant expression, aberrant splicing, and mono-allelic expression from RNA sequencing data. drop was originally written by Vicente Yepez, Christian Mertes, Michaela Mueller, Daniela Andrade, Leonhard Wachutka from the Gagneur lab at the Department of Informatics and School of Medicine of the Technical University of Munich (TUM) and The German Human Genome-Phenome Archive (GHGA).

## Run it
```bash
git submodule update --init pipelines/drop/upstream   # first time only
nfclaw run drop --input samplesheet.tsv --outdir results --genome <genome> -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/drop/upstream -profile docker --input samplesheet.tsv --outdir results --genome <genome>
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions drop` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show drop --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show drop --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `RNA_ID` | string or integer | yes |  | matches ^\S+$ |
| `RNA_BAM_FILE` | string (file path) | no |  | matches ^\S+\.(bam\|cram)$ |
| `RNA_BAI_FILE` | string (file path) | no |  | matches ^\S+\.(bam\|cram)\.(bai\|crai)$ |
| `DNA_ID` | string or integer | no |  | matches ^\S+$ |
| `DNA_VCF_FILE` | string (file path) | no |  | matches ^\S+\.vcf.gz$ |
| `DNA_TBI_FILE` | string (file path) | no |  | matches ^\S+\.vcf.gz.tbi$ |
| `DROP_GROUP` | string | yes |  | matches ^\S+$ |
| `PAIRED_END` | boolean | no |  |  |
| `COUNT_MODE` | string | no | `union`, `IntersectionStrict`, `IntersectionNotEmpty` |  |
| `COUNT_OVERLAPS` | boolean | no |  |  |
| `STRAND` | string | yes | `yes`, `no`, `reverse` |  |
| `HPO_TERMS` | string | no |  |  |
| `GENE_COUNTS_FILE` | string (file path) | no |  | matches ^\S+\.tsv(\.gz)?$ |
| `GENE_ANNOTATION` | string | no |  |  |
| `GENOME` | string | no | `ncbi`, `ucsc` |  |
| `SPLICE_COUNTS_DIR` | string (file or directory path) | no |  | matches ^\S+$ |
| `SEX` | string | no |  |  |
| `TISSUE` | string | no |  |  |
| `DISEASE` | string | no |  |  |

`--input` must match `^\S+\.tsv$`.

The samplesheet is a TSV. Each row must include **exactly one** of these mutually-exclusive column groups (providing columns from more than one group fails validation):
- `RNA_BAM_FILE`
- `GENE_COUNTS_FILE`, `GENE_ANNOTATION`
- `SPLICE_COUNTS_DIR`

Additional row validation rules from the schema:
- When `DNA_ID` is set, also provide `DNA_VCF_FILE`, `GENOME`.
- When `DNA_VCF_FILE` is set, also provide `DNA_ID`.

Fill each value per the table above and `reference.md`. Valid headers — pick the group that matches your data (optional columns from the table may be added):
```tsv
RNA_ID	DROP_GROUP	STRAND	RNA_BAM_FILE
```
```tsv
RNA_ID	DROP_GROUP	STRAND	GENE_COUNTS_FILE	GENE_ANNOTATION
```
```tsv
RNA_ID	DROP_GROUP	STRAND	SPLICE_COUNTS_DIR
```

**From data files.** `--input` may also be the data files — a directory (searched recursively), a quoted glob, or files (`--input` once per file) — from which nfclaw writes this samplesheet: `RNA_ID` from file names; `RNA_BAM_FILE`, `RNA_BAI_FILE`, `DNA_VCF_FILE`, `DNA_TBI_FILE`, `GENE_COUNTS_FILE` from files matching their patterns, by sample name. Schema defaults fill `STRAND` = `no`. Optional columns left out take their schema defaults in the pipeline: `PAIRED_END` = `true`, `COUNT_MODE` = `IntersectionStrict`, `COUNT_OVERLAPS` = `true`, `GENOME` = `ucsc` — set them with `--sheet-set` where your design differs. Set the required columns no file determines with `--sheet-set COLUMN=VALUE` (a constant or a `{sample}`/`{lane}` template): `DROP_GROUP` (matching ^\S+$). Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file path) |  |  | matches ^\S+\.tsv$ | Path to the samplesheet file used by the pipeline. The file should be a TSV file. Equivalent to the `sampleAnnotation` parameter in the snakemake pipeline. |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. Equivalent to the `root` parameter in the snakemake pipeline. |
| `--genome` | string |  | `hg19`, `hs37d5 `, `hg38`, `GRCh38` |  | Equivalent to the `genomeAssembly` parameter in the snakemake pipeline. Either hg19/hs37d5 or hg38/GRCh38, depending on the genome assembly used for mapping |

## Reference genome
No reference genome is set by default: supply your own reference. The schema declares AWS iGenomes at `s3://ngi-igenomes/igenomes/`; selecting `--genome <id>` uses the paths in the pipeline's reference configuration. Access to that remote source is required. To supply your own reference, use the `input_output_options` group in [reference.md](reference.md) lists the reference options. Set `--igenomes-ignore true` to disable the lookup entirely. Confirm the selected reference's paths and source in the pinned `upstream/nextflow.config` and `upstream/conf/` before running.

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, default, allowed values and constraints — organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Aberrant expression options** (`aberrant_expression`) — 11 parameters
- **Aberrant splicing options** (`aberrant_splicing`) — 18 parameters
- **Export counts options** (`export_counts`) — 2 parameters
- **Generic options** (`generic_options`) — 18 parameters
- **Parameters defining the input and output options of the pipeline** (`input_output_options`) — 8 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **Mono-allelic expression options** (`mono_allelic_expression`) — 18 parameters
- **Reference genome options** (`reference_genome_options`) — 2 parameters

## Resources
A real (non-`--demo`) run requests the resources the pipeline's `conf/base.config` asks for, which are sized for a server — a single step can request far more memory than a workstation has, and Nextflow retries a failed step with more still. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run drop --input samplesheet.tsv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=25.10.0'`.

To run the engine this release targets — worth doing if a newer Nextflow emits config-parser warnings the release never saw:
```bash
nfclaw run drop ... --nxf-ver 25.10.0
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/drop/blob/1.0.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: BBmisc, BCFTools, BeautifulSoup4, BiocManager, BiocParallel, BSgenome, Cowplot, Data.table, DelayedMatrixStats, Devtools, Dplyr, DT, FRASER, GATK, GenomicAlignments, GenomicFeatures, GenomicRanges, Ggplot2, Ggthemes, Hdf5r, Htslib, Knitr, Lxml, MafDB, Magrittr, MultiQC, OUTRIDER, Pheatmap, Plotly.R, Python, R, RColorBrewer, Reshape2, Rmarkdown, Rsamtools, Rtracklayer, R utils, R YAML, SAMtools, Stringr, SummarizedExperiment, Tar, Tidyr, tMAE, Txdbmaker, VariantAnnotation.

Full list with references: https://github.com/nf-core/drop/blob/1.0.0/CITATIONS.md

## Demo
```bash
nfclaw run drop --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

## Full reference
Every parameter — name, type, required, hidden, allowed values, constraints, default and description — is in [reference.md](reference.md). Use it as the source of truth; do not guess flags. Nextflow's nf-schema validates every parameter against this schema at runtime, so an unknown or invalid value fails fast. Upstream usage: https://github.com/nf-core/drop/blob/1.0.0/docs/usage.md

<!-- Generated from nf-core/drop@20388350d242746f8e799b28c3ae80421627b077. Do not edit by hand. -->
