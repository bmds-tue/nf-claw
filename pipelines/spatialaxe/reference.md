---
name: spatialaxe
version: 1.0.1
commit: 748d310ac01943c97a15bdbc27ec2525a3ee0a96
---

# spatialaxe — full parameter reference

nf-core/spatialaxe pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean |  | yes |  |  |  | Display help text. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--hook-url` | string |  | yes |  |  |  | Incoming hook URL for messaging service |
| `--max-multiqc-email-size` | string |  | yes |  | matches `^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$` | `25.MB` | File size limit when attaching MultiQC reports to summary emails. |
| `--monochromeLogs` | boolean |  | yes |  |  |  | Do not use coloured log outputs |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--pipelines-testdata-base-path` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/test-datasets/` | Base URL or local path to location of pipeline test dataset files |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | `copy` | Method used to save pipeline results to output directory. |
| `--show-hidden` | boolean |  |  |  |  |  | Display hidden parameters in the help message (only works when --help or --help_full are provided). |
| `--trace-report-suffix` | string |  | yes |  |  |  | Suffix to add to the trace report filename. Default is the date and time in the format yyyy-MM-dd_HH-mm-ss |
| `--validate-params` | boolean |  | yes |  |  | `true` | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--alignment-csv` | string (file path) |  |  |  |  |  | Image alignment file containing similarity transform matrix. (e.g., the _imagealignment.csv file exported from Xenium Explorer) |
| `--cellpose-model` | string (file path) |  |  |  |  |  | Model to use for running or starting training. |
| `--email` | string |  |  |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary. |
| `--gene-panel` | string (file path) |  |  |  |  |  | Path to gene panel JSON file to use for relabeling transcripts with the correct gene. |
| `--gene-synonyms` | string (file path) |  |  |  |  |  | Gene synonyms that may have been counted as off-targets but simply differ in name. |
| `--input` | string (file path) | yes |  |  | matches `^\S+\.csv$` |  | Path to comma-separated file containing information about the Xenium experiment. (eg; meta,path-to-xenium-bundle,path-to-morphology.ome.tif)) |
| `--method` | string |  |  | `cellpose`, `xeniumranger`, `baysor`, `proseg`, `segger`, `ficture`, `stardist` |  |  | Segmentation method to run. |
| `--mode` | string | yes |  | `image`, `coordinate`, `segfree`, `preview`, `qc` |  |  | Mode in which the pipeline is to be run. Either image-based segmentation, coordinate-based segmentation, segmentation-free analysis or data preview. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--probes-fasta` | string (file path) |  |  |  |  |  | Fasta file for the probe sequences used in the xenium experiment. |
| `--qupath-polygons` | string (file path) |  |  |  |  |  | Path to qupath segmentation file in GeoJSON format. |
| `--reference-annotations` | string (file path) |  |  |  |  |  | Path to the directory containing genomic features (.gff) and fasta (.fa) files used as reference annotations. |
| `--segmentation-mask` | string (file path) |  |  |  |  |  | Prior segmentation mask from other segmentation methods. |
| `--stardist-model` | string |  |  |  |  | `2D_versatile_fluo` | StarDist pretrained model for cell segmentation (e.g., '2D_versatile_fluo', '2D_versatile_he'). |
| `--stardist-n-tiles` | string |  |  |  |  | `8 8` | StarDist tiling for large images (e.g., '4 4'). Reduces memory usage. |
| `--stardist-nms-thresh` | number |  |  |  |  |  | StarDist non-maximum suppression threshold. Lower values reduce overlapping detections. |
| `--stardist-nuclei-model` | string |  |  |  |  | `2D_versatile_fluo` | StarDist pretrained model for nuclei segmentation. |
| `--stardist-prob-thresh` | number |  |  |  |  |  | StarDist object probability threshold. Lower values detect more objects. |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/configs/master` | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | `master` | Git commit id for Institutional configs. |
| `--test-data-base` | string |  |  |  |  | `https://raw.githubusercontent.com/nf-core/test-datasets/spatialaxe` | Base path / URL for data used in the test profiles. |

## segmentation_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--batch-size-predict` | integer |  |  |  |  | `1` | Number of samples to process per batch during prediction |
| `--batch-size-train` | integer |  |  |  |  | `4` | Number of samples to process per training batch |
| `--baysor-config` | string (file path) |  |  |  |  |  | Path to Baysor config TOML file (optional). |
| `--baysor-prior` | string |  |  | `cells`, `cellpose` |  |  | Prior segmentation type for Baysor. 'cells' uses Xenium bundle cell_id column; 'cellpose' uses Cellpose mask as image prior. |
| `--baysor-prior-confidence` | number |  |  |  |  | `0.2` | Baysor prior-segmentation-confidence (0-1). |
| `--baysor-scale` | integer |  |  |  |  | `30` | Baysor --scale parameter for non-tiled runs. |
| `--baysor-tiling` | boolean |  |  |  |  | `true` | Enable tiled Baysor segmentation (divide transcripts into patches, run Baysor per patch, stitch results). |
| `--baysor-tiling-balanced` | boolean |  |  |  |  | `true` | Balance transcripts across tiles by merging sparse tiles. |
| `--baysor-tiling-micron` | integer |  |  |  |  | `1200` | Tile width in microns for Baysor tiling. |
| `--baysor-tiling-min-mols-per-cell` | integer |  |  |  |  | `120` | Minimum molecules per cell (--min-molecules-per-cell) for tiled Baysor. |
| `--baysor-tiling-min-transcripts-per-cell` | integer |  |  |  |  | `50` | Post-stitch cell filtering threshold: minimum transcripts per cell. |
| `--baysor-tiling-overlap` | integer |  |  |  |  | `200` | Overlap between Baysor patches in microns. |
| `--baysor-tiling-scale` | integer |  |  |  |  | `39` | Baysor --scale for tiled runs (larger to compensate for EM on smaller tiles). |
| `--boundary-stain` | boolean |  |  |  |  | `true` | Specify the name of the boundary stain to use or disable. Supported for cell segmentation staining workflow output bundles. Possible options are: \"ATP1A1/CD45/E-Cadherin\" (default) or \"disable\" |
| `--buffer-samples` | boolean |  |  |  |  | `false` | Process only one sample at a time from a multi-sample samplesheet. |
| `--buffer-size` | integer |  |  |  |  | `1` | Number of sample(s) to process at a time from a multi-sample samplesheet. Works if buffered_samples is true. |
| `--cc-analysis` | boolean |  |  |  |  | `false` | Whether to use connected components for grouping transcripts without direct nucleus association |
| `--cell-segmentation-only` | boolean |  |  |  |  |  | Whether to only run nucleus segmentation. |
| `--cellpose-downscale` | boolean |  |  |  |  | `false` | Pre-downscale morphology image to avoid Cellpose OOM on large images. |
| `--cellpose-queue` | string |  |  |  |  |  | AWS Batch queue for Cellpose (single large GPU). |
| `--csplit-x-bins` | integer |  |  |  |  | `2` | Number of tiles along the x axis for cell-type separability. |
| `--csplit-y-bins` | integer |  |  |  |  | `2` | Number of tiles along the y axis for cell-type separability. |
| `--dapi-filter` | integer |  |  |  |  | `100` | Minimum intensity in photoelectrons (pe) to filter nuclei. Default: 100. (appropriate range of values is 0 to 99th percentile of image stack or 1000, whichever is larger) |
| `--devices` | integer |  |  |  |  | `4` | Number of devices (GPUs) to use during training |
| `--expansion-distance` | integer |  |  |  |  | `5` | Nuclei boundary expansion distance in µm. Default: 5 (Min: 0, Max: 15 if either boundary-stain or interior-stain are enabled and 100 if nucleus-expansion only) |
| `--features` | string |  |  |  |  |  | List of features to be passed to the ficture method. (eg: TP53,OCIAD1,BCAS3,SOX) |
| `--filter-transcripts` | boolean |  |  |  |  | `false` | Whether to filter the transcripts.parquet file before running Baysor segmentation. |
| `--format` | string |  |  | `xenium`, `cosmx`, `merscope` |  | `xenium` | Input data platform. Used by proseg, segger, and spatialdata modules. |
| `--gpu-queue` | string |  |  |  |  |  | AWS Batch queue for GPU tasks (e.g., Segger, ProSeg). |
| `--image-seg-methods` | array |  |  |  |  |  | List of image-based segmentation methods. |
| `--interior-stain` | boolean |  |  |  |  | `true` | Specify the name of the interior stain to use or disable. Supported for cell segmentation staining workflow output bundles. Possible options are: \"18S\" (default) or \"disable\" |
| `--max-epochs` | integer |  |  |  |  | `200` | Number of training epochs |
| `--max-x` | number |  |  |  |  |  | only keep transcripts whose x-coordinate is less than specified limit, if no limit is specified, the default value will retain all transcripts since Xenium slide is <24000 microns in x and y (default: 24000.0) |
| `--max-y` | number |  |  |  |  |  | only keep transcripts whose y-coordinate is less than specified limit, if no limit is specified, the default value will retain all transcripts since Xenium slide is <24000 microns in x and y (default: 24000.0) |
| `--min-qv` | number |  |  |  |  | `20` | Minimum Q-Score to pass filtering. |
| `--min-x` | number |  |  |  |  |  | only keep transcripts whose x-coordinate is greater than specified limit, if no limit is specified, the default minimum value will be 0.0 |
| `--min-y` | number |  |  |  |  |  | only keep transcripts whose y-coordinate is greater than specified limit, if no limit is specified, the default minimum value will be 0.0 |
| `--negative-control-regex` | string |  |  |  |  |  | Regex used to identify or match negative control samples in a dataset. |
| `--nucleus-segmentation-only` | boolean |  |  |  |  |  | Whether to only run nucleus segmentation. |
| `--offtarget-probe-tracking` | boolean |  |  |  |  | `false` | Whether to run the off-target probe tracking. |
| `--patch-filter-iqr-multiplier` | number |  |  |  |  | `3.0` | IQR multiplier for empirical cell size filtering during stitching. |
| `--patch-filter-method` | string |  |  | `empirical`, `distribution`, `both` |  |  | Post-stitch cell size filtering method. Options: 'empirical' (IQR-based), 'distribution' (z-score), 'both', or null to disable. |
| `--patch-filter-z-threshold` | number |  |  |  |  | `4.0` | Z-score threshold for distribution-based cell size filtering during stitching. |
| `--patch-grid` | string |  |  |  |  | `3x3` | Grid layout for tiling (rows x cols), e.g. '3x3', '4x4'. |
| `--patch-overlap` | integer |  |  |  |  | `50` | Overlap between adjacent patches in microns. |
| `--relabel-genes` | boolean |  |  |  |  |  | Whether to relabel genes with gene_panel.json file. True when gene_panel is provided. |
| `--run-qc` | boolean |  |  |  |  | `true` | Whether to run the qc layer in the pipeline. |
| `--segfree-methods` | array |  |  |  |  |  | List of segmentation-free methods. |
| `--segger-accelerator` | string |  |  | `cpu`, `cuda` |  | `cpu` | Device used for training. (e.g., cuda for GPU or cpu) |
| `--segger-knn-method` | string |  |  | `kd_tree`, `cuda` |  | `kd_tree` | Method for KNN computation. (e.g., cuda for GPU-based computation) |
| `--segger-model` | string (file path) |  |  |  |  |  | Path to a pre-trained Segger model checkpoint. |
| `--segger-num-workers` | integer |  |  |  |  | `4` | Number of data-loader workers for Segger. |
| `--segmentation-refinement` | boolean |  |  |  |  |  | Whether to run refinement on the image-based segmentation methods. Runs coordinate-based methods after the initial image-based segmentation run. |
| `--sharpen-tiff` | boolean |  |  |  |  |  | Whether to enhance the morphology.ome.tif file. |
| `--tile-height` | integer |  |  |  |  | `120` | Height of the tiles in pixels |
| `--tile-width` | integer |  |  |  |  | `120` | Width of the tiles in pixels |
| `--tiling` | boolean |  |  |  |  | `false` | Enable tiled segmentation for large datasets. Divides transcripts into overlapping patches, runs segmentation in parallel per patch, then stitches results. |
| `--transcript-seg-methods` | array |  |  |  |  |  | List of transcript-based segmentation methods. |
| `--use-gpu` | boolean |  |  |  |  | `false` | Enable GPU acceleration (set automatically by the gpu profile). |
| `--xeniumranger-only` | boolean |  |  |  |  |  | Whether to run vanilla xeniumranger workflow. |

<!-- Generated from nf-core/spatialaxe@748d310ac01943c97a15bdbc27ec2525a3ee0a96. Do not edit by hand. -->
