---
name: proteinfamilies
pipeline: nf-core/proteinfamilies
version: 2.6.0
commit: 318acd54eb9c679553338b2db46313bb469d03d1
description: Generate protein family level models (Multiple Sequence Alignments (MSAs), Hidden Markov Models (HMMs)) starting from a FASTA amino acid sequence file.
summary: nf-core/proteinfamilies is a bioinformatics pipeline that generates protein families from amino acid sequences and/or updates existing families with new sequences. It takes a protein fasta file as input, clusters the sequences and then generates protein family Hidden Markov Models (HMMs) along with their multiple sequence alignments (MSAs). Optionally, paths to existing family HMMs and MSAs can be given (must have matching base filenames one-to-one) in order to update with new sequences in case of matching hits.
has_samplesheet: true
input: samplesheet (sample, fasta, existing_hmms_to_update, existing_msas_to_update)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["SeqFu", "SeqKit", "MMseqs2", "FAMSA", "mafft", "ClipKIT", "hmmer", "HH-suite3", "Biopython", "CMAPLE", "MultiQC"]
---
# proteinfamilies

nf-core/proteinfamilies is a bioinformatics pipeline that generates protein families from amino acid sequences and/or updates existing families with new sequences. It takes a protein fasta file as input, clusters the sequences and then generates protein family Hidden Markov Models (HMMs) along with their multiple sequence alignments (MSAs). Optionally, paths to existing family HMMs and MSAs can be given (must have matching base filenames one-to-one) in order to update with new sequences in case of matching hits.

## Run it
```bash
git submodule update --init pipelines/proteinfamilies/upstream   # first time only
nfclaw run proteinfamilies --input samplesheet.csv --outdir results -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/proteinfamilies/upstream -profile docker --input samplesheet.csv --outdir results
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions proteinfamilies` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show proteinfamilies --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show proteinfamilies --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `sample` | string | yes |  | matches ^[a-zA-Z0-9._-]+$ |
| `fasta` | string (file path) | yes |  | matches ^([\S\s]*\/)?[^\s\/]+\.(fa\|fasta\|faa\|fas)(\.gz)?$ |
| `existing_hmms_to_update` | string (file path) | no |  | matches ^([\S\s]*\/)?[^\s\/]+\.tar\.gz$ |
| `existing_msas_to_update` | string (file path) | no |  | matches ^([\S\s]*\/)?[^\s\/]+\.tar\.gz$ |

`--input` must match `^\S+\.csv$`.

The samplesheet is a CSV with this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
sample,fasta
```

Any of the optional columns above may be appended to the header when your data needs them: `existing_hmms_to_update`, `existing_msas_to_update`.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file path) |  |  | matches ^\S+\.csv$ | Path to comma-separated file '.csv' containing information about the samples in the experiment. |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, default, allowed values and constraints — organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Alignment parameters** (`alignment_params`) — 12 parameters
- **Clustering parameters** (`clustering_params`) — 8 parameters
- **Downstream samplsheet creation parameters** (`downstream_params`) — 2 parameters
- **Family generation parameters** (`family_generation_params`) — 3 parameters
- **Generic options** (`generic_options`) — 15 parameters
- **Input/output options** (`input_output_options`) — 4 parameters
- **Institutional config options** (`institutional_config_options`) — 7 parameters
- **Parameters for phylogenetic inference of full alignment sequences** (`phylogeny_params`) — 1 parameter
- **Quality check parameters** (`quality_check_params`) — 4 parameters
- **Redundancy removal parameters** (`redundancy_params`) — 10 parameters
- **Update mechanism parameters** (`update_params`) — 2 parameters

## Resources
A real (non-`--demo`) run requests the resources the pipeline's `conf/base.config` asks for, which are sized for a server — a single step can request far more memory than a workstation has, and Nextflow retries a failed step with more still. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run proteinfamilies --input samplesheet.csv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=26.04.0'`.

To run the engine this release targets — worth doing if a newer Nextflow emits config-parser warnings the release never saw:
```bash
nfclaw run proteinfamilies ... --nxf-ver 26.04.0
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/proteinfamilies/blob/2.6.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: SeqFu, SeqKit, MMseqs2, FAMSA, mafft, ClipKIT, hmmer, HH-suite3, Biopython, CMAPLE, MultiQC.

Full list with references: https://github.com/nf-core/proteinfamilies/blob/2.6.0/CITATIONS.md

## Demo
```bash
nfclaw run proteinfamilies --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

## Full reference
Every parameter — name, type, required, hidden, allowed values, constraints, default and description — is in [reference.md](reference.md). Use it as the source of truth; do not guess flags. Nextflow's nf-schema validates every parameter against this schema at runtime, so an unknown or invalid value fails fast. Upstream usage: https://github.com/nf-core/proteinfamilies/blob/2.6.0/docs/usage.md

<!-- Generated from nf-core/proteinfamilies@318acd54eb9c679553338b2db46313bb469d03d1. Do not edit by hand. -->
