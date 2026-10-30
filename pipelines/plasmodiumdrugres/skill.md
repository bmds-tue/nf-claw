---
name: plasmodiumdrugres
pipeline: nf-core/plasmodiumdrugres
version: 1.0.0
commit: a333327a245ccb3c0f1a37167a7afe670c35894e
description: This pipeline takes PMO format and provides key metrics on supplied markers applicable to drug resistance
summary: nf-core/plasmodiumdrugres is a bioinformatics pipeline for analyzing drug resistance markers from microhaplotype data. It translates variants into amino acid changes at drug resistance loci and estimates allele frequencies and prevalences at both single-locus and multi-locus levels. Microhaplotype data can be supplied in the form of an allele table or a PMO file.
has_samplesheet: false
input: --input (no samplesheet schema)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled)
tools: ["PGEcore", "IDM", "MultiLociBiallelicModel", "FreqEstimationModel", "Dcifer"]
---
# plasmodiumdrugres

nf-core/plasmodiumdrugres is a bioinformatics pipeline for analyzing drug resistance markers from microhaplotype data. It translates variants into amino acid changes at drug resistance loci and estimates allele frequencies and prevalences at both single-locus and multi-locus levels. Microhaplotype data can be supplied in the form of an allele table or a PMO file.

## Run it
```bash
git submodule update --init pipelines/plasmodiumdrugres/upstream   # first time only
nfclaw run plasmodiumdrugres --outdir results --loci-of-interest-bed <loci_of_interest_bed> -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/plasmodiumdrugres/upstream -profile docker --outdir results --loci_of_interest_bed <loci_of_interest_bed>
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions plasmodiumdrugres` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show plasmodiumdrugres --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show plasmodiumdrugres --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
This release publishes no samplesheet schema for `--input`, so nfclaw does not pre-check its contents. The parameter reads: Path to input samplesheet (unused; kept for nf-core template lint compatibility). Configure the other inputs via parameters (see [reference.md](reference.md)).

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--loci-of-interest-bed` | string (file path) |  |  | matches `^\S+\.bed$` | Path to BED file containing individual loci of interest. |

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, required, hidden, allowed values, constraints, default and description. Use it as the source of truth; do not guess flags. It uses nfclaw's hyphenated flags; raw Nextflow requires the exact schema spelling (usually underscores). nfclaw checks explicit parameters before launch; the pinned pipeline's validation handles conditional and complex constraints at runtime. It is organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Generic options** (`generic_options`) — 11 parameters
- **Input/output options** (`input_output_options`) — 12 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **Method options for pipeline steps** (`method_options`) — 14 parameters
- **Reference genome options** (`reference_genome_options`) — 2 parameters

Upstream usage: https://github.com/nf-core/plasmodiumdrugres/blob/1.0.0/docs/usage.md

## Resources
Resource requests follow the pipeline's configs and selected profiles. nf-core's resource labels often assume a server — a single step can request far more memory than a workstation has, and retry rules can increase requests. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run plasmodiumdrugres --outdir results --loci-of-interest-bed <loci_of_interest_bed> -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=25.10.4'`.

To pin this release's declared minimum engine — useful when a newer Nextflow has incompatible config parsing:
```bash
nfclaw run plasmodiumdrugres ... --nxf-ver 25.10.4
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/plasmodiumdrugres/blob/1.0.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: PGEcore, IDM, MultiLociBiallelicModel, FreqEstimationModel, Dcifer.

Full list with references: https://github.com/nf-core/plasmodiumdrugres/blob/1.0.0/CITATIONS.md

## Demo
```bash
nfclaw run plasmodiumdrugres --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

<!-- Generated from nf-core/plasmodiumdrugres@a333327a245ccb3c0f1a37167a7afe670c35894e. Do not edit by hand. -->
