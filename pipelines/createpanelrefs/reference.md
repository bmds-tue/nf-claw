---
name: createpanelrefs
version: 1.0.0
commit: 8ce86a84b5af74facf99abb76216531622b52bc8
---

# createpanelrefs — full parameter reference

nf-core/createpanelrefs pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## cnvkit_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--cnvkit-pon-name` | string |  |  |  |  | `cnvkit` | Name for panel of normals. |
| `--cnvkit-targets` | string (file or directory path) |  |  |  |  |  | Path to directory for target file. |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--max-multiqc-email-size` | string |  | yes |  | matches `^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$` | `25.MB` | File size limit when attaching MultiQC reports to summary emails. |
| `--modules-testdata-base-path` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/test-datasets/` | Base URL or local path to location of modules test dataset files |
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

## gens_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--gens-analysis-type` | string |  |  | `srs`, `lrs` |  | `srs` | GENS panel of normals analysis type ('srs' or 'lrs'). |
| `--gens-bin-length` | number |  |  |  |  | `100` | Length (in bp) of the bins. If zero, no binning will be performed. |
| `--gens-maximum-chunk-size` | number |  |  |  |  | `167772150` | Maximum chunk size when writing the HDF5 file |
| `--gens-min-interval-median-percentile` | number |  |  |  |  | `5` | Minimum interval median percentile for gatk CreateReadCountPanelOfNormals |
| `--gens-pon-name` | string |  |  |  |  | `gens` | Name for panel of normals. |
| `--gens-readcount-format` | string |  |  | `HDF5`, `TSV` |  | `HDF5` | Output file format for count data |

## germlinecnvcaller_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--gcnv-analysis-type` | string |  |  | `wgs`, `wes` |  | `wgs` | Specifies which analysis type for the pipeline- either 'wgs' or 'wes'. |
| `--gcnv-bin-length` | number |  |  |  |  | `1000` | Length (in bp) of the bins. If zero, no binning will be performed. |
| `--gcnv-model-name` | string |  |  |  |  | `germlinecnvcaller` | Name for panel of normals. |
| `--gcnv-padding` | number |  |  |  |  | `0` | Length (in bp) of the padding regions on each side of the intervals. |
| `--gcnv-readcount-format` | string |  |  | `HDF5`, `TSV` |  | `HDF5` | Output file format for count data |
| `--gcnv-scatter-content` | number |  |  |  |  | `5000` | When scattering with this argument, each of the resultant files will (ideally) have this amount of interval-counts. |

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

## main_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--tools` | string | yes |  |  | matches `^((cnvkit\|germlinecnvcaller\|gens\|mutect2)?,?)*(?<!,)$` |  | Tools to use for building Panel of Normals or models. |

## mutect2_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--mutect2-intervals-num` | number |  |  |  | ≥ 1 | `20` | Number of intervals. |
| `--mutect2-pon-name` | string |  |  |  |  | `mutect2` | Name for panel of normals. |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--dict` | string (file path) |  |  |  | matches `^\S+\.dict$` |  | Path to sequence dictionary file |
| `--fai` | string (file path) |  |  |  | matches `^\S+\.fn?a(sta)?\.fai$` |  | Path to fasta index file |
| `--fasta` | string (file path) |  |  |  | matches `^\S+\.fn?a(sta)?(\.gz)?$` |  | Path to FASTA genome file. |
| `--gcnv-exclude-bed` | string (file or directory path) |  |  |  | matches `^\S+\.bed$` |  | Path to directory for a bed file containing regions to be exluded from the analysis. |
| `--gcnv-exclude-interval-list` | string (file or directory path) |  |  |  | matches `^\S+\.interval_list$` |  | Path to directory for exclude_interval_list file. |
| `--gcnv-mappable-regions` | string (file path) |  |  |  |  |  | Path to Umap single-read mappability track in .bed or .bed.gz format. Overlapping intervals must be merged. |
| `--gcnv-ploidy-priors` | string (file path) |  |  |  |  |  | Path to a file containing ploidy priors table. |
| `--gcnv-segmental-duplications` | string (file path) |  |  |  |  |  | Path to segmental-duplication track in .bed or .bed.gz format. Overlapping intervals must be merged. |
| `--gcnv-target-bed` | string (file or directory path) |  |  |  | matches `^\S+\.bed$` |  | Path to directory for target bed file. |
| `--gcnv-target-interval-list` | string (file or directory path) |  |  |  | matches `^\S+\.interval_list$` |  | Path to directory for target interval_list file. |
| `--genome` | string |  |  |  |  |  | Name of iGenomes reference. |
| `--gens-interval-list` | string (file path) |  |  |  | matches `^\S+\.interval_list$` |  | Path to GENS interval list file |
| `--igenomes-base` | string |  | yes |  |  | `s3://ngi-igenomes/igenomes/` | The base path to the igenomes reference files |
| `--igenomes-ignore` | boolean |  | yes |  |  |  | Do not load the iGenomes reference config. |
| `--mutect2-target-bed` | string (file path) |  |  |  | matches `^\S+\.bed$` |  | Path to target bed file |

<!-- Generated from nf-core/createpanelrefs@8ce86a84b5af74facf99abb76216531622b52bc8. Do not edit by hand. -->
