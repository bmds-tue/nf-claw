---
name: createtaxdb
pipeline: nf-core/createtaxdb
version: 3.1.0
commit: b01a0f8ed96a5990d15470828dfa92a22cf08bba
description: Parallelised and automated creation of metagenomic classifier databases of different tools
summary: nf-core/createtaxdb is a bioinformatics pipeline that constructs custom metagenomic classifier databases for multiple classifiers and profilers from the same input reference genome set in a highly automated and parallelised manner. It supports both nucleotide and protein based classifiers and profilers. The pipeline is designed to be a companion pipeline to nf-core/taxprofiler for taxonomic profiling of metagenomic data, but can be used for any context.
has_samplesheet: true
input: samplesheet (id, taxid, fasta_dna, fasta_aa)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["Bracken", "Centrifuge", "Centrifuger", "DIAMOND", "ganon", "Kaiju", "KMCP", "Kraken2", "KrakenUniq", "MALT", "MetaCache", "MultiQC", "SeqKit2", "sourmash", "sylph"]
feeds: ["taxprofiler"]
---
# createtaxdb

nf-core/createtaxdb is a bioinformatics pipeline that constructs custom metagenomic classifier databases for multiple classifiers and profilers from the same input reference genome set in a highly automated and parallelised manner. It supports both nucleotide and protein based classifiers and profilers. The pipeline is designed to be a companion pipeline to nf-core/taxprofiler for taxonomic profiling of metagenomic data, but can be used for any context.

## Run it
```bash
git submodule update --init pipelines/createtaxdb/upstream   # first time only
nfclaw run createtaxdb --input samplesheet.csv --outdir results --dbname <dbname> -profile docker
# direct upstream execution (omits nfclaw's recorded workflow correction):
nextflow run pipelines/createtaxdb/upstream -profile docker --input samplesheet.csv --outdir results --dbname <dbname>
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions createtaxdb` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show createtaxdb --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show createtaxdb --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Runtime corrections
For this exact commit, `nfclaw run` applies `createtaxdb-sourmash-copy-sort-v1` in a separate verified working copy. Sourmash sorts a copy rather than the shared genome list. The original pinned checkout stays unchanged. The direct Nextflow command omits this correction. The actual corrected bytes, recipe, source archive and executable modes are recorded for replay; resume refuses missing or changed source identity. Use `NFCLAW_SOURCE_CACHE` to select another writable user cache. [Recorded source corrections](../../docs/source-corrections.md) explains the exact scope and validation.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `id` | string | yes |  | matches ^\S+$ |
| `taxid` | integer | yes |  |  |
| `fasta_dna` | string (file path) | no |  | matches ^\S+\.(fasta\|fas\|fa\|fna)(\.gz)?$ |
| `fasta_aa` | string (file path) | no |  | matches ^\S+\.(fasta\|fas\|fa\|faa)(\.gz)?$ |

`--input` must match `^\S+\.csv$`.

The samplesheet is a CSV with this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
id,taxid
```

Any of the optional columns above may be appended to the header when your data needs them: `fasta_dna`, `fasta_aa`.

**From data files.** `--input` may also be the data files — a directory (searched recursively), a quoted glob, or files (`--input` once per file) — from which nfclaw writes this samplesheet: `id` from file names; `fasta_dna`, `fasta_aa` from files matching their patterns, by sample name. Set the required columns no file determines with `--sheet-set COLUMN=VALUE` (a constant or a `{sample}`/`{lane}` template): `taxid` (integer). Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file path) |  |  | matches ^\S+\.csv$ | Path to comma-separated file containing information about the samples in the experiment. |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--dbname` | string |  |  |  | Specify name that resulting databases will be prefixed with. |
| `--unzip-batch-size` | integer | 10000 |  |  | How many files to unzip in parallel in a single job. |

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, required, hidden, allowed values, constraints, default and description. Use it as the source of truth; do not guess flags. It uses nfclaw's hyphenated flags; raw Nextflow requires the exact schema spelling (usually underscores). nfclaw checks explicit parameters before launch; the pinned pipeline's validation handles conditional and complex constraints at runtime. It is organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Database Building Options** (`database_building_options`) — 33 parameters
- **Downstream pipeline samplesheet generation options** (`generate_samplesheet_options`) — 2 parameters
- **Generic options** (`generic_options`) — 16 parameters
- **Input file preprocessing** (`input_file_preprocessing`) — 3 parameters
- **Input/output options** (`input_output_options`) — 13 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters

Upstream usage: https://github.com/nf-core/createtaxdb/blob/3.1.0/docs/usage.md

## Resources
Resource requests follow the pipeline's configs and selected profiles. nf-core's resource labels often assume a server — a single step can request far more memory than a workstation has, and retry rules can increase requests. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run createtaxdb --input samplesheet.csv --outdir results --dbname <dbname> -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=25.10.4'`.

To pin this release's declared minimum engine — useful when a newer Nextflow has incompatible config parsing:
```bash
nfclaw run createtaxdb ... --nxf-ver 25.10.4
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/createtaxdb/blob/3.1.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Chaining
Run createtaxdb as one stage of a chain: `nfclaw chain run spec.json --outdir DIR` starts each stage only after the one before it succeeded, and prepares its inputs from that stage's outputs. The rules live in `handoffs/` (format and spec in [docs/chaining.md](../../docs/chaining.md)); list them with `nfclaw chain edges createtaxdb`.

Feeds into:
- `taxprofiler` — createtaxdb, with --generate-downstream-samplesheets, writes downstream_samplesheets/databases-taxprofiler.csv; it becomes taxprofiler's --databases, minus any database for a tool the pinned taxprofiler does not run (createtaxdb 3.1 also builds sourmash). The reads to profile (--input) and the --run-<tool> switches are the stage's own.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: Bracken, Centrifuge, Centrifuger, DIAMOND, ganon, Kaiju, KMCP, Kraken2, KrakenUniq, MALT, MetaCache, MultiQC, SeqKit2, sourmash, sylph.

Full list with references: https://github.com/nf-core/createtaxdb/blob/3.1.0/CITATIONS.md

## Demo
```bash
nfclaw run createtaxdb --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

<!-- Generated from nf-core/createtaxdb@b01a0f8ed96a5990d15470828dfa92a22cf08bba. Do not edit by hand. -->
