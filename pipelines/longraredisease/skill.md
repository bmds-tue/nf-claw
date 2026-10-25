---
name: longraredisease
pipeline: nf-core/longraredisease
version: 1.0.0
commit: f40870fcbcf2e9fc29b623b848487789d487ed4a
description: A Nextflow pipeline for rare disease diagnostics from Oxford Nanopore long-read sequencing data. Includes SV, SNV, CNV, and methylation profiling.
summary: nf-core/longraredisease is a specialized bioinformatics pipeline for structural variant (SV) detection and clinical interpretation from long-read sequencing data (Oxford Nanopore and PacBio). Designed for rare disease diagnostics, it delivers high-confidence variant discovery through multi-caller consensus, family-based analysis, and phenotype-driven prioritization.
has_samplesheet: true
input: samplesheet (sample, file_path, hpo_terms, sex, phenotype, family_id, maternal_id, paternal_id)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["FastQC", "MultiQC"]
---
# longraredisease

nf-core/longraredisease is a specialized bioinformatics pipeline for structural variant (SV) detection and clinical interpretation from long-read sequencing data (Oxford Nanopore and PacBio). Designed for rare disease diagnostics, it delivers high-confidence variant discovery through multi-caller consensus, family-based analysis, and phenotype-driven prioritization.

## Run it
```bash
git submodule update --init pipelines/longraredisease/upstream   # first time only
nfclaw run longraredisease --input samplesheet.csv --outdir results --fasta-file <fasta_file> -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/longraredisease/upstream -profile docker --input samplesheet.csv --outdir results --fasta_file <fasta_file>
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions longraredisease` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show longraredisease --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show longraredisease --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `sample` | string | yes |  | matches ^\S+$ |
| `file_path` | string | yes |  |  |
| `hpo_terms` | string | no |  | matches ^HP:\d{7}(;HP:\d{7})*$ |
| `sex` | integer | no | `1`, `2`, `0` |  |
| `phenotype` | integer | no | `1`, `2`, `0`, `-9` |  |
| `family_id` | string | no |  | matches ^\S+$ |
| `maternal_id` | string | no |  | matches ^\S+$ |
| `paternal_id` | string | no |  | matches ^\S+$ |

`--input` must match `^\S+\.csv$`.

The samplesheet is a CSV with this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
sample,file_path
```

Any of the optional columns above may be appended to the header when your data needs them: `hpo_terms`, `sex`, `phenotype`, `family_id`, `maternal_id`, `paternal_id`.

**From data files.** `--input` may also be the data files — a directory (searched recursively), a quoted glob, or files (`--input` once per file) — from which nfclaw writes this samplesheet: `sample` from file names; `file_path` from files matching their patterns, by sample name. Optional columns left out take their schema defaults in the pipeline: `sex` = `0`, `phenotype` = `0`, `family_id` = `unknown`, `maternal_id` = `0`, `paternal_id` = `0` — set them with `--sheet-set` where your design differs. Set other columns with `--sheet-set COLUMN=VALUE`. Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file path) |  |  | matches ^\S+\.csv$ | Path to comma-separated file containing information about the samples in the experiment. |
| `--fasta-file` | string (file path) |  |  | matches ^\S+\.fn?a(sta)?(\.gz)?$ | Path to FASTA genome file. |

## Reference genome
No reference genome is set by default: supply your own reference. The schema declares AWS iGenomes at `s3://ngi-igenomes/igenomes/`; selecting `--genome <id>` uses the paths in the pipeline's reference configuration. Access to that remote source is required. To supply your own reference, use the `reference_genome_options` group in [reference.md](reference.md) lists the reference options. Set `--igenomes-ignore true` to disable the lookup entirely. Confirm the selected reference's paths and source in the pinned `upstream/nextflow.config` and `upstream/conf/` before running.

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, required, hidden, allowed values, constraints, default and description. Use it as the source of truth; do not guess flags. It uses nfclaw's hyphenated flags; raw Nextflow requires the exact schema spelling (usually underscores). nfclaw checks explicit parameters before launch; the pinned pipeline's validation handles conditional and complex constraints at runtime. It is organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **CNV Calling** (`cnv_calling_options`) — 11 parameters
- **Generic options** (`generic_options`) — 16 parameters
- **Input/output options** (`input_output_options`) — 3 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **Output Options** (`output_options`) — 2 parameters
- **Reference genome options** (`reference_genome_options`) — 6 parameters
- **SNV Calling** (`snv_calling_options`) — 10 parameters
- **STR Analysis** (`str_analysis_options`) — 3 parameters
- **SV Annotation with SvAnna** (`sv_annotation_options`) — 3 parameters
- **Structural Variant Calling** (`sv_calling_options`) — 15 parameters
- **Workflow options** (`workflow_options`) — 21 parameters

Upstream usage: https://github.com/nf-core/longraredisease/blob/1.0.0/docs/usage.md

## Resources
Resource requests follow the pipeline's configs and selected profiles. nf-core's resource labels often assume a server — a single step can request far more memory than a workstation has, and retry rules can increase requests. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run longraredisease --input samplesheet.csv --outdir results --fasta-file <fasta_file> -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=25.04.0'`.

To pin this release's declared minimum engine — useful when a newer Nextflow has incompatible config parsing:
```bash
nfclaw run longraredisease ... --nxf-ver 25.04.0
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/longraredisease/blob/1.0.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: FastQC, MultiQC.

Full list with references: https://github.com/nf-core/longraredisease/blob/1.0.0/CITATIONS.md

## Demo
```bash
nfclaw run longraredisease --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

<!-- Generated from nf-core/longraredisease@f40870fcbcf2e9fc29b623b848487789d487ed4a. Do not edit by hand. -->
