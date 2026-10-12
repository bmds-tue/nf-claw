---
name: mag
pipeline: nf-core/mag
version: 5.5.0
commit: 56abab5b023ce953c9c43fe21090d156ad0e18af
description: Assembly, binning and annotation of metagenomes
summary: nf-core/mag is a bioinformatics best-practice analysis pipeline for assembly, binning and annotation of metagenomes.
has_samplesheet: true
input: samplesheet (sample, run, group, short_reads_1, short_reads_2, short_reads_platform, long_reads, long_reads_platform)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["AdapterRemoval2", "ALE", "BBnorm/BBTools", "BCFtools", "Bowtie2", "BUSCO", "CAT", "CheckM", "CheckM2", "Chopper", "COMEBin", "CONCOCT", "MetaBinner", "SemiBin2", "DAS Tool", "FastP", "FastQC", "Filtlong", "Flye", "Freebayes", "geNomad", "GTDB-Tk", "GUNC", "BIgMAG", "MaxBin2", "MEGAHIT", "MetaBAT2", "MetaEuk", "metaMDBG", "minimap2", "MMseqs2", "MultiQC", "NanoLyse", "NanoPlot", "Nanoq", "Porechop", "Porechop-abi", "Prodigal", "Prokka", "PyDamage", "pypolca", "SAMtools", "Seqtk", "SPAdes", "Tiara", "Trimmomatic"]
---
# mag

nf-core/mag is a bioinformatics best-practice analysis pipeline for assembly, binning and annotation of metagenomes.

## Run it
```bash
git submodule update --init pipelines/mag/upstream   # first time only
nfclaw run mag --input samplesheet.csv --outdir results -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/mag/upstream -profile docker --input samplesheet.csv --outdir results
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions mag` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show mag --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show mag --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `sample` | string | yes |  | matches ^\S+$ |
| `run` | string or integer | no |  | matches ^\S+$ |
| `group` | string or integer | yes |  | matches ^\S+$ |
| `short_reads_1` | string (file path) | no |  | matches ^\S+\.f(ast)?q\.gz$ |
| `short_reads_2` | string (file path) | no |  | matches ^\S+\.f(ast)?q\.gz$ |
| `short_reads_platform` | string | no | `ILLUMINA`, `BGISEQ`, `LS454`, `ION_TORRENT`, `DNBSEQ`, `ELEMENT`, `ULTIMA`, `VELA_DIAGNOSTICS`, `GENAPSYS`, `GENEMIND`, `TAPESTRI` |  |
| `long_reads` | string (file path) | no |  | matches ^\S+\.f(ast)?q\.gz$ |
| `long_reads_platform` | string | no | `OXFORD_NANOPORE`, `OXFORD_NANOPORE_HQ`, `PACBIO_CLR`, `PACBIO_HIFI` |  |

`--input` must match `^\S+\.csv$`.

Additional row validation rules from the schema:
- When `short_reads_2` is set, also provide `short_reads_1`.
- When `short_reads_1` is set, also provide `short_reads_platform`.
- When `long_reads` is set, also provide `long_reads_platform`.

The samplesheet is a CSV with this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
sample,group
```

Any of the optional columns above may be appended to the header when your data needs them: `run`, `short_reads_1`, `short_reads_2`, `short_reads_platform`, `long_reads`, `long_reads_platform`.

**From data files.** `--input` may also be the data files — a directory (searched recursively), a glob or several files — from which nfclaw writes this samplesheet once you choose the read columns: the samplesheet takes reads in several column groups (short_reads_1 + short_reads_2; long_reads) and file names cannot tell which yours belong in; leave the groups you do not use empty, e.g. --sheet-set long_reads=. Set the required columns no file determines with `--sheet-set COLUMN=VALUE`. Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file path) |  |  | matches ^\S+\.csv$ | CSV samplesheet file containing information about the samples in the experiment. |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, default, allowed values and constraints — organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Ancient DNA assembly** (`ancient_dna_assembly`) — 9 parameters
- **Assembly options** (`assembly_options`) — 13 parameters
- **Bin quality check options** (`bin_quality_check_options`) — 23 parameters
- **Binning options** (`binning_options`) — 28 parameters
- **Gene prediction and annotation options** (`gene_prediction_and_annotation_options`) — 9 parameters
- **Generic options** (`generic_options`) — 15 parameters
- **Input/output options** (`input_output_options`) — 6 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **Quality control for long reads options** (`quality_control_for_long_reads_options`) — 15 parameters
- **Quality control for short reads options** (`quality_control_for_short_reads_options`) — 27 parameters
- **Reference genome options** (`reference_genome_options`) — 2 parameters
- **Reproducibility options** (`reproducibility_options`) — 4 parameters
- **Taxonomic profiling options** (`taxonomic_profiling_options`) — 18 parameters
- **Virus identification options** (`virus_identification_options`) — 4 parameters

## Resources
A real (non-`--demo`) run requests the resources the pipeline's `conf/base.config` asks for, which are sized for a server — a single step can request far more memory than a workstation has, and Nextflow retries a failed step with more still. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run mag --input samplesheet.csv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=26.04.0'`.

To run the engine this release targets — worth doing if a newer Nextflow emits config-parser warnings the release never saw:
```bash
nfclaw run mag ... --nxf-ver 26.04.0
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/mag/blob/5.5.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Chaining
Run mag as one stage of a chain: `nfclaw chain run spec.json --outdir DIR` starts each stage only after the one before it succeeded, and prepares its inputs from that stage's outputs. The rules live in `handoffs/` (format and spec in [docs/chaining.md](../../docs/chaining.md)); list them with `nfclaw chain edges mag`.

Fed by:
- `detaxizer` — detaxizer, with --generate-downstream-samplesheets, writes downstream_samplesheets/mag-pe.csv for its filtered paired-end reads, in the column layout of mag 3.x; each sample gets its own group and the read platforms mag 5 requires (short reads ILLUMINA, long reads OXFORD_NANOPORE, as detaxizer labels them for taxprofiler). Different samples are not pooled for binning or assembly; use an inline handoff to supply study-specific pooling groups.
- `fetchngs` — fetchngs writes a mag samplesheet whose read columns predate mag's short_reads_1/short_reads_2; the columns are renamed, each sample gets its own group, and each run keeps its own run id. Different samples are not pooled for binning or assembly; use an inline handoff to supply study-specific pooling groups.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: AdapterRemoval2, ALE, BBnorm/BBTools, BCFtools, Bowtie2, BUSCO, CAT, CheckM, CheckM2, Chopper, COMEBin, CONCOCT, MetaBinner, SemiBin2, DAS Tool, FastP, FastQC, Filtlong, Flye, Freebayes, geNomad, GTDB-Tk, GUNC, BIgMAG, MaxBin2, MEGAHIT, MetaBAT2, MetaEuk, metaMDBG, minimap2, MMseqs2, MultiQC, NanoLyse, NanoPlot, Nanoq, Porechop, Porechop-abi, Prodigal, Prokka, PyDamage, pypolca, SAMtools, Seqtk, SPAdes, Tiara, Trimmomatic.

Full list with references: https://github.com/nf-core/mag/blob/5.5.0/CITATIONS.md

## Demo
```bash
nfclaw run mag --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

## Full reference
Every parameter — name, type, required, hidden, allowed values, constraints, default and description — is in [reference.md](reference.md). Use it as the source of truth; do not guess flags. Nextflow's nf-schema validates every parameter against this schema at runtime, so an unknown or invalid value fails fast. Upstream usage: https://github.com/nf-core/mag/blob/5.5.0/docs/usage.md

<!-- Generated from nf-core/mag@56abab5b023ce953c9c43fe21090d156ad0e18af. Do not edit by hand. -->
