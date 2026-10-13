---
name: metapep
version: 1.0.0
commit: 84feafc9476978c2a1b84849871a553cffd9762a
---

# metapep — full parameter reference

nf-core/metapep pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary, only when pipeline fails. |
| `--hook-url` | string |  | yes |  |  |  | Incoming hook URL for messaging service |
| `--max-multiqc-email-size` | string |  | yes |  | matches ^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$ | 25.MB | File size limit when attaching MultiQC reports to summary emails. |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--pipelines-testdata-base-path` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/test-datasets/ | Base URL or local path to location of pipeline test dataset files |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | copy | Method used to save pipeline results to output directory. |
| `--validate-params` | boolean |  | yes |  |  | true | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--input` | string (file path) |  |  |  | matches ^\S+\.csv$ |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/configs/master | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | master | Git commit id for Institutional configs. |
| `--igenomes-ignore` | boolean |  | yes |  |  | true |  |

## pipeline_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--allow-inconsistent-pep-lengths` | boolean |  | yes |  |  |  | Only takes effect for `pred_method 'syfpeithi'`. Allow all peptide lengths within the range of `min_pep_len` to `max_pep_len` without reducing them to the matching allele models. |
| `--downstream-chunk-size` | integer |  |  |  | ≥ 1 | 7500000 | Maximum chunk size (#epitope predictions) for processing of downstream visualisations. |
| `--hide-pvalue` | boolean |  |  |  |  |  | Do not display mean comparison p-values in boxplots. |
| `--max-pep-len` | integer |  |  |  | ≥ 2 | 11 | Maximum length of produced peptides. |
| `--max-task-num` | integer |  |  |  | ≥ 1 | 1000 | Maximum number of tasks submitted by `PREDICT_EPITOPES` process |
| `--memory-usage-log-deep` | boolean |  | yes |  |  |  | Enables "deep" memory usage output for main DataFrames generated in pandas scripts ("deep" ensures accurate usage values, but slightly increases runtime). |
| `--mhcflurry-mhcnuggets-score-threshold` | number |  | yes |  | ≥ 0; ≤ 1 | 0.426 | Threshold for binder/non-binder calling when using MHCflurry or MHCnuggets epitope prediction methods. The default value of 0.426 corresponds to an IC50 of ≤500. |
| `--min-pep-len` | integer |  |  |  | ≥ 1 | 9 | Minimum length of produced peptides. |
| `--pred-buffer-files` | integer |  | yes |  | ≥ 1 | 1000 | Number of files, which are merged in `MERGE_PREDICTION_BUFFER` |
| `--pred-chunk-size-scaling` | integer |  | yes |  | ≥ 1 | 10 | Scaling factor for `prediction_chunk_size` parameter for usage in python scripts to reduce memory usage when handling DataFrames. |
| `--pred-method` | string |  |  | `syfpeithi`, `mhcflurry`, `mhcnuggets-class-1`, `mhcnuggets-class-2` |  | syfpeithi | Epitope prediction method to use |
| `--prediction-chunk-size` | integer |  |  |  | ≥ 1 | 4000000 | Maximum chunk size (#peptides) for epitope prediction jobs. |
| `--prodigal-mode` | string |  |  |  |  | meta | Prodigal mode, 'meta' or 'single'. |
| `--show-supported-models` | boolean |  |  |  |  |  | Display supported alleles of all prediction methods and exit. |
| `--syfpeithi-score-threshold` | number |  | yes |  | ≥ 0; ≤ 1 | 0.5 | Threshold for binder/non-binder calling when using SYFPEITHI epitope prediction method. |

<!-- Generated from nf-core/metapep@84feafc9476978c2a1b84849871a553cffd9762a. Do not edit by hand. -->
