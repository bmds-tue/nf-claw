---
name: ribomsqc
version: v1.0.0
commit: 3654357ea417c0a52ede22721f584885271fc0e7
---

# ribomsqc — full parameter reference

nf-core/ribomsqc pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--hook-url` | string |  | yes |  |  |  | Incoming hook URL for messaging service |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
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
| `--email` | string |  | yes |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  | matches ^\S+\.csv$ |  | Path to a comma-separated file (CSV) listing samples to process. Must contain a header with two columns: 'id' (sample identifier) and 'raw_file' (full path to the corresponding RAW file). You may specify one or multiple samples for batch processing. |
| `--outdir` | string (directory path) | yes |  |  |  |  | Directory where the pipeline will write its output. If a relative folder name is used (e.g., 'results'), it will be created in the current working directory. If an absolute path is given (e.g., '/path/to/output'), the folder will be created at that specific location. |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/configs/master | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | master | Git commit id for Institutional configs. |

## xic_parameters

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--analyte` | string | yes |  |  |  |  | Short name of the analyte to be extracted, as defined in the 'short_name' column of the TSV file. Use a specific value such as 'm3C' to process one analyte, or use 'all' to process all analytes defined in the TSV file. |
| `--analytes-tsv` | string (file path) | yes |  |  | matches ^\S+\.tsv$ |  | Path to a tab-separated values (TSV) file describing the analytes for chromatographic peak extraction. Must include columns: `short_name`, `long_name`, `mz_M0` (required), and optionally `mz_M1`, `mz_M2`, `ms2_mz`, and `rt_teoretical` (required). Only `mz_M0` and `rt_teoretical` are mandatory. `mz_M1` and `mz_M2` are reserved for future support of isotopic envelope integration. |
| `--ms-level` | integer | yes |  |  |  | 2 | MS level to extract chromatographic peaks from. Set to 1 for MS1 or 2 for MS2. |
| `--mz-tolerance` | integer | yes |  |  |  | 20 | Tolerance in parts-per-million (ppm) around the specified precursor m/z value (mz_M0) for XIC extraction. The window is defined as mz_M0 ± tolerance. |
| `--overwrite-tsv` | boolean |  |  |  |  |  | Whether to generate an additional TSV file accumulating the XIC extraction results. If set to `true`, the output will include a progressively updated results table based on the original input analytes TSV. |
| `--plot-output-path` | string |  |  |  |  | xic_plot.pdf | Output file name for the XIC PDF plot |
| `--plot-xic-ms1` | boolean |  |  |  |  |  | Whether to plot MS1 XICs |
| `--plot-xic-ms2` | boolean |  |  |  |  |  | Whether to plot MS2 XICs |
| `--rt-tolerance` | integer | yes |  |  |  | 150 | Time window (in seconds) around the theoretical retention time in which peaks will be searched. The window is defined as RT ± tolerance. |
| `--test-mode` | boolean |  | yes |  |  | false | Enable test mode - pipeline continues even if analytes are not found in the data. Useful for CI testing with minimal datasets. |

<!-- Generated from nf-core/ribomsqc@3654357ea417c0a52ede22721f584885271fc0e7. Do not edit by hand. -->
