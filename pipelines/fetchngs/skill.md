---
name: fetchngs
pipeline: nf-core/fetchngs
version: 1.13.0
commit: 955c892d80927cee633765e6e390f9cc6b7235c9
description: Pipeline to fetch metadata and raw FastQ files from public databases
summary: nf-core/fetchngs is a bioinformatics pipeline to fetch metadata and raw FastQ files from both public databases. At present, the pipeline supports SRA / ENA / DDBJ / GEO ids (see usage docs).
has_samplesheet: true
input: id list (one value per line)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled)
tools: ["Aspera CLI", "fastq-dl", "Python", "Requests", "sra-tools"]
feeds: ["ampliseq", "atacseq", "mag", "metatdenovo", "rnaseq", "sarek", "taxprofiler", "viralrecon"]
---
# fetchngs

nf-core/fetchngs is a bioinformatics pipeline to fetch metadata and raw FastQ files from both public databases. At present, the pipeline supports SRA / ENA / DDBJ / GEO ids (see usage docs).

## Run it
```bash
git submodule update --init pipelines/fetchngs/upstream   # first time only
nfclaw run fetchngs --input samplesheet.csv --outdir results -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/fetchngs/upstream -profile docker --input samplesheet.csv --outdir results
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions fetchngs` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show fetchngs --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show fetchngs --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
Input is a plain text file with one value per line (no header).

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file path) |  |  | matches `^\S+\.(csv\|tsv\|txt)$` | File containing SRA/ENA/GEO/DDBJ identifiers one per line to download their associated metadata and FastQ files. |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, required, hidden, allowed values, constraints, default and description. Use it as the source of truth; do not guess flags. It uses nfclaw's hyphenated flags; raw Nextflow requires the exact schema spelling (usually underscores). nfclaw checks explicit parameters before launch; the pinned pipeline's validation handles conditional and complex constraints at runtime. It is organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Deprecated options** (`deprecated_options`) — 5 parameters
- **Generic options** (`generic_options`) — 8 parameters
- **Input/output options** (`input_output_options`) — 10 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters

Upstream usage: https://github.com/nf-core/fetchngs/blob/1.13.0/docs/usage.md

## Resources
Resource requests follow the pipeline's configs and selected profiles. nf-core's resource labels often assume a server — a single step can request far more memory than a workstation has, and retry rules can increase requests. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run fetchngs --input samplesheet.csv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=25.10.4'`.

To pin this release's declared minimum engine — useful when a newer Nextflow has incompatible config parsing:
```bash
nfclaw run fetchngs ... --nxf-ver 25.10.4
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/fetchngs/blob/1.13.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Chaining
Run fetchngs as one stage of a chain: `nfclaw chain run spec.json --outdir DIR` starts each stage only after the one before it succeeded, and prepares its inputs from that stage's outputs. The rules live in `handoffs/` (format and spec in [docs/chaining.md](../../docs/chaining.md)); list them with `nfclaw chain edges fetchngs`.

Feeds into:
- `ampliseq` — fetchngs writes an ampliseq samplesheet (sample, fastq_1, fastq_2, run) with --nf-core-pipeline ampliseq. Its run column is empty, so ampliseq treats every sample as one sequencing run and learns one DADA2 error model for all of them; data from several sequencing runs needs run filled per sequencing run: an inline handoff whose set templates it from a column that identifies the run, or your own samplesheet. ampliseq assumes Illumina reads unless told otherwise: for PacBio or Ion Torrent runs (the instrument_platform column) set --pacbio or --iontorrent in the stage's params.
- `atacseq` — fetchngs writes an atacseq samplesheet (every run as replicate 1 of its sample) with --nf-core-pipeline atacseq. Runs whose ENA instrument_platform is not a short-read platform (the ones nf-core/mag accepts as short reads: ILLUMINA, BGISEQ, DNBSEQ, ELEMENT, ULTIMA, ION_TORRENT, LS454, …) are refused: atacseq analyses short reads, and long-read, capillary or colour-space runs would be processed as if they were.
- `mag` — fetchngs writes a mag samplesheet whose read columns predate mag's short_reads_1/short_reads_2; the columns are renamed, each sample gets its own group, and each run keeps its own run id. fetchngs labels every run's reads ILLUMINA short reads; the short-read platform is taken from the run's ENA instrument_platform instead, so a long-read run (OXFORD_NANOPORE, PACBIO_SMRT) is refused rather than analysed as short reads. Different samples are not pooled for binning or assembly; use an inline handoff to supply study-specific pooling groups.
- `metatdenovo` — fetchngs writes a metatdenovo samplesheet (sample, fastq_1, fastq_2) with --nf-core-pipeline metatdenovo. Runs whose ENA instrument_platform is not a short-read platform (the ones nf-core/mag accepts as short reads: ILLUMINA, BGISEQ, DNBSEQ, ELEMENT, ULTIMA, ION_TORRENT, LS454, …) are refused: metatdenovo analyses short reads, and long-read, capillary or colour-space runs would be processed as if they were.
- `rnaseq` — fetchngs downloads the FastQ files and, with --nf-core-pipeline rnaseq, writes samplesheet/samplesheet.csv for rnaseq (absolute FastQ paths; strandedness from --nf-core-rnaseq-strandedness, default auto). Runs whose ENA instrument_platform is not a short-read platform (the ones nf-core/mag accepts as short reads: ILLUMINA, BGISEQ, DNBSEQ, ELEMENT, ULTIMA, ION_TORRENT, LS454, …) are refused: rnaseq analyses short reads, and long-read, capillary or colour-space runs would be processed as if they were.
- `sarek` — fetchngs writes a sarek samplesheet (patient = the ENA sample accession) with --nf-core-pipeline sarek; it has no lane, so each run's accession becomes its lane — sarek needs patient, sample and lane to be unique together; sarek reads paired-end FastQ only, so every row needs a fastq_2. No status or sex column is written: sarek treats every sample as normal tissue (status 0, sex NA) and runs germline analyses only; a tumour/normal design needs its own sarek samplesheet (a handoff's set gives every row the same value). Runs whose ENA instrument_platform is not a short-read platform (the ones nf-core/mag accepts as short reads: ILLUMINA, BGISEQ, DNBSEQ, ELEMENT, ULTIMA, ION_TORRENT, LS454, …) are refused: sarek analyses short reads, and long-read, capillary or colour-space runs would be processed as if they were.
- `taxprofiler` — fetchngs writes a taxprofiler samplesheet with --nf-core-pipeline taxprofiler; run_accession and instrument_platform come from the ENA metadata. The profiling databases (--databases) are the stage's own.
- `viralrecon` — fetchngs writes a viralrecon samplesheet (sample, fastq_1, fastq_2) with --nf-core-pipeline viralrecon. Runs whose ENA instrument_platform is not a short-read platform (the ones nf-core/mag accepts as short reads: ILLUMINA, BGISEQ, DNBSEQ, ELEMENT, ULTIMA, ION_TORRENT, LS454, …) are refused: viralrecon analyses short reads, and long-read, capillary or colour-space runs would be processed as if they were. Pass --platform illumina: viralrecon's nanopore mode does not read this samplesheet.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: Aspera CLI, fastq-dl, Python, Requests, sra-tools.

Full list with references: https://github.com/nf-core/fetchngs/blob/1.13.0/CITATIONS.md

## Demo
```bash
nfclaw run fetchngs --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

<!-- Generated from nf-core/fetchngs@955c892d80927cee633765e6e390f9cc6b7235c9. Do not edit by hand. -->
