---
name: smrnaseq
version: 2.4.1
commit: cb0af579b24cb8d5a3accd87b2f14ea93fe04832
---

# smrnaseq — full parameter reference

nf-core/smrnaseq pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## contamination_filtering

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--cdna` | string (file path) |  |  |  |  |  | Path to the cDNA fasta file to be used as contamination database. |
| `--filter-contamination` | boolean |  |  |  |  |  | Enables the contamination filtering. |
| `--ncrna` | string (file path) |  |  |  |  |  | Path to the ncRNA fasta file to be used as contamination database. |
| `--other-contamination` | string (file path) |  |  |  |  |  | Path to an additional fasta file to be used as contamination database. |
| `--pirna` | string (file path) |  |  |  |  |  | Path to the piRNA fasta file to be used as contamination database. |
| `--rrna` | string (file path) |  |  |  |  |  | Path to the rRNA fasta file to be used as contamination database. |
| `--trna` | string (file path) |  |  |  |  |  | Path to the tRNA fasta file to be used as contamination database. |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--hook-url` | string |  | yes |  |  |  | Incoming hook URL for messaging service |
| `--max-multiqc-email-size` | string |  | yes |  | matches ^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$ | 25.MB | File size limit when attaching MultiQC reports to summary emails. |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--pipelines-testdata-base-path` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/test-datasets/ | Base URL or local path to location of pipeline test dataset files |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | copy | Method used to save pipeline results to output directory. |
| `--show-hidden` | boolean |  |  |  |  |  | Display hidden parameters in the help message (only works when --help or --help_full are provided). |
| `--trace-report-suffix` | string |  | yes |  |  |  | Suffix to add to the trace report filename. Default is the date and time in the format yyyy-MM-dd_HH-mm-ss. |
| `--validate-params` | boolean |  | yes |  |  | true | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  | matches ^\S+\.csv$ |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--save-intermediates` | boolean |  |  |  |  |  | Save all intermediate files (e.g. fastq, bams) of all steps of the pipeline to output directory |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/configs/master | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | master | Git commit id for Institutional configs. |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bowtie-index` | string |  |  |  |  |  | Path to a Bowtie 1 index directory |
| `--fasta` | string (file path) |  |  |  | matches ^\S+\.fn?a(sta)?(\.gz)?$ |  | Path to FASTA genome file. |
| `--genome` | string |  |  |  |  |  | Name of iGenomes reference. |
| `--hairpin` | string |  |  |  |  | https://github.com/nf-core/test-datasets/raw/smrnaseq/miRBase/hairpin.fa | Path to FASTA file with miRNAs precursors. |
| `--igenomes-base` | string (directory path) |  |  |  |  | s3://ngi-igenomes/igenomes/ | Directory / URL base for iGenomes references. |
| `--igenomes-ignore` | boolean |  | yes |  |  |  | Do not load the iGenomes reference config. |
| `--mature` | string |  |  |  |  | https://github.com/nf-core/test-datasets/raw/smrnaseq/miRBase/mature.fa | Path to FASTA file with mature miRNAs. |
| `--mirgenedb` | boolean |  |  |  |  |  | Boolean whether MirGeneDB should be used instead of miRBase |
| `--mirgenedb-gff` | string |  |  |  |  |  | GFF/GTF file with coordinates positions of precursor and miRNAs. |
| `--mirgenedb-hairpin` | string |  |  |  |  |  | Path to FASTA file with miRNAs precursors. |
| `--mirgenedb-mature` | string |  |  |  |  |  | Path to FASTA file with MirGeneDB mature miRNAs. |
| `--mirgenedb-species` | string |  |  |  |  |  | Species of MirGeneDB. |
| `--mirna-gtf` | string |  |  |  |  |  | GFF/GTF file with coordinates positions of precursor and miRNAs. |
| `--mirtrace-species` | string |  |  |  |  |  | Species for miRTrace. |
| `--save-reference` | boolean |  |  |  |  |  | Save generated reference genome files to results. |

## skipping_pipeline_steps

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--skip-fastp` | boolean |  |  |  |  |  | Skip FastP |
| `--skip-fastqc` | boolean |  |  |  |  |  | Skip FastQC |
| `--skip-mirdeep` | boolean |  |  |  |  |  | Skip miRDeep |
| `--skip-multiqc` | boolean |  |  |  |  |  | Skip MultiQC |

## trimming_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--clip-r1` | integer |  |  |  |  |  | The number of basepairs to remove from the 5' end of read 1. |
| `--fastp-known-mirna-adapters` | string (file path) |  |  |  |  | ${projectDir}/assets/known_adapters.fa | Fasta with known miRNA adapter sequences for adapter trimming |
| `--fastp-max-length` | integer |  |  |  |  | 100 | Maximum filter length for raw reads. |
| `--fastp-min-length` | integer |  |  |  |  | 17 | Minimum filter length for raw reads. |
| `--min-trimmed-reads` | integer |  |  |  |  | 10 | Minimum number of reads required in input file to use it |
| `--phred-offset` | integer |  |  |  |  | 33 | The PHRED quality offset to be used for any input fastq files. Default is 33, standard Illumina 1.8+ format. |
| `--save-merged` | boolean |  |  |  |  |  | Save merged reads. |
| `--save-trimmed-fail` | boolean |  |  |  |  |  | Save reads failing trimming |
| `--three-prime-adapter` | string |  |  |  |  | AGATCGGAAGAGCACACGTCTGAACTCCAGTCA | Sequencing adapter sequence to use for trimming. |
| `--three-prime-clip-r1` | integer |  |  |  |  |  | The number of basepairs to remove from the 3' end of read 1 AFTER adapter/quality trimming has been performed. |
| `--trim-fastq` | boolean |  |  |  |  | true | Trim FastQ files |

## umi_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--save-umi-intermeds` | boolean |  |  |  |  |  | If this option is specified, intermediate FastQ and BAM files produced by UMI-tools are also saved in the results directory. |
| `--skip-umi-extract-before-dedup` | boolean |  |  |  |  | true | Skip the UMI extraction from the reads before deduplication. Please note, if this parameter is set to false, the reads will be deduplicated solely on insert sequence. UMIs might be extracted after deduplication depending on the set umitools_bc_pattern nevertheless if with_umi is set to True. |
| `--umi-discard-read` | integer |  |  |  |  |  | After UMI barcode extraction discard either R1 or R2 by setting this parameter to 1 or 2, respectively. |
| `--umitools-bc-pattern` | string |  |  |  |  |  | The UMI barcode pattern to use e.g. 'NNNNNN' indicates that the first 6 nucleotides of the read are from the UMI. |
| `--umitools-extract-method` | string |  |  |  |  | string | UMI pattern to use. Can be either 'string' (default) or 'regex'. |
| `--umitools-method` | string |  |  |  |  | dir | UMI grouping method |
| `--with-umi` | boolean |  |  |  |  |  | Enable UMI-based read deduplication. |

<!-- Generated from nf-core/smrnaseq@cb0af579b24cb8d5a3accd87b2f14ea93fe04832. Do not edit by hand. -->
