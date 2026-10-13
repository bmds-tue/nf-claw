---
name: rangeland
version: 1.0.0
commit: 7c5cb9593b80d2a3cdc8bcb14137722351644435
---

# rangeland — full parameter reference

nf-core/rangeland pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

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
| `--trace-report-suffix` | string |  | yes |  |  |  | Suffix to add to the trace report filename. Default is the date and time in the format yyyy-MM-dd_HH-mm-ss. |
| `--validate-params` | boolean |  | yes |  |  | true | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## higher_level_processing_modification

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--indexes` | string |  |  |  | matches ((BLUE\|GREEN\|RED\|NIR\|SWIR1\|SWIR2\|RE1\|RE2\|RE3\|BNIR\|NDVI\|EVI\|NBR\|NDTI\|ARVI\|SAVI\|SARVI\|TC-BRIGHT\|TC-GREEN\|TC-WET\|TC-DI\|NDBI\|NDWI\|MNDWI\|NDMI\|NDSI\|SMA\|kNDVI\|NDRE1\|NDRE2\|CIre\|NDVIre1\|NDVIre2\|NDVIre3\|NDVIre1n\|NDVIre2n\|NDVIre3n\|MSRre\|MSRren,CCI)(\s\|$))+ | NDVI BLUE GREEN RED NIR SWIR1 SWIR2 | Select which bands and indexes should be considered in time series analyses. |
| `--return-tss` | boolean |  |  |  |  |  | Should the full time series stack be returned. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--aoi` | string (file path) | yes |  |  | matches ^\S+\.(gpkg\|shp)$ |  | Area of interest. |
| `--data-cube` | string (file path) | yes |  |  | matches ^\S+\.prj$ |  | Datacube definition. |
| `--dem` | string (file or directory path) | yes |  |  |  |  | Digital elevation model. |
| `--email` | string |  |  |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--endmember` | string (file path) | yes |  |  | matches ^\S+\.txt$ |  | Endmember definition. |
| `--input` | string (file or directory path) | yes |  |  |  |  | Root directory or tarball of all satellite imagery. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--wvdb` | string (file or directory path) | yes |  |  |  |  | Water vapor dataset. |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/configs/master | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | master | Git commit id for Institutional configs. |

## remote_sensing_image_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--end-date` | string |  |  |  | matches ^\d{4}-\d{2}-\d{2}$ | 2006-12-31 | Last day of interest. |
| `--resolution` | integer |  |  |  | ≥ 1 | 30 | Spatial resolution applied in analyses. |
| `--sensors-level2` | string |  |  |  | matches ^((LND04\|LND05\|LND07\|LND08\|LND09\|SEN2A\|SEN2B\|sen2a\|sen2b\|S1AIA\|S1BIA\|S1AID\|S1BID\|MOD01\|MOD02\|LNDLG\|SEN2L\|SEN2H\|R-G-B\|VVVHP\|MODIS)(\s\|$))+$ | LND04 LND05 LND07 | Satellites for which data should be incorporated into higher level processing. |
| `--start-date` | string |  |  |  | matches ^\d{4}-\d{2}-\d{2}$ | 1984-01-01 | First day of interest. |

## visualization

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--mosaic-visualization` | boolean |  |  |  |  | true | Whether mosaic visualization should be returned. |
| `--pyramid-visualization` | boolean |  |  |  |  | true | Whether pyramid visualization should be returned. |

## workflow_configuration

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--group-size` | integer |  |  |  |  | 100 | Batch size of tiles considered for merging. |
| `--publish-dir-enabled` | boolean |  |  |  |  | true | Publish pipeline outputs. |
| `--save-ard` | boolean |  |  |  |  |  | Whether analysis ready data should be published to the output directory. |
| `--save-tsa` | boolean |  |  |  |  |  | Whether the results of time series analyses should be published to the output directory. |

<!-- Generated from nf-core/rangeland@7c5cb9593b80d2a3cdc8bcb14137722351644435. Do not edit by hand. -->
