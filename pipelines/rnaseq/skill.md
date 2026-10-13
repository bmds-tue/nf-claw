---
name: rnaseq
pipeline: nf-core/rnaseq
version: 3.27.0
commit: a1fcdddd3b826fe46eb46f0479f2ff8a7815af05
description: RNA sequencing analysis pipeline for gene/isoform quantification and extensive quality control.
summary: nf-core/rnaseq is a bioinformatics pipeline that can be used to analyse RNA sequencing data obtained from organisms with a reference genome and annotation. It takes a samplesheet with FASTQ files or pre-aligned BAM files as input, performs quality control (QC), trimming and (pseudo-)alignment, and produces a gene expression matrix and extensive QC report.
has_samplesheet: true
input: samplesheet (sample, fastq_1, fastq_2, strandedness, seq_platform, seq_center, genome_bam, transcriptome_bam, percent_mapped)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["BBMap", "BEDTools", "Bowtie2", "Bracken", "fastp", "FastQC", "featureCounts", "fq", "GffRead", "HISAT2", "Kallisto", "Kraken2", "MultiQC", "picard-tools", "preseq", "Qualimap 2", "RiboDetector", "RSEM", "RustQC", "RSeQC", "Salmon", "SeqKit", "SAMtools", "SortMeRNA", "STAR", "StringTie2", "Sylph", "Trim Galore!", "tximport", "UCSC tools", "UMI-tools", "UMICollapse", "R", "DESeq2", "dupRadar", "ggplot2", "optparse", "pheatmap", "RColorBrewer", "SummarizedExperiment", "Tximeta"]
feeds: ["differentialabundance"]
---
# rnaseq

nf-core/rnaseq is a bioinformatics pipeline that can be used to analyse RNA sequencing data obtained from organisms with a reference genome and annotation. It takes a samplesheet with FASTQ files or pre-aligned BAM files as input, performs quality control (QC), trimming and (pseudo-)alignment, and produces a gene expression matrix and extensive QC report.

## Run it
```bash
git submodule update --init pipelines/rnaseq/upstream   # first time only
nfclaw run rnaseq --input samplesheet.csv --outdir results -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/rnaseq/upstream -profile docker --input samplesheet.csv --outdir results
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions rnaseq` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show rnaseq --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show rnaseq --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `sample` | string or integer | yes |  | matches ^\S+$ |
| `fastq_1` | string (file path) | yes |  | matches ^([\S\s]*\/)?[^\s\/]+\.f(ast)?q(\.gz)?$ |
| `fastq_2` | string (file path) | no |  | matches ^([\S\s]*\/)?[^\s\/]+\.f(ast)?q(\.gz)?$ |
| `strandedness` | string | yes | `forward`, `reverse`, `unstranded`, `auto` |  |
| `seq_platform` | string | no |  | matches ^\S+$ |
| `seq_center` | string | no |  | matches ^\S+$ |
| `genome_bam` | string (file path) | no |  | matches ^([\S\s]*\/)?[^\s\/]+\.(bam\|BAM)$ |
| `transcriptome_bam` | string (file path) | no |  | matches ^([\S\s]*\/)?[^\s\/]+\.(bam\|BAM)$ |
| `percent_mapped` | number | no |  | ≥ 0; ≤ 100 |

`--input` must match `^\S+\.csv$`.

The samplesheet is a CSV with this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
sample,fastq_1,strandedness
```

Any of the optional columns above may be appended to the header when your data needs them: `fastq_2`, `seq_platform`, `seq_center`, `genome_bam`, `transcriptome_bam`, `percent_mapped`.

**From data files.** `--input` may also be the data files — a directory (searched recursively), a quoted glob, or files (`--input` once per file) — from which nfclaw writes this samplesheet: `sample` from file names; `fastq_1`/`fastq_2` from FastQ files (mates paired by `_R1`/`_R2`, or by `_1`/`_2` when their read names show they are mates). Set the required columns no file determines with `--sheet-set COLUMN=VALUE` (a constant or a `{sample}`/`{lane}` template): `strandedness` (one of forward, reverse, unstranded, auto). Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file path) |  |  | matches ^\S+\.csv$ | Path to the sample sheet (CSV) containing metadata about the experimental samples. |
| `--outdir` | string (directory path) |  |  | length ≥ 1 | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## Reference genome
No reference genome is set by default: supply your own reference. The schema declares AWS iGenomes at `s3://ngi-igenomes/igenomes/`; selecting `--genome <id>` uses the paths in the pipeline's reference configuration. Access to that remote source is required. To supply your own reference, use e.g. `--fasta`; the `reference_genome_options` group in [reference.md](reference.md) lists every reference option. Set `--igenomes-ignore true` to disable the lookup entirely. Confirm the selected reference's paths and source in the pinned `upstream/nextflow.config` and `upstream/conf/` before running.

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, default, allowed values and constraints — organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Alignment options** (`alignment_options`) — 23 parameters
- **Generic options** (`generic_options`) — 15 parameters
- **Input/output options** (`input_output_options`) — 4 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **Optional outputs** (`optional_outputs`) — 10 parameters
- **Process skipping options** (`process_skipping_options`) — 22 parameters
- **Quality Control** (`quality_control`) — 9 parameters
- **Read filtering options** (`read_filtering_options`) — 8 parameters
- **Read trimming options** (`read_trimming_options`) — 4 parameters
- **Reference genome options** (`reference_genome_options`) — 25 parameters
- **UMI options** (`umi_options`) — 10 parameters

## Resources
Resource requests follow the pipeline's configs and selected profiles. nf-core's resource labels often assume a server — a single step can request far more memory than a workstation has, and retry rules can increase requests. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run rnaseq --input samplesheet.csv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=25.10.4'`.

To pin this release's declared minimum engine — useful when a newer Nextflow has incompatible config parsing:
```bash
nfclaw run rnaseq ... --nxf-ver 25.10.4
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `--skip-multiqc true` disables that report. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/rnaseq/blob/3.27.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Chaining
Run rnaseq as one stage of a chain: `nfclaw chain run spec.json --outdir DIR` starts each stage only after the one before it succeeded, and prepares its inputs from that stage's outputs. The rules live in `handoffs/` (format and spec in [docs/chaining.md](../../docs/chaining.md)); list them with `nfclaw chain edges rnaseq`.

Feeds into:
- `differentialabundance` — rnaseq's merged gene counts and the gene lengths of the same quantification become differentialabundance's --matrix and --feature-length-matrix (DESeq2 models length bias with them; differentialabundance does not recommend raw counts without lengths) — from the alignment-based quantification when rnaseq ran one, otherwise its pseudo-aligner — with the GTF the rnaseq run used. An rnaseq release that published no lengths for that quantification (before 3.15.0; RSEM before 3.23.0) fails the handoff: hand over its length-scaled counts with an inline handoff instead. The experimental design (--input, sample names as in rnaseq) and --contrasts describe your study and go in the stage's own params.

Fed by:
- `bamtofastq` — bamtofastq publishes converted paired-end reads as reads/<sample>_1.merged.fastq.gz and _2; one rnaseq row per sample, strandedness detected by rnaseq (auto). Single-end conversions (reads/<sample>.merged.fastq.gz) need an inline handoff.
- `demultiplex` — demultiplex writes samplesheet/rnaseq_samplesheet.csv for its demultiplexed FastQ files (strandedness from its --strandedness, default auto).
- `fetchngs` — fetchngs downloads the FastQ files and, with --nf-core-pipeline rnaseq, writes samplesheet/samplesheet.csv for rnaseq (absolute FastQ paths; strandedness from --nf-core-rnaseq-strandedness, default auto). Runs whose ENA instrument_platform is not a short-read platform (the ones nf-core/mag accepts as short reads: ILLUMINA, BGISEQ, DNBSEQ, ELEMENT, ULTIMA, ION_TORRENT, LS454, …) are refused: rnaseq analyses short reads, and long-read, capillary or colour-space runs would be processed as if they were.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: BBMap, BEDTools, Bowtie2, Bracken, fastp, FastQC, featureCounts, fq, GffRead, HISAT2, Kallisto, Kraken2, MultiQC, picard-tools, preseq, Qualimap 2, RiboDetector, RSEM, RustQC, RSeQC, Salmon, SeqKit, SAMtools, SortMeRNA, STAR, StringTie2, Sylph, Trim Galore!, tximport, UCSC tools, UMI-tools, UMICollapse, R, DESeq2, dupRadar, ggplot2, optparse, pheatmap, RColorBrewer, SummarizedExperiment, Tximeta.

Full list with references: https://github.com/nf-core/rnaseq/blob/3.27.0/CITATIONS.md

## Demo
```bash
nfclaw run rnaseq --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

## Full reference
Every parameter — name, type, required, hidden, allowed values, constraints, default and description — is in [reference.md](reference.md). Use it as the source of truth; do not guess flags. nfclaw checks explicit parameters before launch; the pinned pipeline's validation handles conditional and complex constraints at runtime. The reference uses nfclaw's hyphenated flags; raw Nextflow requires the exact schema spelling (usually underscores). Upstream usage: https://github.com/nf-core/rnaseq/blob/3.27.0/docs/usage.md

<!-- Generated from nf-core/rnaseq@a1fcdddd3b826fe46eb46f0479f2ff8a7815af05. Do not edit by hand. -->
