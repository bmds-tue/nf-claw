---
name: raredisease
pipeline: nf-core/raredisease
version: 3.1.2
commit: 83f2699d28bc957e1d3b875da3d96004a818c2c3
description: call and score variants from WGS/WES of rare disease patients
summary: nf-core/raredisease is a best-practice bioinformatic pipeline for calling and scoring variants from WGS/WES data from rare disease patients. This pipeline is heavily inspired by MIP.
has_samplesheet: true
input: samplesheet (sample, lane, fastq_1, fastq_2, spring_1, spring_2, bam, bai, sex, phenotype, paternal_id, maternal_id, case_id)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["BCFtools", "BEDTools", "BWA-MEM", "BWA-MEM2", "BWA-MEME", "CADD<sup>1</sup>", "DeepVariant", "Chromograph", "Ensembl VEP", "ExpansionHunter", "FastQC", "Fastp", "GATK", "Genmod", "Gens", "GLnexus", "Manta", "Mitosalt", "Mosdepth", "ngs-bits-samplegender", "MultiQC", "Peddy", "Picard", "RetroSeq", "rhocall", "RTG Tools (vcfeval)", "saltshaker", "Sambamba", "Sentieon DNAscope", "Sentieon DNASeq", "SMNCopyNumberCaller", "Spring", "stranger", "svdb", "Tabix", "TIDDIT", "UPD", "UCSC Bigwig and Bigbed", "vcf2cytosure", "Vcfanno", "VerifyBamID2"]
---
# raredisease

nf-core/raredisease is a best-practice bioinformatic pipeline for calling and scoring variants from WGS/WES data from rare disease patients. This pipeline is heavily inspired by MIP.

## Run it
```bash
git submodule update --init pipelines/raredisease/upstream   # first time only
nfclaw run raredisease --input samplesheet.csv --outdir results --fasta <fasta> --intervals-wgs <intervals_wgs> --intervals-y <intervals_y> -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/raredisease/upstream -profile docker --input samplesheet.csv --outdir results --fasta <fasta> --intervals_wgs <intervals_wgs> --intervals_y <intervals_y>
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions raredisease` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show raredisease --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show raredisease --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `sample` | string | yes |  | matches ^\S+$ |
| `lane` | integer or string | no |  |  |
| `fastq_1` | string (file path) | no |  | matches ^([\S\s]*\/)?[^\s\/]+\.f(ast)?q\.gz$ |
| `fastq_2` | string (file path) | no |  | matches ^([\S\s]*\/)?[^\s\/]+\.f(ast)?q\.gz$ |
| `spring_1` | string (file path) | no |  | matches ^\S+.spring$ |
| `spring_2` | string (file path) | no |  | matches ^\S+.spring$ |
| `bam` | string (file path) | no |  | matches ^\S+\.bam$ |
| `bai` | string (file path) | no |  | matches ^\S+\.bai$ |
| `sex` | integer or string | yes |  |  |
| `phenotype` | integer | yes | `0`, `1`, `2` |  |
| `paternal_id` | string | no |  |  |
| `maternal_id` | string | no |  |  |
| `case_id` | string | yes |  | matches ^\S+$ |

`--input` must match `^\S+\.(csv|tsv|json|yaml|yml)$`.

Additional row validation rules from the schema:
- When `fastq_2` is set, also provide `fastq_1`.
- When `spring_2` is set, also provide `spring_1`.
- When `bam` is set, also provide `bai`.
- At least one of these conditional requirements must be satisfied: `fastq_1` when `lane` is set; `spring_1` when `lane` is set.

For tabular CSV/TSV input, use this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
sample,sex,phenotype,case_id
```

Any of the optional columns above may be appended to the header when your data needs them: `lane`, `fastq_1`, `fastq_2`, `spring_1`, `spring_2`, `bam`, `bai`, `paternal_id`, `maternal_id`.

**From data files.** `--input` may also be the data files — a directory (searched recursively), a quoted glob, or files (`--input` once per file) — from which nfclaw writes this samplesheet: `sample` from file names; `fastq_1`/`fastq_2` from FastQ files (mates paired by `_R1`/`_R2`, or by `_1`/`_2` when their read names show they are mates); `lane` from Illumina lane numbers (`_L002` → 2, else 1); `bam`, `bai` from files matching their patterns, by sample name. Optional columns left out take their schema defaults in the pipeline: `paternal_id` = `0`, `maternal_id` = `0` — set them with `--sheet-set` where your design differs. Set the required columns no file determines with `--sheet-set COLUMN=VALUE` (a constant or a `{sample}`/`{lane}` template): `sex` (integer or string); `phenotype` (one of 0, 1, 2); `case_id` (matching ^\S+$). Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--fasta` | string (file path) |  |  | matches ^\S+\.fn?a(sta)?(\.gz)?$ | Path to FASTA genome file. |
| `--intervals-wgs` | string (file or directory path) |  |  | matches ^\S+\.intervals?(_list)?$ | Path to the interval list of the genome (autosomes, sex chromosomes, and mitochondria). |
| `--intervals-y` | string (file or directory path) |  |  | matches ^\S+\.intervals?(_list)?$ | Path to the interval list of the Y chromosome. |

## Reference genome
**This release resolves a reference genome remotely by default.** `--genome` defaults to `GRCh38`; the schema declares AWS iGenomes at `s3://ngi-igenomes/igenomes/`. The pinned configuration gives that key the FASTA `${params.igenomes_base}/Homo_sapiens/NCBI/GRCh38/Sequence/WholeGenomeFasta/genome.fa`. Resolving references through that default needs access to this source. For a self-contained run, pass your own reference instead (e.g. `--fasta`; the `reference_file_options` group in [reference.md](reference.md) lists every reference option). Set `--igenomes-ignore true` to disable the lookup entirely. Confirm the selected reference's paths and source in the pinned `upstream/nextflow.config` and `upstream/conf/` before running.

## Secrets
This release reads Nextflow secrets: `SENTIEON_AUTH_MECH_BASE64` (in `conf/test_sentieon.config`); `SENTIEON_AUTH_DATA_BASE64` (in `conf/test_sentieon.config`); `SENTIEON_LICENSE_BASE64` (in `modules/nf-core/sentieon/bwaindex/main.nf`, `modules/nf-core/sentieon/bwamem/main.nf` and 6 more files). Set each one a run needs with `nextflow secrets set NAME VALUE` before launching; a secret that is not set reaches its tasks as an empty value (Nextflow warns that the variable evaluates to an empty value), and a task that needs it then fails. Secrets are not written to nfclaw's provenance.

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, required, hidden, allowed values, constraints, default and description. Use it as the source of truth; do not guess flags. It uses nfclaw's hyphenated flags; raw Nextflow requires the exact schema spelling (usually underscores). nfclaw checks explicit parameters before launch; the pinned pipeline's validation handles conditional and complex constraints at runtime. It is organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Alignment options** (`alignment_options`) — 10 parameters
- **Analysis options** (`analysis_options`) — 17 parameters
- **Annotation options** (`annotation_options`) — 3 parameters
- **Generic options** (`generic_options`) — 17 parameters
- **Input/output options** (`input_output_options`) — 4 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **Mitosalt and saltshaker options** (`mitosalt_options`) — 27 parameters
- **Reference file options** (`reference_file_options`) — 61 parameters
- **Variant calling options** (`variant_calling_options`) — 5 parameters

Upstream usage: https://github.com/nf-core/raredisease/blob/3.1.2/docs/usage.md

## Resources
Resource requests follow the pipeline's configs and selected profiles. nf-core's resource labels often assume a server — a single step can request far more memory than a workstation has, and retry rules can increase requests. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run raredisease --input samplesheet.csv --outdir results --fasta <fasta> --intervals-wgs <intervals_wgs> --intervals-y <intervals_y> -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=25.10.4'`.

To pin this release's declared minimum engine — useful when a newer Nextflow has incompatible config parsing:
```bash
nfclaw run raredisease ... --nxf-ver 25.10.4
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/raredisease/blob/3.1.2/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: BCFtools, BEDTools, BWA-MEM, BWA-MEM2, BWA-MEME, CADD<sup>1</sup>, DeepVariant, Chromograph, Ensembl VEP, ExpansionHunter, FastQC, Fastp, GATK, Genmod, Gens, GLnexus, Manta, Mitosalt, Mosdepth, ngs-bits-samplegender, MultiQC, Peddy, Picard, RetroSeq, rhocall, RTG Tools (vcfeval), saltshaker, Sambamba, Sentieon DNAscope, Sentieon DNASeq, SMNCopyNumberCaller, Spring, stranger, svdb, Tabix, TIDDIT, UPD, UCSC Bigwig and Bigbed, vcf2cytosure, Vcfanno, VerifyBamID2.

Full list with references: https://github.com/nf-core/raredisease/blob/3.1.2/CITATIONS.md

## Demo
```bash
nfclaw run raredisease --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

<!-- Generated from nf-core/raredisease@83f2699d28bc957e1d3b875da3d96004a818c2c3. Do not edit by hand. -->
