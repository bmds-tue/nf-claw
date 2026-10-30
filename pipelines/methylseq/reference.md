---
name: methylseq
version: 4.2.0
commit: 5aa56467a85a5e2d6795ea72dfa5a5f0c9babc23
---

# methylseq — full parameter reference

nf-core/methylseq pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## adapter_trimming

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--clip-r1` | integer |  |  |  |  | `0` | Trim bases from the 5' end of read 1 (or single-end reads). |
| `--clip-r2` | integer |  |  |  |  | `0` | Trim bases from the 5' end of read 2 (paired-end only). |
| `--length-trim` | integer |  |  |  |  |  | Discard reads that become shorter than INT because of either quality or adapter trimming. |
| `--nextseq-trim` | integer |  |  |  |  | `0` | Trim bases below this quality value from the 3' end of the read, ignoring high-quality G bases |
| `--skip-trimming-presets` | boolean |  |  |  |  |  | Skip presetting trimming parameters entirely |
| `--three-prime-clip-r1` | integer |  |  |  |  | `0` | Trim bases from the 3' end of read 1 AFTER adapter/quality trimming. |
| `--three-prime-clip-r2` | integer |  |  |  |  | `0` | Trim bases from the 3' end of read 2 AFTER adapter/quality trimming |

## alignment_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--aligner` | string | yes |  | `bismark`, `bismark_hisat`, `bwameth`, `bwamem` |  | `bismark` | Alignment tool to use. |
| `--use-mem2` | boolean |  |  |  |  |  | Use BWA-MEM2 algorithm for BWA-Meth indexing and alignment. |

## bismark_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--comprehensive` | boolean |  |  |  |  |  | Merges methylation calls for every strand into a single, context dependent file. |
| `--cytosine-report` | boolean |  |  |  |  |  | Output stranded cytosine report, following Bismark's bismark_methylation_extractor step. |
| `--ignore-3prime-r1` | integer |  |  |  |  | `0` | Ignore methylation in last n bases of 3' end of R1 |
| `--ignore-3prime-r2` | integer |  |  |  |  | `2` | Ignore methylation in last n bases of 3' end of R2 |
| `--ignore-r1` | integer |  |  |  |  | `0` | Ignore methylation in first n bases of 5' end of R1 |
| `--ignore-r2` | integer |  |  |  |  | `2` | Ignore methylation in first n bases of 5' end of R2 |
| `--known-splices` | string (file path) |  |  |  | matches `^\S+\.gtf(\.gz)?$` |  | Supply a .gtf file containing known splice sites (bismark_hisat only). |
| `--local-alignment` | boolean |  |  |  |  |  | Allow soft-clipping of reads (potentially useful for single-cell experiments). |
| `--maxins` | integer |  |  |  |  |  | The maximum insert size for valid paired-end alignments. |
| `--meth-cutoff` | integer |  |  |  |  |  | Specify a minimum read coverage to report a methylation call |
| `--minins` | integer |  |  |  |  |  | The minimum insert size for valid paired-end alignments. |
| `--no-overlap` | boolean |  |  |  |  | `true` | Ignore read 2 methylation when it overlaps read 1 |
| `--nomeseq` | boolean |  |  |  |  |  | Sample is NOMe-seq or NMT-seq. Runs coverage2cytosine. |
| `--non-directional` | boolean |  |  |  |  |  | Run alignment against all four possible strands. |
| `--num-mismatches` | number |  |  |  |  | `0.6` | 0.6 will allow a penalty of bp * -0.6 - for 100bp reads (bismark default is 0.2) |
| `--relax-mismatches` | boolean |  |  |  |  |  | Turn on to relax stringency for alignment (set allowed penalty with --num_mismatches). |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--hook-url` | string |  | yes |  |  |  | Incoming hook URL for messaging service |
| `--max-multiqc-email-size` | string |  | yes |  | matches `^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$` | `25.MB` | File size limit when attaching MultiQC reports to summary emails. |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--pipelines-testdata-base-path` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/test-datasets/methylseq/` | Base URL or local path to location of pipeline test dataset files |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | `copy` | Method used to save pipeline results to output directory. |
| `--show-hidden` | boolean |  |  |  |  |  | Display hidden parameters in the help message (only works when --help or --help_full are provided). |
| `--trace-report-suffix` | string |  | yes |  |  |  | Suffix to add to the trace report filename. Default is the date and time in the format yyyy-MM-dd_HH-mm-ss. |
| `--validate-params` | boolean |  | yes |  |  | `true` | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  | matches `^\S+\.csv$` |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/configs/master` | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | `master` | Git commit id for Institutional configs. |

## methyldackel_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--all-contexts` | boolean |  |  |  |  |  | Call methylation in all three CpG, CHG and CHH contexts. |
| `--ignore-flags` | boolean |  |  |  |  |  | MethylDackel - ignore SAM flags |
| `--merge-context` | boolean |  |  |  |  |  | Merges methylation metrics of the Cytosines in a given context. |
| `--methyl-kit` | boolean |  |  |  |  |  | Save files for use with methylKit |
| `--min-depth` | integer |  |  |  |  | `0` | Specify a minimum read coverage for MethylDackel to report a methylation call. |

## qualimap_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bamqc-regions-file` | string (file path) |  |  |  | matches `^\S+\.gff\|\.bed(\.gz)?$` |  | A GFF or BED file containing the target regions which will be passed to Qualimap/Bamqc. |

## rastair_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--trim-OB` | string |  |  |  |  | `0,0,10,0` | Nucleotides to exclude from methylation calling on Original Bottom (strand) reads, following this pattern: R1 start, R1 end, R2 start, R2 end |
| `--trim-OT` | string |  |  |  |  | `0,0,10,0` | Nucleotides to exclude from methylation calling on Original Top (strand) reads, following this pattern: R1 start, R1 end, R2 start, R2 end |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bismark-index` | string (file or directory path) |  |  |  |  |  | Path to a directory containing a Bismark reference index. |
| `--bwamem-index` | string (directory path) |  |  |  |  |  | Path to the BWA-MEM index filename base |
| `--bwameth-index` | string (file or directory path) |  |  |  |  |  | bwameth index filename base |
| `--fasta` | string (file path) |  |  |  | matches `^\S+\.fn?a(sta)?(\.gz)?$` |  | Path to FASTA genome file |
| `--fasta-index` | string (file path) |  |  |  | matches `^\S+\.fn?a(sta)?.fai$` |  | Path to Fasta index file. |
| `--genome` | string |  |  |  |  |  | Name of iGenomes reference. |
| `--igenomes-base` | string (directory path) |  | yes |  |  | `s3://ngi-igenomes/igenomes/` | The base path to the igenomes reference files |
| `--igenomes-ignore` | boolean |  | yes |  |  |  | Do not load the iGenomes reference config. |

## run_pipeline_steps

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--run-preseq` | boolean |  |  |  |  |  | Run preseq/lcextrap tool |
| `--run-qualimap` | boolean |  |  |  |  |  | Run qualimap/bamqc tool |
| `--run-targeted-sequencing` | boolean |  |  |  |  |  | Run advanced analysis for targeted methylation kits with enrichment of specific regions |

## save_intermediate_files

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--save-align-intermeds` | boolean |  |  |  |  |  | Save aligned intermediates to results directory |
| `--save-reference` | boolean |  |  |  |  |  | Save reference(s) to results directory |
| `--save-trimmed` | boolean |  |  |  |  |  | Save trimmed reads to results directory. |
| `--unmapped` | boolean |  |  |  |  |  | Bismark only - Save unmapped reads to FastQ files |

## skip_pipeline_steps

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--skip-deduplication` | boolean |  |  |  |  |  | Skip deduplication step after alignment. |
| `--skip-fastqc` | boolean |  |  |  |  |  | Skip FastQC |
| `--skip-multiqc` | boolean |  |  |  |  |  | Skip MultiQC |
| `--skip-trimming` | boolean |  |  |  |  |  | Skip read trimming. |

## special_library_types

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--accel` | boolean |  |  |  |  |  | Trimming preset for the Accel kit. |
| `--em-seq` | boolean |  |  |  |  |  | Preset for EM-seq libraries. |
| `--pbat` | boolean |  |  |  |  |  | Preset for working with PBAT libraries. |
| `--rrbs` | boolean |  |  |  |  |  | Turn on if dealing with MspI digested material. |
| `--single-cell` | boolean |  |  |  |  |  | Trimming preset for single-cell bisulfite libraries. |
| `--slamseq` | boolean |  |  |  |  |  | Run bismark in SLAM-seq mode. |
| `--taps` | boolean |  |  |  |  |  | Preset for working with TET-assisted pyridine borane sequencing (TAPS) libraries. |
| `--zymo` | boolean |  |  |  |  |  | Trimming preset for the Zymo kit. |

## targeted_sequencing_analysis_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--collecthsmetrics` | boolean |  |  |  |  |  | Run Picard CollectHsMetrics in the targeted analysis |
| `--target-regions-file` | string (file path) |  |  |  | matches `^\S+\|\.bed(\.gz)?$` |  | A BED file containing the target regions |

<!-- Generated from nf-core/methylseq@5aa56467a85a5e2d6795ea72dfa5a5f0c9babc23. Do not edit by hand. -->
