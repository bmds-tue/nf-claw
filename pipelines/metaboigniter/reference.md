---
name: metaboigniter
version: 2.0.1
commit: 55d82547604fcae3b6557fe7a3c442b623184f34
---

# metaboigniter — full parameter reference

nf-core/metaboigniter pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## alignment_and_linking

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--algorithm-distance-intensity-exponent-featurelinkerunlabeledkd-openms` | number |  | yes |  |  | `1` | Differences in relative intensity ([0-1]) are raised to this power (using 1 or 2 will be fast, everything else is REALLY slow) |
| `--algorithm-distance-intensity-log-transform-featurelinkerunlabeledkd-openms` | string |  | yes | `enabled`, `disabled` |  | `enabled` | Log-transform intensities? If disabled, d = \|int_f2 - int_f1\| / int_max. If enabled, d = \|log(int_f2 + 1) - log(int_f1 + 1)\| / log(int_max + 1)) |
| `--algorithm-distance-intensity-weight-featurelinkerunlabeledkd-openms` | number |  | yes |  |  | `1` | Final intensity distances are weighted by this factor |
| `--algorithm-distance-mz-exponent-featurelinkerunlabeledkd-openms` | number |  | yes |  |  | `2` | Normalized ([0-1], relative to 'max_difference') m/z differences are raised to this power (using 1 or 2 will be fast, everything else is REALLY slow) |
| `--algorithm-distance-mz-weight-featurelinkerunlabeledkd-openms` | number |  | yes |  |  | `1` | Final m/z distances are weighted by this factor |
| `--algorithm-distance-rt-exponent-featurelinkerunlabeledkd-openms` | number |  | yes |  |  | `1` | Normalized RT differences ([0-1], relative to 'max_difference') are raised to this power (using 1 or 2 will be fast, everything else is REALLY slow) |
| `--algorithm-distance-rt-weight-featurelinkerunlabeledkd-openms` | number |  | yes |  |  | `1` | Final RT distances are weighted by this factor |
| `--algorithm-link-adduct-merging-featurelinkerunlabeledkd-openms` | string |  |  | `Identical`, `With_unknown_adducts`, `Any` |  | `Any` | whether to only allow the same adduct for linking (Identical), also allow linking features with adduct-free ones, or disregard adducts (Any). |
| `--algorithm-link-charge-merging-featurelinkerunlabeledkd-openms` | string |  |  | `Identical`, `With_charge_zero`, `Any` |  | `With_charge_zero` | whether to disallow charge mismatches (Identical), allow to link charge zero (i.e., unknown charge state) with every charge state, or disregard charges (Any). |
| `--algorithm-link-mz-tol-featurelinkerunlabeledkd-openms` | number |  |  |  |  | `10` | m/z tolerance (in ppm or Da) |
| `--algorithm-link-rt-tol-featurelinkerunlabeledkd-openms` | number |  |  |  |  | `30` | Width of RT tolerance window (sec) |
| `--algorithm-lowess-delta-featurelinkerunlabeledkd-openms` | number |  | yes |  |  | `-1` | Nonnegative parameter which may be used to save computations (recommended value is 0.01 of the range of the input, e.g. for data ranging from 1000 seconds to 2000 seconds, it could be set to 10). Setting a negative value will automatically do this. |
| `--algorithm-lowess-extrapolation-type-featurelinkerunlabeledkd-openms` | string |  | yes | `two-point-linear`, `four-point-linear`, `global-linear` |  | `four-point-linear` | Method to use for extrapolation outside the data range. 'two-point-linear': Uses a line through the first and last point to extrapolate. 'four-point-linear': Uses a line through the first and second point to extrapolate in front and and a line through the last and second-to-last point in the end. 'global-linear': Uses a linear regression to fit a line through all data points and use it for interpolation. |
| `--algorithm-lowess-interpolation-type-featurelinkerunlabeledkd-openms` | string |  | yes | `linear`, `cspline`, `akima` |  | `cspline` | Method to use for interpolation between datapoints computed by lowess. 'linear': Linear interpolation. 'cspline': Use the cubic spline for interpolation. 'akima': Use an akima spline for interpolation |
| `--algorithm-lowess-num-iterations-featurelinkerunlabeledkd-openms` | integer |  | yes |  |  | `3` | Number of robustifying iterations for lowess fitting. |
| `--algorithm-lowess-span-featurelinkerunlabeledkd-openms` | number |  | yes |  |  | `0.666666666666667` | Fraction of datapoints (f) to use for each local regression (determines the amount of smoothing). Choosing this parameter in the range .2 to .8 usually results in a good fit. |
| `--algorithm-max-num-peaks-considered-mapalignerposeclustering-openms` | integer |  |  |  |  | `1000` | The maximal number of peaks/features to be considered per map. To use all, set to '-1'. |
| `--algorithm-mz-unit-featurelinkerunlabeledkd-openms` | string |  |  | `ppm`, `Da` |  | `ppm` | Unit of m/z tolerance |
| `--algorithm-nr-partitions-featurelinkerunlabeledkd-openms` | integer |  |  |  |  | `100` | Number of partitions in m/z space |
| `--algorithm-pairfinder-distance-intensity-exponent-mapalignerposeclustering-openms` | number |  | yes |  |  |  | Differences in relative intensity ([0-1]) are raised to this power (using 1 or 2 will be fast, everything else is REALLY slow) |
| `--algorithm-pairfinder-distance-intensity-log-transform-mapalignerposeclustering-openms` | string |  | yes | `enabled`, `disabled` |  | `disabled` | Log-transform intensities? If disabled, d = \|int_f2 - int_f1\| / int_max. If enabled, d = \|log(int_f2 + 1) - log(int_f1 + 1)\| / log(int_max + 1)) |
| `--algorithm-pairfinder-distance-intensity-weight-mapalignerposeclustering-openms` | number |  | yes |  |  |  | Final intensity distances are weighted by this factor |
| `--algorithm-pairfinder-distance-mz-exponent-mapalignerposeclustering-openms` | number |  | yes |  |  |  | Normalized ([0-1], relative to 'max_difference') m/z differences are raised to this power (using 1 or 2 will be fast, everything else is REALLY slow) |
| `--algorithm-pairfinder-distance-mz-max-difference-mapalignerposeclustering-openms` | number |  |  |  |  | `0.3` | Never pair features with larger m/z distance (unit defined by 'unit') |
| `--algorithm-pairfinder-distance-mz-unit-mapalignerposeclustering-openms` | string |  |  | `Da`, `ppm` |  | `Da` | Unit of the 'max_difference' parameter |
| `--algorithm-pairfinder-distance-mz-weight-mapalignerposeclustering-openms` | number |  | yes |  |  |  | Final m/z distances are weighted by this factor |
| `--algorithm-pairfinder-distance-rt-exponent-mapalignerposeclustering-openms` | number |  | yes |  |  |  | Normalized RT differences ([0-1], relative to 'max_difference') are raised to this power (using 1 or 2 will be fast, everything else is REALLY slow) |
| `--algorithm-pairfinder-distance-rt-max-difference-mapalignerposeclustering-openms` | number |  |  |  |  | `100.0` | Never pair features with a larger RT distance (in seconds). |
| `--algorithm-pairfinder-distance-rt-weight-mapalignerposeclustering-openms` | number |  | yes |  |  |  | Final RT distances are weighted by this factor |
| `--algorithm-pairfinder-ignore-adduct-mapalignerposeclustering-openms` | boolean |  | yes |  |  | `true` | true [default]: pairing requires equal adducts (or at least one without adduct annotation); true: Pairing irrespective of adducts |
| `--algorithm-pairfinder-ignore-charge-mapalignerposeclustering-openms` | boolean |  |  |  |  |  | false [default]: pairing requires equal charge state (or at least one unknown charge '0'); true: Pairing irrespective of charge state |
| `--algorithm-pairfinder-second-nearest-gap-mapalignerposeclustering-openms` | number |  | yes |  |  |  | Only link features whose distance to the second nearest neighbors (for both sides) is larger by 'second_nearest_gap' than the distance between the matched pair itself. |
| `--algorithm-pairfinder-use-identifications-mapalignerposeclustering-openms` | boolean |  | yes |  |  |  | Never link features that are annotated with different peptides (features without ID's always match; only the best hit per peptide identification is considered). |
| `--algorithm-superimposer-dump-buckets-mapalignerposeclustering-openms` | string |  | yes |  |  |  | [DEBUG] If non-empty, base filename where hash table buckets will be dumped to. A serial number for each invocation will be appended automatically. |
| `--algorithm-superimposer-dump-pairs-mapalignerposeclustering-openms` | string |  | yes |  |  |  | [DEBUG] If non-empty, base filename where the individual hashed pairs will be dumped to (large!). A serial number for each invocation will be appended automatically. |
| `--algorithm-superimposer-max-scaling-mapalignerposeclustering-openms` | number |  | yes |  |  |  | Maximal scaling which is considered during histogramming. The minimal scaling is the reciprocal of this. |
| `--algorithm-superimposer-max-shift-mapalignerposeclustering-openms` | number |  | yes |  |  |  | Maximal shift which is considered during histogramming (in seconds). This applies for both directions. |
| `--algorithm-superimposer-mz-pair-max-distance-mapalignerposeclustering-openms` | number |  |  |  |  | `0.5` | Maximum of m/z deviation of corresponding elements in different maps. This condition applies to the pairs considered in hashing. |
| `--algorithm-superimposer-num-used-points-mapalignerposeclustering-openms` | integer |  |  |  |  | `2000` | Maximum number of elements considered in each map (selected by intensity). Use this to reduce the running time and to disregard weak signals during alignment. For using all points, set this to -1. |
| `--algorithm-superimposer-rt-pair-distance-fraction-mapalignerposeclustering-openms` | number |  | yes |  |  | `0.1` | Within each of the two maps, the pairs considered for pose clustering must be separated by at least this fraction of the total elution time interval (i.e., max - min). |
| `--algorithm-superimposer-scaling-bucket-size-mapalignerposeclustering-openms` | number |  | yes |  |  | `0.005` | The scaling of the retention time interval is being hashed into buckets of this size during pose clustering. A good choice for this would be a bit smaller than the error you would expect from repeated runs. |
| `--algorithm-superimposer-shift-bucket-size-mapalignerposeclustering-openms` | number |  | yes |  |  |  | The shift at the lower (respectively, higher) end of the retention time interval is being hashed into buckets of this size during pose clustering. A good choice for this would be about the time between consecutive MS scans. |
| `--algorithm-warp-enabled-featurelinkerunlabeledkd-openms` | boolean |  |  |  |  | `true` | Whether or not to internally warp feature RTs using LOWESS transformation before linking (reported RTs in results will always be the original RTs) |
| `--algorithm-warp-max-nr-conflicts-featurelinkerunlabeledkd-openms` | integer |  | yes |  |  | `0` | Allow up to this many conflicts (features from the same map) per connected component to be used for alignment (-1 means allow any number of conflicts) |
| `--algorithm-warp-max-pairwise-log-fc-featurelinkerunlabeledkd-openms` | number |  | yes |  |  | `0.5` | Maximum absolute log10 fold change between two compatible signals during compatibility graph construction. Two signals from different maps will not be connected by an edge in the compatibility graph if absolute log fold change exceeds this limit (they might still end up in the same connected component, however). Note: this does not limit fold changes in the linking stage, only during RT alignment, where we try to find high-quality alignment anchor points. Setting this to a value < 0 disables the FC check. |
| `--algorithm-warp-min-rel-cc-size-featurelinkerunlabeledkd-openms` | number |  | yes |  |  | `0.5` | Only connected components containing compatible features from at least max(2, (warp_min_occur * number_of_input_maps)) input maps are considered for computing the warping function |
| `--algorithm-warp-mz-tol-featurelinkerunlabeledkd-openms` | number |  |  |  |  | `5.0` | m/z tolerance (in ppm or Da) |
| `--algorithm-warp-rt-tol-featurelinkerunlabeledkd-openms` | number |  |  |  |  | `100.0` | Width of RT tolerance window (sec) |
| `--invert-maprttransformer-openms` | boolean |  | yes |  |  |  | Invert transformation (approximatively) before applying it |
| `--keep-subelements-featurelinkerunlabeledkd-openms` | boolean |  | yes |  |  |  | For consensusXML input only: If set, the sub-features of the inputs are transferred to the output. |
| `--model-b-spline-boundary-condition-maprttransformer-openms` | integer |  | yes |  |  |  | Boundary condition at B-spline endpoints: 0 (value zero), 1 (first derivative zero) or 2 (second derivative zero) |
| `--model-b-spline-extrapolate-maprttransformer-openms` | string |  | yes | `linear`, `b_spline`, `constant`, `global_linear` |  | `linear` | Method to use for extrapolation beyond the original data range. 'linear': Linear extrapolation using the slope of the B-spline at the corresponding endpoint. 'b_spline': Use the B-spline (as for interpolation). 'constant': Use the constant value of the B-spline at the corresponding endpoint. 'global_linear': Use a linear fit through the data (which will most probably introduce discontinuities at the ends of the data range). |
| `--model-b-spline-num-nodes-maprttransformer-openms` | integer |  | yes |  |  |  | Number of nodes for B-spline fitting. Overrides 'wavelength' if set (to two or greater). A lower value means more smoothing. |
| `--model-b-spline-wavelength-maprttransformer-openms` | number |  | yes |  |  |  | Determines the amount of smoothing by setting the number of nodes for the B-spline. The number is chosen so that the spline approximates a low-pass filter with this cutoff wavelength. The wavelength is given in the same units as the data; a higher value means more smoothing. '0' sets the number of nodes to twice the number of input points. |
| `--model-interpolated-extrapolation-type-maprttransformer-openms` | string |  | yes | `two-point-linear`, `four-point-linear`, `global-linear` |  | `two-point-linear` | Type of extrapolation to apply: two-point-linear: use the first and last data point to build a single linear model, four-point-linear: build two linear models on both ends using the first two / last two points, global-linear: use all points to build a single linear model. Note that global-linear may not be continuous at the border. |
| `--model-interpolated-interpolation-type-maprttransformer-openms` | string |  | yes | `linear`, `cspline`, `akima` |  | `cspline` | Type of interpolation to apply. |
| `--model-linear-symmetric-regression-maprttransformer-openms` | boolean |  | yes |  |  |  | Perform linear regression on 'y - x' vs. 'y + x', instead of on 'y' vs. 'x'. |
| `--model-linear-x-datum-max-maprttransformer-openms` | number |  | yes |  |  | `1000000000000000` | Maximum x value |
| `--model-linear-x-datum-min-maprttransformer-openms` | number |  | yes |  |  | `1e-15` | Minimum x value |
| `--model-linear-x-weight-maprttransformer-openms` | string |  | yes | `1/x`, `1/x2`, `ln(x)`, `x` |  | `x` | Weight x values |
| `--model-linear-y-datum-max-maprttransformer-openms` | number |  | yes |  |  | `1000000000000000` | Maximum y value |
| `--model-linear-y-datum-min-maprttransformer-openms` | number |  | yes |  |  | `1e-15` | Minimum y value |
| `--model-linear-y-weight-maprttransformer-openms` | string |  | yes | `1/y`, `1/y2`, `ln(y)`, `y` |  | `y` | Weight y values |
| `--model-lowess-delta-maprttransformer-openms` | number |  | yes |  |  | `-1` | Nonnegative parameter which may be used to save computations (recommended value is 0.01 of the range of the input, e.g. for data ranging from 1000 seconds to 2000 seconds, it could be set to 10). Setting a negative value will automatically do this. |
| `--model-lowess-extrapolation-type-maprttransformer-openms` | string |  | yes | `two-point-linear`, `four-point-linear`, `global-linear` |  | `four-point-linear` | Method to use for extrapolation outside the data range. 'two-point-linear': Uses a line through the first and last point to extrapolate. 'four-point-linear': Uses a line through the first and second point to extrapolate in front and and a line through the last and second-to-last point in the end. 'global-linear': Uses a linear regression to fit a line through all data points and use it for interpolation. |
| `--model-lowess-interpolation-type-maprttransformer-openms` | string |  | yes | `linear`, `cspline`, `akima` |  | `cspline` | Method to use for interpolation between datapoints computed by lowess. 'linear': Linear interpolation. 'cspline': Use the cubic spline for interpolation. 'akima': Use an akima spline for interpolation |
| `--model-lowess-num-iterations-maprttransformer-openms` | integer |  | yes |  |  |  | Number of robustifying iterations for lowess fitting. |
| `--model-lowess-span-maprttransformer-openms` | number |  | yes |  |  |  | Fraction of datapoints (f) to use for each local regression (determines the amount of smoothing). Choosing this parameter in the range .2 to .8 usually results in a good fit. |
| `--model-type-maprttransformer-openms` | string |  | yes | `none`, `linear`, `b_spline`, `lowess`, `interpolated` |  | `none` | Type of model |
| `--store-original-rt-maprttransformer-openms` | boolean |  | yes |  |  |  | Store the original retention times (before transformation) as meta data in the output file |

## annotation

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--adducts-neg` | string |  |  |  |  | `H-1:-:0.8 H-3O-1:-:0.2` | possible negative adducts for adduct detection in the format of adduct:charge:probablity |
| `--adducts-pos` | string |  |  |  |  | `H:+:0.6 Na:+:0.1 NH4:+:0.1 H-1O-1:+:0.1 H-3O-2:+:0.1` | possible positive adducts for adduct detection in the format of adduct:charge:probablity |
| `--algorithm-metabolitefeaturedeconvolution-charge-max-metaboliteadductdecharger-openms` | integer |  |  |  |  | `1` | Maximal possible charge |
| `--algorithm-metabolitefeaturedeconvolution-charge-min-metaboliteadductdecharger-openms` | integer |  |  |  |  | `1` | Minimal possible charge |
| `--algorithm-metabolitefeaturedeconvolution-charge-span-max-metaboliteadductdecharger-openms` | integer |  |  |  |  | `1` | Maximal range of charges for a single analyte, i.e. observing q1=[5,6,7] implies span=3. Setting this to 1 will only find adduct variants of the same charge |
| `--algorithm-metabolitefeaturedeconvolution-default-map-label-metaboliteadductdecharger-openms` | string |  | yes |  |  | `decharged features` | Label of map in output consensus file where all features are put by default |
| `--algorithm-metabolitefeaturedeconvolution-intensity-filter-metaboliteadductdecharger-openms` | boolean |  |  |  |  |  | Enable the intensity filter, which will only allow edges between two equally charged features if the intensity of the feature with less likely adducts is smaller than that of the other feature. It is not used for features of different charge. |
| `--algorithm-metabolitefeaturedeconvolution-mass-max-diff-metaboliteadductdecharger-openms` | number |  |  |  |  | `5` | Maximum allowed mass tolerance per feature. Defines a symmetric tolerance window around the feature. When looking at possible feature pairs, the allowed feature-wise errors are combined for consideration of possible adduct shifts. For ppm tolerances, each window is based on the respective observed feature mz (instead of putative experimental mzs causing the observed one)! |
| `--algorithm-metabolitefeaturedeconvolution-max-minority-bound-metaboliteadductdecharger-openms` | integer |  |  |  |  | `1` | Limits allowed adduct compositions and changes between compositions in the underlying graph optimization problem by introducing a probability-based threshold: the minority bound sets the maximum count of the least probable adduct (according to 'potential_adducts' param) within a charge variant with maximum charge only containing the most likely adduct otherwise. E.g., for 'charge_max' 4 and 'max_minority_bound' 2 with most probable adduct being H+ and least probable adduct being Na+, this will allow adduct compositions of '2(H+),2(Na+)' but not of '1(H+),3(Na+)'. Further, adduct compositions/changes less likely than '2(H+),2(Na+)' will be discarded as well. |
| `--algorithm-metabolitefeaturedeconvolution-max-neutrals-metaboliteadductdecharger-openms` | integer |  |  |  |  | `1` | Maximal number of neutral adducts(q=0) allowed. Add them in the 'potential_adducts' section! |
| `--algorithm-metabolitefeaturedeconvolution-min-rt-overlap-metaboliteadductdecharger-openms` | number |  |  |  |  | `0.66` | Minimum overlap of the convex hull' RT intersection measured against the union from two features (if CHs are given) |
| `--algorithm-metabolitefeaturedeconvolution-q-try-metaboliteadductdecharger-openms` | string |  |  | `feature`, `heuristic`, `all` |  | `feature` | Try different values of charge for each feature according to the above settings ('heuristic' [does not test all charges, just the likely ones] or 'all' ), or leave feature charge untouched ('feature'). |
| `--algorithm-metabolitefeaturedeconvolution-retention-max-diff-local-metaboliteadductdecharger-openms` | number |  |  |  |  | `1` | Maximum allowed RT difference between between two co-features, after adduct shifts have been accounted for (if you do not have any adduct shifts, this value should be equal to 'retention_max_diff', otherwise it should be smaller!) |
| `--algorithm-metabolitefeaturedeconvolution-retention-max-diff-metaboliteadductdecharger-openms` | number |  |  |  |  | `1` | Maximum allowed RT difference between any two features if their relation shall be determined |
| `--algorithm-metabolitefeaturedeconvolution-unit-metaboliteadductdecharger-openms` | string |  |  | `Da`, `ppm` |  | `ppm` | Unit of the 'max_difference' parameter |
| `--algorithm-metabolitefeaturedeconvolution-use-minority-bound-metaboliteadductdecharger-openms` | boolean |  |  |  |  | `true` | Prune the considered adduct transitions by transition probabilities. |

## generic_controls

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--identification` | boolean |  |  |  |  |  | If set to true, identification will be performed. Remember to set identification specific parameters |
| `--ms2-collection-model` | string |  |  | `separate`, `paired` |  | `paired` | Set wether the MS2 collections have been done on all the MS1 data. If there is a separate MS2 file, set to separate |
| `--parallel-linking` | boolean |  |  |  |  |  | If set, the linking will be performed in parallel, see nr_partitions in linking |
| `--polarity` | string |  |  | `positive`, `negative` |  | `positive` | Polarity of the data |
| `--requantification` | boolean |  |  |  |  |  | If set to true, requantification will be performed |
| `--skip-adduct-detection` | boolean |  | yes |  |  |  | If true, the adduct detection will be skipped |
| `--skip-alignment` | boolean |  | yes |  |  |  | If true, the alignment will be skipped |
| `--skip-centroiding` | boolean |  | yes |  |  | `true` | If true, the centroiding will be skipped |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean |  | yes |  |  |  | Display help text. |
| `--hook-url` | string |  | yes |  |  |  | Incoming hook URL for messaging service |
| `--max-multiqc-email-size` | string |  | yes |  | matches `^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$` | `25.MB` | File size limit when attaching MultiQC reports to summary emails. |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | `copy` | Method used to save pipeline results to output directory. |
| `--validate-params` | boolean |  | yes |  |  | `true` | Boolean whether to validate parameters against the schema at runtime |
| `--validationFailUnrecognisedParams` | boolean |  | yes |  |  |  | Validation of parameters fails when an unrecognised parameter is found. |
| `--validationLenientMode` | boolean |  | yes |  |  |  | Validation of parameters in lenient more. |
| `--validationShowHiddenParams` | boolean |  | yes |  |  |  | Show all params when using `--help` |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  | matches `^\S+\.csv$` |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--save-intermeds` | boolean |  | yes |  |  |  | Save intermediate files |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/configs/master` | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | `master` | Git commit id for Institutional configs. |

## mapping_and_identification

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--annotate-ids-with-subelements-pyopenms` | boolean |  | yes |  |  | `true` | Store the map index of the sub-feature in the peptide ID. |
| `--ignore-msms-mapping-charge-pyopenms` | boolean |  | yes |  |  | `false` | When mapping MS2 precursors to consensus elements, ignore the charge. Specially beneficial in negative mode, if the charges of the consensus features are and spectra are different |
| `--library-path-ms2query` | string |  | yes |  |  |  | path to ms2query library |
| `--measure-from-subelements-pyopenms` | boolean |  | yes |  |  | `true` | Match using RT and m/z of sub-features instead of consensus RT and m/z. A consensus feature matches if any of its sub-features matches. |
| `--mgf-splitmgf-pyopenms` | integer |  | yes |  |  | `1` | If higher than one, parameter files will be split into the selected number. The result of the identification will be perform on each part separately |
| `--models-dir-ms2query` | string |  | yes |  |  | `models` | If running offline, this directory has to contain all the files necessary for running MS2Query |
| `--ms2-feature-selection` | string |  | yes | `quality`, `intensity` |  | `quality` | whether feature quality or intensity should be used for feature selection |
| `--ms2-iterations` | integer |  | yes |  |  | `3` | Number of iterations that should be performed to extract the C13 isotope pattern. If no peak is found (C13 distance) the function will abort. Be careful with noisy data - since this can lead to wrong isotope patterns |
| `--ms2-normalized-intensity` | boolean |  | yes |  |  | `true` | If ture, normalized intesity will be used for selecting the best feature |
| `--ms2-ppm-map` | number |  | yes |  |  | `10` | PPM for detecting MS C13 |
| `--ms2-use-feature-ionization` | boolean |  |  |  |  |  | If set, detected adduct will be used in identification |
| `--mz-tolerance-pyopenms` | number |  |  |  |  | `20` | mz tolerance (ppm) for finding C13 |
| `--offline-model-ms2query` | boolean |  | yes |  |  |  | If set, the workflow expects the models to be in models_dir_ms2query |
| `--rt-tolerance-pyopenms` | number |  |  |  |  | `5` | rt tolerance for finding C13 |
| `--run-ms2query` | boolean |  |  |  |  |  | If set, MS2Query will be run |
| `--run-sirius` | boolean |  |  |  |  |  | If set SIRIUS will run |
| `--run-umapped-spectra` | boolean |  | yes |  |  |  | If set identification will be performed on unmapped MS2 spectra |
| `--sirius-email` | string |  |  |  |  |  | E-mail for your SIRIUS account. |
| `--sirius-fingerid-db` | string |  |  |  |  |  | Search structures in the Union of the given databases db-name1,db-name2,db-name3. If no database is given all possible molecular formulas will be respected (no database is used). Example: possible DBs: ALL,BIO,PUBCHEM,MESH,HMDB,KNAPSACK,CHEBI,PUBMED,KEGG,HSDB,MACONDA,METACYC,GNPS,ZINCBIO,UNDP,YMDB,PLANTCYC,NORMAN,ADDITIONAL,PUBCHEMANNOTATIONBIO,PUBCHEMANNOTATIONDRUG,PUBCHEMANNOTATIONSAFETYANDTOXIC,PUBCHEMANNOTATIONFOOD,KEGGMINE,ECOCYCMINE,YMDBMINE |
| `--sirius-password` | string |  |  |  |  |  | Password for your SIRIUS account. |
| `--sirius-project-ignore-formula` | boolean |  | yes |  |  |  | Ignore given molecular formula in internal .ms format, while processing. |
| `--sirius-project-loglevel` | string |  | yes | `SEVERE`, `WARNING`, `INFO`, `FINER`, `ALL` |  | `WARNING` | Set logging level of the Jobs SIRIUS will execute. Valid values: SEVERE, WARNING, INFO, FINER, ALL |
| `--sirius-project-maxmz` | number |  | yes |  |  | `-1` | Just consider compounds with a precursor mz lower or equal this maximum mz. All other compounds in the input file are ignored.= |
| `--sirius-runfid` | boolean |  |  |  |  |  | If set, FingerID will be run. This has to be run together with run_sirius |
| `--sirius-runpassatutto` | boolean |  |  |  |  |  | If set, passatutto will be run |
| `--sirius-sirius-candidates` | integer |  |  |  |  | `10` | The number of formula candidates in the SIRIUS output |
| `--sirius-sirius-candidates-per-ion` | integer |  |  |  |  | `1` | Minimum number of candidates in the output for each ionization. Set to force output of results for each possible ionization, even if not part of highest ranked results. |
| `--sirius-sirius-compound-timeout` | number |  | yes |  |  | `100` | Time out in seconds per fragmentation tree computations. 0 for an infinite amount of time |
| `--sirius-sirius-db` | string |  |  |  |  |  | Search formulas in the Union of the given databases db-name1,db-name2,db-name3. If no database is given all possible molecular formulas will be respected (no database is used). Example: possible DBs: ALL,BIO,PUBCHEM,MESH,HMDB,KNAPSACK,CHEBI,PUBMED,KEGG,HSDB,MACONDA,METACYC,GNPS,ZINCBIO,UNDP,YMDB,PLANTCYC,NORMAN,ADDITIONAL,PUBCHEMANNOTATIONBIO,PUBCHEMANNOTATIONDRUG,PUBCHEMANNOTATIONSAFETYANDTOXIC,PUBCHEMANNOTATIONFOOD,KEGGMINE,ECOCYCMINE,YMDBMINE |
| `--sirius-sirius-elements-considered` | string |  | yes |  |  | `SBrClBSe` | Set the allowed elements for rare element detection. Write SBrClBSe to allow the elements S,Br,Cl,B and Se. |
| `--sirius-sirius-elements-enforced` | string |  | yes |  |  | `CHNOP` | Enforce elements for molecular formula determination. Write CHNOPSCl to allow the elements C, H, N, O, P, S and Cl. Add numbers in brackets to restrict the minimal and maximal allowed occurrence of these elements: CHNOP[5]S[8]Cl[1-2]. When one number is given then it is interpreted as upper bound. |
| `--sirius-sirius-formulas` | string |  | yes |  |  |  | Specify the neutral molecular formula of the measured compound to compute its tree or a list of candidate formulas the method should discriminate. Omit this option if you want to consider all possible molecular formulas |
| `--sirius-sirius-ions-considered` | string |  |  |  |  | `[M+H]+,[M+K]+,[M+Na]+,[M+H-H2O]+,[M+H-H4O2]+,[M+NH4]+,[M-H]-,[M+Cl]-,[M-H2O-H]-,[M+Br]-` | the iontype/adduct of the MS/MS data. Example: [M+H]+, [M-H]-, [M+Cl]-, [M+Na]+, [M]+. You can also provide a comma separated list of adducts. |
| `--sirius-sirius-ions-enforced` | string |  | yes |  |  |  | The iontype/adduct of the MS/MS data. Example: [M+H]+, [M-H]-, [M+Cl]-, [M+Na]+, [M]+. You can also provide a comma separated list of adducts. |
| `--sirius-sirius-no-isotope-filter` | boolean |  | yes |  |  |  | Disable molecular formula filter. When filtering is enabled, molecular formulas are excluded if their theoretical isotope pattern does not match the theoretical one, even if their MS/MS pattern has high score. |
| `--sirius-sirius-no-isotope-score` | boolean |  | yes |  |  |  | Disable isotope pattern score. |
| `--sirius-sirius-no-recalibration` | boolean |  |  |  |  |  | Disable recalibration of input spectra |
| `--sirius-sirius-ppm-max` | number |  |  |  |  | `10` | Maximum allowed mass deviation in ppm for decomposing masses (ppm) |
| `--sirius-sirius-ppm-max-ms2` | number |  |  |  |  | `10` | Maximum allowed mass deviation in ppm for decomposing masses in MS2 (ppm).If not specified, the same value as for the MS1 is used. |
| `--sirius-sirius-profile` | string |  |  | `default`, `qtof`, `orbitrap`, `fticr` |  | `default` | Name of the configuration profile |
| `--sirius-sirius-solver` | string |  | yes |  |  | `CLP` | For GUROBI and CPLEX environment variables need to be configured. |
| `--sirius-sirius-tree-timeout` | number |  | yes |  |  | `100` | Time out in seconds per fragmentation tree computations. 0 for an infinite amount of time |
| `--sirius-split` | boolean |  |  |  |  |  | If set, SIRIUS will be run in parallel. See mgf_splitmgf_pyopenms parameter for segmentation |
| `--split-consensus-parts` | integer |  |  |  |  | `20` | For running MS2 mapping in parallel set this higher than 1 |
| `--train-library-ms2query` | boolean |  | yes |  |  |  | If set, the model training will be performed using library_path_ms2query |

## max_job_request_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--max-cpus` | integer |  | yes |  |  | `16` | Maximum number of CPUs that can be requested for any single job. |
| `--max-memory` | string |  | yes |  | matches `^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$` | `128.GB` | Maximum amount of memory that can be requested for any single job. |
| `--max-time` | string |  | yes |  | matches `^(\d+\.?\s*(s\|m\|h\|d\|day)\s*)+$` | `240.h` | Maximum amount of time that can be requested for any single job. |

## quantification

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--algorithm-common-chrom-fwhm-featurefindermetabo-openms` | number |  |  |  |  | `5` | Expected chromatographic peak width (in seconds). |
| `--algorithm-common-chrom-peak-snr-featurefindermetabo-openms` | number |  |  |  |  | `3` | Minimum signal-to-noise a mass trace should have. |
| `--algorithm-common-noise-threshold-int-featurefindermetabo-openms` | number |  |  |  |  | `10` | Intensity threshold below which peaks are regarded as noise. |
| `--algorithm-epd-enabled-featurefindermetabo-openms` | boolean |  |  |  |  | `true` | Enable splitting of isobaric mass traces by chromatographic peak detection. Disable for direct injection. |
| `--algorithm-epd-masstrace-snr-filtering-featurefindermetabo-openms` | boolean |  | yes |  |  |  | Apply post-filtering by signal-to-noise ratio after smoothing. |
| `--algorithm-epd-max-fwhm-featurefindermetabo-openms` | number |  | yes |  |  | `60` | Maximum full-width-at-half-maximum of chromatographic peaks (in seconds). Ignored if parameter width_filtering is off or auto. |
| `--algorithm-epd-min-fwhm-featurefindermetabo-openms` | number |  | yes |  |  | `1` | Minimum full-width-at-half-maximum of chromatographic peaks (in seconds). Ignored if parameter width_filtering is off or auto. |
| `--algorithm-epd-width-filtering-featurefindermetabo-openms` | string |  |  | `off`, `fixed`, `auto` |  | `fixed` | Enable filtering of unlikely peak widths. The fixed setting filters out mass traces outside the [min_fwhm, max_fwhm] interval (set parameters accordingly!). The auto setting filters with the 5 and 95% quantiles of the peak width distribution. |
| `--algorithm-ffm-charge-lower-bound-featurefindermetabo-openms` | integer |  | yes |  |  | `1` | Lowest charge state to consider |
| `--algorithm-ffm-charge-upper-bound-featurefindermetabo-openms` | integer |  | yes |  |  | `1` | Highest charge state to consider |
| `--algorithm-ffm-elements-featurefindermetabo-openms` | string |  | yes |  |  | `CHNOPS` | Elements assumes to be present in the sample (this influences isotope detection). |
| `--algorithm-ffm-enable-rt-filtering-featurefindermetabo-openms` | boolean |  |  |  |  | `true` | Require sufficient overlap in RT while assembling mass traces. Disable for direct injection data.. |
| `--algorithm-ffm-isotope-filtering-model-featurefindermetabo-openms` | string |  |  | `metabolites (2% RMS)`, `metabolites (5% RMS)`, `peptides`, `none` |  | `metabolites (5% RMS)` | Remove/score candidate assemblies based on isotope intensities. SVM isotope models for metabolites were trained with either 2% or 5% RMS error. For peptides, an averagine cosine scoring is used. Select the appropriate noise model according to the quality of measurement or MS device. |
| `--algorithm-ffm-local-mz-range-featurefindermetabo-openms` | number |  | yes |  |  | `6.5` | MZ range where to look for isotopic mass traces |
| `--algorithm-ffm-local-rt-range-featurefindermetabo-openms` | number |  | yes |  |  | `10` | RT range where to look for coeluting mass traces |
| `--algorithm-ffm-mz-scoring-13c-featurefindermetabo-openms` | boolean |  |  |  |  |  | Use the 13C isotope peak position (~1.003355 Da) as the expected shift in m/z for isotope mass traces (highly recommended for lipidomics!). Disable for general metabolites (as described in Kenar et al. 2014, MCP.). |
| `--algorithm-ffm-mz-scoring-by-elements-featurefindermetabo-openms` | boolean |  | yes |  |  |  | Use the m/z range of the assumed elements to detect isotope peaks. A expected m/z range is computed from the isotopes of the assumed elements. If enabled, this ignores 'mz_scoring_13C' |
| `--algorithm-ffm-remove-single-traces-featurefindermetabo-openms` | boolean |  | yes |  |  |  | Remove unassembled traces (single traces). |
| `--algorithm-ffm-report-convex-hulls-featurefindermetabo-openms` | boolean |  | yes |  |  |  | Augment each reported feature with the convex hull of the underlying mass traces (increases featureXML file size considerably). |
| `--algorithm-ffm-report-summed-ints-featurefindermetabo-openms` | boolean |  | yes |  |  |  | Set to true for a feature intensity summed up over all traces rather than using monoisotopic trace intensity alone. |
| `--algorithm-ffm-use-smoothed-intensities-featurefindermetabo-openms` | boolean |  | yes |  |  | `true` | Use LOWESS intensities instead of raw intensities. |
| `--algorithm-missing-peakpickerhires-openms` | integer |  | yes |  |  |  | Maximum number of missing points allowed when extending a peak to the left or to the right. A missing data point occurs if the spacing between two subsequent data points exceeds 'spacing_difference * min_spacing'. 'min_spacing' is the smaller of the two spacings from the peak apex to its two neighboring points. Not applicable to chromatograms. |
| `--algorithm-mtd-mass-error-ppm-featurefindermetabo-openms` | number |  |  |  |  | `20` | Allowed mass deviation (in ppm). |
| `--algorithm-mtd-max-trace-length-featurefindermetabo-openms` | number |  | yes |  |  | `-1` | Maximum expected length of a mass trace (in seconds). Set to a negative value to disable maximal length check during mass trace detection. |
| `--algorithm-mtd-min-sample-rate-featurefindermetabo-openms` | number |  | yes |  |  | `0.5` | Minimum fraction of scans along the mass trace that must contain a peak. |
| `--algorithm-mtd-min-trace-length-featurefindermetabo-openms` | number |  | yes |  |  | `5` | Minimum expected length of a mass trace (in seconds). |
| `--algorithm-mtd-quant-method-featurefindermetabo-openms` | string |  |  | `area`, `median`, `max_height` |  | `area` | Method of quantification for mass traces. For LC data 'area' is recommended, 'median' for direct injection data. 'max_height' simply uses the most intense peak in the trace. |
| `--algorithm-mtd-reestimate-mt-sd-featurefindermetabo-openms` | boolean |  |  |  |  | `true` | Enables dynamic re-estimation of m/z variance during mass trace collection stage. |
| `--algorithm-mtd-trace-termination-criterion-featurefindermetabo-openms` | string |  | yes | `outlier`, `sample_rate` |  | `outlier` | Termination criterion for the extension of mass traces. In 'outlier' mode, trace extension cancels if a predefined number of consecutive outliers are found (see trace_termination_outliers parameter). In 'sample_rate' mode, trace extension in both directions stops if ratio of found peaks versus visited spectra falls below the 'min_sample_rate' threshold. |
| `--algorithm-mtd-trace-termination-outliers-featurefindermetabo-openms` | integer |  | yes |  |  | `5` | Mass trace extension in one direction cancels if this number of consecutive spectra with no detectable peaks is reached. |
| `--algorithm-report-fwhm-peakpickerhires-openms` | boolean |  | yes |  |  |  | Add metadata for FWHM (as floatDataArray named 'FWHM' or 'FWHM_ppm', depending on param 'report_FWHM_unit') for each picked peak. |
| `--algorithm-report-fwhm-unit-peakpickerhires-openms` | string |  | yes | `relative`, `absolute` |  | `relative` | Unit of FWHM. Either absolute in the unit of input, e.g. 'm/z' for spectra, or relative as ppm (only sensible for spectra, not chromatograms). |
| `--algorithm-signal-to-noise-peakpickerhires-openms` | number |  |  |  |  |  | Minimal signal-to-noise ratio for a peak to be picked (0.0 disables SNT estimation!) |
| `--algorithm-signaltonoise-auto-max-percentile-peakpickerhires-openms` | integer |  | yes |  |  |  | parameter for 'max_intensity' estimation (if 'auto_mode' == 1): auto_max_percentile th percentile |
| `--algorithm-signaltonoise-auto-max-stdev-factor-peakpickerhires-openms` | number |  | yes |  |  |  | parameter for 'max_intensity' estimation (if 'auto_mode' == 0): mean + 'auto_max_stdev_factor' * stdev |
| `--algorithm-signaltonoise-auto-mode-peakpickerhires-openms` | integer |  | yes |  |  |  | method to use to determine maximal intensity: -1 --> use 'max_intensity'; 0 --> 'auto_max_stdev_factor' method (default); 1 --> 'auto_max_percentile' method |
| `--algorithm-signaltonoise-bin-count-peakpickerhires-openms` | integer |  | yes |  |  |  | number of bins for intensity values |
| `--algorithm-signaltonoise-max-intensity-peakpickerhires-openms` | integer |  | yes |  |  |  | maximal intensity considered for histogram construction. By default, it will be calculated automatically (see auto_mode). Only provide this parameter if you know what you are doing (and change 'auto_mode' to '-1')! All intensities EQUAL/ABOVE 'max_intensity' will be added to the LAST histogram bin. If you choose 'max_intensity' too small, the noise estimate might be too small as well. If chosen too big, the bins become quite large (which you could counter by increasing 'bin_count', which increases runtime). In general, the Median-S/N estimator is more robust to a manual max_intensity than the MeanIterative-S/N. |
| `--algorithm-signaltonoise-min-required-elements-peakpickerhires-openms` | integer |  | yes |  |  |  | minimum number of elements required in a window (otherwise it is considered sparse) |
| `--algorithm-signaltonoise-noise-for-empty-window-peakpickerhires-openms` | number |  | yes |  |  | `100000000000000000000` | noise value used for sparse windows |
| `--algorithm-signaltonoise-win-len-peakpickerhires-openms` | number |  | yes |  |  |  | window length in Thomson |
| `--algorithm-spacing-difference-gap-peakpickerhires-openms` | number |  | yes |  |  |  | The extension of a peak is stopped if the spacing between two subsequent data points exceeds 'spacing_difference_gap * min_spacing'. 'min_spacing' is the smaller of the two spacings from the peak apex to its two neighboring points. '0' to disable the constraint. Not applicable to chromatograms. |
| `--algorithm-spacing-difference-peakpickerhires-openms` | number |  | yes |  |  |  | Maximum allowed difference between points during peak extension, in multiples of the minimal difference between the peak apex and its two neighboring points. If this difference is exceeded a missing point is assumed (see parameter 'missing'). A higher value implies a less stringent peak definition, since individual signals within the peak are allowed to be further apart. '0' to disable the constraint. Not applicable to chromatograms. |

## re_quantification

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--detect-min-peak-width-featurefindermetaboident-openms` | number |  | yes |  |  |  | Minimum elution peak width. Absolute value in seconds if 1 or greater, else relative to 'peak_width'. |
| `--detect-peak-width-featurefindermetaboident-openms` | number |  |  |  |  |  | Expected elution peak width in seconds, for smoothing (Gauss filter). Also determines the RT extration window, unless set explicitly via 'extract:rt_window'. |
| `--detect-signal-to-noise-featurefindermetaboident-openms` | number |  | yes |  |  |  | Signal-to-noise threshold for OpenSWATH feature detection |
| `--emgscoring-init-mom-featurefindermetaboident-openms` | boolean |  |  |  |  |  | Alternative initial parameters for fitting through method of moments. |
| `--emgscoring-max-iteration-featurefindermetaboident-openms` | integer |  |  |  |  |  | Maximum number of iterations for EMG fitting. |
| `--extract-isotope-pmin-featurefindermetaboident-openms` | number |  | yes |  |  |  | Minimum probability for an isotope to be included in the assay for a peptide. If set, this parameter takes precedence over 'extract:n_isotopes'. |
| `--extract-mz-window-featurefindermetaboident-openms` | number |  |  |  |  |  | m/z window size for chromatogram extraction (unit: ppm if 1 or greater, else Da/Th) |
| `--extract-n-isotopes-featurefindermetaboident-openms` | integer |  |  |  |  |  | Number of isotopes to include in each peptide assay. |
| `--extract-rt-window-featurefindermetaboident-openms` | number |  | yes |  |  |  | RT window size (in sec.) for chromatogram extraction. If set, this parameter takes precedence over 'extract:rt_quantile'. |
| `--model-add-zeros-featurefindermetaboident-openms` | number |  | yes |  |  |  | Add zero-intensity points outside the feature range to constrain the model fit. This parameter sets the weight given to these points during model fitting; '0' to disable. |
| `--model-check-asymmetry-featurefindermetaboident-openms` | number |  | yes |  |  |  | Upper limit for acceptable asymmetry of elution models (EGH only), expressed in terms of modified (median-based) z-scores. '0' to disable. Not applied to individual mass traces (parameter 'each_trace'). |
| `--model-check-boundaries-featurefindermetaboident-openms` | number |  | yes |  |  |  | Time points corresponding to this fraction of the elution model height have to be within the data region used for model fitting |
| `--model-check-min-area-featurefindermetaboident-openms` | number |  | yes |  |  |  | Lower bound for the area under the curve of a valid elution model |
| `--model-check-width-featurefindermetaboident-openms` | number |  | yes |  |  |  | Upper limit for acceptable widths of elution models (Gaussian or EGH), expressed in terms of modified (median-based) z-scores. '0' to disable. Not applied to individual mass traces (parameter 'each_trace'). |
| `--model-each-trace-featurefindermetaboident-openms` | boolean |  | yes |  |  |  | Fit elution model to each individual mass trace |
| `--model-no-imputation-featurefindermetaboident-openms` | boolean |  | yes |  |  |  | If fitting the elution model fails for a feature, set its intensity to zero instead of imputing a value from the initial intensity estimate |
| `--model-type-featurefindermetaboident-openms` | string |  |  | `symmetric`, `asymmetric`, `none` |  | `symmetric` | Type of elution model to fit to features |
| `--model-unweighted-fit-featurefindermetaboident-openms` | boolean |  | yes |  |  |  | Suppress weighting of mass traces according to theoretical intensities when fitting elution models |

<!-- Generated from nf-core/metaboigniter@55d82547604fcae3b6557fe7a3c442b623184f34. Do not edit by hand. -->
