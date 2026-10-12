---
name: callingcards
pipeline: nf-core/callingcards
version: 1.0.0
commit: 20b66e785a822028eaa125583aad0747d55bba61
description: An automated processing pipeline for mammalian bulk calling cards experiments
summary: nf-core/callingcards is a bioinformatics pipeline that can be used to process raw Calling Cards data obtained from either mammals (human, mouse) or yeast. It takes a samplesheet, which describes the sample names, paths to the fastq files, and paths to the barcode details json files, a parameter which identifies the organism type (either mammals or yeast) and either the name of the reference genome on igenomes or paths to the fasta/gff. It then parses the reads, counts the number of calling cards insertions, and provides some QC metrics.
has_samplesheet: true
input: samplesheet (sample, fastq_1, fastq_2, barcode_details)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["bedtools", "bowtie", "bowtie2", "bwa", "bwamem2", "callingCardsTools", "FastQC", "MultiQC", "nf-core/rnaseq:GTF2BED", "picard", "rseqc", "samtools", "seqkit", "trimmomatic", "UMITools"]
---
# callingcards

nf-core/callingcards is a bioinformatics pipeline that can be used to process raw Calling Cards data obtained from either mammals (human, mouse) or yeast. It takes a samplesheet, which describes the sample names, paths to the fastq files, and paths to the barcode details json files, a parameter which identifies the organism type (either mammals or yeast) and either the name of the reference genome on igenomes or paths to the fasta/gff. It then parses the reads, counts the number of calling cards insertions, and provides some QC metrics.

## Run it
```bash
git submodule update --init pipelines/callingcards/upstream   # first time only
nfclaw run callingcards --input samplesheet.csv --outdir results --datatype <datatype> -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/callingcards/upstream -profile docker --input samplesheet.csv --outdir results --datatype <datatype>
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions callingcards` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show callingcards --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show callingcards --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `sample` | string | yes |  | matches ^\S+$ |
| `fastq_1` | string (file path) | yes |  | matches ^\S+\.f(ast)?q\.gz$ |
| `fastq_2` | string (file path) | no |  |  |
| `barcode_details` | string (file path) | yes |  | matches ^\S+\.json$ |

`--input` must match `^\S+\.csv$`.

The samplesheet is a CSV with this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
sample,fastq_1,barcode_details
```

Any of the optional columns above may be appended to the header when your data needs them: `fastq_2`.

**From data files.** `--input` may also be the data files — a directory (searched recursively), a glob or several files — from which nfclaw writes this samplesheet: `sample` from file names; `fastq_1`/`fastq_2` from FastQ files (mates paired by `_R1`/`_R2` or `_1`/`_2` and confirmed by read name); `barcode_details` from files matching their patterns, by sample name. Set other columns with `--sheet-set COLUMN=VALUE`. Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--datatype` | string |  | `yeast`, `mammals` |  | This determines which workflow to run based on the organism and method from which the data originates. Current options are 'yeast' and 'mammals' |
| `--input` | string (file path) |  |  | matches ^\S+\.csv$ | Path to comma-separated file containing information about the samples in the experiment. |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## Reference genome
No reference genome is set by default: supply your own reference. A genome name alone does not specify where reference files come from. Confirm the selected reference's paths and source in the pinned `upstream/nextflow.config` and `upstream/conf/` before running. To supply your own reference, use e.g. `--fasta`; the `reference_genome_options` group in [reference.md](reference.md) lists every reference option. Set `--igenomes-ignore true` to disable the lookup entirely.

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, default, allowed values and constraints — organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Alignment options** (`alignment_options`) — 1 parameter
- **Generic options** (`generic_options`) — 16 parameters
- **Hops counting options** (`hops_counting_options`) — 1 parameter
- **Input/output options** (`input_output_options`) — 8 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **Max job request options** (`max_job_request_options`) — 3 parameters
- **QC options** (`qc_options`) — 1 parameter
- **Read processing options** (`read_processing_options`) — 6 parameters
- **Reference genome options** (`reference_genome_options`) — 11 parameters

## Resources
A real (non-`--demo`) run requests the resources the pipeline's `conf/base.config` asks for, which are sized for a server — a single step can request far more memory than a workstation has, and Nextflow retries a failed step with more still. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run callingcards --input samplesheet.csv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=23.04.0'`.

To run the engine this release targets — worth doing if a newer Nextflow emits config-parser warnings the release never saw:
```bash
nfclaw run callingcards ... --nxf-ver 23.04.0
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

Nextflow 23.04.0 predates `process.resourceLimits` (24.04.0), so `--limit-*` cannot be combined with this pin — nfclaw refuses it rather than run without the ceiling; cap resources with the release's own `--max-cpus`, `--max-memory`, `--max-time` instead.

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/callingcards/blob/1.0.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: bedtools, bowtie, bowtie2, bwa, bwamem2, callingCardsTools, FastQC, MultiQC, nf-core/rnaseq:GTF2BED, picard, rseqc, samtools, seqkit, trimmomatic, UMITools.

Full list with references: https://github.com/nf-core/callingcards/blob/1.0.0/CITATIONS.md

## Demo
```bash
nfclaw run callingcards --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

## Full reference
Every parameter — name, type, required, hidden, allowed values, constraints, default and description — is in [reference.md](reference.md). Use it as the source of truth; do not guess flags. Nextflow's nf-schema validates every parameter against this schema at runtime, so an unknown or invalid value fails fast. Upstream usage: https://github.com/nf-core/callingcards/blob/1.0.0/docs/usage.md

<!-- Generated from nf-core/callingcards@20b66e785a822028eaa125583aad0747d55bba61. Do not edit by hand. -->
