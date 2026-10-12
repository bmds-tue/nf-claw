---
name: mhcquant
pipeline: nf-core/mhcquant
version: 3.3.0
commit: a4b6d51803af0fbde5acd8e9802df76280ba8306
description: Identify and quantify peptides from mass spectrometry raw data
summary: nfcore/mhcquant is a best-practice bioinformatics pipeline to process data-dependent acquisition (DDA) immunopeptidomics data. This involves mass spectrometry-based identification and quantification of immunopeptides presented on major histocompatibility complex (MHC) molecules which mediate T cell immunosurveillance. Immunopeptidomics has central implications for clinical research, in the context of T cell-centric immunotherapies.
has_samplesheet: true
input: samplesheet (ID, Sample, Condition, ReplicateFileName, Fasta, SearchPreset)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["OpenMS", "ThermoRawFileParser", "tdf2mzml", "Comet", "DeepLC", "MS²PIP", "Ionmob", "IM2Deep", "MS²Rescore", "TIMS²Rescore", "Percolator", "Mokapot", "EasyPQP", "Epicore", "pridepy", "sdrf-pipelines", "MultiQC"]
---
# mhcquant

nfcore/mhcquant is a best-practice bioinformatics pipeline to process data-dependent acquisition (DDA) immunopeptidomics data. This involves mass spectrometry-based identification and quantification of immunopeptides presented on major histocompatibility complex (MHC) molecules which mediate T cell immunosurveillance. Immunopeptidomics has central implications for clinical research, in the context of T cell-centric immunotherapies.

## Run it
```bash
git submodule update --init pipelines/mhcquant/upstream   # first time only
nfclaw run mhcquant --input samplesheet.tsv --outdir results -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/mhcquant/upstream -profile docker --input samplesheet.tsv --outdir results
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions mhcquant` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show mhcquant --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show mhcquant --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `ID` | integer | yes |  |  |
| `Sample` | string or integer | yes |  |  |
| `Condition` | string or integer | yes |  |  |
| `ReplicateFileName` | string (file or directory path) | yes |  | matches ^\S+\.(raw\|RAW\|mzML\|mzML.gz\|d\|d.tar\|d.tar.gz\|d.zip)$ |
| `Fasta` | string (file or directory path) | no |  | matches ^\S+\.(fasta\|fa\|fas\|fna\|faa\|ffn)$ |
| `SearchPreset` | string | no |  | matches ^[a-zA-Z0-9_]+$ |

`--input` must match `^(PXD\d{6,}|\S+\.sdrf\.tsv|\S+\.tsv)$`.

The samplesheet is a TSV with this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```tsv
ID	Sample	Condition	ReplicateFileName
```

Any of the optional columns above may be appended to the header when your data needs them: `Fasta`, `SearchPreset`.

**From data files.** `--input` may also be the data files — a directory (searched recursively), a glob or several files — from which nfclaw writes this samplesheet: `Sample` from file names; `ReplicateFileName`, `Fasta` from files matching their patterns, by sample name. Set the required columns no file determines with `--sheet-set COLUMN=VALUE` (a constant or a `{sample}`/`{lane}` template): `ID` (integer); `Condition` (string or integer). Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string |  |  | matches ^(PXD\d{6,}\|\S+\.sdrf\.tsv\|\S+\.tsv)$ | Input: samplesheet TSV, SDRF file (.sdrf.tsv), or PRIDE accession (PXD...) |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, default, allowed values and constraints — organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Database Options** (`database_options`) — 2 parameters
- **Epicore Options** (`epicore_options`) — 4 parameters
- **Generic options** (`generic_options`) — 15 parameters
- **Input/output options** (`input_output_options`) — 4 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **Post Processing** (`post_processing`) — 4 parameters
- **Spectrum preprocessing** (`preprocessing`) — 3 parameters
- **Quantification Options** (`quantification_options`) — 9 parameters
- **Rescoring settings** (`rescoring_settings`) — 9 parameters
- **Database Search Settings** (`search_settings`) — 22 parameters

## Resources
A real (non-`--demo`) run requests the resources the pipeline's `conf/base.config` asks for, which are sized for a server — a single step can request far more memory than a workstation has, and Nextflow retries a failed step with more still. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run mhcquant --input samplesheet.tsv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=25.10.4'`.

To run the engine this release targets — worth doing if a newer Nextflow emits config-parser warnings the release never saw:
```bash
nfclaw run mhcquant ... --nxf-ver 25.10.4
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/mhcquant/blob/3.3.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: OpenMS, ThermoRawFileParser, tdf2mzml, Comet, DeepLC, MS²PIP, Ionmob, IM2Deep, MS²Rescore, TIMS²Rescore, Percolator, Mokapot, EasyPQP, Epicore, pridepy, sdrf-pipelines, MultiQC.

Full list with references: https://github.com/nf-core/mhcquant/blob/3.3.0/CITATIONS.md

## Demo
```bash
nfclaw run mhcquant --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

## Full reference
Every parameter — name, type, required, hidden, allowed values, constraints, default and description — is in [reference.md](reference.md). Use it as the source of truth; do not guess flags. Nextflow's nf-schema validates every parameter against this schema at runtime, so an unknown or invalid value fails fast. Upstream usage: https://github.com/nf-core/mhcquant/blob/3.3.0/docs/usage.md

<!-- Generated from nf-core/mhcquant@a4b6d51803af0fbde5acd8e9802df76280ba8306. Do not edit by hand. -->
