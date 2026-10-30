---
name: pathogensurveillance
pipeline: nf-core/pathogensurveillance
version: 1.1.0
commit: 13547eaa7345dab4ac97db49775ae8284af4113d
description: Surveillance of pathogens using high-throughput sequencing
summary: nf-core/pathogensurveillance is a population genomics pipeline for pathogen identification, variant detection, and biosurveillance. The pipeline accepts paths to raw reads for one or more organisms and creates reports in the form of an interactive HTML document. Significant features include the ability to analyze unidentified eukaryotic and prokaryotic samples, creation of reports for multiple user-defined groupings of samples, automated discovery and downloading of reference assemblies from NCBI RefSeq, and rapid initial identification based on k-mer sketches followed by a more robust multi gene phylogeny and SNP-based phylogeny.
has_samplesheet: true
input: samplesheet (sample_id, name, description, path, path_2, ncbi_accession, ncbi_query, ncbi_query_max, sequence_type, report_group_ids, color_by, ploidy, enabled, ref_group_ids)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["FastQC", "MultiQC"]
---
# pathogensurveillance

nf-core/pathogensurveillance is a population genomics pipeline for pathogen identification, variant detection, and biosurveillance. The pipeline accepts paths to raw reads for one or more organisms and creates reports in the form of an interactive HTML document. Significant features include the ability to analyze unidentified eukaryotic and prokaryotic samples, creation of reports for multiple user-defined groupings of samples, automated discovery and downloading of reference assemblies from NCBI RefSeq, and rapid initial identification based on k-mer sketches followed by a more robust multi gene phylogeny and SNP-based phylogeny.

## Run it
```bash
git submodule update --init pipelines/pathogensurveillance/upstream   # first time only
nfclaw run pathogensurveillance --input samplesheet.csv --outdir results -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/pathogensurveillance/upstream -profile docker --input samplesheet.csv --outdir results
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions pathogensurveillance` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show pathogensurveillance --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show pathogensurveillance --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `sample_id` | string | no |  |  |
| `name` | string | no |  |  |
| `description` | string | no |  |  |
| `path` | string | no |  | matches `^([\S\s]*\/)?[^\s\/]+\.f(ast)?q\.gz$` |
| `path_2` | string | no |  | matches `^([\S\s]*\/)?[^\s\/]+\.f(ast)?q\.gz$` |
| `ncbi_accession` | string | no |  | matches `^[A-Z]{3,6}[0-9]+$` |
| `ncbi_query` | string | no |  |  |
| `ncbi_query_max` | integer | no |  | ≥ 1 |
| `sequence_type` | string | no |  | matches `(?i)illumina\|nanopore\|pacbio\|bgiseq` |
| `report_group_ids` | string | no |  | matches `^[a-zA-Z0-9_ -]+(?:;[a-zA-Z0-9_ -]+)*$` |
| `color_by` | string | no |  |  |
| `ploidy` | integer | no |  | ≥ 1 |
| `enabled` | boolean | no |  |  |
| `ref_group_ids` | string | no |  |  |

`--input` must match `^\S+\.[ct]sv$`.

The samplesheet is a CSV with this header; fill each value per the table above and `reference.md` (no example value is invented here):
```csv
sample_id,name,description,path,path_2,ncbi_accession,ncbi_query,ncbi_query_max,sequence_type,report_group_ids,color_by,ploidy,enabled,ref_group_ids
```

**From data files.** `--input` may also be the data files — a directory (searched recursively), a quoted glob, or files (`--input` once per file) — from which nfclaw writes this samplesheet: `sample_id` from file names; `path`/`path_2` from FastQ files (mates paired by `_R1`/`_R2`, or by `_1`/`_2` when their read names show they are mates). Optional columns left out take their schema defaults in the pipeline: `ncbi_query_max` = `10`, `report_group_ids` = `_no_group_defined_`, `ploidy` = `1`, `enabled` = `true` — set them with `--sheet-set` where your design differs. Set other columns with `--sheet-set COLUMN=VALUE`. Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file path) |  |  | matches `^\S+\.[ct]sv$` | Path to comma/tab-separated file containing information about samples. |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage if running on Cloud infrastructure. |

## Secrets
This release reads Nextflow secrets: `NCBI_API_KEY` (in `conf/modules.config`, `modules/local/initial_classification/main.nf` and 1 more files). Set each one a run needs with `nextflow secrets set NAME VALUE` before launching; a secret that is not set reaches its tasks as an empty value (Nextflow warns that the variable evaluates to an empty value), and a task that needs it then fails. Secrets are not written to nfclaw's provenance.

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, required, hidden, allowed values, constraints, default and description. Use it as the source of truth; do not guess flags. It uses nfclaw's hyphenated flags; raw Nextflow requires the exact schema spelling (usually underscores). nfclaw checks explicit parameters before launch; the pinned pipeline's validation handles conditional and complex constraints at runtime. It is organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Analysis parameters** (`analysis_parameters`) — 19 parameters
- **Generic options** (`generic_options`) — 17 parameters
- **Input/output options** (`input_output_options`) — 11 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters

Upstream usage: https://github.com/nf-core/pathogensurveillance/blob/1.1.0/docs/usage.md

## Resources
Resource requests follow the pipeline's configs and selected profiles. nf-core's resource labels often assume a server — a single step can request far more memory than a workstation has, and retry rules can increase requests. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run pathogensurveillance --input samplesheet.csv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=25.04.6'`.

To pin this release's declared minimum engine — useful when a newer Nextflow has incompatible config parsing:
```bash
nfclaw run pathogensurveillance ... --nxf-ver 25.04.6
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/pathogensurveillance/blob/1.1.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: FastQC, MultiQC.

Full list with references: https://github.com/nf-core/pathogensurveillance/blob/1.1.0/CITATIONS.md

## Demo
```bash
nfclaw run pathogensurveillance --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

<!-- Generated from nf-core/pathogensurveillance@13547eaa7345dab4ac97db49775ae8284af4113d. Do not edit by hand. -->
