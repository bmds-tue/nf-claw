---
name: callingcards
version: 1.0.0
commit: 20b66e785a822028eaa125583aad0747d55bba61
---

# callingcards — full parameter reference

nf-core/callingcards pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## alignment_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--aligner` | string |  |  | `bwa`, `bwamem2`, `bowtie`, `bowtie2` |  | `bwamem2` | Choose one of the configured aligners. Defaults to bwamem2. |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean |  | yes |  |  |  | Display help text. |
| `--hook-url` | string |  | yes |  |  |  | Incoming hook URL for messaging service |
| `--max-multiqc-email-size` | string |  | yes |  | matches `^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$` | `25.MB` | File size limit when attaching MultiQC reports to summary emails. |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--pipelines-testdata-base-path` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/test-datasets/` | Base URL or local path to location of pipeline test dataset files |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | `copy` | Method used to save pipeline results to output directory. |
| `--validate-params` | boolean |  | yes |  |  | `true` | Boolean whether to validate parameters against the schema at runtime |
| `--validationFailUnrecognisedParams` | boolean |  | yes |  |  |  | Validation of parameters fails when an unrecognised parameter is found. |
| `--validationLenientMode` | boolean |  | yes |  |  |  | Validation of parameters in lenient more. |
| `--validationShowHiddenParams` | boolean |  | yes |  |  |  | Show all params when using `--help` |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## hops_counting_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--min-mapq` | integer |  |  |  |  | `10` | Values with less than or equal to this mapq value will not be counted as transpositions. Defaults to 10 |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--datatype` | string | yes |  | `yeast`, `mammals` |  |  | This determines which workflow to run based on the organism and method from which the data originates. Current options are 'yeast' and 'mammals' |
| `--email` | string |  | yes |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  | matches `^\S+\.csv$` |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--multiqc-title` | string |  | yes |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--save-alignment-intermediate` | boolean |  | yes |  |  |  | set to true to save intermediate files form the ALIGN step, eg un-indexed and unsorted bam files |
| `--save-genome-intermediate` | boolean |  | yes |  |  |  | Set to true to save intermediate files from the PREPARE_GENOME step, eg genome indicies for a given aligner |
| `--save-sequence-intermediate` | boolean |  | yes |  |  |  | Set to true to save intermediate files from the PREPARE_READS step, eg chunked and demultiplexed fastq files |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/configs/master` | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | `master` | Git commit id for Institutional configs. |

## max_job_request_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--max-cpus` | integer |  | yes |  |  | `16` | Maximum number of CPUs that can be requested for any single job. |
| `--max-memory` | string |  | yes |  | matches `^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$` | `128.GB` | Maximum amount of memory that can be requested for any single job. |
| `--max-time` | string |  | yes |  | matches `^(\d+\.?\s*(s\|m\|h\|d\|day)\s*)+$` | `240.h` | Maximum amount of time that can be requested for any single job. |

## qc_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--rseqc-modules` | string |  | yes |  |  | `read_distribution` | Specify the RSeQC modules to run. |

## read_processing_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--gzip-concatenated-fastq` | boolean |  | yes |  |  |  | Set to true to gzip fastq files after concatenating (assuming the fastq have been split -- see split_fastq_chunk_size). Default is false, and generally houl should not need to change this as the concat fastqs are intermediate files, easier for downstream processes to use unzipped, and will be deleted when you delete th work directory. |
| `--r1-bc-pattern` | string |  |  |  |  |  | UMITools compliant read 1 barcode pattern. See UMITools documentation |
| `--r1-crop` | integer |  |  |  |  |  | If reads are single_end, this option allows the user to crop the R1 read. This occurs after trimming |
| `--r2-bc-pattern` | string |  |  |  |  |  | UMITools compliant read 2 barcode pattern. See UMITools documentation |
| `--split-fastq-by-part` | integer |  |  |  |  | `10` | split_fastq_by_size or split_fastq_by_part may be set, but not both at the same time. These parameters control how many parts the input fastq files are split into for parallel processing on a cluster. See seqkit split2 for more information. By default, split_fastq_by_part is set to 10, which will split every fastq file into 10 parts. If you wish to use split_fastq_by_size, set split_fastq_by_part to null to nullify the default value. |
| `--split-fastq-by-size` | integer |  |  |  |  |  | split_fastq_by_size or split_fastq_by_part may be set, but not both at the same time. These parameters control how many parts the input fastq files are split into for parallel processing on a cluster. See seqkit split2 for more information. By default, split_fastq_by_part is set to 10, which will split every fastq file into 10 parts. If you wish to use split_fastq_by_size, set split_fastq_by_part to null to nullify the default value. |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--additional-fasta` | string (file path) |  |  |  | matches `^\S+\.fn?a(sta)?(\.gz)?$` |  | Additional sequences which will be appended to the genomic fasta file after masking |
| `--bowtie2-index` | string (directory path) |  | yes |  |  |  | path to the bowtie2 index. only used if aligner is bowtie2. if the aligner is bowtie2 and this is not provided, the index is created in the pipeline |
| `--bowtie-index` | string (directory path) |  | yes |  |  |  | path to the bowtie index. only used if aligner is bowtie. if the aligner is bowtie and this is not provided, the index is created in the pipeline |
| `--bwa-index` | string (directory path) |  | yes |  |  |  | path to the bwaaln index. only used if aligner is bwaaln. if the aligner is bwaaln and this is not provided, the index is created in the pipeline |
| `--bwamem2-index` | string (directory path) |  | yes |  |  |  | path to the bwamem2 index. only used if aligner is bwamem2. if the aligner is bwamem2 and this is not provided, the index is created in the pipeline |
| `--fasta` | string (file path) |  |  |  | matches `^\S+\.fn?a(sta)?(\.gz)?$` |  | Path to FASTA genome file. |
| `--fasta-index` | string (file path) |  | yes |  | matches `^\S+\.fai$` |  | Path to FASTA genome file. |
| `--genome` | string |  |  |  |  |  | Name of iGenomes reference. |
| `--gtf` | string |  |  |  |  |  | Path to GTF annotation file. |
| `--igenomes-ignore` | boolean |  | yes |  |  |  | Do not load the iGenomes reference config. |
| `--regions-mask` | string (file path) |  |  |  | matches `^\S+\.bed$` |  | A bed file which specifies regions to hard mask in genome fasta |

<!-- Generated from nf-core/callingcards@20b66e785a822028eaa125583aad0747d55bba61. Do not edit by hand. -->
