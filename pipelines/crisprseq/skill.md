---
name: crisprseq
pipeline: nf-core/crisprseq
version: 2.3.0
commit: 0e9f915c4a3c89d02a66ec58e2decbc832323c8b
description: Pipeline for the analysis of CRISPR data
summary: nf-core/crisprseq is a bioinformatics best-practice analysis pipeline for the analysis of CRISPR edited data. It allows the evaluation of the quality of gene editing experiments using targeted next generation sequencing (NGS) data (targeted) as well as the discovery of important genes from knock-out or activation CRISPR-Cas9 screens using CRISPR pooled DNA (screening).
has_samplesheet: true
input: samplesheet (sample, fastq_1, fastq_2, condition, reference, protospacer, template)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["FastQC", "MultiQC", "Pear", "Seqtk", "Bowtie2", "BWA", "Minimap2", "Cutadapt", "Samtools", "MAGeCKFlute"]
---
# crisprseq

nf-core/crisprseq is a bioinformatics best-practice analysis pipeline for the analysis of CRISPR edited data. It allows the evaluation of the quality of gene editing experiments using targeted next generation sequencing (NGS) data (targeted) as well as the discovery of important genes from knock-out or activation CRISPR-Cas9 screens using CRISPR pooled DNA (screening).

## Run it
```bash
git submodule update --init pipelines/crisprseq/upstream   # first time only
nfclaw run crisprseq --input samplesheet.csv --outdir results --analysis <analysis> -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/crisprseq/upstream -profile docker --input samplesheet.csv --outdir results --analysis <analysis>
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions crisprseq` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show crisprseq --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show crisprseq --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `sample` | string | yes |  | matches ^\S+$ |
| `fastq_1` | string (file path) | yes |  | matches ^\S+\.f(ast)?q\.gz$ |
| `fastq_2` | string (file path) | no |  | matches ^\S+\.f(ast)?q\.gz$ |
| `condition` | string | no |  | matches ^\S+$ |
| `reference` | string | no |  | matches ^[ACTGNactgn]+$ |
| `protospacer` | string | no |  | matches ^[ACTGNactgn]+$ |
| `template` | string | no |  | matches ^[ACTGNactgn]+$ |

`--input` must match `^\S+\.csv$`.

The samplesheet is a CSV with this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
sample,fastq_1
```

Any of the optional columns above may be appended to the header when your data needs them: `fastq_2`, `condition`, `reference`, `protospacer`, `template`.

**From data files.** `--input` may also be the data files — a directory (searched recursively), a quoted glob, or files (`--input` once per file) — from which nfclaw writes this samplesheet: `sample` from file names; `fastq_1`/`fastq_2` from FastQ files (mates paired by `_R1`/`_R2`, or by `_1`/`_2` when their read names show they are mates). Set other columns with `--sheet-set COLUMN=VALUE`. Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--analysis` | string |  | `screening`, `targeted` |  | Type of analysis to perform. Targeted for targeted CRISPR experiments and screening for CRISPR screening experiments. |

## Reference genome
No reference genome is set by default: supply your own reference. The schema declares AWS iGenomes at `s3://ngi-igenomes/igenomes/`; selecting `--genome <id>` uses the paths in the pipeline's reference configuration. Access to that remote source is required. To supply your own reference, use e.g. `--fasta`; the `screening_parameters` group in [reference.md](reference.md) lists every reference option. Set `--igenomes-ignore true` to disable the lookup entirely. Confirm the selected reference's paths and source in the pinned `upstream/nextflow.config` and `upstream/conf/` before running.

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, required, hidden, allowed values, constraints, default and description. Use it as the source of truth; do not guess flags. It uses nfclaw's hyphenated flags; raw Nextflow requires the exact schema spelling (usually underscores). nfclaw checks explicit parameters before launch; the pinned pipeline's validation handles conditional and complex constraints at runtime. It is organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Generic options** (`generic_options`) — 12 parameters
- **Input/output options** (`input_output_options`) — 5 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **Reference genome options** (`reference_genome_options`) — 4 parameters
- **Screening parameters** (`screening_parameters`) — 21 parameters
- **Targeted parameters** (`targeted_parameters`) — 2 parameters
- **targeted pipeline steps** (`targeted_pipeline_steps`) — 3 parameters
- **UMI parameters** (`umi_parameters`) — 2 parameters
- **Vsearch parameters** (`vsearch_parameters`) — 3 parameters

Upstream usage: https://github.com/nf-core/crisprseq/blob/2.3.0/docs/usage.md

## Resources
Resource requests follow the pipeline's configs and selected profiles. nf-core's resource labels often assume a server — a single step can request far more memory than a workstation has, and retry rules can increase requests. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run crisprseq --input samplesheet.csv --outdir results --analysis <analysis> -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=24.04.2'`.

To pin this release's declared minimum engine — useful when a newer Nextflow has incompatible config parsing:
```bash
nfclaw run crisprseq ... --nxf-ver 24.04.2
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/crisprseq/blob/2.3.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: FastQC, MultiQC, Pear, Seqtk, Bowtie2, BWA, Minimap2, Cutadapt, Samtools, MAGeCKFlute.

Full list with references: https://github.com/nf-core/crisprseq/blob/2.3.0/CITATIONS.md

## Demo
```bash
nfclaw run crisprseq --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

<!-- Generated from nf-core/crisprseq@0e9f915c4a3c89d02a66ec58e2decbc832323c8b. Do not edit by hand. -->
