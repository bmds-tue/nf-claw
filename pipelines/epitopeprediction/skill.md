---
name: epitopeprediction
pipeline: nf-core/epitopeprediction
version: 3.2.0
commit: e637bc7c49e6e05a09f5207501a142ec68d8570b
description: A fully reproducible and state of the art epitope prediction pipeline.
summary: nf-core/epitopeprediction is a bioinformatics pipeline that predicts which peptides bind to MHC molecules. It accepts three types of input:
has_samplesheet: true
input: samplesheet (sample, alleles, mhc_class, filename, germline_vcf, tumor_sample)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["MultiQC", "BCFtools", "Ensembl VEP", "pVACtools", "MHCflurry", "MHCnuggets", "NetMHC-4.0", "NetMHCpan-4.0", "NetMHCpan-4.1", "NetMHCII-2.3", "NetMHCIIpan-4.0", "MixMHCpred-3.0", "MixMHC2pred-2.0"]
---
# epitopeprediction

nf-core/epitopeprediction is a bioinformatics pipeline that predicts which peptides bind to MHC molecules. It accepts three types of input:

## Run it
```bash
git submodule update --init pipelines/epitopeprediction/upstream   # first time only
nfclaw run epitopeprediction --input samplesheet.csv --outdir results -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/epitopeprediction/upstream -profile docker --input samplesheet.csv --outdir results
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions epitopeprediction` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show epitopeprediction --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show epitopeprediction --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `sample` | integer or string | yes |  |  |
| `alleles` | string | yes |  |  |
| `mhc_class` | string | yes |  | matches ^(I\|II)$ |
| `filename` | string (file path) | yes |  | matches ^\S+\.(vcf\|vcf.gz\|tsv\|fasta\|fa)$ |
| `germline_vcf` | string (file path) | no |  | matches ^\S+\.vcf(\.gz)?$ |
| `tumor_sample` | string | no |  | matches ^\S+$ |

The samplesheet is a CSV with this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
sample,alleles,mhc_class,filename
```

Any of the optional columns above may be appended to the header when your data needs them: `germline_vcf`, `tumor_sample`.

**From data files.** `--input` may also be the data files — a directory (searched recursively), a quoted glob, or files (`--input` once per file) — from which nfclaw writes this samplesheet: `sample` from file names; `filename`, `germline_vcf` from files matching their patterns, by sample name. Set the required columns no file determines with `--sheet-set COLUMN=VALUE` (a constant or a `{sample}`/`{lane}` template): `alleles` (string); `mhc_class` (matching ^(I|II)$). Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file path) |  |  |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, required, hidden, allowed values, constraints, default and description. Use it as the source of truth; do not guess flags. It uses nfclaw's hyphenated flags; raw Nextflow requires the exact schema spelling (usually underscores). nfclaw checks explicit parameters before launch; the pinned pipeline's validation handles conditional and complex constraints at runtime. It is organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **External software** (`external_software`) — 4 parameters
- **Generic options** (`generic_options`) — 15 parameters
- **Input/output options** (`input_output_options`) — 4 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **Peptide prediction options** (`peptide_prediction_options`) — 12 parameters
- **Reference options** (`reference_options`) — 6 parameters
- **Run optimisation** (`run_optimisation`) — 2 parameters

Upstream usage: https://github.com/nf-core/epitopeprediction/blob/3.2.0/docs/usage.md

## Resources
Resource requests follow the pipeline's configs and selected profiles. nf-core's resource labels often assume a server — a single step can request far more memory than a workstation has, and retry rules can increase requests. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run epitopeprediction --input samplesheet.csv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=25.10.4'`.

To pin this release's declared minimum engine — useful when a newer Nextflow has incompatible config parsing:
```bash
nfclaw run epitopeprediction ... --nxf-ver 25.10.4
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/epitopeprediction/blob/3.2.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: MultiQC, BCFtools, Ensembl VEP, pVACtools, MHCflurry, MHCnuggets, NetMHC-4.0, NetMHCpan-4.0, NetMHCpan-4.1, NetMHCII-2.3, NetMHCIIpan-4.0, MixMHCpred-3.0, MixMHC2pred-2.0.

Full list with references: https://github.com/nf-core/epitopeprediction/blob/3.2.0/CITATIONS.md

## Demo
```bash
nfclaw run epitopeprediction --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

<!-- Generated from nf-core/epitopeprediction@e637bc7c49e6e05a09f5207501a142ec68d8570b. Do not edit by hand. -->
