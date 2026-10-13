---
name: rnadnavar
pipeline: nf-core/rnadnavar
version: 1.0.0
commit: 8e8debdb0e7208218a4a2f852de7c741a69ca448
description: Pipeline for RNA and DNA integrated analysis for somatic mutation detection
summary: The nf-core/rnadnavar is a bioinformatics best-practice analysis pipeline for RNA somatic mutation detection able to perform in parallel.
has_samplesheet: true
input: samplesheet (patient, sample, status, lane, fastq_1, fastq_2, table, cram, crai, bam, bai, vcf, variantcaller, maf, normal_id)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["FastQC", "MultiQC", "FASTP", "BWA-MEM", "BWA-MEM2", "STAR", "DragMap", "HISAT2", "SAMtools", "Mosdepth", "GATK", "GATK Mutect2", "Strelka2", "SAGE", "Ensembl VEP", "VT", "vcf2maf", "BCFtools"]
---
# rnadnavar

The nf-core/rnadnavar is a bioinformatics best-practice analysis pipeline for RNA somatic mutation detection able to perform in parallel.

## Run it
```bash
git submodule update --init pipelines/rnadnavar/upstream   # first time only
nfclaw run rnadnavar --input samplesheet.csv --outdir results -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/rnadnavar/upstream -profile docker --input samplesheet.csv --outdir results
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions rnadnavar` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show rnadnavar --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show rnadnavar --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `patient` | string | yes |  | matches ^\S+$ |
| `sample` | string | yes |  | matches ^\S+$ |
| `status` | integer | no |  | ≥ 0; ≤ 2 |
| `lane` | string | no |  | matches ^\S+$ |
| `fastq_1` | string (file path) | no |  | matches ^([\S\s]*\/)?[^\s\/]+\.f(ast)?q\.gz$ |
| `fastq_2` | string (file path) | no |  |  |
| `table` | string (file path) | no |  |  |
| `cram` | string (file path) | no |  |  |
| `crai` | string (file path) | no |  |  |
| `bam` | string (file path) | no |  |  |
| `bai` | string (file path) | no |  |  |
| `vcf` | string (file path) | no |  |  |
| `variantcaller` | string | no |  |  |
| `maf` | string (file path) | no |  |  |
| `normal_id` | string | no |  | matches ^\S+$ |

The samplesheet is a CSV with this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
patient,sample
```

Any of the optional columns above may be appended to the header when your data needs them: `status`, `lane`, `fastq_1`, `fastq_2`, `table`, `cram`, `crai`, `bam`, `bai`, `vcf`, `variantcaller`, `maf`, `normal_id`.

**From data files.** `--input` may also be the data files — a directory (searched recursively), a quoted glob, or files (`--input` once per file) — from which nfclaw writes this samplesheet: `sample` from file names; `fastq_1`/`fastq_2` from FastQ files (mates paired by `_R1`/`_R2`, or by `_1`/`_2` when their read names show they are mates); `lane` from Illumina lane numbers (`_L002` → 2, else 1); `table`, `cram`, `crai`, `bam`, `bai`, `vcf`, `maf` from files matching their patterns, by sample name. Set the required columns no file determines with `--sheet-set COLUMN=VALUE` (a constant or a `{sample}`/`{lane}` template): `patient` (matching ^\S+$). Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string |  |  |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## Reference genome
**This release resolves a reference genome remotely by default.** `--genome` defaults to `GRCh38`; the schema declares AWS iGenomes at `s3://ngi-igenomes/igenomes/`. The pinned configuration gives that key the FASTA `${params.igenomes_base}/Homo_sapiens/NCBI/GRCh38/Sequence/WholeGenomeFasta/genome.fa`. Resolving references through that default needs access to this source. For a self-contained run, pass your own reference instead (e.g. `--fasta`; the `reference_genome_options` group in [reference.md](reference.md) lists every reference option). Set `--igenomes-ignore true` to disable the lookup entirely. Confirm the selected reference's paths and source in the pinned `upstream/nextflow.config` and `upstream/conf/` before running.

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, default, allowed values and constraints — organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Alignment options** (`alignment_options`) — 4 parameters
- **Annotation** (`annotation`) — 18 parameters
- **FASTQ Preprocessing** (`fastq_preprocessing`) — 8 parameters
- **Filtering** (`filtering`) — 9 parameters
- **Generic options** (`generic_options`) — 16 parameters
- **Input/output options** (`input_output_options`) — 10 parameters
- **Institutional config options** (`institutional_config_options`) — 10 parameters
- **Pipeline stage options** (`pipeline_stage_options`) — 3 parameters
- **Reference genome options** (`reference_genome_options`) — 34 parameters
- **Variant calling** (`variant_calling`) — 14 parameters

## Resources
A real (non-`--demo`) run requests the resources the pipeline's `conf/base.config` asks for, which are sized for a server — a single step can request far more memory than a workstation has, and Nextflow retries a failed step with more still. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run rnadnavar --input samplesheet.csv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=25.10.4'`.

To run the engine this release targets — worth doing if a newer Nextflow emits config-parser warnings the release never saw:
```bash
nfclaw run rnadnavar ... --nxf-ver 25.10.4
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/rnadnavar/blob/1.0.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: FastQC, MultiQC, FASTP, BWA-MEM, BWA-MEM2, STAR, DragMap, HISAT2, SAMtools, Mosdepth, GATK, GATK Mutect2, Strelka2, SAGE, Ensembl VEP, VT, vcf2maf, BCFtools.

Full list with references: https://github.com/nf-core/rnadnavar/blob/1.0.0/CITATIONS.md

## Demo
```bash
nfclaw run rnadnavar --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

## Full reference
Every parameter — name, type, required, hidden, allowed values, constraints, default and description — is in [reference.md](reference.md). Use it as the source of truth; do not guess flags. Nextflow's nf-schema validates every parameter against this schema at runtime, so an unknown or invalid value fails fast. Upstream usage: https://github.com/nf-core/rnadnavar/blob/1.0.0/docs/usage.md

<!-- Generated from nf-core/rnadnavar@8e8debdb0e7208218a4a2f852de7c741a69ca448. Do not edit by hand. -->
