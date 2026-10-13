---
name: seqinspector
pipeline: nf-core/seqinspector
version: 1.1.2
commit: 6aa08aabb00cdbb0f5b62adf2749b472e794ba04
description: Pipeline to QC your sequences
summary: nf-core/seqinspector is a bioinformatics pipeline that processes raw sequence data (FASTQ) to provide comprehensive quality control. It can perform subsampling, quality assessment, duplication level analysis, and complexity evaluation on a per-sample basis, while also detecting adapter content, technical artifacts, and common biological contaminants. The pipeline generates detailed MultiQC reports with flexible output options, ranging from individual sample reports to project-wide summaries, making it particularly useful for sequencing core facilities and research groups with access to sequencing instruments. If provided, nf-core/seqinspector can also parse statistics from an Illumina run folder directory into the final MultiQC reports.
has_samplesheet: true
input: samplesheet (sample, fastq_1, fastq_2, rundir, tags)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["BBMap", "BWAMEM2", "checkQC", "Chelae", "FastQC", "Kraken2", "Krona", "Fastp", "FastQ Screen", "FASTQE", "FQ", "MultiQC", "MultiQC SAV", "Riker", "Picard Tools", "Rundirparser", "SAMTOOLS", "SeqFu", "Seqkit", "Seqtk", "Sequali", "ToulligQC", "pigz", "Python", "PyYAML", "GNU tar"]
---
# seqinspector

nf-core/seqinspector is a bioinformatics pipeline that processes raw sequence data (FASTQ) to provide comprehensive quality control. It can perform subsampling, quality assessment, duplication level analysis, and complexity evaluation on a per-sample basis, while also detecting adapter content, technical artifacts, and common biological contaminants. The pipeline generates detailed MultiQC reports with flexible output options, ranging from individual sample reports to project-wide summaries, making it particularly useful for sequencing core facilities and research groups with access to sequencing instruments. If provided, nf-core/seqinspector can also parse statistics from an Illumina run folder directory into the final MultiQC reports.

## Run it
```bash
git submodule update --init pipelines/seqinspector/upstream   # first time only
nfclaw run seqinspector --input samplesheet.csv --outdir results -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/seqinspector/upstream -profile docker --input samplesheet.csv --outdir results
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions seqinspector` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show seqinspector --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show seqinspector --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `sample` | string | yes |  | matches ^\S+$ |
| `fastq_1` | string (file path) | yes |  | matches ^([\S\s]*\/)?[^\s\/]+\.f(ast)?q\.gz$ |
| `fastq_2` | string (file path) | no |  | matches ^([\S\s]*\/)?[^\s\/]+\.f(ast)?q\.gz$ |
| `rundir` | string | no |  |  |
| `tags` | string | no |  | matches ^([A-Za-z0-9_-]+:)*([A-Za-z0-9_-]+)$ |

`--input` must match `^\S+\.csv$`.

Additional row validation rules from the schema:
- When `fastq_2` is set, also provide `fastq_1`.

The samplesheet is a CSV with this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
sample,fastq_1
```

Any of the optional columns above may be appended to the header when your data needs them: `fastq_2`, `rundir`, `tags`.

**From data files.** `--input` may also be the data files — a directory (searched recursively), a quoted glob, or files (`--input` once per file) — from which nfclaw writes this samplesheet: `sample` from file names; `fastq_1`/`fastq_2` from FastQ files (mates paired by `_R1`/`_R2`, or by `_1`/`_2` when their read names show they are mates); `rundir` from files matching their patterns, by sample name. Set other columns with `--sheet-set COLUMN=VALUE`. Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file path) |  |  | matches ^\S+\.csv$ | Path to comma-separated file containing information about the samples in the experiment. |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## Reference genome
No reference genome is set by default: supply your own reference. The schema declares AWS iGenomes at `s3://ngi-igenomes/igenomes/`; selecting `--genome <id>` uses the paths in the pipeline's reference configuration. Access to that remote source is required. To supply your own reference, use e.g. `--fasta`; the `reference_genome_options` group in [reference.md](reference.md) lists every reference option. Set `--igenomes-ignore true` to disable the lookup entirely. Confirm the selected reference's paths and source in the pinned `upstream/nextflow.config` and `upstream/conf/` before running.

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, default, allowed values and constraints — organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **BBMap options** (`bbmap_options`) — 2 parameters
- **Generic options** (`generic_options`) — 16 parameters
- **Input/output options** (`input_output_options`) — 9 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **Kraken2 options** (`kraken2_options`) — 4 parameters
- **Reference genome options** (`reference_genome_options`) — 10 parameters
- **Riker options** (`riker_options`) — 1 parameter
- **Validation options** (`validation_options`) — 3 parameters

## Resources
Resource requests follow the pipeline's configs and selected profiles. nf-core's resource labels often assume a server — a single step can request far more memory than a workstation has, and retry rules can increase requests. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run seqinspector --input samplesheet.csv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=25.10.4'`.

To pin this release's declared minimum engine — useful when a newer Nextflow has incompatible config parsing:
```bash
nfclaw run seqinspector ... --nxf-ver 25.10.4
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/seqinspector/blob/1.1.2/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Chaining
Run seqinspector as one stage of a chain: `nfclaw chain run spec.json --outdir DIR` starts each stage only after the one before it succeeded, and prepares its inputs from that stage's outputs. The rules live in `handoffs/` (format and spec in [docs/chaining.md](../../docs/chaining.md)); list them with `nfclaw chain edges seqinspector`.

Fed by:
- `demultiplex` — demultiplex writes samplesheet/seqinspector_samplesheet.csv for its demultiplexed FastQ files.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: BBMap, BWAMEM2, checkQC, Chelae, FastQC, Kraken2, Krona, Fastp, FastQ Screen, FASTQE, FQ, MultiQC, MultiQC SAV, Riker, Picard Tools, Rundirparser, SAMTOOLS, SeqFu, Seqkit, Seqtk, Sequali, ToulligQC, pigz, Python, PyYAML, GNU tar.

Full list with references: https://github.com/nf-core/seqinspector/blob/1.1.2/CITATIONS.md

## Demo
```bash
nfclaw run seqinspector --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

## Full reference
Every parameter — name, type, required, hidden, allowed values, constraints, default and description — is in [reference.md](reference.md). Use it as the source of truth; do not guess flags. nfclaw checks explicit parameters before launch; the pinned pipeline's validation handles conditional and complex constraints at runtime. The reference uses nfclaw's hyphenated flags; raw Nextflow requires the exact schema spelling (usually underscores). Upstream usage: https://github.com/nf-core/seqinspector/blob/1.1.2/docs/usage.md

<!-- Generated from nf-core/seqinspector@6aa08aabb00cdbb0f5b62adf2749b472e794ba04. Do not edit by hand. -->
