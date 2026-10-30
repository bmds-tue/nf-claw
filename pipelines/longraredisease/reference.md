---
name: longraredisease
version: 1.0.0
commit: f40870fcbcf2e9fc29b623b848487789d487ed4a
---

# longraredisease — full parameter reference

nf-core/longraredisease pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## cnv_calling_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--hificnv-exclude-bed` | string (file path) |  |  |  |  |  | Path to BED file for regions to exclude in HiFiCNV. |
| `--hificnv-expected-cn-bed` | string (file path) |  |  |  |  |  | BED file with expected CNVs for HiFiCNV evaluation. |
| `--spectre-bin-size` | integer |  |  |  |  | `1000` | Spectre bin size |
| `--spectre-blacklist` | string (file path) |  |  |  |  |  | Path to Spectre blacklist BED file. |
| `--spectre-metadata` | string (file path) |  |  |  |  |  | Path to Spectre metadata file. |
| `--spectre-test-clair3-vcf` | string (file path) |  | yes |  |  |  | Path to test Clair3 VCF for Spectre CNV calling. |
| `--spectre-test-fasta-file` | string (file path) |  | yes |  |  |  | Path to test FASTA file for Spectre CNV calling. |
| `--spectre-test-regions-bed` | string (file path) |  | yes |  |  |  | Path to test regions BED file for Spectre CNV calling. |
| `--spectre-test-regions-csi` | string (file path) |  | yes |  |  |  | Path to test regions CSI file for Spectre CNV calling. |
| `--spectre-test-summary-txt` | string (file path) |  | yes |  |  |  | Path to test summary file for Spectre CNV calling. |
| `--use-test-data` | boolean |  |  |  |  | `false` | Use test data for Spectre CNV calling. |

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
| `--outdir` | string (directory path) |  |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/configs/master` | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | `master` | Git commit id for Institutional configs. |

## output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--snf-output` | boolean |  |  |  |  | `true` | Generate SNF output. |
| `--vcf-output` | boolean |  |  |  |  | `true` | Generate VCF output. |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--chromosome-codes` | array |  |  |  |  |  | List of chromosome codes to process. |
| `--fasta-file` | string (file path) | yes |  |  | matches `^\S+\.fn?a(sta)?(\.gz)?$` |  | Path to FASTA genome file. |
| `--genome` | string |  |  |  |  |  | Name of iGenomes reference. |
| `--igenomes-base` | string (directory path) |  | yes |  |  | `s3://ngi-igenomes/igenomes/` | The base path to the igenomes reference files |
| `--igenomes-ignore` | boolean |  | yes |  |  |  | Do not load the iGenomes reference config. |
| `--sniffles-tandem-file` | string (file path) |  |  |  |  |  | Path to tandem repeat BED file for Sniffles. |

## snv_calling_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--annotate-clair3` | boolean |  |  |  |  | `true` | Enable structural variant annotation. |
| `--clair3-min-mq` | integer |  |  |  |  | `10` | Minimum mapping quality for Clair3 to consider an alignment. |
| `--clair3-model` | string |  |  |  |  | `ont` | Clair3 model to use. |
| `--clair3-platform` | string |  |  |  |  | `ont` | Clair3 platform. |
| `--deepvariant-make-examples-extra-args` | string |  |  |  |  | `min_mapping_quality=10` | Extra arguments for DeepVariant make_examples step. |
| `--deepvariant-regions` | string (file path) |  |  |  |  |  | BED file with regions to restrict DeepVariant calling to. |
| `--deepvariant-runtime-report` | boolean |  |  |  |  | `true` | Enable generation of a runtime report for DeepVariant. |
| `--filter-pass-snv` | boolean |  |  |  |  | `true` | Filter PASS variants only in SNV. |
| `--run-deepvariant` | boolean |  |  |  |  | `false` | Run DeepVariant, otherwise runs Clair3. |
| `--snpeff-db` | string |  |  |  |  | `GRCh38.mane.1.2.ensembl` | SnpEff database to use for annotation |

## str_analysis_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--straglr-bed` | string (file path) |  |  |  |  |  | Path to STR BED file. |
| `--trgt-bed` | string (file path) |  |  |  |  |  | Path to STR BED file. |
| `--variant-catalogue` | string (file path) |  |  |  |  |  | Path to variant catalogue JSON file. |

## sv_annotation_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--output-format` | string |  |  | `html`, `tsv` |  | `html` | Output format for SvAnna results. |
| `--run-svanna` | boolean |  |  |  |  | `false` | Enable SV annotation with SvAnna. |
| `--svanna-db` | string (directory path) |  |  |  |  |  | Path to the SvAnna database directory. |

## sv_calling_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--annotate-sv` | boolean |  |  |  |  | `true` | Enable structural variant annotation. |
| `--annotate-svim` | boolean |  |  |  |  | `false` | Enable structural variant annotation. |
| `--annotsv-annotations` | string (directory path) |  |  |  |  |  | Path to AnnotSV annotations directory. |
| `--coverage-bed` | string (file path) |  |  |  |  |  | BED file with coverage information for SV filtering. |
| `--cutesv-min-mapq` | integer |  |  |  |  | `20` | Minimum mapping quality for cuteSV. |
| `--downsample-sv` | boolean |  |  |  |  | `false` | Enable SV filtering by coverage. |
| `--filter-pass-sv` | boolean |  |  |  |  | `true` | Only consider PASS variants. |
| `--merge-sv` | boolean |  |  |  |  | `true` | Merge SV calls from multiple callers. |
| `--min-caller-support` | integer |  |  |  |  | `2` | This is set for jasmine - minimum number of callers supporting the variant |
| `--min-read-support` | string |  |  |  |  | `auto` | Minimum read support for SVs. |
| `--min-read-support-limit` | integer |  |  |  |  | `2` | Minimum read support limit. |
| `--rankfiltering` | string |  |  |  |  | `1-5,NA` | Rank filtering criteria |
| `--run-svim` | boolean |  |  |  |  | `true` | Set off variant caller - SVIM |
| `--sniffles-min-mapq` | integer |  |  |  |  | `20` | Minimum mapping quality for Sniffles. |
| `--svim-min-mapq` | integer |  |  |  |  | `20` | Minimum mapping quality for SVIM. |

## workflow_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--annotate-unified-vcf` | boolean |  |  |  |  | `true` | Enable annotation of unified VCF |
| `--cnv` | boolean |  |  |  |  | `false` | Enable CNV calling with HiFiCNV if cnv_spectre is false. |
| `--filter-targets` | boolean |  |  |  |  | `false` | Enable filtering of alignments to target regions. |
| `--generate-bam-stats` | boolean |  |  |  |  | `true` | Generate BAM statistics using samtools. |
| `--generate-coverage-report` | boolean |  |  |  |  | `true` | Generate coverage statistics. |
| `--haplotag-bam` | boolean |  |  |  |  | `true` | Enable haplotagging of BAM files. |
| `--input-type` | string |  |  | `ubam`, `fastq`, `bam` |  | `ubam` | Input file type. |
| `--methyl` | boolean |  |  |  |  | `false` | Enable methylation calling. |
| `--minimap2-model` | string |  |  |  |  |  | Minimap2 model for alignment. |
| `--modify-str-calls` | boolean |  |  |  |  | `true` | Enable modification of STR calls |
| `--qc` | boolean |  |  |  |  | `false` | Enable quality control analysis. |
| `--sequencing-platform` | string |  |  |  |  | `ont` | Sequencing platform (e.g. 'ont', 'hifi', 'pacbio'). |
| `--snv` | boolean |  |  |  |  | `true` | Enable single nucleotide variant calling. |
| `--str` | boolean |  |  |  |  | `true` | Enable short tandem repeat analysis. |
| `--sv` | boolean |  |  |  |  | `true` | Enable structural variant calling. |
| `--targets-bed` | string (file path) |  |  |  |  |  | BED file with target regions for filtering. |
| `--trio-analysis` | boolean |  |  |  |  | `false` | Enable trio analysis for SNV calling and phasing. |
| `--unify-vcf` | boolean |  |  |  |  | `true` | Enable VCF unification |
| `--use-winnowmap` | boolean |  |  |  |  | `false` | Use Winnowmap for alignment instead of Minimap2 |
| `--winnowmap-kmers` | string (file path) |  |  |  |  |  | Path to repetitive k-mer file for Winnowmap |
| `--winnowmap-model` | string |  |  |  |  |  | Winnowmap model for alignment. |

<!-- Generated from nf-core/longraredisease@f40870fcbcf2e9fc29b623b848487789d487ed4a. Do not edit by hand. -->
