---
name: scrnaseq
version: 4.2.0
commit: 3fc17b4f971a89e47c88337de71d0e777ffad8cc
---

# scrnaseq — full parameter reference

nf-core/scrnaseq pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## cellranger_multi_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--cellranger-multi-barcodes` | string (file path) |  |  |  |  |  | Additional samplesheet to provide information about multiplexed samples. See the 'Usage' section for more details. |
| `--cellranger-vdj-index` | string (file or directory path) |  |  |  |  |  | Specify a pre-built Cell Ranger index for VDJ analysis. |
| `--fb-reference` | string (file path) |  |  |  |  |  | Provide a reference file for feature barcoding (e.g. antibody measurements). Please refer to the [Cell Ranger Feature Reference documentation](https://www.10xgenomics.com/support/software/cell-ranger/latest/analysis/inputs/cr-feature-ref-csv) for more details. |
| `--gex-barcode-sample-assignment` | string (file path) |  |  |  |  |  | This is only necessary to override Cell Ranger's default cell calling and tag calling steps. In most cases, you need to only use the `cellranger_multi_barcodes` parameter. Please refer to the [10x documentation](https://www.10xgenomics.com/support/software/cell-ranger/latest/analysis/running-pipelines/cr-3p-multi#barcode-asst) for more information about this file. |
| `--gex-cmo-set` | string (file path) |  |  |  |  |  | Provide a Cell Multiplexing Oligo (CMO) description file when working with multiplexed samples. This is only necessary if you with to override Cell Ranger's default CMO-set. Please refer to the [10x documentation](https://www.10xgenomics.com/support/software/cell-ranger/latest/analysis/running-pipelines/cr-3p-multi#cmo-ref) about CMO references for more details. |
| `--gex-frna-probe-set` | string (file path) |  |  |  |  |  | Provide a probe set for fixed RNA-seq profiling (used with FFPE samples). Please refer to the [10x documentation about probesets](https://www.10xgenomics.com/support/single-cell-gene-expression-flex/documentation/steps/probe-sets/chromium-frp-probe-set-files) for more details. |
| `--gex-reference-version` | string |  |  |  |  |  | Reference version (e.g. GRCh38, GRCm39). Required if `gex_frna_probe_set` is used and `cellranger_index` is not set. Must match the genome version in the `gex_frna_probe_set` file. |
| `--gex-target-panel` | string (file path) |  |  |  |  |  | Provide a panel description for targeted sequencing. |
| `--skip-cellrangermulti-vdjref` | boolean |  |  |  |  |  | Skip mkvdjref if not using VDJ data with cellranger/multi |
| `--vdj-inner-enrichment-primers` | string (file path) |  |  |  |  |  | This argument takes a .txt file containing primer sequences that were used to enrich cDNA for V(D)J sequences. This is only necessary if you with to override Cell Ranger's defaults. |

## cellranger_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--cellranger-index` | string (file or directory path) |  |  |  |  |  | Specify a pre-calculated cellranger index. Readily prepared indexes can be obtained from the 10x Genomics website. Provide the base directory of the index (e.g., '/PATH/TO/10X_REF/refdata-gex-GRCh38-2024-A/') |
| `--skip-cellranger-renaming` | boolean |  |  |  |  |  | Should it skip the automatic renaming included in cellranger-related modules? |

## cellrangerarc_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--cellrangerarc-config` | string |  |  |  |  |  | Specify a config file to create the cellranger-arc index. |
| `--cellrangerarc-reference` | string |  |  |  |  |  | Specify the genome reference name used in the config file to create a cellranger-arc index. |
| `--motifs` | string |  |  |  |  |  | Specify a motif file to create a cellranger-arc index. Can be taken, e.g., from the JASPAR database. |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
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

## kallisto_bus_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--kallisto-index` | string (file or directory path) |  |  |  |  |  | Specify a path to the precomputed Kallisto index. |
| `--kb-t1c` | string (file path) |  |  |  |  |  | Specify a path to the cDNA transcripts-to-capture. |
| `--kb-t2c` | string (file path) |  |  |  |  |  | Specify a path to the intron transcripts-to-capture. |
| `--kb-workflow` | string |  |  | `standard`, `lamanno`, `nac` |  | `standard` | Type of workflow. Use `nac` for an index type that can quantify nascent and mature RNA. Use `lamanno` for RNA velocity based on La Manno et al. 2018 logic. (default: standard) |

## mandatory_arguments

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--aligner` | string |  |  | `kallisto`, `star`, `simpleaf`, `cellranger`, `cellrangerarc`, `cellrangermulti` |  | `simpleaf` | Name of the tool to use for scRNA (pseudo-) alignment. |
| `--barcode-whitelist` | string (file path) |  |  |  |  |  | If not using the 10X Genomics platform, a custom barcode whitelist can be used with `--barcode_whitelist`. |
| `--protocol` | string |  |  |  |  | `auto` | The protocol that was used to generate the single cell data, e.g. 10x Genomics v2 Chemistry. Can be 'auto' (cellranger only), '10XV1', '10XV2', '10XV3', '10XV4', or any other protocol string that will get directly passed the respective aligner. |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--fasta` | string (file path) |  |  |  | matches `^\S+\.fn?a(sta)?(\.gz)?$` |  | Path to FASTA genome file. |
| `--genome` | string |  |  |  |  |  | Name of iGenomes reference. |
| `--gtf` | string (file path) |  |  |  |  |  | Reference GTF annotation file |
| `--igenomes-base` | string (directory path) |  | yes |  |  | `s3://ngi-igenomes/igenomes/` | Directory / URL base for iGenomes references. |
| `--igenomes-ignore` | boolean |  | yes |  |  |  | Do not load the iGenomes reference config. |
| `--save-align-intermeds` | boolean |  |  |  |  |  | Specify this parameter to save the intermediate alignment files (STAR, CellRanger) to the results. |
| `--save-reference` | boolean |  |  |  |  |  | Specify this parameter to save the indices created (STAR, Kallisto, Simpleaf) to the results. |
| `--transcript-fasta` | string (file path) |  |  |  |  |  | A cDNA FASTA file |
| `--txp2gene` | string (file path) |  |  |  |  |  | Path to transcript to gene mapping file. This allows the specification of a transcript to gene mapping file for Kallisto/BUS and Alevin-fry. |

## simpleaf_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--qcatch-n-partitions` | integer |  |  |  |  |  | Number of partitions (max barcodes) for QCatch's empty_drops step. |
| `--remove-doublets` | boolean |  |  |  |  |  | Enable doublet detection and removal using Scrublet via QCatch. |
| `--simpleaf-index` | string (file or directory path) |  |  |  |  |  | Path to pre-built Simpleaf index. |
| `--simpleaf-umi-resolution` | string |  |  | `cr-like`, `cr-like-em`, `parsimony`, `parsimony-em`, `parsimony-gene`, `parsimony-gene-em` |  | `cr-like` | UMI resolution strategy to deduplicate UMIs. |

## skip_tools

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--skip-cellbender` | boolean |  |  |  |  |  | Skip cellbender empty drops filter subworkflow |
| `--skip-emptydrops` | boolean |  |  |  | deprecated |  |  |
| `--skip-fastqc` | boolean |  |  |  |  |  | Skip FastQC |
| `--skip-multiqc` | boolean |  |  |  |  |  | Skip MultiQC Report |
| `--skip-qcatch` | boolean |  |  |  |  |  | Skip qcatch QC for simpleaf aligner |

## starsolo_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--seq-center` | string |  |  |  |  |  | Name of sequencing center for BAM read group tag. |
| `--star-feature` | string |  |  | `Gene`, `GeneFull`, `Gene Velocyto` |  | `Gene` | Quantification type of different transcriptomic feature. Use `GeneFull` on pre-mRNA count for single-nucleus RNA-seq reads. Use `Gene Velocyto` to generate RNA velocity matrix. |
| `--star-ignore-sjdbgtf` | string |  |  |  |  |  | Ignore the SJDB GTF file. |
| `--star-index` | string (file or directory path) |  |  |  |  |  | Specify a path to the precomputed STAR index. |

<!-- Generated from nf-core/scrnaseq@3fc17b4f971a89e47c88337de71d0e777ffad8cc. Do not edit by hand. -->
