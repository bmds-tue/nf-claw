---
name: provenancereport
pipeline: nf-core/provenancereport
version: 1.0.0
commit: 89ed44de8da1788e5f00a6dd95bd72c51ff36dff
description: Generate reproducible Quarto reports together with an audit trail of inputs, checksums, software versions, runtime environments, and provenance metadata.
summary: nf-core/provenancereport is a reporting pipeline that validates a samplesheet and renders reproducible Quarto reports. The samplesheet has two columns, id and path, where each row points to one input file. The pipeline stages all listed files into a single Quarto render and publishes the rendered report plus any generated artifacts.
has_samplesheet: true
input: samplesheet (id, path)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["Quarto", "nf-prov", "MultiQC"]
---
# provenancereport

nf-core/provenancereport is a reporting pipeline that validates a samplesheet and renders reproducible Quarto reports. The samplesheet has two columns, id and path, where each row points to one input file. The pipeline stages all listed files into a single Quarto render and publishes the rendered report plus any generated artifacts.

## Run it
```bash
git submodule update --init pipelines/provenancereport/upstream   # first time only
nfclaw run provenancereport --input samplesheet.csv --outdir results -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/provenancereport/upstream -profile docker --input samplesheet.csv --outdir results
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions provenancereport` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show provenancereport --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show provenancereport --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `id` | string | yes |  | matches ^[A-Za-z_][A-Za-z0-9_]*$ |
| `path` | string (file path) | yes |  | matches ^[^\s,]+$ |

`--input` must match `^\S+\.csv$`.

The samplesheet is a CSV with this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
id,path
```

**From data files.** nfclaw cannot generate this samplesheet: the samplesheet declares no file type nfclaw could match files against (no column's pattern names a file extension).

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file path) |  |  | matches ^\S+\.csv$ | Path to comma-separated file containing ids and file paths to include in the report. |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, default, allowed values and constraints — organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Generic options** (`generic_options`) — 11 parameters
- **Input/output options** (`input_output_options`) — 5 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters

## Resources
Resource requests follow the pipeline's configs and selected profiles. nf-core's resource labels often assume a server — a single step can request far more memory than a workstation has, and retry rules can increase requests. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run provenancereport --input samplesheet.csv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=25.10.4'`.

To pin this release's declared minimum engine — useful when a newer Nextflow has incompatible config parsing:
```bash
nfclaw run provenancereport ... --nxf-ver 25.10.4
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/provenancereport/blob/1.0.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: Quarto, nf-prov, MultiQC.

Full list with references: https://github.com/nf-core/provenancereport/blob/1.0.0/CITATIONS.md

## Demo
```bash
nfclaw run provenancereport --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

## Full reference
Every parameter — name, type, required, hidden, allowed values, constraints, default and description — is in [reference.md](reference.md). Use it as the source of truth; do not guess flags. nfclaw checks explicit parameters before launch; the pinned pipeline's validation handles conditional and complex constraints at runtime. The reference uses nfclaw's hyphenated flags; raw Nextflow requires the exact schema spelling (usually underscores). Upstream usage: https://github.com/nf-core/provenancereport/blob/1.0.0/docs/usage.md

<!-- Generated from nf-core/provenancereport@89ed44de8da1788e5f00a6dd95bd72c51ff36dff. Do not edit by hand. -->
