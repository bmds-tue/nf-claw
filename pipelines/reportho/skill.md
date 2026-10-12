---
name: reportho
pipeline: nf-core/reportho
version: 1.1.0
commit: 9e8ae5a07ddb5ccd34bb01c72e70e390d97d1cb7
description: A pipeline for ortholog fetching and analysis
summary: nf-core/reportho is a bioinformatics pipeline that compares and summarizes orthology predictions for one or a set of query proteins. For each query (or its closest annotated homolog), it fetches ortholog lists from public databases, identifies synonymous identifiers based on sequences, calculates the agreement of the obtained predictions (pairwise and global) and finally generates a consensus list of orthologs with the desired level of confidence. Additionally, it generates a clean, human-readable report of the results.
has_samplesheet: true
input: samplesheet (id, query, fasta)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["OMA", "PANTHER", "OrthoInspector", "EggNOG", "UniProt", "UniProt ID Mapping", "Diamond", "RefSeq", "Ensembl", "MultiQC"]
---
# reportho

nf-core/reportho is a bioinformatics pipeline that compares and summarizes orthology predictions for one or a set of query proteins. For each query (or its closest annotated homolog), it fetches ortholog lists from public databases, identifies synonymous identifiers based on sequences, calculates the agreement of the obtained predictions (pairwise and global) and finally generates a consensus list of orthologs with the desired level of confidence. Additionally, it generates a clean, human-readable report of the results.

## Run it
```bash
git submodule update --init pipelines/reportho/upstream   # first time only
nfclaw run reportho --input samplesheet.csv --outdir results -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/reportho/upstream -profile docker --input samplesheet.csv --outdir results
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions reportho` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show reportho --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show reportho --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `id` | string | no |  | matches ^\S+$ |
| `query` | string | no |  | matches ^\S+$ |
| `fasta` | string (file path) | no |  | matches ^\S+\.fa(sta)?$ |

`--input` must match `^\S+\.csv$`.

The samplesheet is a CSV with this header; fill each value per the table above and `reference.md` (no example value is invented here):
```csv
id,query,fasta
```

**From data files.** `--input` may also be the data files — a directory (searched recursively), a glob or several files — from which nfclaw writes this samplesheet: `id` from file names; `fasta` from files matching their patterns, by sample name. Set other columns with `--sheet-set COLUMN=VALUE`. Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file path) |  |  | matches ^\S+\.csv$ | Path to comma-separated file containing information about the samples in the experiment. |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, default, allowed values and constraints — organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Downstream analysis options** (`downstream_options`) — 1 parameter
- **Generic options** (`generic_options`) — 16 parameters
- **Input/output options** (`input_output_options`) — 5 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **Ortholog search options** (`ortholog_options`) — 21 parameters
- **Process skipping options** (`process_skipping_options`) — 2 parameters

## Resources
A real (non-`--demo`) run requests the resources the pipeline's `conf/base.config` asks for, which are sized for a server — a single step can request far more memory than a workstation has, and Nextflow retries a failed step with more still. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run reportho --input samplesheet.csv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=25.04.0'`.

To run the engine this release targets — worth doing if a newer Nextflow emits config-parser warnings the release never saw:
```bash
nfclaw run reportho ... --nxf-ver 25.04.0
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `--skip-multiqc true` disables that report. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/reportho/blob/1.1.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: OMA, PANTHER, OrthoInspector, EggNOG, UniProt, UniProt ID Mapping, Diamond, RefSeq, Ensembl, MultiQC.

Full list with references: https://github.com/nf-core/reportho/blob/1.1.0/CITATIONS.md

## Demo
```bash
nfclaw run reportho --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

## Full reference
Every parameter — name, type, required, hidden, allowed values, constraints, default and description — is in [reference.md](reference.md). Use it as the source of truth; do not guess flags. Nextflow's nf-schema validates every parameter against this schema at runtime, so an unknown or invalid value fails fast. Upstream usage: https://github.com/nf-core/reportho/blob/1.1.0/docs/usage.md

<!-- Generated from nf-core/reportho@9e8ae5a07ddb5ccd34bb01c72e70e390d97d1cb7. Do not edit by hand. -->
