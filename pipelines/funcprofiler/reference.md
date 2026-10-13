---
name: funcprofiler
version: 1.0.0
commit: 805e23e866b90142e176d1ae85da6f6a365bf056
---

# funcprofiler — full parameter reference

nf-core/funcprofiler pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
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
| `--databases` | string (file path) | yes |  |  | matches ^\S+\.csv$ |  | Path to comma-separated file containing information about databases and profiling parameters for each taxonomic profiler |
| `--email` | string |  |  |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  | matches ^\S+\.csv$ |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--save-untarred-databases` | boolean |  |  |  |  |  | Specify to save decompressed user-supplied TAR archives of databases |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/configs/master | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | master | Git commit id for Institutional configs. |

## profiling_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--run-diamond` | boolean |  |  |  |  |  | Turn on translated alignment with DIAMOND blastx. Requires a `diamond`-tagged database to be present in the CSV file passed to --databases |
| `--run-eggnogmapper` | boolean |  |  |  |  |  | Turn on functional annotation with eggNOG-mapper. Requires `eggnogmapper`-tagged database entries to be present in the CSV file passed to --databases |
| `--run-fmhfunprofiler` | boolean |  |  |  |  |  | Turn on profiling with FMH FunProfiler. Requires a `fmhfunprofiler`-tagged database to be present in the CSV file passed to --databases |
| `--run-humann-v3` | boolean |  |  |  |  |  | Turn on profiling with HUMAnN3. Requires a `humann_v3`-tagged database to be present in the CSV file passed to --databases |
| `--run-humann-v4` | boolean |  |  |  |  |  | Turn on profiling with HUMAnN4. Requires a `humann_v4`-tagged database to be present in the CSV file passed to --databases |
| `--run-mifaser` | boolean |  |  |  |  |  | Turn on profiling with mi-faser. Requires a `mifaser`-tagged database to be present in the CSV file passed to --databases |
| `--run-rgi` | boolean |  |  |  |  |  | Turn on profiling with RGI. Requires a `rgi`-tagged database to be present in the CSV file passed to --databases |

<!-- Generated from nf-core/funcprofiler@805e23e866b90142e176d1ae85da6f6a365bf056. Do not edit by hand. -->
