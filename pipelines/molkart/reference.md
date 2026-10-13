---
name: molkart
version: 1.2.0
commit: 4ec0790d80cf77f2428d33b1a8571ccb498e2170
---

# molkart — full parameter reference

nf-core/molkart pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--hook-url` | string |  | yes |  |  |  | Incoming hook URL for messaging service |
| `--max-multiqc-email-size` | string |  | yes |  | matches ^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$ | 25.MB | File size limit when attaching MultiQC reports to summary emails. |
| `--modules-testdata-base-path` | string |  |  |  |  | https://raw.githubusercontent.com/nf-core/test-datasets/modules/data/ | URL or local path to location of module test dataset files |
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

## image_preprocessing

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--clahe-cliplimit` | number |  |  |  |  | 0.01 | Contrast limit for localized changes in contrast by CLAHE. |
| `--clahe-kernel` | number |  |  |  |  | 25.0 | Kernel size to be used by CLAHE. |
| `--clahe-nbins` | integer |  |  |  |  | 256 | Number of histogram bins to be used by CLAHE. |
| `--clahe-pixel-size` | number |  |  |  |  | 0.138 | Pixel size to be used by CLAHE. |
| `--clahe-pyramid-tile` | integer |  | yes |  |  | 1072 | Tile size used for pyramid generation (must be divisible by 16). |
| `--mindagap-boxsize` | integer |  |  |  |  | 3 | Box size used by Mindagap to overcome gaps, a larger number allows to overcome large gaps, but results in less fine details in the filled grid. |
| `--mindagap-edges` | boolean |  | yes |  |  |  | Should Mindagap blur area around grid for smoother transitions between tiles with different exposures. |
| `--mindagap-loopnum` | integer |  |  |  |  | 40 | Loop number performed by Mindagap. Lower values are faster, but the result is less good. |
| `--mindagap-tilesize` | integer |  | yes |  |  | 2144 | Tile size (distance between gridlines) for Mindagap. |
| `--skip-clahe` | boolean |  |  |  |  |  | Specifies whether contrast-limited adaptive histogram equalization should be skipped. |
| `--skip-mindagap` | boolean |  |  |  |  |  | Skip mindagap if your data does not contain gaps between tiles. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  | matches ^\S+\.csv$ |  | Path to comma-separated file containing information about the samples in the experiment. |
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

## segmentation_methods_and_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--cellpose-cellprob-threshold` | integer |  |  |  |  | 0 | Cell probability threshold for Cellpose |
| `--cellpose-chan` | integer |  |  |  |  | 0 | Specifies the channel to be segmented by Cellpose. |
| `--cellpose-chan2` | integer |  |  |  |  |  | Specifies nuclear channel index for Cellpose if using pretrained models such as cyto. |
| `--cellpose-custom-model` | string |  |  |  |  |  | Custom Cellpose model can be provided by the user. |
| `--cellpose-diameter` | integer |  |  |  |  | 30 | Cell diameter, if 0 will use the diameter of the training labels used in the model, or with built-in model will estimate diameter for each image. |
| `--cellpose-edge-exclude` | boolean |  |  |  |  | true | Should cells detected near image edges be excluded. |
| `--cellpose-flow-threshold` | number |  |  |  |  | 0.4 | Flow error threshold for Cellpose. |
| `--cellpose-pretrained-model` | string |  |  |  |  | cyto | Pretrained Cellpose model to be used for segmentation. |
| `--cellpose-save-flows` | boolean |  |  |  |  |  | Should flow fields from Cellpose be saved? |
| `--ilastik-multicut-project` | string (file path) |  |  |  |  |  | Provide ilastik with a multicut project to create segmentation masks. |
| `--ilastik-pixel-project` | string (file path) |  |  |  |  |  | Provide ilastik with a pixel classification project to produce probability maps. |
| `--mesmer-compartment` | string |  |  |  |  | whole-cell | Compartment to be segmented with Mesmer (nuclear, whole-cell) |
| `--mesmer-image-mpp` | number |  |  |  |  | 0.138 | Pixel size in microns for segmentation with Mesmer. |
| `--segmentation-max-area` | integer |  |  |  |  |  | Maximum area size (in pixels) for segmentation masks. |
| `--segmentation-method` | string | yes |  |  |  | mesmer | List of segmentation tools to apply to the image. Allowed values: mesmer, cellpose, stardist, ilastik. Use a comma-separated string without whitespaces for multiple methods. |
| `--segmentation-min-area` | integer |  |  |  |  |  | Minimum area size (in pixels) for segmentation masks. |
| `--stardist-model` | string |  |  | `2D_versatile_fluo`, `2D_paper_dsb2018`, `2D_versatile_he` |  | 2D_versatile_fluo | Model to use for segmentation with stardist. |
| `--stardist-n-tiles-x` | integer |  |  |  |  | 3 | Number of tiles on the X axis for Stardist. |
| `--stardist-n-tiles-y` | integer |  |  |  |  | 3 | Number of tiles on the Y axis for Stardist. |

## training_subset_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--create-training-subset` | boolean |  |  |  |  |  | Create subset for training a segmentation model. |
| `--crop-amount` | integer |  |  |  |  | 4 | Number of crops you would like to extract. |
| `--crop-nonzero-fraction` | number |  |  |  |  | 0.4 | Indicates fraction of pixels per crop above global threshold to ensure tissue and not only background is selected. |
| `--crop-size-x` | integer |  |  |  |  | 400 | Indicates crop size on x axis. |
| `--crop-size-y` | integer |  |  |  |  | 400 | Indicates crop size on y axis. |

<!-- Generated from nf-core/molkart@4ec0790d80cf77f2428d33b1a8571ccb498e2170. Do not edit by hand. -->
