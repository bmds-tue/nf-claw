---
name: sopa
version: 1.0.1
commit: 0b959963a3984ff78725209113d9ecdb78cef0b6
---

# sopa — full parameter reference

nf-core/sopa pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## aggregation

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--aggregate-channels` | boolean |  |  |  |  |  | Whether to aggregate the channels (intensity) inside each cell |
| `--aggregate-genes` | boolean |  |  |  |  |  | Whether to aggregate the genes (counts) inside each cell |
| `--expand-radius-ratio` | string |  |  |  |  |  | Cells polygons will be expanded by `expand_radius_ratio * mean_radius` for channels averaging **only**. This help better aggregate boundary stainings |

## baysor

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--baysor-scale` | number |  |  |  |  | -1.0 | Baysor `scale` parameter |
| `--baysor-scale-std` | string |  |  |  |  | 25% | Baysor `scale_std` parameter |
| `--confidence-nn-id` | number |  |  |  |  |  | Baysor `confidence_nn_id` parameter |
| `--force-2d` | boolean |  |  |  |  | true | Baysor `force_2d` parameter |
| `--min-molecules-per-cell` | number |  |  |  |  | 20.0 | Baysor `min_molecules_per_cell` parameter |
| `--min-molecules-per-gene` | number |  |  |  |  | 10.0 | Baysor `min_molecules_per_gene` parameter |
| `--min-molecules-per-segment` | number |  |  |  |  |  | Baysor `min_molecules_per_segment` parameter |
| `--prior-segmentation-confidence` | number |  |  |  |  | 0.2 | Baysor `prior_segmentation_confidence` parameter |
| `--use-baysor` | boolean |  |  |  |  |  | Whether to run baysor segmentation |

## cellpose

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--cellpose-channels` | string |  |  |  |  |  | Channel name(s) to use for cellpose segmentation. If multiple, separate by space, comma or pipe characters. |
| `--cellpose-diameter` | number |  |  |  |  |  | Cellpose `diameter` parameter |
| `--cellpose-kwargs` | string |  |  |  |  |  | Additional cellpose parameters as a python dict string |
| `--cellpose-model-type` | string |  |  |  |  |  | Cellpose model type to use |
| `--cellpose-use-gpu` | boolean |  |  |  |  |  | Whether to use GPU for Cellpose segmentation |
| `--cellprob-threshold` | number |  |  |  |  |  | Cellpose `cellprob_threshold` parameter |
| `--flow-threshold` | number |  |  |  |  |  | Cellpose `flow_threshold` parameter |
| `--pretrained-model` | string |  |  |  |  |  | Cellpose `pretrained_model` parameter |
| `--use-cellpose` | boolean |  |  |  |  |  | Whether to run cellpose segmentation |

## comseg

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--allow-disconnected-polygon` | boolean |  |  |  |  |  | Comseg `allow_disconnected_polygon` parameter |
| `--alpha` | number |  |  |  |  | 0.5 | Comseg `alpha` parameter |
| `--max-cell-radius` | number |  |  |  |  | 15.0 | Comseg `max_cell_radius` parameter |
| `--mean-cell-diameter` | number |  |  |  |  | 10.0 | Comseg `mean_cell_diameter` parameter |
| `--min-rna-per-cell` | number |  |  |  |  | 1.0 | Comseg `min_rna_per_cell` parameter |
| `--norm-vector` | boolean |  |  |  |  |  | Comseg `norm_vector` parameter |
| `--use-comseg` | boolean |  |  |  |  |  | Whether to run comseg segmentation |

## explorer

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--lazy` | boolean |  |  |  |  | true | If `True`, will not load the full images in memory (except if the image memory is below `ram_threshold_gb`) |
| `--pixel-size` | number |  |  |  |  | 0.2125 | Number of microns in a pixel. Invalid value can lead to inconsistent scales in the Explorer. |
| `--ram-threshold-gb` | number |  |  |  |  | 4.0 | Threshold (in gygabytes) from which image can be loaded in memory. |

## filtering

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--min-area-microns2` | number |  |  |  |  | 0.0 | Cells with an area less than this value will be filtered. The unit is in microns^2, and used by Baysor/Comseg. Not used by Proseg. |
| `--min-area-pixels2` | number |  |  |  |  | 0.0 | Cells with an area less than this value will be filtered. The unit is in pixels^2, and used by Stardist/Cellpose. |
| `--min-intensity-ratio` | number |  |  |  |  |  | Cells whose mean channel intensity is less than `min_intensity_ratio * quantile_90` will be filtered. |
| `--min-transcripts` | number |  |  |  |  |  | Cells with less transcripts than this value will be filtered. |

## fluorescence_annotation

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--fluorescence-cell-type-key` | string |  |  |  |  |  | Key of `sdata.obs` containing the cell-types |
| `--marker-cell-dict` | string |  |  |  |  |  | Dictionary mapping whose keys are marker channel names and values are the cell types associated to each marker. Should be provided as a string representation of a python dictionary. |
| `--use-fluorescence-annotation` | boolean |  |  |  |  |  | Whether to run cell-type annotation based on a marker-to-cell dictionary |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
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
| `--clahe-kernel-size` | number |  |  |  |  |  | Parameter for skimage.exposure.equalize_adapthist (applied before running the segmentation method) |
| `--clip-limit` | number |  |  |  |  |  | Parameter for skimage.exposure.equalize_adapthist (applied before running the segmentation method) |
| `--gaussian-sigma` | number |  |  |  |  |  | Parameter for scipy gaussian_filter (applied before running the segmentation method) |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  | matches ^\S+\.csv$ |  | Path to comma-separated file containing information about the samples in the experiment. |
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

## patches

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--image-scale` | string |  |  |  |  |  | The scale to be used for the image patches (e.g., `"scale1"`). By default, uses the highest resolution scale. |
| `--patch-overlap-microns` | number |  |  |  |  |  | Number of overlapping microns between the patches. We advise to choose approximately twice the diameter of a cell |
| `--patch-overlap-pixel` | number |  |  |  |  |  | Number of overlapping pixels between the patches. We advise to choose approximately twice the diameter of a cell |
| `--patch-width-microns` | number |  |  |  |  |  | Width (and height) of each patch in microns |
| `--patch-width-pixel` | number |  |  |  |  |  | Width (and height) of each patch in pixels |
| `--prior-shapes-key` | string |  |  |  |  |  | Optional name of the boundaries element to use as a segmentation prior. Either a column name for the transcript dataframe, or a key of `sdata` containing the shapes names. If combining cellpose with proseg/baysor/comseg, it will be set automatically to `'cellpose_boundaries'`. |
| `--unassigned-value` | string |  |  |  |  |  | If `prior_shapes_key` is provided, this is the value given to transcripts that are not inside any cell (if it's already 0, don't provide this argument) |

## proseg

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--command-line-suffix` | string |  |  |  |  |  | String suffix to add to the proseg command line. This can be used to add extra parameters to the proseg command line. |
| `--infer-presets` | boolean |  |  |  |  |  | Whether to infer the proseg presets based on the columns of the transcripts dataframe. |
| `--use-proseg` | boolean |  |  |  |  |  | Whether to run proseg segmentation |
| `--visium-hd-prior-shapes-key` | string |  |  |  |  |  | **Only for Visium HD data.** Key of `sdata` containing the prior cell boundaries. If `'auto'`, use the latest performed segmentation (e.g., stardist or the 10X Genomics segmentation). If combining stardist with proseg, it will be set automatically to `'stardist_boundaries'`. |

## reader

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--technology` | string | yes |  | `xenium`, `merscope`, `cosmx`, `visium_hd`, `molecular_cartography`, `macsima`, `phenocycler`, `hyperion`, `ome_tif`, `toy_dataset` |  | xenium | Technology used for the spatial data, e.g., 'xenium', 'merscope', ... |
| `--visium-hd-imread-page` | number |  |  |  |  |  | Optional page for the imageio reader |

## scanpy_preprocessing

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--check-counts` | boolean |  |  |  |  |  | Whether to check that adata.X contains counts |
| `--hvg` | boolean |  |  |  |  |  | Whether to compute highly variable genes before computing the UMAP and clustering |
| `--resolution` | number |  |  |  |  |  | Resolution parameter for the leiden clustering |
| `--use-scanpy-preprocessing` | boolean |  |  |  |  |  | Whether to run scanpy preprocessing |

## spaceranger_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--spaceranger-probeset` | string (file path) |  |  |  | matches ^\S+\.csv$ |  | Location of Space Ranger probeset file. |
| `--spaceranger-reference` | string (file or directory path) |  |  |  |  | https://cf.10xgenomics.com/supp/spatial-exp/refdata-gex-GRCh38-2020-A.tar.gz | Location of Space Ranger reference directory. May be packed as `tar.gz` file. |

## stardist

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--nms-thresh` | number |  |  |  |  |  | Stardist `nms_thresh` parameter |
| `--prob-thresh` | number |  |  |  |  |  | Stardist `prob_thresh` parameter |
| `--stardist-channels` | string |  |  |  |  |  | Optional channel name(s) to use for stardist segmentation. If multiple, separate by space, comma or pipe characters. |
| `--stardist-kwargs` | string |  |  |  |  |  | Additional stardist parameters as a python dict string |
| `--stardist-model-type` | string |  |  |  |  |  | Name of stardist model to use |
| `--use-stardist` | boolean |  |  |  |  |  | Whether to run stardist segmentation |

## tissue_segmentation

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--level` | number |  |  |  |  |  | Level of the image pyramid to use for tissue segmentation |
| `--mode` | string |  |  | `staining`, `saturation` |  |  | Mode for the tissue segmentation: 'staining' or 'saturation' (for H&E images). |
| `--tissue-segmentation-kwargs` | string |  |  |  |  |  | Additional tissue segmentation parameters as a python dict string |
| `--use-tissue-segmentation` | boolean |  |  |  |  |  | Whether to run tissue segmentation |

<!-- Generated from nf-core/sopa@0b959963a3984ff78725209113d9ecdb78cef0b6. Do not edit by hand. -->
