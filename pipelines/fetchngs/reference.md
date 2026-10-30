---
name: fetchngs
version: 1.13.0
commit: 955c892d80927cee633765e6e390f9cc6b7235c9
---

# fetchngs — full parameter reference

nf-core/fetchngs pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## deprecated_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--force-sratools-download` | boolean |  | yes | `false` |  |  | This parameter has been deprecated. Please use '--download_method sratools' instead. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--show-hidden` | boolean |  |  |  |  |  | Display hidden parameters in the help message (only works when --help or --help_full are provided). |
| `--trace-report-suffix` | string |  | yes |  |  |  | Suffix to add to the trace report filename. Default is the date and time in the format yyyy-MM-dd_HH-mm-ss. |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary, only when pipeline fails. |
| `--modules-testdata-base-path` | string |  | yes |  |  | `s3://ngi-igenomes/testdata/nf-core/modules/` | Base URL or local path to location of modules test dataset files |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--pipelines-testdata-base-path` | string |  | yes |  |  | `s3://ngi-igenomes/testdata/nf-core/pipelines/fetchngs/1.15.0/` | Base URL or local path to location of pipeline test dataset files |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | `copy` | Method used to save pipeline results to output directory. |
| `--validate-params` | boolean |  | yes |  |  | `true` | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--dbgap-key` | string (file path) |  |  |  |  |  | dbGaP repository key. |
| `--download-method` | string |  |  | `aspera`, `fastq-dl`, `ftp`, `sratools` |  | `ftp` | Method to download FastQ files. Available options are 'aspera', 'fastq-dl', 'ftp' or 'sratools'. Default is 'ftp'. |
| `--email` | string |  |  |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary. |
| `--ena-metadata-fields` | string |  |  |  |  |  | Comma-separated list of ENA metadata fields to fetch before downloading data. |
| `--input` | string (file path) | yes |  |  | matches `^\S+\.(csv\|tsv\|txt)$` |  | File containing SRA/ENA/GEO/DDBJ identifiers one per line to download their associated metadata and FastQ files. |
| `--nf-core-pipeline` | string |  |  | `ampliseq`, `atacseq`, `mag`, `metatdenovo`, `rnaseq`, `sarek`, `taxprofiler`, `viralrecon` |  |  | Name of supported nf-core pipeline e.g. 'rnaseq'. A samplesheet for direct use with the pipeline will be created with the appropriate columns. |
| `--nf-core-rnaseq-strandedness` | string |  |  |  |  | `auto` | Value for 'strandedness' entry added to samplesheet created when using '--nf_core_pipeline rnaseq'. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--sample-mapping-fields` | string |  |  |  |  | `experiment_accession,run_accession,sample_accession,experiment_alias,run_alias,sample_alias,experiment_title,sample_title,sample_description` | Comma-separated list of ENA metadata fields used to create a separate 'id_mappings.csv' and 'multiqc_config.yml' with selected fields that can be used to rename samples in general and in MultiQC. |
| `--skip-fastq-download` | boolean |  |  |  |  |  | Only download metadata for public data database ids and don't download the FastQ files. |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/configs/master` | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | `master` | Git commit id for Institutional configs. |

<!-- Generated from nf-core/fetchngs@955c892d80927cee633765e6e390f9cc6b7235c9. Do not edit by hand. -->
