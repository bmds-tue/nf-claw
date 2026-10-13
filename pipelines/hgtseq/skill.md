---
name: hgtseq
pipeline: nf-core/hgtseq
version: 1.1.0
commit: 683daaf41bb396839445e603152b45daa141ced4
description: A pipeline to investigate horizontal gene transfer from NGS data
summary: nf-core/hgtseq is a bioinformatics best-practice analysis pipeline built to investigate horizontal gene transfer from NGS data.
has_samplesheet: true
input: samplesheet (input1, input2, sample)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["FastQC", "MultiQC", "Trim Galore", "Qualimap", "BAMTOOLS", "BWA", "BWAmem2", "SAMtools", "Kraken2", "Krona", "RMarkDown"]
---
# hgtseq

nf-core/hgtseq is a bioinformatics best-practice analysis pipeline built to investigate horizontal gene transfer from NGS data.

## Run it
```bash
git submodule update --init pipelines/hgtseq/upstream   # first time only
nfclaw run hgtseq --input samplesheet.csv --outdir results --taxonomy-id <taxonomy_id> -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/hgtseq/upstream -profile docker --input samplesheet.csv --outdir results --taxonomy_id <taxonomy_id>
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions hgtseq` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show hgtseq --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show hgtseq --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
**Pinned input correction.** The bundled schema is an unused FASTQ template. These columns come from the pinned consumer, which reads `input1` and optional `input2`. Paired inputs must have the same extension; BAM/CRAM input cannot have a second mate. Write the sheet explicitly.

| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `input1` | string (file path) | yes |  | matches ^\S+\.(fastq(\.gz)?\|bam\|cram)$ |
| `input2` | string (file path) | no |  | matches ^\S+\.fastq(\.gz)?$ |
| `sample` | string | yes |  | matches ^\S+$ |

`--input` must match `^\S+\.csv$`.

The samplesheet is a CSV with this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
input1,sample
```

Any of the optional columns above may be appended to the header when your data needs them: `input2`.

**From data files.** nfclaw cannot generate this samplesheet: the pinned consumer accepts mixed FASTQ/alignment roles that require an explicit samplesheet.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file path) |  |  | matches ^\S+\.csv$ | Path to comma-separated file containing information about the samples in the experiment. |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--taxonomy-id` | number |  |  |  | TaxID of samples used as input |
| `--krakendb` | string | None |  |  | A local path to kraken database folder or compressed database file, or a URL to a compressed database file, in tar.gz format |
| `--kronadb` | string | None |  |  | A local path or a URL to a .tab krona taxonomy file; it can also receive a compressed .tab file in tar.gz format |

## Reference genome
No reference genome is set by default: supply your own reference. The schema declares AWS iGenomes at `s3://ngi-igenomes/igenomes`; selecting `--genome <id>` uses the paths in the pipeline's reference configuration. Access to that remote source is required. To supply your own reference, use e.g. `--fasta`; the `reference_genome_options` group in [reference.md](reference.md) lists every reference option. Set `--igenomes-ignore true` to disable the lookup entirely. Confirm the selected reference's paths and source in the pinned `upstream/nextflow.config` and `upstream/conf/` before running.

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, default, allowed values and constraints — organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Generic options** (`generic_options`) — 14 parameters
- **Input/output options** (`input_output_options`) — 7 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **Max job request options** (`max_job_request_options`) — 3 parameters
- **Reference genome options** (`reference_genome_options`) — 9 parameters
- **Run options** (`run_options`) — 2 parameters

## Resources
Resource requests follow the pipeline's configs and selected profiles. nf-core's resource labels often assume a server — a single step can request far more memory than a workstation has, and retry rules can increase requests. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run hgtseq --input samplesheet.csv --outdir results --taxonomy-id <taxonomy_id> -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=22.10.1'`.

To pin this release's declared minimum engine — useful when a newer Nextflow has incompatible config parsing:
```bash
nfclaw run hgtseq ... --nxf-ver 22.10.1
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

Nextflow 22.10.1 predates `process.resourceLimits` (24.04.0), so `--limit-*` cannot be combined with this pin — nfclaw refuses it rather than run without the ceiling; cap resources with the release's own `--max-cpus`, `--max-memory`, `--max-time` instead.

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/hgtseq/blob/1.1.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: FastQC, MultiQC, Trim Galore, Qualimap, BAMTOOLS, BWA, BWAmem2, SAMtools, Kraken2, Krona, RMarkDown.

Full list with references: https://github.com/nf-core/hgtseq/blob/1.1.0/CITATIONS.md

## Demo
```bash
nfclaw run hgtseq --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

## Full reference
Every parameter — name, type, required, hidden, allowed values, constraints, default and description — is in [reference.md](reference.md). Use it as the source of truth; do not guess flags. nfclaw checks explicit parameters before launch; the pinned pipeline's validation handles conditional and complex constraints at runtime. The reference uses nfclaw's hyphenated flags; raw Nextflow requires the exact schema spelling (usually underscores). Upstream usage: https://github.com/nf-core/hgtseq/blob/1.1.0/docs/usage.md

<!-- Generated from nf-core/hgtseq@683daaf41bb396839445e603152b45daa141ced4. Do not edit by hand. -->
