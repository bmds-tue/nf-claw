---
name: variantbenchmarking
pipeline: nf-core/variantbenchmarking
version: 1.5.0
commit: 8b21c01749c4447b285d242a198127736f3ffe51
description: Variant Benchmarking pipeline for germline and somatic variant callers
summary: nf-core/variantbenchmarking is designed to evaluate and validate the accuracy of variant calling methods in genomic research. Initially, the pipeline is tuned well for available gold standard truth sets (for example, Genome in a Bottle and SEQC2 samples) but it can be used to compare any two variant calling results. The workflow provides benchmarking tools for small variants including SNVs and INDELs, Structural Variants (SVs) and Copy Number Variations (CNVs) for germline and somatic analysis.
has_samplesheet: true
input: samplesheet (test_vcf, test_regions, id, caller, subsample, normshift, normdist, normsizediff, maxdist, pctsize, pctseq, pctovl, refdist, chunksize, dup_to_ins, typeignore, bpDistance, percentThreshold, absoluteThreshold, maxMatches, evaluationmode, liftover, fix_prefix)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["Bcftools", "BEDTools", "bedops", "gatk4-concordance", "datavzrd", "hap.py", "manta", "MultiQC", "picard", "RTG Tools", "SURVIVOR", "som.py", "SVanalyzer", "svtk", "svync", "tabix", "truvari", "UCSC", "variant-extractor", "witty.er", "ggplot2", "reshape2", "pysam"]
---
# variantbenchmarking

nf-core/variantbenchmarking is designed to evaluate and validate the accuracy of variant calling methods in genomic research. Initially, the pipeline is tuned well for available gold standard truth sets (for example, Genome in a Bottle and SEQC2 samples) but it can be used to compare any two variant calling results. The workflow provides benchmarking tools for small variants including SNVs and INDELs, Structural Variants (SVs) and Copy Number Variations (CNVs) for germline and somatic analysis.

## Run it
```bash
git submodule update --init pipelines/variantbenchmarking/upstream   # first time only
nfclaw run variantbenchmarking --input samplesheet.csv --outdir results --analysis <analysis> --variant-type <variant_type> --method <method> --fasta <fasta> --fai <fai> -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/variantbenchmarking/upstream -profile docker --input samplesheet.csv --outdir results --analysis <analysis> --variant-type <variant_type> --method <method> --fasta <fasta> --fai <fai>
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions variantbenchmarking` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show variantbenchmarking --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show variantbenchmarking --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `test_vcf` | string (file path) | no |  | matches \S+\.(vcf\|bcf)(\.gz)?$ |
| `test_regions` | string (file path) | no |  | matches ^\S+\.(vcf\|bed\|txt\|cnn\|csv\|cns\|gz_CNVs)(\.gz)?$ |
| `id` | string | yes |  | matches ^\S+$; length ≥ 1 |
| `caller` | string | yes |  | matches ^\S+$; length ≥ 1 |
| `subsample` | string | no |  | matches ^\S+$; length ≥ 1 |
| `normshift` | number | no |  | ≥ 0; ≤ 1 |
| `normdist` | number | no |  | ≥ 0; ≤ 1 |
| `normsizediff` | number | no |  | ≥ 0; ≤ 1 |
| `maxdist` | integer | no |  | ≥ 0 |
| `pctsize` | number | no |  | ≥ 0; ≤ 1 |
| `pctseq` | number | no |  | ≥ 0; ≤ 1 |
| `pctovl` | number | no |  | ≥ 0; ≤ 1 |
| `refdist` | integer | no |  | ≥ 0 |
| `chunksize` | integer | no |  | ≥ 0 |
| `dup_to_ins` | boolean | no |  |  |
| `typeignore` | boolean | no |  |  |
| `bpDistance` | integer | no |  | ≥ 0 |
| `percentThreshold` | number | no |  | ≥ 0 |
| `absoluteThreshold` | integer | no |  | ≥ 0 |
| `maxMatches` | integer | no |  |  |
| `evaluationmode` | string | no | `sc`, `cts`, `d` | length ≥ 1 |
| `liftover` | boolean | no |  |  |
| `fix_prefix` | boolean | no |  |  |

`--input` must match `^\S+\.(csv|tsv|yaml|yml|json)$`.

Additional row validation rules from the schema:
- At least one of these conditional requirements must be satisfied: `test_vcf` when `id` is set; `test_regions` when `id` is set.

For tabular CSV/TSV input, use this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
id,caller
```

Any of the optional columns above may be appended to the header when your data needs them: `test_vcf`, `test_regions`, `subsample`, `normshift`, `normdist`, `normsizediff`, `maxdist`, `pctsize`, `pctseq`, `pctovl`, `refdist`, `chunksize`, `dup_to_ins`, `typeignore`, `bpDistance`, `percentThreshold`, `absoluteThreshold`, `maxMatches`, `evaluationmode`, `liftover`, `fix_prefix`.

**From data files.** `--input` may also be the data files — a directory (searched recursively), a quoted glob, or files (`--input` once per file) — from which nfclaw writes this samplesheet: `id` from file names; `test_vcf`, `test_regions` from files matching their patterns, by sample name. Set the required columns no file determines with `--sheet-set COLUMN=VALUE` (a constant or a `{sample}`/`{lane}` template): `caller` (matching ^\S+$). Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file path) |  |  | matches ^\S+\.(csv\|tsv\|yaml\|yml\|json)$ | Path to comma-separated file containing information about the samples in the experiment. |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--analysis` | string |  | `germline`, `somatic` |  | The analysis type used by the input files |
| `--variant-type` | string |  | `small`, `snv`, `indel`, `structural`, `copynumber` |  | Variant types to benchmark |
| `--method` | string |  |  | matches ^((truvari\|svanalyzer\|happy\|sompy\|rtgtools\|wittyer\|intersect\|bndeval\|concordance)?,?)*(?<!,)$ | The benchmarking methods to use. For germline small variants (SNV and INDEL) use happy and/or rtgtools, for somatic small variants (SNV and INDEL) use sompy and/or rtgtools, for structural variants use wittyer, truvari and/or svanalyzer, for copy number variations use wittyer and/or truvari. Use intersect to intersect BED files. Should be a comma-separate list of one or more of the following options: truvari, svanalyzer, happy, sompy, rtgtools, wittyer, intersect |
| `--fasta` | string (file path) |  |  | matches ^\S+\.fn?a(sta)?(\.gz)?$ | Path to FASTA genome file. |
| `--fai` | string (file path) |  |  | matches ^\S+\.fai$ | Path to FAI genome file. |

## Reference genome
No reference genome is set by default: supply your own reference. The schema declares AWS iGenomes at `s3://ngi-igenomes/igenomes/`; selecting `--genome <id>` uses the paths in the pipeline's reference configuration. Access to that remote source is required. To supply your own reference, use e.g. `--fasta`; the `reference_genome_options` group in [reference.md](reference.md) lists every reference option. Set `--igenomes-ignore true` to disable the lookup entirely. Confirm the selected reference's paths and source in the pinned `upstream/nextflow.config` and `upstream/conf/` before running.

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, default, allowed values and constraints — organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Generic options** (`generic_options`) — 17 parameters
- **Input/output options** (`input_output_options`) — 24 parameters
- **Institutional config options** (`institutional_config_options`) — 7 parameters
- **Reference genome options** (`reference_genome_options`) — 12 parameters

## Resources
A real (non-`--demo`) run requests the resources the pipeline's `conf/base.config` asks for, which are sized for a server — a single step can request far more memory than a workstation has, and Nextflow retries a failed step with more still. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run variantbenchmarking --input samplesheet.csv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=25.04.0'`.

To run the engine this release targets — worth doing if a newer Nextflow emits config-parser warnings the release never saw:
```bash
nfclaw run variantbenchmarking ... --nxf-ver 25.04.0
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/variantbenchmarking/blob/1.5.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: Bcftools, BEDTools, bedops, gatk4-concordance, datavzrd, hap.py, manta, MultiQC, picard, RTG Tools, SURVIVOR, som.py, SVanalyzer, svtk, svync, tabix, truvari, UCSC, variant-extractor, witty.er, ggplot2, reshape2, pysam.

Full list with references: https://github.com/nf-core/variantbenchmarking/blob/1.5.0/CITATIONS.md

## Demo
```bash
nfclaw run variantbenchmarking --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

## Full reference
Every parameter — name, type, required, hidden, allowed values, constraints, default and description — is in [reference.md](reference.md). Use it as the source of truth; do not guess flags. Nextflow's nf-schema validates every parameter against this schema at runtime, so an unknown or invalid value fails fast. Upstream usage: https://github.com/nf-core/variantbenchmarking/blob/1.5.0/docs/usage.md

<!-- Generated from nf-core/variantbenchmarking@8b21c01749c4447b285d242a198127736f3ffe51. Do not edit by hand. -->
