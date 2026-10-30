---
name: variantprioritization
pipeline: nf-core/variantprioritization
version: 1.0.0
commit: 8ba629c53dbdb65057c85a3b0a76a7eb2e8688ef
description: pipeline for the functional annotation and translation of somatic SNVs/InDels and copy number abberations for precision cancer medicine
summary: nf-core/variantprioritization is a bioinformatics analysis pipeline for the functional annotation and translation of somatic SNVs/InDels and copy number abberations for precision cancer medicine using Personal Cancer Genome Reporter (PCGR). nf-core/variantprioritization offers germline SNVs/INDELS intepretation and annotation using Cancer Predisposition Sequencing Reporter (CPSR).
has_samplesheet: true
input: samplesheet (patient, status, sample, vcf, cna)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["BCFTools", "MultiQC", "PCGR", "Tabix"]
---
# variantprioritization

nf-core/variantprioritization is a bioinformatics analysis pipeline for the functional annotation and translation of somatic SNVs/InDels and copy number abberations for precision cancer medicine using Personal Cancer Genome Reporter (PCGR). nf-core/variantprioritization offers germline SNVs/INDELS intepretation and annotation using Cancer Predisposition Sequencing Reporter (CPSR).

## Run it
```bash
git submodule update --init pipelines/variantprioritization/upstream   # first time only
nfclaw run variantprioritization --input samplesheet.csv --outdir results -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/variantprioritization/upstream -profile docker --input samplesheet.csv --outdir results
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions variantprioritization` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show variantprioritization --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show variantprioritization --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `patient` | string | yes |  | matches `^\S+$` |
| `status` | integer | yes | `0`, `1` |  |
| `sample` | string | yes |  | matches `^\S+$` |
| `vcf` | string (file path) | yes |  | matches `^\S+\.vcf(\.gz)?$` |
| `cna` | string (file path) | no |  | matches `^\S+\.(cns\|txt)$` |

`--input` must match `^\S+\.csv$`.

The samplesheet is a CSV with this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
patient,status,sample,vcf
```

Any of the optional columns above may be appended to the header when your data needs them: `cna`.

**From data files.** `--input` may also be the data files — a directory (searched recursively), a quoted glob, or files (`--input` once per file) — from which nfclaw writes this samplesheet: `sample` from file names; `vcf`, `cna` from files matching their patterns, by sample name. Set the required columns no file determines with `--sheet-set COLUMN=VALUE` (a constant or a `{sample}`/`{lane}` template): `patient` (matching ^\S+$); `status` (one of 0, 1). Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file path) |  |  | matches `^\S+\.csv$` | Path to comma-separated file containing information about the samples in the experiment. |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## Reference genome
No reference genome is set by default: supply your own reference. The schema declares AWS iGenomes at `s3://ngi-igenomes/igenomes/`; selecting `--genome <id>` uses the paths in the pipeline's reference configuration. Access to that remote source is required. To supply your own reference, use the `reference_options` group in [reference.md](reference.md) lists the reference options. Set `--igenomes-ignore true` to disable the lookup entirely. Confirm the selected reference's paths and source in the pinned `upstream/nextflow.config` and `upstream/conf/` before running.

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, required, hidden, allowed values, constraints, default and description. Use it as the source of truth; do not guess flags. It uses nfclaw's hyphenated flags; raw Nextflow requires the exact schema spelling (usually underscores). nfclaw checks explicit parameters before launch; the pinned pipeline's validation handles conditional and complex constraints at runtime. It is organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **CPSR options** (`cpsr_options`) — 13 parameters
- **Generic options** (`generic_options`) — 17 parameters
- **Input/output options** (`input_output_options`) — 4 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **PCGR options** (`pcgr_options`) — 33 parameters
- **PCGR tumor-only options** (`pcgr_tumoronly_options`) — 16 parameters
- **Reference options** (`reference_options`) — 9 parameters
- **Variant filtering options** (`variantfiltering_options`) — 8 parameters
- **VEP options** (`vep_params_options`) — 5 parameters

Upstream usage: https://github.com/nf-core/variantprioritization/blob/1.0.0/docs/usage.md

## Resources
Resource requests follow the pipeline's configs and selected profiles. nf-core's resource labels often assume a server — a single step can request far more memory than a workstation has, and retry rules can increase requests. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run variantprioritization --input samplesheet.csv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=25.10.0'`.

To pin this release's declared minimum engine — useful when a newer Nextflow has incompatible config parsing:
```bash
nfclaw run variantprioritization ... --nxf-ver 25.10.0
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/variantprioritization/blob/1.0.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: BCFTools, MultiQC, PCGR, Tabix.

Full list with references: https://github.com/nf-core/variantprioritization/blob/1.0.0/CITATIONS.md

## Demo
```bash
nfclaw run variantprioritization --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

<!-- Generated from nf-core/variantprioritization@8ba629c53dbdb65057c85a3b0a76a7eb2e8688ef. Do not edit by hand. -->
