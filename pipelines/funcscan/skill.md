---
name: funcscan
pipeline: nf-core/funcscan
version: 4.0.0
commit: aee3dc965eb0c77267435544dda30da858763913
description: Pipeline for screening for functional components of assembled contigs
summary: nf-core/funcscan is a bioinformatics best-practice analysis pipeline for the screening of nucleotide sequences such as assembled contigs for functional genes. It currently features mining for antimicrobial peptides, antibiotic resistance genes and biosynthetic gene clusters.
has_samplesheet: true
input: samplesheet (sample, fasta, protein, gbk, gff, gff_type)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled); MultiQC report (conditional)
tools: ["ABRicate", "AMPir", "AMPlify", "AMRFinderPlus", "AntiSMASH", "argNorm", "Bakta", "BiG-SLiCE", "comBGC", "DeepARG", "DeepBGC", "fARGene", "GECCO", "AMPcombi", "hAMRonization", "HMMER", "InterPro", "InterProScan", "Macrel", "MMseqs2", "Prodigal", "PROKKA", "Pyrodigal", "RGI", "dbCAN", "SeqKit"]
---
# funcscan

nf-core/funcscan is a bioinformatics best-practice analysis pipeline for the screening of nucleotide sequences such as assembled contigs for functional genes. It currently features mining for antimicrobial peptides, antibiotic resistance genes and biosynthetic gene clusters.

## Run it
```bash
git submodule update --init pipelines/funcscan/upstream   # first time only
nfclaw run funcscan --input samplesheet.csv --outdir results -profile docker
# direct upstream execution (omits nfclaw's recorded workflow correction):
nextflow run pipelines/funcscan/upstream -profile docker --input samplesheet.csv --outdir results
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions funcscan` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show funcscan --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show funcscan --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Runtime corrections
For this exact commit, `nfclaw run` applies `funcscan-hmm-metadata-v1` in a separate verified working copy. HMM search retains sample metadata so all HMM results reach AMPcombi. The original pinned checkout stays unchanged. The direct Nextflow command omits this correction. The actual corrected bytes, recipe, source archive and executable modes are recorded for replay; resume refuses missing or changed source identity. Use `NFCLAW_SOURCE_CACHE` to select another writable user cache. [Recorded source corrections](../../docs/source-corrections.md) explains the exact scope and validation.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `sample` | string | yes |  | matches `^\S+$` |
| `fasta` | string (file path) | yes |  | matches `^\S+\.(fasta\|fas\|fna\|fa)(\.gz)?$` |
| `protein` | string (file path) | no |  | matches `^\S+\.(faa\|fasta)(\.gz)?$` |
| `gbk` | string (file path) | no |  | matches `^\S+\.(gbk\|gbff)(\.gz)?$` |
| `gff` | string (file path) | no |  | matches `^\S+\.(gff\|gff3)(\.gz)?$` |
| `gff_type` | string | no | `NCBI_prok`, `prodigal`, `NCBI_euk`, `JGI` |  |

`--input` must match `^\S+\.csv$`.

Additional row validation rules from the schema:
- When `protein` is set, also provide `gbk`.
- When `gbk` is set, also provide `protein`.
- When `gff` is set, also provide `protein`.

The samplesheet is a CSV with this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
sample,fasta
```

Any of the optional columns above may be appended to the header when your data needs them: `protein`, `gbk`, `gff`, `gff_type`.

**From data files.** `--input` may also be the data files — a directory (searched recursively), a quoted glob, or files (`--input` once per file) — from which nfclaw writes this samplesheet: `sample` from file names; `fasta`, `protein`, `gbk`, `gff` from files matching their patterns, by sample name. Set other columns with `--sheet-set COLUMN=VALUE`. Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file path) |  |  | matches `^\S+\.csv$` | Path to comma-separated file containing sample names and paths to corresponding FASTA files, and optional annotation files. |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## Reference database
The bundled demo selects APD. For DRAMP, this release uses AMPcombi 3.0.0, whose downloader crashes on missing sequence cells. Prepare a complete local DRAMP TSV with `nfclaw prepare-dramp RAW.tsv --outdir /refs/amp_DRAMP_database`, inspect its recorded exclusions, then build `mmseqs2/ref_DB` before analysis. Supply both `--amp-ampcombi-db-id DRAMP` and `--amp-ampcombi-db /refs/amp_DRAMP_database`. The helper preserves retained sequences and annotations, excludes missing IDs and noncanonical/missing sequences, and refuses an existing output. [DRAMP reference preparation](../../docs/dramp-reference.md) gives the pinned-image index recipe and validation scope.

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, required, hidden, allowed values, constraints, default and description. Use it as the source of truth; do not guess flags. It uses nfclaw's hyphenated flags; raw Nextflow requires the exact schema spelling (usually underscores). nfclaw checks explicit parameters before launch; the pinned pipeline's validation handles conditional and complex constraints at runtime. It is organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **AMP: ampcombi2 cluster** (`amp_ampcombi2_cluster`) — 7 parameters
- **AMP: ampcombi2 parsetables** (`amp_ampcombi2_parsetables`) — 13 parameters
- **AMP: ampir** (`amp_ampir`) — 3 parameters
- **AMP: AMPlify** (`amp_amplify`) — 1 parameter
- **AMP: hmmsearch** (`amp_hmmsearch`) — 5 parameters
- **AMP: Macrel** (`amp_macrel`) — 1 parameter
- **Annotation: BAKTA** (`annotation_bakta`) — 22 parameters
- **Annotation: general options** (`annotation_general_options`) — 2 parameters
- **Annotation: Prodigal** (`annotation_prodigal`) — 4 parameters
- **Annotation: Prokka** (`annotation_prokka`) — 12 parameters
- **Annotation: Pyrodigal** (`annotation_pyrodigal`) — 5 parameters
- **ARG: ABRicate** (`arg_abricate`) — 5 parameters
- **ARG: AMRFinderPlus** (`arg_amrfinderplus`) — 7 parameters
- **ARG: argNorm** (`arg_argnorm`) — 1 parameter
- **ARG: DeepARG** (`arg_deeparg`) — 9 parameters
- **ARG: fARGene** (`arg_fargene`) — 7 parameters
- **ARG: hAMRonization** (`arg_hamronization`) — 1 parameter
- **ARG: RGI** (`arg_rgi`) — 11 parameters
- **BGC: antiSMASH** (`bgc_antismash`) — 16 parameters
- **BGC: BiG-SLiCE** (`bgc_bigslice`) — 7 parameters
- **BGC: DeepBGC** (`bgc_deepbgc`) — 11 parameters
- **BGC: GECCO** (`bgc_gecco`) — 9 parameters
- **BGC: general options** (`bgc_general_options`) — 2 parameters
- **BGC: hmmsearch** (`bgc_hmmsearch`) — 5 parameters
- **dbCAN** (`cazyme_dbcan`) — 4 parameters
- **Database downloading options** (`database_downloading_options`) — 1 parameter
- **Generic options** (`generic_options`) — 15 parameters
- **Input/output options** (`input_output_options`) — 4 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **Protein Annotation: INTERPROSCAN** (`protein_annotation`) — 6 parameters
- **Screening type activation** (`screening_type_activation`) — 4 parameters
- **Taxonomic classification: general options** (`taxonomic_classification_general_options`) — 3 parameters
- **Taxonomic classification: MMseqs2 databases** (`taxonomic_classification_mmseqs2_databases`) — 3 parameters
- **Taxonomic classification: MMseqs2 taxonomy** (`taxonomic_classification_mmseqs2_taxonomy`) — 8 parameters

Upstream usage: https://github.com/nf-core/funcscan/blob/4.0.0/docs/usage.md

## Resources
Resource requests follow the pipeline's configs and selected profiles. nf-core's resource labels often assume a server — a single step can request far more memory than a workstation has, and retry rules can increase requests. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run funcscan --input samplesheet.csv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=25.10.4'`.

To pin this release's declared minimum engine — useful when a newer Nextflow has incompatible config parsing:
```bash
nfclaw run funcscan ... --nxf-ver 25.10.4
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. The pinned tree includes MultiQC support; a report is produced only when its workflow step runs. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/funcscan/blob/4.0.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: ABRicate, AMPir, AMPlify, AMRFinderPlus, AntiSMASH, argNorm, Bakta, BiG-SLiCE, comBGC, DeepARG, DeepBGC, fARGene, GECCO, AMPcombi, hAMRonization, HMMER, InterPro, InterProScan, Macrel, MMseqs2, Prodigal, PROKKA, Pyrodigal, RGI, dbCAN, SeqKit.

Full list with references: https://github.com/nf-core/funcscan/blob/4.0.0/CITATIONS.md

## Demo
```bash
nfclaw run funcscan --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

<!-- Generated from nf-core/funcscan@aee3dc965eb0c77267435544dda30da858763913. Do not edit by hand. -->
