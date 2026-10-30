---
name: rangeland
pipeline: nf-core/rangeland
version: 1.0.0
commit: 7c5cb9593b80d2a3cdc8bcb14137722351644435
description: Long-term vegetation trend analysis pipeline for rangeland systems using satellite imagery.
summary: nf-core/rangeland is a geographical best-practice analysis pipeline for remotely sensed imagery. The pipeline processes satellite imagery alongside auxiliary data in multiple steps to arrive at a set of trend files related to land-cover changes. The main pipeline steps are:
has_samplesheet: false
input: --input (no samplesheet schema)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["FORCE", "MultiQC"]
---
# rangeland

nf-core/rangeland is a geographical best-practice analysis pipeline for remotely sensed imagery. The pipeline processes satellite imagery alongside auxiliary data in multiple steps to arrive at a set of trend files related to land-cover changes. The main pipeline steps are:

## Run it
```bash
git submodule update --init pipelines/rangeland/upstream   # first time only
nfclaw run rangeland --input <input> --outdir results --dem <dem> --wvdb <wvdb> --data-cube <data_cube> --aoi <aoi> --endmember <endmember> -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/rangeland/upstream -profile docker --input <input> --outdir results --dem <dem> --wvdb <wvdb> --data_cube <data_cube> --aoi <aoi> --endmember <endmember>
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions rangeland` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show rangeland --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show rangeland --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
This release publishes no samplesheet schema for `--input`, so nfclaw does not pre-check its contents. The parameter reads: Root directory or tarball of all satellite imagery. Configure the other inputs via parameters (see [reference.md](reference.md)).

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file or directory path) |  |  |  | Root directory or tarball of all satellite imagery. |
| `--dem` | string (file or directory path) |  |  |  | Digital elevation model. |
| `--wvdb` | string (file or directory path) |  |  |  | Water vapor dataset. |
| `--data-cube` | string (file path) |  |  | matches `^\S+\.prj$` | Datacube definition. |
| `--aoi` | string (file path) |  |  | matches `^\S+\.(gpkg\|shp)$` | Area of interest. |
| `--endmember` | string (file path) |  |  | matches `^\S+\.txt$` | Endmember definition. |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, required, hidden, allowed values, constraints, default and description. Use it as the source of truth; do not guess flags. It uses nfclaw's hyphenated flags; raw Nextflow requires the exact schema spelling (usually underscores). nfclaw checks explicit parameters before launch; the pinned pipeline's validation handles conditional and complex constraints at runtime. It is organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Generic options** (`generic_options`) — 13 parameters
- **Higher level processing modification** (`higher_level_processing_modification`) — 2 parameters
- **Input/output options** (`input_output_options`) — 9 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **Remote sensing image options** (`remote_sensing_image_options`) — 4 parameters
- **Visualization** (`visualization`) — 2 parameters
- **Workflow configuration** (`workflow_configuration`) — 4 parameters

Upstream usage: https://github.com/nf-core/rangeland/blob/1.0.0/docs/usage.md

## Resources
Resource requests follow the pipeline's configs and selected profiles. nf-core's resource labels often assume a server — a single step can request far more memory than a workstation has, and retry rules can increase requests. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run rangeland --input <input> --outdir results --dem <dem> --wvdb <wvdb> --data-cube <data_cube> --aoi <aoi> --endmember <endmember> -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=24.04.2'`.

To pin this release's declared minimum engine — useful when a newer Nextflow has incompatible config parsing:
```bash
nfclaw run rangeland ... --nxf-ver 24.04.2
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/rangeland/blob/1.0.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: FORCE, MultiQC.

Full list with references: https://github.com/nf-core/rangeland/blob/1.0.0/CITATIONS.md

## Demo
```bash
nfclaw run rangeland --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

<!-- Generated from nf-core/rangeland@7c5cb9593b80d2a3cdc8bcb14137722351644435. Do not edit by hand. -->
