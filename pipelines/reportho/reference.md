---
name: reportho
version: 1.1.0
commit: 9e8ae5a07ddb5ccd34bb01c72e70e390d97d1cb7
---

# reportho — full parameter reference

nf-core/reportho pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## downstream_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--skip-report` | boolean |  |  |  |  |  | Skip report generation. |

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
| `--output-intermediates` | boolean |  |  |  |  |  | Output intermediate files, including specific prediction lists. |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/configs/master | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | master | Git commit id for Institutional configs. |

## ortholog_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--eggnog-idmap-path` | string (file or directory path) |  |  |  |  |  | Path to the EggNOG ID map. |
| `--eggnog-path` | string (file or directory path) |  |  |  |  |  | Path to the EggNOG database. |
| `--local-databases` | boolean |  |  |  |  |  | Use local databases for the analysis. |
| `--min-coverage` | number |  |  |  |  | 80 | Minimum sequence coverage in Diamond |
| `--min-identity` | number |  |  |  |  | 90 | Minimum sequence identity in Diamond |
| `--min-score` | number |  |  |  |  | 2 | Minimum score for the ortholog search. |
| `--offline-run` | boolean |  |  |  |  |  | Run the pipeline in offline mode. Overrides all online database flags. |
| `--oma-ensembl-path` | string (file or directory path) |  |  |  |  |  | Path to the Ensembl-OMA ID map. |
| `--oma-path` | string (file or directory path) |  |  |  |  |  | Path to the OMA database. |
| `--oma-refseq-path` | string (file or directory path) |  |  |  |  |  | Path to the RefSeq-OMA ID map. |
| `--oma-uniprot-path` | string (file or directory path) |  |  |  |  |  | Path to the Uniprot-OMA ID map. |
| `--orthoinspector-path` | string (file or directory path) |  |  |  |  |  | Path to the OrthoInspector database. |
| `--orthoinspector-version` | string |  |  |  |  | Eukaryota2023 | The version of the OrthoInspector database to use. |
| `--panther-path` | string (file or directory path) |  |  |  |  |  | Path to the PANTHER database. |
| `--skip-eggnog` | boolean |  |  |  |  |  | Use EggNOG for the ortholog search. |
| `--skip-merge` | boolean |  |  |  |  |  | Skip merging IDs based on sequence. |
| `--skip-oma` | boolean |  |  |  |  |  | Skip using OMA for the ortholog search. |
| `--skip-orthoinspector` | boolean |  |  |  |  |  | Skip using OrthoInspector for the ortholog search. |
| `--skip-panther` | boolean |  |  |  |  |  | Skip using PANTHER for the ortholog search. |
| `--use-all` | boolean |  |  |  |  |  | Use all ortholog search methods. Will mix online and local methods if needed. Overrides all individual database flags. |
| `--use-centroid` | boolean |  |  |  |  |  | Use centroid strategy for the ortholog search. Overrides min_score. |

## process_skipping_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--skip-multiqc` | boolean |  |  |  |  |  | Skip MultiQC. |
| `--skip-orthoplots` | boolean |  |  |  |  |  | Skip the ortholog plots. |

<!-- Generated from nf-core/reportho@9e8ae5a07ddb5ccd34bb01c72e70e390d97d1cb7. Do not edit by hand. -->
