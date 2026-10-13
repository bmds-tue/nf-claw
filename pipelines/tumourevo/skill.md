---
name: tumourevo
pipeline: nf-core/tumourevo
version: 1.0.0
commit: 180ae5447d0eb0214f650b6fcf7dabed0c77b5a2
description: Analysis pipeline to model tumour clonal evolution from WGS data (driver annotation, quality control of copy number calls, subclonal and mutational signature deconvolution)
summary: nf-core/tumourevo is a bioinformatics pipeline to model tumour evolution from whole-genome sequencing (WGS) data. The pipeline performs state-of-the-art downstream analysis of variant and copy-number calls from tumour-normal matched sequencing assays, reconstructing the evolutionary processes leading to the observed tumour genome. This analysis can be done at the level of single samples, multiple samples from the same patient (multi-region/longitudinal assays), and of multiple patients from distinct cohorts.
has_samplesheet: true
input: samplesheet (dataset, patient, tumour_sample, normal_sample, cancer_type, cna_caller, vcf, tbi, tumour_alignment, tumour_alignment_index, cna_segments, cna_extra)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["BCFTools", "CNAqc", "CTREE", "EnsemblVEP", "mobster", "PyClone-VI", "SigProfiler", "SparseSignatures", "Tabix", "TINC", "VIBER"]
---
# tumourevo

nf-core/tumourevo is a bioinformatics pipeline to model tumour evolution from whole-genome sequencing (WGS) data. The pipeline performs state-of-the-art downstream analysis of variant and copy-number calls from tumour-normal matched sequencing assays, reconstructing the evolutionary processes leading to the observed tumour genome. This analysis can be done at the level of single samples, multiple samples from the same patient (multi-region/longitudinal assays), and of multiple patients from distinct cohorts.

## Run it
```bash
git submodule update --init pipelines/tumourevo/upstream   # first time only
nfclaw run tumourevo --input samplesheet.csv --outdir results -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/tumourevo/upstream -profile docker --input samplesheet.csv --outdir results
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions tumourevo` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show tumourevo --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show tumourevo --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `dataset` | string or integer | yes |  |  |
| `patient` | string or integer | yes |  |  |
| `tumour_sample` | string or integer | yes |  |  |
| `normal_sample` | string or integer | no |  |  |
| `cancer_type` | string | no |  |  |
| `cna_caller` | string | yes |  |  |
| `vcf` | string (file path) | yes |  |  |
| `tbi` | string (file path) | yes |  |  |
| `tumour_alignment` | string (file path) | no |  |  |
| `tumour_alignment_index` | string (file path) | no |  |  |
| `cna_segments` | string (file path) | yes |  |  |
| `cna_extra` | string (file path) | no |  |  |

`--input` must match `^\S+\.csv$`.

The samplesheet is a CSV with this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
dataset,patient,tumour_sample,cna_caller,vcf,tbi,cna_segments
```

Any of the optional columns above may be appended to the header when your data needs them: `normal_sample`, `cancer_type`, `tumour_alignment`, `tumour_alignment_index`, `cna_extra`.

**From data files.** `--input` may also be the data files — a directory (searched recursively), a quoted glob, or files (`--input` once per file) — from which nfclaw writes this samplesheet: `vcf`, `tbi`, `tumour_alignment`, `tumour_alignment_index` from files matching their patterns, by sample name. Optional columns left out take their schema defaults in the pipeline: `cancer_type` = `PANCANCER` — set them with `--sheet-set` where your design differs. Set the required columns no file determines with `--sheet-set COLUMN=VALUE` (a constant or a `{sample}`/`{lane}` template): `dataset` (string or integer); `patient` (string or integer); `tumour_sample` (string or integer); `cna_caller` (string); `cna_segments` (string). Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file path) |  |  | matches ^\S+\.csv$ | Path to comma-separated file containing information about the samples in the experiment. |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--genome` | string | GRCh38 | `GRCh38`, `GRCh37` |  | Reference genome name. |

## Reference genome
**This release resolves a reference genome remotely by default.** `--genome` defaults to `GRCh38`; the schema declares AWS iGenomes at `s3://ngi-igenomes/igenomes/`. The pinned configuration gives that key the FASTA `${params.igenomes_base}/Homo_sapiens/NCBI/GRCh38/Sequence/WholeGenomeFasta/genome.fa`. Resolving references through that default needs access to this source. For a self-contained run, pass your own reference instead (e.g. `--fasta`; the `main_options` group in [reference.md](reference.md) lists every reference option). Set `--igenomes-ignore true` to disable the lookup entirely. Confirm the selected reference's paths and source in the pinned `upstream/nextflow.config` and `upstream/conf/` before running.

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, default, allowed values and constraints — organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **CNAqc** (`cnaqc`) — 5 parameters
- **Driver Annotation** (`driver_annotation`) — 1 parameter
- **Generic options** (`generic_options`) — 4 parameters
- **Input/output options** (`input_output_options`) — 2 parameters
- **joinCNAqc** (`joincnaqc`) — 1 parameter
- **Main options** (`main_options`) — 6 parameters
- **mobster** (`mobster`) — 5 parameters
- **Other** (`other`) — 18 parameters
- **pyClone-VI** (`pyclone_vi`) — 4 parameters
- **SigProfiler** (`sigprofiler`) — 11 parameters
- **SparseSignature** (`sparsesignature`) — 12 parameters
- **TINC** (`tinc`) — 1 parameter
- **Variant Annotation** (`variant_annotation`) — 6 parameters
- **VCF2CNAqc** (`vcf2cnaqc`) — 1 parameter
- **viber** (`viber`) — 5 parameters

## Resources
A real (non-`--demo`) run requests the resources the pipeline's `conf/base.config` asks for, which are sized for a server — a single step can request far more memory than a workstation has, and Nextflow retries a failed step with more still. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run tumourevo --input samplesheet.csv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=25.10.4'`.

To run the engine this release targets — worth doing if a newer Nextflow emits config-parser warnings the release never saw:
```bash
nfclaw run tumourevo ... --nxf-ver 25.10.4
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/tumourevo/blob/1.0.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: BCFTools, CNAqc, CTREE, EnsemblVEP, mobster, PyClone-VI, SigProfiler, SparseSignatures, Tabix, TINC, VIBER.

Full list with references: https://github.com/nf-core/tumourevo/blob/1.0.0/CITATIONS.md

## Demo
```bash
nfclaw run tumourevo --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

## Full reference
Every parameter — name, type, required, hidden, allowed values, constraints, default and description — is in [reference.md](reference.md). Use it as the source of truth; do not guess flags. Nextflow's nf-schema validates every parameter against this schema at runtime, so an unknown or invalid value fails fast. Upstream usage: https://github.com/nf-core/tumourevo/blob/1.0.0/docs/usage.md

<!-- Generated from nf-core/tumourevo@180ae5447d0eb0214f650b6fcf7dabed0c77b5a2. Do not edit by hand. -->
