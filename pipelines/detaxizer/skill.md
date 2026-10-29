---
name: detaxizer
pipeline: nf-core/detaxizer
version: 1.4.0
commit: f348e37b6ba368a08edd4056af10e3fec8c10bb3
description: A pipeline to identify (and remove) certain sequences from raw genomic data. Default taxon to identify (and remove) is Homo sapiens. Removal is optional.
summary: nf-core/detaxizer is a bioinformatics pipeline that checks for the presence of a specific taxon in (meta)genomic fastq files and filters out this taxon or taxonomic subtree. The process begins with quality assessment via FastQC and optional preprocessing (adapter trimming, quality cutting and optional length and quality filtering) with fastp. It continues with taxonomic classification using kraken2 and/or bbduk, and optionally uses blastn to validate reads linked to the identified taxa. Users must provide a samplesheet to indicate the fastq files. If bbduk is used in the classification and/or validation step, users must also provide fasta files to classify with bbduk and to build the blastn database that verifies the targeted taxon.
has_samplesheet: true
input: samplesheet (sample, short_reads_fastq_1, short_reads_fastq_2, long_reads_fastq_1)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["bbmap", "blastn", "fastp", "FastQC", "Kraken2", "MultiQC", "seqkit", "dnaio", "Python", "pandas", "numpy"]
feeds: ["mag", "taxprofiler"]
---
# detaxizer

nf-core/detaxizer is a bioinformatics pipeline that checks for the presence of a specific taxon in (meta)genomic fastq files and filters out this taxon or taxonomic subtree. The process begins with quality assessment via FastQC and optional preprocessing (adapter trimming, quality cutting and optional length and quality filtering) with fastp. It continues with taxonomic classification using kraken2 and/or bbduk, and optionally uses blastn to validate reads linked to the identified taxa. Users must provide a samplesheet to indicate the fastq files. If bbduk is used in the classification and/or validation step, users must also provide fasta files to classify with bbduk and to build the blastn database that verifies the targeted taxon.

## Run it
```bash
git submodule update --init pipelines/detaxizer/upstream   # first time only
nfclaw run detaxizer --input samplesheet.csv --outdir results -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/detaxizer/upstream -profile docker --input samplesheet.csv --outdir results
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions detaxizer` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show detaxizer --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show detaxizer --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `sample` | string | no |  | matches ^\S+$ |
| `short_reads_fastq_1` | string (file path) | no |  | matches ^([\S\s]*\/)?[^\s\/]+\.f(ast)?q\.gz$ |
| `short_reads_fastq_2` | string (file path) | no |  | matches ^([\S\s]*\/)?[^\s\/]+\.f(ast)?q\.gz$ |
| `long_reads_fastq_1` | string (file path) | no |  | matches ^([\S\s]*\/)?[^\s\/]+\.f(ast)?q\.gz$ |

`--input` must match `^\S+\.csv$`.

The samplesheet is a CSV with this header; fill each value per the table above and `reference.md` (no example value is invented here):
```csv
sample,short_reads_fastq_1,short_reads_fastq_2,long_reads_fastq_1
```

**From data files.** `--input` may also be the data files — a directory (searched recursively), a quoted glob, or files (`--input` once per file) — from which nfclaw writes this samplesheet once you choose the read columns: the samplesheet takes reads in several column groups (short_reads_fastq_1 + short_reads_fastq_2; long_reads_fastq_1) and file names cannot tell which yours belong in; leave the groups you do not use empty, e.g. --sheet-set long_reads_fastq_1=. Set the required columns no file determines with `--sheet-set COLUMN=VALUE`. Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file path) |  |  | matches ^\S+\.csv$ | Path to comma-separated file containing information about the samples in the experiment. |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## Reference genome
**This release resolves a reference genome remotely by default.** `--genome` defaults to `GRCh38`; the schema declares AWS iGenomes at `s3://ngi-igenomes/igenomes/`. The pinned configuration gives that key the FASTA `${params.igenomes_base}/Homo_sapiens/NCBI/GRCh38/Sequence/WholeGenomeFasta/genome.fa`. Resolving references through that default needs access to this source. For a self-contained run, pass your own reference instead (the `reference_genome_options` group in [reference.md](reference.md) lists the reference options). Set `--igenomes-ignore true` to disable the lookup entirely. Confirm the selected reference's paths and source in the pinned `upstream/nextflow.config` and `upstream/conf/` before running.

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, required, hidden, allowed values, constraints, default and description. Use it as the source of truth; do not guess flags. It uses nfclaw's hyphenated flags; raw Nextflow requires the exact schema spelling (usually underscores). nfclaw checks explicit parameters before launch; the pinned pipeline's validation handles conditional and complex constraints at runtime. It is organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **bbduk** (`bbduk`) — 2 parameters
- **blastn** (`blastn`) — 4 parameters
- **fastp options** (`fastp_options`) — 6 parameters
- **General workflow parameters** (`general_workflow_parameters`) — 11 parameters
- **Downstream pipeline samplesheet generation options** (`generate_samplesheet_options`) — 2 parameters
- **Generic options** (`generic_options`) — 15 parameters
- **Input/output options** (`input_output_options`) — 4 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **kraken2** (`kraken2`) — 11 parameters
- **Reference genome options** (`reference_genome_options`) — 4 parameters

Upstream usage: https://github.com/nf-core/detaxizer/blob/1.4.0/docs/usage.md

## Resources
Resource requests follow the pipeline's configs and selected profiles. nf-core's resource labels often assume a server — a single step can request far more memory than a workstation has, and retry rules can increase requests. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run detaxizer --input samplesheet.csv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=26.04.0'`.

To pin this release's declared minimum engine — useful when a newer Nextflow has incompatible config parsing:
```bash
nfclaw run detaxizer ... --nxf-ver 26.04.0
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/detaxizer/blob/1.4.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Chaining
Run detaxizer as one stage of a chain: `nfclaw chain run spec.json --outdir DIR` starts each stage only after the one before it succeeded, and prepares its inputs from that stage's outputs. The rules live in `handoffs/` (format and spec in [docs/chaining.md](../../docs/chaining.md)); list them with `nfclaw chain edges detaxizer`.

Feeds into:
- `mag` — detaxizer, with --generate-downstream-samplesheets, writes downstream_samplesheets/mag-pe.csv for its filtered paired-end reads, in the column layout of mag 3.x, and mag-se.csv for samples without a second short-read file, which mag cannot take in the same run: a run with any fails this handoff instead of leaving them out; each sample gets its own group and its short reads the ILLUMINA platform detaxizer documents for them. Different samples are not pooled for binning or assembly; use an inline handoff to supply study-specific pooling groups. detaxizer records no long-read platform, and mag chooses its long-read preprocessing and assembler mode by it: samples with long reads are refused until an inline handoff sets long_reads_platform (OXFORD_NANOPORE, OXFORD_NANOPORE_HQ, PACBIO_CLR or PACBIO_HIFI) for the data.
- `taxprofiler` — detaxizer, with --generate-downstream-samplesheets, writes downstream_samplesheets/taxprofiler.csv for its filtered reads (paths into filter/filtered/).

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: bbmap, blastn, fastp, FastQC, Kraken2, MultiQC, seqkit, dnaio, Python, pandas, numpy.

Full list with references: https://github.com/nf-core/detaxizer/blob/1.4.0/CITATIONS.md

## Demo
```bash
nfclaw run detaxizer --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

<!-- Generated from nf-core/detaxizer@f348e37b6ba368a08edd4056af10e3fec8c10bb3. Do not edit by hand. -->
