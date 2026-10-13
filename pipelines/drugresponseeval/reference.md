---
name: drugresponseeval
version: 1.3.0
commit: 6e420c1cc2f1be2907627d9b2b3aca77bf622603
---

# drugresponseeval — full parameter reference

nf-core/drugresponseeval pipeline parameters. Every parameter from the pinned `nextflow_schema.json`, validated by nf-schema at runtime. `hidden` marks nf-core's generic/boilerplate parameters; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) are enforced by nf-schema at runtime.

## additional_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--clean-min-responder-frac` | number |  |  |  | ≤ 1 |  | Keep only drugs whose fraction of significant responder curves is at least this value. |
| `--clean-min-responders` | integer |  |  |  | ≥ 1 |  | Keep only drugs with at least this many reproducible responder curves. |
| `--custom-splitter-path` | string (file path) |  |  |  | matches ^\S+\.py$ |  | Path to a Python script with a custom CV splitter. |
| `--final-model-on-full-data` | boolean |  |  |  |  | false | Train final model on full data. |
| `--model-checkpoint-dir` | string |  |  |  |  | TEMPORARY | Model checkpoint directory |
| `--n-cv-splits` | integer |  |  |  | ≥ 2 | 10 | Number of cross-validation splits. |
| `--no-hyperparameter-tuning` | boolean |  |  |  |  | false | Disable hyperparameter tuning. |
| `--no-refitting` | boolean |  |  |  |  | false | False by default (=refitting). By default, we use measures calculated with CurveCurator instead of original measures reported by the authors for the available datasets, or invoke automatic fitting of custom raw viability data with CurveCurator. Set this flag to disable this option. |
| `--optim-metric` | string |  |  | `RMSE`, `MSE`, `MAE`, `R^2`, `Pearson`, `Spearman`, `Kendall` |  | RMSE | Optimization metric for the pipeline. |
| `--response-transformation` | string |  |  | `None`, `standard`, `minmax`, `robust`, `drug_mean`, `drug_tissue_mean` |  | None | Response transformation |

## data_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--cross-study-datasets` | string |  |  |  | matches ^(?:\|(?:GDSC[12]\|CCLE\|CTRPv[12]\|TOYv[12]\|PDX_Bruna\|BeatAML2)(,(?:GDSC[12]\|CCLE\|CTRPv[12]\|TOYv[12]\|PDX_Bruna\|BeatAML2))*)$ |  | Datasets for cross-study prediction. |
| `--measure` | string |  |  | `LN_IC50`, `pEC50`, `AUC`, `response`, `EC50`, `IC50` |  | LN_IC50 | The name of the drug response measure to use. |
| `--path-data` | string (directory path) |  |  |  |  | data | Path to the data directory. |
| `--zenodo-link` | string |  |  |  | matches (^https://zenodo.org/records/[0-9]+/files/$)\|(https://github.com/nf-core/test-datasets/raw/refs/heads/drugresponseeval/test_data/) | https://zenodo.org/records/23159774/files/ | Link to the latest Zenodo version of the dataset. |

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

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--dataset-name` | string | yes |  |  |  | CTRPv2 | Name of the dataset. Pre-supplied datasets are CTRPv2, CTRPv1, CCLE, GDSC1, GDSC2, TOYv1, TOYv2, BeatAML2, and PDX_Bruna. |
| `--email` | string |  |  |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--outdir` | string (directory path) | yes |  |  |  | results | The output directory where the results will be saved. Default is results/ |
| `--run-id` | string | yes |  |  |  | my_run | Run name for the pipeline. The subdirectory in results will be named like this. |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/configs/master | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | master | Git commit id for Institutional configs. |

## mode_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--test-mode` | string | yes |  |  | matches ^((LPO\|LCO\|LTO\|LDO)?,?)*(?<!,)$ | LCO | Run the pipeline in test mode LPO (Leave-random-Pairs-Out), LCO (Leave-Cell-line-Out), LTO (Leave-Tissue-Out), or LDO (Leave-Drug-Out). |

## model_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--baselines` | string | yes |  |  |  | NaiveMeanEffectsPredictor | Baselines to be tested. |
| `--models` | string | yes |  |  |  | NaiveDrugMeanPredictor | Model to be tested. |

## randomization_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--randomization-mode` | string |  |  |  | matches ^(None\|(?:SVR[CD]\|SVC[CD])(,(?:SVR[CD]\|SVC[CD]))*)$ | None | Randomization mode for the pipeline. |
| `--randomization-type` | string |  |  | `permutation`, `invariant` |  | permutation | Randomization type for the pipeline. |

## robustness_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--n-trials-robustness` | integer |  |  |  | ≥ 0 | 0 | Number of trials to run for the robustness test |

<!-- Generated from nf-core/drugresponseeval@6e420c1cc2f1be2907627d9b2b3aca77bf622603. Do not edit by hand. -->
