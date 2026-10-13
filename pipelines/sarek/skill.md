---
name: sarek
pipeline: nf-core/sarek
version: 3.10.0
commit: 8ccac7ad37b05dd792447763bf9671b719824587
description: An open-source analysis pipeline to detect germline or somatic variants from whole genome or targeted sequencing
summary: nf-core/sarek is a workflow designed to detect variants on whole genome or targeted sequencing data. Initially designed for Human, and Mouse, it can work on any species with a reference genome. Sarek can also handle tumour / normal pairs and could include additional relapses.
has_samplesheet: true
input: samplesheet (patient, sample, sex, status, lane, fastq_1, fastq_2, spring_1, spring_2, table, cram, crai, bam, bai, contamination, vcf, variantcaller)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["ASCAT", "alleleCount", "BCFTools", "BGZip", "BWA-MEM", "BWA-MEM2", "CNVKIT", "Condel", "Control-FREEC", "dbNSFP", "DeepVariant", "DragMap", "EnsemblVEP", "FastP", "FastQC", "FGBio", "FreeBayes", "GATK", "GNU sed", "goleft indexcov", "HaplotypeCaller Joint Germline", "LOFTEE", "Manta", "Mastermind", "Mosdepth", "MSIsensor2", "MSISensorPro", "MultiQC", "NGSCheckMate", "NVIDIA Clara Parabricks", "Phenotypes", "PIGZ", "P7Zip", "SAMtools", "snpEff", "SpliceAI", "SpliceRegion", "SPRING", "Strelka2", "SVDB", "Tabix", "TIDDIT", "Varlociraptor", "VCFTools", "vcflib", "Lofreq", "MuSE", "R", "RColorBrewer"]
---
# sarek

nf-core/sarek is a workflow designed to detect variants on whole genome or targeted sequencing data. Initially designed for Human, and Mouse, it can work on any species with a reference genome. Sarek can also handle tumour / normal pairs and could include additional relapses.

## Run it
```bash
git submodule update --init pipelines/sarek/upstream   # first time only
nfclaw run sarek --input samplesheet.csv --outdir results -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/sarek/upstream -profile docker --input samplesheet.csv --outdir results
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions sarek` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show sarek --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show sarek --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `patient` | string | yes |  | matches ^\S+$ |
| `sample` | string | yes |  | matches ^\S+$ |
| `sex` | string | no | `XX`, `XY`, `NA` |  |
| `status` | integer | no | `0`, `1` |  |
| `lane` | integer or string | no |  | matches ^\S+$ |
| `fastq_1` | string (file path) | no |  | matches ^([\S\s]*\/)?[^\s\/]+\.f(ast)?q\.gz$ |
| `fastq_2` | string (file path) | no |  | matches ^([\S\s]*\/)?[^\s\/]+\.f(ast)?q\.gz$ |
| `spring_1` | string (file path) | no |  | matches ^\S+\.f(ast)?q\.gz.spring$ |
| `spring_2` | string (file path) | no |  | matches ^\S+\.f(ast)?q\.gz.spring$ |
| `table` | string (file path) | no |  | matches ^\S+\.table$ |
| `cram` | string (file path) | no |  | matches ^\S+\.cram$ |
| `crai` | string (file path) | no |  | matches ^\S+\.crai$ |
| `bam` | string (file path) | no |  | matches ^\S+\.bam$ |
| `bai` | string (file path) | no |  | matches ^\S+\.bai$ |
| `contamination` | number | no |  |  |
| `vcf` | string (file path) | no |  | matches ^\S+\.vcf(\.gz)?$ |
| `variantcaller` | string | no |  |  |

`--input` must match `^\S+\.(csv|tsv|yaml|yml|json)$`.

Additional row validation rules from the schema:
- When `fastq_2` is set, also provide `fastq_1`.
- When `spring_2` is set, also provide `spring_1`.
- At least one of these conditional requirements must be satisfied: `fastq_1` when `lane` is set; `spring_1` when `lane` is set; `bam` when `lane` is set.

For tabular CSV/TSV input, use this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
patient,sample
```

Any of the optional columns above may be appended to the header when your data needs them: `sex`, `status`, `lane`, `fastq_1`, `fastq_2`, `spring_1`, `spring_2`, `table`, `cram`, `crai`, `bam`, `bai`, `contamination`, `vcf`, `variantcaller`.

**From data files.** `--input` may also be the data files — a directory (searched recursively), a quoted glob, or files (`--input` once per file) — from which nfclaw writes this samplesheet: `sample` from file names; `fastq_1`/`fastq_2` from FastQ files (mates paired by `_R1`/`_R2`, or by `_1`/`_2` when their read names show they are mates); `lane` from Illumina lane numbers (`_L002` → 2, else 1); `table`, `cram`, `crai`, `bam`, `bai`, `vcf` from files matching their patterns, by sample name. Set the required columns no file determines with `--sheet-set COLUMN=VALUE` (a constant or a `{sample}`/`{lane}` template): `patient` (matching ^\S+$). Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--step` | string | mapping | `mapping`, `markduplicates`, `prepare_recalibration`, `recalibrate`, `variant_calling`, `annotate` |  | Starting step |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## Reference genome
**This release resolves a reference genome remotely by default.** `--genome` defaults to `GATK.GRCh38`; the schema declares AWS iGenomes at `s3://ngi-igenomes/igenomes/`. Resolving references through that default needs access to this source. For a self-contained run, pass your own reference instead (e.g. `--fasta`; the `reference_genome_options` group in [reference.md](reference.md) lists every reference option). Set `--igenomes-ignore true` to disable the lookup entirely. Confirm the selected reference's paths and source in the pinned `upstream/nextflow.config` and `upstream/conf/` before running.

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, default, allowed values and constraints — organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Annotation** (`annotation`) — 33 parameters
- **FASTQ Preprocessing** (`fastq_preprocessing`) — 9 parameters
- **General reference genome options** (`general_reference_genome_options`) — 5 parameters
- **Generic options** (`generic_options`) — 17 parameters
- **Input/output options** (`input_output_options`) — 4 parameters
- **Institutional config options** (`institutional_config_options`) — 10 parameters
- **Main options** (`main_options`) — 7 parameters
- **Post variant calling** (`post_variant_calling`) — 14 parameters
- **Preprocessing** (`preprocessing`) — 6 parameters
- **Reference genome options** (`reference_genome_options`) — 36 parameters
- **Unique Molecular Identifiers** (`umi_processing`) — 10 parameters
- **Variant Calling** (`variant_calling`) — 25 parameters

## Resources
A real (non-`--demo`) run requests the resources the pipeline's `conf/base.config` asks for, which are sized for a server — a single step can request far more memory than a workstation has, and Nextflow retries a failed step with more still. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run sarek --input samplesheet.csv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=25.10.4'`.

To run the engine this release targets — worth doing if a newer Nextflow emits config-parser warnings the release never saw:
```bash
nfclaw run sarek ... --nxf-ver 25.10.4
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/sarek/blob/3.10.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Chaining
Run sarek as one stage of a chain: `nfclaw chain run spec.json --outdir DIR` starts each stage only after the one before it succeeded, and prepares its inputs from that stage's outputs. The rules live in `handoffs/` (format and spec in [docs/chaining.md](../../docs/chaining.md)); list them with `nfclaw chain edges sarek`.

Fed by:
- `demultiplex` — demultiplex writes samplesheet/sarek_samplesheet.csv with an empty patient; each sample is made its own patient (set it per sample yourself if several samples share one); sarek reads paired-end FastQ only, so every row needs a fastq_2. No status or sex column is written: sarek treats every sample as normal tissue (status 0, sex NA) and runs germline analyses only; a tumour/normal design needs its own sarek samplesheet (a handoff's set gives every row the same value).
- `fetchngs` — fetchngs writes a sarek samplesheet (patient = the ENA sample accession) with --nf-core-pipeline sarek; it has no lane, so each run's accession becomes its lane — sarek needs patient, sample and lane to be unique together; sarek reads paired-end FastQ only, so every row needs a fastq_2. No status or sex column is written: sarek treats every sample as normal tissue (status 0, sex NA) and runs germline analyses only; a tumour/normal design needs its own sarek samplesheet (a handoff's set gives every row the same value).

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: ASCAT, alleleCount, BCFTools, BGZip, BWA-MEM, BWA-MEM2, CNVKIT, Condel, Control-FREEC, dbNSFP, DeepVariant, DragMap, EnsemblVEP, FastP, FastQC, FGBio, FreeBayes, GATK, GNU sed, goleft indexcov, HaplotypeCaller Joint Germline, LOFTEE, Manta, Mastermind, Mosdepth, MSIsensor2, MSISensorPro, MultiQC, NGSCheckMate, NVIDIA Clara Parabricks, Phenotypes, PIGZ, P7Zip, SAMtools, snpEff, SpliceAI, SpliceRegion, SPRING, Strelka2, SVDB, Tabix, TIDDIT, Varlociraptor, VCFTools, vcflib, Lofreq, MuSE, R, RColorBrewer.

Full list with references: https://github.com/nf-core/sarek/blob/3.10.0/CITATIONS.md

## Demo
```bash
nfclaw run sarek --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

## Full reference
Every parameter — name, type, required, hidden, allowed values, constraints, default and description — is in [reference.md](reference.md). Use it as the source of truth; do not guess flags. Nextflow's nf-schema validates every parameter against this schema at runtime, so an unknown or invalid value fails fast. Upstream usage: https://github.com/nf-core/sarek/blob/3.10.0/docs/usage.md

<!-- Generated from nf-core/sarek@8ccac7ad37b05dd792447763bf9671b719824587. Do not edit by hand. -->
