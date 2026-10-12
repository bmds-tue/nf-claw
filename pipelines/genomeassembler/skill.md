---
name: genomeassembler
pipeline: nf-core/genomeassembler
version: 2.0.0
commit: a72d47d9cdb50f21b97882dfb2abf4af8f4c74ad
description: Assemble genomes from long ONT or pacbio HiFi reads
summary: nf-core/genomeassembler is a bioinformatics pipeline that carries out genome assembly, polishing and scaffolding from long reads (ONT or pacbio). Assembly can be done via flye or hifiasm, or combinations of both, polishing can be carried out with medaka (ONT), dorado (ONT only, experimental) or pilon (requires short-reads), and scaffolding can be done using LINKS, Longstitch, both using long-reads, yahs if HiC reads are availble, or RagTag if a reference is available. Quality control includes BUSCO, QUAST and merqury (requires short-reads). Currently, this pipeline does not implement phasing of polyploid genomes.
has_samplesheet: true
input: samplesheet (sample, group, ref_fasta, ref_gff, use_ref, strategy, assembler, assembly_scaffolding_order, genome_size, flye_mode, flye_args, hifiasm_args, assembler_ont, assembler_ont_args, assembler_hifi, assembler_hifi_args, ontreads, ont_collect, ont_adapters, ont_fastplong_args, hifireads, hifi_adapters, hifi_fastplong_args, jellyfish, jellyfish_k, jellyfish_size, polish, polish_pilon, polish_dorado, polish_medaka, medaka_model, scaffold_longstitch, scaffold_links, scaffold_ragtag, scaffold_hic, hic_aligner, merqury, qc_reads, busco, busco_db, busco_lineage, quast, ref_map_bam, assembly, assembly_map_bam, csi_index_size, lift_annotations, use_short_reads, shortread_trim, meryl_k, shortread_F, shortread_R, paired, hic_trim, hic_F, hic_R)
output: --outdir/ (configured results); pipeline_info/ (run metadata when enabled)
tools: ["fastp", "hifiasm", "flye", "pilon", "medaka", "dorado", "LINKS", "longstitch", "yahs", "RagTag", "liftoff", "BUSCO", "genomescope2", "jellyfish", "meryl", "QUAST", "minimap2", "samtools", "bwa-mem2", "picard"]
---
# genomeassembler

nf-core/genomeassembler is a bioinformatics pipeline that carries out genome assembly, polishing and scaffolding from long reads (ONT or pacbio). Assembly can be done via flye or hifiasm, or combinations of both, polishing can be carried out with medaka (ONT), dorado (ONT only, experimental) or pilon (requires short-reads), and scaffolding can be done using LINKS, Longstitch, both using long-reads, yahs if HiC reads are availble, or RagTag if a reference is available. Quality control includes BUSCO, QUAST and merqury (requires short-reads). Currently, this pipeline does not implement phasing of polyploid genomes.

## Run it
```bash
git submodule update --init pipelines/genomeassembler/upstream   # first time only
nfclaw run genomeassembler --input samplesheet.csv --outdir results -profile docker
# raw equivalent (the submodule is already pinned to this release, so no -r is needed):
nextflow run pipelines/genomeassembler/upstream -profile docker --input samplesheet.csv --outdir results
```

This is the pinned latest release. To run a different one, list the available releases with `nfclaw versions genomeassembler` and add `--pipeline-version X.Y.Z` to the command above (`nfclaw show genomeassembler --pipeline-version X.Y.Z` prints that release's docs). To run unreleased development code instead, add `--pipeline-version dev`: nfclaw resolves nf-core's `dev` branch to its current head commit at run time and records that commit in provenance (`nfclaw show genomeassembler --pipeline-version dev` prints the docs generated from it). Use it only for changes not yet released.

## Inputs
| column | type | required | allowed values | constraints |
|---|---|---|---|---|
| `sample` | string | yes |  | matches ^\S+$ |
| `group` | string | no |  | matches ^\S+$ |
| `ref_fasta` | string (file path) | no |  |  |
| `ref_gff` | string (file path) | no |  |  |
| `use_ref` | boolean | no |  |  |
| `strategy` | string | no |  |  |
| `assembler` | string | no | `flye`, `hifiasm`, `flye_hifiasm`, `hifiasm_hifiasm`, `flye_flye`, `hifiasm_flye` |  |
| `assembly_scaffolding_order` | string | no | `ont_on_hifi`, `hifi_on_ont` |  |
| `genome_size` | string | no |  |  |
| `flye_mode` | string | no | `--pacbio-raw`, `--pacbio-corr`, `--pacbio-hifi`, `--nano-raw`, `--nano-corr`, `--nano-hq` |  |
| `flye_args` | string | no |  |  |
| `hifiasm_args` | string | no |  |  |
| `assembler_ont` | string | no |  |  |
| `assembler_ont_args` | string | no |  |  |
| `assembler_hifi` | string | no |  |  |
| `assembler_hifi_args` | string | no |  |  |
| `ontreads` | string (file path) | no |  |  |
| `ont_collect` | boolean | no |  |  |
| `ont_adapters` | string | no |  |  |
| `ont_fastplong_args` | string | no |  |  |
| `hifireads` | string (file path) | no |  |  |
| `hifi_adapters` | string | no |  |  |
| `hifi_fastplong_args` | string | no |  |  |
| `jellyfish` | boolean | no |  |  |
| `jellyfish_k` | integer | no |  |  |
| `jellyfish_size` | string | no |  |  |
| `polish` | string | no | `pilon`, `dorado`, `medaka`, `dorado+pilon`, `medaka+pilon` |  |
| `polish_pilon` | boolean | no |  |  |
| `polish_dorado` | boolean | no |  |  |
| `polish_medaka` | boolean | no |  |  |
| `medaka_model` | string | no |  |  |
| `scaffold_longstitch` | boolean | no |  |  |
| `scaffold_links` | boolean | no |  |  |
| `scaffold_ragtag` | boolean | no |  |  |
| `scaffold_hic` | boolean | no |  |  |
| `hic_aligner` | string | no | `bwa-mem2`, `minimap2` |  |
| `merqury` | boolean | no |  |  |
| `qc_reads` | string | no | `ont`, `hifi` |  |
| `busco` | boolean | no |  |  |
| `busco_db` | string (directory path) | no |  |  |
| `busco_lineage` | string | no |  |  |
| `quast` | boolean | no |  |  |
| `ref_map_bam` | string (file path) | no |  |  |
| `assembly` | string | no |  |  |
| `assembly_map_bam` | string (file path) | no |  |  |
| `csi_index_size` | integer | no |  |  |
| `lift_annotations` | boolean | no |  |  |
| `use_short_reads` | boolean | no |  |  |
| `shortread_trim` | boolean | no |  |  |
| `meryl_k` | integer | no |  | ≥ 1 |
| `shortread_F` | string (file path) | no |  |  |
| `shortread_R` | string (file path) | no |  |  |
| `paired` | boolean | no |  |  |
| `hic_trim` | boolean | no |  |  |
| `hic_F` | string (file path) | no |  |  |
| `hic_R` | string (file path) | no |  |  |

`--input` must match `^\S+\.csv$`.

The samplesheet is a CSV with this header (the columns the schema requires); fill each value per the table above and `reference.md` (no example value is invented here):
```csv
sample
```

Any of the optional columns above may be appended to the header when your data needs them: `group`, `ref_fasta`, `ref_gff`, `use_ref`, `strategy`, `assembler`, `assembly_scaffolding_order`, `genome_size`, `flye_mode`, `flye_args`, `hifiasm_args`, `assembler_ont`, `assembler_ont_args`, `assembler_hifi`, `assembler_hifi_args`, `ontreads`, `ont_collect`, `ont_adapters`, `ont_fastplong_args`, `hifireads`, `hifi_adapters`, `hifi_fastplong_args`, `jellyfish`, `jellyfish_k`, `jellyfish_size`, `polish`, `polish_pilon`, `polish_dorado`, `polish_medaka`, `medaka_model`, `scaffold_longstitch`, `scaffold_links`, `scaffold_ragtag`, `scaffold_hic`, `hic_aligner`, `merqury`, `qc_reads`, `busco`, `busco_db`, `busco_lineage`, `quast`, `ref_map_bam`, `assembly`, `assembly_map_bam`, `csi_index_size`, `lift_annotations`, `use_short_reads`, `shortread_trim`, `meryl_k`, `shortread_F`, `shortread_R`, `paired`, `hic_trim`, `hic_F`, `hic_R`.

**From data files.** nfclaw cannot generate this samplesheet: the samplesheet declares no file type nfclaw could match files against (no column's pattern names a file extension).

## Required parameters
| parameter | type | default | allowed values | constraints | description |
|---|---|---|---|---|---|
| `--input` | string (file path) |  |  | matches ^\S+\.csv$ | Path to comma-separated file containing information about the samples in the experiment. |
| `--outdir` | string (directory path) |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## Other parameters
Every parameter not listed above is optional as far as the schema is concerned. [reference.md](reference.md) documents them all — type, default, allowed values and constraints — organised into these groups (counts are full group sizes, so they include any parameter already listed above):
- **Annotations options** (`annotations_options`) — 1 parameter
- **Assembly options** (`assembly_options`) — 11 parameters
- **Generic options** (`generic_options`) — 9 parameters
- **HiC short read options** (`hic_options`) — 3 parameters
- **Input/output options** (`input_output_options`) — 3 parameters
- **Institutional config options** (`institutional_config_options`) — 6 parameters
- **Long-read preprocessing** (`long_read_preprocessing`) — 10 parameters
- **Polishing options** (`polishing_options`) — 5 parameters
- **QC options** (`qc_options`) — 10 parameters
- **Reference Parameters** (`reference_parameters`) — 3 parameters
- **Scaffolding options** (`scaffolding_options`) — 5 parameters
- **Short read options** (`short_read_options`) — 6 parameters

## Resources
A real (non-`--demo`) run requests the resources the pipeline's `conf/base.config` asks for, which are sized for a server — a single step can request far more memory than a workstation has, and Nextflow retries a failed step with more still. If a run fails with `Process requirement exceeds available memory` (or CPUs), cap every request, and every retry, at what this machine actually has:

```bash
nfclaw run genomeassembler --input samplesheet.csv --outdir results -profile docker \
  --limit-cpus 4 --limit-memory 15.GB
```

nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` config — the mechanism nf-core prescribes for exactly this ([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in `<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.

## Nextflow engine
This release declares `nextflowVersion = '!>=25.10.4'`.

To run the engine this release targets — worth doing if a newer Nextflow emits config-parser warnings the release never saw:
```bash
nfclaw run genomeassembler ... --nxf-ver 25.10.4
```
`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same engine. See [known-issues](../../docs/known-issues.md).

## Outputs
Results land in `--outdir`; the files and directory layout depend on the selected workflow, parameters and publication settings. Run metadata is normally placed in `<outdir>/pipeline_info/` (execution report, software versions), when those outputs are enabled. `nfclaw run` also writes `<outdir>/provenance/` with the exact params file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless `--no-provenance` it adds a run manifest (pinned version, commit and exact command), input/output SHA-256 checksums, and a replayable `commands.sh`.

The exact output files and directory layout for this release are documented upstream: https://github.com/nf-core/genomeassembler/blob/2.0.0/docs/output.md

Check a run — in the foreground or the background — with `nfclaw status <outdir>`: success, still running, how it ended (with the error), or stopped without an outcome; exit 0 success, 3 running, 1 otherwise.

## Tools this pipeline runs
The tools/methods this pipeline runs, per the authors' own list: fastp, hifiasm, flye, pilon, medaka, dorado, LINKS, longstitch, yahs, RagTag, liftoff, BUSCO, genomescope2, jellyfish, meryl, QUAST, minimap2, samtools, bwa-mem2, picard.

Full list with references: https://github.com/nf-core/genomeassembler/blob/2.0.0/CITATIONS.md

## Demo
```bash
nfclaw run genomeassembler --demo --outdir results   # adds the upstream test profile (-profile test,docker)
```

## Full reference
Every parameter — name, type, required, hidden, allowed values, constraints, default and description — is in [reference.md](reference.md). Use it as the source of truth; do not guess flags. Nextflow's nf-schema validates every parameter against this schema at runtime, so an unknown or invalid value fails fast. Upstream usage: https://github.com/nf-core/genomeassembler/blob/2.0.0/docs/usage.md

<!-- Generated from nf-core/genomeassembler@a72d47d9cdb50f21b97882dfb2abf4af8f4c74ad. Do not edit by hand. -->
