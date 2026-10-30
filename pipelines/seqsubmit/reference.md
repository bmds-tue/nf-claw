---
name: seqsubmit
version: 1.0.0
commit: 717fd19e7a40099fbe5362ec48ab8ec21f62d3f8
---

# seqsubmit — full parameter reference

nf-core/seqsubmit pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

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

## genome_evaluation_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--checkm2-db` | string (file path) |  |  |  |  |  | Path to pre-downloaded CheckM2 database. If omitted, downloads the version set by `--checkm2_db_download_id` |
| `--checkm2-db-download-id` | integer |  |  |  |  | `14897628` | Zenodo ID for CheckM2 database download |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  | matches `^\S+\.(csv\|tsv\|yaml\|yml\|json)$` |  | Path to samplesheet describing the data to be submitted (supported formats: csv, tsv, yaml, yml, json). Columns/fields depend on the pipeline mode |
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

## pipeline_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--centre-name` | string | yes |  |  |  |  | Name of the submitter's organisation (mandatory for broker accounts). |
| `--is-private` | boolean |  |  |  |  | `false` | Use that flag if you are referencing private data accessions in the samplesheet |
| `--mode` | string | yes |  | `mags`, `bins`, `metagenomic_assemblies`, `reads` |  |  | Type of the data to be submitted |
| `--release-date` | string |  |  |  | matches `^\d{4}-\d{2}-\d{2}$` |  | Date (YYYY-MM-DD) until which the newly created study stays private in ENA. |
| `--study-metadata` | string (file path) |  |  |  |  |  | Path to a file (JSON, CSV, or TSV) with metadata for registering a new ENA study. Required if --submission_study is not set. |
| `--submission-study` | string |  |  |  |  |  | ENA study accession (PRJ/ERP) to submit the data to |
| `--test-upload` | boolean |  |  |  |  | `true` | Upload to ENA TEST server instead of LIVE server |
| `--upload-tpa` | boolean |  |  |  |  | `false` | Mark the assemblies as a Third PArty (TPA) |
| `--webincli-mode` | string |  |  | `submit`, `validate` |  | `submit` | Webin-CLI mode for ENA interaction: `submit` uploads data, `validate` performs validation only. |

## rna_detection_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--rrna-limit` | number |  |  |  |  | `80` | Minimum percentage of 16S, 23S, and 5S rRNA gene length recovered to count the gene as present. |
| `--trna-limit` | number |  |  |  |  | `18` | Minimum number of tRNA genes detected to count tRNA as present. This value is defined by the MISAG/MIMAG standard and must not be modified. |

## taxonomy_assignment_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--cat-db` | string (file path) |  |  |  |  |  | Path to local CAT_pack DB |

<!-- Generated from nf-core/seqsubmit@717fd19e7a40099fbe5362ec48ab8ec21f62d3f8. Do not edit by hand. -->
