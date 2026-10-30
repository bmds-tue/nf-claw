---
name: scnanoseq
version: 1.3.0
commit: 83d55ea87eb625a3564d40124fb1fa54c4c63f9e
---

# scnanoseq — full parameter reference

nf-core/scnanoseq pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## analysis_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--quantifier` | string | yes |  |  | matches `^(oarfish\|isoquant)(,(oarfish\|isoquant))*$` |  | Provide a comma-delimited options of quantifiers for the pipeline to use. Available tools: isoquant, oarfish |
| `--retain-introns` | boolean |  |  |  |  | `true` | Indicate whether to include introns in the count matrices |

## cell_barcode_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--barcode-format` | string | yes |  | `10X_3v3`, `10X_3v4`, `10X_5v2`, `10X_5v3` |  |  | Specify the format for the barcode+umi. This parameter also defines a default barcode whitelist for the pipeline to use for barcode calling, this can be overridden with the 'whitelist' parameter. |
| `--dedup-tool` | string | yes |  | `umitools`, `picard` |  | `umitools` | Specify which tool to be used for deduplication (Options: picard, umitools) |
| `--skip-blaze-demux` | boolean |  |  |  |  | `true` | Do not perform the demultiplexing step in BLAZE (conserves time and disk space). |
| `--whitelist` | string (file path) |  |  |  |  |  | User-provided file containing a list of cellular barcodes. Using this parameter will override the default whitelists provided by the pipeline and use the user-provided one instead. |

## fastq_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--split-amount` | integer |  |  |  |  | `0` | The number of lines to split the FASTQ into. |

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
| `--pipelines-testdata-base-path` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/test-datasets/` | Base URL or local path to location of pipeline test dataset files |
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

## mapping

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--kmer-size` | integer |  |  |  |  | `14` | Minimizer k-mer length. |
| `--save-genome-secondary-alignment` | boolean |  |  |  |  |  | Save the secondary alignments when aligning to the genome |
| `--save-transcript-secondary-alignment` | boolean |  |  |  |  | `true` | Save the secondary alignments when aligning to the transcriptome |
| `--stranded` | string |  |  | `None`, `reverse`, `forward` |  |  | Library strandness option. |

## process_skipping_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--skip-bam-nanocomp` | boolean |  |  |  |  | `true` | Skip NanoComp from BAM file(s). |
| `--skip-dedup` | boolean |  |  |  |  |  | Skip umi dedup. |
| `--skip-fastq-nanocomp` | boolean |  |  |  |  |  | Skip NanoComp from FASTQ file(s). |
| `--skip-fastqc` | boolean |  |  |  |  |  | Skip FastQC. |
| `--skip-multiqc` | boolean |  |  |  |  |  | Skip MultiQC. |
| `--skip-nanoplot` | boolean |  |  |  |  |  | Skip Nanoplot. |
| `--skip-qc` | boolean |  |  |  |  |  | Skip all QC. |
| `--skip-rseqc` | boolean |  |  |  |  |  | Skip RSeQC. |
| `--skip-save-minimap2-index` | boolean |  |  |  |  |  | Skip saving minimap2 index. |
| `--skip-seurat` | boolean |  |  |  |  |  | Skip Seurat QC. |
| `--skip-toulligqc` | boolean |  |  |  |  |  | Skip ToulligQC. |

## read_trimming_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--min-length` | integer |  |  |  |  | `1` | Choose minimum read length. |
| `--min-q-score` | integer |  |  |  |  | `10` | Choose minimum average read quality score. |
| `--skip-trimming` | boolean |  |  |  |  |  | Skip quality trimming step. |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--fasta-delimiter` | string |  |  |  |  |  | This is the delimiter the FASTA uses in the sequence identifier to separate the string. |
| `--genome` | string |  |  |  |  |  | Name of iGenomes reference. |
| `--genome-fasta` | string (file path) |  |  |  | matches `^\S+\.fn?a(sta)?(\.gz\|\.zip)?$` |  | Path to genome FASTA file. |
| `--gtf` | string (file path) | yes |  |  | matches `^\S+\.gtf(\.gz\|\.zip)?$` |  | Path to GTF file. |
| `--igenomes-base` | string (directory path) |  | yes |  |  | `s3://ngi-igenomes/igenomes/` | The base path to the igenomes reference files |
| `--igenomes-ignore` | boolean |  | yes |  |  | `true` | Do not load the iGenomes reference config. |
| `--transcript-fasta` | string (file path) |  |  |  | matches `^\S+\.fn?a(sta)?(\.gz\|\.zip)?$` |  | Path to transcriptome FASTA file. |

<!-- Generated from nf-core/scnanoseq@83d55ea87eb625a3564d40124fb1fa54c4c63f9e. Do not edit by hand. -->
