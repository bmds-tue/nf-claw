---
name: hadge
pipeline: nf-core/hadge
version: 1.0.0
commit: 921d3780498d0d6f4da0d3ea8c8416d214a3ff42
description: Comprehensive pipeline for donor demultiplexing in single cell
summary: nf-core/hadge (hashing deconvolution combined with genotype information) is a bioinformatics pipeline that combines 11 methods to perform both hashing- and genotype-based deconvolution on single cell multiplexing data. It takes a samplesheet with count matrices, BAM and VCF files as input, performs deconvolution with every method, joins all results and finally recovers previously discarded cells by combining the best performing methods (donor matching).
has_samplesheet: true
input: samplesheet (sample, rna_matrix, hto_matrix, bam, barcodes, n_samples, vcf)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["Demuxlet", "Freemuxlet", "Souporcell", "Vireo", "BFF", "Demuxem", "GMM-Demux", "HashedDrops", "Hashsolo", "HTODemux", "Multiseq", "Cellsnp-lite", "MultiQC"]
---
# hadge

nf-core/hadge (hashing deconvolution combined with genotype information) is a bioinformatics pipeline that combines 11 methods to perform both hashing- and genotype-based deconvolution on single cell multiplexing data. It takes a samplesheet with count matrices, BAM and VCF files as input, performs deconvolution with every method, joins all results and finally recovers previously discarded cells by combining the best performing methods (donor matching).

## Run it
```bash
git submodule update --init pipelines/hadge/upstream   # first time only
nfclaw run hadge --input samplesheet.csv --outdir results -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/hadge/upstream -profile docker --input samplesheet.csv --outdir results
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions hadge` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show hadge --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show hadge --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `sample` | string | yes |  | matches ^\S+$ |
| `rna_matrix` | string (file or directory path) | no |  | matches ^\S+$ |
| `hto_matrix` | string (file or directory path) | no |  | matches ^\S+$ |
| `bam` | string (file path) | no |  | matches ^\S+\.bam$ |
| `barcodes` | string (file path) | no |  | matches ^\S+\.tsv$ |
| `n_samples` | integer | no |  | ≥ 1 |
| `vcf` | string (file path) | no |  | matches ^\S+\.vcf$ |

`--input` must match `^\S+\.csv$`.

The samplesheet is a CSV with this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
sample
```

Any of the optional columns above may be appended to the header when your data needs them: `rna_matrix`, `hto_matrix`, `bam`, `barcodes`, `n_samples`, `vcf`.

**From data files.** `--input` may also be the data files — a directory (searched recursively), a quoted glob, or files (`--input` once per file) — from which nfclaw writes this samplesheet: `sample` from file names; `bam`, `barcodes`, `vcf` from files matching their patterns, by sample name. Set other columns with `--sheet-set COLUMN=VALUE`. Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file path) |  |  | matches ^\S+\.csv$ | Path to comma-separated file containing information about the samples in the experiment. |
| `--mode` | string | rescue | `genetic`, `hashing`, `rescue`, `donor_match` |  | Mode of the pipeline. |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## Reference genome
No reference genome is set by default: supply your own reference. The schema declares AWS iGenomes at `s3://ngi-igenomes/igenomes/`; selecting `--genome <id>` uses the paths in the pipeline's reference configuration. Access to that remote source is required. To supply your own reference, use e.g. `--fasta`; the `reference_genome_options` group in [reference.md](reference.md) lists every reference option. Set `--igenomes-ignore true` to disable the lookup entirely. Confirm the selected reference's paths and source in the pinned `upstream/nextflow.config` and `upstream/conf/` before running.

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, default, allowed values and constraints — organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **BFF options** (`bff_options`) — 12 parameters
- **CellSNP-lite options** (`cellsnp_options`) — 10 parameters
- **demuxEM options** (`demuxem_options`) — 7 parameters
- **Demuxlet options** (`demuxlet_options`) — 8 parameters
- **Donor match options** (`donor_match_options`) — 11 parameters
- **DSC-Pileup options** (`dsc_pileup_options`) — 10 parameters
- **Freemuxlet options** (`freemuxlet_options`) — 8 parameters
- **Generic options** (`generic_options`) — 15 parameters
- **GMM-Demux options** (`gmmdemux_options`) — 9 parameters
- **HashedDrops options** (`hasheddrops_options`) — 20 parameters
- **Hashsolo options** (`hashsolo_options`) — 6 parameters
- **HTODemux options** (`htodemux_options`) — 7 parameters
- **HTODemux visualization options** (`htodemux_visualization_options`) — 17 parameters
- **Input/output options** (`input_output_options`) — 10 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **MultiSeqDemux options** (`multiseqdemux_options`) — 7 parameters
- **Preprocessing options** (`preprocessing_options`) — 7 parameters
- **Reference genome options** (`reference_genome_options`) — 4 parameters
- **Souporcell options** (`souporcell_options`) — 10 parameters
- **Vireo options** (`vireo_options`) — 11 parameters

## Resources
A real (non-`--demo`) run requests the resources the pipeline's `conf/base.config` asks for, which are sized for a server — a single step can request far more memory than a workstation has, and Nextflow retries a failed step with more still. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run hadge --input samplesheet.csv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=25.10.4'`.

To run the engine this release targets — worth doing if a newer Nextflow emits config-parser warnings the release never saw:
```bash
nfclaw run hadge ... --nxf-ver 25.10.4
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/hadge/blob/1.0.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: Demuxlet, Freemuxlet, Souporcell, Vireo, BFF, Demuxem, GMM-Demux, HashedDrops, Hashsolo, HTODemux, Multiseq, Cellsnp-lite, MultiQC.

Full list with references: https://github.com/nf-core/hadge/blob/1.0.0/CITATIONS.md

## Demo
```bash
nfclaw run hadge --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

## Full reference
Every parameter — name, type, required, hidden, allowed values, constraints, default and description — is in [reference.md](reference.md). Use it as the source of truth; do not guess flags. Nextflow's nf-schema validates every parameter against this schema at runtime, so an unknown or invalid value fails fast. Upstream usage: https://github.com/nf-core/hadge/blob/1.0.0/docs/usage.md

<!-- Generated from nf-core/hadge@921d3780498d0d6f4da0d3ea8c8416d214a3ff42. Do not edit by hand. -->
