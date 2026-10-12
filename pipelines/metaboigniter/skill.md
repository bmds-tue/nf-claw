---
name: metaboigniter
pipeline: nf-core/metaboigniter
version: 2.0.1
commit: 55d82547604fcae3b6557fe7a3c442b623184f34
description: Pre-processing of mass spectrometry-based metabolomics data
summary: nf-core/metaboigniter is a bioinformatics pipeline that ingests raw mass spectrometry data in mzML format, typically in the form of peak lists and MS2 spectral data, for comprehensive metabolomics analysis. The key stages involve centroiding, feature detection, adduct detection, alignment, and linking, which progressively refine and align the data. The pipeline can also perform requantification to compensate for missing values and leverages MS2Query for compound identification based on MS2 data, outputting a comprehensive list of detected and potentially identified metabolites.
has_samplesheet: true
input: samplesheet (sample, type, level, msfile)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["OpenMS", "SIRIUS", "MS2Query"]
---
# metaboigniter

nf-core/metaboigniter is a bioinformatics pipeline that ingests raw mass spectrometry data in mzML format, typically in the form of peak lists and MS2 spectral data, for comprehensive metabolomics analysis. The key stages involve centroiding, feature detection, adduct detection, alignment, and linking, which progressively refine and align the data. The pipeline can also perform requantification to compensate for missing values and leverages MS2Query for compound identification based on MS2 data, outputting a comprehensive list of detected and potentially identified metabolites.

## Run it
```bash
git submodule update --init pipelines/metaboigniter/upstream   # first time only
nfclaw run metaboigniter --input samplesheet.csv --outdir results -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/metaboigniter/upstream -profile docker --input samplesheet.csv --outdir results
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions metaboigniter` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show metaboigniter --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show metaboigniter --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `sample` | string | yes |  | matches ^\S+$ |
| `type` | string | yes |  | matches ^\S+$ |
| `level` | string | yes | `MS1`, `MS2`, `MS12` |  |
| `msfile` | string (file path) | yes |  | matches ^\S+\.mzML |

`--input` must match `^\S+\.csv$`.

The samplesheet is a CSV with this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
sample,type,level,msfile
```

**From data files.** `--input` may also be the data files — a directory (searched recursively), a glob or several files — from which nfclaw writes this samplesheet: `sample` from file names; `msfile` from files matching their patterns, by sample name. Set the required columns no file determines with `--sheet-set COLUMN=VALUE` (a constant or a `{sample}`/`{lane}` template): `type` (matching ^\S+$); `level` (one of MS1, MS2, MS12). Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file path) |  |  | matches ^\S+\.csv$ | Path to comma-separated file containing information about the samples in the experiment. |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, default, allowed values and constraints — organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Alignment and Linking** (`alignment_and_linking`) — 70 parameters
- **Annotation** (`annotation`) — 16 parameters
- **Generic controls** (`generic_controls`) — 8 parameters
- **Generic options** (`generic_options`) — 15 parameters
- **Input/output options** (`input_output_options`) — 5 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **Mapping and Identification** (`mapping_and_identification`) — 45 parameters
- **Max job request options** (`max_job_request_options`) — 3 parameters
- **Quantification** (`quantification`) — 43 parameters
- **Re-Quantification** (`re_quantification`) — 18 parameters

## Resources
A real (non-`--demo`) run requests the resources the pipeline's `conf/base.config` asks for, which are sized for a server — a single step can request far more memory than a workstation has, and Nextflow retries a failed step with more still. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run metaboigniter --input samplesheet.csv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=23.04.0'`.

To run the engine this release targets — worth doing if a newer Nextflow emits config-parser warnings the release never saw:
```bash
nfclaw run metaboigniter ... --nxf-ver 23.04.0
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

Nextflow 23.04.0 predates `process.resourceLimits` (24.04.0), so `--limit-*` cannot be combined with this pin — nfclaw refuses it rather than run without the ceiling; cap resources with the release's own `--max-cpus`, `--max-memory`, `--max-time` instead.

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/metaboigniter/blob/2.0.1/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: OpenMS, SIRIUS, MS2Query.

Full list with references: https://github.com/nf-core/metaboigniter/blob/2.0.1/CITATIONS.md

## Demo
```bash
nfclaw run metaboigniter --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

## Full reference
Every parameter — name, type, required, hidden, allowed values, constraints, default and description — is in [reference.md](reference.md). Use it as the source of truth; do not guess flags. Nextflow's nf-schema validates every parameter against this schema at runtime, so an unknown or invalid value fails fast. Upstream usage: https://github.com/nf-core/metaboigniter/blob/2.0.1/docs/usage.md

<!-- Generated from nf-core/metaboigniter@55d82547604fcae3b6557fe7a3c442b623184f34. Do not edit by hand. -->
