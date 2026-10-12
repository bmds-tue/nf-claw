---
name: proteinfold
pipeline: nf-core/proteinfold
version: 2.0.0
commit: 5338c24b2af62cc4c02dcd34bcc49912eebffb3a
description: Protein 3D structure prediction pipeline
summary: nf-core/proteinfold is a bioinformatics best-practice analysis pipeline for Protein 3D structure prediction.
has_samplesheet: true
input: samplesheet (sequence, id, fasta)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["AlphaFold", "ColabFold", "MMseqs2", "ESMFold", "MultiQC"]
---
# proteinfold

nf-core/proteinfold is a bioinformatics best-practice analysis pipeline for Protein 3D structure prediction.

## Run it
```bash
git submodule update --init pipelines/proteinfold/upstream   # first time only
nfclaw run proteinfold --input samplesheet.csv --outdir results -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/proteinfold/upstream -profile docker --input samplesheet.csv --outdir results
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions proteinfold` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show proteinfold --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show proteinfold --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `sequence` | string | no |  | matches ^\S+$ |
| `id` | string | no |  | matches ^\S+$ |
| `fasta` | string (file path) | yes |  | matches ^\S+\.(fa(sta)?\|faa\|yaml\|yml\|json)$ |

`--input` must match `^\S+\.csv$`.

The samplesheet is a CSV with this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
fasta
```

Any of the optional columns above may be appended to the header when your data needs them: `sequence`, `id`.

**From data files.** `--input` may also be the data files — a directory (searched recursively), a glob or several files — from which nfclaw writes this samplesheet: `id` from file names; `fasta` from files matching their patterns, by sample name. Set other columns with `--sheet-set COLUMN=VALUE`. Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file path) |  |  | matches ^\S+\.csv$ | Path to comma-separated file containing information about the samples in the experiment. |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, default, allowed values and constraints — organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **AlphaFold2 DBs and parameters links options** (`alphafold2_dbs_and_parameters_link_options`) — 12 parameters
- **AlphaFold2 DBs and parameters paths options** (`alphafold2_dbs_and_parameters_paths_options`) — 12 parameters
- **AlphaFold2 options** (`alphafold2_options`) — 6 parameters
- **AlphaFold3 DBs and parameters links options** (`alphafold3_dbs_and_parameters_link_options`) — 10 parameters
- **AlphaFold3 DBs and parameters links options** (`alphafold3_dbs_and_parameters_path_options`) — 10 parameters
- **Boltz DBs and model links options** (`boltz_dbs_and_model_links_options`) — 5 parameters
- **Boltz DBs and model paths options** (`boltz_dbs_and_parameters_paths_options`) — 6 parameters
- **Boltz options** (`boltz_options`) — 3 parameters
- **ColabFold DBs and parameters links options** (`colabfold_dbs_and_parameters_link_options`) — 3 parameters
- **ColabFold DBs and parameters paths options** (`colabfold_dbs_and_parameters_paths_options`) — 5 parameters
- **ColabFold options** (`colabfold_options`) — 7 parameters
- **ESMFold options** (`esmfold_options`) — 2 parameters
- **ESMFold parameters links options** (`esmfold_parameters_link_options`) — 3 parameters
- **ESMFold parameters paths options** (`esmfold_parameters_paths_options`) — 2 parameters
- **Foldseek options** (`foldseek_options`) — 4 parameters
- **Generic options** (`generic_options`) — 16 parameters
- **HelixFold3 dbs and parameters link options** (`helixfold3_dbs_and_parameters_link_options`) — 14 parameters
- **HelixFold3 dbs and parameters paths options** (`helixfold3_dbs_and_parameters_paths_options`) — 14 parameters
- **HelixFold3 options** (`helixfold3_options`) — 3 parameters
- **Global options** (`input_output_options`) — 13 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **Process skipping options** (`process_skipping_options`) — 2 parameters
- **RosettaFold2NA DBs and parameters links options** (`rosettafold2na_dbs_and_parameters_link_options`) — 9 parameters
- **RosettaFold2NA DBs and parameters paths options** (`rosettafold2na_dbs_and_parameters_path_options`) — 5 parameters
- **RosettaFold2NA options** (`rosettafold2na_options`) — 1 parameter
- **RoseTTAFold All Atom DBs and parameters links options** (`rosettafold_all_atom_dbs_and_parameters_links_options`) — 4 parameters
- **RoseTTAFold All Atom DBs and parameters paths options** (`rosettafold_all_atom_dbs_and_parameters_paths_options`) — 5 parameters

## Resources
A real (non-`--demo`) run requests the resources the pipeline's `conf/base.config` asks for, which are sized for a server — a single step can request far more memory than a workstation has, and Nextflow retries a failed step with more still. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run proteinfold --input samplesheet.csv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=25.10.2'`.

To run the engine this release targets — worth doing if a newer Nextflow emits config-parser warnings the release never saw:
```bash
nfclaw run proteinfold ... --nxf-ver 25.10.2
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `--skip-multiqc true` disables that report. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/proteinfold/blob/2.0.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: AlphaFold, ColabFold, MMseqs2, ESMFold, MultiQC.

Full list with references: https://github.com/nf-core/proteinfold/blob/2.0.0/CITATIONS.md

## Demo
```bash
nfclaw run proteinfold --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

## Full reference
Every parameter — name, type, required, hidden, allowed values, constraints, default and description — is in [reference.md](reference.md). Use it as the source of truth; do not guess flags. Nextflow's nf-schema validates every parameter against this schema at runtime, so an unknown or invalid value fails fast. Upstream usage: https://github.com/nf-core/proteinfold/blob/2.0.0/docs/usage.md

<!-- Generated from nf-core/proteinfold@5338c24b2af62cc4c02dcd34bcc49912eebffb3a. Do not edit by hand. -->
