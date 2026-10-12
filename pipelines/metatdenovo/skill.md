---
name: metatdenovo
pipeline: nf-core/metatdenovo
version: 2.0.0
commit: e9f8311e9a24278fdaed0f8717eb819532aef55e
description: Assembly and annotation of metatranscriptomic data, both prokaryotic and eukaryotic
summary: nf-core/metatdenovo is a bioinformatics best-practice analysis pipeline for assembly and annotation of metatranscriptomic and metagenomic data from prokaryotes, eukaryotes or viruses.
has_samplesheet: true
input: samplesheet (sample, fastq_1, fastq_2)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["FastQC", "MultiQC", "Trim Galore!", "Seqtk", "SPAdes", "Megahit", "TransDecoder", "MetaEuk", "Prokka", "Prodigal", "BBmap", "FeatureCounts", "BEDTools", "MMseqs2", "SAMtools", "SeqKit", "Eggnog", "Kofamscan", "dbCAN", "HMMsearch", "EUKulele", "Diamond", "TaxonKit", "QUAST", "DuckDB"]
---
# metatdenovo

nf-core/metatdenovo is a bioinformatics best-practice analysis pipeline for assembly and annotation of metatranscriptomic and metagenomic data from prokaryotes, eukaryotes or viruses.

## Run it
```bash
git submodule update --init pipelines/metatdenovo/upstream   # first time only
nfclaw run metatdenovo --input samplesheet.csv --outdir results -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/metatdenovo/upstream -profile docker --input samplesheet.csv --outdir results
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions metatdenovo` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show metatdenovo --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show metatdenovo --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `sample` | string | yes |  | matches ^\S+$ |
| `fastq_1` | string (file path) | yes |  | matches ^([\S\s]*\/)?[^\s\/]+\.f(ast)?q(\.gz)?$ |
| `fastq_2` | string (file path) | no |  | matches ^([\S\s]*\/)?[^\s\/]+\.f(ast)?q(\.gz)?$ |

`--input` must match `^\S+\.csv$`.

The samplesheet is a CSV with this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
sample,fastq_1
```

Any of the optional columns above may be appended to the header when your data needs them: `fastq_2`.

**From data files.** `--input` may also be the data files — a directory (searched recursively), a quoted glob, or files (`--input` once per file) — from which nfclaw writes this samplesheet: `sample` from file names; `fastq_1`/`fastq_2` from FastQ files (mates paired by `_R1`/`_R2`, or by `_1`/`_2` when their read names show they are mates). Set other columns with `--sheet-set COLUMN=VALUE`. Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file path) |  |  | matches ^\S+\.csv$ | Path to comma-separated file containing information about the samples in the experiment. |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, default, allowed values and constraints — organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Assembler options** (`assembler_options`) — 11 parameters
- **Filtering options** (`bbduk_options`) — 3 parameters
- **Consolidation options** (`consolidation_options`) — 4 parameters
- **Digital normalization options** (`digital_normalization_options`) — 4 parameters
- **Functional annotation options** (`functional_annotation_options`) — 15 parameters
- **Generic options** (`generic_options`) — 15 parameters
- **Input/output options** (`input_output_options`) — 5 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **Mapping options** (`mapping_options`) — 5 parameters
- **Orf Caller options** (`orf_caller_options`) — 12 parameters
- **Quality control options** (`quality_control_options`) — 1 parameter
- **Quantification options** (`quantification_options`) — 2 parameters
- **Taxonomy annotation options** (`taxonomy_annotation_options`) — 7 parameters
- **trimming options** (`trimming_options`) — 7 parameters

## Resources
A real (non-`--demo`) run requests the resources the pipeline's `conf/base.config` asks for, which are sized for a server — a single step can request far more memory than a workstation has, and Nextflow retries a failed step with more still. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run metatdenovo --input samplesheet.csv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=25.10.4'`.

To run the engine this release targets — worth doing if a newer Nextflow emits config-parser warnings the release never saw:
```bash
nfclaw run metatdenovo ... --nxf-ver 25.10.4
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/metatdenovo/blob/2.0.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Chaining
Run metatdenovo as one stage of a chain: `nfclaw chain run spec.json --outdir DIR` starts each stage only after the one before it succeeded, and prepares its inputs from that stage's outputs. The rules live in `handoffs/` (format and spec in [docs/chaining.md](../../docs/chaining.md)); list them with `nfclaw chain edges metatdenovo`.

Fed by:
- `fetchngs` — fetchngs writes a metatdenovo samplesheet (sample, fastq_1, fastq_2) with --nf-core-pipeline metatdenovo.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: FastQC, MultiQC, Trim Galore!, Seqtk, SPAdes, Megahit, TransDecoder, MetaEuk, Prokka, Prodigal, BBmap, FeatureCounts, BEDTools, MMseqs2, SAMtools, SeqKit, Eggnog, Kofamscan, dbCAN, HMMsearch, EUKulele, Diamond, TaxonKit, QUAST, DuckDB.

Full list with references: https://github.com/nf-core/metatdenovo/blob/2.0.0/CITATIONS.md

## Demo
```bash
nfclaw run metatdenovo --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

## Full reference
Every parameter — name, type, required, hidden, allowed values, constraints, default and description — is in [reference.md](reference.md). Use it as the source of truth; do not guess flags. Nextflow's nf-schema validates every parameter against this schema at runtime, so an unknown or invalid value fails fast. Upstream usage: https://github.com/nf-core/metatdenovo/blob/2.0.0/docs/usage.md

<!-- Generated from nf-core/metatdenovo@e9f8311e9a24278fdaed0f8717eb819532aef55e. Do not edit by hand. -->
