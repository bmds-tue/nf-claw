---
name: coproid
version: 2.0.1
commit: 045d569d5b01b2d1572220718e64a6d054ad57eb
---

# coproid — full parameter reference

nf-core/coproid pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--hook-url` | string |  | yes |  |  |  | Incoming hook URL for messaging service |
| `--max-multiqc-email-size` | string |  | yes |  | matches ^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$ | 25.MB | File size limit when attaching MultiQC reports to summary emails. |
| `--modules-testdata-base-path` | string |  |  |  |  | https://raw.githubusercontent.com/nf-core/test-datasets/modules/data |  |
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
| `--version` | boolean |  |  |  |  |  |  |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--genome-sheet` | string (file path) | yes |  |  | matches ^\S+\.csv$ |  | Path to comma-separated file containing information about the reference genomes. |
| `--input` | string (file path) | yes |  |  | matches ^\S+\.csv$ |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--multiqc-title` | string |  |  |  |  | coproid | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
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

## pipeline_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--file-prefix` | string |  |  |  |  | coproid | Used as a prefix for (merged) output reports |
| `--igenomes-base` | string (directory path) |  | yes |  |  | s3://ngi-igenomes/igenomes/ | The base path to the igenomes reference files |
| `--igenomes-ignore` | boolean |  | yes |  |  | true | Do not load the iGenomes reference config. |
| `--kraken2-db` | string (file path) | yes |  |  |  |  | Path to a kraken2 database, can be a directory or *.tar.gz |
| `--sam2lca-acc2tax` | string |  |  |  |  | adnamap | Sam2lca parameter --acc2tax, use default 'adnamap' when no sam2lca_db is supplied, change accordingly for sam2lca_db (e.g. 'nucl') |
| `--sam2lca-db` | string |  |  |  |  |  | Path to pre-downloaded ~/.sam2lca directory, if not supplied a local database will be build from the reference genomes |
| `--sam2lca-identity` | number |  |  |  |  | 0.9 | Set the sam2lca --identity parameter |
| `--sp-labels` | string (file path) | yes |  |  |  |  | Labels for the sources table in csv format for sourcepredict |
| `--sp-sources` | string (file path) | yes |  |  |  |  | Sources TAXID count table in csv format for sourcepredict |
| `--taxa-sqlite` | string (file path) |  |  |  |  | [:]/genomics/prokaryotes/metagenome/taxonomy/misc/taxa_sqlite.xz | Path to pre-downloaded ~/.etetoolkit/taxa.sqlite file, if not supplied it will be pulled from the test-data repository |
| `--taxa-sqlite-traverse-pkl` | string (file path) |  |  |  |  | [:]/genomics/prokaryotes/metagenome/taxonomy/misc/taxa_sqlite_traverse.pkl | Path to pre-downloaded ~/.etetoolkit/taxa.sqlite.traverse.pkl file, if not supplied it will be pulled from the test-data repository |

<!-- Generated from nf-core/coproid@045d569d5b01b2d1572220718e64a6d054ad57eb. Do not edit by hand. -->
