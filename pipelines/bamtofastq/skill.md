---
name: bamtofastq
pipeline: nf-core/bamtofastq
version: 2.2.1
commit: 8a295860c0c9221337dec7f2620709a47cea254d
description: Workflow converts one or multiple bam/cram files to fastq format
summary: nf-core/bamtofastq is a bioinformatics best-practice analysis pipeline that converts (un)mapped .bam or .cram files into fq.gz files. Initially, it auto-detects, whether the input file contains single-end or paired-end reads. Following this step, the reads are sorted using samtools collate and extracted with samtools fastq. Furthermore, for mapped bam/cram files it is possible to only convert reads mapping to a specific region or chromosome. The obtained FastQ files can then be used to further process with other pipelines.
has_samplesheet: true
input: samplesheet (sample_id, mapped, index, file_type)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["FastQC", "fastq_utils", "MultiQC", "SAMtools"]
feeds: ["rnaseq"]
---
# bamtofastq

nf-core/bamtofastq is a bioinformatics best-practice analysis pipeline that converts (un)mapped .bam or .cram files into fq.gz files. Initially, it auto-detects, whether the input file contains single-end or paired-end reads. Following this step, the reads are sorted using samtools collate and extracted with samtools fastq. Furthermore, for mapped bam/cram files it is possible to only convert reads mapping to a specific region or chromosome. The obtained FastQ files can then be used to further process with other pipelines.

## Run it
```bash
git submodule update --init pipelines/bamtofastq/upstream   # first time only
nfclaw run bamtofastq --input samplesheet.csv --outdir results -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/bamtofastq/upstream -profile docker --input samplesheet.csv --outdir results
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions bamtofastq` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show bamtofastq --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show bamtofastq --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `sample_id` | string | yes |  | matches `^\S+$` |
| `mapped` | string (file path) | yes |  | matches `^\S+\.(bam\|cram)$` |
| `index` | string (file path) | no |  | matches `^\S+\.(bai\|crai)$` |
| `file_type` | string | yes | `bam`, `cram` |  |

`--input` must match `^\S+\.csv$`.

The samplesheet is a CSV with this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
sample_id,mapped,file_type
```

Any of the optional columns above may be appended to the header when your data needs them: `index`.

**From data files.** `--input` may also be the data files — a directory (searched recursively), a quoted glob, or files (`--input` once per file) — from which nfclaw writes this samplesheet: `sample_id` from file names; `mapped`, `index` from files matching their patterns, by sample name. Set the required columns no file determines with `--sheet-set COLUMN=VALUE` (a constant or a `{sample}`/`{lane}` template): `file_type` (one of bam, cram). Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file path) |  |  | matches `^\S+\.csv$` | Path to comma-separated file containing information about the samples in the experiment. |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## Reference genome
No reference genome is set by default: supply your own reference. The schema declares AWS iGenomes at `s3://ngi-igenomes/igenomes/`; selecting `--genome <id>` uses the paths in the pipeline's reference configuration. Access to that remote source is required. To supply your own reference, use e.g. `--fasta`; the `reference_genome_options` group in [reference.md](reference.md) lists every reference option. Set `--igenomes-ignore true` to disable the lookup entirely. Confirm the selected reference's paths and source in the pinned `upstream/nextflow.config` and `upstream/conf/` before running.

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, required, hidden, allowed values, constraints, default and description. Use it as the source of truth; do not guess flags. It uses nfclaw's hyphenated flags; raw Nextflow requires the exact schema spelling (usually underscores). nfclaw checks explicit parameters before launch; the pinned pipeline's validation handles conditional and complex constraints at runtime. It is organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Generic options** (`generic_options`) — 17 parameters
- **Input/output options** (`input_output_options`) — 2 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **Main options** (`main_options`) — 5 parameters
- **Reference genome options** (`reference_genome_options`) — 5 parameters

Upstream usage: https://github.com/nf-core/bamtofastq/blob/2.2.1/docs/usage.md

## Resources
Resource requests follow the pipeline's configs and selected profiles. nf-core's resource labels often assume a server — a single step can request far more memory than a workstation has, and retry rules can increase requests. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run bamtofastq --input samplesheet.csv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=25.10.4'`.

To pin this release's declared minimum engine — useful when a newer Nextflow has incompatible config parsing:
```bash
nfclaw run bamtofastq ... --nxf-ver 25.10.4
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/bamtofastq/blob/2.2.1/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Chaining
Run bamtofastq as one stage of a chain: `nfclaw chain run spec.json --outdir DIR` starts each stage only after the one before it succeeded, and prepares its inputs from that stage's outputs. The rules live in `handoffs/` (format and spec in [docs/chaining.md](../../docs/chaining.md)); list them with `nfclaw chain edges bamtofastq`.

Feeds into:
- `rnaseq` — bamtofastq publishes converted paired-end reads as reads/<sample>_1.merged.fastq.gz and _2; one rnaseq row per sample, strandedness detected by rnaseq (auto). Single-end conversions are published as reads/<sample>_other.fq.gz: a run with any fails this handoff instead of leaving them out, and needs an inline handoff.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: FastQC, fastq_utils, MultiQC, SAMtools.

Full list with references: https://github.com/nf-core/bamtofastq/blob/2.2.1/CITATIONS.md

## Demo
```bash
nfclaw run bamtofastq --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

This pinned test profile omits its required reference. For the bundled demo input, nfclaw supplies the matched chr22:1-40001 test FASTA from immutable test-datasets commit `618f1541382c4ad49eff566dadf13d5ccbd0ebb4` and records it in params/provenance. Explicit `--fasta` or params-file values override it. Your own input, genome, test-data base, extra profiles or `--config` disable this demo default; choose a reference matched to your data. The correction applies only to the bundled test plus engine profiles. Other releases retain their own defaults.

<!-- Generated from nf-core/bamtofastq@8a295860c0c9221337dec7f2620709a47cea254d. Do not edit by hand. -->
