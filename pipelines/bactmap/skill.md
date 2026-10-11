---
name: bactmap
pipeline: nf-core/bactmap
version: 1.0.0
commit: 834642d8ac150ca10d705833223e7bcf15efc210
description: A mapping-based pipeline for creating a phylogeny from bacterial whole genome sequences
summary: nf-core/bactmap is a bioinformatics best-practice analysis pipeline for mapping short reads from bacterial WGS to a reference sequence, creating filtered VCF files, making pseudogenomes based on high quality positions in the VCF files and optionally creating a phylogeny from an alignment of the pseudogenomes.
has_samplesheet: false
input: --input (no samplesheet schema)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled)
tools: ["bcftools", "BWA", "fastp", "FastQC", "FastTree2", "Gubbins", "IQ-TREE2", "Mash", "MultiQC", "RapidNJ", "RAxML-NG", "Rasusa", "samtools", "SNP-sites"]
---
# bactmap

nf-core/bactmap is a bioinformatics best-practice analysis pipeline for mapping short reads from bacterial WGS to a reference sequence, creating filtered VCF files, making pseudogenomes based on high quality positions in the VCF files and optionally creating a phylogeny from an alignment of the pseudogenomes.

## Run it
```bash
git submodule update --init pipelines/bactmap/upstream   # first time only
nfclaw run bactmap --input <input> --outdir results --reference <reference> -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/bactmap/upstream -profile docker --input <input> --outdir results --reference <reference>
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions bactmap` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show bactmap --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show bactmap --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
This release publishes no samplesheet schema for `--input`, so nfclaw does not pre-check its contents. The parameter reads: Path to a sample sheet describing paths to input fastq files. Configure the other inputs via parameters (see [reference.md](reference.md)).

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string |  |  |  | Path to a sample sheet describing paths to input fastq files |
| `--reference` | string |  |  |  | Path to a fasta file of the reference sequence |

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, default, allowed values and constraints — organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Compulsory parameters** (`compulsory_parameters`) — 1 parameter
- **Generic options** (`generic_options`) — 14 parameters
- **Input/output options** (`input_output_options`) — 3 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **Max job request options** (`max_job_request_options`) — 3 parameters
- **Optional pipeline steps** (`optional_pipeline_steps`) — 12 parameters

## Resources
A real (non-`--demo`) run requests the resources the pipeline's `conf/base.config` asks for, which are sized for a server — a single step can request far more memory than a workstation has, and Nextflow retries a failed step with more still. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run bactmap --input <input> --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=21.04.0'`.

To run the engine this release targets — worth doing if a newer Nextflow emits config-parser warnings the release never saw:
```bash
nfclaw run bactmap ... --nxf-ver 21.04.0
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

Nextflow 21.04.0 predates `process.resourceLimits` (24.04.0), so `--limit-*` cannot be combined with this pin — nfclaw refuses it rather than run without the ceiling; cap resources with the release's own `--max-cpus`, `--max-memory`, `--max-time` instead.

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/bactmap/blob/1.0.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: bcftools, BWA, fastp, FastQC, FastTree2, Gubbins, IQ-TREE2, Mash, MultiQC, RapidNJ, RAxML-NG, Rasusa, samtools, SNP-sites.

Full list with references: https://github.com/nf-core/bactmap/blob/1.0.0/CITATIONS.md

## Demo
```bash
nfclaw run bactmap --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

## Full reference
Every parameter — name, type, required, hidden, allowed values, constraints, default and description — is in [reference.md](reference.md). Use it as the source of truth; do not guess flags. Nextflow's nf-schema validates every parameter against this schema at runtime, so an unknown or invalid value fails fast. Upstream usage: https://github.com/nf-core/bactmap/blob/1.0.0/docs/usage.md

<!-- Generated from nf-core/bactmap@834642d8ac150ca10d705833223e7bcf15efc210. Do not edit by hand. -->
